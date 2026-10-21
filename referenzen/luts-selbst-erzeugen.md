# LUTs selbst erzeugen — Node 3 (Rec.709 → ARRI LogC), Fassung 2

`werkzeuge/lut_rec709_zu_arri_logc_v2.py` erzeugt `ARRI_Rec709_zu_LogC_v2.cube`.
Aufruf wie beim alten Werkzeug:

```bash
py werkzeuge/lut_rec709_zu_arri_logc_v2.py [--dat <pfad>] [--out <pfad>] [--size 33]
```

Grundlage ist ARRIs eigene Rec.709-Wiedergabe (`Arri Alexa LogC to Rec709.dat` aus der
Resolve-Installation). Die Datei wird nur gelesen und nie weitergegeben.

## Warum eine Fassung 2

Die alte LUT (`lut_rec709_zu_arri_logc.py` → `ARRI_Rec709_zu_LogC.cube`) kehrt ARRIs
3D-Wandlung Punkt für Punkt per Newton-Verfahren um. ARRIs Wiedergabe ist in den Lichtern
sehr flach und an den Farbraumrändern beschnitten — dort findet die Suche keinen Weg und
bleibt beim Startwert stehen. Ab etwa 85 % im Rotkanal gibt die alte LUT praktisch den
Eingangswert zurück (Rec.709 0,86 → LogC 0,86 statt 0,62). Nach der Filmemulation springt
helle Haut dadurch schlagartig nach Lachsrot.

## Rechenweg der Fassung 2

Statt punktweise zu suchen, wird ein **analytisches, monotones Modell** der ARRI-Wiedergabe
aufgestellt und exakt umgekehrt:

```
vorwärts:   LogC3 (AWG3, EI 800) → 3×3-Matrix → Tonwertkurve je Kanal → Rec.709
Umkehrung:  Rec.709 → inverse Tonwertkurve je Kanal → inverse Matrix → LogC3 (≥ 0)
```

- **Tonwertkurve** — aus der Grauachse der ARRI-Datei gelesen, streng monoton erzwungen,
  glatt verbunden (monotone kubische Hermite-Interpolation), außerhalb linear fortgesetzt.
  Damit ist die Grauachse exakt.
- **Matrix** — per kleinster Quadrate an die ARRI-Datei gefittet (nur unbeschnittene
  Stützstellen), jede Zeile mit Summe 1, damit Grau Grau bleibt.
- **Wo wirkt die Matrix?** Voreinstellung `--modell log`: auf den LogC-Werten. Gemessen
  trifft das ARRIs Wiedergabe in Lichtern und kräftigen Farben deutlich besser als die
  klassische lineare Matrix (ARRI dämpft die Sättigung dort). `--modell linear` (Matrix auf
  linearem Licht, wahlweise `--matrix standard` = AWG3 → Rec.709) bleibt zum Vergleich.
- Eingänge werden auf 0–1 beschnitten, negative Werte nach der Matrix auf 0 geklemmt —
  keine ungültigen Werte möglich.

Jeder Schritt ist monoton und stetig, die LUT kann deshalb nicht springen.

## Prüfwerte (rein rechnerisch, ohne Resolve)

**Modellgüte** — Modell gegen ARRI-Datei, größter Kanalfehler, Mittel / 95 %:

| Modell | Grauachse | unbeschnittene Stützstellen | Mitten (< 0,8) |
|---|---|---|---|
| Matrix auf LogC, gefittet (Voreinstellung) | 0,0000 | 0,045 / 0,143 | 0,039 / 0,107 |
| Matrix linear, gefittet | 0,0000 | 0,105 / 0,465 | 0,037 / 0,160 |
| Matrix linear, Standard AWG3 → Rec.709 | 0,0000 | 0,121 / 0,459 | 0,048 / 0,178 |

**Rundreise** ARRI(LUT(x)) − x über rund 5000 Rec.709-Farben (Haut, Graukeil, gesättigte
Farben), größter Kanalfehler, Mittel / 95 %:

| | Mitten (< 0,8) alt | Mitten v2 | Lichter (≥ 0,8) alt | Lichter v2 |
|---|---|---|---|---|
| alle Farben | 0,036 / 0,240 | **0,023 / 0,094** | 0,119 / 0,360 | **0,059 / 0,209** |
| Haut | 0,023 / 0,225 | **0,009 / 0,021** | 0,086 / 0,175 | **0,033 / 0,075** |
| Grau | 0,000 / 0,001 | 0,001 / 0,002 | 0,001 / 0,004 | 0,001 / 0,004 |
| gesättigt | 0,056 / 0,250 | **0,045 / 0,143** | 0,163 / 0,380 | **0,093 / 0,287** |

**Haut-Rampe** — Rec.709 0,86 / 0,68 / 0,58 von 0,5× bis 1,2× (auf 1 beschnitten), durch
Node 3 und danach durch `Filmemulation_Negativ_Print_ARRI_LogC.cube`; Farbton in Grad,
Sättigung (HSV):

| Faktor | alt | v2 |
|---|---|---|
| 0,50 | 20,7° / 0,26 | 22,6° / 0,27 |
| 0,70 | 20,4° / 0,31 | 22,4° / 0,32 |
| 0,80 | 20,6° / 0,32 | 22,7° / 0,33 |
| 0,85 | **11,9° / 0,46** | 23,1° / 0,33 |
| 0,90 | **8,7° / 0,55** | 23,3° / 0,34 |
| 1,00 | **9,4° / 0,52** | 23,7° / 0,34 |
| 1,10 | 10,5° / 0,48 | 22,9° / 0,37 |
| 1,20 | 12,6° / 0,43 | 23,5° / 0,42 |

Alt springt zwischen 0,80 und 0,85 um 9° nach Rot (größter Sprung je 0,005-Schritt 4,1°);
v2 bleibt über die ganze Rampe zwischen 21,8° und 23,8° (größter Sprung 0,4°). Dass die
Sättigung bei v2 ganz oben steigt, liegt am bereits beschnittenen Rotkanal des Eingangs —
dort ist die Information verloren, das kann keine Rückwandlung zurückholen.

**Monotonie** — v2 steigt entlang der Grauachse (fein abgetastet, tetraedrisch) und je
Kanal (Rot-Eingang → Rot-Ausgang usw.) an jeder Stelle des Gitters; keine ungültigen Werte.
