# -*- coding: utf-8 -*-
"""Erzeugt die LUT fuer Node 4 der Kette: freie Filmemulation (Negativ + Kopierfilm).

Das ist der kostenlose Ersatz fuer eine gekaufte Filmemulation. Statt einen echten
Filmscan nachzubilden, rechnet dieses Skript den Weg nach, den Licht im Kinoprozess
tatsaechlich nimmt:

  ARRI LogC  ->  Belichtung (log E)
             ->  NEGATIV: Dichtekurve je Schicht (Fuss, gerader Teil, Schulter)
             ->  Maskierung/Kopplung zwischen den Schichten (Farbcharakter)
             ->  KOPIERFILM: zweite Dichtekurve mit hoeherer Steilheit
             ->  Durchlaessigkeit  ->  Rec.709

Daraus ergibt sich von selbst, was ein Film-Look ausmacht: Schwarz laeuft nie ganz zu
(Fuss der Kurve), Lichter brennen nicht hart aus (Schulter), der Kontrast entsteht im
Kopierfilm, und die Farben verschieben sich in den Extremen leicht gegeneinander.

Die Parameter sind so eingestellt, dass sich die typischen Kennwerte einer Kinokopie
ergeben: angehobenes Filmschwarz statt zulaufender Tiefen, 18-%-Grau bei rund 0,30 und
eine Schulter, die Weiss bei etwa 0,93 auslaufen laesst statt es abzuschneiden.
Es ist bewusst KEIN Nachbau eines bestimmten kommerziellen LUT-Satzes - die Kurven
stammen aus dem Modell, nicht aus fremden LUT-Daten.

Voraussetzung:  py -m pip install numpy colour-science
Aufruf:         py lut_filmemulation_negativ_print.py [--out-dir <ordner>] [--size 33]
                py lut_filmemulation_negativ_print.py --kontrolle    (Kennwerte ausgeben)
"""
import argparse
import os

import numpy as np
import colour
from colour.models import log_decoding_ARRILogC3


def weich_ab(u, weichheit):
    """Weiche untere Begrenzung bei 0 (Fuss der Kurve) - Softplus."""
    return weichheit * np.logaddexp(0.0, u / weichheit)


def weich_auf(u, grenze, weichheit):
    """Weiche obere Begrenzung bei 'grenze' (Schulter der Kurve)."""
    return grenze - weich_ab(grenze - u, weichheit)


# --- Negativ ---------------------------------------------------------------
# Steilheit je Schicht leicht unterschiedlich: das erzeugt den typischen
# Farbversatz zwischen Schatten und Lichtern, den man an Film erkennt.
GAMMA_NEG = 0.7387 * np.array([0.98, 1.00, 1.02])
DICHTE_MAX = 2.3756 * np.array([0.99, 1.00, 1.01])  # Schulter des Negativs
FUSS = 0.6943                                      # Weichheit des Kurvenfusses
SCHULTER = 0.7334                                  # Weichheit der Schulter

# Kopplung zwischen den Schichten (Maskierung). Zeilen = Ergebnis, Spalten = Quelle.
KOPPLUNG = np.array([
    [1.000, -0.055, -0.015],
    [-0.045, 1.000, -0.040],
    [-0.010, -0.060, 1.000],
])

# --- Kopierfilm ------------------------------------------------------------
GAMMA_PRINT = 3.3996
DICHTE_PRINT_MAX = 3.6445
FUSS_PRINT = 0.9038
SCHULTER_PRINT = 0.2553
PRINT_ABGLEICH = np.array([1.0000, 1.0000, 1.0000])   # Farbabgleich der Kopiermaschine
DICHTE_BEZUG = 1.1928                                 # Belichtung der Kopie

# Waerme der Lichter: Kinokopien laufen in den Lichtern leicht ins Warme.
# 0.0 = voellig neutral, 0.03 = deutlich. Wird erst NACH dem Neutral-Abgleich
# aufgetragen und wirkt nur oberhalb der Mitteltoene.
WAERME_LICHTER = 0.015


def _roh(logc):
    """Der reine Filmprozess ohne Neutral-Abgleich."""
    linear = np.clip(log_decoding_ARRILogC3(logc), 1e-6, None)
    log_e = np.log10(linear)

    # Negativ: gerader Teil mit weichem Fuss und weicher Schulter
    dichte = weich_auf(weich_ab(GAMMA_NEG * (log_e + 2.0), FUSS), DICHTE_MAX, SCHULTER)
    dichte = dichte @ KOPPLUNG.T                      # Kopplung der Schichten

    # Kopierfilm: sieht die Negativdichte als Belichtung, invertiert und steilt auf
    v = GAMMA_PRINT * (DICHTE_BEZUG - dichte) * PRINT_ABGLEICH
    dichte_print = weich_auf(weich_ab(v, FUSS_PRINT), DICHTE_PRINT_MAX, SCHULTER_PRINT)

    # Dichte -> Durchlaessigkeit -> Anzeige.
    # Bezug ist die hellste moegliche Kopie (Negativ maximal dicht -> Kopie klar).
    weiss = 10.0 ** (-weich_ab(GAMMA_PRINT * (DICHTE_BEZUG - DICHTE_MAX.mean()), FUSS_PRINT))
    rgb = np.clip(10.0 ** (-dichte_print) / weiss, 0, 1)
    return np.clip(colour.models.eotf_inverse_BT1886(rgb, L_B=0.0, L_W=1.0), 0, 1)


# Neutral-Abgleich ("Kopierlicht"): die Schichten haben unterschiedliche Steilheit,
# dadurch bekaeme ein grauer Keil einen leichten Farbstich. Der Abgleich zieht Rot und
# Blau ueber den ganzen Tonwertumfang auf den Gruenkanal - Grau bleibt exakt Grau,
# waehrend farbige Bildstellen ihren Filmcharakter behalten.
_STUETZ = np.linspace(0, 1, 129)
_GRAU = _roh(np.stack([_STUETZ, _STUETZ, _STUETZ], 1))


def film(logc):
    """ARRI LogC3 (0..1) -> Rec.709 (0..1) ueber Negativ + Kopierfilm."""
    rgb = _roh(logc)
    aus = rgb.copy()
    for k in (0, 2):
        x, y = _GRAU[:, k], _GRAU[:, 1]
        reihe = np.argsort(x)
        aus[..., k] = np.interp(rgb[..., k], x[reihe], y[reihe])
    if WAERME_LICHTER:
        luma = 0.2126 * aus[..., 0] + 0.7152 * aus[..., 1] + 0.0722 * aus[..., 2]
        oben = np.clip((luma - 0.45) / 0.55, 0, 1) ** 2
        aus[..., 0] += WAERME_LICHTER * oben
        aus[..., 2] -= WAERME_LICHTER * oben
    return np.clip(aus, 0, 1)


def cube_schreiben(pfad, funktion, titel, n):
    g = np.linspace(0, 1, n)
    R, G, B = np.meshgrid(g, g, g, indexing="ij")
    gitter = np.stack([R, G, B], -1).transpose(2, 1, 0, 3).reshape(-1, 3).astype(np.float64)
    werte = np.clip(funktion(gitter), 0, 1)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(f"# {titel}\n")
        f.write("# Erzeugt von lut_filmemulation_negativ_print.py\n")
        f.write(f"LUT_3D_SIZE {n}\n")
        for v in werte:
            f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
    print("geschrieben:", pfad)


def kontrolle():
    """Kennwerte der Kurve ausgeben - zum Nachpruefen nach Parameteraenderungen."""
    g = np.linspace(0, 1, 11)
    aus = film(np.stack([g, g, g], 1))
    print("LogC ein | Rec.709 aus (R/G/B)")
    for k in range(11):
        print(f"  {g[k]:.2f}   {aus[k,0]:.4f} {aus[k,1]:.4f} {aus[k,2]:.4f}")
    mitte = film(np.array([[0.391, 0.391, 0.391]]))
    print(f"18-%-Grau (LogC 0,391) -> {mitte[0,1]:.4f}   (Zielbereich 0,29-0,33)")
    print(f"Schwarz -> {aus[0,1]:.4f}  (Filmschwarz, soll nicht 0 sein)")
    print(f"Weiss  -> {aus[-1,1]:.4f}  (soll unter 1,0 bleiben - weiche Schulter)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default=".")
    p.add_argument("--size", type=int, default=33)
    p.add_argument("--kontrolle", action="store_true")
    a = p.parse_args()
    if a.kontrolle:
        kontrolle()
        return
    os.makedirs(a.out_dir, exist_ok=True)
    cube_schreiben(
        os.path.join(a.out_dir, "Filmemulation_Negativ_Print_ARRI_LogC.cube"),
        film,
        "Filmemulation Negativ + Kopierfilm (ARRI LogC3 -> Rec.709), frei gerechnet",
        a.size,
    )


if __name__ == "__main__":
    main()
