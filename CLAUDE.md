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

The Python half has no tests and no linter. The script *is* the test: `python3 map_cover.py`
either runs through and writes two PNGs per collection into `out/` (the cover and its
background), or it aborts. A change counts as checked only once the resulting image has been
looked at — especially anything touching positions, since there is no collision detection
for labels. If you only work on one collection, append its folder name
(`python3 map_cover.py brandy-haiger`); if you change the shared layout, check all of them,
because every collection has a different map frame.

The app half does have one automated check, and it is worth running: `npm run check
--prefix web` is `svelte-check` against `src/lib/types.ts`, which mirrors what
`export_data.py` writes. A field renamed on one side and not the other is exactly the
mistake that would otherwise surface as an empty map. CI runs it.

Three things have a cheap, exact check and should use it instead of an opinion:

- **The cover must not move.** `sha256` of `out/<collection>.png` before and after. Anything
  that leaves it unchanged cannot have touched what komoot gets.
- **The geometry must not move.** `web/static/data/<collection>.json` carries the projected
  routes, highlights and endpoints. Keep a copy before a change and diff it after: same
  `projection()`, same `rdp` tolerance, so any difference in the numbers is a bug and not a
  matter of taste.
- **The icons must agree.** The icon page shows every icon twice, stamped by PIL and
  recorded by `svgdraw.py`. They come from the same function in `icons.py`; where the two
  tiles differ, the recorder is wrong. `shark` is the only `arc`, `windmount` has the
  thinnest strokes, `bike` the only stroked circle — those three catch most of it.

For the rest of the site the order is `map_cover.py`, then `export_data.py`, then
`npm run build --prefix web`. A change is checked only once it has been looked at in a
browser — home, a collection subpage and the icon list. On the subpage that means picking a
tour and looking at the two places where tours meet: „Der Knoten" sits on the Ulmtalradweg
and „Ulmtalradweg" lies across Über Greifenstein. Pick FU and the Ulmtalradweg has to run
unbroken through „Der Knoten" while „Der Knoten" steps back; pick KN and the same the other
way round. `#tour-FU` and `#tour-KN` in the address get you there in one load. The vector
lines have no alignment of their own — they come from `projection()` — so a shifted frame
shows up as lines running beside the tree-free corridors the background was stamped around
them, which is most visible at full zoom. The workflow `.github/workflows/maps.yml` does all
of it in CI: in a pull request as the artifact `collection-icons`, on `main` as a GitHub
Page.

Anything touching the progressive web app cannot be checked over `file://` — service worker
and manifest need an origin. `npm run preview --prefix web` and `http://localhost:4173/` are
enough; `localhost` counts as secure. A plain `python3 -m http.server` is *not*, because it
cannot answer a deep link with `404.html` and a collection page will simply 404. Checked
means: the service worker is *activated* under *Application*, and all four page types —
including a collection reached directly by its URL — still open with *Network → Offline*
switched on.

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
  its own collection and nothing else. It sits outside `render` because `export_data.py`
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

## The line between Python and the app

`export_data.py` writes no markup, no stylesheet and no script, and it must stay that way.
Python's job is what only Python can do here: read the GPX, project it, draw the sheets,
record the icons. Everything it produces is data or an image, and the app under `web/` is
what turns that into a page. If you find yourself putting a tag in a Python string, the
thing you are building belongs in `web/src`.

It hangs off the same configuration as the renderer: it imports `discover`, `read_config`,
`slugify`, `projection` and the colors from `map_cover.py` instead of repeating paths or
values. The icon list does not come from an enumeration but from the signature — every
function in `icons.py` whose first four parameters are named `d, x, y, s` is an icon, which
is what drops `poly` and `circ`. Icons are stamped large and then cropped to what was
actually drawn, because they reach past their radius by different amounts.

What crosses the line, all under `web/static/`:

- `data/index.json` — the collections, the four map colors, the fonts that shipped.
- `data/<slug>.json` — `geometry()`: routes, highlights, endpoints, elevation profiles and
  the cartouche clip, in the pixels of the finished image.
- `icons/sprite.svg` — one `<g id="ic-<name>-<size>">` per icon *and size*, recorded through
  `svgdraw.py`. The size is in the id on purpose; see below.
- `icons/<name>.svg` and `.png` — the two tiles of the icon page.
- `covers/`, `pwa/`, `fonts/` — the images and the faces.
- and beside the sources, `src/generated/tokens.css` and `theme.json`: `PAPER`, `INK`,
  `MUTED` and `ACCENT` as custom properties. The app is painted in the colors the map is
  drawn in, so it may not write them down a second time. `vite.config.ts` reads the same
  values for the manifest.

`src/lib/types.ts` is the other side of that contract and has to be changed with it.

## The map in the browser

`Map.svelte` builds the SVG over the background image. The background carries only what is
painted; everything semantic is a vector element on top of it.

That is the whole reason the highlighting works. Picking a tour sets two class names, the
rest is CSS: a `wash` rectangle over the painted map, `.route`/`.mark` at low opacity,
`.on` at full. There is nothing to cut free, so two tours crossing is not a case — they are
separate elements and always were. A highlight of another tour recedes with its tour even
when it sits on the picked line, and the picked line runs through unbroken. Do not
reintroduce a marker around the picked highlights: being the only ones left in front is
what marks them.

Five things carry weight in there:

- **The vector layer is clipped out of the cartouche** (`guard` in the JSON,
  `cartouche_box()` in `map_cover.py`). The cartouche is filled opaquely and sits inside
  the map frame; the renderer draws the routes underneath it, and without the clip the
  browser would draw them over it. Today there are 23 px between it and the nearest route —
  that is not a margin, it is one bad `offset` away.
- **Which tour a click means is decided by distance** (`hit.ts`), computed over the real
  lines, not by a stack of click paths. Where two tours run side by side both are reachable
  and the nearer wins; a near tie goes to the tour already picked, so a shared stretch does
  not flicker. This is what the old stacked `stroke-width` paths could not do.
- **Labels are measured in the browser** from `getBBox()`, twice — once when the marks
  render and once in `document.fonts.ready`, because before the web font arrives the
  fallback gives a narrower box. That measurement is the one imperative corner of an
  otherwise declarative component, and it stays imperative: there is no `label_box`
  mirroring the renderer any more and there must not be one again, because the background
  carries no labels and nothing has to agree with anything.
- **`rdp` returns indices, not points**, and its tolerance is 0.25 px rather than 1. The
  indices are what lets each point carry its position along the tour (per mille), which is
  what ties the map to the elevation profile in both directions. The tolerance is a quarter
  pixel because the map zooms to four times, where a whole pixel of error walks visibly out
  of the tree-free corridor.
- **Do not call a binding `state` in a component that uses runes.** A local `state` turns
  every `$state` in the file into a store subscription, silently. The tour state is called
  `tour` for exactly that reason.

Under zoom, routes scale with the map while icons, plates and text scale against it, so they
hold their size on screen. The zoom lives in `view.svelte.ts` and is the viewBox itself —
one coordinate system for image and vectors, so nothing can drift apart. The cover image
stays untouched and downloadable: it is what komoot shows as the cover.

Paths in the data (`bg`, `cover`) are relative to the site root, not to the page that reads
them — a collection page sits two levels down, so they need `base` in front. That is the
mistake that renders a map with no painted background under it.

`svgdraw.py` is what keeps the icons single-sourced. `SvgRecorder` behaves like an
`ImageDraw.Draw` and writes SVG instead of pixels, so `icons.py` stays the only place an
icon is described. Two things in there were measured against PIL rather than assumed, and
both would be silent if wrong: PIL lays the outline of an `ellipse` and the band of an
`arc` *inside* the bounding box, so stroked radii shrink by half the width; and the angles
of `arc` are parametric, not geometric. Icons are recorded at `size * S` — the radius the
renderer passes — because the stroke widths inside `icons.py` are clamped with
`max(2, int(s·k))`, and at any other scale those clamps resolve differently. The `<use>`
carries the matching `scale(1/S)`.

## Routing, the shell and the progressive web app

It is a single-page app. `ssr` is off everywhere; `/`, `/collections` and `/icons` are
prerendered as empty shells so GitHub Pages answers them with a real 200, and a collection
is a parameter, so it is reached through the `404.html` fallback `adapter-static` writes.
Pages returns a 404 status for it and the app renders anyway — that is the arrangement, not
a bug. `paths.base` comes from `$GITHUB_REPOSITORY` because the site lives under
`/<repository>/`, and `paths.relative` is off so those shells work at any depth.

Nothing renders on a server, so anything that has to exist before JavaScript runs belongs in
`app.html` — the manifest link, the icons, the `@font-face` rules, the `<noscript>`. A
`<svelte:head>` entry arrives only after hydration. The service worker registers itself from
`+layout.svelte` in `onMount`, because SvelteKit does not run `app.html` through Vite's html
plugin and nothing is injected for us.

`vite-plugin-pwa` generates the manifest and the service worker from the finished build, so
the precache list is whatever was actually written and there is nothing to keep in step by
hand. The old `service_worker()` walk, the sha256 cache name and the `map.js?v=<hash>` guard
are all gone with it: the bundler hashes asset file names, so a changed file is a different
URL and there is nothing left to invalidate. `maximumFileSizeToCacheInBytes` is raised
because the cover images are 1600×1200 and go past the 2 MB default. Navigations are
answered from the precached shell, which is what makes a collection open offline even though
its URL was never a file.

`app_icon()` still draws the compass rose with the PIL primitives of the maps, and
`ship_fonts()` still copies a font only when its licence file sits next to it, so the Google
fonts travel with the site and whatever a Windows or Linux machine happens to provide does
not. The `@font-face` rules are static: a face whose file never arrives simply does not
apply and the fallback in the same declaration takes over. That is also why the site never
disagrees with the PNG — both halves resolve the same face through `font_file()`.

`icons.py` contains nothing but the icons. Each follows the signature `fn(d, x, y, s)` with
`s` as the radius scale — the caller already passes `*S`, so do not scale again inside the
icon function. Icons draw relative to `x,y` and return nothing. Building blocks: `poly`,
`circ`, `tree`. The function name is the public interface: it appears as `"icon"` in the
JSON files, renaming it breaks them.

## Data

The GPX files in `gpx/<collection>/` are tracked and stay that way — without them the
script does not run. They contain start and end point to the metre, i.e. a home address;
that is a deliberate decision and not an open question. The `.gitignore` covers output
PNGs, `out/`, `__pycache__`, `*.pyc`, `.venv/` and, on the app side, everything generated:
`web/static/`, `web/src/generated/`, `web/build/`, `web/.svelte-kit/` and
`web/node_modules/`. `collection.json` and `web/package-lock.json`, by contrast, belong in
the repository — the lockfile because CI installs with `npm ci`.
