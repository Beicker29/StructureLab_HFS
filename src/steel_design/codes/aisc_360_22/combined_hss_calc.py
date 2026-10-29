from ...design_methods import require_design_method
from ...tracing import observed_value, quantity
import math
from typing import Dict, Optional


def _positive(value: Optional[float]) -> float:
    return float(value) if isinstance(value, (int, float)) and value > 0.0 else 0.0


def calculate_round_hss_torsional_constant(*, D_mm: float, t_mm: float, c_catalog_mm3: float, j_mm4: float) -> Dict[str, float | str]:
    """
    H3 User Note / commentary-aligned torsional constant C for round HSS.
    Preference order:
    1) catalog C
    2) conservative user note approximation C = pi*(D-t)^2*t/2
    j_mm4 is retained for call compatibility, but not used as a normative C.
    """
    c_catalog = _positive(c_catalog_mm3)
    D = _positive(D_mm)
    t = _positive(t_mm)

    if c_catalog > 0.0:
        return {"C_mm3": c_catalog, "source": "catalog_C"}

    if min(D, t) <= 0.0:
        return {"C_mm3": 0.0, "source": "invalid"}

    c_user = math.pi * ((D - t) ** 2) * t / 2.0
    return {"C_mm3": c_user, "source": "user_note_conservative"}


def calculate_rectangular_hss_torsional_constant(*, B_mm: float, H_mm: float, t_mm: float, c_catalog_mm3: float) -> Dict[str, float | str]:
    """
    H3 User Note conservative expression for rectangular HSS:
    C = 2*(B-t)*(H-t)*t - 4.5*(4-pi)*t^3
    """
    c_catalog = _positive(c_catalog_mm3)
    B = _positive(B_mm)
    H = _positive(H_mm)
    t = _positive(t_mm)

    if c_catalog > 0.0:
        return {"C_mm3": c_catalog, "source": "catalog_C"}

    if min(B, H, t) <= 0.0:
        return {"C_mm3": 0.0, "source": "invalid"}

    c_user = (2.0 * (B - t) * (H - t) * t) - (4.5 * (4.0 - math.pi) * (t**3))
    return {"C_mm3": max(c_user, 0.0), "source": "user_note_conservative"}


def calculate_round_hss_fcr_h3(*, E_mpa: float, Fy_mpa: float, L_mm: float | None, D_mm: float, t_mm: float) -> Dict[str, float | str | None]:
    """
    H3-2a/H3-2b for round HSS torsion:
    Fcr = max(Fcr_2a, Fcr_2b), but <= 0.6Fy
    """
    E = _positive(E_mpa)
    Fy = _positive(Fy_mpa)
    L = _positive(L_mm)
    D = _positive(D_mm)
    t = _positive(t_mm)
    if min(E, Fy, D, t) <= 0.0:
        return {"Fcr_mpa": 0.0, "Fcr_H3_2a_mpa": 0.0, "Fcr_H3_2b_mpa": 0.0, "branch": "invalid"}

    if L_mm is None:
        lower_bound = .60 * E / ((D / t) ** 1.5)
        known = lower_bound >= .6 * Fy
        return {"Fcr_mpa": .6 * Fy if known else None, "Fcr_H3_2a_mpa": None,
                "Fcr_H3_2b_mpa": lower_bound,
                "branch": "yielding_proved_without_L" if known else "requires_member_length"}
    if L <= 0:
        return {"Fcr_mpa": 0.0, "Fcr_H3_2a_mpa": 0.0, "Fcr_H3_2b_mpa": 0.0, "branch": "invalid"}

    l_over_d = L / D
    d_over_t = D / t
    if min(l_over_d, d_over_t) <= 0.0:
        return {"Fcr_mpa": 0.0, "Fcr_H3_2a_mpa": 0.0, "Fcr_H3_2b_mpa": 0.0, "branch": "invalid"}

    fcr_h3_2a = 1.23 * E / ((l_over_d**0.5) * (d_over_t ** 1.25))
    fcr_h3_2b = 0.60 * E / (d_over_t**1.5)
    fcr = max(fcr_h3_2a, fcr_h3_2b)
    fcr_limited = min(fcr, 0.6 * Fy)
    branch = "H3-2a" if fcr_h3_2a >= fcr_h3_2b else "H3-2b"
    if fcr > 0.6 * Fy:
        branch = f"{branch}_limited_by_0.6Fy"
    return {
        "Fcr_mpa": fcr_limited,
        "Fcr_H3_2a_mpa": fcr_h3_2a,
        "Fcr_H3_2b_mpa": fcr_h3_2b,
        "branch": branch,
    }


def calculate_rectangular_hss_fcr_h3(*, E_mpa: float, Fy_mpa: float, h_mm: float, t_mm: float) -> Dict[str, float | str | None]:
    """
    H3-3/H3-4/H3-5 for rectangular HSS torsion.
    """
    E = _positive(E_mpa)
    Fy = _positive(Fy_mpa)
    h = _positive(h_mm)
    t = _positive(t_mm)
    if min(E, Fy, h, t) <= 0.0:
        return {
            "Fcr_mpa": 0.0,
            "h_over_t": 0.0,
            "limit_H3_3": 0.0,
            "limit_H3_4": 0.0,
            "branch": "invalid",
        }

    h_over_t = h / t
    sqrt_e_over_fy = math.sqrt(E / Fy)
    limit_h3_3 = 2.45 * sqrt_e_over_fy
    limit_h3_4 = 3.07 * sqrt_e_over_fy

    if h_over_t <= limit_h3_3:
        return {
            "Fcr_mpa": 0.6 * Fy,
            "h_over_t": h_over_t,
            "limit_H3_3": limit_h3_3,
            "limit_H3_4": limit_h3_4,
            "branch": "H3-3",
        }

    if h_over_t <= limit_h3_4:
        fcr = 0.6 * Fy * (limit_h3_3 / h_over_t)
        return {
            "Fcr_mpa": fcr,
            "h_over_t": h_over_t,
            "limit_H3_3": limit_h3_3,
            "limit_H3_4": limit_h3_4,
            "branch": "H3-4",
        }

    if h_over_t > 260:
        return {"Fcr_mpa": None, "h_over_t": h_over_t, "limit_H3_3": limit_h3_3,
                "limit_H3_4": limit_h3_4, "branch": "outside_H3_5_h_over_t_260"}
    fcr = 0.458 * math.pi**2 * E / (h_over_t**2)
    return {
        "Fcr_mpa": fcr,
        "h_over_t": h_over_t,
        "limit_H3_3": limit_h3_3,
        "limit_H3_4": limit_h3_4,
        "branch": "H3-5",
    }


def calculate_nominal_torsional_strength(*, fcr_mpa: float, c_mm3: float) -> float:
    """
    H3-1: Tn = Fcr * C.
    Fcr in MPa (N/mm2), C in mm3 -> N*mm.
    """
    fcr = _positive(fcr_mpa)
    c_value = _positive(c_mm3)
    if min(fcr, c_value) <= 0.0:
        return 0.0
    return observed_value(fcr * c_value, name="Tn", unit="N-mm", producer=__name__+":calculate_nominal_torsional_strength",
        limit_state="HSS_torsion", branch="positive_inputs", reference="H3.1", equation="H3-1",
        expression="Fcr * C", inputs=(quantity("Fcr", fcr, "MPa"), quantity("C", c_value, "mm3")))


def calculate_available_torsional_strength(*, tn_nmm: float, design_method: str, phi_t: float = 0.90, omega_t: float = 1.67) -> float:
    """
    Converts Tn from N*mm to available torsional strength in kN-m.
    """
    method = require_design_method(design_method)
    tn = _positive(tn_nmm)
    if tn <= 0.0:
        return 0.0
    if method == "LRFD":
        return observed_value(_positive(phi_t) * tn / 1_000_000.0, name="Tc", unit="kN-m",
            producer=__name__+":calculate_available_torsional_strength", limit_state="HSS_torsion",
            branch="LRFD", reference="H3.1", equation=None, expression="positive(phi_t) * Tn / 1000000",
            inputs=(quantity("Tn", tn, "N-mm"),), factors=(quantity("phi_t", phi_t, "ratio", "function argument"),),
            unknowns=("Conversion; critical stress branch is not expanded here.",))
    omega = _positive(omega_t)
    return observed_value((tn / omega) / 1_000_000.0 if omega > 0.0 else 0.0, name="Tc", unit="kN-m",
        producer=__name__+":calculate_available_torsional_strength", limit_state="HSS_torsion",
        branch="ASD", reference="H3.1", equation=None, expression="(Tn / omega) / 1000000 if omega > 0 else 0",
        inputs=(quantity("Tn", tn, "N-mm"),), factors=(quantity("omega", omega, "ratio", "positive(omega_t)"),),
        unknowns=("Conversion; existing invalid-factor fallback preserved, not accredited.",))


def calculate_h3_6_interaction(*, normal_ratio: float, shear_torsion_ratio: float) -> float:
    """
    H3-6 interaction in implemented scope:
    normal_ratio + (shear_torsion_ratio)^2, S22 printed 16.1-86.
    """
    normal = max(0.0, float(normal_ratio))
    shear_torsion = max(0.0, float(shear_torsion_ratio))
    return observed_value(normal + (shear_torsion**2), name="interaction", unit="ratio",
        producer=__name__+":calculate_h3_6_interaction", limit_state="HSS_combined_actions",
        branch="nonnegative_terms", reference="H3.2", equation="H3-6",
        expression="normal + shear_torsion**2",
        inputs=(quantity("normal", normal, "ratio"), quantity("shear_torsion", shear_torsion, "ratio")))
