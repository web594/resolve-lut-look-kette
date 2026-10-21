# Film-Look als LUT-Kette für DaVinci Resolve

Ein nachvollziehbarer Kino-Look für Log-Material: **vier LUT-Nodes für die objektiven
Schritte, ein regelbarer Node für Weißabgleich und Helligkeit.** Dazu Skripte, die alle
LUTs selbst erzeugen und die Kette als geteilte Farbgruppe über beliebig viele Kameras
anlegen.

Entstanden bei der Arbeit an Mehrkamera-Mitschnitten von Vorträgen und Interviews
(Sony S-Log3 / S-Gamut3.Cine), nutzbar für jedes Log-Material.

```
Node 1   Log  ->  ARRI Rec.709          LUT        geteilt
Node 2   Weissabgleich + Helligkeit     regelbar   pro Kamera
Node 3   Rec.709  ->  ARRI LogC         LUT        geteilt
Node 4   Filmemulation (Negativ+Print)  LUT        geteilt
Node 5   Kino-Look (Teal/Orange)        LUT        geteilt
```

## Der Grundgedanke

**Was objektiv ist, darf eine LUT sein. Was subjektiv ist, muss ein Regler bleiben.**

Farbwandlungen und der Look ändern sich innerhalb eines Projekts nicht — als LUT gut
aufgehoben. Weißabgleich, Helligkeit und Kontrast ändern sich dagegen pro Kamera und pro
Situation. Wer sie mit in eine LUT backt, kann sie nicht mehr einzeln zurückstellen und
weiß später nicht mehr, was das Bild eigentlich vom Original entfernt hat.

Der zweite Gedanke: **Die Reihenfolge entscheidet.** Der Weißabgleich steht vor der
Filmemulation, weil eine Film-LUT einen Farbstich nicht ausgleicht, sondern verstärkt.

## Schnellstart

```bash
py -m pip install numpy colour-science
```
```bash
py werkzeuge/luts_erzeugen.py
```
```bash
py werkzeuge/luts_installieren.py
```
```bash
py werkzeuge/look_anwenden.py --timeline "nah" --timeline "weit"
```

In Resolve muss unter *Einstellungen → System → Allgemein* das externe Scripting erlaubt
sein. Die drei Nodes im Gruppen-Graph „nach Clipbearbeitung" werden einmalig mit **Alt+S**
angelegt — die Resolve-API kann keine Nodes erzeugen; das Skript sagt genau, wann.

## Inhalt

| Ordner | Inhalt |
|---|---|
| `SKILL.md` | die Kurzfassung als Claude-Skill |
| `referenzen/nodekette.md` | warum die Reihenfolge so ist, Werte für Node 2 |
| `referenzen/gekaufte-luts.md` | kommerzielle Alternativen, Einstellungen, Bezugsquellen |
| `referenzen/messwerte.md` | gemessene Kurven, frei gegen gekauft |
| `referenzen/luts-selbst-erzeugen.md` | wie die Node-3-LUT (Fassung 2) gerechnet wird, Prüfwerte |
| `referenzen/fallstricke.md` | was in der Praxis schiefgeht |
| `werkzeuge/` | LUT-Erzeugung, Installation, Anwendung per Resolve-API |
| `luts/` | die fertig erzeugten LUTs für Node 4 und 5 |
| `praesentation/` | der ganze Ablauf grafisch erklärt (PDF) |

## Zu den LUT-Dateien

Alle LUTs dieser Kette lassen sich mit den beiliegenden Skripten selbst erzeugen — es
muss nichts gekauft werden.

- **Im Repository liegen** die LUTs für Node 4 (Filmemulation) und Node 5 (Kino-Look).
  Sie sind vollständig gerechnet; es stecken keine fremden LUT-Daten darin.
- **Nicht im Repository liegen** die LUTs für Node 1 und 3. Sie werden aus der
  ARRI-Farbwandlung abgeleitet, die DaVinci Resolve bereits mitbringt — diese Datei
  gehört ihren Rechteinhabern und wird hier nicht weitergegeben. `luts_erzeugen.py`
  rechnet beide LUTs in Sekunden aus der lokalen Resolve-Installation.
- **Node 3 heißt seit Fassung 2 `ARRI_Rec709_zu_LogC_v2.cube`** (Werkzeug
  `lut_rec709_zu_arri_logc_v2.py`). Die alte `ARRI_Rec709_zu_LogC.cube` aus
  `lut_rec709_zu_arri_logc.py` ist instabil bei heller Haut (kippt nach Lachsrot) und
  bleibt nur für bestehende Projekte erhalten.
- **Kommerzielle LUT-Sätze** sind hier ebenfalls nicht enthalten. Wer einen besitzt, kann
  damit die Nodes 3 und 4 ersetzen; welche Datei wohin gehört, steht in
  `referenzen/gekaufte-luts.md`.

## Als Claude-Skill verwenden

Repository nach `~/.claude/skills/resolve-lut-look-kette` klonen (unter Windows nach
`%USERPROFILE%\.claude\skills\resolve-lut-look-kette`). Claude Code liest `SKILL.md`
dann automatisch, sobald es um Film-Look, Grading-Ketten oder LUTs geht.

## Lizenz

MIT — siehe `LICENSE`. Gilt für Skripte, Texte und die in `luts/` enthaltenen,
selbst gerechneten LUT-Dateien.

## Kontakt

Entstanden in der Praxis bei [wunder-media.de](https://wunder-media.de) — Film und
Livestream für Veranstaltungen. Rückmeldungen und Verbesserungen gern per Issue oder an
web@wunder-media.de.
