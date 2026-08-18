# Die Node-Kette im Einzelnen

## Warum überhaupt fünf Nodes?

Man könnte denselben Look in eine einzige LUT backen. Genau das ist das Problem: Eine LUT
ist eine Blackbox. Wenn das Bild danach „irgendwie komisch" aussieht, lässt sich nicht
mehr sagen, welcher Schritt schuld war, und nichts einzeln zurückstellen.

Die Kette trennt deshalb **objektiv** von **subjektiv**:

- **Objektiv** (Nodes 1, 3, 4, 5): Wandlungen und der Look. Die ändern sich innerhalb
  eines Projekts nicht. Als LUT völlig richtig aufgehoben.
- **Subjektiv** (Node 2): Weißabgleich, Helligkeit, Kontrast. Das ändert sich pro Kamera,
  pro Location, manchmal pro Clip. Muss regelbar bleiben.

## Node 1 — Log → ARRI Rec.709

Sony-Material in S-Log3/S-Gamut3.Cine ist flach und entsättigt; darin lässt sich nichts
beurteilen. Die naheliegende Lösung wäre Sonys eigene Rec.709-LUT — die sieht aber
technisch und hart aus.

Stattdessen: das Bild rechnerisch nach **ARRI LogC3 / ARRI Wide Gamut 3** bringen und
dann durch **ARRIs eigene Rec.709-Wiedergabe** schicken. ARRIs Farbwiedergabe gilt als
Referenz für angenehme Hauttöne — Hauttöne bleiben warm statt ins Orange oder Magenta zu
kippen, und die Lichter laufen weich aus.

Diese LUT ist eine **reine Wandlung**: kein Farbstich, keine Helligkeitsanhebung, keine
Sättigungsänderung. Alles Kreative kommt später.

> Andere Kameras: Das Skript `lut_slog3_zu_arri_rec709.py` lässt sich auf jedes
> Log-Format umstellen, für das `colour-science` einen Dekoder hat (S-Log2, V-Log,
> C-Log, Log3G10 …) — nur die Zeile mit `log_decoding_…` und den Quellfarbraum tauschen.

## Node 2 — Weißabgleich und Helligkeit (der einzige regelbare Node)

Hier passiert alles, was von Motiv und Kamera abhängt:

| Regler | Wofür | Anhaltspunkt |
|---|---|---|
| **Temperatur** | Kameras aneinander angleichen, Kunstlicht neutralisieren | Schritte von 100–200 sind meist schon deutlich sichtbar |
| **Tönung** | Grün-/Magentastich von Leuchtstoff- und LED-Licht | klein halten, ±10 |
| **Gamma / Mitteltöne** | Gesamthelligkeit | Helligkeit **hier** machen, nicht über Gain |
| **Gain** | nur wenn die Lichter wirklich zu dunkel sind | vorsichtig, brennt schnell aus |
| **Kontrast / Drehpunkt** | Grundkontrast | die Filmemulation bringt schon reichlich Kontrast mit |

**Warum Gamma und nicht Gain?** Gain zieht die Lichter mit hoch — bei einem Gesicht im
Scheinwerferlicht ist die Stirn dann sofort ausgebrannt. Gamma hebt die Mitteltöne, wo
das Gesicht liegt, und lässt die Lichter, wo sie sind.

**Warum steht dieser Node vor der Filmemulation?** Weil eine Film-LUT einen Farbstich
nicht ausgleicht, sondern durchreicht und verstärkt. Erst neutral machen, dann den Look
darauf setzen.

**Mehrkamera:** Node 2 liegt auf der Clip-Ebene und ist damit pro Kamera unterschiedlich —
genau richtig, denn zwei Kameras auf dieselbe Bühne haben fast nie dieselbe Farbtemperatur.
Alle anderen Nodes liegen in der Gruppe und sind für alle Kameras identisch.

## Node 3 — Rec.709 → ARRI LogC

Ein technischer Zwischenschritt, der oft falsch gemacht wird.

Filmemulations-LUTs der Alexa-Familie erwarten **LogC am Eingang**. Nach Node 1 und 2
liegt aber Rec.709 vor. Also muss das Bild zurück ins Log-Format.

⚠ **Nicht** über einen Color-Space-Transform „Rec.709 → ARRI LogC3" machen. Der legt das
Material rund zwei Blenden unter den Arbeitspunkt, den die Film-LUTs erwarten; das Bild
wird dunkel und flau, und Gegensteuern per Offset passt dann immer nur an einer Stelle.
Richtig ist eine Wandlung, die exakt die Umkehrung der Rec.709-Wiedergabe aus Node 1 ist —
`lut_rec709_zu_arri_logc.py` rechnet genau diese Umkehrung aus.

## Node 4 — Filmemulation

Das Herz des Looks. Was ein Filmbild ausmacht, sind drei Eigenschaften, die eine reine
Kontrastkurve nicht hat:

1. **Schwarz läuft nicht zu.** Film hat einen Kurvenfuß — die tiefsten Töne werden flacher,
   aber nie zu einem toten Schwarz.
2. **Lichter brennen nicht ab.** Die Schulter der Kurve komprimiert helle Stellen weich,
   statt sie abzuschneiden.
3. **Farben verschieben sich in den Extremen.** Die drei Schichten eines Farbnegativs haben
   leicht unterschiedliche Steilheiten und beeinflussen sich gegenseitig. Deshalb sind
   Schatten und Lichter auf Film nie exakt gleich getönt.

Die freie Emulation (`lut_filmemulation_negativ_print.py`) rechnet diesen Weg nach:
Belichtung → Negativdichte → Schichtkopplung → Kopierfilm → Durchlässigkeit. Ein
Neutral-Abgleich sorgt dafür, dass ein grauer Keil exakt grau bleibt, während farbige
Bildstellen ihren Filmcharakter behalten.

## Node 5 — Kino-Look

Zum Schluss der Feinschliff, bewusst zurückhaltend, weil Node 4 schon den Großteil macht:
weiche Kontrastkurve um Mittelgrau, angehobene Schwarzwerte, Split-Tone (Schatten Richtung
Teal, Lichter Richtung Warm), leichte Entsättigung.

Drei Stärken stehen zur Wahl: `leicht`, `mittel`, `stark`. Bei Vorträgen und Interviews mit
Hautton im Bild ist `mittel` meist der Punkt, an dem es „nach Film" aussieht, ohne dass das
Gesicht verfärbt wirkt. Die Stärke zu wechseln ist erlaubt — das ist die Look-LUT selbst
und keine versteckte Korrektur.

## Die Aufteilung auf Farbgruppe und Clip-Ebene

```
Farbgruppe "vor Clipbearbeitung"   Node 1   Log -> ARRI Rec.709        geteilt
        |
Clip-Ebene (je Kamera)             Node 1   Weissabgleich, Helligkeit  einzeln
        |
Farbgruppe "nach Clipbearbeitung"  Node 1   Rec.709 -> ARRI LogC       geteilt
                                   Node 2   Filmemulation              geteilt
                                   Node 3   Kino-Look                  geteilt
```

Bei genesteten Quell-Timelines (eine Timeline je Kamera, die im Schnitt als Clip liegt)
wirkt eine Änderung an der Gruppe **live in jedem Schnitt** dieser Kamera. Nichts wird
eingebacken, nichts muss nachträglich verteilt werden. Das ist der praktische Gewinn
gegenüber „Grade auf alle Clips kopieren".
