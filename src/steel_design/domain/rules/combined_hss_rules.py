from __future__ import annotations

import math
from typing import Dict, Optional

from ...codes.aisc_360_22 import axial_calc, combined_hss_calc, flexure_calc
from ...models import CheckResult, CheckStatus, SteelCase
from ...sections.models import Section
from ..errors import ValidationError, IncompleteSectionDataError, RuleNotImplementedError
from ..actions import shear_demand, shear_trace
from ..evaluators.hss_shear import evaluate_hss_shear, round_hss_dimensions, require_section_values
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


def _torsion_capacity_h3(case: SteelCase, section: Section) -> Dict[str, object]:
    profile = section.type.upper()
    fy = case.material.Fy
    e = case.material.E

    if profile == "CIRCULAR_HSS":
        diameter, t = round_hss_dimensions(section)
        fcr_data = combined_hss_calc.calculate_round_hss_fcr_h3(E_mpa=e, Fy_mpa=fy, L_mm=None, D_mm=diameter, t_mm=t)
        if fcr_data["Fcr_mpa"] is None:
            raise IncompleteSectionDataError("H3.1 needs member length L; Kz*Lz is not that length.",
                details={"reference": "H3-2a/b", "section": section.name,
                         "required": "Physical member length L; input not yet represented", "Fcr_data": fcr_data})
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
                "L_member_mm": None,
                "D_mm": diameter,
                "t_mm": t,
                "J_mm4": section.j,
                "C_catalog_mm3": section.c,
            },
        }

    if profile != "RECTANGULAR_HSS":
        raise RuleNotImplementedError("H3.1 is limited to round/rectangular HSS.", details={"profile_type": profile})
    h, b, t = require_section_values(section, ("h", "b", "tdes"), "H3.1(b); B4.2")
    h_long = max(h, b)
    fcr_data = combined_hss_calc.calculate_rectangular_hss_fcr_h3(E_mpa=e, Fy_mpa=fy, h_mm=h_long, t_mm=t)
    if fcr_data["Fcr_mpa"] is None:
        raise RuleNotImplementedError("Rectangular HSS outside H3-5 applicability (h/t > 260).",
                                      details={"reference": "H3-5", "h_over_t": h_long / t})
    (c_value,) = require_section_values(section, ("c",), "H3-1: C in mm3")
    # Flat widths cannot be inverted to exact exterior B/H without corner geometry.
    c_data = {"C_mm3": c_value, "source": "declared_C_no_outside_geometry_inference"}
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

    available = flexure_calc.available_flexural_strength(evaluation["Mn_Nmm"], case.design_method.value)
    return {"available_kN_m": available, "evaluation": evaluation}


def _available_shear_strength(case: SteelCase, section: Section) -> Dict[str, object]:
    # H3-6 specifies the larger RATIO, retaining each demand with its own capacity.
    evaluations, capacities, demands, ratios = {}, {}, {}, {}
    for axis in ("x", "y"):
        demands[axis] = shear_demand(case, axis)
        if demands[axis] == 0:
            ratios[axis], capacities[axis] = 0.0, None
            continue
        evaluation = evaluate_hss_shear(case, section, axis)
        evaluations[axis] = evaluation
        capacities[axis] = evaluation["capacity_kN"]
        ratios[axis] = _safe_ratio(demand=demands[axis], capacity=capacities[axis], ratio_name=f"Vr{axis}/Vc{axis}")
    governing = max(ratios, key=ratios.get) if any(demands.values()) else None
    return {"required_kN": demands[governing] if governing else 0.0,
            "available_kN": capacities[governing] if governing else None,
            "ratio": ratios[governing] if governing else 0.0, "governing_axis": governing,
            "axis_capacities": capacities, "axis_demands": demands, "axis_ratios": ratios,
            "evaluations": evaluations,
            "directions": {axis: shear_trace(case, axis) for axis in ("x", "y")}}


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
            raise RuleNotImplementedError(
                "H3.2 permits neglecting torsional interaction at Tr/Tc <= 0.20, but a qualified H1/G alternative is not established; threshold is not a resistance check.",
                details={"reference": "H3.2", "Tr_kN_m": tr, "Tc_kN_m": tc,
                         "Tr_over_Tc": tr / tc, "alternative": "Qualified H1/G checks required",
                         "component": "Pu+Mux+Muy+V+Tu"})

        axial = _available_axial_strength(case, section)
        flex_x = _available_flexural_strength(case, section, "x")
        flex_y = _available_flexural_strength(case, section, "y")
        shear = _available_shear_strength(case, section)

        pu_ratio = _safe_ratio(demand=case.loads.Pu, capacity=float(axial["available_kN"]), ratio_name="Pr/Pc")
        mx_ratio = _safe_ratio(demand=case.loads.Mux, capacity=float(flex_x["available_kN_m"]), ratio_name="Mrx/Mcx")
        my_ratio = _safe_ratio(demand=case.loads.Muy, capacity=float(flex_y["available_kN_m"]), ratio_name="Mry/Mcy")
        vr_ratio = float(shear["ratio"])
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
                        "shear_governing_axis": shear["governing_axis"],
                        "shear_ratios_by_axis": shear["axis_ratios"],
                        "normative_equation": "ANSI/AISC 360-22 H3-6",
                        "Pr_over_Pc": pu_ratio,
                        "Mrx_over_Mcx": mx_ratio,
                        "Mry_over_Mcy": my_ratio,
                        "normal_ratio_sum": normal_ratio,
                        "shear_torsion_ratio_sum": shear_torsion_ratio,
                        "interaction_expression": "(Pr/Pc + Mrx/Mcx + Mry/Mcy) + (max(Vrx/Vcx,Vry/Vcy) + Tr/Tc)^2",
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
