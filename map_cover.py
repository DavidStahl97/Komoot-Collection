"""Renders a cover image for every komoot collection found under gpx/.

A collection is a folder below gpx/ holding its GPX files and optionally a
collection.json (title, highlights, rivers, endpoints). Without a collection.json
the map is drawn from every GPX in the folder and the folder name becomes the title.

    python3 map_cover.py                 # every collection into out/
    python3 map_cover.py brandy-haiger   # only this one
    python3 map_cover.py --out /tmp/cover
"""
import argparse, json, math, os, random, sys
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import icons as IC

NS = '{http://www.topografix.com/GPX/1/1}'
GPX_ROOT = 'gpx'
OUT_DIR = 'out'

S = 2                      # supersampling
W, H = 1600 * S, 1200 * S
PAPER = (243, 232, 208); INK = (59, 52, 42); MUTED = (126, 112, 88)
ACCENT = (176, 96, 58)
BOX = (300 * S, 70 * S, 1300 * S, 1130 * S)     # map frame on the sheet

FONT_DIRS = ["/usr/share/fonts/truetype/google-fonts",
             "/usr/share/fonts/truetype/dejavu",
             "/usr/share/fonts/truetype/liberation"]
FONT_FALLBACK = {"Lora-Italic-Variable": ["DejaVuSerif-Italic", "LiberationSerif-Italic"],
                 "Poppins-Medium": ["DejaVuSans", "LiberationSans-Regular"],
                 "Poppins-Bold": ["DejaVuSans-Bold", "LiberationSans-Bold"]}


def F(name, size):
    """Load a font; fall back to a system font when the Google fonts are missing."""
    for cand in [name] + FONT_FALLBACK.get(name, []):
        for dirn in FONT_DIRS:
            p = os.path.join(dirn, cand + ".ttf")
            if os.path.exists(p):
                return ImageFont.truetype(p, int(size * S))
    return ImageFont.load_default()


# --------------------------------------------------------------- GPX helpers
def load(path):
    r = ET.parse(path).getroot()
    pts = [(float(t.get('lat')), float(t.get('lon'))) for t in r.iter(NS + 'trkpt')]
    if not pts:                                   # GPX without namespace / route only
        pts = [(float(t.get('lat')), float(t.get('lon')))
               for t in r.iter() if t.tag.endswith('trkpt') or t.tag.endswith('rtept')]
    if not pts:
        raise ValueError("no track points in %s" % path)
    return np.array(pts)


def cum(a):
    R = 6371000.0; la = np.radians(a[:, 0]); lo = np.radians(a[:, 1])
    h = np.sin(np.diff(la) / 2) ** 2 + np.cos(la[:-1]) * np.cos(la[1:]) * np.sin(np.diff(lo) / 2) ** 2
    return np.concatenate([[0], np.cumsum(2 * R * np.arcsin(np.clip(np.sqrt(h), 0, 1)))])


def seg(a, k0, k1):
    c = cum(a); i0 = np.searchsorted(c, k0 * 1000); i1 = np.searchsorted(c, k1 * 1000)
    return a[i0:i1]


def at(a, km):
    c = cum(a); i = min(np.searchsorted(c, km * 1000), len(a) - 1)
    return float(a[i, 0]), float(a[i, 1])


# ------------------------------------------------------- reading a collection
def discover(root=GPX_ROOT):
    """Every subfolder of gpx/ holding at least one GPX file."""
    if not os.path.isdir(root):
        return []
    out = []
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if os.path.isdir(d) and any(f.lower().endswith('.gpx') for f in os.listdir(d)):
            out.append(d)
    if not out and any(f.lower().endswith('.gpx') for f in os.listdir(root)):
        out.append(root)                          # flat gpx/ (legacy layout)
    return out


def slugify(name):
    """Collection or folder name -> file-safe slug; German umlauts are transliterated."""
    keep = "abcdefghijklmnopqrstuvwxyz0123456789-_"
    s = name.lower().replace(' ', '-')
    for a, b in (('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss')):
        s = s.replace(a, b)
    s = ''.join(c for c in s if c in keep)
    return s.strip('-_') or "collection"


def read_config(folder):
    """Read collection.json and fill missing fields with defaults from the folder."""
    cfg = {}
    p = os.path.join(folder, 'collection.json')
    if os.path.exists(p):
        with open(p, encoding='utf-8') as fh:
            cfg = json.load(fh)

    folder_name = os.path.basename(os.path.abspath(folder))
    cfg.setdefault('name', folder_name)
    cfg.setdefault('output', slugify(folder_name) + '.png')
    cfg.setdefault('title', [w.upper() for w in folder_name.replace('_', '-').split('-') if w][:2])
    cfg.setdefault('subtitle', [])
    cfg.setdefault('arrow', len(cfg['title']) == 2)
    cfg.setdefault('rivers', [])
    cfg.setdefault('highlights', [])
    cfg.setdefault('endpoints', [])

    files = sorted(f for f in os.listdir(folder) if f.lower().endswith('.gpx'))
    entries = cfg.get('routes') or [{'key': os.path.splitext(f)[0], 'file': f} for f in files]

    routes, order = {}, []
    for e in entries:
        if isinstance(e, str):
            e = {'key': os.path.splitext(e)[0], 'file': e}
        fp = os.path.join(folder, e['file'])
        if not os.path.exists(fp):
            raise FileNotFoundError("%s: missing GPX: %s" % (cfg['name'], e['file']))
        key = e.get('key') or os.path.splitext(e['file'])[0]
        routes[key] = load(fp)
        order.append(key)

    known = {os.path.basename(e['file']) if isinstance(e, dict) else e for e in entries}
    for f in files:                               # draw unconfigured GPX as well
        if f not in known:
            key = os.path.splitext(f)[0]
            routes[key] = load(os.path.join(folder, f)); order.append(key)

    cfg['_routes'] = routes
    cfg['_order'] = order
    return cfg


def route_of(cfg, key):
    r = cfg['_routes'].get(key)
    if r is None:
        raise KeyError("%s: unknown route '%s' (known: %s)"
                       % (cfg['name'], key, ', '.join(cfg['_order'])))
    return r


def icon_of(name):
    fn = getattr(IC, name, None)
    if not callable(fn):
        raise KeyError("unknown icon '%s' — add it to icons.py" % name)
    return fn


# ----------------------------------------------------------------- rendering
def render(cfg, out_path):
    ROUTES = [cfg['_routes'][k] for k in cfg['_order']]

    img = Image.new('RGB', (W, H), PAPER)

    # paper grain
    rnd = random.Random(7)
    grain = Image.new('L', (W // 4, H // 4))
    grain.putdata([rnd.randint(0, 255) for _ in range(grain.size[0] * grain.size[1])])
    grain = grain.resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1))
    img = Image.composite(Image.new('RGB', (W, H), (233, 221, 196)), img,
                          grain.point(lambda v: 20 if v > 150 else 0))
    d = ImageDraw.Draw(img)

    # projection (shared bounding box of every route in this collection)
    def merc(a):
        return np.radians(a[:, 1]), np.log(np.tan(np.pi / 4 + np.radians(a[:, 0]) / 2))

    AX = np.concatenate([merc(r)[0] for r in ROUTES]); AY = np.concatenate([merc(r)[1] for r in ROUTES])
    pad = 0.10
    spanx = max(AX.max() - AX.min(), 1e-9); spany = max(AY.max() - AY.min(), 1e-9)
    sc = min((BOX[2] - BOX[0]) / (spanx * (1 + pad)), (BOX[3] - BOX[1]) / (spany * (1 + pad)))
    cx, cy = (AX.min() + AX.max()) / 2, (AY.min() + AY.max()) / 2
    MX, MY = (BOX[0] + BOX[2]) / 2, (BOX[1] + BOX[3]) / 2

    def P(lat, lon):
        x = math.radians(lon); y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
        return (MX + (x - cx) * sc, MY - (y - cy) * sc)

    def PA(a):
        X, Y = merc(a); return list(zip(MX + (X - cx) * sc, MY - (Y - cy) * sc))

    # woodland (soft blobs along the routes)
    forest = Image.new('L', (W, H), 0); fd = ImageDraw.Draw(forest)
    rnd = random.Random(11)
    for r in ROUTES:
        pts = PA(r)
        for i in range(0, len(pts), 9):
            x, y = pts[i]
            rr = rnd.randint(34, 88) * S
            if rnd.random() < 0.55:
                fd.ellipse([x - rr, y - rr * 0.8, x + rr, y + rr * 0.8], fill=255)
    rnd2 = random.Random(41)
    for _ in range(26):
        x = rnd2.randint(0, W); y = rnd2.randint(0, H)
        rr = rnd2.randint(90, 210) * S
        fd.ellipse([x - rr, y - rr * 0.75, x + rr, y + rr * 0.75], fill=88)
    forest = forest.filter(ImageFilter.GaussianBlur(26 * S))
    forest = forest.point(lambda v: 255 if v > 110 else int(v * 0.9))
    img = Image.composite(Image.new('RGB', (W, H), (214, 222, 190)), img,
                          forest.point(lambda v: int(v * 0.38)))
    d = ImageDraw.Draw(img)
    fmask = forest.load()
    rmask = Image.new('L', (W, H), 0); rmd = ImageDraw.Draw(rmask)
    for r in ROUTES:
        rmd.line(PA(r), fill=255, width=int(30 * S), joint='curve')
    rmask = rmask.load()
    rnd = random.Random(23)
    for _ in range(1700):
        x = rnd.randint(0, W - 1); y = rnd.randint(0, H - 1)
        if fmask[x, y] > 170 and rmask[x, y] == 0 and rnd.random() < 0.34:
            IC.tree(d, x, y, rnd.uniform(4.5, 7.5) * S, (164, 184, 138))
    for _ in range(420):
        x = rnd.randint(0, W - 1); y = rnd.randint(0, H - 1)
        if 60 < fmask[x, y] <= 170 and rmask[x, y] == 0 and rnd.random() < 0.34:
            IC.tree(d, x, y, rnd.uniform(3.5, 5.5) * S, (202, 210, 180))

    # rivers (derived from route segments)
    for w in cfg['rivers']:
        pts = PA(seg(route_of(cfg, w['route']), w['from'], w['to']))
        if len(pts) < 2:
            continue
        wd = w.get('width', 6)
        d.line(pts, fill=(150, 190, 206), width=int(wd * S * 1.9), joint='curve')
        d.line(pts, fill=(112, 164, 188), width=int(wd * S), joint='curve')

    # routes: dashed hiking-map line
    def dashed(pts, col, dash=14, gap=10, w=4):
        acc = 0; on = True; cur = [pts[0]]
        for i in range(1, len(pts)):
            x0, y0 = pts[i - 1]; x1, y1 = pts[i]
            seglen = math.hypot(x1 - x0, y1 - y0); t = 0
            while t < seglen:
                step = min((dash if on else gap) * S - acc, seglen - t)
                nx = x0 + (x1 - x0) * (t + step) / seglen; ny = y0 + (y1 - y0) * (t + step) / seglen
                if on:
                    cur.append((nx, ny))
                t += step; acc += step
                if acc >= (dash if on else gap) * S - 0.01:
                    if on and len(cur) > 1:
                        d.line(cur, fill=col, width=int(w * S), joint='curve')
                    on = not on; acc = 0; cur = [(nx, ny)]
        if on and len(cur) > 1:
            d.line(cur, fill=col, width=int(w * S), joint='curve')

    for r in ROUTES:
        dashed(PA(r), (255, 255, 255), w=7, dash=14, gap=10)
    for r in ROUTES:
        dashed(PA(r), ACCENT, w=4, dash=14, gap=10)

    # highlights
    f_lab = F("Lora-Italic-Variable", 26); f_place = F("Poppins-Medium", 30)

    def label(x, y, txt, font, side):
        tw = d.textlength(txt, font=font); th = font.size
        tx = x - tw / 2 if side == 'c' else (x if side == 'r' else x - tw)
        d.rectangle([tx - 9 * S, y - 5 * S, tx + tw + 9 * S, y + th + 7 * S], fill=(246, 237, 216))
        d.text((tx, y), txt, font=font, fill=INK)

    for hl in cfg['highlights']:
        la, lo = (hl['lat'], hl['lon']) if 'lat' in hl else at(route_of(cfg, hl['route']), hl['km'])
        ox, oy = hl.get('offset', (14, 44))
        x, y = P(la, lo)
        icon_of(hl['icon'])(d, x, y, hl.get('size', 34) * S)
        label(x + ox * S, y + oy * S, hl['label'], f_lab, hl.get('side', 'r'))

    # endpoints
    for ep in cfg['endpoints']:
        x, y = P(ep['lat'], ep['lon'])
        icon_of(ep['icon'])(d, x, y, ep.get('size', 44) * S)
        name = ep['label']
        tw = d.textlength(name, font=f_place)
        yy = y + 62 * S
        d.rectangle([x - tw / 2 - 14 * S, yy, x + tw / 2 + 14 * S, yy + f_place.size + 12 * S], fill=INK)
        d.text((x - tw / 2, yy + 5 * S), name, font=f_place, fill=PAPER)

    # compass
    ccx, ccy, cr = 1478 * S, 1086 * S, 54 * S
    d.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], outline=ACCENT, width=3 * S)
    d.polygon([(ccx, ccy - cr * .82), (ccx - cr * .24, ccy + cr * .10), (ccx + cr * .24, ccy + cr * .10)], fill=ACCENT)
    d.polygon([(ccx, ccy + cr * .72), (ccx - cr * .24, ccy + cr * .10), (ccx + cr * .24, ccy + cr * .10)], fill=(214, 200, 172))
    f_n = F("Poppins-Medium", 22)
    d.text((ccx - d.textlength("N", font=f_n) / 2, ccy - cr - 32 * S), "N", font=f_n, fill=INK)

    # title cartouche, bottom left (grows upwards with the number of lines)
    titles = list(cfg['title']); subs = list(cfg['subtitle'])
    if titles or subs:
        f_t = F("Poppins-Bold", 60); f_s = F("Lora-Italic-Variable", 27)
        arrow = cfg['arrow'] and len(titles) >= 2

        h = 42 * S
        for i, _ in enumerate(titles):
            h += f_t.size
            if i < len(titles) - 1:
                h += (58 * S if arrow else 20 * S)
        if subs:
            h += 52 * S + len(subs) * 40 * S
        h += 27 * S

        wid = max([d.textlength(t, font=f_t) for t in titles] +
                  [d.textlength(s, font=f_s) for s in subs] + [0]) + 68 * S
        cx0, cy1 = 64 * S, 1042 * S
        cx1 = cx0 + max(414 * S, wid); cy0 = cy1 - h
        d.rectangle([cx0, cy0, cx1, cy1], fill=(246, 238, 218), outline=ACCENT, width=3 * S)
        d.rectangle([cx0 + 9 * S, cy0 + 9 * S, cx1 - 9 * S, cy1 - 9 * S], outline=(206, 186, 152), width=1 * S)

        tx = cx0 + 34 * S; y = cy0 + 42 * S
        for i, t in enumerate(titles):
            d.text((tx, y), t, font=f_t, fill=INK)
            y += f_t.size
            if i < len(titles) - 1:
                if arrow:
                    ay = y + 30 * S; a0, a1 = tx + 2 * S, tx + 134 * S
                    d.line([(a0, ay), (a1, ay)], fill=ACCENT, width=5 * S)
                    for xx, dx in ((a0, 1), (a1, -1)):
                        d.line([(xx, ay), (xx + 13 * S * dx, ay - 9 * S)], fill=ACCENT, width=5 * S)
                        d.line([(xx, ay), (xx + 13 * S * dx, ay + 9 * S)], fill=ACCENT, width=5 * S)
                    y += 58 * S
                else:
                    y += 20 * S
        if subs:
            y += 32 * S
            d.line([(tx, y), (cx1 - 34 * S, y)], fill=(206, 186, 152), width=2 * S)
            y += 20 * S
            for s in subs:
                d.text((tx, y), s, font=f_s, fill=MUTED)
                y += 40 * S

    img = img.resize((1600, 1200), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    img.save(out_path)
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render cover images for komoot collections")
    ap.add_argument('collections', nargs='*', help="folder names below gpx/ (default: all)")
    ap.add_argument('--gpx', default=GPX_ROOT, help="root folder of the collections (default: gpx)")
    ap.add_argument('--out', default=OUT_DIR, help="target folder for the PNGs (default: out)")
    a = ap.parse_args(argv)

    folders = discover(a.gpx)
    if a.collections:
        wanted = {c.rstrip('/\\') for c in a.collections}
        folders = [f for f in folders if os.path.basename(os.path.abspath(f)) in wanted]
        missing = wanted - {os.path.basename(os.path.abspath(f)) for f in folders}
        if missing:
            sys.exit("no such collection: %s" % ', '.join(sorted(missing)))
    if not folders:
        sys.exit("no collection found in %s/ — put the GPX files into a subfolder." % a.gpx)

    for folder in folders:
        cfg = read_config(folder)
        out = render(cfg, os.path.join(a.out, cfg['output']))
        print("%-24s %d routes -> %s" % (cfg['name'], len(cfg['_order']), out))


if __name__ == '__main__':
    main()
