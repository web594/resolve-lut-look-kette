# Messwerte

Alle Zahlen sind Codewerte 0–1. Gemessen wurde rechnerisch auf den LUT-Daten, nicht am
Bildschirm — die Werte sind damit reproduzierbar und unabhängig von der Monitorkalibrierung.

Als Vergleichsmaßstab dient ein kommerzieller Satz (ImpulZ Ultimate, Alexa-Filmemulation
`Kodak Vis3 500T 5219 (NEG)_FPE` mit der zugehörigen Rec.709→LogC-Wandlung). Die
kommerziellen Dateien liegen dem Repository nicht bei; hier stehen nur Messergebnisse.

## Node 1 — Log-Wandlung, Kontrollwert

18-%-Grau (Szenenreflexion 0,18) durchläuft die Kette so:

```
S-Log3-Codewert  ->  ARRI LogC3 0,391  ->  Rec.709 0,398
```

Der ARRI-Referenzwert für LogC-Mittelgrau liegt bei 0,391 — die Wandlung sitzt also
exakt. Das Skript gibt diesen Kontrollwert bei jedem Lauf mit aus.

## Node 3 — Rec.709 → LogC, frei gegen gekauft

> Die Tabelle unten stammt von der **alten** freien Fassung (`ARRI_Rec709_zu_LogC.cube`,
> Newton-Umkehrung). Sie ist auf der Grauachse genau, kippt aber helle Haut nach Rot.
> Messwerte der stabilen Fassung 2 und der Vergleich alt gegen v2 stehen in
> `luts-selbst-erzeugen.md`.

Graukeil, Eingang Rec.709:

| Rec.709 ein | frei erzeugt | gekauft | Abweichung |
|---|---|---|---|
| 0,1 | 0,1849 | 0,1449 | −0,0400 |
| 0,2 | 0,2794 | 0,2749 | −0,0046 |
| 0,3 | 0,3394 | 0,3427 | +0,0034 |
| 0,4 | 0,3919 | 0,3938 | +0,0018 |
| 0,5 | 0,4434 | 0,4467 | +0,0033 |
| 0,6 | 0,4961 | 0,5003 | +0,0042 |
| 0,7 | 0,5502 | 0,5541 | +0,0039 |
| 0,8 | 0,6069 | 0,6165 | +0,0096 |
| 0,9 | 0,6799 | 0,7742 | +0,0942 |
| 1,0 | 1,0000 | 0,9176 | −0,0824 |

**Lesart:** Von 0,2 bis 0,8 — also über den gesamten Bereich, in dem Gesichter, Kleidung
und normal belichtete Hintergründe liegen — stimmen beide auf unter einen Prozentpunkt
überein. Auseinander gehen sie nur an den Rändern: Die gekaufte Wandlung hat eine eigene
Lichter-Rolloff-Kurve, die freie ist an dieser Stelle die mathematisch exakte Umkehrung
der ARRI-Wiedergabe.

Über 30 000 realistische Motivfarben (schwach gesättigt, Helligkeit 0,1–0,85):
**mittlere Abweichung 0,015, Median 0,008, 95-%-Wert 0,058.**

### Grenze des Verfahrens

Die ARRI-Rec.709-Wiedergabe wirft in stark gesättigten Bereichen Information weg
(mehrere LogC-Farben landen auf derselben Rec.709-Farbe). Diese Information kann
**keine** Rückwandlung wiederherstellen — auch keine gekaufte. Praktisch heißt das:
Kräftig gesättigtes Bühnenlicht kommt nach der Rückwandlung nicht exakt wieder dort
an, wo es herkam. Bei normalem Licht spielt das keine Rolle.

## Node 4 — Filmemulation, frei gegen gekauft

Graukeil, Eingang ARRI LogC, Ausgabe R/G/B:

| LogC ein | frei erzeugt | gekauft |
|---|---|---|
| 0,1 | 0,040 / 0,040 / 0,040 | 0,044 / 0,044 / 0,043 |
| 0,2 | 0,103 / 0,103 / 0,103 | 0,082 / 0,083 / 0,083 |
| 0,3 | 0,185 / 0,185 / 0,185 | 0,173 / 0,167 / 0,172 |
| 0,4 | 0,308 / 0,308 / 0,308 | 0,333 / 0,313 / 0,301 |
| 0,5 | 0,470 / 0,470 / 0,470 | 0,493 / 0,474 / 0,451 |
| 0,6 | 0,640 / 0,638 / 0,636 | 0,638 / 0,622 / 0,596 |
| 0,7 | 0,778 / 0,773 / 0,768 | 0,770 / 0,746 / 0,728 |
| 0,8 | 0,871 / 0,863 / 0,854 | 0,858 / 0,827 / 0,809 |
| 0,9 | 0,926 / 0,916 / 0,905 | 0,901 / 0,863 / 0,851 |
| 1,0 | 0,958 / 0,946 / 0,933 | 0,916 / 0,879 / 0,867 |

**Lesart:** Die Tonwertkurven laufen nahezu deckungsgleich — beide haben angehobenes
Filmschwarz (kein Wert bei 0) und eine weiche Schulter (kein Wert bei 1,0). Der
Unterschied liegt in der Farbe: Die gekaufte Emulation ist über den ganzen Verlauf
wärmer, die freie ist bis in die Mitteltöne exakt neutral und wird erst in den Lichtern
leicht warm (Parameter `WAERME_LICHTER`, Voreinstellung 0,015).

Über dieselben 30 000 Motivfarben: **mittlere Abweichung 0,050, Median 0,037.**

## Node 3 + 4 zusammen

Eingang Rec.709 (also nach den Nodes 1 und 2), Ausgabe nach der Filmemulation:

| Rec.709 ein | freie Kette | gekaufte Kette |
|---|---|---|
| 0,3 | 0,228 | 0,238 / 0,225 / 0,224 |
| 0,5 | 0,375 | 0,408 / 0,387 / 0,369 |
| 0,7 | 0,556 | 0,579 / 0,559 / 0,532 |
| 0,9 | 0,754 | 0,835 / 0,805 / 0,787 |

Hautton (Rec.709-Eingang 0,55 / 0,42 / 0,35):

```
freie Kette      0,390 / 0,303 / 0,261
gekaufte Kette   0,496 / 0,366 / 0,294
```

**Das ist der einzige praktisch relevante Unterschied:** Die freie Kette rendert
Hauttöne rund 10 Prozentpunkte dunkler und deutlich neutraler. Ausgleich in Node 2 —
genau dafür ist er da:

- **Gamma / Mitteltöne leicht anheben** (Größenordnung +0,08 bis +0,12)
- **Temperatur etwas wärmer** (Größenordnung +100 bis +200)

Danach liegen beide Ketten im Gesicht dicht beieinander. Über alle 30 000 Motivfarben
beträgt der Abstand der kompletten Ketten **im Mittel 0,040, im Median 0,032.**

## Wie diese Werte entstanden sind

Die Vergleichszahlen stammen aus einem Messskript, das beide LUT-Ketten auf denselben
Eingangswerten auswertet: Graukeil in Zehntelschritten sowie 30 000 zufällige, schwach
gesättigte Farben im Helligkeitsbereich 0,1–0,85 (typisch für Innenaufnahmen mit
Gesichtern). Die kommerziellen LUTs werden dabei nur gelesen — es fließen keine ihrer
Daten in die erzeugten LUTs ein.
