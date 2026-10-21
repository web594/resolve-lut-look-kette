# -*- coding: utf-8 -*-
"""Erzeugt alle LUTs der Kette auf einen Schlag und legt sie in ./luts ab.

Es entstehen:
  Sony_SLog3_zu_ARRI_Rec709.cube            (Node 2, aus der Resolve-eigenen ARRI-Wandlung)
  ARRI_Rec709_zu_LogC_v2.cube               (Node 3, freie Alternative zur gekauften Wandlung;
                                             stabile Fassung 2 - die alte ARRI_Rec709_zu_LogC.cube
                                             kippt helle Haut nach Rot und wird nicht mehr erzeugt)
  Filmemulation_Negativ_Print_ARRI_LogC.cube(Node 4, freie Alternative zur gekauften Filmemulation)
  Kinolook_Kontrast_TealOrange_*.cube       (Node 5, drei Staerken)

Aufruf:  py luts_erzeugen.py [--out-dir <ordner>] [--size 33]
"""
import argparse
import os
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
STANDARD_ZIEL = os.path.join(os.path.dirname(HIER), "luts")


def lauf(skript, argumente):
    befehl = [sys.executable, os.path.join(HIER, skript)] + argumente
    print("\n>", " ".join(befehl))
    if subprocess.call(befehl) != 0:
        sys.exit(f"Abgebrochen bei {skript}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default=STANDARD_ZIEL)
    p.add_argument("--size", type=int, default=33)
    p.add_argument("--dat", default=None, help="Pfad zur ARRI-LUT aus der Resolve-Installation")
    a = p.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    dat = ["--dat", a.dat] if a.dat else []

    lauf("lut_slog3_zu_arri_rec709.py",
         dat + ["--size", str(a.size), "--out", os.path.join(a.out_dir, "Sony_SLog3_zu_ARRI_Rec709.cube")])
    lauf("lut_rec709_zu_arri_logc_v2.py",
         dat + ["--size", str(a.size), "--out", os.path.join(a.out_dir, "ARRI_Rec709_zu_LogC_v2.cube")])
    lauf("lut_filmemulation_negativ_print.py", ["--size", str(a.size), "--out-dir", a.out_dir])
    lauf("lut_kinolook_tealorange.py", ["--size", str(a.size), "--out-dir", a.out_dir])

    print("\nFertig. LUTs liegen in:", a.out_dir)
    print("Weiter mit:  py luts_installieren.py")


if __name__ == "__main__":
    main()
