# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@README.md

The README explains purpose, setup and how to deal with collections, tours, highlights and
the knobs to turn — it is pulled in via the import above and is not repeated here. What
follows is only what trips you up while working in the code.

## Language

The repository language is English: code, identifiers, comments, docstrings, CLI help and
error messages, documentation, workflow files and commit messages.

The *content* of a collection stays German, because it names real places and is what
readers of the komoot collection see:

- everything visible in `gpx/<collection>/collection.json` — `name`, `title`, `subtitle`,
  the `label` of highlights and endpoints, and free-text `note` fields,
- the GPX file names from the komoot export and the data inside them.

Everything that describes those values — field names, keys, comments about them — is
English. A German label in a JSON file is correct; a German variable name is not.

## Verification

There are no tests, no linter and no build system. The script *is* the test:
`python3 map_cover.py` either runs through and writes two PNGs per collection into `out/`
(the cover and its background), or it aborts. A change counts as checked only once the
resulting image has been looked at — especially anything touching positions, since there is
no collision detection for labels. If you only work on one collection, append its folder
name (`python3 map_cover.py brandy-haiger`); if you change the shared layout, check all of
them, because every collection has a different map frame.

Two things have a cheap, exact check and should use it instead of an opinion:

- **The cover must not move.** `sha256` of `out/<collection>.png` before and after. Anything
  that leaves it unchanged cannot have touched what komoot gets.
- **The icons must agree.** `site/icons/index.html` shows every icon twice, stamped by PIL
  and recorded by `svgdraw.py`. They come from the same function in `icons.py`; where the
  two tiles differ, the recorder is wrong. `shark` is the only `arc`, `windmount` has the
  thinnest strokes, `bike` the only stroked circle — those three catch most of it.

For the rest of the site: `python3 build_site.py` runs after `map_cover.py` and writes
`site/`. A change is checked only once it has been looked at in a browser — home, a
collection subpage and the icon list. On the subpage that means picking a tour and looking
at the two places where tours meet: „Der Knoten" sits on the Ulmtalradweg and
„Ulmtalradweg" lies across Über Greifenstein. Pick FU and the Ulmtalradweg has to run
unbroken through „Der Knoten" while „Der Knoten" steps back; pick KN and the same the other
way round. The vector lines have no alignment of their own — they come from `projection()`
— so a shifted frame shows up as lines running beside the tree-free corridors the
background was stamped around them. The workflow `.github/workflows/maps.yml` does all of
it in CI: in a pull request as the artifact `collection-icons`, on `main` as a GitHub Page.

Anything touching the progressive web app cannot be checked over `file://` — service
worker and manifest need an origin. `python3 -m http.server -d site 8000` and
`http://127.0.0.1:8000/` are enough; `localhost` counts as secure. Checked means: the
service worker is *activated* under *Application*, and the three page types still open
with *Network → Offline* switched on.

The target directory and the fonts are no longer hard-wired: `out/` is created when
missing, and `F(...)` falls back to DejaVu or Liberation when the Google fonts are absent,
on Windows to Georgia and Calibri. A run on someone else's machine therefore says nothing
about the final typography — font metrics differ, lines can break or overlap differently.
What it does have to say something about is the *size*: if a map comes out with tiny
labels in plates that have shrunk with them, then no font was found at all and
`load_default` is drawing. Then the layout is not being checked, only a caricature of it.

## Architecture

`map_cover.py` has two halves. On top sit the configuration and the GPX helpers (`load`,
`elevation`, `cum`, `seg`, `at`, `discover`, `read_config`); below,
`render(cfg, out_path, overlay=True)` draws one collection onto a PIL canvas. Inside
`render`, the order in the file is the drawing order (paper grain → woodland → rivers →
routes → highlights → endpoints → compass → cartouche). Moving something changes what
covers what.

`overlay=False` leaves routes, highlights and endpoints off and yields the background of
the interactive map. That it comes out identical to the background under the full cover is
not luck: every generator is seeded inside `render` and all four seeds (7, 11, 41, 23) are
spent before the routes are drawn. Put anything random *between* the rivers and the
cartouche and the two images drift apart without a word.

`main()` uses `discover()` to find every subfolder of `gpx/` containing GPX files and calls
`read_config` and `render` for each, twice. Every collection is entirely self-contained: its
own frame, its own highlights, its own output files. Only the constants at the top of the
file (`S`, `W`/`H`, colors, `BOX`) and the icons in `icons.py` are shared.

Load-bearing concepts:

- **Configuration instead of code.** Everything collection-specific lives in
  `gpx/<collection>/collection.json`, not in the script. New tours, highlights or titles
  belong there; `map_cover.py` is only touched when the *map image itself* changes.
  `read_config` fills missing fields from the folder, so every new field needs a
  `setdefault` there — a folder without a `collection.json` has to keep working.
- **References via keys.** Highlights and rivers point at a `key` from `routes` via
  `"route"`; `route_of` resolves it and raises with a readable message when the key does
  not exist. `icon_of` does the same for icon names from `icons.py`. Both are loud on
  purpose — a silently missing highlight would otherwise go unnoticed.
- **Supersampling.** `S=2` scales the entire canvas; at the end it is resampled down to
  1600×1200 via LANCZOS. That is why *every* new pixel size has to be multiplied by `*S` —
  otherwise the element gets the wrong size when `S` changes. Values from the JSON
  (`offset`, `size`) are unscaled and get their `*S` at drawing time.
- **Projection.** `projection(routes, box)` implements Web Mercator and returns `P` (one
  coordinate) and `PA` (a whole track). Scale and centre come from the bounding box of
  *this* collection's routes, framed by `box`. A new tour therefore shifts the layout of
  its own collection and nothing else. It sits outside `render` because `build_site.py`
  needs the same positions for the interactive overlay; called with `BOX` it yields
  supersampled pixels, called with `BOX/S` the pixels of the finished 1600×1200 image.
  Overlay positions are never estimated from the image — they come from here.
- **GPX access via kilometre marks.** `cum` returns the cumulative haversine distance;
  `at(route, km)` (point at km) and `seg(route, k0, k1)` (section) build on it. Coordinates
  always come via `km`, never estimated — the exception are endpoints such as Haiger and
  Brandoberndorf, which sit in the JSON as town centres with `lat`/`lon`.
- **Masks instead of geodata.** The woodland is a blurred greyscale mask of ellipses along
  the routes (`forest`); trees are only stamped where `fmask` is bright enough and `rmask`
  (route) is clear. The rivers are route sections via `seg`.
- **Determinism.** Every `random.Random(...)` has a fixed seed (7, 11, 41, 23) and is reset
  inside `render`, so the order of the collections does not influence the image. Change
  seeds deliberately only; they are the knob for the scatter, not noise.

`build_site.py` hangs off the same configuration: it imports `discover`, `read_config`,
`slugify` and `PAPER` from `map_cover.py` instead of repeating paths or colors. The icon
list of the icon page does not come from an enumeration but from the signature — every
function in `icons.py` whose first four parameters are named `d, x, y, s` is an icon, which
is what drops `poly` and `circ`. Icons are stamped large and then cropped to what was
actually drawn, because they reach past their radius by different amounts.

The map of a collection page is generated the same way. `geometry(cfg, bg)` projects
routes, highlights and endpoints into the coordinates of the finished image and emits them
as a JSON island; `MAP_JS` — written to `site/map.js` — builds an SVG from it over the
background image. The background carries only what is painted; everything semantic is a
vector element on top of it.

That is the whole reason the highlighting works. Picking a tour sets two class names, the
rest is CSS: a `wash` rectangle over the painted map, `.route`/`.mark` at low opacity,
`.on` at full. There is nothing to cut free, so two tours crossing is not a case — they are
separate elements and always were. A highlight of another tour recedes with its tour even
when it sits on the picked line, and the picked line runs through unbroken. Do not
reintroduce a marker around the picked highlights: being the only ones left in front is
what marks them.

Four things carry weight in there:

- **The vector layer is clipped out of the cartouche** (`guard` in the JSON,
  `cartouche_box()` in `map_cover.py`). The cartouche is filled opaquely and sits inside
  the map frame; the renderer draws the routes underneath it, and without the clip the
  browser would draw them over it. Today there are 23 px between it and the nearest route —
  that is not a margin, it is one bad `offset` away.
- **Which tour a click means is decided by distance**, computed in JS over the real lines,
  not by a stack of click paths. Where two tours run side by side both are reachable and
  the nearer wins; a near tie goes to the tour already picked, so a shared stretch does not
  flicker. This is what the old stacked `stroke-width` paths could not do.
- **Labels are measured in the browser** from `getBBox()`, twice — once immediately and
  once in `document.fonts.ready`, because before the web font arrives the fallback gives a
  narrower box. There is no `label_box` mirroring the renderer any more and there must not
  be one again: the background carries no labels, so nothing has to agree with anything.
- **`rdp` returns indices, not points**, and its tolerance is 0.25 px rather than 1. The
  indices are what lets each point carry its position along the tour (per mille), which is
  what ties the map to the elevation profile in both directions. The tolerance is a quarter
  pixel because the map zooms to four times, where a whole pixel of error walks visibly out
  of the tree-free corridor.

Under zoom, routes scale with the map and icons, plates and text scale against it
(`place()`), so they hold their size on screen. The cover image itself stays untouched and
downloadable — it is what komoot shows as the cover, and without JavaScript it is the whole
page.

`svgdraw.py` is what keeps the icons single-sourced. `SvgRecorder` behaves like an
`ImageDraw.Draw` and writes SVG instead of pixels, so `icons.py` stays the only place an
icon is described. Two things in there were measured against PIL rather than assumed, and
both would be silent if wrong: PIL lays the outline of an `ellipse` and the band of an
`arc` *inside* the bounding box, so stroked radii shrink by half the width; and the angles
of `arc` are parametric, not geometric. Icons are recorded at `size * S` — the radius the
renderer passes — because the stroke widths inside `icons.py` are clamped with
`max(2, int(s·k))`, and at any other scale those clamps resolve differently. The `<use>`
carries the matching `scale(1/S)`.

The progressive web app also comes out of `build_site.py` and follows from the same rule:
nothing is maintained by hand. `manifest()` derives its colors from `PAPER`, `app_icon()`
draws the compass rose with the PIL primitives of the maps, and `service_worker()` walks
the finished `site/` and writes exactly what is there into the precache list — which is
why it has to run *last* in `build`, after every page and image exists. A new page that is
written after it would be missing offline. The cache name is a sha256 over path and
content of all files: same content, same name, kept cache; one changed byte, new cache,
old one deleted on activation. All paths in manifest, `<link>` and registration are
relative (`base` from `page()`), because the page is not served from the domain root but
from `/<repository>/`; an absolute `/sw.js` would go nowhere on GitHub Pages.

Two consequences of that for anything new under `site/`. `map.js` is written before
`service_worker()` and asked for as `map.js?v=<hash>`, because pages come from the network
first while assets come from the cache — without the version a fresh page could meet a
stale module for one visit. The service worker therefore looks assets up with
`ignoreSearch`, or the precached `map.js` would never answer the versioned request offline.
And `ship_fonts()` copies a font only when its licence file sits next to it, so the Google
fonts travel with the site and whatever a Windows or Linux machine happens to provide does
not. That is also why the site never disagrees with the PNG: both halves resolve the same
face through `font_file()`.

`icons.py` contains nothing but the icons. Each follows the signature `fn(d, x, y, s)` with
`s` as the radius scale — the caller already passes `*S`, so do not scale again inside the
icon function. Icons draw relative to `x,y` and return nothing. Building blocks: `poly`,
`circ`, `tree`. The function name is the public interface: it appears as `"icon"` in the
JSON files, renaming it breaks them.

## Data

The GPX files in `gpx/<collection>/` are tracked and stay that way — without them the
script does not run. They contain start and end point to the metre, i.e. a home address;
that is a deliberate decision and not an open question. The `.gitignore` covers output
PNGs, `out/`, `__pycache__`, `*.pyc` and `.venv/`; `collection.json`, by contrast, belongs
in the repository.
