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

import numpy as np
from PIL import Image, ImageChops, ImageDraw

import icons as IC
import svgdraw
from map_cover import (ACCENT, BOX, GPX_ROOT, H, INK, MUTED, OUT_DIR, PAPER, S, W, at,
                       bg_name, cartouche_box, cum, discover, font_file, icon_of,
                       projection, read_config, route_of, slugify)

SITE_DIR = 'site'
MAP_JS_NAME = 'map.js'          # the client module, written next to the pages
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
  .icon img, .icon svg { display: block; width: 100%; height: auto; background: #f3e8d0; }
  /* stamped and recorded side by side — the pair is the check that svgdraw.py still
     draws what icons.py draws; there is no other test for it */
  .icon .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .icon .pair em { display: block; font-size: .68rem; font-style: normal; color: #7e7058;
                   letter-spacing: .08em; }
  .icon code { font-size: .85rem; color: #3b342a; }
  .icon span { display: block; font-size: .78rem; color: #7e7058; font-style: italic; }
  table { border-collapse: collapse; width: 100%; margin: 0 0 32px; }
  th, td { text-align: left; padding: 7px 12px 7px 0; border-bottom: 1px solid #ceba98;
           font-size: .95rem; }
  th { color: #7e7058; font-weight: normal; font-style: italic; }
  td img { vertical-align: middle; width: 34px; height: 34px; }
  footer { border-top: 1px solid #ceba98; margin-top: 56px; padding-top: 14px;
           font-size: .85rem; color: #7e7058; }

  /* The interactive map. The painted background is an image, everything that means
     something is a vector on top of it — so picking a tour is a class name, not a hole
     cut into a veil, and two tours crossing is not a case that has to be handled. */
  .mapfig { position: relative; margin: 0 0 12px; border: 1px solid #ceba98; line-height: 0;
            background: #f3e8d0; aspect-ratio: 4 / 3; }
  .mapfig:focus-visible { outline: 2px solid #b0603a; outline-offset: 2px; }
  .zoom { position: absolute; top: 10px; right: 10px; display: flex; flex-direction: column;
          gap: 4px; }
  .zoom button { width: 32px; height: 32px; font: 16px/1 Georgia, serif; cursor: pointer;
                 background: #f6eeda; color: #3b342a; border: 1px solid #ceba98; }
  .zoom button:hover, .zoom button:focus-visible { border-color: #b0603a; }
  .mapfig > svg, .mapfig img { display: block; width: 100%; height: auto; }
  .mapfig > svg { touch-action: none; -webkit-user-select: none; user-select: none; }
  .mapfig .grab { fill: transparent; }
  .mapfig .casing { fill: none; stroke: #fff; stroke-width: 7; stroke-dasharray: 14 10;
                    stroke-linecap: butt; stroke-linejoin: round; }
  .mapfig .dash { fill: none; stroke: #b0603a; stroke-width: 4; stroke-dasharray: 14 10;
                  stroke-linecap: butt; stroke-linejoin: round; }
  .mapfig .plate { fill: #f6edd8; }
  .mapfig .lab text { font: italic 26px "map-label", Georgia, "Times New Roman", serif;
                      fill: #3b342a; }
  .mapfig .place .plate { fill: #3b342a; }
  .mapfig .place text { font: 30px "map-place", "Segoe UI", Helvetica, Arial, sans-serif;
                        fill: #f3e8d0; }
  /* What marks the picked tour is that everything else steps back: a sheet of paper over
     the painted map, and the other lines and highlights fading into it. Nothing is drawn
     on top of the picked one — being the only thing left in front is the emphasis. */
  .mapfig .wash { fill: #f3e8d0; opacity: 0; transition: opacity .35s ease; }
  .mapfig svg.focus .wash { opacity: .58; }
  .mapfig .route, .mapfig .mark { transition: opacity .25s ease; }
  .mapfig svg.focus .route { opacity: .13; }
  .mapfig svg.focus .route.on { opacity: 1; }
  .mapfig svg.focus .mark { opacity: .10; }
  .mapfig svg.focus .mark.on { opacity: 1; }
  .mapfig .cursor circle { fill: #b0603a; stroke: #fff; stroke-width: 2; }
  /* the elevation profile of the picked tour, its cursor tied to the map both ways */
  .profile { margin: 0 0 14px; }
  .profile[hidden] { display: none; }
  .profile svg { display: block; width: 100%; height: auto; background: #f6eeda;
                 border: 1px solid #ceba98; }
  .profile .area { fill: #b0603a; fill-opacity: .16; }
  .profile .line { fill: none; stroke: #b0603a; stroke-width: 1.5; }
  .profile .base { stroke: #ceba98; stroke-width: 1; }
  .profile .rule { stroke: #3b342a; stroke-width: 1; }
  .profile .tick { font: 13px Georgia, serif; fill: #7e7058; }
  .profile figcaption { font-size: .82rem; color: #7e7058; font-style: italic;
                        padding-top: 5px; }
  .profile .read { font-style: normal; color: #3b342a; }
  .caption { margin: 0 0 26px; font-size: .9rem; color: #7e7058; font-style: italic;
             min-height: 1.4em; }
  .tours { list-style: none; margin: 0 0 10px; padding: 0; display: grid; gap: 10px;
           grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
  .tours button { width: 100%; display: flex; align-items: baseline; gap: 10px;
                  font: inherit; text-align: left; cursor: pointer;
                  background: #f6eeda; color: #3b342a;
                  border: 1px solid #ceba98; padding: 10px 12px; }
  .tours button:hover, .tours button:focus-visible { border-color: #b0603a; }
  .tours button[aria-pressed="true"] { border-color: #b0603a; background: #f0e2c4;
                                       box-shadow: inset 3px 0 0 #b0603a; }
  .tours .no { color: #b0603a; font-size: .85rem; letter-spacing: .08em; }
  .tours .km { margin-left: auto; color: #7e7058; font-size: .85rem; font-style: italic; }
  .dim { opacity: .38; }
  .actions { margin: 0 0 30px; font-size: .9rem; }
  .actions a { margin-right: 18px; }
  /* without JavaScript the map is the plain cover image again, so the controls that only
     work with it are not offered at all */
  .no-js .tours { display: none; }
  @media (prefers-reduced-motion: reduce) {
    .mapfig .wash, .mapfig .route, .mapfig .mark { transition: none; }
  }
"""

PAGE = """<!doctype html>
<html lang="en" class="no-js">
<script>document.documentElement.classList.remove("no-js");</script>
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
<style>{css}{styles}</style>
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
<footer>Generated by <a href="https://github.com/{repo}">{repo}</a>{built}.{credit}</footer>
</div>
{script}
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


def icon_svg(name, fn, box, cls='vec'):
    """The same icon as SVG, framed like the stamped sheet.

    Recorded at the same radius the stamp uses, so the width clamps inside icons.py
    resolve the same way, and framed with the box PIL measured — the two tiles on the
    icon page are therefore directly comparable, which is the whole point of showing them
    next to each other.
    """
    x0, y0, x1, y1 = box
    side = max(x1 - x0, y1 - y0) / IC_FIT
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return ('<svg class="%s" viewBox="%s %s %s %s" role="img" aria-label="Icon %s as vector">'
            '%s</svg>'
            % (cls, svgdraw.num(cx - side / 2), svgdraw.num(cy - side / 2),
               svgdraw.num(side), svgdraw.num(side), html.escape(name),
               svgdraw.record(fn, IC_BIG * 0.12)))


# ------------------------------------------------------- interactive overlay
VIEW = (W // S, H // S)         # the finished image: 1600 x 1200 pixels

# Label fonts, mirrored from render(): the size is what the SVG uses, the file is what the
# site ships. Nothing has to line up with the background any more — it carries no labels —
# but a map whose two halves are set in different faces reads as two maps.
LABEL_FONTS = {'label': ("Lora-Italic-Variable", 26),
               'place': ("Poppins-Medium", 30)}


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


def geometry(cfg, bg):
    """Everything the interactive map draws, in pixels of the finished image.

    The same projection as the renderer, only with the map frame scaled down by the
    supersampling — so the vector lines land exactly in the tree-free corridors the
    background was stamped around them. Label boxes are not in here: the browser measures
    its own text, which is the one thing this file used to have to guess.
    """
    order = cfg['_order']
    routes = [cfg['_routes'][k] for k in order]
    P, PA = projection(routes, tuple(v / S for v in BOX))

    data = {'view': list(VIEW), 'sup': S, 'bg': bg, 'guard': [], 'icons': {},
            'label': "Map of the collection %s" % cfg['name'],
            'routes': [], 'highlights': [], 'endpoints': []}

    # The cartouche is filled opaquely and sits inside the map frame: on the drawn map the
    # routes run underneath it, so the vector layer has to be clipped out of it.
    box = cartouche_box(cfg)
    if box:
        x0, y0, x1, y1 = (v / S for v in box)
        data['guard'].append([round(x0, 1), round(y0, 1),
                              round(x1 - x0, 1), round(y1 - y0, 1)])

    def icon(name, size):
        """Record an icon once per name and size; the key is its id in the page."""
        key = '%s-%g' % (name, size)
        if key not in data['icons']:
            # recorded at the radius the renderer passes, placed with a matching scale(1/S)
            data['icons'][key] = svgdraw.record(icon_of(name), size * S)
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
            'icon': icon(hl['icon'], size), 'size': size,
            'x': round(x, 1), 'y': round(y, 1),
            'ax': round(x + ox, 1), 'ay': round(y + oy, 1),
            'side': hl.get('side', 'r'), 'font': 'label',
        })

    for ep in cfg['endpoints']:
        x, y = P(ep['lat'], ep['lon'])
        size = ep.get('size', 44)
        data['endpoints'].append({
            'label': ep['label'], 'icon': icon(ep['icon'], size), 'size': size,
            'x': round(x, 1), 'y': round(y, 1),
            'ax': round(x, 1), 'ay': round(y + 62, 1),
            'side': 'c', 'font': 'place',
        })
    return data


def data_island(geo):
    """The geometry as a JSON block in the page.

    "</" would end the script element early; "\\/" is a legal escape inside a JSON string,
    so the block stays parseable.
    """
    return ('<script type="application/json" id="map-data">%s</script>'
            % json.dumps(geo, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))


MAP_JS = r"""// Interactive map of a collection — generated by build_site.py, do not edit in site/.
//
// The background image carries only what is painted: paper, woodland, rivers, compass and
// cartouche. Everything that means something — the routes, the highlights, the endpoints —
// is drawn here as vectors from the same projection the renderer used. Picking a tour is
// therefore two class names, not a hole cut into a veil, and two tours crossing is not a
// case at all: they are separate elements and always were.
(function () {
  var fig = document.querySelector(".mapfig");
  var island = document.getElementById("map-data");
  if (!fig || !island || !document.createElementNS || !window.DOMParser) return;

  var geo = JSON.parse(island.textContent);
  if (!geo.routes.length || !geo.bg) return;

  var NS = "http://www.w3.org/2000/svg";
  var VW = geo.view[0], VH = geo.view[1];
  var ICON = 1 / geo.sup;          // icons are recorded supersampled, like the renderer draws them
  var PICK = 14;                   // how near a pointer has to come to a line, in CSS pixels

  function el(name, attrs) {
    var e = document.createElementNS(NS, name);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }
  function frag(markup) {
    // the recorded icons arrive as markup; parsing them as a document keeps this
    // independent of innerHTML on SVG elements
    var doc = new DOMParser().parseFromString(
      '<svg xmlns="' + NS + '">' + markup + '</svg>', "image/svg+xml");
    var out = document.createDocumentFragment();
    if (doc.documentElement.nodeName === "parsererror") return out;
    // a snapshot, because importNode copies and would leave the list untouched
    [].slice.call(doc.documentElement.childNodes).forEach(function (k) {
      out.appendChild(document.importNode(k, true));
    });
    return out;
  }
  function d_of(pts) {
    return "M" + pts.map(function (p) { return p[0] + " " + p[1]; }).join("L");
  }

  // ------------------------------------------------------------------ build
  var svg = el("svg", {viewBox: "0 0 " + VW + " " + VH, "class": "map",
                       role: "img", "aria-label": geo.label || "Map of the collection"});
  var defs = el("defs");
  svg.appendChild(defs);

  for (var key in geo.icons) {
    var sym = el("g", {id: "ic-" + key});
    sym.appendChild(frag(geo.icons[key]));
    defs.appendChild(sym);
  }

  // the vector layer keeps out of the cartouche, which is painted over it on the drawn map
  var clipId = null;
  if (geo.guard.length) {
    clipId = "map-guard";
    var holes = "M0 0H" + VW + "V" + VH + "H0Z";
    geo.guard.forEach(function (g) {
      holes += "M" + g[0] + " " + g[1] + "h" + g[2] + "v" + g[3] + "h" + (-g[2]) + "Z";
    });
    var clip = el("clipPath", {id: clipId, clipPathUnits: "userSpaceOnUse"});
    clip.appendChild(el("path", {d: holes, "clip-rule": "evenodd"}));
    defs.appendChild(clip);
  }

  svg.appendChild(el("image", {href: geo.bg, x: 0, y: 0, width: VW, height: VH,
                               preserveAspectRatio: "none"}));
  svg.appendChild(el("rect", {"class": "wash", x: 0, y: 0, width: VW, height: VH}));

  var vec = el("g", {"class": "vec"});
  if (clipId) vec.setAttribute("clip-path", "url(#" + clipId + ")");
  svg.appendChild(vec);

  var gRoutes = el("g", {"class": "routes"});
  var gMarks = el("g", {"class": "marks"});
  var gCursor = el("g", {"class": "cursor"});
  var dot = el("circle", {r: 7});
  gCursor.appendChild(dot);
  gCursor.style.display = "none";
  vec.appendChild(gRoutes); vec.appendChild(gMarks); vec.appendChild(gCursor);

  var routeG = {}, byKey = {};
  geo.routes.forEach(function (r) {
    byKey[r.key] = r;
    var g = el("g", {"class": "route", "data-key": r.key});
    var d = d_of(r.pts);
    g.appendChild(el("path", {"class": "casing", d: d}));
    g.appendChild(el("path", {"class": "dash", d: d}));
    gRoutes.appendChild(g);
    routeG[r.key] = g;
  });

  // Highlights and endpoints sit above the routes, exactly as the renderer stacks them —
  // which is why the line no longer has to be masked out from under icon and plate.
  var marks = [];
  function mark(m, kind) {
    var g = el("g", {"class": "mark " + kind});
    if (m.route) g.setAttribute("data-route", m.route);
    var use = el("use", {"class": "sym"});
    use.setAttribute("href", "#ic-" + m.icon);
    use.setAttribute("transform", "translate(" + m.x + "," + m.y + ") scale(" + ICON + ")");
    g.appendChild(use);

    var lab = el("g", {"class": "lab"});
    var plate = el("rect", {"class": "plate", rx: 2});
    var text = el("text", {x: 0, y: 0});
    text.setAttribute("text-anchor", m.side === "c" ? "middle" : (m.side === "r" ? "start" : "end"));
    text.textContent = m.label;
    lab.appendChild(plate); lab.appendChild(text);
    g.appendChild(lab);
    gMarks.appendChild(g);
    marks.push({data: m, g: g, use: use, lab: lab, plate: plate, text: text,
                pad: kind === "place" ? 14 : 9});
  }
  geo.highlights.forEach(function (h) { mark(h, "spot"); });
  geo.endpoints.forEach(function (e) { mark(e, "place"); });

  var grab = el("rect", {"class": "grab", x: 0, y: 0, width: VW, height: VH});
  svg.appendChild(grab);

  fig.insertBefore(svg, fig.firstChild);
  fig.setAttribute("tabindex", "0");

  // ------------------------------------------------------------ zoom and pan
  // The view is the viewBox: one coordinate system for image and vectors, so nothing can
  // drift apart. Routes scale with the map — a line width is map content — while icons and
  // plates scale against it and keep their size on screen. Otherwise the labels would be
  // the only thing left at four times in, which is when you wanted to read what is under
  // them.
  var MAXK = 4;
  var view = {x: 0, y: 0, w: VW, h: VH};

  function place() {
    var k = VW / view.w;
    dot.setAttribute("r", (7 / k).toFixed(2));
    marks.forEach(function (m) {
      m.use.setAttribute("transform",
        "translate(" + m.data.x + "," + m.data.y + ") scale(" + (ICON / k).toFixed(4) + ")");
      m.lab.setAttribute("transform",
        "translate(" + m.data.ax + "," + m.data.ay + ") scale(" + (1 / k).toFixed(4) + ")");
    });
  }
  function apply() {
    svg.setAttribute("viewBox", [view.x.toFixed(2), view.y.toFixed(2),
                                 view.w.toFixed(2), view.h.toFixed(2)].join(" "));
    fig.classList.toggle("zoomed", view.w < VW - 0.5);
    place();
  }
  function setZoom(k, ux, uy) {
    k = Math.max(1, Math.min(MAXK, k));
    var w = VW / k, h = VH / k;
    // keep the point under the pointer where it is
    view.x = ux - (ux - view.x) * (w / view.w);
    view.y = uy - (uy - view.y) * (h / view.h);
    view.w = w; view.h = h;
    clamp();
    apply();
  }
  function clamp() {
    view.x = Math.max(0, Math.min(VW - view.w, view.x));
    view.y = Math.max(0, Math.min(VH - view.h, view.y));
  }
  function panBy(dx, dy) { view.x += dx; view.y += dy; clamp(); apply(); }

  var zoomBar = document.createElement("div");
  zoomBar.className = "zoom";
  [["+", "Zoom in", function () { setZoom(VW / view.w * 1.6, view.x + view.w / 2, view.y + view.h / 2); }],
   ["−", "Zoom out", function () { setZoom(VW / view.w / 1.6, view.x + view.w / 2, view.y + view.h / 2); }],
   ["⤡", "Whole map", function () { setZoom(1, VW / 2, VH / 2); }]
  ].forEach(function (b) {
    var el2 = document.createElement("button");
    el2.type = "button"; el2.textContent = b[0]; el2.title = b[1];
    el2.setAttribute("aria-label", b[1]);
    el2.addEventListener("click", b[2]);
    zoomBar.appendChild(el2);
  });
  fig.appendChild(zoomBar);

  // The plate is measured, not calculated: the browser knows how wide its own text is, and
  // the drawn map no longer carries a label this has to agree with. Twice, because before
  // the web font has loaded the fallback gives a narrower box.
  //
  // Everything is laid out around the anchor at the origin, so that scale() can be hung in
  // front of it later without the offsets riding along.
  function layout() {
    marks.forEach(function (m) {
      var bb;
      m.text.setAttribute("y", 0);
      try { bb = m.text.getBBox(); } catch (e) { return; }
      m.text.setAttribute("y", (-bb.y).toFixed(1));    // the renderer puts the top of the
      m.plate.setAttribute("x", (bb.x - m.pad).toFixed(1));   // text at the anchor
      m.plate.setAttribute("y", -5);
      m.plate.setAttribute("width", (bb.width + 2 * m.pad).toFixed(1));
      m.plate.setAttribute("height", (bb.height + 12).toFixed(1));
    });
    place();
  }

  // ------------------------------------------------------------------ state
  var st = {picked: null, hovered: null};
  var caption = document.querySelector(".caption");
  var buttons = [].slice.call(document.querySelectorAll(".tours button[data-key]"));
  var rows = [].slice.call(document.querySelectorAll("tr[data-route]"));
  var intro = caption ? caption.textContent : "";

  function draw() {
    var key = st.hovered || st.picked;
    svg.classList.toggle("focus", !!key);
    geo.routes.forEach(function (r) {
      routeG[r.key].classList.toggle("on", r.key === key);
    });
    marks.forEach(function (m) {
      m.g.classList.toggle("on", !m.data.route || m.data.route === key);
    });
    if (key) gRoutes.appendChild(routeG[key]);      // the picked line belongs on top
    buttons.forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-key") === st.picked ? "true" : "false");
    });
    rows.forEach(function (tr) {
      var r = tr.getAttribute("data-route");
      tr.classList.toggle("dim", !!key && !!r && r !== key);
    });
    if (caption) {
      var r = key && byKey[key];
      var n = r ? count(key) : 0;
      caption.textContent = r
        ? (r.label + " — " + comma(r.km, 1) + " km, "
           + (n === 0 ? "no highlights" : n === 1 ? "one highlight" : n + " highlights"))
        : intro;
    }
    drawProfile();
    drawCursor();
  }
  function count(key) {
    return geo.highlights.filter(function (h) { return h.route === key; }).length;
  }
  function pick(key) {
    st.picked = key && byKey[key] ? key : null;
    if (history.replaceState)
      history.replaceState(null, "",
        st.picked ? "#tour-" + st.picked : location.pathname + location.search);
    draw();
  }
  function peek(key) { st.hovered = key && byKey[key] ? key : null; draw(); }
  function comma(v, digits) { return v.toFixed(digits).replace(".", ","); }

  // --------------------------------------------------------- elevation profile
  // One profile, re-pathed on every change instead of one hidden copy per tour: only ever
  // one is shown, and "hovered or picked" is the same expression the map runs on.
  var PW = 1000, PH = 170, PL = 46, PR = 12, PT = 12, PB = 26;
  var pbox = null, psvg, pArea, pLine, pBase, pRule, pHi, pLo, pNote, pRead, pcur = null;

  if (geo.routes.some(function (r) { return r.ele && r.ele.length; })) {
    pbox = document.createElement("figure");
    pbox.className = "profile";
    psvg = el("svg", {viewBox: "0 0 " + PW + " " + PH, role: "img",
                      "aria-label": "Elevation profile of the picked tour"});
    pArea = el("path", {"class": "area"});
    pLine = el("path", {"class": "line"});
    pBase = el("line", {"class": "base", x1: PL, x2: PW - PR});
    pRule = el("line", {"class": "rule", y1: PT, y2: PH - PB});
    pHi = el("text", {"class": "tick", x: PL - 8, y: PT + 9, "text-anchor": "end"});
    pLo = el("text", {"class": "tick", x: PL - 8, y: PH - PB, "text-anchor": "end"});
    [pArea, pLine, pBase, pRule, pHi, pLo].forEach(function (n) { psvg.appendChild(n); });
    pNote = document.createElement("figcaption");
    pRead = document.createElement("span");
    pRead.className = "read";
    pNote.appendChild(document.createElement("span"));
    pNote.appendChild(pRead);
    pbox.appendChild(psvg); pbox.appendChild(pNote);
    // below the caption, which already carries the name and the distance
    var after = caption || fig;
    after.parentNode.insertBefore(pbox, after.nextSibling);

    psvg.addEventListener("pointermove", function (ev) {
      var b = psvg.getBoundingClientRect();
      if (!b.width || !pcur) return;
      var f = ((ev.clientX - b.left) / b.width * PW - PL) / (PW - PL - PR);
      st.cursor = Math.max(0, Math.min(1, f)) * 1000;
      drawCursor();
    });
    psvg.addEventListener("pointerleave", function () { st.cursor = null; drawCursor(); });
  }

  function drawProfile() {
    if (!pbox) return;
    var key = st.hovered || st.picked, r = key && byKey[key];
    pcur = (r && r.ele && r.ele.length) ? r : null;
    pbox.hidden = !pcur;
    if (!pcur) { st.cursor = null; return; }
    var n = r.ele.length, span = Math.max(1, r.hi - r.lo);
    var iw = PW - PL - PR, ih = PH - PT - PB, base = PT + ih;
    pcur.X = function (i) { return PL + i / (n - 1) * iw; };
    pcur.Y = function (v) { return PT + (1 - (v - r.lo) / span) * ih; };
    var d = "";
    for (var i = 0; i < n; i++)
      d += (i ? "L" : "M") + pcur.X(i).toFixed(1) + " " + pcur.Y(r.ele[i]).toFixed(1);
    pLine.setAttribute("d", d);
    pArea.setAttribute("d", d + "L" + pcur.X(n - 1).toFixed(1) + " " + base
                             + "L" + PL + " " + base + "Z");
    pBase.setAttribute("y1", base); pBase.setAttribute("y2", base);
    pHi.textContent = r.hi + " m"; pLo.textContent = r.lo + " m";
    pNote.firstChild.textContent =
      r.lo + "–" + r.hi + " m · " + r.ascent + " m of ascent, from the GPX track";
  }

  // Where along the tour a per mille mark lands on the map — the third number of every
  // point is exactly what makes this a lookup rather than a second measurement.
  function along(r, t) {
    var p = r.pts, lo = 0, hi = p.length - 1;
    while (lo < hi - 1) {
      var mid = (lo + hi) >> 1;
      if (p[mid][2] <= t) lo = mid; else hi = mid;
    }
    var span = p[hi][2] - p[lo][2];
    var f = span > 0 ? (t - p[lo][2]) / span : 0;
    return [p[lo][0] + (p[hi][0] - p[lo][0]) * f, p[lo][1] + (p[hi][1] - p[lo][1]) * f];
  }

  function drawCursor() {
    var show = pcur && st.cursor !== null && st.cursor !== undefined;
    gCursor.style.display = show ? "" : "none";
    if (pRule) pRule.style.display = show ? "" : "none";
    if (pRead) pRead.textContent = "";
    if (!show) return;
    var n = pcur.ele.length;
    var i = Math.max(0, Math.min(n - 1, Math.round(st.cursor / 1000 * (n - 1))));
    var x = pcur.X(i);
    pRule.setAttribute("x1", x.toFixed(1)); pRule.setAttribute("x2", x.toFixed(1));
    var p = along(pcur, st.cursor);
    dot.setAttribute("cx", p[0].toFixed(1)); dot.setAttribute("cy", p[1].toFixed(1));
    pRead.textContent = " · km " + comma(pcur.km * st.cursor / 1000, 1)
                      + " · " + pcur.ele[i] + " m";
  }

  // -------------------------------------------------------------- hit testing
  // One computation over the real lines instead of stacked click paths: where two tours
  // overlap, both are reachable and the nearer one wins — not whichever was drawn last.
  function segDist(px, py, ax, ay, bx, by) {
    var dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
    var t = l2 ? ((px - ax) * dx + (py - ay) * dy) / l2 : 0;
    t = t < 0 ? 0 : (t > 1 ? 1 : t);
    var qx = ax + t * dx - px, qy = ay + t * dy - py;
    return {d: Math.sqrt(qx * qx + qy * qy), t: t};
  }
  function nearest(px, py, tol) {
    var best = null;
    geo.routes.forEach(function (r) {
      var pts = r.pts, bd = Infinity, bt = 0;
      for (var i = 1; i < pts.length; i++) {
        var s = segDist(px, py, pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1]);
        if (s.d < bd) {
          bd = s.d;
          bt = pts[i - 1][2] + (pts[i][2] - pts[i - 1][2]) * s.t;
        }
      }
      // a near tie goes to the tour already picked, so a shared stretch does not flicker
      if (!best || bd < best.d - 0.5 || (Math.abs(bd - best.d) <= 0.5 && r.key === st.picked))
        best = {key: r.key, d: bd, t: bt};
    });
    return best && best.d <= tol ? best : null;
  }
  function atPointer(ev) {
    var b = svg.getBoundingClientRect();
    if (!b.width || !b.height) return null;
    return {x: view.x + (ev.clientX - b.left) / b.width * view.w,
            y: view.y + (ev.clientY - b.top) / b.height * view.h,
            tol: PICK * view.w / b.width,
            sx: view.w / b.width, sy: view.h / b.height};
  }

  // ------------------------------------------------------------------ input
  // The bare wheel scrolls the page: a figure this wide that swallows it is unpleasant on
  // a laptop and impossible on a phone. Zooming is ctrl/⌘ plus wheel, pinch, double click
  // or the buttons.
  var pointers = {}, drag = null, moved = 0;

  function pointerList() {
    var out = []; for (var id in pointers) out.push(pointers[id]); return out;
  }
  svg.addEventListener("pointerdown", function (ev) {
    pointers[ev.pointerId] = {x: ev.clientX, y: ev.clientY};
    if (svg.setPointerCapture) svg.setPointerCapture(ev.pointerId);
    var list = pointerList();
    moved = 0;
    drag = list.length === 1
      ? {mode: "pan", x: ev.clientX, y: ev.clientY}
      : {mode: "pinch",
         d: Math.hypot(list[0].x - list[1].x, list[0].y - list[1].y),
         k: VW / view.w};
    cursor();
  });
  svg.addEventListener("pointermove", function (ev) {
    var p = atPointer(ev);
    if (!p) return;
    if (pointers[ev.pointerId]) {
      pointers[ev.pointerId] = {x: ev.clientX, y: ev.clientY};
      var list = pointerList();
      if (drag && drag.mode === "pinch" && list.length >= 2) {
        var d = Math.hypot(list[0].x - list[1].x, list[0].y - list[1].y);
        if (drag.d > 0) {
          var b = svg.getBoundingClientRect();
          var mx = view.x + ((list[0].x + list[1].x) / 2 - b.left) / b.width * view.w;
          var my = view.y + ((list[0].y + list[1].y) / 2 - b.top) / b.height * view.h;
          setZoom(drag.k * d / drag.d, mx, my);
        }
        moved = 99;
        return;
      }
      if (drag && drag.mode === "pan") {
        var dx = ev.clientX - drag.x, dy = ev.clientY - drag.y;
        moved += Math.abs(dx) + Math.abs(dy);
        drag.x = ev.clientX; drag.y = ev.clientY;
        if (view.w < VW) { panBy(-dx * p.sx, -dy * p.sy); return; }
      }
    }
    var hit = nearest(p.x, p.y, p.tol);
    peek(hit ? hit.key : null);
    cursor(!!hit);
    // running along the line moves the cursor in the profile, and the other way round
    st.cursor = (hit && pcur && hit.key === pcur.key) ? hit.t : null;
    drawCursor();
  });
  function release(ev) {
    delete pointers[ev.pointerId];
    if (!pointerList().length) drag = null;
    cursor();
  }
  svg.addEventListener("pointerup", release);
  svg.addEventListener("pointercancel", release);
  svg.addEventListener("pointerleave", function (ev) { release(ev); peek(null); });

  function cursor(over) {
    svg.style.cursor = drag && drag.mode === "pan" && view.w < VW ? "grabbing"
      : (over ? "pointer" : (view.w < VW ? "grab" : ""));
  }

  svg.addEventListener("click", function (ev) {
    if (moved > 6) return;                       // that was a drag, not a pick
    var p = atPointer(ev);
    var hit = p && nearest(p.x, p.y, p.tol);
    pick(hit && hit.key !== st.picked ? hit.key : null);
  });
  svg.addEventListener("dblclick", function (ev) {
    var p = atPointer(ev);
    if (p) setZoom(VW / view.w * (ev.shiftKey ? 1 / 2 : 2), p.x, p.y);
  });
  svg.addEventListener("wheel", function (ev) {
    if (!ev.ctrlKey && !ev.metaKey) return;      // let the page scroll
    ev.preventDefault();
    var p = atPointer(ev);
    if (p) setZoom(VW / view.w * Math.pow(0.9985, ev.deltaY), p.x, p.y);
  }, {passive: false});

  fig.addEventListener("keydown", function (ev) {
    var step = view.w / 8, k = VW / view.w;
    var keys = {ArrowLeft: [-step, 0], ArrowRight: [step, 0],
                ArrowUp: [0, -step], ArrowDown: [0, step]};
    if (keys[ev.key]) { panBy(keys[ev.key][0], keys[ev.key][1]); ev.preventDefault(); }
    else if (ev.key === "+" || ev.key === "=") setZoom(k * 1.6, view.x + view.w / 2, view.y + view.h / 2);
    else if (ev.key === "-") setZoom(k / 1.6, view.x + view.w / 2, view.y + view.h / 2);
    else if (ev.key === "0") setZoom(1, VW / 2, VH / 2);
  });

  buttons.forEach(function (b) {
    var key = b.getAttribute("data-key");
    b.addEventListener("click", function () { pick(key === st.picked ? null : key); });
    b.addEventListener("mouseenter", function () { peek(key); });
    b.addEventListener("mouseleave", function () { peek(null); });
    b.addEventListener("focus", function () { peek(key); });
    b.addEventListener("blur", function () { peek(null); });
  });

  addEventListener("keydown", function (e) { if (e.key === "Escape") pick(null); });

  layout();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(layout);
  apply();

  var hash = (location.hash || "").replace(/^#tour-/, "");
  pick(byKey[hash] ? hash : null);
})();
"""



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

  // ignoreSearch, because the client module is asked for with a version in the query while
  // the precache holds it under its plain name — the query is there to keep a fresh page
  // from meeting a stale module, not to name a different file.
  e.respondWith(caches.match(e.request, {ignoreSearch: true})
    .then((hit) => hit || fetch(e.request)));
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


def page(path, title, body, nav, repo, built, base, script='', styles='', credit=''):
    """Write one page. `script` is raw markup — the caller decides what it needs."""
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(PAGE.format(title=html.escape(title), css=CSS, nav=nav, body=body,
                             script=script, styles=styles, credit=credit,
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


FONT_DIR = 'fonts'
FONT_FACES = {'label': ('map-label', 'italic'), 'place': ('map-place', 'normal')}


def licence_beside(path):
    """The licence file belonging to a font, or None — no licence, no handing on."""
    folder = os.path.dirname(path)
    family = os.path.splitext(os.path.basename(path))[0].split('-')[0]
    for cand in ('%s-OFL.txt' % family, '%s-LICENSE.txt' % family, 'OFL.txt', 'LICENSE.txt'):
        p = os.path.join(folder, cand)
        if os.path.exists(p):
            return p
    return None


def ship_fonts(site_dir):
    """Copy the label fonts next to the site — but only those that may travel.

    The vector labels are set in the same face the PNG was drawn with, which is only
    possible if that file may be passed on. Lora and Poppins come with their Open Font
    License, so they go; whatever a Windows or Linux machine happens to provide instead
    does not, so it stays where it is and the CSS falls back to what the reader has. Both
    halves therefore always agree: in CI both are Lora and Poppins, on a machine without
    them both are the system serif and sans.
    """
    shipped = []
    for kind in sorted(LABEL_FONTS):
        path = font_file(LABEL_FONTS[kind][0])
        lic = licence_beside(path) if path else None
        if not path or not lic:
            continue
        os.makedirs(os.path.join(site_dir, FONT_DIR), exist_ok=True)
        for src in (path, lic):
            shutil.copyfile(src, os.path.join(site_dir, FONT_DIR, os.path.basename(src)))
        shipped.append((kind, os.path.basename(path), os.path.basename(lic)))
    return shipped


def font_css(shipped, base):
    """@font-face rules for the shipped fonts, relative to the page that uses them."""
    return ''.join(
        '@font-face{font-family:"%s";font-style:%s;font-display:swap;'
        'src:url("%s%s/%s") format("truetype")}'
        % (FONT_FACES[kind][0], FONT_FACES[kind][1], base, FONT_DIR, fname)
        for kind, fname, _ in shipped)


def font_credit(shipped, base):
    """Where the fonts come from — the licence travels with them, so name it."""
    if not shipped:
        return ''
    return (' Set in Lora and Poppins, under the <a href="%s%s/%s">SIL Open Font License</a>.'
            % (base, FONT_DIR, shipped[0][2]))


def write_map_js(site_dir):
    """Write the client module and return a short hash of it.

    Pages come from the network first but assets from the cache, so without the hash in
    the URL a fresh page could meet a stale module for one visit.
    """
    with open(os.path.join(site_dir, MAP_JS_NAME), 'w', encoding='utf-8') as fh:
        fh.write(MAP_JS)
    return hashlib.sha256(MAP_JS.encode('utf-8')).hexdigest()[:8]


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
    shipped = ship_fonts(site_dir)
    map_v = write_map_js(site_dir)

    # write out cover images, backgrounds and icons
    covers, grounds = {}, {}
    for slug, cfg, png, bg in items:
        covers[slug] = 'covers/' + os.path.basename(png)
        shutil.copyfile(png, os.path.join(site_dir, covers[slug]))
        if bg:
            grounds[slug] = 'covers/' + os.path.basename(bg)
            shutil.copyfile(bg, os.path.join(site_dir, grounds[slug]))
    names, boxes = [], {}
    for name, fn in icon_list():
        boxes[name] = stamp(fn, os.path.join(site_dir, 'icons', name + '.png'))
        names.append(name)

    subs = [(cfg['name'], 'collections/%s.html' % slug) for slug, cfg, _, _ in items]
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
             for slug, cfg, _, _ in items]
    body = ("<h1>Maps for komoot collections</h1>\n"
            "<p class=\"lead\">Drawn from the GPX exports of the tours — tinted paper, "
            "dashed paths, stamped woodland. Every map is 1600×1200 pixels and is rebuilt "
            "on each push to <code>main</code>.</p>\n"
            "<div class=\"grid\">\n%s\n</div>" % '\n'.join(cards))
    page(os.path.join(site_dir, 'index.html'), "Maps for komoot collections", body,
         nav_html(nav_items, 'home', ''), repo, built, '',
         styles=font_css(shipped, ''), credit=font_credit(shipped, ''))

    # ------------------------------------------------------- collections
    nav_c = nav_html(nav_items, 'collections', '../')
    sub_styles, sub_credit = font_css(shipped, '../'), font_credit(shipped, '../')
    cards = [card(cfg['name'], ' '.join(cfg['subtitle']), meta_of(cfg),
                  '../' + covers[slug], '%s.html' % slug)
             for slug, cfg, _, _ in items]
    body = ("<h1>Collections</h1>\n"
            "<p class=\"lead\">One folder below <code>gpx/</code> per collection — its own "
            "map frame, its own highlights, its own cover image.</p>\n"
            "<div class=\"grid\">\n%s\n</div>" % '\n'.join(cards))
    page(os.path.join(site_dir, 'collections', 'index.html'), "Collections", body,
         nav_c, repo, built, '../', styles=sub_styles, credit=sub_credit)

    for slug, cfg, png, bg in items:
        geo = geometry(cfg, '../' + grounds[slug] if slug in grounds else None)
        rows = []
        for h in cfg['highlights'] + cfg['endpoints']:
            icon = h.get('icon')
            img = ('<img src="../icons/%s.png" alt="">' % html.escape(icon)
                   if icon in names else '')
            where = ("%s at km %s" % (h['route'], h['km'])) if 'km' in h else "fixed coordinate"
            rows.append('<tr data-route="%s"><td>%s</td><td>%s</td><td>%s</td></tr>'
                        % (html.escape(str(h.get('route', ''))), img,
                           html.escape(str(h.get('label', ''))), html.escape(where)))
        table = ("<h2>Highlights and endpoints</h2>\n<table><tr><th></th><th>Label</th>"
                 "<th>Location</th></tr>\n%s</table>" % '\n'.join(rows)) if rows else ""

        # the tours as buttons — the same pick as clicking the line on the map
        tours = ("<h2>Tours</h2>\n<ul class=\"tours\">\n%s\n</ul>" % '\n'.join(
            '  <li><button type="button" data-key="%s" aria-pressed="false">'
            '<span class="no">%d</span><span>%s</span>'
            '<span class="km">%s km</span></button></li>'
            % (html.escape(r['key']), i + 1, html.escape(r['label']),
               html.escape(('%.1f' % r['km']).replace('.', ',')))
            for i, r in enumerate(geo['routes'])))

        lead = ('<p class="lead">%s</p>\n' % html.escape(' '.join(cfg['subtitle']))
                if cfg['subtitle'] else '')
        # With the background the map is built as vectors and the full cover image is only
        # the fallback; without it the page is what it always was, an image and a link.
        alt = 'Cover image of the collection %s' % html.escape(cfg['name'])
        cover_img = '<img src="../%s" alt="%s">' % (covers[slug], alt)
        if geo['bg']:
            figure = '<figure class="mapfig"><noscript>%s</noscript></figure>' % cover_img
            script = (data_island(geo)
                      + '<script src="../%s?v=%s" defer></script>' % (MAP_JS_NAME, map_v))
        else:
            figure = '<figure class="mapfig">%s</figure>' % cover_img
            script = ''
        body = ('<h1>%s</h1>\n%s%s\n<p class="caption" aria-live="polite">%s</p>\n'
                '<p class="actions"><a href="../%s" download>Download cover image (PNG)</a>'
                '<span class="meta">%s</span></p>\n%s%s'
                % (html.escape(cfg['name']), lead, figure,
                   "Pick a tour to follow it on its own — click it again to bring the whole "
                   "collection back.",
                   covers[slug], html.escape(meta_of(cfg)), tours, table))
        page(os.path.join(site_dir, 'collections', slug + '.html'), cfg['name'], body,
             nav_c, repo, built, '../', script=script,
             styles=sub_styles, credit=sub_credit)

    # ------------------------------------------------------------- icons
    fns = dict(icon_list())
    tiles = ['  <figure class="icon"><div class="pair">'
             '<span><img src="%s.png" alt="Icon %s" loading="lazy"><em>PIL</em></span>'
             '<span>%s<em>SVG</em></span></div>'
             '<figcaption><code>%s</code></figcaption></figure>'
             % (n, n, icon_svg(n, fns[n], boxes[n]), n) for n in names]
    body = ("<h1>Icons</h1>\n"
            "<p class=\"lead\">The icons from <code>icons.py</code>, each drawn with PIL "
            "primitives. The function name is also the value of <code>\"icon\"</code> in the "
            "<code>collection.json</code>. Every icon is shown twice: stamped as a pixel image "
            "for the cover map, and recorded as SVG for the interactive map. Both come from the "
            "same function — where the two differ, the recorder in <code>svgdraw.py</code> is "
            "wrong.</p>\n"
            "<div class=\"icons\">\n%s\n</div>" % '\n'.join(tiles))
    page(os.path.join(site_dir, 'icons', 'index.html'), "Icons", body,
         nav_html(nav_items, 'icons', '../'), repo, built, '../',
         styles=sub_styles, credit=sub_credit)

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
