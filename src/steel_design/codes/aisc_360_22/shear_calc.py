from ...design_methods import require_design_method
import math
from typing import Dict


NORMATIVE_E_MPA = 200000.0


def _safe_positive(value: float | None) -> float:
    return float(value) if isinstance(value, (int, float)) and value > 0.0 else 0.0


def calculate_cv1_g2_1(*, h_over_tw: float, fy_mpa: float, e_mpa: float, kv: float) -> Dict[str, float | str]:
    """
    Web shear buckling coefficient Cv1 for Section G2.1(b), Eq. G2-3/G2-4.
    """
    ratio = _safe_positive(h_over_tw)
    fy = _safe_positive(fy_mpa)
    e = _safe_positive(e_mpa)
    kv_value = _safe_positive(kv)
    if min(ratio, fy, e, kv_value) <= 0.0:
        return {"Cv1": 0.0, "limit_g2_3": 0.0, "branch": "invalid"}

    limit_g2_3 = 1.10 * math.sqrt((kv_value * e) / fy)
    if ratio <= limit_g2_3:
        return {"Cv1": 1.0, "limit_g2_3": limit_g2_3, "branch": "G2-3"}
    return {"Cv1": limit_g2_3 / ratio, "limit_g2_3": limit_g2_3, "branch": "G2-4"}


def calculate_cv2_g2_2(*, h_over_tw: float, fy_mpa: float, e_mpa: float, kv: float) -> Dict[str, float | str]:
    """
    Web shear buckling coefficient Cv2 for Section G2.2, Eq. G2-9/G2-10/G2-11.
    """
    ratio = _safe_positive(h_over_tw)
    fy = _safe_positive(fy_mpa)
    e = _safe_positive(e_mpa)
    kv_value = _safe_positive(kv)
    if min(ratio, fy, e, kv_value) <= 0.0:
        return {"Cv2": 0.0, "limit_g2_9": 0.0, "limit_g2_10": 0.0, "branch": "invalid"}

    limit_g2_9 = 1.10 * math.sqrt((kv_value * e) / fy)
    limit_g2_10 = 1.37 * math.sqrt((kv_value * e) / fy)
    if ratio <= limit_g2_9:
        return {"Cv2": 1.0, "limit_g2_9": limit_g2_9, "limit_g2_10": limit_g2_10, "branch": "G2-9"}
    if ratio <= limit_g2_10:
        return {"Cv2": limit_g2_9 / ratio, "limit_g2_9": limit_g2_9, "limit_g2_10": limit_g2_10, "branch": "G2-10"}
    cv2 = (1.51 * kv_value * e) / ((ratio**2) * fy)
    return {"Cv2": cv2, "limit_g2_9": limit_g2_9, "limit_g2_10": limit_g2_10, "branch": "G2-11"}


def calculate_nominal_shear_strength(*, fy_mpa: float, aw_mm2: float, cv: float) -> float:
    """
    Generic nominal shear strength equation used in G2/G4/G6:
    Vn = 0.6*Fy*Aw*Cv
    Returns N.
    """
    fy = _safe_positive(fy_mpa)
    aw = _safe_positive(aw_mm2)
    cv_value = _safe_positive(cv)
    if min(fy, aw, cv_value) <= 0.0:
        return 0.0
    return 0.6 * fy * aw * cv_value


def calculate_available_shear_strength(
    *,
    vn_n: float,
    design_method: str,
    phi_v: float,
    omega_v: float,
) -> float:
    """
    Converts nominal shear strength Vn (N) to available strength (kN).
    """
    method = require_design_method(design_method)
    vn = _safe_positive(vn_n)
    if vn <= 0.0:
        return 0.0
    if method == "LRFD":
        return _safe_positive(phi_v) * vn / 1000.0
    return vn / (_safe_positive(omega_v) * 1000.0) if _safe_positive(omega_v) > 0.0 else 0.0


def calculate_round_hss_fcr(
    *,
    e_mpa: float,
    fy_mpa: float,
    lv_mm: float | None,
    diameter_mm: float,
    thickness_mm: float,
) -> Dict[str, float | str | None]:
    """
    Shear critical stress Fcr for round HSS per Eq. G5-2a/G5-2b.
    """
    e = _safe_positive(e_mpa)
    fy = _safe_positive(fy_mpa)
    lv = _safe_positive(lv_mm)
    diameter = _safe_positive(diameter_mm)
    thickness = _safe_positive(thickness_mm)
    if min(e, fy, diameter, thickness) <= 0.0:
        return {"Fcr_mpa": 0.0, "fcr_g5_2a_mpa": 0.0, "fcr_g5_2b_mpa": 0.0, "branch": "invalid"}

    if lv_mm is None:
        # max(a,b), capped by 0.6Fy: if b reaches the cap, the answer is
        # independent of a and hence of unknown Lv. Otherwise do not invent Lv.
        lower_bound = .78 * e / ((diameter / thickness) ** 1.5)
        known = lower_bound >= .6 * fy
        return {"Fcr_mpa": .6 * fy if known else None, "fcr_g5_2a_mpa": None,
                "fcr_g5_2b_mpa": lower_bound,
                "branch": "yielding_proved_without_Lv" if known else "requires_Lv"}

    if lv <= 0:
        return {"Fcr_mpa": 0.0, "fcr_g5_2a_mpa": 0.0, "fcr_g5_2b_mpa": 0.0, "branch": "invalid"}

    lv_over_d = lv / diameter
    d_over_t = diameter / thickness
    if min(lv_over_d, d_over_t) <= 0.0:
        return {"Fcr_mpa": 0.0, "fcr_g5_2a_mpa": 0.0, "fcr_g5_2b_mpa": 0.0, "branch": "invalid"}

    # Eq. G5-2a and G5-2b
    fcr_g5_2a = (1.60 * e) / ((lv_over_d**0.5) * (d_over_t ** (5.0 / 4.0)))
    fcr_g5_2b = (0.78 * e) / (d_over_t ** (3.0 / 2.0))
    fcr = max(fcr_g5_2a, fcr_g5_2b)
    fcr_limited = min(fcr, 0.6 * fy)
    branch = "G5-2a" if fcr_g5_2a >= fcr_g5_2b else "G5-2b"
    if abs(fcr_limited - 0.6 * fy) <= 1e-9 and fcr > 0.6 * fy:
        branch = f"{branch}_limited_by_0.6Fy"
    return {
        "Fcr_mpa": fcr_limited,
        "fcr_g5_2a_mpa": fcr_g5_2a,
        "fcr_g5_2b_mpa": fcr_g5_2b,
        "branch": branch,
    }


def calculate_round_hss_nominal_shear_strength(*, fcr_mpa: float, ag_mm2: float) -> float:
    """
    Eq. G5-1: Vn = Fcr*Ag/2
    Returns N.
    """
    fcr = _safe_positive(fcr_mpa)
    ag = _safe_positive(ag_mm2)
    if min(fcr, ag) <= 0.0:
        return 0.0
    return fcr * ag / 2.0
