# Maps for komoot collections

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
Liberation: the layout stays, the typeface looks different.

Every run produces exactly the same image — all random numbers have fixed seeds.

## What lives where

| File | Purpose |
|---|---|
| `map_cover.py` | Finds the collections and builds each map, in layers from top to bottom. |
| `icons.py` | The drawn icons: fox, lake, wind-turbine hill, cycle path, river, idyllic path, dill, mine, shark, house in the woods. |
| `build_site.py` | Builds the GitHub Page from the rendered maps: home, collections, icons. |
| `gpx/<collection>/` | One folder per collection: the GPX exports and optionally a `collection.json`. Nothing runs without them. |
| `out/` | The rendered PNGs. Not checked in. |
| `site/` | The generated site. Not checked in. |
| `.github/workflows/maps.yml` | Renders on every push and pull request, attaches the images to the PR and publishes the site. |

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
    {"key": "FU", "file": "_____Fuchskaute___Ulmtalradweg.gpx"}
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
| `routes` | Order and keys of the GPX files. GPX files not listed are still drawn. |
| `rivers` | River sections, derived from `route` plus the kilometre range `from`/`to`. |
| `highlights` | Icon with a label, see below. |
| `endpoints` | Start and finish with a fixed coordinate, icon and bar label. |

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
python3 map_cover.py --out out
python3 build_site.py --png out --out site
```

New icons and new collections show up on their own: `build_site.py` collects the
collections via `discover()` and the icons via the signature `fn(d, x, y, s)`.

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
