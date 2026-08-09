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
home, a collection subpage and the icon list. The workflow `.github/workflows/maps.yml`
does both in CI: in a pull request as the artifact `collection-icons`, on `main` as a
GitHub Page.

The target directory and the fonts are no longer hard-wired: `out/` is created when
missing, and `F(...)` falls back to DejaVu or Liberation when the Google fonts are absent.
A run on someone else's machine therefore says nothing about the final typography — font
metrics differ, lines can break or overlap differently.

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
- **Projection.** `merc`/`P`/`PA` implement Web Mercator. They live inside `render` because
  scale and center come from the bounding box of *this* collection's routes, framed by
  `BOX`. A new tour therefore shifts the layout of its own collection and nothing else.
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
