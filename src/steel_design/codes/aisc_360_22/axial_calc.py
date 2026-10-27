from ...design_methods import require_design_method
import math
from typing import Dict, Optional


NORMATIVE_E_MPA = 200000.0
NORMATIVE_G_MPA = 77200.0


def _classify_element(ratio: Optional[float], lambda_r: float) -> Dict[str, Optional[float]]:
    if ratio is None or ratio <= 0.0 or lambda_r <= 0.0:
        return {"ratio": ratio, "lambda_r": lambda_r, "classification": "unknown"}
    classification = "slender" if ratio > lambda_r else "non_slender"
    return {"ratio": ratio, "lambda_r": lambda_r, "classification": classification}


def classify_compression_elements(profile_type: str, slenderness: Dict[str, float], E: float, Fy: float) -> Dict[str, object]:
    """
    Element slenderness classification for compression members.
    Returns per-element classification and overall slenderness flag.
    """
    profile = (profile_type or "").upper()
    if E <= 0.0 or Fy <= 0.0:
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
    elif profile in {"SINGLE_ANGLE", "DOUBLE_ANGLE"}:
        elements["leg"] = _classify_element(slenderness.get("b_t_ratio"), 0.45 * sqrt_e_over_fy)

    statuses = [item["classification"] for item in elements.values()]
    is_slender = any(status == "slender" for status in statuses)
    if not statuses:
        overall = "unknown"
    elif all(status == "unknown" for status in statuses):
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
    if Fe_y <= 0.0 or Fe_z <= 0.0:
        return 0.0
    if H is None or H <= 0.0:
        H = 1.0

    sum_fe = Fe_y + Fe_z
    if sum_fe <= 0.0:
        return 0.0

    radicand = 1.0 - ((4.0 * Fe_y * Fe_z * H) / (sum_fe**2))
    if radicand < 0.0:
        radicand = 0.0
    return (sum_fe / (2.0 * H)) * (1.0 - math.sqrt(radicand))


def calculate_e5_effective_slenderness(slenderness: float, mode: str) -> float:
    """
    Effective slenderness approximation for single-angle compression (E5 mode selection).
    """
    if slenderness <= 0.0:
        return 0.0
    if mode == "one_leg":
        return 72.0 + 0.75 * slenderness
    return slenderness


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
