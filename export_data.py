"""Exports everything the web app needs: the geometry as JSON, the icons as SVG, the images.

This script writes no markup, no stylesheet and no script. It reads the GPX exports through
map_cover.py, projects them into the pixels of the finished image and hands the result
across as data; what the reader sees is built from that by the application under web/.

    python3 map_cover.py --out out
    python3 export_data.py --png out --out web/static

Result, below the target folder:

    data/index.json         every collection, the theme and the shipped fonts
    data/<slug>.json        one collection: routes, highlights, endpoints, profiles
    data/icons.json         the icon names from icons.py
    icons/sprite.svg        every icon at every size a collection uses, as <use> targets
    icons/<name>.svg        one icon on its own, for the icon page
    icons/<name>.png        the same icon stamped by PIL, to compare it against
    covers/                 the cover images and their backgrounds
    pwa/                    the app icon
    fonts/                  the label fonts, if they may travel

and next to the application sources:

    src/generated/tokens.css    the map colors as custom properties
    src/generated/theme.json    the same values, for the build configuration
"""
import argparse, inspect, json, math, os, shutil, sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw

import icons as IC
import svgdraw
from map_cover import (ACCENT, BOX, GPX_ROOT, H, INK, MUTED, OUT_DIR, PAPER, S, W, at,
                       bg_name, cartouche_box, cum, discover, font_file, icon_of,
                       projection, read_config, route_of, slugify)

STATIC_DIR = os.path.join('web', 'static')      # what the application serves as it is
GEN_DIR = os.path.join('web', 'src', 'generated')

DATA_DIR = 'data'
ICON_DIR = 'icons'
COVER_DIR = 'covers'
PWA_DIR = 'pwa'
FONT_DIR = 'fonts'

IC_S = 2                        # supersampling of the icon sheets
IC_PX = 150                     # edge length of an icon sheet in pixels

VIEW = (W // S, H // S)         # the finished image: 1600 x 1200 pixels

# Label fonts, mirrored from render(): the size is what the SVG uses, the file is what the
# site ships. Nothing has to line up with the background — it carries no labels — but a map
# whose two halves are set in different faces reads as two maps.
LABEL_FONTS = {'label': ("Lora-Italic-Variable", 26),
               'place': ("Poppins-Medium", 30)}

# The names the application knows these colors by. The map is drawn from the constants in
# map_cover.py, so the site has no business writing them down a second time.
THEME = {'paper': PAPER, 'ink': INK, 'muted': MUTED, 'accent': ACCENT}


def hexcol(rgb):
    return '#%02x%02x%02x' % tuple(rgb)


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


IC_BIG = IC_PX * IC_S * 4       # the sheet an icon is stamped on before it is cropped
IC_FIT = 0.8                    # share of the sheet the cropped icon is fitted into


def stamp(fn, path):
    """Draw a single icon onto a small sheet of paper; returns its box around the centre.

    The icons reach past their radius by different amounts — fox and shark are wider
    than the lake. So they are stamped large, cropped to what was actually drawn and
    only then fitted onto the sheet. That measured box is what icon_svg() frames the
    vector version with, so both end up at the same crop and the same scale.
    """
    img = Image.new('RGB', (IC_BIG, IC_BIG), PAPER)
    fn(ImageDraw.Draw(img), IC_BIG / 2, IC_BIG / 2, IC_BIG * 0.12)
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
    return (box[0] - IC_BIG / 2, box[1] - IC_BIG / 2,
            box[2] - IC_BIG / 2, box[3] - IC_BIG / 2)


def icon_svg(name, fn, box):
    """The same icon as its own SVG file, framed like the stamped sheet.

    Recorded at the same radius the stamp uses, so the width clamps inside icons.py
    resolve the same way, and framed with the box PIL measured — the two tiles on the
    icon page are therefore directly comparable, which is the whole point of showing them
    next to each other.
    """
    x0, y0, x1, y1 = box
    side = max(x1 - x0, y1 - y0) / IC_FIT
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s %s %s %s" '
            'role="img" aria-label="Icon %s as vector">%s</svg>\n'
            % (svgdraw.num(cx - side / 2), svgdraw.num(cy - side / 2),
               svgdraw.num(side), svgdraw.num(side), name,
               svgdraw.record(fn, IC_BIG * 0.12)))


def write_sprite(path, sprite):
    """Every icon a collection asks for, once per size, as a <use> target.

    A <g> rather than a <symbol>: the recorded markup is centred on the origin and reaches
    into negative coordinates, which a symbol would clip at its own viewport. Inside <defs>
    nothing of it renders until a <use> asks for it.
    """
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" '
             'style="position:absolute;width:0;height:0;overflow:hidden"><defs>']
    for key in sorted(sprite):
        parts.append('<g id="ic-%s">%s</g>' % (key, sprite[key]))
    parts.append('</defs></svg>\n')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(''.join(parts))


# ------------------------------------------------------------------ geometry
def rdp(pts, tol):
    """Ramer-Douglas-Peucker: the indices of the points nobody can do without.

    Indices, not points, because the elevation profile has to find its way back from a
    place on the line to the kilometre it sits at. The tolerance is a quarter pixel of the
    finished image, not a whole one: the line is zoomable now, and at four times the size
    a whole pixel of error walks visibly out of the tree-free corridor the background was
    stamped around it.
    """
    if len(pts) < 3:
        return list(range(len(pts)))
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i0, i1 = stack.pop()
        (x0, y0), (x1, y1) = pts[i0], pts[i1]
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy)
        best, bi = -1.0, -1
        for i in range(i0 + 1, i1):
            x, y = pts[i]
            dist = (abs(dy * x - dx * y + x1 * y0 - y1 * x0) / n if n
                    else math.hypot(x - x0, y - y0))
            if dist > best:
                best, bi = dist, i
        if bi > 0 and best > tol:
            keep[bi] = True
            stack.append((i0, bi)); stack.append((bi, i1))
    return [i for i, k in enumerate(keep) if k]


PROFILE_N = 400                 # samples of one elevation profile


def profile(route, ele):
    """Elevation sampled evenly along the distance, plus the ascent that follows from it.

    Evenly by distance, so the index is the position along the tour and no kilometre
    values have to travel with it. The ascent is summed over the whole track rather than
    over the samples, and without a threshold: measured against komoot the sum already
    comes out about a tenth low, and every bit of hysteresis widens that gap instead of
    closing it. komoot uses its own elevation model, not the exported track.
    """
    if ele is None or len(ele) != len(route):
        return None
    c = cum(route)
    total = float(c[-1])
    if total <= 0:
        return None
    ys = np.interp(np.linspace(0, total, PROFILE_N), c, ele)
    return {'ele': [int(round(float(v))) for v in ys],
            'lo': int(round(float(ys.min()))), 'hi': int(round(float(ys.max()))),
            'ascent': int(round(float(np.clip(np.diff(ele), 0, None).sum()), -1))}


def geometry(cfg, sprite):
    """Everything the interactive map draws, in pixels of the finished image.

    The same projection as the renderer, only with the map frame scaled down by the
    supersampling — so the vector lines land exactly in the tree-free corridors the
    background was stamped around them. Label boxes are not in here: the browser measures
    its own text, which is the one thing this file used to have to guess.
    """
    order = cfg['_order']
    routes = [cfg['_routes'][k] for k in order]
    P, PA = projection(routes, tuple(v / S for v in BOX))

    data = {'view': list(VIEW), 'sup': S, 'guard': [],
            'label': "Map of the collection %s" % cfg['name'],
            'routes': [], 'highlights': [], 'endpoints': []}

    # The cartouche is filled opaquely and sits inside the map frame: on the drawn map the
    # routes run underneath it, so the vector layer has to be clipped out of it.
    box = cartouche_box(cfg)
    if box:
        x0, y0, x1, y1 = (v / S for v in box)
        data['guard'].append([round(x0, 1), round(y0, 1),
                              round(x1 - x0, 1), round(y1 - y0, 1)])

    def sym(name, size):
        """Record an icon once per name and size; the key is its id in the sprite.

        The size is part of the key because the stroke widths inside icons.py are clamped
        with max(2, int(s·k)) — recorded at another scale those clamps resolve differently
        and the vector icon drifts away from the drawn one.
        """
        key = '%s-%g' % (name, size)
        if key not in sprite:
            # recorded at the radius the renderer passes, placed with a matching scale(1/S)
            sprite[key] = svgdraw.record(icon_of(name), size * S)
        return key

    for key in order:
        r = cfg['_routes'][key]
        pts = PA(r)
        c = cum(r)
        total = float(c[-1]) or 1.0
        entry = {
            'key': key,
            'label': cfg['_labels'].get(key, key),
            'file': cfg['_files'].get(key, ''),
            'km': round(total / 1000, 1),
            # x, y and the position along the tour in per mille — the third number is what
            # ties a place on the map to a place in the elevation profile
            'pts': [[round(pts[i][0], 1), round(pts[i][1], 1), int(round(c[i] / total * 1000))]
                    for i in rdp(pts, 0.25)],
        }
        entry.update(profile(r, cfg.get('_ele', {}).get(key)) or {})
        data['routes'].append(entry)

    for hl in cfg['highlights']:
        lat, lon = (hl['lat'], hl['lon']) if 'lat' in hl else at(route_of(cfg, hl['route']), hl['km'])
        x, y = P(lat, lon)
        size = hl.get('size', 34)
        ox, oy = hl.get('offset', (14, 44))
        data['highlights'].append({
            'label': hl['label'], 'route': hl.get('route'), 'km': hl.get('km'),
            # `icon` is the name from the configuration, `sym` the id in the sprite
            'icon': hl['icon'], 'sym': sym(hl['icon'], size), 'size': size,
            'x': round(x, 1), 'y': round(y, 1),
            'ax': round(x + ox, 1), 'ay': round(y + oy, 1),
            'side': hl.get('side', 'r'),
        })

    for ep in cfg['endpoints']:
        x, y = P(ep['lat'], ep['lon'])
        size = ep.get('size', 44)
        data['endpoints'].append({
            'label': ep['label'], 'icon': ep['icon'], 'sym': sym(ep['icon'], size), 'size': size,
            'x': round(x, 1), 'y': round(y, 1),
            'ax': round(x, 1), 'ay': round(y + 62, 1),
            'side': 'c',
        })
    return data


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


# ---------------------------------------------------------------------- fonts
def licence_beside(path):
    """The licence file belonging to a font, or None — no licence, no handing on."""
    folder = os.path.dirname(path)
    family = os.path.splitext(os.path.basename(path))[0].split('-')[0]
    for cand in ('%s-OFL.txt' % family, '%s-LICENSE.txt' % family, 'OFL.txt', 'LICENSE.txt'):
        p = os.path.join(folder, cand)
        if os.path.exists(p):
            return p
    return None


def ship_fonts(static_dir):
    """Copy the label fonts next to the site — but only those that may travel.

    The vector labels are set in the same face the PNG was drawn with, which is only
    possible if that file may be passed on. Lora and Poppins come with their Open Font
    License, so they go; whatever a Windows or Linux machine happens to provide instead
    does not, so it stays where it is and the CSS falls back to what the reader has. Both
    halves therefore always agree: in CI both are Lora and Poppins, on a machine without
    them both are the system serif and sans.

    The @font-face rules are static in the application: a face whose file never arrives
    simply does not apply, and the fallback in the same declaration takes over.
    """
    shipped = []
    for kind in sorted(LABEL_FONTS):
        path = font_file(LABEL_FONTS[kind][0])
        lic = licence_beside(path) if path else None
        if not path or not lic:
            continue
        os.makedirs(os.path.join(static_dir, FONT_DIR), exist_ok=True)
        for src in (path, lic):
            shutil.copyfile(src, os.path.join(static_dir, FONT_DIR, os.path.basename(src)))
        shipped.append({'kind': kind, 'file': os.path.basename(path),
                        'licence': os.path.basename(lic)})
    return shipped


# ----------------------------------------------------------------- collecting
def collect(gpx_root, out_dir):
    """Collect configuration, cover image and background for every collection."""
    items = []
    for folder in discover(gpx_root):
        cfg = read_config(folder)
        png = os.path.join(out_dir, cfg['output'])
        if not os.path.exists(png):
            print("skipped (no PNG): %s" % cfg['name'], file=sys.stderr)
            continue
        # without the background the page falls back to the plain cover image
        bg = os.path.join(out_dir, bg_name(cfg['output']))
        items.append((slugify(os.path.basename(os.path.abspath(folder))), cfg, png,
                      bg if os.path.exists(bg) else None))
    return items


def write_json(path, data, compact=False):
    with open(path, 'w', encoding='utf-8') as fh:
        if compact:
            json.dump(data, fh, ensure_ascii=False, separators=(',', ':'))
        else:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write('\n')


def write_tokens(gen_dir):
    """The map colors, once as custom properties and once for the build configuration.

    The application is painted in the colors the map is drawn in, and those live in
    map_cover.py. Writing them down a second time in a stylesheet is how the two drift
    apart, so they are generated instead — data that happens to be in CSS syntax.
    """
    os.makedirs(gen_dir, exist_ok=True)
    theme = {k: hexcol(v) for k, v in THEME.items()}
    with open(os.path.join(gen_dir, 'tokens.css'), 'w', encoding='utf-8') as fh:
        fh.write("/* Generated by export_data.py from the constants in map_cover.py. */\n"
                 ":root {\n")
        for k in sorted(theme):
            fh.write("  --%s: %s;\n" % (k, theme[k]))
        fh.write("}\n")
    write_json(os.path.join(gen_dir, 'theme.json'), theme)
    return theme


def export(gpx_root, out_dir, static_dir, gen_dir):
    items = collect(gpx_root, out_dir)
    if not items:
        sys.exit("no maps found in %s/ — run map_cover.py first." % out_dir)

    for sub in (DATA_DIR, ICON_DIR, COVER_DIR, PWA_DIR):
        os.makedirs(os.path.join(static_dir, sub), exist_ok=True)

    theme = write_tokens(gen_dir)

    # the app icon of the progressive web app, drawn with the primitives of the maps
    for name, px, mask in (('icon-192.png', 192, False), ('icon-512.png', 512, False),
                           ('icon-maskable-512.png', 512, True),
                           ('apple-touch-icon.png', 180, False)):
        app_icon(os.path.join(static_dir, PWA_DIR, name), px, mask)
    shipped = ship_fonts(static_dir)

    # every icon twice: stamped by PIL and recorded as SVG, from the same function
    names = []
    for name, fn in icon_list():
        box = stamp(fn, os.path.join(static_dir, ICON_DIR, name + '.png'))
        with open(os.path.join(static_dir, ICON_DIR, name + '.svg'), 'w', encoding='utf-8') as fh:
            fh.write(icon_svg(name, fn, box))
        names.append(name)
    write_json(os.path.join(static_dir, DATA_DIR, 'icons.json'), {'icons': names})

    sprite, index = {}, []
    for slug, cfg, png, bg in items:
        cover = '%s/%s' % (COVER_DIR, os.path.basename(png))
        shutil.copyfile(png, os.path.join(static_dir, cover))
        ground = None
        if bg:
            ground = '%s/%s' % (COVER_DIR, os.path.basename(bg))
            shutil.copyfile(bg, os.path.join(static_dir, ground))

        data = geometry(cfg, sprite)
        data.update({'slug': slug, 'name': cfg['name'], 'subtitle': cfg['subtitle'],
                     'cover': cover, 'bg': ground})
        write_json(os.path.join(static_dir, DATA_DIR, slug + '.json'), data, compact=True)

        index.append({'slug': slug, 'name': cfg['name'], 'subtitle': cfg['subtitle'],
                      'tours': len(cfg['_order']), 'highlights': len(cfg['highlights']),
                      'cover': cover, 'bg': ground})

    write_sprite(os.path.join(static_dir, ICON_DIR, 'sprite.svg'), sprite)
    write_json(os.path.join(static_dir, DATA_DIR, 'index.json'),
               {'theme': theme, 'fonts': shipped, 'collections': index})

    print("%d collections, %d icons, %d sprite symbols, %d fonts -> %s"
          % (len(items), len(names), len(sprite), len(shipped), static_dir))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export the data the web app is built from")
    ap.add_argument('--gpx', default=GPX_ROOT, help="root folder of the collections (default: gpx)")
    ap.add_argument('--png', default=OUT_DIR, help="folder with the rendered PNGs (default: out)")
    ap.add_argument('--out', default=STATIC_DIR,
                    help="target folder, served as it is (default: web/static)")
    ap.add_argument('--generated', default=GEN_DIR,
                    help="target folder for tokens.css and theme.json "
                         "(default: web/src/generated)")
    a = ap.parse_args(argv)
    export(a.gpx, a.png, a.out, a.generated)


if __name__ == '__main__':
    main()
