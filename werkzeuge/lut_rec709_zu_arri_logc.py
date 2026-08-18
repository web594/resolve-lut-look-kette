# -*- coding: utf-8 -*-
"""Erzeugt die LUT fuer Node 3 der Kette: ARRI Rec.709 -> ARRI LogC3 (Rueckwandlung).

Wozu? Die Filmemulations-LUTs der Alexa-Familie erwarten ARRI LogC am Eingang. Node 2
liefert aber Rec.709, weil dort korrigiert und beurteilt wird. Node 3 dreht das Bild
also wieder ins Log-Format zurueck - genau bis zu dem Arbeitspunkt, den die Film-LUTs
erwarten.

Rechenweg: numerische Umkehrung von ARRIs eigenem Rec.709-Rendering
("Arri Alexa LogC to Rec709.dat" aus der Resolve-Installation) per gedaempfter
Fixpunkt-Iteration mit diagonaler Jacobi-Naeherung. Die ARRI-Datei selbst wird nicht
weitergegeben - das Skript liest sie lokal.

Wichtig: Diese LUT ist eine *mathematische* Umkehrung. Kommerzielle Sets (z. B. ImpulZ
"Alexa Rec709 to LOG-C") sind zusaetzlich auf ihre eigene Filmstock-Familie abgestimmt.
Wer so ein Set besitzt, nimmt dessen Wandlung; wer nicht, kommt mit dieser hier sehr
nah heran (Abweichung siehe referenzen/luts-selbst-erzeugen.md).

Voraussetzung:  py -m pip install numpy
Aufruf:         py lut_rec709_zu_arri_logc.py [--dat <pfad>] [--out <pfad>] [--size 33]
"""
import argparse
import os
import sys

import numpy as np

DAT_STANDARD = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Arri\Arri Alexa LogC to Rec709.dat"


def dat_lesen(pfad):
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
                    werte.append([float(t) for t in teile])
                except ValueError:
                    pass
    a = np.array(werte, dtype=np.float64)
    n = groesse
    if n is None or len(a) != n ** 3:
        raise SystemExit(f"Unerwartetes .dat-Format: {len(a)} Werte, erwartet {n}^3")
    return a.reshape(n, n, n, 3), n


def trilinear(lut, n, q):
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


def umkehren(dat, n_dat, ziel, schritte=60, eps=2e-3, daempfung=1.0):
    """Sucht x mit F(x) ~ ziel (Newton-Verfahren mit voller 3x3-Jacobi-Matrix).

    Die ARRI-Wandlung mischt die Kanaele (Saettigung/Gamut), deshalb reicht eine
    kanalweise Umkehrung nicht - erst die volle Matrix trifft auch kraeftige Farben.
    Die Matrix wird per Differenzenquotient geschaetzt und mit einer kleinen
    Tikhonov-Regularisierung invertiert, damit flache Stellen (Clipping) nicht
    explodieren. Zusaetzlich Rueckwaertssuche: ein Schritt wird nur angenommen,
    wenn er den Restfehler verkleinert.
    """
    x = ziel.copy()
    rest = ziel - trilinear(dat, n_dat, x)
    fehler = np.sum(rest ** 2, axis=1)
    for _ in range(schritte):
        if fehler.max() < 1e-10:
            break
        # Jacobi-Matrix J[:, i, k] = dF_i / dx_k
        J = np.empty((len(x), 3, 3))
        for k in range(3):
            xp, xm = x.copy(), x.copy()
            xp[:, k] = np.clip(x[:, k] + eps, 0, 1)
            xm[:, k] = np.clip(x[:, k] - eps, 0, 1)
            dx = np.maximum(xp[:, k] - xm[:, k], 1e-9)
            J[:, :, k] = (trilinear(dat, n_dat, xp) - trilinear(dat, n_dat, xm)) / dx[:, None]
        # (J^T J + lambda I) s = J^T r   - regularisierter Newton-Schritt
        JtJ = np.einsum("nij,nik->njk", J, J)
        Jtr = np.einsum("nij,ni->nj", J, rest)
        JtJ[:, 0, 0] += 1e-4
        JtJ[:, 1, 1] += 1e-4
        JtJ[:, 2, 2] += 1e-4
        schritt = np.linalg.solve(JtJ, Jtr[..., None])[..., 0]
        s = daempfung
        for _ in range(6):   # Rueckwaertssuche
            kandidat = np.clip(x + s * schritt, 0, 1)
            neu = ziel - trilinear(dat, n_dat, kandidat)
            neuer_fehler = np.sum(neu ** 2, axis=1)
            besser = neuer_fehler < fehler
            if besser.all():
                break
            x = np.where(besser[:, None], kandidat, x)
            rest = np.where(besser[:, None], neu, rest)
            fehler = np.where(besser, neuer_fehler, fehler)
            s *= 0.5
        else:
            kandidat, neu, neuer_fehler = x, rest, fehler
        besser = neuer_fehler < fehler
        x = np.where(besser[:, None], kandidat, x)
        rest = np.where(besser[:, None], neu, rest)
        fehler = np.where(besser, neuer_fehler, fehler)
    return x


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dat", default=DAT_STANDARD)
    p.add_argument("--out", default="ARRI_Rec709_zu_LogC.cube")
    p.add_argument("--size", type=int, default=33)
    a = p.parse_args()

    if not os.path.isfile(a.dat):
        sys.exit(f"ARRI-LUT nicht gefunden: {a.dat}  (Pfad per --dat angeben)")

    dat, n_dat = dat_lesen(a.dat)
    print(f"ARRI-Wandlung gelesen: {n_dat}^3")

    n = a.size
    g = np.linspace(0, 1, n)
    R, G, B = np.meshgrid(g, g, g, indexing="ij")
    gitter = np.stack([R, G, B], -1).transpose(2, 1, 0, 3).reshape(-1, 3)

    logc = umkehren(dat, n_dat, gitter)
    rest = np.abs(trilinear(dat, n_dat, logc) - gitter).max()
    print(f"groesster Restfehler der Umkehrung: {rest:.5f}")

    with open(a.out, "w", encoding="utf-8") as f:
        f.write("# ARRI Rec.709 -> ARRI LogC3 (numerische Umkehrung des ARRI-Rec709-Renderings)\n")
        f.write("# Erzeugt von lut_rec709_zu_arri_logc.py\n")
        f.write(f"LUT_3D_SIZE {n}\n")
        for v in logc:
            f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
    print(f"geschrieben: {a.out} ({len(logc)} Zeilen)")


if __name__ == "__main__":
    main()
