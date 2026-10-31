"""AISC Manual Tables 6-2a, 6-2b, 6-3 and 6-4, reproduced in Design Guide 6 (Figures 2-7, 2-8, 2-13, 2-16). Not a standard.

Cross-section strength points of the plastic stress distribution method, without length effects. Units N, mm, MPa.
Each function returns {point: (P, M)}, from pure compression (A) to pure flexure (B).
"""
import math


def table_6_2a(*, Fy, Fyr, fc, h1, h2, As, Asr, Asrs, c, Zs, d, bf, tf, tw) -> dict:
    """Encased W-shape about its major axis; bars at h2/2 - c from the center and side bars at the centerline (Asrs)."""
    Ac = h1 * h2 - As - Asr
    Zr = (Asr - Asrs) * (h2 / 2 - c)
    Zc = h1 * h2**2 / 4 - Zs - Zr
    MD = Fy * Zs + Fyr * Zr + 0.85 * fc * Zc / 2
    hn = (0.85 * fc * (Ac + Asrs) - 2 * Fyr * Asrs) / (2 * (0.85 * fc * (h1 - tw) + 2 * Fy * tw))
    if hn <= d / 2 - tf:
        Zsn = tw * hn**2
    else:
        hn = ((0.85 * fc * (Ac + As - d * bf + Asrs) - 2 * Fy * (As - d * bf) - 2 * Fyr * Asrs)
              / (2 * (0.85 * fc * (h1 - bf) + 2 * Fy * bf)))
        if hn <= d / 2:
            Zsn = Zs - bf * (d / 2 - hn) * (d / 2 + hn)
        else:
            hn = (0.85 * fc * (Ac + As + Asrs) - 2 * Fy * As - 2 * Fyr * Asrs) / (2 * 0.85 * fc * h1)
            Zsn = Zs
    MB = MD - Fy * Zsn - 0.85 * fc * (h1 * hn**2 - Zsn) / 2
    return {"A": (Fy * As + Fyr * Asr + 0.85 * fc * Ac, 0.0), "C": (0.85 * fc * Ac, MB), "D": (0.85 * fc * Ac / 2, MD), "B": (0.0, MB)}


def table_6_2b(*, Fy, Fyr, fc, h1, h2, As, Asr, Asr_outer, c, Zs, bf, tf, tw) -> dict | None:
    """Encased W-shape about its minor axis. As in Example 2.4 of the guide, Zr takes the bars at h2/2 - c only (Asr_outer).

    None when the neutral axis falls in the web, a case that the table does not give.
    """
    Ac = h1 * h2 - As - Asr
    Zr = Asr_outer * (h2 / 2 - c)
    Zc = h1 * h2**2 / 4 - Zs - Zr
    MD = Fy * Zs + Fyr * Zr + 0.85 * fc * Zc / 2
    PE = Fy * As + 0.85 * fc * (Ac - h1 / 2 * (h2 - bf) + Asr / 2)
    ME = MD - Zs * Fy - 0.85 * fc * (h1 * bf**2 / 4 - Zs) / 2
    hn = (0.85 * fc * (Ac + As) - 2 * Fy * As) / (2 * 0.85 * fc * h1)
    if hn > bf / 2:
        Zsn = Zs
    else:
        hn = ((0.85 * fc * (Ac + As - 2 * tf * bf) - 2 * Fy * (As - 2 * tf * bf))
              / (2 * (4 * Fy * tf + 0.85 * fc * (h1 - 2 * tf))))
        if hn <= tw / 2:
            return None
        Zsn = Zs - 2 * tf * (bf / 2 + hn) * (bf / 2 - hn)
    MB = MD - Fy * Zsn - 0.85 * fc * (h1 * hn**2 - Zsn) / 2
    return {"A": (Fy * As + Fyr * Asr + 0.85 * fc * Ac, 0.0), "E": (PE, ME), "C": (0.85 * fc * Ac, MB),
            "D": (0.85 * fc * Ac / 2, MD), "B": (0.0, MB)}


def table_6_3(*, Fy, fc, As, Ac, bi, hi, r, H, t, Zs) -> dict:
    """Filled rectangular HSS; H is the outside depth along the bending direction, hi and bi the clear dimensions."""
    Zc = bi * hi**2 / 4 - 0.429 * r**2 * hi + 0.192 * r**3
    MD = Fy * Zs + 0.85 * fc * Zc / 2
    hn = min(0.85 * fc * Ac / (2 * (0.85 * fc * bi + 4 * Fy * t)), hi / 2)
    MB = MD - Fy * 2 * t * hn**2 - 0.85 * fc * bi * hn**2 / 2
    hE = hn / 2 + H / 4
    PE = 0.85 * fc * Ac / 2 + 0.85 * fc * bi * hE + 4 * Fy * t * hE
    ME = MD - Fy * 2 * t * hE**2 - 0.85 * fc * bi * hE**2 / 2
    return {"A": (Fy * As + 0.85 * fc * Ac, 0.0), "E": (PE, ME), "C": (0.85 * fc * Ac, MB), "D": (0.85 * fc * Ac / 2, MD), "B": (0.0, MB)}


def table_6_4(*, Fy, fc, d, t) -> dict:
    """Filled round HSS, with the thin-wall closed form of the table for theta."""
    h = d - 2 * t
    As, Ac = math.pi * (d * t - t**2), math.pi * h**2 / 4
    Zc = h**3 / 6
    Zs = d**3 / 6 - Zc
    MD = Fy * Zs + 0.95 * fc * Zc / 2
    Kc, Ks = fc * h**2, Fy * (d - t) / 2 * t
    theta = ((0.0260 * Kc - 2 * Ks) / (0.0848 * Kc)
             + math.sqrt((0.0260 * Kc + 2 * Ks) ** 2 + 0.857 * Kc * Ks) / (0.0848 * Kc))
    half = math.sin(theta / 2)
    MB = Fy * (d**3 - h**3) / 6 * half + 0.95 * fc * h**3 / 6 * half**3 / 2
    hn = h / 2 * math.sin(math.pi / 2 - theta / 2)
    hE = hn / 2 + h / 4
    theta2 = math.pi - 2 * math.asin(2 * hE / h)
    half2 = math.sin(theta2 / 2)
    wedge = theta2 - math.sin(theta2)
    PA = Fy * As + 0.95 * fc * Ac
    PE = PA - Fy * (d**2 - h**2) * wedge / 4 - 0.95 * fc * h**2 * wedge / 8
    ME = Fy * (d**3 - h**3) / 6 * half2 + 0.95 * fc * h**3 / 6 * half2**3 / 2
    return {"A": (PA, 0.0), "E": (PE, ME), "C": (0.95 * fc * Ac, MB), "D": (0.95 * fc * Ac / 2, MD), "B": (0.0, MB)}
