# -*- coding: utf-8 -*-
"""Erzeugt die LUT fuer Node 3 der Kette: ARRI Rec.709 -> ARRI LogC3 (Rueckwandlung), Fassung 2.

Wozu? Die Filmemulations-LUTs der Alexa-Familie erwarten ARRI LogC am Eingang. Node 2
liefert aber Rec.709, weil dort korrigiert und beurteilt wird. Node 3 dreht das Bild
also wieder ins Log-Format zurueck.

Warum eine zweite Fassung? Die erste (lut_rec709_zu_arri_logc.py) kehrt ARRIs
3D-Wandlung Punkt fuer Punkt per Newton-Verfahren um. In den Lichtern ist ARRIs
Wiedergabe so flach und an den Gamut-Raendern so beschnitten, dass diese Umkehrung
dort springt: sehr helle Haut (ab etwa 90 %) kippt nach Lachsrot, und auch die Mitten
werden etwas roeter. Diese Fassung kehrt stattdessen ein *analytisches, monotones
Modell* von ARRIs Rec.709-Wiedergabe um - sie kann nicht springen.

Modell der ARRI-Wiedergabe (vorwaerts), Voreinstellung --modell log:
  LogC3 (EI 800, AWG3) -> 3x3-Matrix auf den LogC-Werten
  -> je Kanal dieselbe 1D-Tonwertkurve -> Rec.709-Anzeigewert
Alternative --modell linear: LogC3 -> linear AWG3 -> Matrix -> linear Rec.709 -> Kurve.
Die Tonwertkurve wird aus der Grauachse der ARRI-Datei gelesen (Grauachse damit exakt),
streng monoton gemacht und glatt (monotone kubische Hermite-Interpolation) zwischen den
Stuetzstellen verbunden, ausserhalb linear fortgesetzt. Die Matrix wird per kleinster
Quadrate an die ARRI-Datei gefittet (nur unbeschnittene Stuetzstellen), mit der
Nebenbedingung Zeilensumme 1 (Grau bleibt Grau). Gemessen trifft die Matrix auf den
LogC-Werten ARRIs Wiedergabe in Lichtern und kraeftigen Farben deutlich besser als die
lineare Standard-Matrix, weil ARRI die Saettigung dort daempft.

Umkehrung (das, was die LUT enthaelt):
  Rec.709 -> inverse Tonwertkurve je Kanal -> inverse Matrix -> negative Werte auf 0
  (bei --modell linear: dazwischen linear dekodieren und wieder LogC3 kodieren)
Jeder Schritt ist monoton und stetig; Sprungstellen sind ausgeschlossen.

Die ARRI-Datei selbst wird nicht weitergegeben - das Skript liest sie lokal.

Voraussetzung:  py -m pip install numpy
Aufruf:         py lut_rec709_zu_arri_logc_v2.py [--dat <pfad>] [--out <pfad>] [--size 33]
                                                  [--modell log|linear] [--matrix fit|standard]
"""
import argparse
import os
import sys

import numpy as np

DAT_STANDARD = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Arri\Arri Alexa LogC to Rec709.dat"

# ARRI LogC3, EI 800 (dieselben Konstanten wie colour.models.log_encoding_ARRILogC3)
CUT, A, B, C, D, E, F = 0.010591, 5.555556, 0.052272, 0.247190, 0.385537, 5.367655, 0.092809
ECUT = E * CUT + F

# ARRI Wide Gamut 3 -> Rec.709 (beide D65, also ohne chromatische Anpassung)
AWG3_ZU_REC709 = np.array([
    [1.617523, -0.537287, -0.080237],
    [-0.070573, 1.334613, -0.264040],
    [-0.021102, -0.226954, 1.248056],
])


def logc_kodieren(x):
    x = np.asarray(x, dtype=np.float64)
    return np.where(x > CUT, C * np.log10(np.maximum(A * x + B, 1e-12)) + D, E * x + F)


def logc_dekodieren(t):
    t = np.asarray(t, dtype=np.float64)
    return np.where(t > ECUT, (10 ** ((t - D) / C) - B) / A, (t - F) / E)


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
                    werte.append([float(t) for t in teile])
                except ValueError:
                    pass
    a = np.array(werte, dtype=np.float64)
    n = groesse
    if n is None or len(a) != n ** 3:
        raise SystemExit(f"Unerwartetes .dat-Format: {len(a)} Werte, erwartet {n}^3")
    return a.reshape(n, n, n, 3), n   # Achsen [r, g, b]


def trilinear(lut, n, q):
    """Trilineare Interpolation in einer 3D-LUT mit Achsen [r, g, b]. q: (M,3) in [0,1]."""
    q = np.clip(q, 0, 1) * (n - 1)
    i0 = np.minimum(np.floor(q).astype(int), n - 2)
    f = q - i0
    i1 = i0 + 1
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


# ---------------------------------------------------------------------------
# Monotone Kurve (Fritsch-Carlson / PCHIP), ohne scipy
# ---------------------------------------------------------------------------
class MonotoneKurve:
    """Streng monoton steigende, stetig differenzierbare Kurve durch (x, y).

    Ausserhalb der Stuetzstellen linear mit der Randsteigung fortgesetzt.
    Mit umkehren() wird die exakte Umkehrfunktion ausgewertet (Bisektion auf dem
    jeweiligen Hermite-Segment - stets eindeutig, weil streng monoton)."""

    def __init__(self, x, y):
        self.x = np.asarray(x, dtype=np.float64)
        self.y = np.asarray(y, dtype=np.float64)
        h = np.diff(self.x)
        delta = np.diff(self.y) / h
        if np.any(delta <= 0):
            raise ValueError("Kurve ist nicht streng monoton")
        m = np.empty_like(self.y)
        m[0], m[-1] = delta[0], delta[-1]
        for k in range(1, len(self.x) - 1):
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k])   # harmonisches Mittel
        self.m = m

    def __call__(self, t):
        t = np.asarray(t, dtype=np.float64)
        x, y, m = self.x, self.y, self.m
        k = np.clip(np.searchsorted(x, t) - 1, 0, len(x) - 2)
        h = x[k + 1] - x[k]
        s = (t - x[k]) / h
        h00 = (1 + 2 * s) * (1 - s) ** 2
        h10 = s * (1 - s) ** 2
        h01 = s ** 2 * (3 - 2 * s)
        h11 = s ** 2 * (s - 1)
        innen = h00 * y[k] + h10 * h * m[k] + h01 * y[k + 1] + h11 * h * m[k + 1]
        unten = y[0] + m[0] * (t - x[0])
        oben = y[-1] + m[-1] * (t - x[-1])
        return np.where(t < x[0], unten, np.where(t > x[-1], oben, innen))

    def umkehren(self, w):
        w = np.asarray(w, dtype=np.float64)
        x, y, m = self.x, self.y, self.m
        k = np.clip(np.searchsorted(y, w) - 1, 0, len(x) - 2)
        lo, hi = x[k].copy(), x[k + 1].copy()
        for _ in range(48):
            mitte = 0.5 * (lo + hi)
            zu_klein = self(mitte) < w
            lo = np.where(zu_klein, mitte, lo)
            hi = np.where(zu_klein, hi, mitte)
        innen = 0.5 * (lo + hi)
        unten = x[0] + (w - y[0]) / m[0]
        oben = x[-1] + (w - y[-1]) / m[-1]
        return np.where(w < y[0], unten, np.where(w > y[-1], oben, innen))


# ---------------------------------------------------------------------------
# Modell der ARRI-Wiedergabe
# ---------------------------------------------------------------------------
class ArriModell:
    """forward: LogC3/AWG3 -> Rec.709-Anzeige;  inverse: Rec.709-Anzeige -> LogC3/AWG3.

    Die Tonwertkurve arbeitet auf der LogC-Achse: kurve(u) = ARRI-Grauwert bei LogC u.
    'Linear -> Anzeige' ist damit kurve(logc_kodieren(lin)).

    modell="log"    (Voreinstellung) Matrix wirkt auf die LogC-Werte:
                    forward = kurve(M * logc)        inverse = M^-1 * kurve^-1(rec709)
    modell="linear" Matrix wirkt auf lineares Licht:
                    forward = kurve(logc(M * lin))   inverse = logc(M^-1 * lin(kurve^-1))
    Gemessen trifft "log" ARRIs Wiedergabe in Lichtern und kraeftigen Farben deutlich
    besser (ARRI daempft die Saettigung im Log-Bereich) und haelt helle Haut im Farbton
    stabil; "linear" ist der klassische Weg und bleibt zum Vergleich waehlbar.
    """

    def __init__(self, dat, n, modell="log", matrix="fit"):
        u = np.linspace(0, 1, n)
        grau = np.array([dat[i, i, i].mean() for i in range(n)])
        # streng monoton erzwingen: laufendes Maximum plus winzige Mindeststeigung
        grau = np.maximum.accumulate(grau) + 1e-6 * u
        self.kurve = MonotoneKurve(u, grau)
        self.modell = modell
        if matrix == "fit":
            self.M = self._matrix_fitten(dat, n)
        elif modell == "linear":
            self.M = AWG3_ZU_REC709.copy()
        else:
            raise ValueError("Standard-Matrix gibt es nur fuer modell='linear'")
        self.M_inv = np.linalg.inv(self.M)

    # Linear Rec.709 -> Anzeige und zurueck
    def ton(self, lin):
        return self.kurve(logc_kodieren(lin))

    def ton_inv(self, anzeige):
        return logc_dekodieren(self.kurve.umkehren(anzeige))

    def forward(self, logc):
        logc = np.asarray(logc, dtype=np.float64)
        if self.modell == "log":
            return self.kurve(logc @ self.M.T)
        return self.ton(logc_dekodieren(logc) @ self.M.T)

    def inverse(self, rec709):
        y = np.clip(np.asarray(rec709, dtype=np.float64), 0, 1)
        if self.modell == "log":
            return np.maximum(self.kurve.umkehren(y) @ self.M_inv.T, 0.0)
        lin_awg = np.maximum(self.ton_inv(y) @ self.M_inv.T, 0.0)   # ausserhalb AWG3: auf 0
        return logc_kodieren(lin_awg)

    def _matrix_fitten(self, dat, n):
        """Kleinste Quadrate an die ARRI-Datei, je Zeile Summe 1 (Grau bleibt Grau).

        Ziel ist kurve^-1(ARRI(x)) - also der Wert vor der Tonwertkurve. Benutzt werden
        nur Stuetzstellen, deren Ausgabe nirgends beschnitten ist (0,03 < Kanal < 0,9);
        dort ist ARRIs Wiedergabe eindeutig umkehrbar."""
        g = np.linspace(0, 1, n)
        R, G, Bb = np.meshgrid(g, g, g, indexing="ij")
        x = np.stack([R, G, Bb], -1).reshape(-1, 3)
        y = dat.reshape(-1, 3)
        ok = ((y > 0.03) & (y < 0.9)).all(1)
        x, y = x[ok], y[ok]
        if self.modell == "log":
            quelle, ziel = x, self.kurve.umkehren(y)
            gewicht = np.ones(len(x))
        else:
            quelle, ziel = logc_dekodieren(x), self.ton_inv(y)
            gewicht = 1.0 / np.maximum(quelle.mean(1), 1e-3)   # relative Fehler
        M = np.empty((3, 3))
        for z in range(3):
            # Zeilensumme 1:  ziel_z - q_z = a*(q_a - q_z) + b*(q_b - q_z)
            andere = [k for k in range(3) if k != z]
            Xm = np.stack([quelle[:, k] - quelle[:, z] for k in andere], 1) * gewicht[:, None]
            ym = (ziel[:, z] - quelle[:, z]) * gewicht
            koeff, *_ = np.linalg.lstsq(Xm, ym, rcond=None)
            M[z, andere] = koeff
            M[z, z] = 1 - koeff.sum()
        return M


def cube_gitter(n):
    g = np.linspace(0, 1, n)
    R, G, B = np.meshgrid(g, g, g, indexing="ij")
    # .cube-Schreibreihenfolge: Rot variiert am schnellsten
    return np.stack([R, G, B], -1).transpose(2, 1, 0, 3).reshape(-1, 3)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dat", default=DAT_STANDARD)
    p.add_argument("--out", default="ARRI_Rec709_zu_LogC_v2.cube")
    p.add_argument("--size", type=int, default=33)
    p.add_argument("--modell", choices=["log", "linear"], default="log",
                   help="log = Matrix auf LogC-Werten (Voreinstellung), linear = Matrix auf linearem Licht")
    p.add_argument("--matrix", choices=["fit", "standard"], default="fit",
                   help="fit = an die ARRI-Datei angepasst (Voreinstellung); standard = AWG3->Rec.709 (nur mit --modell linear)")
    a = p.parse_args()

    if not os.path.isfile(a.dat):
        sys.exit(f"ARRI-LUT nicht gefunden: {a.dat}  (Pfad per --dat angeben)")

    dat, n_dat = dat_lesen(a.dat)
    print(f"ARRI-Wandlung gelesen: {n_dat}^3")
    if a.modell == "log" and a.matrix == "standard":
        sys.exit("--matrix standard geht nur mit --modell linear")
    modell = ArriModell(dat, n_dat, a.modell, a.matrix)
    print(f"Modell: Matrix auf {'LogC-Werten' if a.modell == 'log' else 'linearem Licht'} ({a.matrix}):")
    for zeile in modell.M:
        print("  " + "  ".join(f"{v:+.5f}" for v in zeile))

    gitter = cube_gitter(a.size)
    logc = np.clip(modell.inverse(gitter), 0, 1)
    if not np.isfinite(logc).all():
        sys.exit("Fehler: ungueltige Werte in der LUT")

    # Kontrolle: Grauachse hin und zurueck
    grau = np.linspace(0, 1, 11)[:, None].repeat(3, 1)
    rest = np.abs(trilinear(dat, n_dat, np.clip(modell.inverse(grau), 0, 1)) - grau).max()
    print(f"Grauachse ARRI(LUT(x)) - x: groesste Abweichung {rest:.5f}")

    with open(a.out, "w", encoding="utf-8") as f:
        f.write("# ARRI Rec.709 -> ARRI LogC3 / AWG3 (EI 800), Fassung 2\n")
        f.write("# Umkehrung eines monotonen Modells der ARRI-Rec.709-Wiedergabe\n")
        f.write("# (Tonwertkurve je Kanal + Matrix) - stabil auch bei sehr heller Haut\n")
        f.write("# Erzeugt von lut_rec709_zu_arri_logc_v2.py\n")
        f.write(f"LUT_3D_SIZE {a.size}\n")
        for v in logc:
            f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
    print(f"geschrieben: {a.out} ({len(logc)} Zeilen)")


if __name__ == "__main__":
    main()
