# Brandy ↔ Haiger

Generator für das Titelbild der komoot-Collection
[„Brandy <-> Haiger"](https://www.komoot.com/collection/4605392/-brandy-haiger) —
Gravel-Routen zwischen Haiger und Brandoberndorf im Lahn-Dill-Bergland.

Erzeugt eine illustrierte Karte (1600×1200, 4:3) aus den GPX-Exporten der Touren.
Kein Netz nötig, keine externen Assets, keine Bild-KI — alles wird aus PIL-Primitiven gezeichnet.

## Inhalt

| Datei | Zweck |
|---|---|
| `map_cover.py` | Baut die Karte. Rendert intern mit 2× Supersampling. |
| `icons.py` | Die gezeichneten Motive (Fuchs, See, Windräder-Berg, Radweg, Fluss, idyllischer Weg, Dill, Grube, Hai, Haus im Wald). |
| `gpx/` | Die GPX-Exporte der Touren. Ohne sie läuft das Skript nicht. |

## Setup

```bash
pip install pillow numpy
python3 map_cover.py
```

Läuft ohne Anpassung, wenn du aus dem Repo-Wurzelverzeichnis startest — `U = 'gpx/'` ist
relativ gesetzt. Nur den Pfad in `img.save(...)` musst du auf dein Zielverzeichnis ändern.

> **Hinweis:** Die GPX enthalten den Start- und Endpunkt der Touren metergenau.
> Bei einem öffentlichen Repo ist das eine Wohnadresse für jeden lesbar —
> in dem Fall besser `gpx/` in die `.gitignore` aufnehmen oder das Repo privat halten.

## Eingabedaten

GPX-Exporte der Touren aus komoot, im Ordner `gpx/`. Aktuell eingebunden:

| Datei | Tour | Distanz | Höhenmeter |
|---|---|---|---|
| `______ber_Greifenstein.gpx` | Über Greifenstein | 69,7 km | 1.150 hm |
| `_____Fuchskaute___Ulmtalradweg.gpx` | Fuchskaute – Ulmtalradweg | 73,5 km | 750 hm |
| `_____Dilltalradweg.gpx` | Dilltalradweg | 56,6 km | 470 hm |
| `______ber_den_Knoten.gpx` | Über den Knoten | 80,1 km | 1.090 hm |

Die kryptischen Dateinamen stammen aus dem komoot-Export (Umlaute werden zu Unterstrichen).
Umbenennen ist möglich, dann aber auch die `load(...)`-Aufrufe in `map_cover.py` anpassen.

## Neue Tour hinzufügen

1. GPX exportieren, nach `gpx/` legen.
2. In `map_cover.py` mit `load(...)` einlesen und der Liste `ROUTES` anhängen.

Kartenausschnitt, Waldfläche und Baumstempel skalieren automatisch mit der gemeinsamen
Bounding Box aller Routen.

## Neues Highlight hinzufügen

**Koordinaten nicht schätzen.** Die komoot-Tourseite nennt zu jedem Highlight eine
Kilometermarke. `at(ROUTE, km)` läuft die GPX bis zu dieser Distanz ab und liefert den
echten Punkt:

```python
at(FU, 17.0)   # -> Fuchskaute
```

Dann einen Eintrag in `HL` ergänzen:

```python
("Name", at(ROUTE, km), IC.iconfunktion, 'l'|'r'|'c', (dx, dy))
```

`dx/dy` verschiebt nur das Label (in unskalierten px). `'l'` = rechtsbündig endend,
`'r'` = rechts vom Punkt, `'c'` = zentriert. Eine Kollisionsprüfung gibt es nicht —
Bild ansehen und nachjustieren.

Neues Motiv: Funktion in `icons.py` nach dem Muster `fn(d, x, y, s)` anlegen, wobei `s`
der Radius-Maßstab ist. Hilfsfunktionen `poly`, `circ`, `tree` stehen bereit.

## Stellschrauben

| Stelle | Wirkung |
|---|---|
| `random.Random(23)` | Streuung der Waldbäume. Andere Zahl = andere Verteilung. |
| `for _ in range(26)` (bei `rnd2`) | Anzahl der weichen Randflächen. Mehr = vollere Ecken. |
| `for _ in range(420)` | Blasse Randbäume. Zu hoch gesetzt sieht es nach Tapete aus. |
| `box = (...)` | Kartenausschnitt auf dem Blatt. |

Alle Zufallszahlen haben feste Seeds — jeder Lauf erzeugt exakt dasselbe Bild.

## Bekannte Grenzen

- Die Waldfläche ist eine weiche Hülle um die Routen, keine echten Waldflächen
  (es gibt keine Landnutzungsdaten im Projekt).
- Die Flüsse (Lahn, Dill) sind aus Streckenabschnitten abgeleitet und stimmen nur dort,
  wo die Route tatsächlich am Fluss entlangführt.
- Kartusche (unten links) und Kompass (unten rechts) sind fest positioniert. Wenn neue
  Touren den Ausschnitt stark verbreitern, können Routen darunter laufen.
- Die Höhendaten in komoot-GPX sind geglättet; kurze Steilrampen über ~15 % tauchen darin
  nicht auf. Für Steigungsanalysen ist die aufgezeichnete Fahrt aussagekräftiger — und
  selbst da ist die Geschwindigkeit der ehrlichere Indikator als die Höhenkurve.

## Format

1600×1200 (4:3), weil komoot die Vorschau in 4:3 rendert und bei 3:2 links und rechts
beschneidet.
