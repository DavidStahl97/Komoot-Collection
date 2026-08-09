# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@README.md

Die README erklärt Zweck, Setup und den Umgang mit Touren, Highlights und
Stellschrauben — sie wird über den Import oben mitgeladen und hier nicht
wiederholt. Was folgt, ist nur, was beim Arbeiten im Code stolpern lässt.

Projektsprache ist Deutsch — Kommentare, Commits und Doku auf Deutsch halten.

## Verifikation

Es gibt keine Tests, keinen Linter und kein Build-System. Das Skript *ist* der Test:
`python3 map_cover.py` läuft durch und schreibt ein PNG, oder es bricht ab. Eine Änderung
gilt erst als geprüft, wenn das erzeugte Bild angesehen wurde — insbesondere bei allem, was
Positionen betrifft, denn für Labels existiert keine Kollisionsprüfung.

Zwei Pfade sind hart verdrahtet und brechen in einer frischen Umgebung sofort:
`img.save('/home/claude/cover/...')` braucht ein existierendes Zielverzeichnis, und
`GF="/usr/share/fonts/truetype/google-fonts/%s.ttf"` erwartet Lora und Poppins dort —
fehlen sie, wirft schon der erste `F(...)`-Aufruf.

## Architektur

`map_cover.py` ist ein Skript, kein Modul: Es läuft von oben nach unten durch und zeichnet
schichtweise auf eine einzige PIL-Leinwand. Die Reihenfolge im File ist die
Zeichenreihenfolge (Papierkorn → Wald → Flüsse → Routen → Highlights → Endpunkte →
Kompass → Kartusche). Wer etwas verschiebt, ändert damit, was was überdeckt.

Tragende Konzepte:

- **Supersampling.** `S=2` skaliert die gesamte Leinwand; am Ende wird per LANCZOS auf
  1600×1200 zurückgerechnet. Deshalb muss *jede* neue Pixelgröße mit `*S` multipliziert
  werden — sonst wird das Element bei Änderung von `S` falsch groß.
- **Projektion.** `merc`/`P`/`PA` bilden Web-Mercator ab. Maßstab und Zentrum leiten sich
  aus der gemeinsamen Bounding Box *aller* Routen in `ROUTES` ab, gerahmt von `box`.
  Eine neue Tour verschiebt damit automatisch das gesamte Layout.
- **GPX-Zugriff über Kilometermarken.** `cum` liefert die kumulierte Haversine-Distanz;
  darauf setzen `at(route, km)` (Punkt bei km) und `seg(route, k0, k1)` (Teilstück) auf.
  Koordinaten werden immer über `at(...)` geholt, nie geschätzt oder als Literal
  eingetragen — Ausnahme sind die beiden Endpunkte Haiger und Brandoberndorf, die als
  Ortsmittelpunkte fest im Code stehen.
- **Masken statt Geodaten.** Die Waldfläche ist eine geblurrte Graustufenmaske aus
  Ellipsen entlang der Routen (`forest`); Bäume werden nur dort gestempelt, wo `fmask`
  hell genug und `rmask` (Route) frei ist. Die Flüsse sind Routenabschnitte via `seg`.
- **Determinismus.** Alle `random.Random(...)` haben feste Seeds (7, 11, 41, 23). Seeds
  nur bewusst ändern; sie sind die Stellschraube für die Streuung, nicht Rauschen.

`icons.py` enthält ausschließlich die Motive. Jedes folgt der Signatur `fn(d, x, y, s)` mit
`s` als Radius-Maßstab — der Aufrufer übergibt bereits `*S`, in der Icon-Funktion also
nicht erneut skalieren. Motive zeichnen relativ zu `x,y` und geben nichts zurück.
Bausteine: `poly`, `circ`, `tree`.

## Daten

Die vier GPX in `gpx/` sind getrackt und bleiben es — das Skript läuft ohne sie nicht.
Sie enthalten Start- und Endpunkt metergenau, also eine Wohnadresse; das ist bewusst so
entschieden und keine offene Frage. Die `.gitignore` deckt nur Ausgabe-PNGs, `__pycache__`,
`*.pyc` und `.venv/` ab.
