"""ANSI/AISC 360-22 Chapter G formulations (shear). Pure functions; units N, mm, MPa. LRFD only.

Webs without transverse stiffeners (kv = 5.34 in G2.1); tension field action (G2.2, G2.3) and
stiffeners (G2.4) are not implemented. Selection lives in domain/shear.py.
"""
import math

E_STEEL = 200000.0     # MPa, as stated in G2.1(a)
PHI_V = 0.90          # G1(a)
PHI_V_ROLLED = 1.00   # G2.1(a): webs of rolled I-shapes with h/tw <= 2.24*sqrt(E/Fy)
KV_UNSTIFFENED = 5.34  # G2.1(b)(2)(i)
KV_HSS = 5.0           # G4
KV_LEG = 1.2           # G3, G6


def _positive(**values):
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive, got {value!r}")


def rolled_web_limit(*, E, Fy) -> float:
    """G2.1(a): 2.24*sqrt(E/Fy)."""
    _positive(E=E, Fy=Fy)
    return 2.24 * math.sqrt(E / Fy)


def cv1(*, h_tw, kv, E, Fy) -> dict:
    """G2.1(b)(1): web shear strength coefficient Cv1 (G2-3, G2-4)."""
    _positive(h_tw=h_tw, kv=kv, E=E, Fy=Fy)
    limit = 1.10 * math.sqrt(kv * E / Fy)
    if h_tw <= limit:
        return {"Cv": 1.0, "equation": "G2-3", "limit": limit}
    return {"Cv": limit / h_tw, "equation": "G2-4", "limit": limit}


def cv2(*, h_tw, kv, E, Fy) -> dict:
    """G2.2: web shear buckling strength coefficient Cv2 (G2-9, G2-10, G2-11)."""
    _positive(h_tw=h_tw, kv=kv, E=E, Fy=Fy)
    root = math.sqrt(kv * E / Fy)
    if h_tw <= 1.10 * root:
        return {"Cv": 1.0, "equation": "G2-9", "limit": 1.10 * root}
    if h_tw <= 1.37 * root:
        return {"Cv": 1.10 * root / h_tw, "equation": "G2-10", "limit": 1.37 * root}
    return {"Cv": 1.51 * kv * E / (h_tw**2 * Fy), "equation": "G2-11", "limit": 1.37 * root}


def web_strength(*, Fy, Aw, Cv, equation) -> dict:
    """0.6*Fy*Aw*Cv: G2-1 (I-shapes, channels) and G4-1 (HSS, box)."""
    _positive(Fy=Fy, Aw=Aw, Cv=Cv)
    return {"Vn": 0.6 * Fy * Aw * Cv, "equation": equation}


def leg_strength(*, Fy, b, t, Cv) -> dict:
    """G3-1: Vn = 0.6*Fy*b*t*Cv2 of one angle leg."""
    _positive(Fy=Fy, b=b, t=t, Cv=Cv)
    return {"Vn": 0.6 * Fy * b * t * Cv, "equation": "G3-1"}


def flange_strength(*, Fy, bf, tf, Cv) -> dict:
    """G6-1: Vn = 0.6*Fy*bf*tf*Cv2 of one flange."""
    _positive(Fy=Fy, bf=bf, tf=tf, Cv=Cv)
    return {"Vn": 0.6 * Fy * bf * tf * Cv, "equation": "G6-1"}


def round_hss_strength(*, E, Fy, Ag, D, t, Lv=None) -> dict:
    """G5: Vn = Fcr*Ag/2; Fcr = max(G5-2a, G5-2b) <= 0.6Fy. Without Lv only G5-2b (a lower bound)."""
    _positive(E=E, Fy=Fy, Ag=Ag, D=D, t=t)
    d_t = D / t
    fcr_b = 0.78 * E / d_t**1.5                                   # G5-2b
    fcr_a = None
    if Lv is not None:
        _positive(Lv=Lv)
        fcr_a = 1.60 * E / (math.sqrt(Lv / D) * d_t**1.25)         # G5-2a
    buckling = max(fcr_b, fcr_a) if fcr_a is not None else fcr_b
    fcr = min(buckling, 0.6 * Fy)
    equation = "0.6Fy" if fcr == 0.6 * Fy else ("G5-2a" if fcr_a is not None and fcr_a >= fcr_b else "G5-2b")
    return {"Vn": fcr * Ag / 2, "equation": "G5-1", "Fcr": fcr, "Fcr_equation": equation,
            "Fcr_G5_2a": fcr_a, "Fcr_G5_2b": fcr_b, "D_t": d_t}


def design_strength(Vn_N: float, phi: float) -> float:
    """phi_v*Vn (LRFD) in kN."""
    return phi * Vn_N / 1000.0
