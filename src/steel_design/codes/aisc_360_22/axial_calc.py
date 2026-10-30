from ...design_methods import require_design_method
import math
from typing import Dict, Optional


NORMATIVE_E_MPA = 200000.0
NORMATIVE_G_MPA = 77200.0


def _classify_element(ratio: Optional[float], lambda_r: float) -> Dict[str, Optional[float]]:
    if ratio is None or not math.isfinite(ratio) or ratio <= 0.0 or not math.isfinite(lambda_r) or lambda_r <= 0.0:
        return {"ratio": ratio, "lambda_r": lambda_r, "classification": "unknown"}
    classification = "slender" if ratio > lambda_r else "non_slender"
    return {"ratio": ratio, "lambda_r": lambda_r, "classification": classification}


def classify_compression_elements(profile_type: str, slenderness: Dict[str, float], E: float, Fy: float) -> Dict[str, object]:
    """
    Element slenderness classification for compression members.
    Returns per-element classification and overall slenderness flag.
    """
    profile = (profile_type or "").upper()
    if not math.isfinite(E) or not math.isfinite(Fy) or E <= 0.0 or Fy <= 0.0:
        return {"profile_type": profile, "overall": "unknown", "is_slender": False, "elements": {}}

    sqrt_e_over_fy = math.sqrt(E / Fy)
    elements: Dict[str, Dict[str, Optional[float]]] = {}

    if profile in {"W"}:
        elements["flange"] = _classify_element(slenderness.get("bf_2tf_ratio"), 0.56 * sqrt_e_over_fy)
        elements["web"] = _classify_element(slenderness.get("h_tw_ratio"), 1.49 * sqrt_e_over_fy)
    elif profile == "CHANNEL":
        elements["flange"] = _classify_element(slenderness.get("b_t_ratio"), 0.56 * sqrt_e_over_fy)
        elements["web"] = _classify_element(slenderness.get("h_tw_ratio"), 1.49 * sqrt_e_over_fy)
    elif profile == "RECTANGULAR_HSS":
        limit = 1.40 * sqrt_e_over_fy
        elements["wall_b"] = _classify_element(slenderness.get("b_tdes_ratio"), limit)
        elements["wall_h"] = _classify_element(slenderness.get("h_tdes_ratio"), limit)
    elif profile == "CIRCULAR_HSS":
        elements["wall"] = _classify_element(slenderness.get("d_t_ratio"), 0.11 * (E / Fy))
    elif profile == "SINGLE_ANGLE":
        elements["leg"] = _classify_element(slenderness.get("b_t_ratio"), 0.45 * sqrt_e_over_fy)
    # DOUBLE_ANGLE needs contact/fabrication data absent from JSON 1.0.
    # No choice between B4.1a cases 1 and 3 can be inferred from this label.

    statuses = [item["classification"] for item in elements.values()]
    is_slender = any(status == "slender" for status in statuses)
    if not statuses:
        overall = "unknown"
    elif any(status == "unknown" for status in statuses):
        overall = "unknown"
    elif is_slender:
        overall = "slender"
    else:
        overall = "non_slender"

    return {
        "profile_type": profile,
        "overall": overall,
        "is_slender": is_slender,
        "elements": elements,
    }


def calculate_Fe_flexural(E: float, K: float, L: float, r: float) -> float:
    """
    Elastic flexural buckling stress Fe per AISC 360-22 Eq. E3-4.
    Returns MPa.
    """
    if E <= 0.0 or K <= 0.0 or L <= 0.0 or r is None or r <= 0.0:
        return 0.0
    slenderness = (K * L) / r
    return (math.pi**2 * E) / (slenderness**2)


def calculate_Fcr(Fy: float, Fe: float) -> float:
    """
    Critical stress Fcr per AISC 360-22 Eq. E3-2 and E3-3.
    Returns MPa.
    """
    if Fy <= 0.0 or Fe <= 0.0:
        return 0.0

    if (Fy / Fe) <= 2.25:
        return (0.658 ** (Fy / Fe)) * Fy
    return 0.877 * Fe


def calculate_Pn(Fcr: float, Ag: float) -> float:
    """
    Nominal compressive strength Pn = Fcr * Ag.
    Fcr in MPa and Ag in mm2 -> N.
    """
    if Fcr <= 0.0 or Ag <= 0.0:
        return 0.0
    return Fcr * Ag


def compression_design_factor(method: str) -> dict:
    method = require_design_method(method).value
    if method == "LRFD":
        return {"design_method": method, "phi": 0.90, "omega": None, "capacity_expression": "phi*Pn"}
    return {"design_method": method, "phi": None, "omega": 1.67, "capacity_expression": "Pn/omega"}


def calculate_available_compressive_strength(Pn: float, method: str) -> float:
    """
    Converts Pn (N) to available compressive strength (kN).
    LRFD: phi_c = 0.90
    ASD: omega_c = 1.67
    """
    factor = compression_design_factor(method)
    if Pn <= 0.0:
        return 0.0
    Pn_kn = Pn / 1000.0
    if factor["design_method"] == "LRFD":
        return factor["phi"] * Pn_kn
    return Pn_kn / factor["omega"]


def calculate_ro_for_double_symmetric(Ag: float, Ix: float, Iy: float) -> float:
    """
    Approximates polar radius about shear center for double-symmetric shapes.
    ro^2 = (Ix + Iy) / Ag
    """
    if Ag <= 0.0 or Ix is None or Iy is None or Ix <= 0.0 or Iy <= 0.0:
        return 0.0
    return math.sqrt((Ix + Iy) / Ag)


def calculate_Fe_torsional(
    E: float,
    G: float,
    J: float,
    Cw: float,
    Kz: float,
    Lz: float,
    Ag: float,
    ro: float,
) -> float:
    """
    Elastic torsional buckling stress Fez for compression members.
    Returns MPa.
    """
    if min(E, G, J, Kz, Lz, Ag, ro) <= 0.0:
        return 0.0
    torsional_stiffness = ((math.pi**2 * E * Cw) / ((Kz * Lz) ** 2)) + (G * J)
    return torsional_stiffness / (Ag * (ro**2))


def calculate_Fe_flexural_torsional(Fe_y: float, Fe_z: float, H: float) -> float:
    """
    Flexural-torsional elastic buckling stress (lower root form).
    Returns MPa.
    """
    _positive_finite(Fe_symmetry=Fe_y, Fe_z=Fe_z)
    if H is None or not math.isfinite(H) or not 0.0 < H <= 1.0:
        raise ValueError("E4 coupling requires an explicit finite H in (0, 1]; unknown is not 1.")

    # Rationalized E4-3 avoids subtracting nearly equal numbers when H is small.
    # Scaling also avoids squaring physical stress magnitudes.
    scale = max(Fe_y, Fe_z)
    a, b = Fe_y / scale, Fe_z / scale
    discriminant = (a - b)**2 + 4 * a * b * (1 - H)
    return scale * 2 * a * b / (a + b + math.sqrt(discriminant))


def _positive_finite(**values: float) -> None:
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")


def calculate_Fe_unsymmetric(Fex: float, Fey: float, Fez: float, xo: float, yo: float, ro: float) -> dict:
    """S22 E4-4: smallest root, principal axes and shear-center coordinates (mm).

    For 0<z<min(Fex,Fey), divide the characteristic polynomial by
    (Fex-z)(Fey-z): Fez-z-z²*alpha/(Fex-z)-z²*beta/(Fey-z).
    It is strictly decreasing. The lowest root is therefore bracketed by zero
    and min(Fex,Fey,Fez), including uncoupled roots at that upper endpoint.
    Bisection uses dimensionless stresses; residual and iterations are exposed.
    """
    _positive_finite(Fex=Fex, Fey=Fey, Fez=Fez, ro=ro)
    if not all(math.isfinite(v) for v in (xo, yo)):
        raise ValueError("Shear-center coordinates must be finite")
    alpha, beta = (xo/ro)**2, (yo/ro)**2
    if alpha + beta >= 1:
        raise ValueError("E4-8 requires positive H=1-(xo²+yo²)/ro²")
    scale = max(Fex, Fey, Fez)
    a, b, c = Fex/scale, Fey/scale, Fez/scale

    def polynomial(z):
        return (a-z)*(b-z)*(c-z) - z*z*(b-z)*alpha - z*z*(a-z)*beta

    lo, hi = 0.0, min(a, b, c)
    # Coincident flexural poles may make P(hi)=0 while a smaller coupled
    # root exists. Probe the monotone secular equation instead of accepting hi.
    for iteration in range(100):
        mid = (lo+hi)/2
        if mid == lo or mid == hi:
            break
        if polynomial(mid) > 0:
            lo = mid
        else:
            hi = mid
    root = (lo+hi)/2
    return {"Fe_mpa": root*scale, "H": 1-alpha-beta,
            "normalized_residual": polynomial(root), "iterations": iteration+1,
            "bracket_mpa": [lo*scale, hi*scale], "equation": "E4-4"}


def calculate_Fe_offset(*, E: float, G: float, J: float, Ix: float, Iy: float,
                        Ag: float, rx: float, ry: float, ho: float, Lcz: float,
                        xa: float, ya: float, bracing: str) -> dict:
    """S22 E4(d/e), doubly symmetric I only; caller proves family/restraints.

    Distances mm, inertias/J mm4, Ag mm2, E/G MPa. No simultaneous offsets or
    default choice of the lateral restraint. E4(f) requires separate analysis.
    """
    _positive_finite(E=E, G=G, J=J, Ix=Ix, Iy=Iy, Ag=Ag, rx=rx, ry=ry, ho=ho, Lcz=Lcz)
    if not all(math.isfinite(v) for v in (xa, ya)):
        raise ValueError("Bracing offsets must be finite")
    if bracing == "MINOR_AXIS_LATERAL" and xa == 0:
        term, equation = ho**2/4 + ya**2, "E4-10"
    elif bracing == "MAJOR_AXIS_LATERAL" and ya == 0:
        term, equation = ho**2/4 + (Ix/Iy)*xa**2, "E4-12"
    else:
        raise ValueError("Offset configuration requires E4(f) analysis")
    ro2 = rx**2 + ry**2 + xa**2 + ya**2
    fe = (math.pi**2 * E * Iy / Lcz**2 * term + G*J) / (Ag*ro2)
    return {"Fe_mpa": fe, "ro2_mm2": ro2, "equation": equation}


def calculate_e5_slenderness(*, s: float, configuration: str, connected_leg: str,
                             leg_ratio: float, principal_slenderness: float | None) -> dict:
    """S22 E5-1..4 and (a/b)(2), geometry supplied explicitly.

    s=L/ra, principal_slenderness=L/rz. The returned eligibility flag is
    mandatory: extrapolated arithmetic above 200 is not a design permission.
    Connection/end-load/adjacent-web conditions belong to the case evaluator.
    """
    _positive_finite(s=s, leg_ratio=leg_ratio)
    if not 1 <= leg_ratio < 1.7:
        raise ValueError("E5 requires 1 <= bl/bs < 1.7")
    if connected_leg not in {"LONG", "SHORT", "EQUAL"}:
        raise ValueError("E5 requires the connected leg")
    if (connected_leg == "EQUAL") != (leg_ratio == 1):
        raise ValueError("Equal/unequal leg designation contradicts bl/bs")
    if configuration == "A":
        base, equation = (72 + .75*s, "E5-1") if s <= 80 else (32 + 1.25*s, "E5-2")
        coefficient, floor_factor = 4, .95
    elif configuration == "B":
        base, equation = (60 + .8*s, "E5-3") if s <= 75 else (45 + s, "E5-4")
        coefficient, floor_factor = 6, .82
    else:
        raise ValueError("E5 requires an explicit A/B configuration")
    correction, floor = 0.0, 0.0
    if connected_leg == "SHORT":
        _positive_finite(principal_slenderness=principal_slenderness)
        correction = coefficient*(leg_ratio**2-1)
        floor = floor_factor*principal_slenderness
    effective = max(base+correction, floor)
    return {"effective_slenderness": effective, "base": base, "correction": correction,
            "principal_floor": floor, "equation": equation, "eligible_slenderness": effective <= 200}


def calculate_e6_slenderness(*, s0: float, a_over_ri: float, connector: str, arrangement: str) -> dict:
    """S22 E6-1/2; only for modes producing relative shear in connectors.

    End connections and E6.2 detailing must be checked by the caller.
    """
    _positive_finite(s0=s0, a_over_ri=a_over_ri)
    ki = {"ANGLES_BACK_TO_BACK": .50, "CHANNELS_BACK_TO_BACK": .75, "OTHER": .86}.get(arrangement)
    if ki is None:
        raise ValueError("E6 requires an explicit component arrangement")
    if connector == "SNUG_TIGHT":
        value, equation = math.hypot(s0, a_over_ri), "E6-1"
    elif connector in {"WELDED", "PRETENSIONED_CLASS_A", "PRETENSIONED_CLASS_B"}:
        value, equation = (s0, "E6-2a") if a_over_ri <= 40 else (math.hypot(s0, ki*a_over_ri), "E6-2b")
    else:
        raise ValueError("E6 connector type/class is not supported")
    return {"modified_slenderness": value, "Ki": ki, "equation": equation}


def calculate_e7_effective_width(*, b: float, t: float, lambda_r: float,
                                 Fn: float, Fy: float, element_kind: str) -> dict:
    """S22 E7-2..5; c1 from Table E7.1, c2 from E7-4 without rounding.

    HFS-031R engineering criterion confirmed by user. b/t must be the B4.1
    element width, not a reconstructed outside HSS dimension. Units mm/MPa.
    """
    _positive_finite(b=b, t=t, lambda_r=lambda_r, Fn=Fn, Fy=Fy)
    if Fn > Fy:
        raise ValueError("E7 nominal stress cannot exceed Fy")
    c1 = {"STIFFENED": .18, "HSS_WALL": .20, "UNSTIFFENED": .22}.get(element_kind)
    if c1 is None:
        raise ValueError("Unknown E7.1 element kind")
    c2 = 2 / (1 + math.sqrt(1 - 4*c1))  # Rationalized E7-4, no rounded table c2.
    ratio = b/t
    fel = (c2*lambda_r/ratio)**2*Fy
    if ratio <= lambda_r*math.sqrt(Fy/Fn):
        be, equation = b, "E7-2"
    else:
        z = math.sqrt(fel/Fn)
        be, equation = b*(1-c1*z)*z, "E7-3"
    return {"be_mm": be, "b_mm": b, "t_mm": t, "lambda": ratio, "lambda_r": lambda_r,
            "c1": c1, "c2": c2, "Fel_mpa": fel, "Fn_mpa": Fn, "equation": equation,
            "area_loss_mm2": (b-be)*t}


def calculate_e7_round_area(*, Ag: float, D_over_t: float, E: float, Fy: float) -> dict:
    """S22 E7-6/7, outside diameter / design thickness, strict upper limit.

    HFS-031R explicit engineering criterion: Ae <= Ag. The literal E7-7
    expression can exceed Ag for .11E/Fy < D/t < .114E/Fy. Preserve its value
    and the applied bound; this is not represented as a published AISC erratum.
    """
    _positive_finite(Ag=Ag, D_over_t=D_over_t, E=E, Fy=Fy)
    if D_over_t <= .11*E/Fy:
        ae, equation = Ag, "E7-6"
    elif D_over_t < .45*E/Fy:
        ae, equation = (.038*E/(Fy*D_over_t)+2/3)*Ag, "E7-7"
    else:
        raise ValueError("D/t is outside E7-7: D/t must be strictly below 0.45E/Fy")
    return {"Ae_mm2": min(ae, Ag), "Ae_equation_mm2": ae, "Ag_mm2": Ag,
            "gross_area_bound_applied": ae > Ag, "equation": equation,
            "area_bound_basis": "HFS-031R user-confirmed Ae<=Ag criterion"}


def calculate_e7_plate_area(*, Ag: float, Fn: float, Fy: float, elements: list[dict]) -> dict:
    """E7-1 area from explicit B4 plates; caller owns family/completeness.

    Corners/fillets remain in Ag. Only each plate's (b-be)t loss is deducted.
    Counts are physical repetitions, never a calibration or an area multiplier.
    """
    _positive_finite(Ag=Ag)
    if not elements:
        raise ValueError("E7 requires all compression elements")
    rows = []
    for element in elements:
        count = element['count']
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ValueError("E7 element count must be a positive integer")
        row = calculate_e7_effective_width(b=element['b'], t=element['t'],
            lambda_r=element['lambda_r'], Fn=Fn, Fy=Fy, element_kind=element['kind'])
        rows.append({**row, 'count': count, 'total_loss_mm2': count*row['area_loss_mm2']})
    ae = Ag-math.fsum(row['total_loss_mm2'] for row in rows)
    if not math.isfinite(ae) or ae <= 0:
        raise ValueError("E7 effective area is not positive; verify Ag and physical plate geometry")
    return {'Ae_mm2': ae, 'Ag_mm2': Ag, 'elements': rows, 'equation': 'E7-1'}


def calculate_q_factor(profile_type: str, slenderness: Dict[str, float], E: float, Fy: float) -> float:
    """
    Q reduction factor for members with slender elements (E7), by section family.
    """
    if E <= 0.0 or Fy <= 0.0:
        return 1.0

    profile = (profile_type or "").upper()
    sqrt_e_over_fy = math.sqrt(E / Fy)

    def ratio_limit(ratio_value: float, limit: float) -> float:
        if ratio_value is None or ratio_value <= 0.0 or limit <= 0.0:
            return 1.0
        return min(1.0, limit / ratio_value)

    if profile in {"W", "CHANNEL"}:
        flange_ratio = slenderness.get("bf_2tf_ratio")
        if flange_ratio is None or flange_ratio <= 0.0:
            flange_ratio = slenderness.get("b_t_ratio")
        web_ratio = slenderness.get("h_tw_ratio")
        qf = ratio_limit(flange_ratio, 0.56 * sqrt_e_over_fy)
        qw = ratio_limit(web_ratio, 1.49 * sqrt_e_over_fy)
        return max(0.0, min(1.0, qf * qw))

    if profile == "RECTANGULAR_HSS":
        raw_ratios = (
            slenderness.get("b_tdes_ratio"),
            slenderness.get("h_tdes_ratio"),
            slenderness.get("b_t_ratio"),
            slenderness.get("h_tw_ratio"),
        )
        ratios = [value for value in raw_ratios if isinstance(value, (int, float)) and value > 0.0]
        wall_ratio = max(ratios) if ratios else 0.0
        return ratio_limit(wall_ratio, 1.40 * sqrt_e_over_fy)

    if profile == "CIRCULAR_HSS":
        d_t_ratio = slenderness.get("d_t_ratio")
        return ratio_limit(d_t_ratio, 0.11 * (E / Fy))

    if profile in {"SINGLE_ANGLE", "DOUBLE_ANGLE"}:
        angle_ratio = slenderness.get("b_t_ratio")
        return ratio_limit(angle_ratio, 0.45 * sqrt_e_over_fy)

    return 1.0


def calculate_Fcr_slender(Fy: float, Fe: float, Q: float) -> float:
    """
    Critical stress form for slender compression elements using Q*Fy.
    """
    if Fe <= 0.0 or Fy <= 0.0:
        return 0.0
    qfy = max(0.0, min(1.0, Q)) * Fy
    if qfy <= 0.0:
        return 0.0
    return calculate_Fcr(qfy, Fe)
