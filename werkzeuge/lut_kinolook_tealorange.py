# -*- coding: utf-8 -*-
"""Erzeugt die LUT fuer Node 5 der Kette: der Kino-Look obendrauf.

Was die LUT tut (Rec.709 -> Rec.709, rein gerechnet, kein Filmscan):
  1. weiche Kontrastkurve um Mittelgrau (Drehpunkt 0,42)
  2. Schwarzwerte anheben, damit Schwarz nicht zulaeuft ("Filmschwarz")
  3. Split-Tone: Schatten Richtung Teal, Lichter Richtung Warm - der klassische
     Kino-Farbkontrast (Teal/Orange)
  4. leichte Entsaettigung, damit der Farbkontrast nicht bunt wirkt

Drei Staerken: leicht / mittel / stark. Alles ist bewusst zurueckhaltend dosiert,
weil die Filmemulation davor (Node 4) den groessten Teil des Looks macht.

Voraussetzung:  py -m pip install numpy colour-science
Aufruf:         py lut_kinolook_tealorange.py [--out-dir <ordner>] [--size 33]
"""
import argparse
import os

import numpy as np
import colour


def weich(x):
    """Smoothstep - weiche 0..1-Ueberblendung ohne harte Kante."""
    return x * x * (3 - 2 * x)


# Grundwerte des Looks. SH = Farbversatz in den Schatten (Richtung Teal),
# HI = Farbversatz in den Lichtern (Richtung Warm), je als RGB-Offset.
SH = np.array([-0.020, 0.008, 0.022])
HI = np.array([0.028, 0.012, -0.030])
DREHPUNKT = 0.42

# Staerke-Stufen: (Kontrast, Schwarzanhebung, Split-Tone-Faktor, Saettigung)
STUFEN = {
    "leicht": (1.12, 0.030, 1.00, 0.92),
    "mittel": (1.19, 0.039, 1.53, 0.902),
    "stark":  (1.20, 0.040, 1.60, 0.90),
}


def kinolook(rgb, kontrast, schwarz, tonfaktor, saettigung):
    x = np.clip((rgb - DREHPUNKT) * kontrast + DREHPUNKT, 0, 1)
    x = x * (1 - schwarz) + schwarz
    luma = (0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2])[..., None]
    schatten = weich(np.clip(1 - luma / 0.5, 0, 1))
    lichter = weich(np.clip((luma - 0.5) / 0.5, 0, 1))
    x = np.clip(x + SH * tonfaktor * schatten + HI * tonfaktor * lichter, 0, 1)
    hsv = colour.RGB_to_HSV(x)
    hsv[..., 1] = np.clip(hsv[..., 1] * saettigung, 0, 1)
    return np.clip(colour.HSV_to_RGB(hsv), 0, 1)


def cube_schreiben(pfad, funktion, titel, n):
    g = np.linspace(0, 1, n)
    R, G, B = np.meshgrid(g, g, g, indexing="ij")
    # .cube-Schreibreihenfolge: Rot variiert am schnellsten
    gitter = np.stack([R, G, B], -1).transpose(2, 1, 0, 3).reshape(-1, 3).astype(np.float64)
    werte = np.clip(funktion(gitter), 0, 1)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(f"# {titel}\n")
        f.write("# Erzeugt von lut_kinolook_tealorange.py\n")
        f.write(f"LUT_3D_SIZE {n}\n")
        for v in werte:
            f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
    print("geschrieben:", pfad)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default=".")
    p.add_argument("--size", type=int, default=33)
    a = p.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    for name, werte in STUFEN.items():
        cube_schreiben(
            os.path.join(a.out_dir, f"Kinolook_Kontrast_TealOrange_{name}.cube"),
            lambda rgb, w=werte: kinolook(rgb, *w),
            f"Kino-Look {name}: Kontrast + Schwarzanhebung + Split-Tone Teal/Orange + leichte Entsaettigung (Rec.709 -> Rec.709)",
            a.size,
        )


if __name__ == "__main__":
    main()
