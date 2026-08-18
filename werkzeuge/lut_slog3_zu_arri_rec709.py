# -*- coding: utf-8 -*-
"""Erzeugt die LUT fuer Node 2 der Kette: Sony S-Log3 / S-Gamut3.Cine -> ARRI Rec.709.

Warum als Skript und nicht als fertige .cube-Datei?
Die LUT wird aus der ARRI-Wandlung gebacken, die DaVinci Resolve bereits mitbringt
("Arri Alexa LogC to Rec709.dat"). Diese Datei gehoert ARRI bzw. Blackmagic Design und
wird hier deshalb NICHT weitergegeben. Das Skript rechnet die LUT in wenigen Sekunden
aus der lokalen Resolve-Installation neu.

Rechenweg:
  S-Log3-Codewerte -> linear (S-Gamut3.Cine) -> ARRI Wide Gamut 3 (Bradford)
  -> ARRI LogC3 -> ARRIs eigenes Rec.709-Rendering (die .dat-LUT)

Ergebnis ist eine reine Wandlung ohne kreative Zutat: kein Farbstich, keine
Helligkeitsanhebung, keine Saettigungsaenderung. Alles Kreative kommt in die
spaeteren Nodes.

Voraussetzung:  py -m pip install numpy colour-science
Aufruf:         py lut_slog3_zu_arri_rec709.py [--dat <pfad>] [--out <pfad>] [--size 33]
"""
import argparse
import os
import sys

import numpy as np
import colour
from colour.models import log_decoding_SLog3, log_encoding_ARRILogC3

DAT_STANDARD = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Arri\Arri Alexa LogC to Rec709.dat"


def dat_lesen(pfad):
    """ARRI .dat einlesen: Zeile '3DLUTSIZE n', danach n^3 Tripel, Blau variiert am schnellsten."""
    groesse, werte = None, []
    with open(pfad, encoding="utf-8", errors="ignore") as f:
        for zeile in f:
            s = zeile.strip()
            if not s:
                continue
            if s.upper().startswith("3DLUTSIZE"):
                groesse = int(s.split()[1])
                continue
            teile = s.split()
            if len(teile) == 3:
                try:
                    werte.append([float(teile[0]), float(teile[1]), float(teile[2])])
                except ValueError:
                    pass
    a = np.array(werte, dtype=np.float64)
    n = groesse
    if n is None or len(a) != n ** 3:
        raise SystemExit(f"Unerwartetes .dat-Format: {len(a)} Werte, erwartet {n}^3")
    return a.reshape(n, n, n, 3), n   # Achsen [r, g, b]


def trilinear(lut, n, q):
    """Trilineare Interpolation in einer 3D-LUT. q: (M,3) in [0,1] -> (M,3)."""
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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dat", default=DAT_STANDARD, help="ARRI LogC->Rec709 .dat aus der Resolve-Installation")
    p.add_argument("--out", default="Sony_SLog3_zu_ARRI_Rec709.cube")
    p.add_argument("--size", type=int, default=33, help="Kantenlaenge der 3D-LUT (33 ist Standard)")
    a = p.parse_args()

    if not os.path.isfile(a.dat):
        sys.exit(
            f"ARRI-LUT nicht gefunden: {a.dat}\n"
            "Sie liegt bei einer Standardinstallation unter\n"
            r"  <ProgramData>\Blackmagic Design\DaVinci Resolve\Support\LUT\Arri\ ""\n"
            "Pfad sonst per --dat angeben."
        )

    dat, n_dat = dat_lesen(a.dat)
    print(f"ARRI-Wandlung gelesen: {n_dat}^3")

    n = a.size
    g = np.linspace(0, 1, n)
    R, G, B = np.meshgrid(g, g, g, indexing="ij")
    # .cube-Schreibreihenfolge: Rot variiert am schnellsten
    gitter = np.stack([R, G, B], axis=-1).transpose(2, 1, 0, 3).reshape(-1, 3)

    linear = log_decoding_SLog3(gitter)
    awg = colour.RGB_to_RGB(
        linear,
        colour.RGB_COLOURSPACES["S-Gamut3.Cine"],
        colour.RGB_COLOURSPACES["ARRI Wide Gamut 3"],
        chromatic_adaptation_transform="Bradford",
    )
    logc = np.clip(log_encoding_ARRILogC3(awg), 0, 1)
    rec709 = np.clip(trilinear(dat, n_dat, logc), 0, 1)

    with open(a.out, "w", encoding="utf-8") as f:
        f.write("# Sony S-Log3 / S-Gamut3.Cine -> ARRI AWG3 / LogC3 -> Rec.709 (ARRI-Rendering)\n")
        f.write("# Erzeugt von lut_slog3_zu_arri_rec709.py - reine Wandlung, kein Look\n")
        f.write(f"LUT_3D_SIZE {n}\n")
        for v in rec709:
            f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
    print(f"geschrieben: {a.out} ({len(rec709)} Zeilen)")

    # Kontrollwert: 18-%-Grau muss nach der Wandlung etwa auf Rec.709 0,39-0,42 landen
    grau = log_encoding_ARRILogC3(
        colour.RGB_to_RGB(
            np.array([[0.18, 0.18, 0.18]]),
            colour.RGB_COLOURSPACES["S-Gamut3.Cine"],
            colour.RGB_COLOURSPACES["ARRI Wide Gamut 3"],
            chromatic_adaptation_transform="Bradford",
        )
    )
    print("Kontrolle 18-%-Grau -> LogC", np.round(grau, 3),
          "-> Rec.709", np.round(trilinear(dat, n_dat, np.clip(grau, 0, 1)), 3))


if __name__ == "__main__":
    main()
