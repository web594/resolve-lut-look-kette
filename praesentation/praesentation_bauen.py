# -*- coding: utf-8 -*-
"""Baut praesentation.html - alle Diagramme werden aus den echten LUT-Daten gerechnet.

Aufruf:  py praesentation_bauen.py
Danach:  chrome --headless=new --no-pdf-header-footer --print-to-pdf=Film-Look-LUT-Kette.pdf praesentation.html
"""
import os
import sys

import numpy as np

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(HIER)
sys.path.insert(0, os.path.join(WURZEL, "werkzeuge"))

from lut_filmemulation_negativ_print import film                 # noqa: E402
from lut_kinolook_tealorange import kinolook, STUFEN            # noqa: E402

BREITE, HOEHE = 1000, 460          # Zeichenflaeche der Diagramme


# ---------------------------------------------------------------- Hilfsmittel
def hex_von(rgb):
    v = np.clip(np.asarray(rgb, float), 0, 1)
    return "#%02x%02x%02x" % tuple(int(round(c * 255)) for c in v)


def pfad(punkte):
    return "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in punkte)


def achsen(x0, y0, b, h, xlabel, ylabel, striche=5):
    t = [f'<rect x="{x0}" y="{y0}" width="{b}" height="{h}" class="feld"/>']
    for i in range(striche + 1):
        x = x0 + b * i / striche
        y = y0 + h * i / striche
        t.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y0+h}" class="gitter"/>')
        t.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+b}" y2="{y:.1f}" class="gitter"/>')
        t.append(f'<text x="{x:.1f}" y="{y0+h+16}" class="tick">{i/striche:.1f}</text>')
        t.append(f'<text x="{x0-8}" y="{y0+h-h*i/striche+4:.1f}" class="tick re">{i/striche:.1f}</text>')
    t.append(f'<text x="{x0+b/2}" y="{y0+h+36}" class="achse">{xlabel}</text>')
    t.append(f'<text transform="translate({x0-40},{y0+h/2}) rotate(-90)" class="achse">{ylabel}</text>')
    return "".join(t)


# ------------------------------------------------------- Diagramm: Node-Kette
def svg_kette():
    nodes = [
        ("1", "Log &#8594; ARRI Rec.709", "LUT", "geteilt", "#3f6f9f"),
        ("2", "Weißabgleich + Helligkeit", "regelbar", "pro Kamera", "#b8762e"),
        ("3", "Rec.709 &#8594; ARRI LogC", "LUT", "geteilt", "#3f6f9f"),
        ("4", "Filmemulation", "LUT", "geteilt", "#3f6f9f"),
        ("5", "Kino-Look", "LUT", "geteilt", "#3f6f9f"),
    ]
    b, l, x0, y = 168, 28, 30, 150
    t = []
    for i, (nr, name, art, wo, farbe) in enumerate(nodes):
        x = x0 + i * (b + l)
        hoch = art == "regelbar"
        t.append(f'<rect x="{x}" y="{y - (14 if hoch else 0)}" width="{b}" height="{104 if hoch else 92}" '
                 f'rx="8" class="node" style="stroke:{farbe};stroke-width:{3 if hoch else 2}"/>')
        t.append(f'<circle cx="{x+22}" cy="{y+(8 if hoch else 22)}" r="14" fill="{farbe}"/>')
        t.append(f'<text x="{x+22}" y="{y+(13 if hoch else 27)}" class="nodenr">{nr}</text>')
        t.append(f'<text x="{x+44}" y="{y+(13 if hoch else 27)}" class="nodeart" fill="{farbe}">{art}</text>')
        for j, zeile in enumerate(name.split(" + ")):
            t.append(f'<text x="{x+16}" y="{y+(46 if hoch else 56)+j*20}" class="nodename">{zeile}</text>')
        t.append(f'<text x="{x+16}" y="{y+(80 if hoch else 82)}" class="nodewo">{wo}</text>')
        if i < len(nodes) - 1:
            t.append(f'<path d="M {x+b+4} {y+46} l {l-8} 0" class="pfeil"/>')
    t.append('<text x="30" y="70" class="dtitel">Das Bild läuft von links nach rechts durch fünf Nodes</text>')
    t.append('<text x="30" y="98" class="dtext">Blau = objektiv, ändert sich im Projekt nicht &#8594; als LUT richtig aufgehoben.'
             '  Orange = subjektiv &#8594; muss ein Regler bleiben.</text>')
    t.append(f'<text x="{x0+ (b+l)+b/2}" y="{y+126}" class="hinweis">der einzige Node mit Zahlenwerten</text>')
    t.append('<text x="30" y="330" class="dtext">Die Reihenfolge ist der eigentliche Trick: Der Weißabgleich steht '
             '<tspan class="stark">vor</tspan> der Filmemulation.</text>')
    t.append('<text x="30" y="356" class="dtext">Eine Film-LUT gleicht einen Farbstich nicht aus &#8211; sie reicht ihn '
             'durch und verstärkt ihn.</text>')
    return t


# --------------------------------------------- Diagramm: Filmkurve mit Fuß/Schulter
def svg_filmkurve():
    x0, y0, b, h = 80, 60, 430, 330
    t = [achsen(x0, y0, b, h, "ARRI LogC (Eingang)", "Rec.709 (Ausgang)")]
    g = np.linspace(0, 1, 201)
    aus = film(np.stack([g, g, g], 1))
    for k, farbe in ((0, "#d05a4a"), (1, "#4a9a5a"), (2, "#4a7ad0")):
        p = [(x0 + b * g[i], y0 + h - h * aus[i, k]) for i in range(len(g))]
        t.append(f'<path d="{pfad(p)}" class="kurve" style="stroke:{farbe}"/>')
    # Vergleichslinie: lineare Wiedergabe
    t.append(f'<line x1="{x0}" y1="{y0+h}" x2="{x0+b}" y2="{y0}" class="hilfslinie"/>')
    # Markierungen
    schwarz = film(np.array([[0.0, 0.0, 0.0]]))[0, 1]
    weiss = film(np.array([[1.0, 1.0, 1.0]]))[0, 1]
    ys = y0 + h - h * schwarz
    yw = y0 + h - h * weiss
    t.append(f'<line x1="{x0}" y1="{ys:.1f}" x2="{x0+b}" y2="{ys:.1f}" class="marke"/>')
    t.append(f'<text x="{x0+12}" y="{ys-8:.1f}" class="markentext">Filmschwarz {schwarz:.3f}<tspan class="klein"> &#8211; läuft nie zu</tspan></text>')
    t.append(f'<line x1="{x0}" y1="{yw:.1f}" x2="{x0+b}" y2="{yw:.1f}" class="marke"/>')
    t.append(f'<text x="{x0+12}" y="{yw-8:.1f}" class="markentext">Weiß {weiss:.3f}<tspan class="klein"> &#8211; weiche Schulter</tspan></text>')
    mitte = film(np.array([[0.391, 0.391, 0.391]]))[0, 1]
    xm, ym = x0 + b * 0.391, y0 + h - h * mitte
    t.append(f'<circle cx="{xm:.1f}" cy="{ym:.1f}" r="5" class="punkt"/>')
    t.append(f'<text x="{xm+10:.1f}" y="{ym-10:.1f}" class="markentext">18-%-Grau &#8594; {mitte:.3f}</text>')
    t.append(f'<text x="{x0+b-10}" y="{y0+24}" class="legende re">Rot / Grün / Blau liegen fast deckungsgleich</text>')
    t.append('<text x="560" y="110" class="dtitel2">Drei Eigenschaften machen ein Filmbild aus</text>')
    for i, (fett, rest) in enumerate([
            ("Der Kurvenfuß", "hält die tiefsten Töne flach, statt sie auf Null zu drücken. Schatten behalten Zeichnung."),
            ("Die Schulter", "komprimiert die Lichter weich. Ein Scheinwerfer brennt nicht ab, er läuft aus."),
            ("Die Schichten", "haben leicht verschiedene Steilheiten. Deshalb sind Schatten und Lichter nie gleich getönt.")]):
        y = 156 + i * 100
        t.append(f'<text x="560" y="{y}" class="dtext"><tspan class="stark">{fett}</tspan></text>')
        for j, zeile in enumerate(umbruch(rest, 48)):
            t.append(f'<text x="560" y="{y+26+j*23}" class="dtext">{zeile}</text>')
    return t


def umbruch(text, breite):
    worte, zeilen, jetzt = text.split(), [], ""
    for w in worte:
        if len(jetzt) + len(w) + 1 > breite:
            zeilen.append(jetzt)
            jetzt = w
        else:
            jetzt = (jetzt + " " + w).strip()
    if jetzt:
        zeilen.append(jetzt)
    return zeilen


# ------------------------------------------------- Diagramm: Split-Tone Kino-Look
def svg_kino():
    x0, y0, b, h = 90, 70, 420, 300
    t = [achsen(x0, y0, b, h, "Eingang", "Ausgang")]
    g = np.linspace(0, 1, 201)
    grau = np.stack([g, g, g], 1)
    aus = kinolook(grau, *STUFEN["mittel"])
    for k, farbe in ((0, "#d05a4a"), (1, "#4a9a5a"), (2, "#4a7ad0")):
        p = [(x0 + b * g[i], y0 + h - h * aus[i, k]) for i in range(len(g))]
        t.append(f'<path d="{pfad(p)}" class="kurve" style="stroke:{farbe}"/>')
    t.append(f'<line x1="{x0}" y1="{y0+h}" x2="{x0+b}" y2="{y0}" class="hilfslinie"/>')
    t.append(f'<text x="{x0+14}" y="{y0+h-14}" class="markentext">Schatten &#8594; Teal</text>')
    t.append(f'<text x="{x0+b-14}" y="{y0+34}" class="markentext re">Lichter &#8594; Warm</text>')
    # Farbfelder: vorher / nachher
    t.append('<text x="580" y="104" class="dtitel2">Derselbe Graukeil, vorher und nachher</text>')
    for i, z in enumerate(np.linspace(0.08, 0.92, 8)):
        x = 580 + i * 46
        vor = np.array([z, z, z])
        nach = kinolook(vor[None], *STUFEN["mittel"])[0]
        t.append(f'<rect x="{x}" y="130" width="42" height="52" fill="{hex_von(vor)}"/>')
        t.append(f'<rect x="{x}" y="186" width="42" height="52" fill="{hex_von(nach)}"/>')
    t.append('<text x="580" y="258" class="klein">oben ohne, unten mit Kino-Look &#8211; '
             'Schwarz wird angehoben, Kontrast steigt</text>')
    t.append('<text x="580" y="308" class="dtext">Bewusst zurückhaltend dosiert: Node 4 hat den</text>')
    t.append('<text x="580" y="330" class="dtext">Großteil des Looks schon gemacht. Hier kommt nur</text>')
    t.append('<text x="580" y="352" class="dtext">der Feinschliff obendrauf &#8211; in drei Stärken.</text>')
    return t


# ------------------------------------------- Diagramm: Gruppe und Durchschlag
def svg_gruppe():
    t = []
    t.append('<rect x="40" y="70" width="920" height="112" rx="10" class="gruppe"/>')
    t.append('<text x="60" y="100" class="dtitel2">Farbgruppe &#8222;vor Clipbearbeitung&#8220; &#8211; geteilt</text>')
    t.append('<rect x="60" y="112" width="200" height="52" rx="6" class="node" style="stroke:#3f6f9f"/>')
    t.append('<text x="76" y="143" class="nodename">Node 1 &#8211; Log &#8594; Rec.709</text>')

    for i, (name, x) in enumerate((("Kamera A", 140), ("Kamera B", 420), ("Kamera C", 700))):
        t.append(f'<rect x="{x}" y="210" width="200" height="76" rx="8" class="node" style="stroke:#b8762e;stroke-width:3"/>')
        t.append(f'<text x="{x+16}" y="238" class="nodename">{name}</text>')
        t.append(f'<text x="{x+16}" y="264" class="klein">Node 2 &#8211; eigener Weißabgleich</text>')
        t.append(f'<path d="M {x+100} 182 l 0 24" class="pfeil"/>')
        t.append(f'<path d="M {x+100} 286 l 0 24" class="pfeil"/>')

    t.append('<rect x="40" y="314" width="920" height="112" rx="10" class="gruppe"/>')
    t.append('<text x="60" y="344" class="dtitel2">Farbgruppe &#8222;nach Clipbearbeitung&#8220; &#8211; geteilt</text>')
    for i, name in enumerate(("Node 3 &#8211; Rec.709 &#8594; LogC", "Node 4 &#8211; Filmemulation", "Node 5 &#8211; Kino-Look")):
        x = 60 + i * 300
        t.append(f'<rect x="{x}" y="356" width="270" height="52" rx="6" class="node" style="stroke:#3f6f9f"/>')
        t.append(f'<text x="{x+16}" y="387" class="nodename">{name}</text>')
    t.append('<text x="40" y="452" class="dtext">Liegen die Kameras als genestete Quell-Timelines im Schnitt, '
             'wirkt jede Änderung <tspan class="stark">live in jedem einzelnen Schnitt</tspan> &#8211; nichts wird eingebacken.</text>')
    return t


# ------------------------------------------------- Diagramm: frei gegen gekauft
def svg_vergleich(daten):
    x0, y0, b, h = 90, 70, 430, 300
    t = [achsen(x0, y0, b, h, "Rec.709 (Eingang)", "Rec.709 (nach Filmemulation)")]
    for reihe, farbe, name in ((daten["frei"], "#2f7fb8", "frei erzeugt"),
                               (daten["gekauft"], "#c0662a", "gekauft")):
        p = [(x0 + b * x, y0 + h - h * y) for x, y in reihe]
        t.append(f'<path d="{pfad(p)}" class="kurve" style="stroke:{farbe}"/>')
    t.append(f'<rect x="{x0+16}" y="{y0+16}" width="14" height="4" fill="#2f7fb8"/>')
    t.append(f'<text x="{x0+38}" y="{y0+24}" class="legende">frei erzeugt</text>')
    t.append(f'<rect x="{x0+16}" y="{y0+40}" width="14" height="4" fill="#c0662a"/>')
    t.append(f'<text x="{x0+38}" y="{y0+48}" class="legende">gekaufter LUT-Satz</text>')

    t.append('<text x="590" y="104" class="dtitel2">Wie weit liegen sie auseinander?</text>')
    zeilen = [
        ("Mitteltöne", "unter einem Prozentpunkt &#8211; dort, wo Gesichter liegen"),
        ("Lichter", "der gekaufte Satz hält sie heller"),
        ("Hautton", "die freie Kette ist neutraler und rund 10 % dunkler"),
        ("Ausgleich", "Gamma leicht hoch, Temperatur leicht wärmer &#8211; in Node 2"),
    ]
    y = 148
    for fett, rest in zeilen:
        t.append(f'<text x="590" y="{y}" class="dtext"><tspan class="stark">{fett}</tspan></text>')
        teile = umbruch(rest, 44)
        for j, zeile in enumerate(teile):
            t.append(f'<text x="590" y="{y+25+j*22}" class="dtext">{zeile}</text>')
        y += 46 + 22 * len(teile)
    return t


# ------------------------------------------------------------------- Aufbau
def folie(nummer, titel, unter, inhalt, gesamt):
    return f'''<section class="folie">
  <header><h2>{titel}</h2><p>{unter}</p></header>
  <svg viewBox="0 0 {BREITE} {HOEHE}" class="dia">{"".join(inhalt)}</svg>
  <footer><span>Film-Look als LUT-Kette &#183; wunder-media.de</span><span>{nummer} / {gesamt}</span></footer>
</section>'''


def textfolie(nummer, titel, unter, bloecke, gesamt, spalten=2):
    kacheln = "".join(
        f'<div class="kachel"><h3>{k}</h3><p>{v}</p></div>' for k, v in bloecke)
    return f'''<section class="folie">
  <header><h2>{titel}</h2><p>{unter}</p></header>
  <div class="kacheln s{spalten}">{kacheln}</div>
  <footer><span>Film-Look als LUT-Kette &#183; wunder-media.de</span><span>{nummer} / {gesamt}</span></footer>
</section>'''


def main():
    # Messreihe fuer die Vergleichsfolie: freie Kette (Node 3 + 4) gegen die
    # in referenzen/messwerte.md dokumentierten Werte des gekauften Satzes.
    x = np.linspace(0.1, 1.0, 10)
    frei_lut = os.path.join(WURZEL, "luts", "ARRI_Rec709_zu_LogC.cube")
    if os.path.isfile(frei_lut):
        logc = lade_cube(frei_lut)
        frei = [(float(z), float(film(auswerten(logc, np.array([[z, z, z]])))[0, 1])) for z in x]
    else:   # ohne erzeugte Node-3-LUT: dokumentierte Messwerte verwenden
        frei = list(zip(x, [0.093, 0.165, 0.228, 0.297, 0.375, 0.463, 0.557, 0.650, 0.754, 0.946]))
    gekauft = list(zip(x, [0.057, 0.142, 0.225, 0.304, 0.387, 0.474, 0.559, 0.644, 0.805, 0.867]))
    daten = {"frei": frei, "gekauft": gekauft}

    folien = []
    gesamt = 11
    folien.append(f'''<section class="folie titel">
  <div>
    <p class="augenbraue">DaVinci Resolve &#183; Grading</p>
    <h1>Film-Look als LUT-Kette</h1>
    <p class="unter">Vier LUTs für das Objektive, ein Regler für das Subjektive</p>
    <p class="quelle">wunder-media.de</p>
  </div>
</section>''')

    folien.append(textfolie(2, "Warum nicht einfach eine LUT?",
                            "Der Unterschied zwischen einem Look, den man versteht, und einem, den man nur hat",
                            [("Eine LUT ist eine Blackbox",
                              "Sieht das Bild hinterher &#8222;irgendwie komisch&#8220; aus, lässt sich nicht mehr sagen, "
                              "welcher Schritt schuld war. Zurückstellen kann man auch nichts einzeln."),
                             ("Objektiv oder subjektiv?",
                              "Farbwandlungen und der Look ändern sich im Projekt nicht &#8211; als LUT gut aufgehoben. "
                              "Weißabgleich und Helligkeit ändern sich pro Kamera und pro Situation."),
                             ("Die Regel",
                              "LUTs nur für die vier objektiven Schritte. Alles andere &#8211; Temperatur, Belichtung, "
                              "Sättigung, Hautton &#8211; bleibt ein Regler in Node 2. Nie eine zusätzlich gebackene LUT."),
                             ("Der praktische Gewinn",
                              "Man sieht jederzeit, was das Bild vom Original entfernt hat, und kann jeden einzelnen "
                              "Wert wieder zurückdrehen.")],
                            gesamt))

    folien.append(folie(3, "Die Kette", "Fünf Nodes, klar getrennte Aufgaben", svg_kette(), gesamt))

    folien.append(textfolie(4, "Node 1 &#8211; vom Log-Bild zum beurteilbaren Bild",
                            "S-Log3 ist flach und entsättigt; darin lässt sich nichts entscheiden",
                            [("Nicht die Hersteller-LUT",
                              "Sonys eigene Rec.709-LUT sieht technisch und hart aus. Stattdessen wird das Bild "
                              "rechnerisch nach ARRI LogC gebracht und durch ARRIs Farbwiedergabe geschickt."),
                             ("Warum ARRI",
                              "ARRIs Farbwiedergabe gilt als Referenz für angenehme Hauttöne. Gesichter bleiben warm, "
                              "statt ins Orange oder Magenta zu kippen; die Lichter laufen weich aus."),
                             ("Eine reine Wandlung",
                              "Kein Farbstich, keine Helligkeitsanhebung, keine Sättigungsänderung. Alles Kreative "
                              "kommt erst später &#8211; sonst wüsste man wieder nicht, wer was gemacht hat."),
                             ("Kontrollwert",
                              "18-%-Grau landet auf LogC 0,391 und Rec.709 0,398. Das Skript gibt diesen Wert bei "
                              "jedem Lauf aus &#8211; sitzt er, sitzt die Wandlung.")],
                            gesamt))

    folien.append(textfolie(5, "Node 2 &#8211; der einzige Node mit Reglern",
                            "Hier wird jede Kamera einzeln angepasst",
                            [("Helligkeit über Gamma, nicht über Gain",
                              "Gain zieht die Lichter mit hoch &#8211; bei einem Gesicht im Scheinwerfer ist die Stirn "
                              "sofort ausgebrannt. Gamma hebt die Mitteltöne, wo das Gesicht liegt."),
                             ("Temperatur und Tönung",
                              "Zwei Kameras auf dieselbe Bühne haben fast nie dieselbe Farbtemperatur. Schritte von "
                              "100 bis 200 sind meist schon sichtbar; die Tönung klein halten."),
                             ("Warum dieser Node vor der Film-LUT steht",
                              "Eine Filmemulation gleicht einen Farbstich nicht aus. Sie reicht ihn durch und "
                              "verstärkt ihn. Erst neutral machen, dann den Look daraufsetzen."),
                             ("Pro Kamera, nicht global",
                              "Node 2 liegt auf der Clip-Ebene und darf je Kamera anders sein. Alle anderen Nodes "
                              "liegen in der Gruppe und sind für alle identisch.")],
                            gesamt))

    folien.append(textfolie(6, "Node 3 &#8211; zurück ins Log-Format",
                            "Ein technischer Zwischenschritt, der oft falsch gemacht wird",
                            [("Warum überhaupt zurück?",
                              "Filmemulationen der Alexa-Familie erwarten LogC am Eingang. Nach Node 1 und 2 liegt "
                              "aber Rec.709 vor &#8211; also muss das Bild noch einmal ins Log."),
                             ("Die Falle",
                              "Ein Color-Space-Transform &#8222;Rec.709 &#8594; LogC&#8220; legt das Material rund zwei Blenden "
                              "unter den Arbeitspunkt der Film-LUTs. Ergebnis: dunkel und flau."),
                             ("Richtig",
                              "Eine Wandlung nehmen, die exakt die Umkehrung von Node 1 ist. Das Skript rechnet sie "
                              "per Newton-Verfahren aus der ARRI-Wiedergabe aus."),
                             ("Was keine Umkehrung kann",
                              "Stark gesättigte Farben verliert die Rec.709-Wiedergabe unwiederbringlich. Das gilt "
                              "für die gekaufte Wandlung genauso &#8211; bei normalem Licht ohne Bedeutung.")],
                            gesamt))

    folien.append(folie(7, "Node 4 &#8211; die Filmemulation",
                        "Belichtung &#8594; Negativdichte &#8594; Schichtkopplung &#8594; Kopierfilm &#8594; Bild",
                        svg_filmkurve(), gesamt))

    folien.append(folie(8, "Node 5 &#8211; der Kino-Look obendrauf",
                        "Kontrast, angehobenes Schwarz, Split-Tone, leichte Entsättigung",
                        svg_kino(), gesamt))

    folien.append(folie(9, "Geteilte Nodes statt kopierter Grades",
                        "Eine Änderung am Look wirkt sofort auf alle Kameras &#8211; bis in jeden Schnitt",
                        svg_gruppe(), gesamt))

    folien.append(folie(10, "Selbst erzeugt oder gekauft?",
                        "Beide Ketten gemessen, Graukeil durch Node 3 und 4",
                        svg_vergleich(daten), gesamt))

    folien.append(textfolie(11, "Der ganze Ablauf",
                            "Drei Befehle &#8211; und zwei Handgriffe, die die Resolve-API nicht kann",
                            [("1. LUTs erzeugen",
                              "<code>py werkzeuge/luts_erzeugen.py</code><br>Rechnet alle vier LUTs aus. "
                              "Dauert eine knappe Minute; es muss nichts gekauft werden."),
                             ("2. Installieren",
                              "<code>py werkzeuge/luts_installieren.py</code><br>Kopiert sie in den LUT-Ordner "
                              "von Resolve und meldet sie dort an."),
                             ("3. Kette anlegen",
                              "<code>py werkzeuge/look_anwenden.py --timeline &quot;nah&quot;</code><br>"
                              "Legt die Farbgruppe an, ordnet die Clips zu und setzt alle LUTs."),
                             ("Von Hand bleibt",
                              "Drei Nodes im Gruppen-Graph mit <b>Alt+S</b> anlegen &#8211; die API kann keine Nodes "
                              "erzeugen. Und die LUT-Interpolation einmal auf <b>tetraedrisch</b> stellen.")],
                            gesamt))

    html = KOPF + "\n".join(folien) + FUSS
    ziel = os.path.join(HIER, "praesentation.html")
    with open(ziel, "w", encoding="utf-8") as f:
        f.write(html)
    print("geschrieben:", ziel)
    print("PDF bauen mit:")
    print(r'  chrome --headless=new --no-pdf-header-footer '
          r'--print-to-pdf="Film-Look-LUT-Kette.pdf" praesentation.html')


# --- .cube lesen (fuer die Vergleichsfolie, falls Node-3-LUT schon erzeugt wurde) ---
def lade_cube(pfad_):
    werte = []
    for zeile in open(pfad_, encoding="utf-8", errors="ignore"):
        teile = zeile.split()
        if len(teile) == 3:
            try:
                werte.append([float(t) for t in teile])
            except ValueError:
                pass
    a = np.array(werte)
    n = round(len(a) ** (1 / 3))
    return a.reshape(n, n, n, 3).transpose(2, 1, 0, 3), n


def auswerten(lut_n, q):
    lut, n = lut_n
    q = np.clip(q, 0, 1) * (n - 1)
    i0 = np.floor(q).astype(int)
    i1 = np.minimum(i0 + 1, n - 1)
    f = q - i0
    r0, g0, b0 = i0[:, 0], i0[:, 1], i0[:, 2]
    r1, g1, b1 = i1[:, 0], i1[:, 1], i1[:, 2]
    fr, fg, fb = f[:, 0:1], f[:, 1:2], f[:, 2:3]
    c00 = lut[r0, g0, b0] * (1 - fr) + lut[r1, g0, b0] * fr
    c10 = lut[r0, g1, b0] * (1 - fr) + lut[r1, g1, b0] * fr
    c01 = lut[r0, g0, b1] * (1 - fr) + lut[r1, g0, b1] * fr
    c11 = lut[r0, g1, b1] * (1 - fr) + lut[r1, g1, b1] * fr
    c0 = c00 * (1 - fg) + c10 * fg
    c1 = c01 * (1 - fg) + c11 * fg
    return c0 * (1 - fb) + c1 * fb


KOPF = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><title>Film-Look als LUT-Kette</title>
<style>
@page { size: 297mm 167mm; margin: 0; }
* { box-sizing: border-box; }
body { margin:0; font-family: "Segoe UI", system-ui, sans-serif; color:#1d2733; background:#eef1f5; }
.folie { width:297mm; height:167mm; padding:14mm 16mm 10mm; background:#fff; position:relative;
         page-break-after:always; display:flex; flex-direction:column; overflow:hidden; }
.folie:last-child { page-break-after:auto; }
header h2 { font-size:25pt; margin:0 0 3px; font-weight:650; letter-spacing:-0.2px; }
header p { font-size:11.5pt; margin:0 0 10px; color:#5d6b7c; }
footer { position:absolute; left:16mm; right:16mm; bottom:6mm; display:flex; justify-content:space-between;
         font-size:8pt; color:#93a0b0; border-top:1px solid #e2e7ee; padding-top:5px; }
.dia { width:100%; flex:1; }
.titel { justify-content:center; background:linear-gradient(135deg,#1d2733 0%,#2f4256 100%); color:#fff; }
.titel h1 { font-size:44pt; margin:6px 0 12px; font-weight:680; letter-spacing:-0.8px; }
.augenbraue { font-size:11pt; letter-spacing:2.5px; text-transform:uppercase; color:#8fb4d8; margin:0; }
.unter { font-size:16pt; color:#c8d6e4; margin:0; font-weight:340; }
.quelle { position:absolute; bottom:10mm; font-size:10pt; color:#7f97ae; }
.kacheln { display:grid; gap:10mm 11mm; flex:1; align-content:center; padding-bottom:6mm; }
.kacheln.s2 { grid-template-columns:1fr 1fr; }
.kachel h3 { font-size:13pt; margin:0 0 6px; color:#2f4d6d; font-weight:640; }
.kachel p { font-size:11pt; line-height:1.5; margin:0; color:#38434f; }
.kachel code { background:#eef2f7; padding:2px 6px; border-radius:4px; font-size:10pt; color:#1d3a56; }
text { font-family:"Segoe UI", system-ui, sans-serif; }
.feld { fill:#fbfcfd; stroke:#d5dde6; }
.gitter { stroke:#e8edf2; stroke-width:1; }
.tick { font-size:11px; fill:#93a0b0; text-anchor:middle; }
.tick.re { text-anchor:end; }
.achse { font-size:12px; fill:#5d6b7c; text-anchor:middle; }
.kurve { fill:none; stroke-width:3; stroke-linejoin:round; }
.hilfslinie { stroke:#c3ccd6; stroke-width:1.5; stroke-dasharray:5 5; }
.marke { stroke:#b8762e; stroke-width:1.5; stroke-dasharray:4 4; }
.markentext { font-size:13px; fill:#38434f; }
.markentext.re { text-anchor:end; }
.klein { font-size:12px; fill:#7c8996; }
.punkt { fill:#b8762e; }
.legende { font-size:13px; fill:#5d6b7c; }
.legende.re { text-anchor:end; }
.node { fill:#fff; stroke-width:2; }
.gruppe { fill:#f3f7fb; stroke:#c9d9e8; stroke-width:1.5; }
.nodenr { font-size:15px; font-weight:700; fill:#fff; text-anchor:middle; }
.nodeart { font-size:12px; font-weight:600; letter-spacing:0.4px; text-transform:uppercase; }
.nodename { font-size:14.5px; fill:#1d2733; font-weight:600; }
.nodewo { font-size:12px; fill:#7c8996; }
.pfeil { stroke:#9fb0c2; stroke-width:2.5; fill:none; marker-end:url(#spitze); }
.dtitel { font-size:17px; fill:#1d2733; font-weight:650; }
.dtitel2 { font-size:16px; fill:#2f4d6d; font-weight:650; }
.dtext { font-size:14.5px; fill:#38434f; }
.hinweis { font-size:12.5px; fill:#b8762e; text-anchor:middle; }
.stark { font-weight:700; fill:#1d2733; }
</style></head><body>
<svg width="0" height="0" style="position:absolute"><defs><marker id="spitze" viewBox="0 0 10 10" refX="9" refY="5"
 markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#9fb0c2"/></marker></defs></svg>
"""

FUSS = "\n</body></html>\n"


if __name__ == "__main__":
    main()
