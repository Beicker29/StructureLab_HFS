"""ANSI/AISC 360-22 Appendix 2: rectangular filled composite members with high-strength materials. Units N, mm, MPa. LRFD."""
import math

E_STEEL = 200000.0
FY_MAX = 690.0       # 2.1.1(c)
FC_MAX = 100.0       # 2.1.1(b)
FY_I13 = 525.0       # I1.3(b)
FC_I13 = 69.0        # I1.3(a), normal weight concrete


def slenderness(*, b_t, Fy) -> float:
    """lambda of Section 2.1.2: the largest width-to-thickness ratio multiplied by sqrt(Fy/E)."""
    return b_t * math.sqrt(Fy / E_STEEL)


def critical_stress(*, lam, Fy) -> float:
    """A-2-2."""
    return (1.0 - 0.075 * lam) * Fy


def pno(*, Fn, As, fc, Ac) -> float:
    """A-2-1."""
    return Fn * As + 0.85 * fc * Ac


def nominal_moment(*, Fy, Fn, fc, H, tw, tf, bi) -> dict:
    """Section 2.1.3: 90 % of the moment of the stress distribution (Design Guide 6, Eqs. 2-4 to 2-6)."""
    a = (2 * Fy * H * tw + (Fy - Fn) * bi * tf + 0.85 * fc * bi * tf) / (2 * tw * Fy + 2 * tw * Fn + 0.85 * fc * bi)
    msd = (Fn * tf * bi * (a - tf / 2) + 2 * Fn * tw * a * a / 2 + 0.85 * fc * bi * (a - tf) ** 2 / 2
           + 2 * Fy * tw * (H - a) ** 2 / 2 + Fy * tf * bi * (H - a - tf / 2))
    return {"Mn": 0.9 * msd, "Msd": msd, "a_mm": a}


def interaction_coefficients(*, B, H, lam, Pn, Pno, fc, Fy) -> dict:
    """A-2-3 and A-2-4."""
    cp = 0.175 - 0.075 / (B / H) + lam * (0.3 / (Pn / Pno)) * (fc / Fy)
    cm = 0.6 + 0.3 * (Pn / Pno) ** 2 + 0.6 * lam * (B / H) * (FY_MAX / Fy) * (fc / Fy)
    return {"cp": cp, "cm": cm}
