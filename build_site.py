"""Baut aus den erzeugten Karten die GitHub-Page: Home, Collections, Icons.

Erwartet die PNGs, die map_cover.py nach out/ geschrieben hat, liest zu jeder
Collection deren Konfiguration und stempelt zusaetzlich jedes Motiv aus icons.py
einzeln auf ein kleines Blatt.

    python3 map_cover.py --out out
    python3 build_site.py --out site

Ergebnis:

    site/index.html                 Home — alle Collections mit ihrem Titelbild
    site/collections/index.html     Uebersicht, je Collection eine Unterseite
    site/icons/index.html           alle Motive als Liste
"""
import argparse, html, inspect, os, shutil, sys

from PIL import Image, ImageChops, ImageDraw

import icons as IC
from map_cover import GPX_ROOT, OUT_DIR, PAPER, discover, read_config, slugify

SITE_DIR = 'site'
IC_S = 2                        # Supersampling der Icon-Blaetter
IC_PX = 150                     # Kantenlaenge eines Icon-Blatts in Pixeln

CSS = """
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 0 24px 72px; background: #f3e8d0; color: #3b342a;
         font-family: Georgia, "Times New Roman", serif; }
  a { color: #b0603a; }
  .wrap { max-width: 1100px; margin: 0 auto; }
  nav { border-bottom: 2px solid #b0603a; padding: 20px 0 14px; margin-bottom: 40px; }
  nav ul { list-style: none; margin: 0; padding: 0; display: flex; gap: 34px; flex-wrap: wrap; }
  nav > .wrap > ul > li > a { text-transform: uppercase; letter-spacing: .08em;
                              text-decoration: none; font-size: .95rem; }
  nav a[aria-current] { color: #3b342a; border-bottom: 2px solid #b0603a; }
  nav ul ul { display: block; margin: 6px 0 0; }
  nav ul ul a { font-size: .82rem; font-style: italic; color: #7e7058; }
  h1 { margin: 0 0 12px; font-size: 2.1rem; letter-spacing: .06em; text-transform: uppercase; }
  h2 { margin: 18px 0 6px; font-size: 1.25rem; letter-spacing: .05em; text-transform: uppercase; }
  .lead { margin: 0 0 40px; color: #7e7058; font-style: italic; max-width: 46em; }
  .grid { display: grid; gap: 32px; justify-content: center;
          grid-template-columns: repeat(auto-fit, minmax(320px, 520px)); }
  .karte { background: #f6eeda; border: 3px solid #b0603a; padding: 12px; }
  .karte > div { border: 1px solid #ceba98; padding: 16px; height: 100%; }
  .karte img { display: block; width: 100%; height: auto; border: 1px solid #ceba98; }
  .karte p { margin: 0 0 10px; color: #7e7058; font-style: italic; }
  .meta { margin: 0; font-size: .85rem; color: #7e7058; font-style: normal; }
  .motive { display: grid; gap: 22px; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); }
  .motiv { background: #f6eeda; border: 1px solid #ceba98; padding: 12px; text-align: center; }
  .motiv img { display: block; width: 100%; height: auto; }
  .motiv code { font-size: .85rem; color: #3b342a; }
  .motiv span { display: block; font-size: .78rem; color: #7e7058; font-style: italic; }
  table { border-collapse: collapse; width: 100%; margin: 0 0 32px; }
  th, td { text-align: left; padding: 7px 12px 7px 0; border-bottom: 1px solid #ceba98;
           font-size: .95rem; }
  th { color: #7e7058; font-weight: normal; font-style: italic; }
  td img { vertical-align: middle; width: 34px; height: 34px; }
  footer { border-top: 1px solid #ceba98; margin-top: 56px; padding-top: 14px;
           font-size: .85rem; color: #7e7058; }
"""

PAGE = """<!doctype html>
<html lang="de">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
<nav><div class="wrap"><ul>
{nav}
</ul></div></nav>
<div class="wrap">
{body}
<footer>Erzeugt von <a href="https://github.com/{repo}">{repo}</a>{stand}.</footer>
</div>
</html>
"""


# ------------------------------------------------------------------- Motive
def motive():
    """Alle Motive aus icons.py — Funktionen mit der Signatur fn(d, x, y, s)."""
    out = []
    for name, fn in sorted(vars(IC).items()):
        if name.startswith('_') or not inspect.isfunction(fn) or fn.__module__ != IC.__name__:
            continue
        params = list(inspect.signature(fn).parameters)[:4]
        if params == ['d', 'x', 'y', 's']:
            out.append((name, fn))
    return out


def stamp(fn, path):
    """Ein Motiv auf ein kleines Blatt Papier zeichnen.

    Die Motive zeichnen unterschiedlich weit ueber ihren Radius hinaus — Fuchs und
    Hai sind breiter als der See. Darum wird gross gestempelt, auf das tatsaechlich
    Gezeichnete beschnitten und erst dann ins Blatt eingepasst.
    """
    big = IC_PX * IC_S * 4
    img = Image.new('RGB', (big, big), PAPER)
    fn(ImageDraw.Draw(img), big / 2, big / 2, big * 0.12)
    box = ImageChops.difference(img, Image.new('RGB', img.size, PAPER)).getbbox()
    if box is None:
        raise ValueError("Motiv zeichnet nichts: %s" % fn.__name__)

    px, pad = IC_PX * IC_S, IC_PX * IC_S // 10
    motiv = img.crop(box)
    k = min((px - 2 * pad) / motiv.width, (px - 2 * pad) / motiv.height)
    motiv = motiv.resize((max(1, int(motiv.width * k)), max(1, int(motiv.height * k))),
                         Image.LANCZOS)
    blatt = Image.new('RGB', (px, px), PAPER)
    blatt.paste(motiv, ((px - motiv.width) // 2, (px - motiv.height) // 2))
    blatt.resize((IC_PX, IC_PX), Image.LANCZOS).save(path)


# --------------------------------------------------------------- Seitenbau
def nav_html(items, active, base):
    """Navigation mit den Collections als Unterpunkte."""
    li = []
    for key, label, href, subs in items:
        cur = ' aria-current="page"' if key == active else ''
        sub = ''
        if subs:
            sub = '\n    <ul>%s</ul>' % ''.join(
                '<li><a href="%s%s">%s</a></li>' % (base, h, html.escape(t)) for t, h in subs)
        li.append('  <li><a href="%s%s"%s>%s</a>%s</li>' % (base, href, cur, html.escape(label), sub))
    return '\n'.join(li)


def page(path, title, body, nav, repo, stand, base):
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(PAGE.format(title=html.escape(title), css=CSS, nav=nav, body=body,
                             repo=html.escape(repo),
                             stand=(" — Stand: %s" % html.escape(stand)) if stand else ""))
    return path


def card(name, subtitle, meta, img, href):
    return """  <article class="karte"><div>
    <a href="{href}"><img src="{img}" alt="Titelbild der Collection {name}" loading="lazy"></a>
    <h2><a href="{href}">{name}</a></h2>
    {sub}<p class="meta">{meta}</p>
  </div></article>""".format(
        href=href, img=img, name=html.escape(name), meta=html.escape(meta),
        sub=("<p>%s</p>\n    " % html.escape(subtitle)) if subtitle else "")


def collect(gpx_root, out_dir):
    """Je Collection Konfiguration und Titelbild einsammeln."""
    items = []
    for folder in discover(gpx_root):
        cfg = read_config(folder)
        png = os.path.join(out_dir, cfg['output'])
        if not os.path.exists(png):
            print("uebersprungen (kein PNG): %s" % cfg['name'], file=sys.stderr)
            continue
        items.append((slugify(os.path.basename(os.path.abspath(folder))), cfg, png))
    return items


def build(gpx_root, out_dir, site_dir, repo, stand):
    items = collect(gpx_root, out_dir)
    if not items:
        sys.exit("Keine Karten in %s/ gefunden — erst map_cover.py laufen lassen." % out_dir)

    for sub in ('karten', 'collections', 'icons'):
        os.makedirs(os.path.join(site_dir, sub), exist_ok=True)

    # Titelbilder und Motive ablegen
    covers = {}
    for slug, cfg, png in items:
        covers[slug] = 'karten/' + os.path.basename(png)
        shutil.copyfile(png, os.path.join(site_dir, covers[slug]))
    names = []
    for name, fn in motive():
        stamp(fn, os.path.join(site_dir, 'icons', name + '.png'))
        names.append(name)

    subs = [(cfg['name'], 'collections/%s.html' % slug) for slug, cfg, _ in items]
    nav_items = [('home', 'Home', 'index.html', []),
                 ('collections', 'Collections', 'collections/index.html', subs),
                 ('icons', 'Icons', 'icons/index.html', [])]

    def meta_of(cfg):
        m = "%d Touren" % len(cfg['_order'])
        if cfg['highlights']:
            m += ", %d Highlights" % len(cfg['highlights'])
        return m

    # -------------------------------------------------------------- Home
    cards = [card(cfg['name'], ' '.join(cfg['subtitle']), meta_of(cfg),
                  covers[slug], 'collections/%s.html' % slug)
             for slug, cfg, _ in items]
    body = ("<h1>Karten für komoot-Collections</h1>\n"
            "<p class=\"lead\">Aus den GPX-Exporten der Touren gezeichnet — getöntes Papier, "
            "gestrichelte Wege, gestempelte Wälder. Jede Karte ist 1600×1200 Pixel groß und "
            "wird bei jedem Push auf <code>main</code> neu erzeugt.</p>\n"
            "<div class=\"grid\">\n%s\n</div>" % '\n'.join(cards))
    page(os.path.join(site_dir, 'index.html'), "Karten für komoot-Collections", body,
         nav_html(nav_items, 'home', ''), repo, stand, '')

    # ------------------------------------------------------- Collections
    nav_c = nav_html(nav_items, 'collections', '../')
    cards = [card(cfg['name'], ' '.join(cfg['subtitle']), meta_of(cfg),
                  '../' + covers[slug], '%s.html' % slug)
             for slug, cfg, _ in items]
    body = ("<h1>Collections</h1>\n"
            "<p class=\"lead\">Ein Ordner unter <code>gpx/</code> je Collection — eigener "
            "Kartenausschnitt, eigene Highlights, eigenes Titelbild.</p>\n"
            "<div class=\"grid\">\n%s\n</div>" % '\n'.join(cards))
    page(os.path.join(site_dir, 'collections', 'index.html'), "Collections", body,
         nav_c, repo, stand, '../')

    for slug, cfg, png in items:
        rows = []
        for h in cfg['highlights'] + cfg['endpoints']:
            icon = h.get('icon')
            img = ('<img src="../icons/%s.png" alt="">' % html.escape(icon)
                   if icon in names else '')
            wo = ("%s bei km %s" % (h['route'], h['km'])) if 'km' in h else "feste Koordinate"
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                        % (img, html.escape(str(h.get('label', ''))), html.escape(wo)))
        tabelle = ("<h2>Highlights und Endpunkte</h2>\n<table><tr><th></th><th>Beschriftung</th>"
                   "<th>Fundstelle</th></tr>\n%s</table>" % '\n'.join(rows)) if rows else ""
        dateien = {e['key']: e['file'] for e in cfg.get('routes') or []
                   if isinstance(e, dict) and e.get('key')}
        touren = ("<h2>Touren</h2>\n<table><tr><th>Kürzel</th><th>GPX</th></tr>%s</table>"
                  % ''.join("<tr><td>%s</td><td>%s</td></tr>"
                            % (html.escape(k), html.escape(dateien.get(k, k + '.gpx')))
                            for k in cfg['_order']))
        lead = ('<p class="lead">%s</p>\n' % html.escape(' '.join(cfg['subtitle']))
                if cfg['subtitle'] else '')
        body = ('<h1>%s</h1>\n%s'
                '<p><img src="../%s" alt="Titelbild der Collection %s" '
                'style="width:100%%;height:auto;border:1px solid #ceba98"></p>\n'
                '<p class="meta">%s &middot; <a href="../%s">PNG herunterladen</a></p>\n%s%s'
                % (html.escape(cfg['name']), lead, covers[slug], html.escape(cfg['name']),
                   html.escape(meta_of(cfg)), covers[slug], touren, tabelle))
        page(os.path.join(site_dir, 'collections', slug + '.html'), cfg['name'], body,
             nav_c, repo, stand, '../')

    # ------------------------------------------------------------- Icons
    kacheln = ['  <figure class="motiv"><img src="%s.png" alt="Motiv %s" loading="lazy">'
               '<figcaption><code>%s</code></figcaption></figure>' % (n, n, n) for n in names]
    body = ("<h1>Icons</h1>\n"
            "<p class=\"lead\">Die Motive aus <code>icons.py</code>, jedes mit PIL-Primitiven "
            "gezeichnet. Der Funktionsname ist zugleich der Wert von <code>\"icon\"</code> in "
            "der <code>collection.json</code>.</p>\n"
            "<div class=\"motive\">\n%s\n</div>" % '\n'.join(kacheln))
    page(os.path.join(site_dir, 'icons', 'index.html'), "Icons", body,
         nav_html(nav_items, 'icons', '../'), repo, stand, '../')

    print("%d Collections, %d Motive -> %s/index.html" % (len(items), len(names), site_dir))


def main(argv=None):
    ap = argparse.ArgumentParser(description="GitHub-Page aus den erzeugten Karten bauen")
    ap.add_argument('--gpx', default=GPX_ROOT, help="Wurzelordner der Collections (Default: gpx)")
    ap.add_argument('--png', default=OUT_DIR, help="Ordner mit den erzeugten PNGs (Default: out)")
    ap.add_argument('--out', default=SITE_DIR, help="Zielordner der Seite (Default: site)")
    ap.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY',
                                                     'DavidStahl97/Komoot-Collection'))
    ap.add_argument('--stand', default=os.environ.get('BUILD_DATE', ''), help="Datum in der Fusszeile")
    a = ap.parse_args(argv)
    build(a.gpx, a.png, a.out, a.repo, a.stand)


if __name__ == '__main__':
    main()
