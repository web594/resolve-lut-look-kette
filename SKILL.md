---
name: resolve-lut-look-kette
description: Film-/Kino-Look in DaVinci Resolve als nachvollziehbare Kette aus vier LUT-Nodes plus einem regelbaren Node für Weißabgleich und Helligkeit — für Log-Material (Sony S-Log3/S-Gamut3.Cine) und Mehrkamera-Produktionen, mit Skripten, die die LUTs selbst erzeugen und die Kette als geteilte Farbgruppe anlegen. Nutzen bei "Film-Look", "Kino-Look", "Grading-Kette aufbauen", "LUT-Kette", "S-Log3 nach Rec.709", "auf ARRI wandeln", "Filmemulation", "Look auf alle Kameras", "eigene LUT erzeugen", "Look ohne gekaufte LUTs".
---

# Film-Look als LUT-Kette mit einem regelbaren Node

Ein Look, den man **auseinandernehmen kann**. Vier LUTs machen die objektiven Schritte,
ein einziger regelbarer Node macht alles Subjektive. Wer den Look später ändern will,
dreht an Reglern — nicht an einer neu gebackenen LUT.

## Die Kette

| # | Node | Art | Was er tut |
|---|------|-----|------------|
| 1 | **Log → ARRI Rec.709** | LUT | bringt das flache Log-Bild in ein normales, beurteilbares Bild — über ARRIs Farbwiedergabe statt über die Hersteller-LUT der Kamera |
| 2 | **Weißabgleich + Helligkeit** | **regelbar** | der einzige Node mit Zahlenwerten: Temperatur, Tönung, Belichtung, Kontrast — hier wird jede Kamera einzeln angepasst |
| 3 | **Rec.709 → ARRI LogC** | LUT | dreht das Bild wieder ins Log-Format zurück, weil die Filmemulation Log am Eingang erwartet |
| 4 | **Filmemulation** | LUT | Negativ + Kopierfilm: angehobenes Filmschwarz, weiche Lichter, Filmfarben |
| 5 | **Kino-Look** | LUT | der Feinschliff obendrauf: Kontrast, Teal/Orange, leichte Entsättigung |

**Die Reihenfolge ist der eigentliche Trick.** Der Weißabgleich steht *vor* der
Filmemulation — sonst verstärkt der Film-Look einen vorhandenen Farbstich mit, statt ihn
zu korrigieren. Und beurteilt wird in Node 2 in Rec.709, weil man Log-Bilder nicht
zuverlässig beurteilen kann.

⭐ **Harte Regel: LUTs nur für die objektiven Schritte.** Weißabgleich, Helligkeit,
Sättigung, Hautton, Farbstich — das gehört *immer* in Node 2 als regelbarer Wert,
**nie** in eine zusätzlich gebackene LUT. Eine LUT ist eine Blackbox; ein Regler lässt
sich zurückstellen. Begründung und Details: `referenzen/nodekette.md`.

## Schnellstart

```bash
py werkzeuge/luts_erzeugen.py
```
```bash
py werkzeuge/luts_installieren.py
```
```bash
py werkzeuge/look_anwenden.py --timeline "nah" --timeline "weit"
```

Das erste Skript rechnet alle LUTs selbst aus (rund eine Minute), das zweite legt sie in
den LUT-Ordner von Resolve, das dritte baut die Kette als **geteilte Farbgruppe** über
alle angegebenen Timelines.

Voraussetzung: `py -m pip install numpy colour-science` und in Resolve unter
*Einstellungen → System → Allgemein* das **externe Scripting** erlauben.

## Woher die LUTs kommen

Alle vier LUTs lassen sich mit den Skripten in `werkzeuge/` **selbst erzeugen** — es muss
nichts gekauft werden:

| Node | Skript | Grundlage |
|---|---|---|
| 1 | `lut_slog3_zu_arri_rec709.py` | rechnet S-Log3 → ARRI LogC und schickt das durch die ARRI-Wandlung, die in Resolve bereits enthalten ist |
| 3 | `lut_rec709_zu_arri_logc.py` | kehrt genau diese ARRI-Wandlung numerisch um (Newton-Verfahren) |
| 4 | `lut_filmemulation_negativ_print.py` | Modell aus Negativ-Dichtekurve, Schichtkopplung und Kopierfilm |
| 5 | `lut_kinolook_tealorange.py` | Kontrastkurve, Schwarzanhebung, Split-Tone, Entsättigung |

**Wer gekaufte LUT-Sätze besitzt, kann Node 3 und 4 dadurch ersetzen** — die kommerziellen
Filmemulationen sind aus echten Filmscans gemessen und in den Farben feiner. Welche Dateien
genau, mit welchen Einstellungen und wo es sie gibt: `referenzen/gekaufte-luts.md`.
Gemessener Unterschied zwischen freier und gekaufter Variante: `referenzen/messwerte.md`.

## Geteilte Nodes statt kopierter Grades

Die Kette gehört in eine **Farbgruppe**, nicht auf jeden Clip einzeln:

- **Gruppe „vor Clipbearbeitung"** → Node 1 (Log-Wandlung), für alle Kameras gemeinsam
- **Clip-Ebene** → Node 2 (Weißabgleich/Helligkeit), pro Kamera einzeln
- **Gruppe „nach Clipbearbeitung"** → Nodes 3–5, für alle Kameras gemeinsam

Eine Änderung am Look wirkt damit sofort auf alle Kameras, während der Weißabgleich je
Kamera unterschiedlich bleiben darf. Liegen die Kameras als **genestete Quell-Timelines**
im Schnitt, schlägt jede Änderung live bis in jeden einzelnen Schnitt durch — nichts ist
eingebacken. Das ist der wichtigste Punkt der ganzen Methode.

## Was das Skript kann und was nicht

| Aufgabe | Weg |
|---|---|
| LUTs erzeugen, installieren, anmelden | ✅ Skript |
| Farbgruppe anlegen, Clips zuordnen | ✅ Skript (`AddColorGroup`, `AssignToColorGroup`) |
| LUTs auf Nodes setzen | ✅ Skript (`SetLUT`) |
| **Nodes anlegen** | ❌ die Resolve-API hat kein `AddNode` — einmal **Alt+S** in der GUI |
| Nodes beschriften | ❌ nur per Doppelklick in der GUI |
| LUT-Interpolation auf tetraedrisch | ❌ nicht in der API — einmal in den Projekteinstellungen |
| „heller oder dunkler?" | ❌ Mensch |

`py werkzeuge/look_anwenden.py --pruefen` zeigt, was gerade auf welchem Node liegt,
ohne etwas zu ändern.

## Weiterlesen

- `referenzen/nodekette.md` — warum die Reihenfolge so ist, Werte für Node 2
- `referenzen/gekaufte-luts.md` — kommerzielle Alternativen, Einstellungen, Bezug
- `referenzen/messwerte.md` — gemessene Kurven, frei gegen gekauft
- `referenzen/fallstricke.md` — was in der Praxis schiefgeht
- `praesentation/` — der ganze Ablauf grafisch erklärt
