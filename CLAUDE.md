# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Projektsprache ist Deutsch — Kommentare, Commits und Doku auf Deutsch halten.

## Ausführen

```bash
pip install pillow numpy      # einzige Abhängigkeiten
python3 map_cover.py          # muss aus dem Repo-Wurzelverzeichnis laufen (U='gpx/' ist relativ)
```

Es gibt keine Tests, keinen Linter und kein Build-System. Das Skript *ist* der Test:
Es läuft durch und schreibt ein PNG, oder es bricht ab. Verifikation heißt, das erzeugte
Bild anzusehen.

Zwei Pfade sind hart verdrahtet und müssen in einer neuen Umgebung angepasst werden,
bevor `map_cover.py` durchläuft:

- `img.save('/home/claude/cover/brandy-haiger-karte.png')` — Zielverzeichnis muss existieren.
- `GF="/usr/share/fonts/truetype/google-fonts/%s.ttf"` — erwartet die Google-Fonts
  Lora und Poppins an diesem Pfad. Fehlen sie, wirft `ImageFont.truetype` beim ersten
  `F(...)`-Aufruf.

## Architektur

`map_cover.py` ist ein Skript, kein Modul: Es läuft beim Import von oben nach unten durch
und zeichnet dabei schichtweise auf eine einzige PIL-Leinwand. Die Reihenfolge im File ist
die Zeichenreihenfolge (Papierkorn → Wald → Flüsse → Routen → Highlights → Endpunkte →
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
  Highlight-Koordinaten werden immer über `at(...)` mit der Kilometermarke von der
  komoot-Tourseite geholt, nie geschätzt oder als Literal eingetragen.
- **Masken statt Geodaten.** Es gibt keine Landnutzungsdaten. Die Waldfläche ist eine
  geblurrte Graustufenmaske aus Ellipsen entlang der Routen (`forest`); Bäume werden nur
  dort gestempelt, wo `fmask` hell genug und `rmask` (Route) frei ist. Die Flüsse sind
  Routenabschnitte via `seg`, keine echten Flussläufe.
- **Determinismus.** Alle `random.Random(...)` haben feste Seeds (7, 11, 41, 23) — jeder
  Lauf erzeugt exakt dasselbe Bild. Seeds nur bewusst ändern; sie sind die Stellschraube
  für die Streuung, nicht Rauschen.

`icons.py` enthält ausschließlich die gezeichneten Motive. Jedes folgt der Signatur
`fn(d, x, y, s)` mit `s` als Radius-Maßstab (Aufrufer übergibt bereits `*S`), zeichnet
relativ zu `x,y` und gibt nichts zurück. Bausteine: `poly`, `circ`, `tree`.

## Daten

`gpx/` enthält die vier komoot-Exporte. Sie sind getrackt, obwohl die `.gitignore` ihre
Namen listet — die Regel greift für getrackte Dateien nicht mehr. Beachten: Die GPX
enthalten Start- und Endpunkt metergenau, also eine Wohnadresse. Vor einem öffentlichen
Repo ist das eine bewusste Entscheidung, keine Nebensache.

Die Dateinamen (`______ber_den_Knoten.gpx` etc.) stammen aus dem komoot-Export, der
Umlaute zu Unterstrichen macht. Beim Umbenennen die `load(...)`-Aufrufe mitziehen.

## Erweitern

Neue Tour: GPX nach `gpx/`, mit `load(...)` einlesen, an `ROUTES` anhängen — Ausschnitt
und Wald skalieren mit.

Neues Highlight: Eintrag in `HL` als
`("Name", at(ROUTE, km), IC.iconfunktion, 'l'|'r'|'c', (dx, dy))`. `dx/dy` verschiebt nur
das Label in unskalierten px, `'l'` endet rechtsbündig am Punkt, `'r'` steht rechts davon,
`'c'` zentriert. Es gibt **keine** Kollisionsprüfung für Labels — nach jeder Änderung das
Bild ansehen und nachjustieren.

Kartusche (unten links) und Kompass (unten rechts) sind fest positioniert. Verbreitert
eine neue Tour den Ausschnitt stark, können Routen darunter durchlaufen.
