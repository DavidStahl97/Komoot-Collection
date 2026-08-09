# Brandy ↔ Haiger

Generator für das Titelbild der komoot-Collection
[„Brandy <-> Haiger"](https://www.komoot.com/collection/4605392/-brandy-haiger) —
Gravel-Routen zwischen Haiger und Brandoberndorf im Lahn-Dill-Bergland.

Aus den GPX-Exporten der Touren entsteht eine illustrierte Karte im Stil einer
alten Wanderkarte: getöntes Papier, gestrichelte Wege, gestempelte Wälder und
kleine gezeichnete Motive an den Highlights. Kein Netz nötig, keine externen
Assets, keine Bild-KI — jede Linie kommt aus PIL-Primitiven. Das Ergebnis ist
1600×1200 Pixel groß, weil komoot die Vorschau im Seitenverhältnis 4:3 rendert
und bei 3:2 links und rechts beschneidet.

## Loslegen

```bash
pip install pillow numpy
python3 map_cover.py
```

Aus dem Repo-Wurzelverzeichnis starten — der Pfad zu den GPX ist relativ gesetzt.
Zwei Dinge musst du vorher anpassen: das Zielverzeichnis in `img.save(...)` am
Ende von `map_cover.py`, und gegebenenfalls den Fontpfad `GF` weiter oben, der die
Google-Fonts Lora und Poppins unter `/usr/share/fonts/truetype/google-fonts/`
erwartet.

Jeder Lauf erzeugt exakt dasselbe Bild — alle Zufallszahlen haben feste Seeds.

## Was wo liegt

| Datei | Zweck |
|---|---|
| `map_cover.py` | Baut die Karte, von oben nach unten in Schichten. |
| `icons.py` | Die gezeichneten Motive: Fuchs, See, Windräder-Berg, Radweg, Fluss, idyllischer Weg, Dill, Grube, Hai, Haus im Wald. |
| `gpx/` | Die GPX-Exporte der Touren. Ohne sie läuft nichts. |

## Die Touren

| Datei | Tour | Distanz | Höhenmeter |
|---|---|---|---|
| `______ber_Greifenstein.gpx` | Über Greifenstein | 69,7 km | 1.150 hm |
| `_____Fuchskaute___Ulmtalradweg.gpx` | Fuchskaute – Ulmtalradweg | 73,5 km | 750 hm |
| `_____Dilltalradweg.gpx` | Dilltalradweg | 56,6 km | 470 hm |
| `______ber_den_Knoten.gpx` | Über den Knoten | 80,1 km | 1.090 hm |

Die kryptischen Dateinamen stammen aus dem komoot-Export, der Umlaute zu
Unterstrichen macht. Umbenennen geht, dann aber auch die `load(...)`-Aufrufe in
`map_cover.py` mitziehen.

Die GPX enthalten Start- und Endpunkt der Touren metergenau — in einem
öffentlichen Repo ist das eine lesbare Wohnadresse. Hier ist das bewusst so
entschieden; wer das Projekt für eigene Touren nachbaut, sollte die Frage für
sich neu beantworten.

## Eine Tour ergänzen

GPX exportieren, nach `gpx/` legen, in `map_cover.py` mit `load(...)` einlesen und
an die Liste `ROUTES` anhängen. Kartenausschnitt, Waldfläche und Baumstempel
skalieren automatisch mit der gemeinsamen Bounding Box aller Routen.

## Ein Highlight ergänzen

Koordinaten nicht schätzen. Die komoot-Tourseite nennt zu jedem Highlight eine
Kilometermarke, und `at(ROUTE, km)` läuft die GPX bis dorthin ab und liefert den
echten Punkt:

```python
at(FU, 17.0)   # -> Fuchskaute
```

Damit einen Eintrag in `HL` ergänzen:

```python
("Name", at(ROUTE, km), IC.iconfunktion, 'l'|'r'|'c', (dx, dy))
```

`dx/dy` verschiebt nur das Label, `'l'` lässt es rechtsbündig am Punkt enden,
`'r'` setzt es rechts daneben, `'c'` zentriert. Eine Kollisionsprüfung gibt es
nicht — Bild ansehen und nachjustieren.

Ein neues Motiv wird eine Funktion in `icons.py` nach dem Muster `fn(d, x, y, s)`,
wobei `s` der Radius-Maßstab ist. `poly`, `circ` und `tree` stehen als Bausteine
bereit.

## Woran man drehen kann

| Stelle | Wirkung |
|---|---|
| `random.Random(23)` | Streuung der Waldbäume. Andere Zahl = andere Verteilung. |
| `for _ in range(26)` (bei `rnd2`) | Anzahl der weichen Randflächen. Mehr = vollere Ecken. |
| `for _ in range(420)` | Blasse Randbäume. Zu hoch gesetzt sieht es nach Tapete aus. |
| `box = (...)` | Kartenausschnitt auf dem Blatt. |

## Was die Karte nicht kann

- Die Waldfläche ist eine weiche Hülle um die Routen, keine echten Waldflächen —
  Landnutzungsdaten gibt es im Projekt nicht.
- Die Flüsse (Lahn, Dill) sind aus Streckenabschnitten abgeleitet und stimmen nur
  dort, wo die Route tatsächlich am Fluss entlangführt.
- Kartusche (unten links) und Kompass (unten rechts) sind fest positioniert. Wenn
  neue Touren den Ausschnitt stark verbreitern, können Routen darunter laufen.
- Die Höhendaten in komoot-GPX sind geglättet; kurze Steilrampen über ~15 %
  tauchen darin nicht auf. Für Steigungsanalysen ist die aufgezeichnete Fahrt
  aussagekräftiger — und selbst da ist die Geschwindigkeit der ehrlichere
  Indikator als die Höhenkurve.
