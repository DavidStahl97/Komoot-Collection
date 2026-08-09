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
`python3 map_cover.py` either runs through and writes one PNG per collection into `out/`,
or it aborts. A change counts as checked only once the resulting image has been looked at —
especially anything touching positions, since there is no collision detection for labels.
If you only work on one collection, append its folder name
(`python3 map_cover.py brandy-haiger`); if you change the shared layout, check all of them,
because every collection has a different map frame.

The same goes for the site: `python3 build_site.py` runs after `map_cover.py` and writes
`site/`. A change is checked only once `site/index.html` has been looked at in a browser —
home, a collection subpage and the icon list. On the subpage that also means picking a
tour: the overlay lies on top of the image without any alignment of its own, so a shifted
frame or a moved label shows up as lines next to the drawn ones or as half-veiled text. The workflow `.github/workflows/maps.yml`
does both in CI: in a pull request as the artifact `collection-icons`, on `main` as a
GitHub Page.

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
`cum`, `seg`, `at`, `discover`, `read_config`); below, `render(cfg, out_path)` draws one
collection onto a PIL canvas. Inside `render`, the order in the file is the drawing order
(paper grain → woodland → rivers → routes → highlights → endpoints → compass → cartouche).
Moving something changes what covers what.

`main()` uses `discover()` to find every subfolder of `gpx/` containing GPX files and calls
`read_config` and `render` for each. Every collection is entirely self-contained: its own
frame, its own highlights, its own output file. Only the constants at the top of the file
(`S`, `W`/`H`, colors, `BOX`) and the icons in `icons.py` are shared.

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

The interactive layer of a collection page is generated the same way: `geometry(cfg)`
projects routes, highlights and endpoints into the coordinates of the finished image and
`MAP_JS` builds an SVG over the PNG from that JSON. Dimming is one veil rectangle with a
mask — the picked route, its highlights and the endpoints are holes in it, so what stays
visible is the drawn map, never a redrawn copy. The order inside the mask carries meaning:
first the corridor of each route is cut open, then the highlights of the *other* tours are
painted back white (`marks` with a padding), and only then the endpoints. Without that
second pass a highlight of another tour would ride along in the focus wherever its label
reaches into the corridor. What is meant is the one tour, not its surroundings, and the
two numbers that decide that are the corridor width (40, wide enough for the drawn line,
not for its neighbourhood) and the padding of the holes.

The padding of the covers is *negative*: they hug icon and plate instead of taking the air
around them, and they use their own, crisper blur (`map-edge`). Both follow from the same
constraint — „Der Knoten" sits on the Ulmtalradweg and „Ulmtalradweg" lies across Über
Greifenstein. A generous cover would cut the picked tour in two there, and the picked tour
has to stay unbroken over its whole length. What is lost is nothing: under icon and plate
the route is invisible anyway, because `render` draws them over it. Anything drawn beyond
the mark — the masts of the wind turbines, for instance — stays faintly visible where the
picked route passes; that is the price of the unbroken line. Four things follow.

The label holes come from `label_box`, which mirrors the label drawing in `render`
(offset, `side`, plate padding) and measures the text with the same fonts via `measure()`
— if the labels move in `render`, they have to move here as well, otherwise the veil clips
them. The holes are blurred (`stdDeviation` in `MAP_JS`), so every box keeps a margin
wider than that blur, but only a little wider: with too much, „Lahn bei Löhnberg" pulls
the border of the cartouche out of the veil. The covers over foreign highlights need more,
because they have to reach past the soft edge of the hole underneath them.

The line drawn on top is masked with `map-over`, which punches out every highlight and
every endpoint — on the drawn map the highlights lie above the routes, and the overlay has
to keep to that order instead of running through icon and label. And the highlights of the
picked tour get no ring or marker of their own: what marks them is that they are the only
ones left uncovered, which is why the veil is deep (`.veil.on`) — the emphasis comes from
the contrast, not from anything drawn on top. The image itself stays untouched and
downloadable — it is what komoot shows as the cover.

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
