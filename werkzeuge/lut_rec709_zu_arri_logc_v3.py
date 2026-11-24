# -*- coding: utf-8 -*-
"""Erzeugt die LUT fuer Node 3 der Kette: ARRI Rec.709 -> ARRI LogC3 (Rueckwandlung), Fassung 3.

Warum eine dritte Fassung? Fassung 2 (lut_rec709_zu_arri_logc_v2.py) kehrt ein monotones
Modell von ARRIs Rec.709-Wiedergabe exakt um - bis ganz oben. ARRIs Schulter ist dort aber
so flach (LogC 0,78 -> 1,00 ergibt nur noch Anzeige 0,97 -> 1,00), dass die Umkehrung im
letzten Gitterschritt um ein Vielfaches springt: Grauachse 0,97 -> 0,778, 1,00 -> 1,000.
Mathematisch richtig - aber ein UEBERSTEUERTER Kanal (Webcam, 8-Bit-Film mit ausgefressener
Stirn) ist keine "sehr helle Farbe", sondern abgeschnitten. Fassung 2 macht aus R = 255 im
Gesicht ein extrem helles Rot, und wo der Rotkanal im Bild an den Anschlag stoesst, entsteht
eine scharf begrenzte lachs-orange Flaeche (gemessen 23.11.2026 an einem Webcam-Film).

Was Fassung 3 anders macht - nur in den obersten Lichtern, darunter ist sie Fassung 2:
  1. Knie: Die Umkehrung folgt ARRIs Schulter nur bis Anzeige KNIE (0,92). Dort ist ihre
     Steigung schon doppelt so gross wie in den Mitten (1,13 gegen 0,55): ARRI hat die
     oberen 30 % des LogC-Umfangs in die oberen 8 % der Anzeige gepresst, und was ein
     8-Bit-Film dort noch traegt, reicht fuer eine Umkehrung nicht. Darueber laeuft die
     Kurve als Parabel weiter - Wert UND Steigung stetig am Knie, Steigung waechst bis
     Anzeige 1,0 nur auf das ENDE_STEIGUNG-fache (2,0) statt auf das Zehnfache.
  2. Entsaettigung in den Lichtern: Liegt der groesste Kanal ueber ENTS_AB (0,88), wird die
     Farbe zum Weiss ihrer Helligkeit hin entsaettigt, sanft (smoothstep) bis ENTS_STAERKE (0,3)
     am Anschlag - wie Film, dessen Lichter zum Weiss hin ausbleichen. Ein uebersteuerter
     Kanal gibt so keinen Farbton-Sprung mehr.
Beides ist stetig und monoton. Unter Anzeige 0,875 (Gitterpunkt 28 von 32) sind alle
Gitterpunkte gleich Fassung 2 - richtig belichtete Projekte sehen gleich aus.

Ausserdem stehen hier kleine Helfer zum Nachmessen (cube_lesen, anwenden mit trilinearer
und tetraedrischer Interpolation, farbton) - die Pruefung im Runner (test_lut_v3.py) nutzt sie.

Voraussetzung:  py -m pip install numpy ; lut_rec709_zu_arri_logc_v2.py im selben Ordner
Aufruf:         py lut_rec709_zu_arri_logc_v3.py [--dat <pfad>] [--out <pfad>] [--size 33]
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lut_rec709_zu_arri_logc_v2 as v2  # noqa: E402  (Modell der ARRI-Wiedergabe)

KNIE = 0.92           # Anzeige, bis zu der die Umkehrung der ARRI-Schulter folgt
ENDE_STEIGUNG = 2.0   # Steigung bei Anzeige 1,0 als Vielfaches der Steigung am Knie
ENTS_AB = 0.88        # ab diesem groessten Kanal beginnt die Entsaettigung
ENTS_STAERKE = 0.3    # Anteil der Entsaettigung, wenn der groesste Kanal am Anschlag ist
LUMA = np.array([0.2126, 0.7152, 0.0722])


def _smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def entsaettigen(rgb, ab=ENTS_AB, staerke=ENTS_STAERKE):
    """Farben, deren groesster Kanal nahe am Anschlag liegt, zum Weiss ihrer Helligkeit ziehen.

    Ziel ist das Grau in Hoehe des groessten Kanals: Der groesste Kanal bleibt, die anderen
    ruecken zu ihm auf. So bleibt jeder Kanal monoton steigend (heller hinein -> heller
    heraus); ein Ziehen zur Luma hin senkte den groessten Kanal und kehrte die Rampe um."""
    rgb = np.asarray(rgb, dtype=np.float64)
    gross = rgb.max(-1, keepdims=True)
    w = staerke * _smoothstep((gross - ab) / max(1.0 - ab, 1e-6))
    return gross - (gross - rgb) * (1.0 - w)


class SanfteUmkehrung:
    """Fassung 3: Umkehrung mit Knie und Entsaettigung. ``kurve`` ist eine MonotoneKurve
    (LogC -> Anzeige), ``M_inv`` die inverse Matrix des Modells (auf LogC-Werten)."""

    def __init__(self, kurve, M_inv, knie=KNIE, ende_steigung=ENDE_STEIGUNG,
                 ents_ab=ENTS_AB, ents_staerke=ENTS_STAERKE):
        self.kurve, self.M_inv = kurve, np.asarray(M_inv, dtype=np.float64)
        self.knie, self.ents_ab, self.ents_staerke = knie, ents_ab, ents_staerke
        self.u_k = float(kurve.umkehren(np.array([knie]))[0])
        d = 1e-5
        self.s_k = float((kurve.umkehren(np.array([knie + d]))[0]
                          - kurve.umkehren(np.array([knie - d]))[0]) / (2 * d))
        # u(y) = u_k + s_k t + c t^2, t = y - knie;  u'(1) = ende_steigung * s_k
        self.c = (ende_steigung - 1.0) * self.s_k / (2.0 * max(1.0 - knie, 1e-6))

    def ton_inv(self, y):
        y = np.asarray(y, dtype=np.float64)
        t = np.maximum(y - self.knie, 0.0)
        oben = self.u_k + self.s_k * t + self.c * t * t
        return np.where(y <= self.knie, self.kurve.umkehren(np.minimum(y, self.knie)), oben)

    def inverse(self, rec709):
        y = np.clip(np.asarray(rec709, dtype=np.float64), 0, 1)
        y = entsaettigen(y, self.ents_ab, self.ents_staerke)
        return np.maximum(self.ton_inv(y) @ self.M_inv.T, 0.0)


# ---------------------------------------------------------------------------
# Helfer zum Nachmessen
# ---------------------------------------------------------------------------
def cube_lesen(pfad):
    """.cube lesen -> (lut[r, g, b, 3], n). In der Datei variiert Rot am schnellsten."""
    n, werte = None, []
    with open(pfad, encoding="utf-8", errors="ignore") as f:
        for zeile in f:
            s = zeile.strip()
            if not s or s.startswith("#"):
                continue
            if s.upper().startswith("LUT_3D_SIZE"):
                n = int(s.split()[1])
                continue
            teile = s.split()
            if len(teile) == 3:
                try:
                    werte.append([float(t) for t in teile])
                except ValueError:
                    pass
    a = np.array(werte, dtype=np.float64)
    if n is None or len(a) != n ** 3:
        raise ValueError(f"{pfad}: kein 3D-.cube ({len(a)} Werte)")
    return a.reshape(n, n, n, 3).transpose(2, 1, 0, 3), n


def _tetraedrisch(lut, n, q):
    q = np.clip(q, 0, 1) * (n - 1)
    i0 = np.minimum(np.floor(q).astype(int), n - 2)
    f = q - i0
    r, g, b = i0[:, 0], i0[:, 1], i0[:, 2]
    fr, fg, fb = f[:, 0], f[:, 1], f[:, 2]

    def P(dr, dg, db):
        return lut[r + dr, g + dg, b + db]

    c000, c111 = P(0, 0, 0), P(1, 1, 1)
    aus = np.empty_like(q)
    faelle = [
        ((fr >= fg) & (fg >= fb), (fr, fg, fb), (P(1, 0, 0), P(1, 1, 0))),
        ((fr >= fb) & (fb > fg), (fr, fb, fg), (P(1, 0, 0), P(1, 0, 1))),
        ((fb > fr) & (fr >= fg), (fb, fr, fg), (P(0, 0, 1), P(1, 0, 1))),
        ((fg > fr) & (fr >= fb), (fg, fr, fb), (P(0, 1, 0), P(1, 1, 0))),
        ((fg >= fb) & (fb > fr), (fg, fb, fr), (P(0, 1, 0), P(0, 1, 1))),
        ((fb > fg) & (fg > fr), (fb, fg, fr), (P(0, 0, 1), P(0, 1, 1))),
    ]
    erledigt = np.zeros(len(q), bool)
    for maske, (a, b_, c), (p1, p2) in faelle:
        m = maske & ~erledigt
        erledigt |= m
        a, b_, c = a[m, None], b_[m, None], c[m, None]
        aus[m] = (1 - a) * c000[m] + (a - b_) * p1[m] + (b_ - c) * p2[m] + c * c111[m]
    return aus


def anwenden(lut, n, rgb, art="tri"):
    """3D-LUT auf Farben (..., 3) anwenden, art = "tri" (trilinear) oder "tetra"."""
    rgb = np.asarray(rgb, dtype=np.float64)
    form = rgb.shape
    q = rgb.reshape(-1, 3)
    aus = v2.trilinear(lut, n, q) if art == "tri" else _tetraedrisch(lut, n, q)
    return aus.reshape(form)


def farbton(rgb):
    """Farbton (Grad, HSV) und Saettigung (max - min) je Farbe."""
    rgb = np.asarray(rgb, dtype=np.float64)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    gross, klein = rgb.max(-1), rgb.min(-1)
    chroma = gross - klein
    sicher = np.where(chroma > 1e-9, chroma, 1.0)
    h = np.where(gross == r, ((g - b) / sicher) % 6,
                 np.where(gross == g, (b - r) / sicher + 2, (r - g) / sicher + 4)) * 60.0
    return np.where(chroma > 1e-9, h, 0.0), chroma


def lut_v3_rechnen(dat_pfad=v2.DAT_STANDARD, groesse=33):
    """Gitterwerte der Fassung 3 (in .cube-Reihenfolge) und das Modell."""
    dat, n_dat = v2.dat_lesen(dat_pfad)
    modell = v2.ArriModell(dat, n_dat, "log", "fit")
    sanft = SanfteUmkehrung(modell.kurve, modell.M_inv)
    werte = np.clip(sanft.inverse(v2.cube_gitter(groesse)), 0, 1)
    return werte, modell, sanft


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dat", default=v2.DAT_STANDARD)
    p.add_argument("--out", default="ARRI_Rec709_zu_LogC_v3.cube")
    p.add_argument("--size", type=int, default=33)
    a = p.parse_args()

    if not os.path.isfile(a.dat):
        sys.exit(f"ARRI-LUT nicht gefunden: {a.dat}  (Pfad per --dat angeben)")
    logc, modell, sanft = lut_v3_rechnen(a.dat, a.size)
    if not np.isfinite(logc).all():
        sys.exit("Fehler: ungueltige Werte in der LUT")
    print(f"Knie bei Anzeige {sanft.knie:.2f}: LogC {sanft.u_k:.4f}, Steigung {sanft.s_k:.3f}; "
          f"Anzeige 1,0 -> LogC {float(sanft.ton_inv(np.array([1.0]))[0]):.4f}")

    with open(a.out, "w", encoding="utf-8") as f:
        f.write("# ARRI Rec.709 -> ARRI LogC3 / AWG3 (EI 800), Fassung 3\n")
        f.write("# wie Fassung 2, aber oben mit Knie (0,92) und Entsaettigung in den Lichtern:\n")
        f.write("# ein uebersteuerter Kanal gibt keinen Farbsprung mehr\n")
        f.write("# Erzeugt von lut_rec709_zu_arri_logc_v3.py\n")
        f.write(f"LUT_3D_SIZE {a.size}\n")
        for v in logc:
            f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
    print(f"geschrieben: {a.out} ({len(logc)} Zeilen)")


if __name__ == "__main__":
    main()
