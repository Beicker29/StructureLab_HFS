"""ANSI/AISC 360-22 Chapter F formulations (flexure) and Table B4.1b limits. LRFD only.

Pure functions, units N, mm, MPa; moments in N*mm. Each function returns the
equation identifier actually applied. F7 numbering follows errata E25-02
(January 2025): the LTB equations are F7-8 to F7-11. Selection lives in domain/flexure.py.
"""
import math

E_STEEL = 200000.0  # MPa
PHI_B = 0.90        # F1(a), LRFD

# Table B4.1b (flexure): case -> (lambda_p coefficient, lambda_r coefficient, form)
_B41B = {
    10: (0.38, 1.0, "sqrt"),   # flanges of rolled I-shapes, channels (major axis)
    12: (0.54, 0.91, "sqrt"),  # legs of single angles (also double-angle legs through F9 -> F10.3)
    13: (0.38, 1.0, "sqrt"),   # flanges of I-shapes and channels, minor-axis flexure
    15: (3.76, 5.70, "sqrt"),  # webs of doubly symmetric I-shapes and channels
    17: (1.12, 1.40, "sqrt"),  # flanges of rectangular HSS
    19: (2.42, 5.70, "sqrt"),  # webs of rectangular HSS
    20: (0.07, 0.31, "linear"),  # round HSS, D/t
}


def _positive(**values):
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive, got {value!r}")


def limits(case: int, E: float, Fy: float) -> dict:
    """Table B4.1b lambda_p (compact/noncompact) and lambda_r (noncompact/slender)."""
    _positive(E=E, Fy=Fy)
    p, r, form = _B41B[case]
    base = E / Fy if form == "linear" else math.sqrt(E / Fy)
    return {"lambda_p": p * base, "lambda_r": r * base, "b4_case": case}


def classify(ratio: float, lim: dict) -> str:
    if ratio <= lim["lambda_p"]:
        return "compacto"
    return "no compacto" if ratio <= lim["lambda_r"] else "esbelto"


def design_strength(Mn_Nmm: float) -> float:
    """F1(a): phi_b*Mn in kN*m."""
    return PHI_B * Mn_Nmm / 1e6


def _between(mp, m_low, x, x_p, x_r):
    """Linear transition used by F2-2, F3-1, F6-2, F7-2, F7-6, F7-8 (without Cb)."""
    return mp - (mp - m_low) * (x - x_p) / (x_r - x_p)


# --- F2 doubly symmetric compact I-shapes and channels, major axis -----------------------------------

def f2_plastic(*, Fy, Zx) -> dict:
    _positive(Fy=Fy, Zx=Zx)
    return {"Mn": Fy * Zx, "equation": "F2-1"}


def f2_ltb(*, E, Fy, Sx, Zx, ry, Iy, Cw, J, ho, Lb, Cb, channel: bool) -> dict:
    """F2-2 to F2-8: lateral-torsional buckling. c = 1 (I) or (ho/2)*sqrt(Iy/Cw) (channels)."""
    _positive(E=E, Fy=Fy, Sx=Sx, Zx=Zx, ry=ry, Iy=Iy, Cw=Cw, J=J, ho=ho, Lb=Lb, Cb=Cb)
    mp = Fy * Zx
    rts = math.sqrt(math.sqrt(Iy * Cw) / Sx)                                   # F2-7
    c = ho / 2 * math.sqrt(Iy / Cw) if channel else 1.0                         # F2-8b / F2-8a
    jc = J * c / (Sx * ho)
    lp = 1.76 * ry * math.sqrt(E / Fy)                                          # F2-5
    lr = 1.95 * rts * E / (0.7 * Fy) * math.sqrt(jc + math.sqrt(jc**2 + 6.76 * (0.7 * Fy / E) ** 2))  # F2-6
    out = {"Lp_mm": lp, "Lr_mm": lr, "rts_mm": rts, "c": c, "Lb_mm": Lb, "Cb": Cb}
    if Lb <= lp:
        return {**out, "applies": False, "reason": "Lb ≤ Lp: el pandeo lateral-torsional no aplica (F2.2(a))."}
    if Lb <= lr:
        mn = min(Cb * _between(mp, 0.7 * Fy * Sx, Lb, lp, lr), mp)
        return {**out, "applies": True, "Mn": mn, "equation": "F2-2"}
    fcr = Cb * math.pi**2 * E / (Lb / rts) ** 2 * math.sqrt(1 + 0.078 * jc * (Lb / rts) ** 2)  # F2-4
    return {**out, "applies": True, "Fcr_mpa": fcr, "Mn": min(fcr * Sx, mp), "equation": "F2-3"}


# --- F3 doubly symmetric I-shapes, compact web, noncompact or slender flanges ---------------------------

def f3_flb(*, E, Fy, Sx, Zx, bf_2tf, h_tw, lim: dict) -> dict:
    _positive(E=E, Fy=Fy, Sx=Sx, Zx=Zx, bf_2tf=bf_2tf, h_tw=h_tw)
    mp = Fy * Zx
    if bf_2tf <= lim["lambda_r"]:
        return {"Mn": _between(mp, 0.7 * Fy * Sx, bf_2tf, lim["lambda_p"], lim["lambda_r"]), "equation": "F3-1"}
    kc = min(max(4 / math.sqrt(h_tw), 0.35), 0.76)
    return {"Mn": 0.9 * E * kc * Sx / bf_2tf**2, "kc": kc, "equation": "F3-2"}


# --- F6 I-shapes and channels, minor axis --------------------------------------------------------------

def f6_plastic(*, Fy, Zy, Sy) -> dict:
    _positive(Fy=Fy, Zy=Zy, Sy=Sy)
    return {"Mn": min(Fy * Zy, 1.6 * Fy * Sy), "equation": "F6-1"}


def f6_flb(*, E, Fy, Zy, Sy, b_t, lim: dict) -> dict:
    _positive(E=E, Fy=Fy, Zy=Zy, Sy=Sy, b_t=b_t)
    mp = min(Fy * Zy, 1.6 * Fy * Sy)
    if b_t <= lim["lambda_r"]:
        return {"Mn": _between(mp, 0.7 * Fy * Sy, b_t, lim["lambda_p"], lim["lambda_r"]), "equation": "F6-2"}
    fcr = 0.70 * E / b_t**2                                                     # F6-4
    return {"Mn": fcr * Sy, "Fcr_mpa": fcr, "equation": "F6-3"}


# --- F7 rectangular HSS (axis of bending given by the caller's S, Z, b, h) --------------------------------

def f7_plastic(*, Fy, Z) -> dict:
    _positive(Fy=Fy, Z=Z)
    return {"Mn": Fy * Z, "equation": "F7-1"}


def f7_effective_width(*, E, Fy, b, t) -> dict:
    """F7-4 (HSS): be = 1.92 t sqrt(E/Fy) (1 - 0.38/(b/t) sqrt(E/Fy)) <= b."""
    _positive(E=E, Fy=Fy, b=b, t=t)
    be = 1.92 * t * math.sqrt(E / Fy) * (1 - 0.38 / (b / t) * math.sqrt(E / Fy))
    return {"be_mm": min(be, b), "equation": "F7-4"}


def effective_section_modulus(*, inertia, A, depth, t, b, be) -> dict:
    """Se referred to the compression flange with the shifted neutral axis (Commentary F7).

    The ineffective width (b - be) is removed from the compression flange, whose
    mid-thickness is (depth - t)/2 from the centroid. Thin strip own inertia included.
    """
    _positive(inertia=inertia, A=A, depth=depth, t=t, b=b, be=be)
    lost = (b - be) * t
    a = (depth - t) / 2
    area = A - lost
    shift = lost * a / area                     # neutral axis moves toward the tension flange
    i_eff = inertia - lost * a**2 - (b - be) * t**3 / 12 - area * shift**2
    c = depth / 2 + shift                       # neutral axis to the extreme compression fiber
    return {"Se": i_eff / c, "I_eff": i_eff, "neutral_axis_shift_mm": shift, "c_compression_mm": c,
            "area_removed_mm2": lost}


def f7_flb(*, Fy, S, Z, b_t, lim: dict, Se: float | None = None) -> dict:
    mp = Fy * Z
    if b_t <= lim["lambda_r"]:
        return {"Mn": min(_between(mp, Fy * S, b_t, lim["lambda_p"], lim["lambda_r"]), mp), "equation": "F7-2"}
    _positive(Se=Se)
    return {"Mn": Fy * Se, "equation": "F7-3"}


def f7_wlb(*, Fy, S, Z, h_t, lim: dict) -> dict:
    mp = Fy * Z
    if h_t > lim["lambda_r"]:
        raise ValueError("Slender HSS web: F7-7 is not implemented (no HSS have slender webs, F7 User Note)")
    return {"Mn": min(_between(mp, Fy * S, h_t, lim["lambda_p"], lim["lambda_r"]), mp), "equation": "F7-6"}


def f7_ltb(*, E, Fy, Sx, Zx, ry, J, Ag, Lb, Cb) -> dict:
    """F7-8 to F7-11 (errata E25-02 numbering)."""
    _positive(E=E, Fy=Fy, Sx=Sx, Zx=Zx, ry=ry, J=J, Ag=Ag, Lb=Lb, Cb=Cb)
    mp = Fy * Zx
    root = math.sqrt(J * Ag)
    lp = 0.13 * E * ry * root / mp                                              # F7-10
    lr = 2 * E * ry * root / (0.7 * Fy * Sx)                                   # F7-11
    out = {"Lp_mm": lp, "Lr_mm": lr, "Lb_mm": Lb, "Cb": Cb}
    if Lb <= lp:
        return {**out, "applies": False, "reason": "Lb ≤ Lp: el pandeo lateral-torsional no aplica (F7.4(a))."}
    if Lb <= lr:
        return {**out, "applies": True, "Mn": min(Cb * _between(mp, 0.7 * Fy * Sx, Lb, lp, lr), mp), "equation": "F7-8"}
    return {**out, "applies": True, "Mn": min(2 * E * Cb * root / (Lb / ry), mp), "equation": "F7-9"}


# --- F8 round HSS ------------------------------------------------------------------------------------

def f8_plastic(*, Fy, Z) -> dict:
    _positive(Fy=Fy, Z=Z)
    return {"Mn": Fy * Z, "equation": "F8-1"}


def f8_local_buckling(*, E, Fy, S, D_t, lim: dict) -> dict:
    _positive(E=E, Fy=Fy, S=S, D_t=D_t)
    if D_t >= 0.45 * E / Fy:
        raise ValueError("F8 applies only to D/t < 0.45E/Fy")
    if D_t <= lim["lambda_r"]:
        return {"Mn": (0.021 * E / D_t + Fy) * S, "equation": "F8-2"}
    fcr = 0.33 * E / D_t                                                        # F8-4
    return {"Mn": fcr * S, "Fcr_mpa": fcr, "equation": "F8-3"}


# --- F11 rectangular bars and rounds ----------------------------------------------------------------------

def f11_plastic(*, Fy, Z, S, round_bar: bool) -> dict:
    _positive(Fy=Fy, Z=Z, S=S)
    k, eqn = (1.6, "F11-2") if round_bar else (1.5, "F11-1")
    return {"Mn": min(Fy * Z, k * Fy * S), "equation": eqn}


def f11_ltb(*, E, Fy, S, Z, d, t, Lb, Cb) -> dict:
    """Rectangular bar bent about its major axis: F11-3 to F11-5 (d depth, t width)."""
    _positive(E=E, Fy=Fy, S=S, Z=Z, d=d, t=t, Lb=Lb, Cb=Cb)
    mp = min(Fy * Z, 1.5 * Fy * S)
    x = Lb * d / t**2
    out = {"Lb_d_over_t2": x, "Lb_mm": Lb, "Cb": Cb}
    if x <= 0.08 * E / Fy:
        return {**out, "applies": False, "reason": "Lb·d/t² ≤ 0.08E/Fy: el pandeo lateral-torsional no aplica (F11.2(a))."}
    if x <= 1.9 * E / Fy:
        return {**out, "applies": True, "Mn": min(Cb * (1.52 - 0.274 * x * Fy / E) * Fy * S, mp), "equation": "F11-3"}
    fcr = 1.9 * E * Cb / x                                                      # F11-5
    return {**out, "applies": True, "Fcr_mpa": fcr, "Mn": min(fcr * S, mp), "equation": "F11-4"}


# --- F9 double angles loaded in the plane of symmetry (bending about x) ------------------------------------

def f9_plastic(*, Fy, Zx, Sx, web_legs: str) -> dict:
    """F9-1 to F9-5: web legs in tension Mp = FyZx <= 1.6My; in compression Mp = 1.5My (My = FySx)."""
    _positive(Fy=Fy, Zx=Zx, Sx=Sx)
    my = Fy * Sx                                                                # F9-3
    if web_legs == "tension":
        return {"Mn": min(Fy * Zx, 1.6 * my), "My": my, "equation": "F9-2"}
    return {"Mn": 1.5 * my, "My": my, "equation": "F9-5"}


def f9_mcr(*, E, Iy, J, d, Lb, web_legs: str) -> dict:
    """F9-10 with B from F9-11 (web legs in tension) or F9-12 (in compression); d = web leg width."""
    _positive(E=E, Iy=Iy, J=J, d=d, Lb=Lb)
    b = 2.3 * d / Lb * math.sqrt(Iy / J) * (1 if web_legs == "tension" else -1)
    return {"Mcr": 1.95 * E / Lb * math.sqrt(Iy * J) * (b + math.sqrt(1 + b**2)), "B": b,
            "B_equation": "F9-11" if web_legs == "tension" else "F9-12"}


def f10_from_mcr(*, My, Mcr) -> dict:
    """F10-2 (My/Mcr <= 1) or F10-3: lateral-torsional buckling strength from the elastic moment."""
    _positive(My=My, Mcr=Mcr)
    if My / Mcr <= 1.0:
        return {"Mn": min((1.92 - 1.17 * math.sqrt(My / Mcr)) * My, 1.5 * My), "equation": "F10-2"}
    return {"Mn": (0.92 - 0.17 * Mcr / My) * Mcr, "equation": "F10-3"}


def f9_ltb(*, E, Fy, Zx, Sx, ry, Iy, J, d, Lb, web_legs: str) -> dict:
    """F9.2: web legs in tension (F9-6 to F9-9) or in compression (F9-10/F9-12 with F10-2/F10-3)."""
    _positive(E=E, Fy=Fy, Zx=Zx, Sx=Sx, ry=ry, Iy=Iy, J=J, d=d, Lb=Lb)
    my = Fy * Sx
    mcr = f9_mcr(E=E, Iy=Iy, J=J, d=d, Lb=Lb, web_legs=web_legs)
    out = {"Lb_mm": Lb, "My": my, "Mcr": mcr["Mcr"], "B": mcr["B"], "B_equation": mcr["B_equation"]}
    if web_legs == "compression":
        return {**out, "applies": True, **f10_from_mcr(My=my, Mcr=mcr["Mcr"])}
    mp = min(Fy * Zx, 1.6 * my)
    lp = 1.76 * ry * math.sqrt(E / Fy)                                          # F9-8
    lr = 1.95 * (E / Fy) * math.sqrt(Iy * J) / Sx * math.sqrt(2.36 * (Fy / E) * d * Sx / J + 1)  # F9-9
    out.update(Lp_mm=lp, Lr_mm=lr)
    if Lb <= lp:
        return {**out, "applies": False, "reason": "Lb ≤ Lp: el pandeo lateral-torsional no aplica (F9.2(a)(1))."}
    if Lb <= lr:
        return {**out, "applies": True, "Mn": _between(mp, my, Lb, lp, lr), "equation": "F9-6"}
    return {**out, "applies": True, "Mn": mcr["Mcr"], "equation": "F9-7"}


# --- F10 single angles --------------------------------------------------------------------------------

def f10_plastic(*, My) -> dict:
    _positive(My=My)
    return {"Mn": 1.5 * My, "My": My, "equation": "F10-1"}


def f10_mcr_principal(*, E, Ag, rz, t, Lb, Cb, beta_w) -> dict:
    """F10-4: major principal axis; Cb limited to 1.5; beta_w signed by the caller."""
    _positive(E=E, Ag=Ag, rz=rz, t=t, Lb=Lb, Cb=Cb)
    cb = min(Cb, 1.5)
    k = 4.4 * beta_w * rz / (Lb * t)
    return {"Mcr": 9 * E * Ag * rz * t * cb / (8 * Lb) * (math.sqrt(1 + k**2) + k), "Cb_used": cb,
            "beta_w_mm": beta_w, "Mcr_equation": "F10-4"}


def f10_mcr_geometric(*, E, b, t, Lb, Cb, toe: str) -> dict:
    """F10-5a (maximum compression at the toe) or F10-5b (maximum tension at the toe), equal-leg angles."""
    _positive(E=E, b=b, t=t, Lb=Lb, Cb=Cb)
    root = math.sqrt(1 + 0.88 * (Lb * t / b**2) ** 2)
    sign, eqn = (-1, "F10-5a") if toe == "compression" else (1, "F10-5b")
    return {"Mcr": 0.58 * E * b**4 * t * Cb / Lb**2 * (root + sign), "Mcr_equation": eqn}


def f10_leg_local(*, E, Fy, Sc, b_t, lim: dict) -> dict:
    """F10-6 (noncompact) or F10-7/F10-8 (slender); the caller handles compact legs."""
    _positive(E=E, Fy=Fy, Sc=Sc, b_t=b_t)
    if b_t <= lim["lambda_r"]:
        return {"Mn": Fy * Sc * (2.43 - 1.72 * b_t * math.sqrt(Fy / E)), "equation": "F10-6"}
    fcr = 0.71 * E / b_t**2                                                     # F10-8
    return {"Mn": fcr * Sc, "Fcr_mpa": fcr, "equation": "F10-7"}


# --- F13.1 bolt holes in the tension flange --------------------------------------------------------------

def f13_tension_flange(*, Fy, Fu, Afg, Afn, Sx) -> dict:
    _positive(Fy=Fy, Fu=Fu, Afg=Afg, Afn=Afn, Sx=Sx)
    yt = 1.0 if Fy / Fu <= 0.8 else 1.1
    out = {"Yt": yt, "Afg_mm2": Afg, "Afn_mm2": Afn, "FuAfn": Fu * Afn, "YtFyAfg": yt * Fy * Afg}
    if Fu * Afn >= yt * Fy * Afg:
        return {**out, "applies": False, "reason": "Fu·Afn ≥ Yt·Fy·Afg: la rotura del ala traccionada no aplica (F13.1(a))."}
    return {**out, "applies": True, "Mn": Fu * Afn / Afg * Sx, "equation": "F13-1"}
