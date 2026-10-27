import math
from typing import Dict, Optional


NORMATIVE_E_MPA = 200000.0
PHI_B_LRFD = 0.90
OMEGA_B_ASD = 1.67


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _positive(value: Optional[float]) -> float:
    if isinstance(value, (int, float)) and value > 0.0:
        return float(value)
    return 0.0


def _sqrt_ratio(E: float, Fy: float) -> float:
    return math.sqrt(E / Fy) if E > 0.0 and Fy > 0.0 else 0.0


def _interpolate(lb: float, lp: float, lr: float, top_at_lp: float, bot_at_lr: float) -> float:
    if lr <= lp:
        return bot_at_lr
    ratio = (lb - lp) / (lr - lp)
    return top_at_lp - (top_at_lp - bot_at_lr) * ratio


def _derive_rts(section) -> float:
    if _positive(section.rts) > 0.0:
        return _positive(section.rts)
    iy = _positive(section.iy)
    cw = _positive(section.cw)
    sx = _positive(section.sx)
    if iy <= 0.0 or cw <= 0.0 or sx <= 0.0:
        return 0.0
    return math.sqrt(math.sqrt(iy * cw) / sx)


def _f2_c_factor(section) -> float:
    profile = (section.type or "").upper()
    if profile == "CHANNEL":
        ho = _positive(section.ho)
        iy = _positive(section.iy)
        cw = _positive(section.cw)
        if ho > 0.0 and iy > 0.0 and cw > 0.0:
            return (ho / 2.0) * math.sqrt(iy / cw)
    return 1.0


def _f2_ltb_strength(
    *,
    Fy: float,
    E: float,
    Cb: float,
    Lb: float,
    Mp: float,
    Sx: float,
    ry: float,
    rts: float,
    J: float,
    ho: float,
    c_factor: float,
) -> Dict[str, float]:
    if min(Fy, E, Cb, Lb, Mp, Sx, ry, rts, J, ho, c_factor) <= 0.0:
        return {
            "Mn_ltb_Nmm": Mp,
            "Lp_mm": 0.0,
            "Lr_mm": 0.0,
            "Fcr_mpa": Fy,
        }

    lp = 1.76 * ry * math.sqrt(E / Fy)
    term = (J * c_factor) / (Sx * ho) if Sx * ho > 0.0 else 0.0
    lr = 1.95 * rts * (E / (0.7 * Fy)) * math.sqrt(term + math.sqrt((term**2) + 6.76 * ((0.7 * Fy / E) ** 2)))

    if Lb <= lp:
        return {"Mn_ltb_Nmm": Mp, "Lp_mm": lp, "Lr_mm": lr, "Fcr_mpa": Fy}

    if Lb <= lr:
        mn = Cb * _interpolate(Lb, lp, lr, Mp, 0.7 * Fy * Sx)
        return {"Mn_ltb_Nmm": min(Mp, mn), "Lp_mm": lp, "Lr_mm": lr, "Fcr_mpa": mn / Sx if Sx > 0.0 else 0.0}

    lb_over_rts = Lb / rts if rts > 0.0 else 0.0
    root_term = 1.0 + 0.078 * term * (lb_over_rts**2)
    root_term = max(root_term, 0.0)
    fcr = Cb * ((math.pi**2) * E / (lb_over_rts**2)) * math.sqrt(root_term) if lb_over_rts > 0.0 else Fy
    mn = min(Mp, fcr * Sx)
    return {"Mn_ltb_Nmm": mn, "Lp_mm": lp, "Lr_mm": lr, "Fcr_mpa": fcr}


def _kc_from_web_ratio(web_ratio: float) -> float:
    if web_ratio <= 0.0:
        return 0.76
    return _clamp(4.0 / math.sqrt(web_ratio), 0.35, 0.76)


def _classify_ratio(value: float, lp: float, lr: float) -> str:
    if value <= lp:
        return "compact"
    if value <= lr:
        return "noncompact"
    return "slender"


def available_flexural_strength(Mn_Nmm: float, design_method: str) -> float:
    """F1(a), ANSI/AISC 360-22: available moment in kN-m from nominal N-mm.

    This conversion does not establish applicability or enable an ASD route.
    Preserve the original LRFD operation order for exact regression stability.
    """
    if design_method == "LRFD":
        return PHI_B_LRFD * Mn_Nmm / 1_000_000.0
    if design_method == "ASD":
        return Mn_Nmm / OMEGA_B_ASD / 1_000_000.0
    raise ValueError(f"Unsupported flexural design method: {design_method!r}")


def available_flexural_strength_lrfd(Mn_Nmm: float) -> float:
    """Compatibility entrypoint for the existing LRFD-only Chapter F checks."""
    return available_flexural_strength(Mn_Nmm, "LRFD")


def evaluate_f2(case, section) -> Dict[str, object]:
    Fy = case.material.Fy
    E = case.material.E
    Cb = case.factors.Cb
    Lb = case.lengths.Lb
    Zx = _positive(section.zx)
    Sx = _positive(section.sx)
    ry = _positive(section.ry)
    J = _positive(section.j)
    ho = _positive(section.ho)
    rts = _derive_rts(section)
    c_factor = _f2_c_factor(section)
    mp = Fy * Zx
    ltb = _f2_ltb_strength(
        Fy=Fy,
        E=E,
        Cb=Cb,
        Lb=Lb,
        Mp=mp,
        Sx=Sx,
        ry=ry,
        rts=rts,
        J=J,
        ho=ho,
        c_factor=c_factor,
    )
    mn = min(mp, ltb["Mn_ltb_Nmm"])
    return {
        "Mn_Nmm": mn,
        "Mp_Nmm": mp,
        "limit_states": {
            "yielding_Mn_Nmm": mp,
            "ltb_Mn_Nmm": ltb["Mn_ltb_Nmm"],
        },
        "intermediate": {
            "Lp_mm": ltb["Lp_mm"],
            "Lr_mm": ltb["Lr_mm"],
            "Fcr_mpa": ltb["Fcr_mpa"],
            "rts_mm": rts,
            "c_factor": c_factor,
        },
    }


def evaluate_f3(case, section) -> Dict[str, object]:
    Fy = case.material.Fy
    E = case.material.E
    ratio = _positive(section.bf_2tf_ratio)
    web_ratio = _positive(section.h_tw_ratio)
    sqrt_ratio = _sqrt_ratio(E, Fy)
    lambda_pf = 0.38 * sqrt_ratio
    lambda_rf = 1.0 * sqrt_ratio
    class_f = _classify_ratio(ratio, lambda_pf, lambda_rf)

    f2 = evaluate_f2(case, section)
    mp = f2["Mp_Nmm"]
    sx = _positive(section.sx)
    if class_f == "compact":
        mn_flb = mp
    elif class_f == "noncompact":
        mn_flb = mp - (mp - 0.7 * Fy * sx) * ((ratio - lambda_pf) / (lambda_rf - lambda_pf))
    else:
        kc = _kc_from_web_ratio(web_ratio)
        mn_flb = 0.9 * E * kc * sx / (ratio**2) if ratio > 0.0 else 0.0
    mn = min(mp, f2["limit_states"]["ltb_Mn_Nmm"], mn_flb)
    return {
        "Mn_Nmm": mn,
        "Mp_Nmm": mp,
        "limit_states": {
            "yielding_Mn_Nmm": mp,
            "ltb_Mn_Nmm": f2["limit_states"]["ltb_Mn_Nmm"],
            "flange_local_buckling_Mn_Nmm": mn_flb,
        },
        "intermediate": {
            **f2["intermediate"],
            "lambda_f": ratio,
            "lambda_pf": lambda_pf,
            "lambda_rf": lambda_rf,
            "flange_class": class_f,
            "kc": _kc_from_web_ratio(web_ratio),
        },
    }


def _f5_rpg(Fy: float, E: float, aw: float, hc_over_tw: float) -> float:
    if min(Fy, E) <= 0.0:
        return 1.0
    reduction = (aw / (1200.0 + 300.0 * aw)) * (hc_over_tw - 5.7 * math.sqrt(E / Fy))
    return _clamp(1.0 - reduction, 0.0, 1.0)


def _f5_rt(bfc: float, aw: float) -> float:
    denom = 12.0 * (1.0 + (aw / 6.0))
    if min(bfc, denom) <= 0.0:
        return 0.0
    return bfc / math.sqrt(denom)


def evaluate_f5(case, section) -> Dict[str, object]:
    Fy = case.material.Fy
    E = case.material.E
    Cb = case.factors.Cb
    Lb = case.lengths.Lb
    sx = _positive(section.sx)
    bf = _positive(section.bf)
    tf = _positive(section.tf)
    tw = _positive(section.tw)
    hc = _positive(section.h)
    if hc <= 0.0 and _positive(section.d) > 0.0 and tf > 0.0:
        hc = max(_positive(section.d) - 2.0 * tf, 0.0)
    aw = (hc * tw) / (bf * tf) if min(hc, tw, bf, tf) > 0.0 else 0.0
    hc_over_tw = hc / tw if min(hc, tw) > 0.0 else 0.0
    rpg = _f5_rpg(Fy, E, aw, hc_over_tw)
    rt = _f5_rt(bf, aw)
    lp = 1.1 * rt * math.sqrt(E / Fy) if min(rt, E, Fy) > 0.0 else 0.0
    lr = math.pi * rt * math.sqrt(E / (0.7 * Fy)) if min(rt, E, Fy) > 0.0 else 0.0
    if Lb <= lp:
        fcr_ltb = Fy
    elif Lb <= lr and lr > lp:
        fcr_ltb = Cb * _interpolate(Lb, lp, lr, Fy, 0.7 * Fy)
        fcr_ltb = min(Fy, fcr_ltb)
    else:
        lb_over_rt = Lb / rt if rt > 0.0 else 0.0
        fcr_ltb = Cb * (math.pi**2) * E / (lb_over_rt**2) if lb_over_rt > 0.0 else Fy
        fcr_ltb = min(0.7 * Fy, fcr_ltb)

    ratio = _positive(section.bf_2tf_ratio)
    sqrt_ratio = _sqrt_ratio(E, Fy)
    lambda_pf = 0.38 * sqrt_ratio
    lambda_rf = 1.0 * sqrt_ratio
    flange_class = _classify_ratio(ratio, lambda_pf, lambda_rf)
    kc = _kc_from_web_ratio(_positive(section.h_tw_ratio))
    if flange_class == "compact":
        fcr_flb = Fy
    elif flange_class == "noncompact" and lambda_rf > lambda_pf:
        fcr_flb = Fy - 0.3 * Fy * ((ratio - lambda_pf) / (lambda_rf - lambda_pf))
    else:
        fcr_flb = 0.9 * E * kc / (ratio**2) if ratio > 0.0 else 0.0

    mn_cfy = rpg * Fy * sx
    mn_ltb = rpg * fcr_ltb * sx
    mn_flb = rpg * fcr_flb * sx
    mn = min(mn_cfy, mn_ltb, mn_flb)
    return {
        "Mn_Nmm": mn,
        "limit_states": {
            "compression_flange_yielding_Mn_Nmm": mn_cfy,
            "lateral_torsional_buckling_Mn_Nmm": mn_ltb,
            "compression_flange_local_buckling_Mn_Nmm": mn_flb,
        },
        "intermediate": {
            "aw": aw,
            "Rpg": rpg,
            "rt_mm": rt,
            "Lp_mm": lp,
            "Lr_mm": lr,
            "Fcr_ltb_mpa": fcr_ltb,
            "Fcr_flb_mpa": fcr_flb,
            "lambda_f": ratio,
            "lambda_pf": lambda_pf,
            "lambda_rf": lambda_rf,
            "flange_class": flange_class,
            "kc": kc,
            "implementation_note": "Doubly symmetric branch.",
        },
    }


def evaluate_f4_conservative(case, section) -> Dict[str, object]:
    base = evaluate_f5(case, section)
    base["intermediate"]["implementation_note"] = (
        "Conservative implementation using F5 per User Note in F4."
    )
    return base


def evaluate_f6(case, section) -> Dict[str, object]:
    Fy = case.material.Fy
    E = case.material.E
    sy = _positive(section.sy)
    zy = _positive(section.zy)
    ratio = _positive(section.bf_2tf_ratio)
    sqrt_ratio = _sqrt_ratio(E, Fy)
    lambda_pf = 0.38 * sqrt_ratio
    lambda_rf = 1.0 * sqrt_ratio
    mp = min(Fy * zy, 1.6 * Fy * sy)
    class_f = _classify_ratio(ratio, lambda_pf, lambda_rf)
    if class_f == "compact":
        mn_flb = mp
    elif class_f == "noncompact":
        mn_flb = mp - (mp - 0.7 * Fy * sy) * ((ratio - lambda_pf) / (lambda_rf - lambda_pf))
    else:
        fcr = 0.7 * E / (ratio**2) if ratio > 0.0 else 0.0
        mn_flb = fcr * sy
    mn = min(mp, mn_flb)
    return {
        "Mn_Nmm": mn,
        "limit_states": {
            "yielding_Mn_Nmm": mp,
            "flange_local_buckling_Mn_Nmm": mn_flb,
        },
        "intermediate": {
            "lambda_f": ratio,
            "lambda_pf": lambda_pf,
            "lambda_rf": lambda_rf,
            "flange_class": class_f,
        },
    }


def evaluate_f7(case, section, axis: str) -> Dict[str, object]:
    Fy = case.material.Fy
    E = case.material.E
    Cb = case.factors.Cb
    Lb = case.lengths.Lb
    t = _positive(section.tdes)
    h = _positive(section.h)
    b = _positive(section.b)
    if axis == "x":
        z = _positive(section.zx)
        s = _positive(section.sx)
        lambda_f = _positive(section.b_tdes_ratio)
        lambda_w = _positive(section.h_tdes_ratio)
        ry = _positive(section.ry)
    else:
        z = _positive(section.zy)
        s = _positive(section.sy)
        lambda_f = _positive(section.h_tdes_ratio)
        lambda_w = _positive(section.b_tdes_ratio)
        ry = _positive(section.rx)
    mp = Fy * z
    sqrt_ratio = _sqrt_ratio(E, Fy)
    lambda_pf = 1.12 * sqrt_ratio
    lambda_rf = 1.40 * sqrt_ratio
    lambda_pw = 2.42 * sqrt_ratio
    lambda_rw = 5.70 * sqrt_ratio
    flange_class = _classify_ratio(lambda_f, lambda_pf, lambda_rf)
    web_class = _classify_ratio(lambda_w, lambda_pw, lambda_rw)

    if flange_class == "compact":
        mn_flange = mp
    elif flange_class == "noncompact":
        mn_flange = mp - (mp - Fy * s) * ((lambda_f - lambda_pf) / (lambda_rf - lambda_pf))
    else:
        be_ref = b if axis == "x" else h
        be = 1.92 * t * math.sqrt(E / Fy) * (1.0 - (0.38 / lambda_f) * math.sqrt(E / Fy)) if lambda_f > 0.0 else 0.0
        be = _clamp(be, 0.0, be_ref) if be_ref > 0.0 else 0.0
        se = s * (be / be_ref) if be_ref > 0.0 else 0.0
        mn_flange = Fy * se

    if web_class == "compact":
        mn_web = mp
    elif web_class == "noncompact":
        mn_web = mp - (mp - Fy * s) * ((lambda_w - lambda_pw) / (lambda_rw - lambda_pw))
    else:
        aw = (2.0 * h / b) if b > 0.0 else 0.0
        hc_over_tw = h / t if t > 0.0 else 0.0
        rpg = _f5_rpg(Fy, E, aw, hc_over_tw)
        mn_web = rpg * Fy * s

    # Conservative LTB model for HSS (user note indicates LTB is often non-governing)
    if axis == "y" or abs(b - h) <= 1e-9:
        mn_ltb = mp
        ltb_note = "LTB not applicable for minor axis or square section."
    else:
        lp = 1.76 * ry * math.sqrt(E / Fy) if min(ry, E, Fy) > 0.0 else 0.0
        if Lb <= lp:
            mn_ltb = mp
        else:
            mn_ltb = min(mp, Cb * 0.7 * Fy * s)
        ltb_note = "Conservative LTB branch for rectangular HSS in current scope."

    mn = min(mp, mn_flange, mn_web, mn_ltb)
    return {
        "Mn_Nmm": mn,
        "limit_states": {
            "yielding_Mn_Nmm": mp,
            "flange_local_buckling_Mn_Nmm": mn_flange,
            "web_local_buckling_Mn_Nmm": mn_web,
            "lateral_torsional_buckling_Mn_Nmm": mn_ltb,
        },
        "intermediate": {
            "axis": axis,
            "lambda_f": lambda_f,
            "lambda_pf": lambda_pf,
            "lambda_rf": lambda_rf,
            "flange_class": flange_class,
            "lambda_w": lambda_w,
            "lambda_pw": lambda_pw,
            "lambda_rw": lambda_rw,
            "web_class": web_class,
            "ltb_note": ltb_note,
        },
    }


def evaluate_f8(case, section, axis: str) -> Dict[str, object]:
    Fy = case.material.Fy
    E = case.material.E
    z = _positive(section.zx if axis == "x" else section.zy)
    s = _positive(section.sx if axis == "x" else section.sy)
    ratio = _positive(section.d_t_ratio)
    mp = Fy * z
    lambda_p = 0.07 * E / Fy if Fy > 0.0 else 0.0
    lambda_r = 0.31 * E / Fy if Fy > 0.0 else 0.0
    if ratio <= lambda_p:
        mn_lb = mp
        wall_class = "compact"
        fcr = Fy
    elif ratio <= lambda_r:
        wall_class = "noncompact"
        fcr = (0.021 * E / ratio) + Fy if ratio > 0.0 else Fy
        mn_lb = min(mp, fcr * s)
    else:
        wall_class = "slender"
        fcr = 0.33 * E / ratio if ratio > 0.0 else 0.0
        mn_lb = min(mp, fcr * s)
    mn = min(mp, mn_lb)
    return {
        "Mn_Nmm": mn,
        "limit_states": {
            "yielding_Mn_Nmm": mp,
            "local_buckling_Mn_Nmm": mn_lb,
        },
        "intermediate": {
            "axis": axis,
            "D_over_t": ratio,
            "lambda_p": lambda_p,
            "lambda_r": lambda_r,
            "wall_class": wall_class,
            "Fcr_mpa": fcr,
        },
    }


def evaluate_f10(case, section, axis: str) -> Dict[str, object]:
    Fy = case.material.Fy
    E = case.material.E
    ratio = _positive(section.b_t_ratio)
    leg_b = _positive(section.b)
    t = _positive(section.t)

    if axis == "major_principal":
        s_ref = _positive(section.sz) or _positive(section.sx)
    else:
        s_ref = _positive(section.sx) if abs(case.loads.Mux) > 0.0 else _positive(section.sy)
    my = Fy * s_ref
    mn_y = 1.5 * my

    restraint = case.connection.angle_ltb_restraint.value if case.connection.angle_ltb_restraint else "discrete_unbraced"
    if restraint == "continuous":
        mn_ltb = mn_y
        mcr = None
    else:
        # Conservative branch while keeping F10-2/F10-3 structure.
        mcr = 1.0 * my if axis == "major_principal" else 0.8 * my
        if restraint == "max_moment_only":
            mcr *= 1.25
        my_over_mcr = my / mcr if mcr and mcr > 0.0 else 10.0
        if my_over_mcr <= 1.0:
            mn_ltb = my * (1.92 - 1.17 * my_over_mcr)
        else:
            mn_ltb = mcr * (0.92 - 0.17 * my_over_mcr)
        mn_ltb = _clamp(mn_ltb, 0.0, mn_y)

    sqrt_ratio = _sqrt_ratio(E, Fy)
    lambda_p = 0.54 * sqrt_ratio
    lambda_r = 0.91 * sqrt_ratio
    if ratio <= lambda_p:
        mn_lb = mn_y
        leg_class = "compact"
        fcr = Fy
    elif ratio <= lambda_r:
        leg_class = "noncompact"
        # F10-6
        mn_lb = my * (1.92 - 1.17 * ratio * math.sqrt(Fy / E))
        mn_lb = min(mn_lb, mn_y)
        fcr = mn_lb / s_ref if s_ref > 0.0 else 0.0
    else:
        leg_class = "slender"
        fcr = 0.71 * E / (ratio**2) if ratio > 0.0 else 0.0
        sc = 0.8 * s_ref if axis == "geometric_axis" and restraint != "continuous" else s_ref
        mn_lb = fcr * sc

    mn = min(mn_y, mn_ltb, mn_lb)
    return {
        "Mn_Nmm": mn,
        "limit_states": {
            "yielding_Mn_Nmm": mn_y,
            "lateral_torsional_buckling_Mn_Nmm": mn_ltb,
            "leg_local_buckling_Mn_Nmm": mn_lb,
        },
        "intermediate": {
            "axis": axis,
            "My_Nmm": my,
            "Mcr_Nmm": mcr,
            "restraint": restraint,
            "leg_width_b_mm": leg_b,
            "leg_thickness_t_mm": t,
            "lambda_leg": ratio,
            "lambda_p": lambda_p,
            "lambda_r": lambda_r,
            "leg_class": leg_class,
            "Fcr_mpa": fcr,
        },
    }


def evaluate_f11(case, section, axis: str) -> Dict[str, object]:
    Fy = case.material.Fy
    E = case.material.E
    Cb = case.factors.Cb
    Lb = case.lengths.Lb
    profile = (section.type or "").upper()

    if axis == "x":
        s = _positive(section.sx)
        z = _positive(section.zx)
    else:
        s = _positive(section.sy)
        z = _positive(section.zy)

    if profile == "SOLID_CIRCULAR":
        mp = min(Fy * z, 1.6 * Fy * s)
        mn_ltb = mp
        ltb_note = "LTB not applicable for rounds in F11.2(a)."
        slender_param = None
        fcr = Fy
    else:
        mp = min(Fy * z, 1.5 * Fy * s)
        h = _positive(section.h)
        b = _positive(section.b)
        depth = max(h, b)
        thickness = min(h, b)
        slender_param = (Lb * depth) / (thickness**2) if min(Lb, depth, thickness) > 0.0 else 0.0
        limit_a = 0.08 * E / Fy if Fy > 0.0 else 0.0
        limit_b = 1.9 * E / Fy if Fy > 0.0 else 0.0
        if axis == "y":
            mn_ltb = mp
            fcr = Fy
            ltb_note = "LTB not applicable for minor-axis bending in rectangular bars (F11.2a)."
        elif slender_param <= limit_a:
            mn_ltb = mp
            fcr = Fy
            ltb_note = "LTB not applicable (F11.2a)."
        elif slender_param <= limit_b:
            fcr = Cb * Fy * (1.52 - 0.274 * slender_param * Fy / E)
            mn_ltb = min(mp, fcr * s)
            ltb_note = "Inelastic LTB branch (F11-3)."
        else:
            fcr = 1.9 * E / slender_param if slender_param > 0.0 else 0.0
            mn_ltb = min(mp, fcr * s)
            ltb_note = "Elastic LTB branch (F11-5)."

    mn = min(mp, mn_ltb)
    return {
        "Mn_Nmm": mn,
        "limit_states": {
            "yielding_Mn_Nmm": mp,
            "lateral_torsional_buckling_Mn_Nmm": mn_ltb,
        },
        "intermediate": {
            "axis": axis,
            "ltb_note": ltb_note,
            "slenderness_parameter": slender_param,
            "Fcr_mpa": fcr,
        },
    }
