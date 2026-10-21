# -*- coding: utf-8 -*-
"""Kopiert die LUTs dorthin, wo DaVinci Resolve sie findet, und meldet sie an.

Resolve durchsucht seinen LUT-Ordner nur beim Start neu - oder wenn ein Skript
RefreshLUTList() aufruft. Genau das macht dieses Skript am Ende, damit die neuen
Dateien sofort im LUT-Menue stehen.

Liegt im Ziel noch die alte ARRI_Rec709_zu_LogC.cube (Fassung 1), bleibt sie unangetastet,
damit bestehende Projekte sich nicht veraendern. Neue Ketten nehmen
ARRI_Rec709_zu_LogC_v2.cube - die alte Fassung kippt sehr helle Haut nach Rot.

Aufruf:  py luts_installieren.py [--quelle <ordner>] [--unterordner Look]
"""
import argparse
import os
import shutil
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
STANDARD_QUELLE = os.path.join(os.path.dirname(HIER), "luts")

ZIELE = [
    r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT",
    os.path.expanduser(r"~/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT"),
    os.path.expanduser(r"~/.local/share/DaVinciResolve/LUT"),
]


def lut_ordner():
    for z in ZIELE:
        if os.path.isdir(z):
            return z
    sys.exit("LUT-Ordner von Resolve nicht gefunden - Pfad bitte mit --ziel angeben.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--quelle", default=STANDARD_QUELLE)
    p.add_argument("--ziel", default=None)
    p.add_argument("--unterordner", default="Look", help="Unterordner im LUT-Verzeichnis")
    a = p.parse_args()

    ziel = os.path.join(a.ziel or lut_ordner(), a.unterordner)
    os.makedirs(ziel, exist_ok=True)

    dateien = sorted(f for f in os.listdir(a.quelle) if f.lower().endswith(".cube"))
    if not dateien:
        sys.exit(f"Keine .cube-Dateien in {a.quelle} - erst luts_erzeugen.py laufen lassen.")
    for f in dateien:
        shutil.copy2(os.path.join(a.quelle, f), os.path.join(ziel, f))
        print("kopiert:", f)
    print("\nZiel:", ziel)
    if os.path.isfile(os.path.join(ziel, "ARRI_Rec709_zu_LogC.cube")):
        print("Hinweis: alte ARRI_Rec709_zu_LogC.cube bleibt fuer bestehende Projekte liegen -",
              "fuer neue Ketten ARRI_Rec709_zu_LogC_v2.cube nehmen (die alte kippt helle Haut nach Rot).")

    # Resolve die neuen LUTs melden (falls Resolve laeuft)
    try:
        sys.path.append(os.path.join(
            os.environ.get("RESOLVE_SCRIPT_API",
                           r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"),
            "Modules"))
        import DaVinciResolveScript as dvr
        proj = dvr.scriptapp("Resolve").GetProjectManager().GetCurrentProject()
        proj.RefreshLUTList()
        print("Resolve kennt die LUTs jetzt (LUT-Liste aktualisiert).")
    except Exception as e:
        print("Hinweis: Resolve laeuft nicht oder ist nicht erreichbar -",
              "die LUTs erscheinen spaetestens nach einem Neustart von Resolve.", f"({e})")


if __name__ == "__main__":
    main()
