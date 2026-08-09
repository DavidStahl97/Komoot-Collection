"""Builds the GitHub Page from the rendered maps: Home, Collections, Icons.

Expects the PNGs that map_cover.py wrote to out/, reads the configuration of every
collection and additionally stamps each icon from icons.py onto its own small sheet.

    python3 map_cover.py --out out
    python3 build_site.py --out site

Result:

    site/index.html                 Home — every collection with its cover image
    site/collections/index.html     overview, one subpage per collection
    site/icons/index.html           every icon as a list
    site/manifest.webmanifest       the site as an installable progressive web app
    site/sw.js                      service worker, precaches everything for offline use
"""
import argparse, hashlib, html, inspect, json, math, os, shutil, sys

from PIL import Image, ImageChops, ImageDraw

import icons as IC
from map_cover import ACCENT, GPX_ROOT, INK, MUTED, OUT_DIR, PAPER, discover, read_config, slugify

SITE_DIR = 'site'
IC_S = 2                        # supersampling of the icon sheets
IC_PX = 150                     # edge length of an icon sheet in pixels

PWA_DIR = 'pwa'                 # app icons, below the site root
APP_NAME = "Maps for komoot collections"
APP_SHORT = "komoot maps"
APP_DESC = ("Illustrated cover images for komoot collections — drawn from the GPX exports "
            "of the tours.")

CSS = """
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #f3e8d0; color: #3b342a;
         font-family: Georgia, "Times New Roman", serif;
         /* viewport-fit=cover: installed on a phone the page runs under the notch */
         padding: env(safe-area-inset-top) calc(24px + env(safe-area-inset-right))
                  calc(72px + env(safe-area-inset-bottom)) calc(24px + env(safe-area-inset-left)); }
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
  .card { background: #f6eeda; border: 3px solid #b0603a; padding: 12px; }
  .card > div { border: 1px solid #ceba98; padding: 16px; height: 100%; }
  .card img { display: block; width: 100%; height: auto; border: 1px solid #ceba98; }
  .card p { margin: 0 0 10px; color: #7e7058; font-style: italic; }
  .meta { margin: 0; font-size: .85rem; color: #7e7058; font-style: normal; }
  .icons { display: grid; gap: 22px; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); }
  .icon { background: #f6eeda; border: 1px solid #ceba98; padding: 12px; text-align: center; }
  .icon img { display: block; width: 100%; height: auto; }
  .icon code { font-size: .85rem; color: #3b342a; }
  .icon span { display: block; font-size: .78rem; color: #7e7058; font-style: italic; }
  table { border-collapse: collapse; width: 100%; margin: 0 0 32px; }
  th, td { text-align: left; padding: 7px 12px 7px 0; border-bottom: 1px solid #ceba98;
           font-size: .95rem; }
  th { color: #7e7058; font-weight: normal; font-style: italic; }
  td img { vertical-align: middle; width: 34px; height: 34px; }
  footer { border-top: 1px solid #ceba98; margin-top: 56px; padding-top: 14px;
           font-size: .85rem; color: #7e7058; }
"""

PAGE = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="{paper}">
<link rel="manifest" href="{base}manifest.webmanifest">
<link rel="icon" href="{base}pwa/icon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="{base}pwa/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{short}">
<meta name="mobile-web-app-capable" content="yes">
<style>{css}</style>
<script>
  // Progressive web app: the service worker precaches pages, maps and icons, so an
  // installed copy also opens without a network. Registration is optional — without it
  // the page is an ordinary static site.
  if ("serviceWorker" in navigator)
    addEventListener("load", function () {{ navigator.serviceWorker.register("{base}sw.js"); }});
</script>
<nav><div class="wrap"><ul>
{nav}
</ul></div></nav>
<div class="wrap">
{body}
<footer>Generated by <a href="https://github.com/{repo}">{repo}</a>{built}.</footer>
</div>
</html>
"""


# -------------------------------------------------------------------- icons
def icon_list():
    """Every icon in icons.py — functions with the signature fn(d, x, y, s)."""
    out = []
    for name, fn in sorted(vars(IC).items()):
        if name.startswith('_') or not inspect.isfunction(fn) or fn.__module__ != IC.__name__:
            continue
        params = list(inspect.signature(fn).parameters)[:4]
        if params == ['d', 'x', 'y', 's']:
            out.append((name, fn))
    return out


def stamp(fn, path):
    """Draw a single icon onto a small sheet of paper.

    The icons reach past their radius by different amounts — fox and shark are wider
    than the lake. So they are stamped large, cropped to what was actually drawn and
    only then fitted onto the sheet.
    """
    big = IC_PX * IC_S * 4
    img = Image.new('RGB', (big, big), PAPER)
    fn(ImageDraw.Draw(img), big / 2, big / 2, big * 0.12)
    box = ImageChops.difference(img, Image.new('RGB', img.size, PAPER)).getbbox()
    if box is None:
        raise ValueError("icon draws nothing: %s" % fn.__name__)

    px, pad = IC_PX * IC_S, IC_PX * IC_S // 10
    icon = img.crop(box)
    k = min((px - 2 * pad) / icon.width, (px - 2 * pad) / icon.height)
    icon = icon.resize((max(1, int(icon.width * k)), max(1, int(icon.height * k))),
                       Image.LANCZOS)
    sheet = Image.new('RGB', (px, px), PAPER)
    sheet.paste(icon, ((px - icon.width) // 2, (px - icon.height) // 2))
    sheet.resize((IC_PX, IC_PX), Image.LANCZOS).save(path)


# ------------------------------------------------------------- app identity
def rose(d, x, y, r):
    """Compass rose — the motif of the app icon, taken from the compass on the map."""
    IC.circ(d, x, y, r * 1.16, outline=MUTED, w=max(1, int(r * 0.045)))
    IC.circ(d, x, y, r * 1.30, outline=INK, w=max(1, int(r * 0.07)))
    for i in range(4):                                   # short points, diagonal
        a = math.radians(45 + 90 * i)
        d.polygon([(x + r * 0.62 * math.cos(a), y + r * 0.62 * math.sin(a)),
                   (x + r * 0.20 * math.cos(a + math.pi / 2),
                    y + r * 0.20 * math.sin(a + math.pi / 2)),
                   (x + r * 0.20 * math.cos(a - math.pi / 2),
                    y + r * 0.20 * math.sin(a - math.pi / 2))], fill=ACCENT)
    for i in range(4):                                   # long points, cardinal
        a = math.radians(90 * i - 90)
        tip = (x + r * math.cos(a), y + r * math.sin(a))
        for side in (1, -1):                             # one half dark, one half light
            base = (x + r * 0.17 * math.cos(a + side * math.pi / 2),
                    y + r * 0.17 * math.sin(a + side * math.pi / 2))
            d.polygon([tip, base, (x, y)],
                      fill=INK if side > 0 else PAPER, outline=INK)


def app_icon(path, px, maskable=False):
    """The icon of the installed app: compass rose on paper.

    A maskable icon may be cropped to a circle by the launcher, so the rose stays inside
    the safe zone (80 % of the edge) and the frame of the other icons is left out.
    """
    s, k = 4, 0.28 if maskable else 0.30             # supersampling, radius share
    big = px * s
    img = Image.new('RGB', (big, big), PAPER)
    d = ImageDraw.Draw(img)
    if not maskable:
        m, w = big * 0.06, max(1, int(big * 0.035))
        d.rectangle([m, m, big - m - 1, big - m - 1], outline=ACCENT, width=w)
    rose(d, big / 2, big / 2, big * k)
    img.resize((px, px), Image.LANCZOS).save(path)


def manifest(site_dir):
    """The web app manifest — all paths relative, the page lives in a repository subfolder."""
    icon = lambda f, size, purpose: {"src": "%s/%s" % (PWA_DIR, f), "sizes": "%dx%d" % (size, size),
                                     "type": "image/png", "purpose": purpose}
    data = {
        "name": APP_NAME,
        "short_name": APP_SHORT,
        "description": APP_DESC,
        "lang": "en",
        "start_url": "./",
        "scope": "./",
        "id": "./",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#%02x%02x%02x" % PAPER,
        "theme_color": "#%02x%02x%02x" % PAPER,
        "icons": [icon("icon-192.png", 192, "any"), icon("icon-512.png", 512, "any"),
                  icon("icon-maskable-512.png", 512, "maskable")],
    }
    path = os.path.join(site_dir, 'manifest.webmanifest')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


SW = """// Service worker of the progressive web app — generated by build_site.py.
// The cache name carries a hash over all files: a build with unchanged content keeps
// the cache, any change replaces it as a whole.
const CACHE = "komoot-maps-%(version)s";
const ASSETS = %(assets)s;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;

  // Pages from the network first, so a new deployment is visible right away; the cache
  // steps in when offline. Images and the manifest come from the cache — the cache name
  // changes with every content change anyway.
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request)
        .then((hit) => hit || caches.match(self.registration.scope))));
    return;
  }

  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
});
"""


def service_worker(site_dir):
    """Write sw.js with a precache list of everything below site/ and a content hash."""
    files, h = [], hashlib.sha256()
    for root, _, names in os.walk(site_dir):
        for name in sorted(names):
            if name == 'sw.js':
                continue
            p = os.path.join(root, name)
            rel = os.path.relpath(p, site_dir).replace(os.sep, '/')
            files.append(rel)
            with open(p, 'rb') as fh:
                h.update(rel.encode()); h.update(fh.read())
    files.sort()
    # "./" is the start URL of the manifest and has to be cached under that name as well.
    assets = ['./'] + files
    with open(os.path.join(site_dir, 'sw.js'), 'w', encoding='utf-8') as fh:
        fh.write(SW % {'version': h.hexdigest()[:12],
                       'assets': json.dumps(assets, indent=2)})
    return len(assets)


# ---------------------------------------------------------------- page build
def nav_html(items, active, base):
    """Navigation with the collections as sub-items."""
    li = []
    for key, label, href, subs in items:
        cur = ' aria-current="page"' if key == active else ''
        sub = ''
        if subs:
            sub = '\n    <ul>%s</ul>' % ''.join(
                '<li><a href="%s%s">%s</a></li>' % (base, h, html.escape(t)) for t, h in subs)
        li.append('  <li><a href="%s%s"%s>%s</a>%s</li>' % (base, href, cur, html.escape(label), sub))
    return '\n'.join(li)


def page(path, title, body, nav, repo, built, base):
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(PAGE.format(title=html.escape(title), css=CSS, nav=nav, body=body,
                             base=base, desc=html.escape(APP_DESC),
                             short=html.escape(APP_SHORT),
                             paper="#%02x%02x%02x" % PAPER,
                             repo=html.escape(repo),
                             built=(" — built: %s" % html.escape(built)) if built else ""))
    return path


def card(name, subtitle, meta, img, href):
    return """  <article class="card"><div>
    <a href="{href}"><img src="{img}" alt="Cover image of the collection {name}" loading="lazy"></a>
    <h2><a href="{href}">{name}</a></h2>
    {sub}<p class="meta">{meta}</p>
  </div></article>""".format(
        href=href, img=img, name=html.escape(name), meta=html.escape(meta),
        sub=("<p>%s</p>\n    " % html.escape(subtitle)) if subtitle else "")


def collect(gpx_root, out_dir):
    """Collect configuration and cover image for every collection."""
    items = []
    for folder in discover(gpx_root):
        cfg = read_config(folder)
        png = os.path.join(out_dir, cfg['output'])
        if not os.path.exists(png):
            print("skipped (no PNG): %s" % cfg['name'], file=sys.stderr)
            continue
        items.append((slugify(os.path.basename(os.path.abspath(folder))), cfg, png))
    return items


def build(gpx_root, out_dir, site_dir, repo, built):
    items = collect(gpx_root, out_dir)
    if not items:
        sys.exit("no maps found in %s/ — run map_cover.py first." % out_dir)

    for sub in ('covers', 'collections', 'icons', PWA_DIR):
        os.makedirs(os.path.join(site_dir, sub), exist_ok=True)

    # app icons and manifest — the site is installable as a progressive web app
    for name, px, mask in (('icon-192.png', 192, False), ('icon-512.png', 512, False),
                           ('icon-maskable-512.png', 512, True),
                           ('apple-touch-icon.png', 180, False)):
        app_icon(os.path.join(site_dir, PWA_DIR, name), px, mask)
    manifest(site_dir)

    # write out cover images and icons
    covers = {}
    for slug, cfg, png in items:
        covers[slug] = 'covers/' + os.path.basename(png)
        shutil.copyfile(png, os.path.join(site_dir, covers[slug]))
    names = []
    for name, fn in icon_list():
        stamp(fn, os.path.join(site_dir, 'icons', name + '.png'))
        names.append(name)

    subs = [(cfg['name'], 'collections/%s.html' % slug) for slug, cfg, _ in items]
    nav_items = [('home', 'Home', 'index.html', []),
                 ('collections', 'Collections', 'collections/index.html', subs),
                 ('icons', 'Icons', 'icons/index.html', [])]

    def meta_of(cfg):
        m = "%d tours" % len(cfg['_order'])
        if cfg['highlights']:
            m += ", %d highlights" % len(cfg['highlights'])
        return m

    # --------------------------------------------------------------- home
    cards = [card(cfg['name'], ' '.join(cfg['subtitle']), meta_of(cfg),
                  covers[slug], 'collections/%s.html' % slug)
             for slug, cfg, _ in items]
    body = ("<h1>Maps for komoot collections</h1>\n"
            "<p class=\"lead\">Drawn from the GPX exports of the tours — tinted paper, "
            "dashed paths, stamped woodland. Every map is 1600×1200 pixels and is rebuilt "
            "on each push to <code>main</code>.</p>\n"
            "<div class=\"grid\">\n%s\n</div>" % '\n'.join(cards))
    page(os.path.join(site_dir, 'index.html'), "Maps for komoot collections", body,
         nav_html(nav_items, 'home', ''), repo, built, '')

    # ------------------------------------------------------- collections
    nav_c = nav_html(nav_items, 'collections', '../')
    cards = [card(cfg['name'], ' '.join(cfg['subtitle']), meta_of(cfg),
                  '../' + covers[slug], '%s.html' % slug)
             for slug, cfg, _ in items]
    body = ("<h1>Collections</h1>\n"
            "<p class=\"lead\">One folder below <code>gpx/</code> per collection — its own "
            "map frame, its own highlights, its own cover image.</p>\n"
            "<div class=\"grid\">\n%s\n</div>" % '\n'.join(cards))
    page(os.path.join(site_dir, 'collections', 'index.html'), "Collections", body,
         nav_c, repo, built, '../')

    for slug, cfg, png in items:
        rows = []
        for h in cfg['highlights'] + cfg['endpoints']:
            icon = h.get('icon')
            img = ('<img src="../icons/%s.png" alt="">' % html.escape(icon)
                   if icon in names else '')
            where = ("%s at km %s" % (h['route'], h['km'])) if 'km' in h else "fixed coordinate"
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                        % (img, html.escape(str(h.get('label', ''))), html.escape(where)))
        table = ("<h2>Highlights and endpoints</h2>\n<table><tr><th></th><th>Label</th>"
                 "<th>Location</th></tr>\n%s</table>" % '\n'.join(rows)) if rows else ""
        files = {e['key']: e['file'] for e in cfg.get('routes') or []
                 if isinstance(e, dict) and e.get('key')}
        tours = ("<h2>Tours</h2>\n<table><tr><th>Key</th><th>GPX</th></tr>%s</table>"
                 % ''.join("<tr><td>%s</td><td>%s</td></tr>"
                           % (html.escape(k), html.escape(files.get(k, k + '.gpx')))
                           for k in cfg['_order']))
        lead = ('<p class="lead">%s</p>\n' % html.escape(' '.join(cfg['subtitle']))
                if cfg['subtitle'] else '')
        body = ('<h1>%s</h1>\n%s'
                '<p><img src="../%s" alt="Cover image of the collection %s" '
                'style="width:100%%;height:auto;border:1px solid #ceba98"></p>\n'
                '<p class="meta">%s &middot; <a href="../%s">download PNG</a></p>\n%s%s'
                % (html.escape(cfg['name']), lead, covers[slug], html.escape(cfg['name']),
                   html.escape(meta_of(cfg)), covers[slug], tours, table))
        page(os.path.join(site_dir, 'collections', slug + '.html'), cfg['name'], body,
             nav_c, repo, built, '../')

    # ------------------------------------------------------------- icons
    tiles = ['  <figure class="icon"><img src="%s.png" alt="Icon %s" loading="lazy">'
             '<figcaption><code>%s</code></figcaption></figure>' % (n, n, n) for n in names]
    body = ("<h1>Icons</h1>\n"
            "<p class=\"lead\">The icons from <code>icons.py</code>, each drawn with PIL "
            "primitives. The function name is also the value of <code>\"icon\"</code> in the "
            "<code>collection.json</code>.</p>\n"
            "<div class=\"icons\">\n%s\n</div>" % '\n'.join(tiles))
    page(os.path.join(site_dir, 'icons', 'index.html'), "Icons", body,
         nav_html(nav_items, 'icons', '../'), repo, built, '../')

    # last, because the service worker precaches everything that exists at this point
    cached = service_worker(site_dir)
    print("%d collections, %d icons, %d files precached -> %s/index.html"
          % (len(items), len(names), cached, site_dir))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the GitHub Page from the rendered maps")
    ap.add_argument('--gpx', default=GPX_ROOT, help="root folder of the collections (default: gpx)")
    ap.add_argument('--png', default=OUT_DIR, help="folder with the rendered PNGs (default: out)")
    ap.add_argument('--out', default=SITE_DIR, help="target folder for the site (default: site)")
    ap.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY',
                                                     'DavidStahl97/Komoot-Collection'))
    ap.add_argument('--built', default=os.environ.get('BUILD_DATE', ''),
                    help="date shown in the footer")
    a = ap.parse_args(argv)
    build(a.gpx, a.png, a.out, a.repo, a.built)


if __name__ == '__main__':
    main()
