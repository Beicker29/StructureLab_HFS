"""ANSI/AISC 360-22 Chapter I formulations (composite members). Pure functions; units N, mm, MPa. LRFD only.

Stress blocks of filled rectangular sections: Commentary Fig. C-I3.8. Selection lives in domain/composite.py.
"""
import math

E_STEEL = 200000.0   # MPa, I2.1b
PHI_C = 0.75         # I2.1b
PHI_T = 0.90         # I2.1c, I2.2c
PHI_B = 0.90         # I3.2a, I3.3a, I3.4b
PHI_V_FILLED = 0.90  # I4.2
PHI_C_WALL = 0.90    # I2.3a
PHI_V_WALL = 0.90    # I4.4
PHI_STUD_V = 0.65    # I8.3a
PHI_STUD_T = 0.75    # I8.3b
PHI_CHANNEL = 0.75   # I8.3d
G_STEEL = 77200.0    # MPa, I1.5


def concrete_modulus(*, wc, fc) -> float:
    """Ec = 0.043*wc^1.5*sqrt(f'c), MPa (I2.1b)."""
    return 0.043 * wc**1.5 * math.sqrt(fc)


def c1_encased(*, As, Asr, Ag) -> float:
    """I2-6."""
    return min(0.25 + 3 * (As + Asr) / Ag, 0.7)


def c3_filled(*, As, Asr, Ag) -> float:
    """I2-13."""
    return min(0.45 + 3 * (As + Asr) / Ag, 0.9)


def effective_stiffness(*, Is, Isr, C, Ec, Ic) -> float:
    """(EI)eff: I2-5 with C1, I2-12 with C3."""
    return E_STEEL * Is + E_STEEL * Isr + C * Ec * Ic


def elastic_buckling_load(*, EI_eff, Lc) -> float:
    """I2-4."""
    return math.pi**2 * EI_eff / Lc**2


def nominal_compression(*, Pno, Pe) -> dict:
    """I2-2 and I2-3."""
    if Pno / Pe <= 2.25:
        return {"Pn": Pno * 0.658 ** (Pno / Pe), "equation": "I2-2", "Pno_over_Pe": Pno / Pe}
    return {"Pn": 0.877 * Pe, "equation": "I2-3", "Pno_over_Pe": Pno / Pe}


def pno_encased(*, Fy, As, Fysr, Asr, fc, Ac) -> float:
    """I2-7."""
    return Fy * As + Fysr * Asr + 0.85 * fc * Ac


def tension_yielding(*, Fy, As, Fysr=0.0, Asr=0.0) -> float:
    """I2-8 and I2-14."""
    return Fy * As + Fysr * Asr


def filled_limits(*, shape, element, Fy) -> dict:
    """Table I1.1a ("axial") and Table I1.1b ("flange", "web", "flexure_round"): lambda_p, lambda_r, maximum."""
    root = math.sqrt(E_STEEL / Fy)
    if shape == "round":
        ratio = E_STEEL / Fy
        return {"axial": {"p": 0.15 * ratio, "r": 0.19 * ratio, "max": 0.31 * ratio},
                "flexure_round": {"p": 0.09 * ratio, "r": 0.31 * ratio, "max": 0.31 * ratio}}[element]
    return {"axial": {"p": 2.26 * root, "r": 3.00 * root, "max": 5.00 * root},
            "flange": {"p": 2.26 * root, "r": 3.00 * root, "max": 5.00 * root},
            "web": {"p": 3.00 * root, "r": 5.70 * root, "max": 5.70 * root}}[element]


def classify_filled(*, ratio, limits) -> str:
    """I1.4: compact, noncompact or slender; beyond the maximum permitted the section is not allowed."""
    if ratio > limits["max"]:
        return "exceeds_maximum"
    if ratio <= limits["p"]:
        return "compact"
    return "noncompact" if ratio <= limits["r"] else "slender"


def critical_stress_rectangular(*, lam) -> float:
    """I2-10."""
    return 9 * E_STEEL / lam**2


def critical_stress_round(*, D_t, Fy) -> float:
    """I2-11."""
    return 0.72 * Fy / (D_t * Fy / E_STEEL) ** 0.2


def pno_filled(*, cls, shape, Fy, As, fc, Ac, lam, limits, Fn=None) -> dict:
    """I2-9a to I2-9e, without longitudinal reinforcement (Asr = 0)."""
    c2 = 0.95 if shape == "round" else 0.85
    pp = Fy * As + c2 * fc * Ac                                      # I2-9b
    if cls == "compact":
        return {"Pno": pp, "equation": "I2-9a", "Pp": pp}
    if cls == "noncompact":
        py = Fy * As + 0.7 * fc * Ac                                 # I2-9d
        pno = pp - (pp - py) / (limits["r"] - limits["p"]) ** 2 * (lam - limits["p"]) ** 2
        return {"Pno": pno, "equation": "I2-9c", "Pp": pp, "Py": py}
    return {"Pno": Fn * As + 0.7 * fc * Ac, "equation": "I2-9e", "Fn": Fn}


def rect_plastic_moment(*, Fy, fc, Zs, t, bi, hi, r) -> dict:
    """Mp of a filled rectangular section: Fig. C-I3.8(a) with the catalog Zs and rounded inside corners (Example I.6)."""
    Ac = bi * hi - (4 - math.pi) * r**2
    Zc = bi * hi**2 / 4 - 0.429 * r**2 * hi + 0.192 * r**3
    hn = min(0.85 * fc * Ac / (2 * (0.85 * fc * bi + 4 * Fy * t)), hi / 2)
    Zsn, Zcn = 2 * t * hn**2, bi * hn**2
    return {"Mp": Fy * (Zs - Zsn) + 0.85 * fc * (Zc - Zcn) / 2, "hn_mm": hn, "Zc_mm3": Zc,
            "Md": Fy * Zs + 0.85 * fc * Zc / 2}                      # neutral axis at the centroid (point D)


def rect_yield_moment(*, Fy, fc, H, tw, tf, bi) -> dict:
    """My of a noncompact filled rectangular section: Fig. C-I3.8(b) and Example I.7, Table I.7-2."""
    a = (2 * Fy * H * tw + 0.35 * fc * bi * tf) / (4 * tw * Fy + 0.35 * fc * bi)
    forces = [(bi * tf * Fy, a - tf / 2), (0.35 * fc * (a - tf) * bi, 2 * (a - tf) / 3), (a * 2 * tw * 0.5 * Fy, 2 * a / 3),
              (a * 2 * tw * 0.5 * Fy, 2 * a / 3), ((H - 2 * a) * 2 * tw * Fy, H / 2), (bi * tf * Fy, H - a - tf / 2)]
    return {"My": sum(f * y for f, y in forces), "a_mm": a}


def rect_first_yield_moment(*, Fy, Fn, fc, H, tw, tf, bi) -> dict:
    """Mcr of a slender filled rectangular section: Fig. C-I3.8(c) and Example I.7, Table I.7-3."""
    a = (Fy * H * tw + (0.35 * fc + Fy - Fn) * bi * tf) / (tw * (Fn + Fy) + 0.35 * fc * bi)
    forces = [(bi * tf * Fn, a - tf / 2), (0.35 * fc * (a - tf) * bi, 2 * (a - tf) / 3), (a * 2 * tw * 0.5 * Fn, 2 * a / 3),
              ((H - a) * 2 * tw * 0.5 * Fy, 2 * (H - a) / 3), (bi * tf * Fy, H - a - tf / 2)]
    return {"Mcr": sum(f * y for f, y in forces), "a_mm": a}


def noncompact_moment(*, Mp, My, lam, limits) -> float:
    """I3-5b."""
    return Mp - (Mp - My) * (lam - limits["p"]) / (limits["r"] - limits["p"])


def _balance(force, low, high) -> float:
    """Root of a function that decreases with the neutral axis position (bisection, to the float resolution)."""
    for _ in range(200):
        middle = (low + high) / 2
        if force(middle) > 0:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def round_plastic_moment(*, Fy, fc, D, t) -> dict:
    """Mp of a filled round section: plastic distribution of I1.2a with 0.95f'c; annulus and circle from D and t."""
    ro, ri = D / 2, D / 2 - t

    def segment(r, y):
        """Area above y of a circle of radius r, and its first moment about the center."""
        if y >= r:
            return 0.0, 0.0
        alpha = math.acos(y / r)
        return r**2 * (alpha - math.sin(alpha) * math.cos(alpha)), 2 / 3 * r**3 * math.sin(alpha) ** 3

    def forces(y):
        outer, inner = segment(ro, y), segment(ri, y)
        steel_above = outer[0] - inner[0]
        steel_total = math.pi * (ro**2 - ri**2)
        axial = 0.95 * fc * inner[0] + Fy * steel_above - Fy * (steel_total - steel_above)
        moment = 0.95 * fc * inner[1] + 2 * Fy * (outer[1] - inner[1])
        return axial, moment

    hn = _balance(lambda y: forces(y)[0], 0.0, ro)
    return {"Mp": forces(hn)[1], "hn_mm": hn, "Md": forces(0.0)[1]}


def _w_band(*, axis, d, bf, tf, tw, As, Zs, hn) -> tuple[float, float]:
    """Steel area and plastic modulus of a W-shape within |v| <= hn of the bending axis (Manual Part 6 forms)."""
    if axis == "x":
        if hn <= d / 2 - tf:
            return 2 * hn * tw, tw * hn**2
        if hn < d / 2:
            return As - 2 * bf * (d / 2 - hn), Zs - bf * (d / 2 - hn) * (d / 2 + hn)
        return As, Zs
    if hn <= tw / 2:
        return 2 * hn * d, d * hn**2
    if hn < bf / 2:
        return As - 4 * tf * (bf / 2 - hn), Zs - 2 * tf * (bf / 2 - hn) * (bf / 2 + hn)
    return As, Zs


def encased_plastic_moment(*, axis, Fy, Fysr, fc, b, h, d, bf, tf, tw, As, Zs, bars) -> dict:
    """Mp of an encased W-shape (I1.2a): h is parallel to the bending direction; bars = [(area, v from the axis)].

    Plastic neutral axis at hn on the compressed side: steel and bars at Fy and Fysr, concrete at 0.85f'c above it.
    Bars at or beyond the axis on the tension side do not displace compressed concrete.
    """
    def forces(hn):
        band, zsn = _w_band(axis=axis, d=d, bf=bf, tf=tf, tw=tw, As=As, Zs=Zs, hn=hn)
        above = [(a, v) for a, v in bars if v > hn]
        below = [(a, v) for a, v in bars if v <= hn]
        steel_above = (As - band) / 2
        concrete = b * (h / 2 - hn) - steel_above - sum(a for a, _ in above)
        axial = (0.85 * fc * concrete + Fy * steel_above + Fysr * sum(a for a, _ in above)
                 - Fy * (As - steel_above) - Fysr * sum(a for a, _ in below))
        first_moment = b * (h**2 / 4 - hn**2) / 2 - (Zs - zsn) / 2 - sum(a * v for a, v in above)
        moment = (0.85 * fc * first_moment + Fy * (Zs - zsn) + Fysr * sum(a * v for a, v in above)
                  - Fysr * sum(a * v for a, v in below))
        return axial, moment

    hn = _balance(lambda y: forces(y)[0], 0.0, h / 2)
    return {"Mp": forces(hn)[1], "hn_mm": hn, "Md": forces(0.0)[1]}


def shear_filled(*, Av, Fy, Kc, Ac, fc) -> float:
    """I4-1. The constant 0.06 applies with f'c in ksi, as printed; it is converted here to f'c in MPa."""
    ksi = 6.894757293168361
    return 0.6 * Av * Fy + 0.06 * Kc * Ac * math.sqrt(fc * ksi)


def i5_coefficients(*, shape, csr) -> dict:
    """Table I5.1."""
    if shape == "round":
        cp, high, low = 0.27 / csr**0.4, 1.10 / csr**0.08, 0.95 / csr**0.32
    else:
        cp, high, low = 0.17 / csr**0.4, 1.06 / csr**0.11, 0.90 / csr**0.36
    cm = max(high, 1.0) if csr >= 0.5 else min(low, 1.67)
    return {"cp": cp, "cm": cm}


def strength_ratio(*, As, Fy, Asr, Fysr, Ac, fc) -> float:
    """I5-2, with Fysr as corrected by the September 2026 errata."""
    return (As * Fy + Asr * Fysr) / (Ac * fc)


def i5_interaction(*, Pr_Pc, Mr_Mc, cp, cm) -> dict:
    """I5-1a and I5-1b."""
    if Pr_Pc >= cp:
        return {"ratio": Pr_Pc + (1 - cp) / cm * Mr_Mc, "equation": "I5-1a"}
    return {"ratio": (1 - cm) / cp * Pr_Pc + Mr_Mc, "equation": "I5-1b"}


def method2_simplified(*, Pr, PA, PC, Mrx, Mcx, Mry, Mcy) -> dict:
    """Commentary I5, Method 2 simplified: C-I5-1a and C-I5-1b. Zero moments need no capacity."""
    moments = (Mrx / Mcx if Mrx else 0.0) + (Mry / Mcy if Mry else 0.0)
    if Pr <= PC:                                                     # both equations coincide at Pr = PC
        return {"ratio": moments, "equation": "C-I5-1a"}
    return {"ratio": (Pr - PC) / (PA - PC) + moments, "equation": "C-I5-1b"}


def method2_ratio(*, Pr, Mr, points) -> float:
    """Commentary I5, Method 2: demand over the curve (P, M) along the ray from the origin, between anchor points."""
    for (p1, m1), (p2, m2) in zip(points, points[1:]):
        dp, dm = p2 - p1, m2 - m1
        cross = Pr * dm - Mr * dp
        if cross == 0:
            continue
        factor = (p1 * dm - m1 * dp) / cross
        position = -(Pr * m1 - Mr * p1) / cross
        if factor > 0 and -1e-12 <= position <= 1 + 1e-12:
            return 1 / factor
    raise ValueError("The demand does not cross the interaction curve.")


def wall_stiffness(*, Is, Ec, Ic) -> float:
    """I1-1."""
    return E_STEEL * Is + 0.35 * Ec * Ic


def pno_wall(*, Fy, As, fc, Ac) -> float:
    """I2-15."""
    return Fy * As + 0.85 * fc * Ac


def wall_shear(*, Asw, Fy, Ec, Ac) -> dict:
    """I4-2 to I4-4."""
    Ks = G_STEEL * Asw
    Ksc = 0.7 * (Ec * Ac) * (E_STEEL * Asw) / (4 * E_STEEL * Asw + Ec * Ac)
    return {"Vn": (Ks + Ksc) / math.sqrt(3 * Ks**2 + Ksc**2) * Asw * Fy, "Ks_N": Ks, "Ksc_N": Ksc}


def wall_tie_limit(*, t, tsc, dtie) -> dict:
    """I1-6 and I1-5M."""
    alpha = 1.7 * (tsc / t - 2) * (t / dtie) ** 4
    return {"alpha": alpha, "limit": 0.38 * math.sqrt(E_STEEL / (2 * alpha + 1))}


def wall_plastic_moment(*, Fy, fc, H, t, tf, bi, P=0.0) -> dict:
    """Plastic distribution of Fig. C-I3.8(a) (I1.2a, I3.5) at the axial force P (N, compression positive).

    H is the wall length, bi the concrete thickness, t each long plate and tf each flange plate.
    """
    def forces(a):
        """Axial force and moment about mid-length with the compression block a deep (mm)."""
        rows = []                                                    # (force, distance from the top)
        rows += [(2 * t * a * Fy, a / 2), (-2 * t * (H - a) * Fy, (H + a) / 2)]
        for top, bottom in ((0.0, tf), (H - tf, H)):
            above = min(max(a, top), bottom)                         # the part of the flange plate above a compresses
            rows += [(bi * (above - top) * Fy, (top + above) / 2), (-bi * (bottom - above) * Fy, (above + bottom) / 2)]
        depth = min(max(a - tf, 0.0), H - 2 * tf)
        rows.append((0.85 * fc * bi * depth, tf + depth / 2))
        return sum(f for f, _ in rows), sum(f * (H / 2 - y) for f, y in rows)

    if not forces(0.0)[0] <= P <= forces(H)[0]:
        return {"within_section": False, "Mp": 0.0, "a_mm": None, "P_max_N": forces(H)[0], "P_min_N": forces(0.0)[0]}
    a = _balance(lambda y: P - forces(y)[0], 0.0, H)
    return {"within_section": True, "Mp": forces(a)[1], "a_mm": a}


def stud_shear_strength(*, Fu, Asa) -> float:
    """I8-3."""
    return Fu * Asa


def stud_tension_strength(*, Fu, Asa) -> float:
    """I8-4."""
    return Fu * Asa


def stud_interaction(*, Qrv, Qcv, Qrt, Qct) -> float:
    """I8-5."""
    return (Qrt / Qct) ** (5 / 3) + (Qrv / Qcv) ** (5 / 3)


def effective_slab_width(*, span, left, right) -> dict:
    """I3.1a: each side is the least of L/8 and its limit (half the beam spacing, or the edge distance)."""
    sides = [min(span / 8, limit) for limit in (left, right)]
    return {"b_mm": sum(sides), "left_mm": sides[0], "right_mm": sides[1]}


def stud_strength(*, Asa, fc, Ec, Rg, Rp, Fu) -> dict:
    """I8-1."""
    concrete, limit = 0.5 * Asa * math.sqrt(fc * Ec), Rg * Rp * Asa * Fu
    return {"Qn": min(concrete, limit), "equation": "I8-1", "concrete_N": concrete, "limit_N": limit}


def channel_strength(*, tf, tw, la, fc, Ec) -> float:
    """I8-2."""
    return 0.3 * (tf + 0.5 * tw) * la * math.sqrt(fc * Ec)


def beam_plastic_moment(*, C, a, Ycon, Fy, As, d, bf, tf, tw) -> dict:
    """Plastic Mn of a composite beam (I3.2a(a)): concrete block C of depth a; PNA in the slab, flange or web."""
    arm = Ycon - a / 2                                               # concrete force to the top of the steel
    if C >= Fy * As:
        return {"Mn": Fy * As * (d / 2 + arm), "pna": "losa", "x_mm": 0.0}
    steel_compression = (Fy * As - C) / 2
    if steel_compression <= Fy * bf * tf:
        x = steel_compression / (Fy * bf)
        moment_top = steel_compression * x / 2                       # compressed steel about the top of the steel
        pna = "ala"
    else:
        web = steel_compression - Fy * bf * tf
        x = tf + web / (Fy * tw)
        moment_top = Fy * bf * tf * tf / 2 + web * (tf + (x - tf) / 2)
        pna = "alma"
    tension = Fy * As - steel_compression
    # Tension acts at the centroid of the steel that remains below the PNA.
    tension_arm = (Fy * As * d / 2 - moment_top) / tension
    return {"Mn": C * arm + tension * tension_arm - moment_top, "pna": pna, "x_mm": x}
