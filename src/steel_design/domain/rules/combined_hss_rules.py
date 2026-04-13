from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

from ...codes.aisc_360_22 import axial_calc, combined_hss_calc, flexure_calc, shear_calc
from ...models import CheckResult, CheckStatus, SteelCase
from ...sections.models import Section
from ..errors import ValidationError
from ..evaluators.tension_evaluator import TensionEvaluator


def _positive(value: Optional[float]) -> float:
    return float(value) if isinstance(value, (int, float)) and value > 0.0 else 0.0


def _nominal_pass(name: str, clause: str) -> CheckResult:
    return CheckResult(name=name, clause=clause, demand=0.0, capacity=0.0, dcr=0.0, status=CheckStatus.PASS)


def _build_result(*, name: str, clause: str, demand: float, capacity: float, details: dict) -> CheckResult:
    dcr = demand / capacity if capacity > 0.0 else float("inf")
    return CheckResult(
        name=name,
        clause=clause,
        demand=round(demand, 3),
        capacity=round(capacity, 3),
        dcr=round(dcr, 3),
        status=CheckStatus.PASS if dcr <= 1.0 else CheckStatus.FAIL,
        details=details,
    )


def _safe_ratio(*, demand: float, capacity: float, ratio_name: str) -> float:
    demand_abs = abs(demand)
    if demand_abs <= 0.0:
        return 0.0
    if capacity <= 0.0:
        raise ValidationError(
            "Interaction check cannot be evaluated because available strength is zero.",
            details={"ratio": ratio_name, "demand": demand_abs, "capacity": capacity},
        )
    return demand_abs / capacity


def _slenderness_values(section: Section) -> dict:
    return {
        "bf_2tf_ratio": section.bf_2tf_ratio,
        "b_t_ratio": section.b_t_ratio,
        "b_tdes_ratio": section.b_tdes_ratio,
        "h_tw_ratio": section.h_tw_ratio,
        "h_tdes_ratio": section.h_tdes_ratio,
        "d_t_ratio": section.d_t_ratio,
    }


def _effective_torsion_length(case: SteelCase) -> float:
    return case.factors.Kz * case.lengths.Lz


def _round_hss_dimensions(section: Section) -> Tuple[float, float]:
    diameter = _positive(section.od) or _positive(section.d)
    t = _positive(section.tdes) or _positive(section.t)
    if min(diameter, t) > 0.0:
        return diameter, t
    ratio = _positive(section.d_t_ratio)
    if diameter <= 0.0 and min(ratio, t) > 0.0:
        diameter = ratio * t
    elif t <= 0.0 and min(ratio, diameter) > 0.0:
        t = diameter / ratio
    return diameter, t


def _rectangular_hss_long_flat_width(section: Section) -> float:
    return max(_positive(section.h), _positive(section.b))


def _rectangular_hss_outside_dimensions(section: Section, t: float) -> Tuple[float, float]:
    # Catalog `h` and `b` are flat widths in this repository.
    # For user-note C approximation we conservatively recover outside dimensions
    # assuming outside corner radius ~= 2t -> flat width ~= B-3t.
    b_flat = _positive(section.b)
    h_flat = _positive(section.h)
    if min(b_flat, h_flat, t) <= 0.0:
        return 0.0, 0.0
    return b_flat + 3.0 * t, h_flat + 3.0 * t


def _torsion_capacity_h3(case: SteelCase, section: Section) -> Dict[str, object]:
    profile = section.type.upper()
    fy = case.material.Fy
    e = case.material.E
    l_eff = _effective_torsion_length(case)

    if profile == "CIRCULAR_HSS":
        diameter, t = _round_hss_dimensions(section)
        fcr_data = combined_hss_calc.calculate_round_hss_fcr_h3(E_mpa=e, Fy_mpa=fy, L_mm=l_eff, D_mm=diameter, t_mm=t)
        c_data = combined_hss_calc.calculate_round_hss_torsional_constant(
            D_mm=diameter,
            t_mm=t,
            c_catalog_mm3=_positive(section.c),
            j_mm4=_positive(section.j),
        )
        c_mm3 = float(c_data["C_mm3"])
        tn_nmm = combined_hss_calc.calculate_nominal_torsional_strength(fcr_mpa=float(fcr_data["Fcr_mpa"]), c_mm3=c_mm3)
        tc_kn_m = combined_hss_calc.calculate_available_torsional_strength(
            tn_nmm=tn_nmm,
            design_method=case.design_method.value,
        )
        return {
            "profile_type": profile,
            "Fcr_data": fcr_data,
            "C_data": c_data,
            "Tn_Nmm": tn_nmm,
            "Tc_kN_m": tc_kn_m,
            "inputs": {
                "Fy_mpa": fy,
                "E_mpa": e,
                "L_effective_mm": l_eff,
                "D_mm": diameter,
                "t_mm": t,
                "J_mm4": section.j,
                "C_catalog_mm3": section.c,
            },
        }

    h_long = _rectangular_hss_long_flat_width(section)
    t = _positive(section.tdes) or _positive(section.t)
    B_out, H_out = _rectangular_hss_outside_dimensions(section, t)
    fcr_data = combined_hss_calc.calculate_rectangular_hss_fcr_h3(E_mpa=e, Fy_mpa=fy, h_mm=h_long, t_mm=t)
    c_data = combined_hss_calc.calculate_rectangular_hss_torsional_constant(
        B_mm=B_out,
        H_mm=H_out,
        t_mm=t,
        c_catalog_mm3=_positive(section.c),
    )
    c_mm3 = float(c_data["C_mm3"])
    tn_nmm = combined_hss_calc.calculate_nominal_torsional_strength(fcr_mpa=float(fcr_data["Fcr_mpa"]), c_mm3=c_mm3)
    tc_kn_m = combined_hss_calc.calculate_available_torsional_strength(
        tn_nmm=tn_nmm,
        design_method=case.design_method.value,
    )
    return {
        "profile_type": profile,
        "Fcr_data": fcr_data,
        "C_data": c_data,
        "Tn_Nmm": tn_nmm,
        "Tc_kN_m": tc_kn_m,
        "inputs": {
            "Fy_mpa": fy,
            "E_mpa": e,
            "h_long_mm": h_long,
            "t_mm": t,
            "B_outside_mm": B_out,
            "H_outside_mm": H_out,
            "b_flat_mm": section.b,
            "h_flat_mm": section.h,
            "C_catalog_mm3": section.c,
        },
    }


def _available_axial_strength(case: SteelCase, section: Section) -> Dict[str, object]:
    pu = case.loads.Pu
    if pu == 0.0:
        return {"available_kN": math.inf, "mode": "none", "components": {}}

    if pu < 0.0:
        evaluation = TensionEvaluator().evaluate(case, section)
        available = min(evaluation["yielding_capacity"], evaluation["rupture_capacity"])
        return {
            "available_kN": available,
            "mode": "tension",
            "components": {
                "yielding_capacity_kN": evaluation["yielding_capacity"],
                "rupture_capacity_kN": evaluation["rupture_capacity"],
                "governing": "D2",
                "An_mm2": evaluation["An_mm2"],
                "U": evaluation["U_factor"],
                "Ae_mm2": evaluation["Ae_mm2"],
            },
        }

    fe_x = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Kx, case.lengths.Lx, section.rx or 0.0)
    fe_y = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Ky, case.lengths.Ly, section.ry or 0.0)
    fe_candidates = [value for value in (fe_x, fe_y) if value > 0.0]
    fe_e3 = min(fe_candidates) if fe_candidates else 0.0
    fcr_e3 = axial_calc.calculate_Fcr(case.material.Fy, fe_e3)
    pn_e3 = axial_calc.calculate_Pn(fcr_e3, section.area)
    p_available_e3 = axial_calc.calculate_available_compressive_strength(pn_e3, case.design_method.value)

    ro = section.ro
    if ro is None or ro <= 0.0:
        ro = axial_calc.calculate_ro_for_double_symmetric(section.area, section.ix or 0.0, section.iy or 0.0)
    fe_e4 = axial_calc.calculate_Fe_torsional(
        case.material.E,
        axial_calc.NORMATIVE_G_MPA,
        section.j or 0.0,
        section.cw or 0.0,
        case.factors.Kz,
        case.lengths.Lz,
        section.area,
        ro,
    )
    fcr_e4 = axial_calc.calculate_Fcr(case.material.Fy, fe_e4)
    pn_e4 = axial_calc.calculate_Pn(fcr_e4, section.area)
    p_available_e4 = axial_calc.calculate_available_compressive_strength(pn_e4, case.design_method.value)

    classification = axial_calc.classify_compression_elements(
        profile_type=section.type,
        slenderness=_slenderness_values(section),
        E=case.material.E,
        Fy=case.material.Fy,
    )

    p_available_e7 = None
    if classification.get("is_slender"):
        q = axial_calc.calculate_q_factor(section.type, _slenderness_values(section), case.material.E, case.material.Fy)
        fe_for_e7_candidates = [value for value in (fe_e3, fe_e4) if value > 0.0]
        fe_for_e7 = min(fe_for_e7_candidates) if fe_for_e7_candidates else 0.0
        fcr_e7 = axial_calc.calculate_Fcr_slender(case.material.Fy, fe_for_e7, q)
        pn_e7 = axial_calc.calculate_Pn(fcr_e7, section.area)
        p_available_e7 = axial_calc.calculate_available_compressive_strength(pn_e7, case.design_method.value)

    candidates = [value for value in (p_available_e3, p_available_e4, p_available_e7) if isinstance(value, (int, float)) and value > 0.0]
    available = min(candidates) if candidates else 0.0
    return {
        "available_kN": available,
        "mode": "compression",
        "components": {
            "E3_capacity_kN": p_available_e3,
            "E4_capacity_kN": p_available_e4,
            "E7_capacity_kN": p_available_e7,
            "Fex_mpa": fe_x,
            "Fey_mpa": fe_y,
            "Fe4_mpa": fe_e4,
            "element_classification": classification,
        },
    }


def _available_flexural_strength(case: SteelCase, section: Section, axis: str) -> Dict[str, object]:
    demand = abs(case.loads.Mux if axis == "x" else case.loads.Muy)
    if demand <= 0.0:
        return {"available_kN_m": math.inf, "evaluation": None}

    profile = section.type.upper()
    if profile == "RECTANGULAR_HSS":
        evaluation = flexure_calc.evaluate_f7(case, section, axis=axis)
    elif profile == "CIRCULAR_HSS":
        evaluation = flexure_calc.evaluate_f8(case, section, axis=axis)
    else:
        raise ValidationError("H1/H3 flexural interaction is scoped to HSS profiles only.", details={"profile_type": profile})

    available = flexure_calc.available_flexural_strength_lrfd(evaluation["Mn_Nmm"])
    return {"available_kN_m": available, "evaluation": evaluation}


def _rectangular_hss_shear_capacity(case: SteelCase, section: Section, axis: str) -> float:
    fy = case.material.Fy
    e = case.material.E
    t = _positive(section.tdes) or _positive(section.t)
    h_resisting = _positive(section.h) if axis == "x" else _positive(section.b)
    if h_resisting <= 0.0:
        h_resisting = _positive(section.b) if axis == "x" else _positive(section.h)
    h_over_t = h_resisting / t if min(h_resisting, t) > 0.0 else 0.0
    aw = 2.0 * h_resisting * t if min(h_resisting, t) > 0.0 else 0.0
    cv_data = shear_calc.calculate_cv2_g2_2(h_over_tw=h_over_t, fy_mpa=fy, e_mpa=e, kv=5.0)
    vn_n = shear_calc.calculate_nominal_shear_strength(fy_mpa=fy, aw_mm2=aw, cv=float(cv_data["Cv2"]))
    return shear_calc.calculate_available_shear_strength(
        vn_n=vn_n,
        design_method=case.design_method.value,
        phi_v=0.90,
        omega_v=1.67,
    )


def _round_hss_shear_capacity(case: SteelCase, section: Section, axis: str) -> float:
    fy = case.material.Fy
    e = case.material.E
    ag = _positive(section.area)
    diameter, t = _round_hss_dimensions(section)
    lv = case.lengths.Lx if axis == "x" else case.lengths.Ly
    fcr_data = shear_calc.calculate_round_hss_fcr(
        e_mpa=e,
        fy_mpa=fy,
        lv_mm=lv,
        diameter_mm=diameter,
        thickness_mm=t,
    )
    vn_n = shear_calc.calculate_round_hss_nominal_shear_strength(
        fcr_mpa=float(fcr_data["Fcr_mpa"]),
        ag_mm2=ag,
    )
    return shear_calc.calculate_available_shear_strength(
        vn_n=vn_n,
        design_method=case.design_method.value,
        phi_v=0.90,
        omega_v=1.67,
    )


def _required_shear_demand(case: SteelCase) -> float:
    if abs(case.loads.Vux) > 0.0 or abs(case.loads.Vuy) > 0.0:
        return max(abs(case.loads.Vux), abs(case.loads.Vuy))
    return abs(case.loads.Vu)


def _available_shear_strength(case: SteelCase, section: Section) -> Dict[str, object]:
    vr = _required_shear_demand(case)
    if vr <= 0.0:
        return {"required_kN": 0.0, "available_kN": math.inf, "axis_capacities": {"x": math.inf, "y": math.inf}}

    profile = section.type.upper()
    if profile == "RECTANGULAR_HSS":
        vc_x = _rectangular_hss_shear_capacity(case, section, "x")
        vc_y = _rectangular_hss_shear_capacity(case, section, "y")
    elif profile == "CIRCULAR_HSS":
        vc_x = _round_hss_shear_capacity(case, section, "x")
        vc_y = _round_hss_shear_capacity(case, section, "y")
    else:
        raise ValidationError("H3 shear interaction is scoped to HSS profiles only.", details={"profile_type": profile})

    return {
        "required_kN": vr,
        "available_kN": max(vc_x, vc_y),
        "axis_capacities": {"x": vc_x, "y": vc_y},
    }


def _compute_h1_interaction(case: SteelCase, section: Section) -> Dict[str, object]:
    if case.loads.Pu == 0.0 or (abs(case.loads.Mux) <= 0.0 and abs(case.loads.Muy) <= 0.0):
        raise ValidationError("H1 requires combined axial force and flexure.", details={"Pu": case.loads.Pu, "Mux": case.loads.Mux, "Muy": case.loads.Muy})

    axial = _available_axial_strength(case, section)
    flex_x = _available_flexural_strength(case, section, "x")
    flex_y = _available_flexural_strength(case, section, "y")

    pu_ratio = _safe_ratio(demand=case.loads.Pu, capacity=float(axial["available_kN"]), ratio_name="Pu/P_available")
    mx_ratio = _safe_ratio(demand=case.loads.Mux, capacity=float(flex_x["available_kN_m"]), ratio_name="Mux/Mcx")
    my_ratio = _safe_ratio(demand=case.loads.Muy, capacity=float(flex_y["available_kN_m"]), ratio_name="Muy/Mcy")

    if case.loads.Pu > 0.0:
        if pu_ratio >= 0.2:
            interaction = pu_ratio + ((8.0 / 9.0) * (mx_ratio + my_ratio))
            clause = "H1-1a"
            branch = "compression_high_axial"
        else:
            interaction = (pu_ratio / 2.0) + (mx_ratio + my_ratio)
            clause = "H1-1b"
            branch = "compression_low_axial"
    else:
        interaction = pu_ratio + mx_ratio + my_ratio
        clause = "H1-2"
        branch = "tension"

    return {
        "interaction_ratio": interaction,
        "clause": clause,
        "branch": branch,
        "ratios": {
            "Pu_over_Pavailable": pu_ratio,
            "Mux_over_Mcx": mx_ratio,
            "Muy_over_Mcy": my_ratio,
        },
        "capacities": {
            "P_available_kN": axial["available_kN"],
            "Mcx_kN_m": flex_x["available_kN_m"],
            "Mcy_kN_m": flex_y["available_kN_m"],
        },
        "components": {
            "axial": axial,
            "flexure_x": flex_x,
            "flexure_y": flex_y,
        },
    }


class CombinedH1HssRule:
    """H1 interaction for HSS members with combined axial force and flexure."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if case.loads.Pu == 0.0 or (abs(case.loads.Mux) <= 0.0 and abs(case.loads.Muy) <= 0.0):
            return _nominal_pass("Combined Forces H1", "H1")

        interaction = _compute_h1_interaction(case, section)
        return _build_result(
            name=f"Combined Forces ({interaction['clause']})",
            clause=interaction["clause"],
            demand=float(interaction["interaction_ratio"]),
            capacity=1.0,
            details={
                "memory": {
                    "clause": interaction["clause"],
                    "inputs": {
                        "Pu_kN": case.loads.Pu,
                        "Mux_kN_m": case.loads.Mux,
                        "Muy_kN_m": case.loads.Muy,
                    },
                    "intermediate": {
                        "branch": interaction["branch"],
                        **interaction["ratios"],
                        "interaction_ratio": interaction["interaction_ratio"],
                    },
                    "capacities": interaction["capacities"],
                    "components": interaction["components"],
                    "design_factor": {
                        "design_method": case.design_method.value,
                        "capacity_expression": "interaction <= 1.0",
                    },
                    "capacity": 1.0,
                }
            },
        )


class HssTorsionH3_1Rule:
    """H3-1: round and rectangular HSS subjected to torsion."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        tr = abs(case.loads.Tu)
        if tr <= 0.0:
            return _nominal_pass("HSS Torsion H3-1", "H3-1")

        torsion = _torsion_capacity_h3(case, section)
        tc = float(torsion["Tc_kN_m"])
        return _build_result(
            name="HSS Torsion (H3-1)",
            clause="H3-1",
            demand=tr,
            capacity=tc,
            details={
                "memory": {
                    "clause": "H3-1",
                    "inputs": {
                        **torsion["inputs"],
                        "Tr_kN_m": tr,
                    },
                    "intermediate": {
                        **torsion["Fcr_data"],
                        **torsion["C_data"],
                        "Tn_Nmm": torsion["Tn_Nmm"],
                        "Tn_kN_m": float(torsion["Tn_Nmm"]) / 1_000_000.0,
                    },
                    "design_factor": {
                        "design_method": case.design_method.value,
                        "phi_t": 0.90,
                        "omega_t": 1.67,
                        "capacity_expression": "phi_t*Tn (LRFD) or Tn/omega_t (ASD)",
                    },
                    "capacity_kN_m": tc,
                }
            },
        )


class HssCombinedH3_2Rule:
    """H3-2: HSS subjected to combined torsion, shear, flexure, and axial force."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        tr = abs(case.loads.Tu)
        has_other_forces = (
            abs(case.loads.Pu) > 0.0
            or abs(case.loads.Mux) > 0.0
            or abs(case.loads.Muy) > 0.0
            or abs(case.loads.Vu) > 0.0
            or abs(case.loads.Vux) > 0.0
            or abs(case.loads.Vuy) > 0.0
        )
        if tr <= 0.0 or not has_other_forces:
            return _nominal_pass("HSS Combined Actions H3-2", "H3-2")

        torsion = _torsion_capacity_h3(case, section)
        tc = float(torsion["Tc_kN_m"])
        torsion_threshold = 0.2 * tc

        if tr <= torsion_threshold:
            h1_interaction = None
            if case.loads.Pu != 0.0 and (abs(case.loads.Mux) > 0.0 or abs(case.loads.Muy) > 0.0):
                h1_interaction = _compute_h1_interaction(case, section)
            return _build_result(
                name="HSS Combined Actions Threshold (H3-2)",
                clause="H3-2",
                demand=tr,
                capacity=torsion_threshold,
                details={
                    "memory": {
                        "clause": "H3-2",
                        "inputs": {
                            "Tr_kN_m": tr,
                            "Tc_kN_m": tc,
                        },
                        "intermediate": {
                            "Tr_over_Tc": _safe_ratio(demand=tr, capacity=tc, ratio_name="Tr/Tc"),
                            "threshold_expression": "Tr <= 0.2*Tc",
                            "threshold_kN_m": torsion_threshold,
                            "h3_2_mode": "torsion_below_threshold_use_H1_and_G_checks",
                            "h1_reference": h1_interaction,
                        },
                        "design_factor": {
                            "design_method": case.design_method.value,
                            "capacity_expression": "0.2*Tc",
                        },
                        "capacity_kN_m": torsion_threshold,
                    }
                },
            )

        axial = _available_axial_strength(case, section)
        flex_x = _available_flexural_strength(case, section, "x")
        flex_y = _available_flexural_strength(case, section, "y")
        shear = _available_shear_strength(case, section)

        pu_ratio = _safe_ratio(demand=case.loads.Pu, capacity=float(axial["available_kN"]), ratio_name="Pr/Pc")
        mx_ratio = _safe_ratio(demand=case.loads.Mux, capacity=float(flex_x["available_kN_m"]), ratio_name="Mrx/Mcx")
        my_ratio = _safe_ratio(demand=case.loads.Muy, capacity=float(flex_y["available_kN_m"]), ratio_name="Mry/Mcy")
        vr_ratio = _safe_ratio(demand=float(shear["required_kN"]), capacity=float(shear["available_kN"]), ratio_name="Vr/Vrc")
        tr_ratio = _safe_ratio(demand=tr, capacity=tc, ratio_name="Tr/Tc")

        normal_ratio = pu_ratio + mx_ratio + my_ratio
        shear_torsion_ratio = vr_ratio + tr_ratio
        interaction = combined_hss_calc.calculate_h3_6_interaction(
            normal_ratio=normal_ratio,
            shear_torsion_ratio=shear_torsion_ratio,
        )

        return _build_result(
            name="HSS Combined Torsion/Shear/Flexure/Axial (H3-2)",
            clause="H3-2",
            demand=interaction,
            capacity=1.0,
            details={
                "memory": {
                    "clause": "H3-2",
                    "inputs": {
                        "Pr_kN": case.loads.Pu,
                        "Mrx_kN_m": case.loads.Mux,
                        "Mry_kN_m": case.loads.Muy,
                        "Vr_kN": shear["required_kN"],
                        "Tr_kN_m": tr,
                    },
                    "intermediate": {
                        "Tr_over_Tc": tr_ratio,
                        "Vr_over_Vrc": vr_ratio,
                        "Pr_over_Pc": pu_ratio,
                        "Mrx_over_Mcx": mx_ratio,
                        "Mry_over_Mcy": my_ratio,
                        "normal_ratio_sum": normal_ratio,
                        "shear_torsion_ratio_sum": shear_torsion_ratio,
                        "interaction_expression": "(Pr/Pc + Mrx/Mcx + Mry/Mcy)^2 + (Vr/Vrc + Tr/Tc)^2",
                        "interaction_ratio": interaction,
                    },
                    "capacities": {
                        "Pc_kN": axial["available_kN"],
                        "Mcx_kN_m": flex_x["available_kN_m"],
                        "Mcy_kN_m": flex_y["available_kN_m"],
                        "Vrc_kN": shear["available_kN"],
                        "Tc_kN_m": tc,
                        "Vrc_by_axis_kN": shear["axis_capacities"],
                    },
                    "components": {
                        "axial": axial,
                        "flexure_x": flex_x,
                        "flexure_y": flex_y,
                        "shear": shear,
                        "torsion": torsion,
                    },
                    "design_factor": {
                        "design_method": case.design_method.value,
                        "capacity_expression": "interaction <= 1.0",
                    },
                    "capacity": 1.0,
                }
            },
        )
