# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@README.md

Die README erklärt Zweck, Setup und den Umgang mit Collections, Touren, Highlights und
Stellschrauben — sie wird über den Import oben mitgeladen und hier nicht wiederholt.
Was folgt, ist nur, was beim Arbeiten im Code stolpern lässt.

Projektsprache ist Deutsch — Kommentare, Commits und Doku auf Deutsch halten.

## Verifikation

Es gibt keine Tests, keinen Linter und kein Build-System. Das Skript *ist* der Test:
`python3 map_cover.py` läuft durch und schreibt je Collection ein PNG nach `out/`, oder es
bricht ab. Eine Änderung gilt erst als geprüft, wenn das erzeugte Bild angesehen wurde —
insbesondere bei allem, was Positionen betrifft, denn für Labels existiert keine
Kollisionsprüfung. Wer nur an einer Collection arbeitet, hängt ihren Ordnernamen an
(`python3 map_cover.py brandy-haiger`); wer am gemeinsamen Layout dreht, prüft alle, denn
jede Collection hat einen anderen Kartenausschnitt.

Zielverzeichnis und Fonts sind nicht mehr hart verdrahtet: `out/` wird angelegt, wenn es
fehlt, und `F(...)` weicht auf DejaVu bzw. Liberation aus, wenn die Google-Fonts fehlen.
Ein Lauf auf einer fremden Maschine sagt darum nichts über die endgültige Typografie —
Schriftmetriken unterscheiden sich, Zeilen können anders brechen oder überlappen.

## Architektur

`map_cover.py` hat zwei Hälften. Oben stehen Konfiguration und GPX-Helfer (`load`, `cum`,
`seg`, `at`, `discover`, `read_config`), unten zeichnet `render(cfg, out_path)` eine
Collection auf eine PIL-Leinwand. Innerhalb von `render` ist die Reihenfolge im File die
Zeichenreihenfolge (Papierkorn → Wald → Flüsse → Routen → Highlights → Endpunkte →
Kompass → Kartusche). Wer etwas verschiebt, ändert damit, was was überdeckt.

`main()` sucht über `discover()` alle Unterordner von `gpx/`, die GPX enthalten, und ruft
für jeden `read_config` und `render` auf. Jede Collection ist vollständig für sich: eigener
Ausschnitt, eigene Highlights, eigene Ausgabedatei. Gemeinsam sind nur die Konstanten am
Dateikopf (`S`, `W`/`H`, Farben, `BOX`) und die Motive in `icons.py`.

Tragende Konzepte:

- **Konfiguration statt Code.** Alles Collection-Spezifische steht in
  `gpx/<collection>/collection.json`, nicht im Skript. Neue Touren, Highlights oder Titel
  gehören dorthin; `map_cover.py` wird nur angefasst, wenn sich das *Kartenbild an sich*
  ändert. `read_config` füllt fehlende Felder aus dem Ordner auf, deshalb muss jedes neue
  Feld dort ein `setdefault` bekommen — ein Ordner ohne `collection.json` muss weiter
  durchlaufen.
- **Referenzen über Kürzel.** Highlights und Flüsse zeigen per `"route"` auf einen `key`
  aus `routes`; `route_of` löst auf und wirft mit lesbarer Meldung, wenn das Kürzel nicht
  existiert. `icon_of` macht dasselbe für Motivnamen aus `icons.py`. Beides ist absichtlich
  laut — eine stille Karte ohne Highlight fällt sonst niemandem auf.
- **Supersampling.** `S=2` skaliert die gesamte Leinwand; am Ende wird per LANCZOS auf
  1600×1200 zurückgerechnet. Deshalb muss *jede* neue Pixelgröße mit `*S` multipliziert
  werden — sonst wird das Element bei Änderung von `S` falsch groß. Werte aus der JSON
  (`offset`, `size`) sind unskaliert und werden beim Zeichnen mit `*S` versehen.
- **Projektion.** `merc`/`P`/`PA` bilden Web-Mercator ab. Sie sind lokal in `render`, weil
  Maßstab und Zentrum aus der Bounding Box der Routen *dieser* Collection kommen, gerahmt
  von `BOX`. Eine neue Tour verschiebt damit das Layout ihrer Collection und nur das.
- **GPX-Zugriff über Kilometermarken.** `cum` liefert die kumulierte Haversine-Distanz;
  darauf setzen `at(route, km)` (Punkt bei km) und `seg(route, k0, k1)` (Teilstück) auf.
  Koordinaten kommen immer über `km`, nie geschätzt — Ausnahme sind Endpunkte wie Haiger
  und Brandoberndorf, die als Ortsmittelpunkte mit `lat`/`lon` in der JSON stehen.
- **Masken statt Geodaten.** Die Waldfläche ist eine geblurrte Graustufenmaske aus
  Ellipsen entlang der Routen (`forest`); Bäume werden nur dort gestempelt, wo `fmask`
  hell genug und `rmask` (Route) frei ist. Die Flüsse sind Routenabschnitte via `seg`.
- **Determinismus.** Alle `random.Random(...)` haben feste Seeds (7, 11, 41, 23) und werden
  in `render` neu gesetzt, damit die Reihenfolge der Collections das Bild nicht beeinflusst.
  Seeds nur bewusst ändern; sie sind die Stellschraube für die Streuung, nicht Rauschen.

`icons.py` enthält ausschließlich die Motive. Jedes folgt der Signatur `fn(d, x, y, s)` mit
`s` als Radius-Maßstab — der Aufrufer übergibt bereits `*S`, in der Icon-Funktion also
nicht erneut skalieren. Motive zeichnen relativ zu `x,y` und geben nichts zurück.
Bausteine: `poly`, `circ`, `tree`. Der Funktionsname ist die öffentliche Schnittstelle:
er steht als `"icon"` in den JSONs, Umbenennen bricht sie.

## Daten

Die GPX in `gpx/<collection>/` sind getrackt und bleiben es — ohne sie läuft das Skript
nicht. Sie enthalten Start- und Endpunkt metergenau, also eine Wohnadresse; das ist bewusst
so entschieden und keine offene Frage. Die `.gitignore` deckt Ausgabe-PNGs, `out/`,
`__pycache__`, `*.pyc` und `.venv/` ab; `collection.json` gehört dagegen ins Repo.
