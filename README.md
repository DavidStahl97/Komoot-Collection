# Karten für komoot-Collections

Generator für die Titelbilder meiner komoot-Collections. Die erste ist
[„Brandy <-> Haiger"](https://www.komoot.com/collection/4605392/-brandy-haiger) —
Gravel-Routen zwischen Haiger und Brandoberndorf im Lahn-Dill-Bergland; weitere
kommen als eigene Ordner dazu.

Aus den GPX-Exporten der Touren entsteht eine illustrierte Karte im Stil einer
alten Wanderkarte: getöntes Papier, gestrichelte Wege, gestempelte Wälder und
kleine gezeichnete Motive an den Highlights. Kein Netz nötig, keine externen
Assets, keine Bild-KI — jede Linie kommt aus PIL-Primitiven. Das Ergebnis ist
1600×1200 Pixel groß, weil komoot die Vorschau im Seitenverhältnis 4:3 rendert
und bei 3:2 links und rechts beschneidet.

## Loslegen

```bash
pip install pillow numpy
python3 map_cover.py                 # alle Collections unter gpx/ nach out/
python3 map_cover.py brandy-haiger   # nur diese eine
python3 map_cover.py --out /pfad/zu/cover
```

Aus dem Repo-Wurzelverzeichnis starten — die Pfade sind relativ gesetzt und lassen
sich mit `--gpx` und `--out` verschieben. Fehlen die Google-Fonts Lora und Poppins
unter `/usr/share/fonts/truetype/google-fonts/`, weicht das Skript auf DejaVu bzw.
Liberation aus: Das Layout bleibt, die Schrift sieht anders aus.

Jeder Lauf erzeugt exakt dasselbe Bild — alle Zufallszahlen haben feste Seeds.

## Was wo liegt

| Datei | Zweck |
|---|---|
| `map_cover.py` | Findet die Collections und baut jede Karte, von oben nach unten in Schichten. |
| `icons.py` | Die gezeichneten Motive: Fuchs, See, Windräder-Berg, Radweg, Fluss, idyllischer Weg, Dill, Grube, Hai, Haus im Wald. |
| `build_site.py` | Baut aus den erzeugten Karten die GitHub-Page: Home, Collections, Icons. |
| `gpx/<collection>/` | Ein Ordner je Collection: die GPX-Exporte und optional eine `collection.json`. Ohne sie läuft nichts. |
| `out/` | Die erzeugten PNGs. Nicht eingecheckt. |
| `site/` | Die erzeugte Seite. Nicht eingecheckt. |
| `.github/workflows/karten.yml` | Rendert bei jedem Push und Pull Request, hängt die Bilder an den PR und veröffentlicht die Seite. |

## Eine neue Collection anlegen

1. Ordner unter `gpx/` anlegen, etwa `gpx/westerwald-runden/`.
2. Die GPX-Exporte aus komoot hineinlegen.
3. `python3 map_cover.py` — der Ordner wird von allein gefunden.

Das reicht schon für eine fertige Karte: Ausschnitt, Waldfläche und Baumstempel
skalieren mit der gemeinsamen Bounding Box der Routen *dieses* Ordners, der Titel
kommt aus dem Ordnernamen (`westerwald-runden` → `WESTERWALD` / `RUNDEN`), die
Datei heißt `out/westerwald-runden.png`. Collections beeinflussen sich nicht
gegenseitig — jede bekommt ihren eigenen Kartenausschnitt.

Titel, Highlights, Flüsse und Endpunkte kommen in eine `collection.json` im selben
Ordner. Sie ist optional, und jedes Feld darin ist es auch:

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

| Feld | Bedeutung |
|---|---|
| `name` | Nur für die Konsolenausgabe. Default: Ordnername. |
| `output` | Dateiname im Zielordner. Default: `<ordnername>.png`. |
| `title` | Zeilen der Kartusche in Großschrift. Leere Liste = keine Kartusche. |
| `arrow` | Doppelpfeil zwischen zwei Titelzeilen. Default: an, wenn es genau zwei sind. |
| `subtitle` | Kursive Zeilen unter dem Trennstrich. |
| `routes` | Reihenfolge und Kürzel der GPX. Nicht aufgeführte GPX des Ordners werden trotzdem gezeichnet. |
| `rivers` | Flussabschnitte, abgeleitet aus `route` plus Kilometerbereich `from`/`to`. |
| `highlights` | Motiv mit Beschriftung, siehe unten. |
| `endpoints` | Start und Ziel mit fester Koordinate, Motiv und Balkenbeschriftung. |

Die Kartusche wächst mit Zeilenzahl und Textbreite mit und bleibt dabei unten links
verankert — längere Titel sprengen sie also nicht.

## Die Touren

Aktuell eingebunden, in `gpx/brandy-haiger/`:

| Datei | Tour | Distanz | Höhenmeter |
|---|---|---|---|
| `______ber_Greifenstein.gpx` | Über Greifenstein | 69,7 km | 1.150 hm |
| `_____Fuchskaute___Ulmtalradweg.gpx` | Fuchskaute – Ulmtalradweg | 73,5 km | 750 hm |
| `_____Dilltalradweg.gpx` | Dilltalradweg | 56,6 km | 470 hm |
| `______ber_den_Knoten.gpx` | Über den Knoten | 80,1 km | 1.090 hm |

Die kryptischen Dateinamen stammen aus dem komoot-Export, der Umlaute zu
Unterstrichen macht. Umbenennen geht, dann aber auch die `file`-Einträge in der
`collection.json` mitziehen.

Die GPX enthalten Start- und Endpunkt der Touren metergenau — in einem
öffentlichen Repo ist das eine lesbare Wohnadresse. Hier ist das bewusst so
entschieden; wer das Projekt für eigene Touren nachbaut, sollte die Frage für
sich neu beantworten.

## Eine Tour ergänzen

GPX exportieren und in den Ordner der Collection legen. Steht dort keine
`routes`-Liste, ist damit alles getan; sonst noch einen Eintrag `{"key": "…",
"file": "…"}` ergänzen, damit sie sich in Highlights und Flüssen ansprechen lässt.
Kartenausschnitt, Waldfläche und Baumstempel skalieren automatisch mit der
gemeinsamen Bounding Box aller Routen der Collection.

## Ein Highlight ergänzen

Koordinaten nicht schätzen. Die komoot-Tourseite nennt zu jedem Highlight eine
Kilometermarke, und `route` plus `km` läuft die GPX bis dorthin ab und liefert den
echten Punkt. Nur wo es keine Kilometermarke gibt — Ortsmittelpunkte etwa —
stehen `lat`/`lon` direkt in der Konfiguration:

```json
{"label": "Name", "route": "FU", "km": 17.0, "icon": "fox", "side": "l", "offset": [-6, -56], "size": 34}
```

`offset` verschiebt nur das Label, `"l"` lässt es rechtsbündig am Punkt enden,
`"r"` setzt es rechts daneben, `"c"` zentriert. Eine Kollisionsprüfung gibt es
nicht — Bild ansehen und nachjustieren.

Ein neues Motiv wird eine Funktion in `icons.py` nach dem Muster `fn(d, x, y, s)`,
wobei `s` der Radius-Maßstab ist; ihr Name ist der Wert von `"icon"`. `poly`,
`circ` und `tree` stehen als Bausteine bereit.

## GitHub Actions und die Seite

`.github/workflows/karten.yml` läuft bei jedem Push auf `main` und bei jedem Pull
Request. Beide Male werden die Karten gerendert und die Seite gebaut:

- **Im Pull Request** hängen die Bilder als Artefakt `collection-icons` am Lauf —
  die Titelbilder aus `out/` und jedes einzelne Motiv aus `icons.py`. Weil es keine
  Tests gibt, ist das Herunterladen und Ansehen dieses Artefakts die Prüfung.
- **Auf `main`** wird die Seite zusätzlich über GitHub Pages veröffentlicht. Dafür
  muss in den Repo-Einstellungen unter *Pages* als Quelle *GitHub Actions* gewählt
  sein; der Workflow braucht keine weiteren Secrets.

Die Seite hat drei Bereiche: **Home** listet alle Collections mit ihrem Titelbild,
**Collections** führt zu je einer Unterseite pro Collection (großes Bild, Touren,
Highlights mit Motiv), **Icons** zeigt alle Motive aus `icons.py` mit ihrem
Funktionsnamen — also mit dem Wert, der als `"icon"` in die `collection.json` gehört.
Lokal:

```bash
python3 map_cover.py --out out
python3 build_site.py --png out --out site
```

Neue Motive und neue Collections tauchen von allein auf: `build_site.py` sammelt die
Collections über `discover()` und die Motive über die Signatur `fn(d, x, y, s)`.

Lora und Poppins fehlen den GitHub-Runnern; der Workflow lädt sie vor dem Rendern
nach. Schlägt das fehl, greift der Fallback auf DejaVu/Liberation — die Karte
entsteht trotzdem, nur die Schrift sieht anders aus.

## Woran man drehen kann

| Stelle | Wirkung |
|---|---|
| `random.Random(23)` | Streuung der Waldbäume. Andere Zahl = andere Verteilung. |
| `for _ in range(26)` (bei `rnd2`) | Anzahl der weichen Randflächen. Mehr = vollere Ecken. |
| `for _ in range(420)` | Blasse Randbäume. Zu hoch gesetzt sieht es nach Tapete aus. |
| `BOX = (...)` | Kartenausschnitt auf dem Blatt. Gilt für alle Collections. |

## Was die Karte nicht kann

- Die Waldfläche ist eine weiche Hülle um die Routen, keine echten Waldflächen —
  Landnutzungsdaten gibt es im Projekt nicht.
- Die Flüsse (Lahn, Dill) sind aus Streckenabschnitten abgeleitet und stimmen nur
  dort, wo die Route tatsächlich am Fluss entlangführt.
- Kompass (unten rechts) und Kartusche (unten links) sind fest positioniert; die
  Kartusche wächst zwar mit ihrem Text, weicht Routen darunter aber nicht aus.
- Die Höhendaten in komoot-GPX sind geglättet; kurze Steilrampen über ~15 %
  tauchen darin nicht auf. Für Steigungsanalysen ist die aufgezeichnete Fahrt
  aussagekräftiger — und selbst da ist die Geschwindigkeit der ehrlichere
  Indikator als die Höhenkurve.
