# Komoot-Collection-Karten

Generator für die Titelbilder der komoot-Collections — illustrierte Karten (1600×1200, 4:3)
aus den GPX-Exporten der Touren. Kein Netz nötig, keine externen Assets, keine Bild-KI —
alles wird aus PIL-Primitiven gezeichnet.

Erste Collection: [„Brandy <-> Haiger"](https://www.komoot.com/collection/4605392/-brandy-haiger) —
Gravel-Routen zwischen Haiger und Brandoberndorf im Lahn-Dill-Bergland.

## Inhalt

| Datei | Zweck |
|---|---|
| `map_cover.py` | Baut die Karten. Rendert intern mit 2× Supersampling. |
| `icons.py` | Die gezeichneten Motive (Fuchs, See, Windräder-Berg, Radweg, Fluss, idyllischer Weg, Dill, Grube, Hai, Haus im Wald). |
| `gpx/<collection>/` | Ein Ordner pro Collection: die GPX-Exporte und optional eine `collection.json`. |
| `out/` | Zielordner der erzeugten PNGs (nicht eingecheckt). |

## Setup

```bash
pip install pillow numpy
python3 map_cover.py                 # alle Collections unter gpx/ nach out/
python3 map_cover.py brandy-haiger   # nur eine Collection
python3 map_cover.py --out /pfad/zu/cover
```

Alle Pfade sind relativ zum Repo-Wurzelverzeichnis; `--gpx` und `--out` verschieben sie.
Fehlen die Google-Fonts (Poppins, Lora), weicht das Skript auf DejaVu bzw. Liberation aus —
das Layout bleibt gleich, die Schrift ändert sich.

> **Hinweis:** Die GPX enthalten den Start- und Endpunkt der Touren metergenau.
> Bei einem öffentlichen Repo ist das eine Wohnadresse für jeden lesbar —
> in dem Fall besser `gpx/` in die `.gitignore` aufnehmen oder das Repo privat halten.

## Neue Collection anlegen

1. Ordner unter `gpx/` anlegen, z. B. `gpx/westerwald-runden/`.
2. Die GPX-Exporte aus komoot hineinlegen.
3. `python3 map_cover.py` laufen lassen — der Ordner wird automatisch erkannt.

Ohne weitere Angaben entsteht bereits eine vollständige Karte: Ausschnitt, Waldfläche und
Baumstempel skalieren mit der gemeinsamen Bounding Box der Routen des Ordners, der Titel
wird aus dem Ordnernamen abgeleitet (`westerwald-runden` → `WESTERWALD` / `RUNDEN`), die
Datei heißt `out/westerwald-runden.png`.

Für Titel, Highlights, Flüsse und Endpunkte kommt eine `collection.json` in denselben Ordner:

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

Alle Felder sind optional:

| Feld | Bedeutung |
|---|---|
| `name` | Nur für die Konsolenausgabe. Default: Ordnername. |
| `output` | Dateiname im Zielordner. Default: `<ordnername>.png`. |
| `title` | Zeilen der Kartusche (Großschrift). Leere Liste = keine Kartusche. |
| `arrow` | Doppelpfeil zwischen den Titelzeilen. Default: an, wenn genau zwei Zeilen. |
| `subtitle` | Kursive Zeilen unter dem Trennstrich. |
| `routes` | Reihenfolge und Kürzel der GPX. Nicht aufgeführte GPX des Ordners werden trotzdem gezeichnet. |
| `rivers` | Flussabschnitte, abgeleitet aus `route` + Kilometerbereich `from`/`to`. |
| `highlights` | Motiv + Beschriftung (siehe unten). |
| `endpoints` | Start/Ziel mit fester Koordinate, Motiv und Balkenbeschriftung. |

Die Kartusche wächst mit der Zeilenzahl nach oben und in der Breite mit — sie bleibt
unten links verankert.

## Neues Highlight hinzufügen

**Koordinaten nicht schätzen.** Die komoot-Tourseite nennt zu jedem Highlight eine
Kilometermarke. Mit `"route"` + `"km"` läuft das Skript die GPX bis zu dieser Distanz ab
und nimmt den echten Punkt. Alternativ direkt `"lat"`/`"lon"` angeben.

```json
{"label": "Name", "route": "FU", "km": 17.0, "icon": "fox", "side": "l", "offset": [-6, -56], "size": 34}
```

`offset` verschiebt nur das Label (in unskalierten px). `side`: `"l"` = rechtsbündig endend,
`"r"` = rechts vom Punkt, `"c"` = zentriert. Eine Kollisionsprüfung gibt es nicht —
Bild ansehen und nachjustieren.

Neues Motiv: Funktion in `icons.py` nach dem Muster `fn(d, x, y, s)` anlegen, wobei `s`
der Radius-Maßstab ist; der Name daraus ist der Wert von `"icon"`. Hilfsfunktionen `poly`,
`circ`, `tree` stehen bereit.

## Eingabedaten

GPX-Exporte der Touren aus komoot. Aktuell eingebunden — `gpx/brandy-haiger/`:

| Datei | Tour | Distanz | Höhenmeter |
|---|---|---|---|
| `______ber_Greifenstein.gpx` | Über Greifenstein | 69,7 km | 1.150 hm |
| `_____Fuchskaute___Ulmtalradweg.gpx` | Fuchskaute – Ulmtalradweg | 73,5 km | 750 hm |
| `_____Dilltalradweg.gpx` | Dilltalradweg | 56,6 km | 470 hm |
| `______ber_den_Knoten.gpx` | Über den Knoten | 80,1 km | 1.090 hm |

Die kryptischen Dateinamen stammen aus dem komoot-Export (Umlaute werden zu Unterstrichen).
Umbenennen ist möglich, dann aber auch die `file`-Einträge in `collection.json` anpassen.

## Stellschrauben

| Stelle | Wirkung |
|---|---|
| `random.Random(23)` | Streuung der Waldbäume. Andere Zahl = andere Verteilung. |
| `for _ in range(26)` (bei `rnd2`) | Anzahl der weichen Randflächen. Mehr = vollere Ecken. |
| `for _ in range(420)` | Blasse Randbäume. Zu hoch gesetzt sieht es nach Tapete aus. |
| `BOX = (...)` | Kartenausschnitt auf dem Blatt. |

Alle Zufallszahlen haben feste Seeds — jeder Lauf erzeugt exakt dasselbe Bild.

## Bekannte Grenzen

- Die Waldfläche ist eine weiche Hülle um die Routen, keine echten Waldflächen
  (es gibt keine Landnutzungsdaten im Projekt).
- Die Flüsse sind aus Streckenabschnitten abgeleitet und stimmen nur dort,
  wo die Route tatsächlich am Fluss entlangführt.
- Kartusche (unten links) und Kompass (unten rechts) sind fest positioniert. Wenn neue
  Touren den Ausschnitt stark verbreitern, können Routen darunter laufen.
- Die Höhendaten in komoot-GPX sind geglättet; kurze Steilrampen über ~15 % tauchen darin
  nicht auf. Für Steigungsanalysen ist die aufgezeichnete Fahrt aussagekräftiger — und
  selbst da ist die Geschwindigkeit der ehrlichere Indikator als die Höhenkurve.

## Format

1600×1200 (4:3), weil komoot die Vorschau in 4:3 rendert und bei 3:2 links und rechts
beschneidet.
