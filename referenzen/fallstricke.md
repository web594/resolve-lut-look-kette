# Fallstricke

Alles hier ist in der Praxis schon einmal schiefgegangen.

## LUTs und Farbwissenschaft

**Nicht per Color-Space-Transform nach LogC wandeln.**
Der naheliegende Weg für Node 3 wäre ein CST „Rec.709 / Gamma 2.2 → ARRI Wide Gamut 3 /
ARRI LogC3". Der legt das Material rund zwei Blenden unter den Arbeitspunkt, den die
Film-LUTs erwarten — gemessen landete ein Hautton bei 28 % statt bei etwa 45 % LogC.
Ergebnis: dunkel und flau. Die Tone-Mapping-Einstellung im CST ändert daran nichts
(geprüft: „DaVinci" gegen „Ohne" praktisch identisch). Gegensteuern per Offset ist eine
Krücke, die nur an einer Stelle der Timeline passt.

**Nach der Film-LUT kommt kein Rück-Transform nach Rec.709.** Die Filmemulation wandelt
selbst. Ein zusätzlicher CST danach macht das Bild flau.

**LUT-Interpolation auf tetraedrisch stellen.** In den Projekteinstellungen unter
*Farbmanagement*. Auf der Voreinstellung „trilinear" entstehen in weichen Verläufen
sichtbare Stufen. Nicht über die API erreichbar — einmal von Hand.

**Projekt auf DaVinci YRGB, nicht Color Managed.** Unter Color Management würde Resolve
das Bild vor Node 1 bereits transformieren; die Log-Wandlung bekäme dann kein Log mehr,
und der ganze Aufbau kippt.

## Resolve-API

**Die API kann keine Nodes anlegen.** Es gibt kein `AddNode`. Nodes entstehen per
**Alt+S** in der GUI (oder indem ein fertiger Grade aus einem DRX geladen wird). Erst
danach lassen sich LUTs per `SetLUT(index, pfad)` setzen.

**`SetLUT` findet nur LUTs, die Resolve schon kennt.** Nach dem Kopieren neuer
`.cube`-Dateien einmal `projekt.RefreshLUTList()` aufrufen — sonst schlägt `SetLUT`
kommentarlos fehl und liefert `False`. `luts_installieren.py` macht das automatisch.

**Nodes lassen sich per Skript nicht beschriften.** `SetNodeLabel` existiert nicht.
Beschriftung geht nur per Doppelklick auf den Node-Namen — Kosmetik, aber bei fünf
Nodes hilfreich.

**`proj.SetCurrentTimeline()` setzt die Farbansicht auf die Clip-Ebene zurück.** Danach
in der GUI wieder auf die gewünschte Node-Ebene umschalten.

**Neu angelegte Nodes werden unaufgeräumt platziert** und sehen unverbunden aus. Sie sind
es nicht — nicht „reparieren" wollen.

## Farbgruppen

**Ein Node im Gruppen-Graph wirkt auf alle zugeordneten Clips — auch dort, wo man ihn
nicht haben will.** Das ist der Sinn der Sache, wird aber zur Falle, sobald ein Eingriff
motivabhängig ist: Ein Power Window oder ein Qualifizierer in der Gruppe steht bei jeder
Kamera an derselben Bildstelle. Solche Eingriffe gehören auf die **Clip-Ebene**.

**Beim Zuordnen zur Gruppe bleiben vorhandene Clip-Grades bestehen** und addieren sich
zum Gruppen-Look. Wenn vorher schon gegradet wurde, mit
`look_anwenden.py --clipgrades-loeschen` aufräumen — aber vorher prüfen, ob dort nicht
doch der Weißabgleich steckt, den man behalten will.

**Geteilte Nodes sind gegen versehentliches Ändern gesperrt.** Wer an einem geteilten
Node etwas ändern will, muss das bewusst tun — das ist Absicht, wirkt aber beim ersten
Mal wie ein Fehler.

## Beurteilen

**Exportierte Einzelbilder sind dunkler als der Viewer.** Den Look immer am Viewer
beurteilen, nicht an einem herausgerechneten PNG.

**Bei mehrteiligem Material den Frame aus der Mitte nehmen.** Der Anfang eines Clips ist
oft noch Aufbau, Einlauf oder wechselndes Licht.

**Vor dem Eintippen von Zahlenwerten prüfen, welches Feld aktiv ist.** In der
Farbpalette liegen Master, Rot, Grün und Blau nebeneinander; ein Zahlenwert im falschen
Feld erzeugt einen Farbstich, den man später lange sucht. Im Zweifel an einem Farbstreifen
gegenprüfen, welches Feld welchen Kanal bedient.

## Rechenzeit

Die LUT-Erzeugung dauert je nach Rechner etwa eine halbe bis zwei Minuten — den größten
Anteil hat die numerische Umkehrung in `lut_rec709_zu_arri_logc.py` (Newton-Verfahren
über 35 937 Gitterpunkte). Eine feinere LUT (`--size 65`) dauert rund achtmal so lange
und bringt sichtbar nichts, solange die Interpolation auf tetraedrisch steht.
