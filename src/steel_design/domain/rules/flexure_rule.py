from ...codes.aisc_360_22 import flexure_calc
from ...models import CheckResult, CheckStatus, SteelCase
from ...sections.models import Section
from ..errors import ValidationError


def _nominal_pass(name: str, clause: str) -> CheckResult:
    return CheckResult(
        name=name,
        clause=clause,
        demand=0.0,
        capacity=0.0,
        dcr=0.0,
        status=CheckStatus.PASS,
    )


def _major_demand(case: SteelCase) -> float:
    return abs(case.loads.Mux)


def _minor_demand(case: SteelCase) -> float:
    return abs(case.loads.Muy)


def _any_flexure_demand(case: SteelCase) -> tuple[str, float]:
    if _major_demand(case) > 0.0:
        return "x", _major_demand(case)
    return "y", _minor_demand(case)


def _build_flexure_result(*, case: SteelCase, name: str, clause: str, demand: float, evaluation: dict, inputs: dict) -> CheckResult:
    mn_nmm = evaluation["Mn_Nmm"]
    capacity = flexure_calc.available_flexural_strength_lrfd(mn_nmm)
    dcr = demand / capacity if capacity > 0.0 else float("inf")
    return CheckResult(
        name=name,
        clause=clause,
        demand=round(demand, 3),
        capacity=round(capacity, 3),
        dcr=round(dcr, 3),
        status=CheckStatus.PASS if dcr <= 1.0 else CheckStatus.FAIL,
        details={
            "memory": {
                "chapter_f_selection": clause,
                "inputs": inputs,
                "limit_states": evaluation["limit_states"],
                "intermediate": evaluation["intermediate"],
                "design_factor": {"design_method": "LRFD", "phi_b": 0.90, "capacity_expression": "phi_b*Mn"},
                "Mn_Nmm": mn_nmm,
                "capacity_kn_m": capacity,
            }
        },
    )


class FlexureRule:
    """F2: Doubly symmetric compact I-shaped members and channels (major axis)."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass("Flexure Major F2", "F2")
        evaluation = flexure_calc.evaluate_f2(case, section)
        return _build_flexure_result(
            case=case,
            name="Flexure Major F2",
            clause="F2",
            demand=demand,
            evaluation=evaluation,
            inputs={
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Cb": case.factors.Cb,
                "Lb_mm": case.lengths.Lb,
                "Mux_kn_m": demand,
                "Zx_mm3": section.zx,
                "Sx_mm3": section.sx,
            },
        )


class FlexureF3Rule:
    """F3: Doubly symmetric I-shapes, compact web with noncompact/slender flange."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass("Flexure Major F3", "F3")
        evaluation = flexure_calc.evaluate_f3(case, section)
        return _build_flexure_result(
            case=case,
            name="Flexure Major F3",
            clause="F3",
            demand=demand,
            evaluation=evaluation,
            inputs={
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Cb": case.factors.Cb,
                "Lb_mm": case.lengths.Lb,
                "Mux_kn_m": demand,
                "bf_2tf_ratio": section.bf_2tf_ratio,
                "h_tw_ratio": section.h_tw_ratio,
            },
        )


class FlexureF4Rule:
    """F4 implemented conservatively via F5 branch (User Note in F4)."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass("Flexure Major F4", "F4")
        evaluation = flexure_calc.evaluate_f4_conservative(case, section)
        return _build_flexure_result(
            case=case,
            name="Flexure Major F4",
            clause="F4",
            demand=demand,
            evaluation=evaluation,
            inputs={
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Cb": case.factors.Cb,
                "Lb_mm": case.lengths.Lb,
                "Mux_kn_m": demand,
                "bf_2tf_ratio": section.bf_2tf_ratio,
                "h_tw_ratio": section.h_tw_ratio,
            },
        )


class FlexureF5Rule:
    """F5: I-shaped members with slender webs."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass("Flexure Major F5", "F5")
        evaluation = flexure_calc.evaluate_f5(case, section)
        return _build_flexure_result(
            case=case,
            name="Flexure Major F5",
            clause="F5",
            demand=demand,
            evaluation=evaluation,
            inputs={
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Cb": case.factors.Cb,
                "Lb_mm": case.lengths.Lb,
                "Mux_kn_m": demand,
                "bf_2tf_ratio": section.bf_2tf_ratio,
                "h_tw_ratio": section.h_tw_ratio,
            },
        )


class FlexureF6Rule:
    """F6: I-shaped members and channels bent about minor axis."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = _minor_demand(case)
        if demand <= 0.0:
            return _nominal_pass("Flexure Minor F6", "F6")
        evaluation = flexure_calc.evaluate_f6(case, section)
        return _build_flexure_result(
            case=case,
            name="Flexure Minor F6",
            clause="F6",
            demand=demand,
            evaluation=evaluation,
            inputs={
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Muy_kn_m": demand,
                "Zy_mm3": section.zy,
                "Sy_mm3": section.sy,
                "bf_2tf_ratio": section.bf_2tf_ratio,
            },
        )


class FlexureF7Rule:
    """F7: Square/rectangular HSS and box sections."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        axis, demand = _any_flexure_demand(case)
        if demand <= 0.0:
            return _nominal_pass("Flexure HSS Rectangular F7", "F7")
        evaluation = flexure_calc.evaluate_f7(case, section, axis=axis)
        return _build_flexure_result(
            case=case,
            name="Flexure HSS Rectangular F7",
            clause="F7",
            demand=demand,
            evaluation=evaluation,
            inputs={
                "axis": axis,
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Cb": case.factors.Cb,
                "Lb_mm": case.lengths.Lb,
                "Mux_kn_m": _major_demand(case),
                "Muy_kn_m": _minor_demand(case),
                "b_tdes_ratio": section.b_tdes_ratio,
                "h_tdes_ratio": section.h_tdes_ratio,
            },
        )


class FlexureF8Rule:
    """F8: Round HSS."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        axis, demand = _any_flexure_demand(case)
        if demand <= 0.0:
            return _nominal_pass("Flexure HSS Circular F8", "F8")
        evaluation = flexure_calc.evaluate_f8(case, section, axis=axis)
        return _build_flexure_result(
            case=case,
            name="Flexure HSS Circular F8",
            clause="F8",
            demand=demand,
            evaluation=evaluation,
            inputs={
                "axis": axis,
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Mux_kn_m": _major_demand(case),
                "Muy_kn_m": _minor_demand(case),
                "D_t_ratio": section.d_t_ratio,
            },
        )


class FlexureF10Rule:
    """F10: Single angles."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        _, demand = _any_flexure_demand(case)
        if demand <= 0.0:
            return _nominal_pass("Flexure Single Angle F10", "F10")
        axis = case.connection.angle_flexure_axis.value if case.connection.angle_flexure_axis else None
        restraint = case.connection.angle_ltb_restraint
        if axis is None:
            raise ValidationError(
                "connection.angle_flexure_axis is required for single-angle flexure (F10).",
                details={"required_field": "connection.angle_flexure_axis"},
            )
        if restraint is None:
            raise ValidationError(
                "connection.angle_ltb_restraint is required for single-angle flexure (F10).",
                details={"required_field": "connection.angle_ltb_restraint"},
            )
        if axis == "geometric_axis" and case.connection.angle_max_tension_location is None:
            raise ValidationError(
                "connection.angle_max_tension_location is required for geometric-axis bending of single angles (F10).",
                details={"required_field": "connection.angle_max_tension_location"},
            )
        evaluation = flexure_calc.evaluate_f10(case, section, axis=axis)
        return _build_flexure_result(
            case=case,
            name="Flexure Single Angle F10",
            clause="F10",
            demand=demand,
            evaluation=evaluation,
            inputs={
                "axis": axis,
                "restraint": restraint.value,
                "max_tension_location": (
                    case.connection.angle_max_tension_location.value
                    if case.connection.angle_max_tension_location
                    else None
                ),
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Cb": case.factors.Cb,
                "Lb_mm": case.lengths.Lb,
                "lambda_leg_b_t": section.b_t_ratio,
            },
        )


class FlexureF11Rule:
    """F11: Rectangular bars and rounds (custom solid sections)."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        axis, demand = _any_flexure_demand(case)
        if demand <= 0.0:
            return _nominal_pass("Flexure Solid Bar/Round F11", "F11")
        evaluation = flexure_calc.evaluate_f11(case, section, axis=axis)
        return _build_flexure_result(
            case=case,
            name="Flexure Solid Bar/Round F11",
            clause="F11",
            demand=demand,
            evaluation=evaluation,
            inputs={
                "axis": axis,
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Cb": case.factors.Cb,
                "Lb_mm": case.lengths.Lb,
                "Mux_kn_m": _major_demand(case),
                "Muy_kn_m": _minor_demand(case),
                "section_type": section.type,
                "h_mm": section.h,
                "b_mm": section.b,
                "d_mm": section.od,
            },
        )
