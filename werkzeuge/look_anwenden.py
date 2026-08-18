# -*- coding: utf-8 -*-
"""Baut die Look-Kette als GETEILTE Nodes ueber eine Farbgruppe (Color Group).

Aufteilung (siehe referenzen/nodekette.md):
  Gruppe "vor Clipbearbeitung"  Node 1  ->  Sony S-Log3 -> ARRI Rec.709
  Clip-Ebene                    Node 1  ->  Weissabgleich + Helligkeit  (pro Kamera regelbar)
  Gruppe "nach Clipbearbeitung" Node 1  ->  Rec.709 -> ARRI LogC
                                Node 2  ->  Filmemulation
                                Node 3  ->  Kino-Look

Der Sinn: alles Objektive liegt geteilt in der Gruppe (eine Aenderung wirkt auf alle
Kameras), alles Subjektive liegt auf der Clip-Ebene und bleibt je Kamera einzeln
regelbar. Bei genesteten Quell-Timelines schlaegt das live bis in den Schnitt durch.

⚠ Die Resolve-API kann KEINE Nodes anlegen (es gibt kein AddNode). Die drei Nodes im
Gruppen-Graph "nach Clipbearbeitung" muessen einmal von Hand mit Alt+S ergaenzt werden -
danach setzt dieses Skript die LUTs. Ohne die Nodes meldet es genau das und aendert nichts.

Aufruf:
  py look_anwenden.py --timeline "nah" --timeline "weit"
  py look_anwenden.py --pruefen
"""
import argparse
import os
import sys

STANDARD_LUTS = {
    "arri": "Look/Sony_SLog3_zu_ARRI_Rec709.cube",
    "logc": "Look/ARRI_Rec709_zu_LogC.cube",
    "film": "Look/Filmemulation_Negativ_Print_ARRI_LogC.cube",
    "kino": "Look/Kinolook_Kontrast_TealOrange_mittel.cube",
}


def resolve_verbinden():
    api = os.environ.get(
        "RESOLVE_SCRIPT_API",
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting")
    os.environ.setdefault("RESOLVE_SCRIPT_API", api)
    os.environ.setdefault(
        "RESOLVE_SCRIPT_LIB",
        r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll")
    sys.path.append(os.path.join(api, "Modules"))
    import DaVinciResolveScript as dvr
    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        sys.exit("Resolve nicht erreichbar - laeuft es, und ist Scripting in den Einstellungen erlaubt?")
    projekt = resolve.GetProjectManager().GetCurrentProject()
    if projekt is None:
        sys.exit("Kein Projekt geoeffnet.")
    return resolve, projekt


def timelines_suchen(projekt, fragmente):
    alle = [projekt.GetTimelineByIndex(i) for i in range(1, projekt.GetTimelineCount() + 1)]
    if not fragmente:
        aktuell = projekt.GetCurrentTimeline()
        return [aktuell] if aktuell else []
    treffer = []
    for t in alle:
        name = t.GetName()
        if any(f.lower() in name.lower() for f in fragmente):
            treffer.append(t)
    return treffer


def clips_sammeln(timelines, spur):
    clips = []
    for t in timelines:
        clips.extend(t.GetItemListInTrack("video", spur))
    return clips


def bericht(graph, titel):
    print(f"  {titel}: {graph.GetNumNodes()} Node(s)")
    for i in range(1, graph.GetNumNodes() + 1):
        print(f"    Node {i}: LUT = {graph.GetLUT(i) or '-'}   Werkzeuge = {graph.GetToolsInNode(i) or '-'}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--timeline", action="append", default=[],
                   help="Namensfragment einer Quell-Timeline (mehrfach moeglich)")
    p.add_argument("--spur", type=int, default=1, help="Videospur der Quell-Timelines")
    p.add_argument("--gruppe", default="Look")
    p.add_argument("--lut-arri", default=STANDARD_LUTS["arri"])
    p.add_argument("--lut-logc", default=STANDARD_LUTS["logc"])
    p.add_argument("--lut-film", default=STANDARD_LUTS["film"])
    p.add_argument("--lut-kino", default=STANDARD_LUTS["kino"])
    p.add_argument("--clipgrades-loeschen", action="store_true",
                   help="Clip-Grades der Zielclips zuruecksetzen, bevor die Gruppe greift")
    p.add_argument("--pruefen", action="store_true", help="nur anzeigen, nichts aendern")
    a = p.parse_args()

    resolve, projekt = resolve_verbinden()
    projekt.RefreshLUTList()

    timelines = timelines_suchen(projekt, a.timeline)
    if not timelines:
        sys.exit("Keine passende Timeline gefunden.")
    print("Timelines:", ", ".join(t.GetName() for t in timelines))
    clips = clips_sammeln(timelines, a.spur)
    print("Clips:", len(clips))
    if not clips:
        sys.exit("Auf der angegebenen Videospur liegen keine Clips.")

    gruppe = next((g for g in projekt.GetColorGroupsList() if g.GetName() == a.gruppe), None)

    if a.pruefen:
        if gruppe is None:
            print(f"Farbgruppe '{a.gruppe}' existiert noch nicht.")
        else:
            print(f"Farbgruppe '{a.gruppe}':")
            bericht(gruppe.GetPreClipNodeGraph(), "vor Clipbearbeitung")
            bericht(gruppe.GetPostClipNodeGraph(), "nach Clipbearbeitung")
        bericht(clips[0].GetNodeGraph(), "Clip-Ebene (erster Clip)")
        return

    if gruppe is None:
        gruppe = projekt.AddColorGroup(a.gruppe)
        print("Farbgruppe angelegt:", gruppe.GetName())

    for clip in clips:
        if a.clipgrades_loeschen:
            clip.GetNodeGraph().ResetAllGrades()
        clip.AssignToColorGroup(gruppe)
    print("Clips der Gruppe zugeordnet.")

    vor = gruppe.GetPreClipNodeGraph()
    if not vor.SetLUT(1, a.lut_arri):
        print("⚠ ARRI-LUT konnte nicht gesetzt werden - Name/Pfad pruefen:", a.lut_arri)
    else:
        print("vor Clipbearbeitung, Node 1 =", vor.GetLUT(1))

    nach = gruppe.GetPostClipNodeGraph()
    if nach.GetNumNodes() < 3:
        print(f"\n⚠ Der Gruppen-Graph 'nach Clipbearbeitung' hat nur {nach.GetNumNodes()} Node(s), "
              "es werden 3 gebraucht.")
        print("  Einmalig in der GUI: Farbe-Seite -> Node-Modus 'Gruppe (nach Clipbearbeitung)' "
              "-> Alt+S so oft, bis 3 Nodes stehen. Danach dieses Skript erneut aufrufen.")
        return
    for index, lut in ((1, a.lut_logc), (2, a.lut_film), (3, a.lut_kino)):
        if not nach.SetLUT(index, lut):
            print(f"⚠ LUT auf Node {index} nicht gesetzt - Name/Pfad pruefen:", lut)
        else:
            print(f"nach Clipbearbeitung, Node {index} =", nach.GetLUT(index))

    print("\nFertig. Weissabgleich und Helligkeit jetzt auf der CLIP-Ebene einstellen -")
    print("nicht als LUT, damit jeder Wert einzeln regelbar bleibt.")


if __name__ == "__main__":
    main()
