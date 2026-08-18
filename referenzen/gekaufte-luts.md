# Gekaufte LUT-Sätze als Alternative zu Node 3 und 4

Die Kette läuft vollständig mit den selbst erzeugten LUTs aus `werkzeuge/`. Wer mehr
Feinheit in den Farben will, kann **Node 3 und Node 4** durch einen gekauften Satz
ersetzen. Node 1 (Log-Wandlung) und Node 5 (Kino-Look) bleiben in jedem Fall die
selbst erzeugten.

Kommerzielle LUT-Dateien werden in diesem Repository **nicht mitgeliefert** — sie
gehören ihren Herstellern. Hier steht nur, welche Datei an welche Stelle gehört.

## ImpulZ (VisionColor)

Der Satz, für den diese Kette ursprünglich gebaut wurde. Filmemulationen aus echten
Scans belichteter Filmbestände, sortiert nach Kamera und Log-Format.

**Bezug:** visioncolor.com → ImpulZ Ultimate. Einmalzahlung im Bereich von rund 90–100 €
(Stand 2026), keine Abogebühr. Es gibt auch kleinere Pakete; gebraucht wird der
Alexa-Satz plus die Cineon-Wandlungen.

### Node 3 — Rec.709 → LogC

```
28 ImpulZ - Cineon Conversions/Alexa Rec709 to LOG-C_Impulz.cube
```

Diese Wandlung ist auf die ImpulZ-Filmstocks abgestimmt: danach sitzt der Look **ohne
jede Belichtungskorrektur** richtig. Genau deshalb sollte man sie nehmen, wenn man den
Satz besitzt — und keinesfalls durch einen Color-Space-Transform ersetzen
(siehe `nodekette.md`, Node 3).

### Node 4 — Filmemulation

```
05 ImpulZ - Arri Alexa LOG-C/Alexa_<Filmbestand>_<Variante>.cube
```

**Filmbestand.** Für ein warmes, weiches Kinobild ist `Kodak Vis3 500T 5219 (NEG)` die
naheliegende Wahl — der meistgedrehte Negativbestand der letzten Jahre. Kühler und
grünlicher wird es mit den Fuji-Beständen, kräftiger und gesättigter mit `Kodak Ektar 100`.

⚠ Der Filmbestand muss zur Kamera passen. Bei Consumer-Camcordern mit fertigem
Rec.709-Bild (kein Log) wirken viele Emulationen auf Standardstärke unnatürlich — dort
die Intensität deutlich zurücknehmen oder bei der frei gerechneten Emulation bleiben.

**Variante (Namenssuffix).** Zu jedem Bestand gibt es vier:

| Suffix | Bedeutung | Wirkung |
|---|---|---|
| `_FPE` | Film Print Emulation | Negativ **plus** Kopierfilm — der klassische Kinoaufbau, hier die Empfehlung |
| `_CIN` | Cineon | milder, flacher, mehr Reserve für eigene Korrekturen |
| `_FC` | Film Contrast | kontrastiger |
| `_VS` | VisionSpace | eigenständiger, kräftigerer Farbraum |

**Nach der Film-LUT kommt kein Rück-Transform nach Rec.709** — die LUT wandelt selbst.

### Reihenfolge bleibt gleich

```
Node 1  Sony_SLog3_zu_ARRI_Rec709.cube               (selbst erzeugt)
Node 2  Weissabgleich + Helligkeit                   (regelbar, keine LUT)
Node 3  Alexa Rec709 to LOG-C_Impulz.cube            (gekauft)
Node 4  Alexa_Kodak Vis3 500T 5219 (NEG)_FPE.cube    (gekauft)
Node 5  Kinolook_Kontrast_TealOrange_mittel.cube     (selbst erzeugt)
```

Umstellen im Skript:

```bash
py werkzeuge/look_anwenden.py --timeline "nah" --timeline "weit" --lut-logc "ImpulZ/28 ImpulZ - Cineon Conversions/Alexa Rec709 to LOG-C_Impulz.cube" --lut-film "ImpulZ/05 ImpulZ - Arri Alexa LOG-C/Alexa_Kodak Vis3 500T 5219 (NEG)_FPE.cube"
```

Die Pfade sind relativ zum LUT-Ordner von Resolve; dorthin gehört der ImpulZ-Ordner
kopiert, danach in Resolve die LUT-Liste aktualisieren.

## Weitere Sätze

Die Kette ist nicht an einen Hersteller gebunden. Jeder Satz funktioniert, der eine
**Rec.709 → LogC**-Wandlung und **LogC-Filmemulationen** mitbringt — etwa FilmConvert
Nitrate (arbeitet als Plugin statt als LUT und ersetzt dann die Nodes 3 und 4 gemeinsam)
oder LUT-Pakete mit Kodak-2383-Kopierfilm-Emulation.

Wichtig ist nur: **Eingangsformat der Film-LUT und Ausgang von Node 3 müssen
zusammenpassen.** Erwartet die Film-LUT Cineon statt LogC, muss Node 3 nach Cineon
wandeln, nicht nach LogC.

## Was sich der Kauf lohnt — und was nicht

Gemessen (siehe `messwerte.md`) liegen freie und gekaufte Variante über den ganzen
Mittelton-Bereich um wenige Prozent auseinander. Die Unterschiede stecken in den
Lichtern und in kräftigen Farben.

- **Lohnt sich**, wenn ein bestimmter Filmbestand gefragt ist, wenn viel gesättigtes
  Bühnenlicht im Bild ist oder wenn der Look zu einem bestehenden Projekt passen muss.
- **Lohnt sich nicht** für Vorträge, Interviews und Veranstaltungen in normalem Licht —
  dort ist der sichtbare Unterschied kleiner als der Einfluss des Weißabgleichs in Node 2.
