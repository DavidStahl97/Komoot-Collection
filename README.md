# Maps for komoot collections

**➡️ [Open the site](https://davidstahl97.github.io/Komoot-Collection/)** — all
collections with their maps, the interactive tour picker and the icon list.

Generator for the cover images of my komoot collections. The first one is
[„Brandy <-> Haiger"](https://www.komoot.com/collection/4605392/-brandy-haiger) —
gravel routes between Haiger and Brandoberndorf in the Lahn-Dill-Bergland; more
will follow as their own folders.

From the GPX exports of the tours it draws an illustrated map in the style of an
old hiking map: tinted paper, dashed paths, stamped woodland and small hand-drawn
icons at the highlights. No network needed, no external assets, no image AI —
every line comes from PIL primitives. The result is 1600×1200 pixels, because
komoot renders the preview in a 4:3 aspect ratio and crops left and right at 3:2.

Note on language: code, comments and documentation are English. The *content* of a
collection stays German — the labels in `collection.json` (title, subtitle,
highlights, endpoints) and the GPX file names, since they name real places.

## Getting started

```bash
pip install pillow numpy
python3 map_cover.py                 # every collection under gpx/ into out/
python3 map_cover.py brandy-haiger   # only this one
python3 map_cover.py --out /path/to/cover
```

Run it from the repository root — the paths are relative and can be moved with
`--gpx` and `--out`. If the Google fonts Lora and Poppins are missing under
`/usr/share/fonts/truetype/google-fonts/`, the script falls back to DejaVu and
Liberation, on Windows to Georgia and Calibri: the layout stays, the typeface looks
different.

Each collection produces two files: `<collection>.png`, the cover komoot gets, and
`<collection>-bg.png`, the same sheet without routes, highlights and endpoints. The
site draws those as vectors on top of it, so the background is what stays painted.

Every run produces exactly the same image — all random numbers have fixed seeds.

For the site there is a second half, and it needs Node:

```bash
python3 export_data.py --png out --out web/static
npm ci --prefix web
npm run dev --prefix web        # http://localhost:5173
```

`export_data.py` has to run first — the app is built from what it writes, and the build
stops with a readable error if it has not. `npm run build --prefix web` writes the finished
site to `web/build`, `npm run preview --prefix web` serves that.

## What lives where

Python draws and measures; it does not build the web app. Everything it produces is data
and images, and the app under `web/` is an ordinary single-page app that reads them.

| File | Purpose |
|---|---|
| `map_cover.py` | Finds the collections and builds each map, in layers from top to bottom — twice: the cover image and, without routes and highlights, the background of the interactive map. |
| `icons.py` | The drawn icons: fox, lake, wind-turbine hill, cycle path, river, idyllic path, dill, mine, shark, house in the woods. |
| `svgdraw.py` | Records what `icons.py` draws as SVG instead of pixels, so the app gets the same icons as vectors without a second set of them. |
| `export_data.py` | Exports what the app is built from: the geometry of every collection as JSON, the icons as SVG, the cover images, the app icon and the fonts. No markup, no stylesheet, no script. |
| `web/` | The web app: SvelteKit, Svelte 5 and TypeScript. Hand-written; everything generated lands in `web/static/` and is not checked in. |
| `gpx/<collection>/` | One folder per collection: the GPX exports and optionally a `collection.json`. Nothing runs without them. |
| `out/` | The rendered PNGs: `<collection>.png` is the cover, `<collection>-bg.png` its background. Not checked in. |
| `web/build/` | The finished site, what GitHub Pages publishes. Not checked in. |
| `.github/workflows/maps.yml` | Renders on every push and pull request, attaches the images to the PR and publishes the site. |

Inside `web/src`:

| File | Purpose |
|---|---|
| `routes/` | The four pages: home, collections, one collection, icons. Each fetches its own JSON. |
| `lib/types.ts` | The data contract with `export_data.py`. A field renamed on one side and not the other is the one mistake nothing else would catch. |
| `lib/map/` | The interactive map: `Map.svelte` and `Profile.svelte` over `view` (zoom and pan), `tour` (what is picked), `hit` (which line a click means), `profile` and `geom`. |
| `app.css`, `generated/tokens.css` | The stylesheet, and the four map colors written out of `map_cover.py`. |

## Adding a new collection

1. Create a folder under `gpx/`, e.g. `gpx/westerwald-runden/`.
2. Put the GPX exports from komoot into it.
3. `python3 map_cover.py` — the folder is picked up on its own.

That alone is enough for a finished map: frame, woodland and tree stamps scale
with the shared bounding box of the routes in *this* folder, the title comes from
the folder name (`westerwald-runden` → `WESTERWALD` / `RUNDEN`), and the file is
called `out/westerwald-runden.png`. Collections do not affect each other — each
one gets its own map frame.

Title, highlights, rivers and endpoints go into a `collection.json` in the same
folder. It is optional, and so is every field in it:

```json
{
  "name": "Westerwald-Runden",
  "output": "westerwald-runden.png",
  "title": ["WESTER", "WALD"],
  "arrow": true,
  "subtitle": ["Runden rund um", "die Fuchskaute"],

  "routes": [
    {"key": "FU", "file": "_____Fuchskaute___Ulmtalradweg.gpx",
     "label": "Fuchskaute – Ulmtalradweg"}
  ],
  "rivers":     [{"route": "FU", "from": 20.5, "to": 23.5, "width": 5}],
  "highlights": [{"label": "Fuchskaute", "route": "FU", "km": 17.0,
                  "icon": "fox", "side": "l", "offset": [-6, -56]}],
  "endpoints":  [{"label": "HAIGER", "lat": 50.7402, "lon": 8.2223, "icon": "shark"}]
}
```

The visible strings in there — `name`, `title`, `subtitle`, `label` — are German
on purpose; they are the content of the collection, not part of the code.

| Field | Meaning |
|---|---|
| `name` | Console output only. Default: folder name. |
| `output` | File name in the target folder. Default: `<foldername>.png`. |
| `title` | Lines of the cartouche in capitals. Empty list = no cartouche. |
| `arrow` | Double arrow between two title lines. Default: on when there are exactly two. |
| `subtitle` | Italic lines below the divider. |
| `routes` | Order and keys of the GPX files, optionally a `label` — the tour name on the site. GPX files not listed are still drawn. |
| `rivers` | River sections, derived from `route` plus the kilometre range `from`/`to`. |
| `highlights` | Icon with a label, see below. |
| `endpoints` | Start and finish with a fixed coordinate, icon and bar label. |

The `label` of a tour only ever shows up on the site, never on the map. Without it
the file name of the komoot export has to serve, and that one has lost its umlauts —
`______ber_den_Knoten.gpx` becomes `ber den Knoten`. One line per tour is enough to
avoid that.

The cartouche grows with the number of lines and the width of the text while
staying anchored in the bottom left — longer titles do not break it.

## The tours

Currently included, in `gpx/brandy-haiger/`:

| File | Tour | Distance | Elevation |
|---|---|---|---|
| `______ber_Greifenstein.gpx` | Über Greifenstein | 69.7 km | 1,150 m |
| `_____Fuchskaute___Ulmtalradweg.gpx` | Fuchskaute – Ulmtalradweg | 73.5 km | 750 m |
| `_____Dilltalradweg.gpx` | Dilltalradweg | 56.6 km | 470 m |
| `______ber_den_Knoten.gpx` | Über den Knoten | 80.1 km | 1,090 m |

The cryptic file names come from the komoot export, which turns umlauts into
underscores. Renaming them works, but then the `file` entries in the
`collection.json` have to follow.

The GPX files contain the start and end point of the tours to the metre — in a
public repository that is a readable home address. Here this is a deliberate
decision; anyone rebuilding this project for their own tours should answer the
question for themselves.

## Adding a tour

Export the GPX and drop it into the collection's folder. If there is no `routes`
list, that is all there is to it; otherwise add an entry `{"key": "…", "file":
"…"}` so it can be referenced from highlights and rivers. Map frame, woodland and
tree stamps scale automatically with the shared bounding box of all routes in the
collection.

## Adding a highlight

Do not guess coordinates. The komoot tour page gives a kilometre mark for every
highlight, and `route` plus `km` walks the GPX up to that point and returns the
real position. Only where there is no kilometre mark — town centres, for example —
do `lat`/`lon` go straight into the configuration:

```json
{"label": "Name", "route": "FU", "km": 17.0, "icon": "fox", "side": "l", "offset": [-6, -56], "size": 34}
```

`offset` moves the label only, `"l"` makes it end flush right at the point, `"r"`
puts it to the right of the point, `"c"` centres it. There is no collision
detection — look at the image and adjust.

A new icon becomes a function in `icons.py` following the pattern `fn(d, x, y, s)`,
where `s` is the radius scale; its name is the value of `"icon"`. `poly`, `circ`
and `tree` are available as building blocks.

## GitHub Actions and the site

`.github/workflows/maps.yml` runs on every push to `main` and on every pull
request. Both times the maps are rendered and the site is built:

- **In a pull request** the images are attached to the run as the artifact
  `collection-icons` — the cover images from `out/` and every single icon from
  `icons.py`. Since there are no tests, downloading and looking at this artifact
  *is* the check.
- **On `main`** the site is additionally published via GitHub Pages. For that,
  *GitHub Actions* has to be selected as the source under *Pages* in the
  repository settings; the workflow needs no further secrets.

The site has three areas: **Home** lists all collections with their cover image,
**Collections** leads to one subpage per collection (large image, tours,
highlights with their icon), **Icons** shows every icon from `icons.py` with its
function name — that is, with the value that belongs in `collection.json` as
`"icon"`. Locally:

```bash
python3 map_cover.py --out out && python3 export_data.py --png out --out web/static && npm run build --prefix web
```

New icons and new collections show up on their own: `export_data.py` collects the
collections via `discover()` and the icons via the signature `fn(d, x, y, s)`, and the app
renders whatever is in `data/index.json`. Adding a collection therefore never touches the
app.

Because the pages are routed in the browser, a deep link such as
`/collections/brandy-haiger/` is not a file. GitHub Pages answers it with `404.html`, which
is the same app shell, and the router takes it from there — the page is correct, the status
code is not. That is the standard arrangement for a single-page app on Pages.

### The map as a vector map

On the subpage of a collection the map is not a picture at all. Only what is *painted*
comes as an image — paper grain, woodland, tree stamps, rivers, compass, cartouche. That
is `out/<collection>-bg.png`, the same sheet as the cover but with the routes, highlights
and endpoints left off. Everything that means something is drawn in the browser as SVG:
one path per tour, one group per highlight, one per endpoint.

Which makes picking a tour two class names. Click a line on the map or an entry under
*Tours* and that tour stays in front while everything else steps back — a sheet of paper
over the painted map, and the other lines and highlights fading into it. Nothing is drawn
around the highlights that remain: being the only ones left in front is what marks them.
Clicking again, a click next to it or `Esc` brings the whole collection back; hovering only
shows a preview. The rows under *Highlights and endpoints* fade along with it, and the
picked tour ends up in the address as `#tour-KN`, so a single tour can be linked to.

Tours crossing each other is not a case that has to be handled — they are separate
elements. A highlight of another tour goes back with its tour even when it sits directly on
the picked line, and the picked line runs through unbroken. Which tour a click means is
decided by distance, not by drawing order, so on a stretch where two run side by side both
are reachable and the nearer one wins.

The positions come from the same projection as the renderer (`projection()` in
`map_cover.py`, with the map frame scaled down by the supersampling), which is why the
lines land exactly in the tree-free corridors the background was stamped around them. They
arrive as `data/<collection>.json`, written by `export_data.py` and fetched by the page.
The icons come from `icons.py` through `svgdraw.py`, which records the drawing calls as SVG
instead of pixels — there is no second, hand-written set of icons that could drift. They
travel as `icons/sprite.svg`, one `<g>` per icon and size, which the page inlines once and
then points `<use>` at. The label plates are measured in the browser from the text itself.

**Zoom and pan.** Ctrl/⌘ and the wheel, pinch, double click or the buttons zoom in up to
four times; drag to move, arrow keys with the map focused, `0` back to the whole sheet. The
bare wheel keeps scrolling the page. Routes scale with the map, icons and labels keep their
size on screen. The painted background is a 1600×1200 image and goes soft when magnified —
as does the cartouche, which is part of it.

**The elevation profile** below the map belongs to the picked tour, sampled from the `<ele>`
values of the GPX. Running along it marks the spot on the map, running along the route
marks the spot in the profile.

The cover image stays untouched — *Download cover image (PNG)* gives out exactly the file
from `out/`, with all tours on it, which is what komoot gets.

**Without JavaScript there is no page.** This is what the move to a single-page app gave
up: the collection subpages used to be static HTML and still showed the cover image and a
download link with scripting off. Now they are routed in the browser, so a reader without
JavaScript gets the `<noscript>` notice and a link to `data/index.json`, which names the
file of every cover below `covers/`. The images themselves are still ordinary PNGs and
still open on their own.

### The site as a progressive web app

The page is installable and works offline. The service worker and the manifest are
generated by `vite-plugin-pwa` from the finished build, so the precache list is whatever
was actually written — nothing has to be kept in step by hand:

| File | Purpose |
|---|---|
| `manifest.webmanifest` | Name, colors, icons. All paths relative, because the page lives under `/<repository>/`. The colors are `PAPER` from `map_cover.py`, read out of `src/generated/theme.json`. |
| `sw.js` | Service worker: precaches every file of the build, serves it when offline. |
| `pwa/icon-*.png` | App icon — a compass rose on paper, drawn with the same PIL primitives as the maps. |
| `fonts/` | Lora and Poppins, if they were found *and* their licence sits next to them — so the labels on the site are set in the same face the PNG was drawn with. Otherwise the CSS falls back, exactly as the renderer does. |

Installing works from the browser menu ("Install app" / "Add to Home Screen") once
the page is served over HTTPS — GitHub Pages does that. On the first visit the
service worker caches every page, cover image, icon and data file; after that every subpage
opens without a network, including a deep link to a collection.

The old hand-rolled cache is gone with it: the bundler gives every asset a hash in its
name, so a changed file is a different URL and there is nothing to invalidate. Navigations
are answered from the precached shell, which is why a collection opens offline even though
its URL was never a file.

Testing this locally needs a server — `file://` has no service worker, and `python3 -m
http.server` alone will not do because it cannot answer a deep link with `404.html`:

```bash
npm run preview --prefix web    # then http://localhost:4173/
```

`localhost` counts as a secure origin, so registration works there too. In the
developer tools under *Application* the service worker, the manifest and the
cache content are visible; *Network → Offline* plus a reload is the test.

The GitHub runners do not have Lora and Poppins; the workflow fetches them before
rendering. If that fails, the fallback to DejaVu/Liberation kicks in — the map is
still created, only the typeface looks different.

## Knobs to turn

| Place | Effect |
|---|---|
| `random.Random(23)` | Scatter of the woodland trees. Different number = different distribution. |
| `for _ in range(26)` (at `rnd2`) | Number of soft edge patches. More = fuller corners. |
| `for _ in range(420)` | Pale edge trees. Set too high it looks like wallpaper. |
| `BOX = (...)` | Map frame on the sheet. Applies to all collections. |

## What the map cannot do

- The woodland is a soft hull around the routes, not actual forest areas — there
  is no land-use data in the project.
- The rivers (Lahn, Dill) are derived from route sections and are only correct
  where the route really follows the river.
- Compass (bottom right) and cartouche (bottom left) are placed at fixed
  positions; the cartouche does grow with its text but does not dodge routes
  underneath it.
- The elevation data in komoot GPX files is smoothed; short steep ramps above
  ~15 % do not show up in it. For gradient analysis the recorded ride is more
  meaningful — and even there, speed is the more honest indicator than the
  elevation curve.
- Because of that, the ascent under the profile on the site comes out about a tenth
  below what komoot shows for the same tour (670 against 750 m, 990 against 1,090 m):
  it is summed over the exported track, komoot uses its own elevation model. No
  threshold is applied — every bit of hysteresis widens the gap instead of closing
  it. The table above stays komoot's figure, the site says where its own comes from.
