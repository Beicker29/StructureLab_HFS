from ...tracing import traced_rule, emit_step, quantity
from ..design_methods import require_case_method
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


def _axis_demand(case: SteelCase, axis: str) -> float:
    return _major_demand(case) if axis == "x" else _minor_demand(case)


def _axis_m_label(axis: str) -> str:
    return "Mx" if axis == "x" else "My"


def _flexure_name(clause: str, limit_state: str, context: str) -> str:
    return f"Flexure {clause} - {limit_state} ({context})"


def _build_flexure_result(*, case: SteelCase, name: str, clause: str, demand: float, evaluation: dict, inputs: dict) -> CheckResult:
    require_case_method(case, chapter="F")
    mn_nmm = evaluation["Mn_Nmm"]
    capacity = flexure_calc.available_flexural_strength(mn_nmm, case.design_method.value)
    return CheckResult.from_values(
        unit='kN-m',
        name=name,
        clause=clause,
        demand=demand,
        capacity=capacity,
        details={
            "memory": {
                "chapter_f_selection": clause,
                "inputs": inputs,
                "limit_states": evaluation["limit_states"],
                "intermediate": evaluation["intermediate"],
                "design_factor": {"design_method": case.design_method.value, "phi_b": flexure_calc.PHI_B_LRFD, "capacity_expression": "phi_b*Mn"},
                "Mn_Nmm": mn_nmm,
                "capacity_kn_m": capacity,
            }
        },
    )


def _build_flexure_result_from_mn(
    *,
    case: SteelCase,
    name: str,
    clause: str,
    demand: float,
    mn_nmm: float,
    base_evaluation: dict,
    inputs: dict,
    limit_state_label: str,
) -> CheckResult:
    emit_step(producer=__name__+":_build_flexure_result_from_mn", limit_state=limit_state_label,
        branch="reported_limit_state", reference="Chapter F; see canonical rule metadata", equation=None,
        expression=None, outputs=(quantity("selected_Mn", mn_nmm, "N-mm", "calling rule's selected limit-state value"),),
        unknowns=("Selected output is observed; nominal equation, subbranch and axis are not inferred from clause text.",))
    evaluation = {
        "Mn_Nmm": mn_nmm,
        "limit_states": base_evaluation["limit_states"],
        "intermediate": {**base_evaluation["intermediate"], "reported_limit_state": limit_state_label},
    }
    return _build_flexure_result(case=case, name=name, clause=clause, demand=demand, evaluation=evaluation, inputs=inputs)


def _common_major_inputs(case: SteelCase, section: Section, demand: float) -> dict:
    return {
        "Fy_mpa": case.material.Fy,
        "E_mpa": case.material.E,
        "Cb": case.factors.Cb,
        "Lb_mm": case.lengths.Lb,
        "Mux_kn_m": demand,
        "Zx_mm3": section.zx,
        "Sx_mm3": section.sx,
    }


class FlexureF2YieldRule:
    """F2-1: yielding for compact I-shapes/channels in major-axis flexure."""

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F2-1", "Yielding", "Major Axis"), "F2-1")
        evaluation = flexure_calc.evaluate_f2(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F2-1", "Yielding", "Major Axis"),
            clause="F2-1",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["yielding_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs=_common_major_inputs(case, section, demand),
            limit_state_label="yielding",
        )


class FlexureF2LtbRule:
    """F2-2: lateral-torsional buckling for compact I-shapes/channels in major-axis flexure."""

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F2-2", "Lateral-Torsional Buckling", "Major Axis"), "F2-2")
        evaluation = flexure_calc.evaluate_f2(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F2-2", "Lateral-Torsional Buckling", "Major Axis"),
            clause="F2-2",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["ltb_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs=_common_major_inputs(case, section, demand),
            limit_state_label="lateral_torsional_buckling",
        )


class FlexureF3YieldRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F3-1", "Yielding", "Major Axis"), "F3-1")
        evaluation = flexure_calc.evaluate_f3(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F3-1", "Yielding", "Major Axis"),
            clause="F3-1",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["yielding_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs=_common_major_inputs(case, section, demand),
            limit_state_label="yielding",
        )


class FlexureF3LtbRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F3-2", "Lateral-Torsional Buckling", "Major Axis"), "F3-2")
        evaluation = flexure_calc.evaluate_f3(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F3-2", "Lateral-Torsional Buckling", "Major Axis"),
            clause="F3-2",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["ltb_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs=_common_major_inputs(case, section, demand),
            limit_state_label="lateral_torsional_buckling",
        )


class FlexureF3FlbRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F3-3", "Flange Local Buckling", "Major Axis"), "F3-3")
        evaluation = flexure_calc.evaluate_f3(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F3-3", "Flange Local Buckling", "Major Axis"),
            clause="F3-3",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["flange_local_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={
                **_common_major_inputs(case, section, demand),
                "bf_2tf_ratio": section.bf_2tf_ratio,
                "h_tw_ratio": section.h_tw_ratio,
            },
            limit_state_label="flange_local_buckling",
        )


class FlexureF4CompressionYieldRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F4-1", "Compression Flange Yielding", "Major Axis"), "F4-1")
        evaluation = flexure_calc.evaluate_f4_conservative(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F4-1", "Compression Flange Yielding", "Major Axis"),
            clause="F4-1",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["compression_flange_yielding_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs=_common_major_inputs(case, section, demand),
            limit_state_label="compression_flange_yielding",
        )


class FlexureF4LtbRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F4-2", "Lateral-Torsional Buckling", "Major Axis"), "F4-2")
        evaluation = flexure_calc.evaluate_f4_conservative(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F4-2", "Lateral-Torsional Buckling", "Major Axis"),
            clause="F4-2",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["lateral_torsional_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs=_common_major_inputs(case, section, demand),
            limit_state_label="lateral_torsional_buckling",
        )


class FlexureF4FlbRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F4-3", "Compression Flange Local Buckling", "Major Axis"), "F4-3")
        evaluation = flexure_calc.evaluate_f4_conservative(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F4-3", "Compression Flange Local Buckling", "Major Axis"),
            clause="F4-3",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["compression_flange_local_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={**_common_major_inputs(case, section, demand), "bf_2tf_ratio": section.bf_2tf_ratio},
            limit_state_label="compression_flange_local_buckling",
        )


class FlexureF4TensionYieldRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F4-4", "Tension Flange Yielding", "Major Axis"), "F4-4")
        evaluation = flexure_calc.evaluate_f4_conservative(case, section)
        # Conservative placeholder in current doubly-symmetric implementation.
        mn_tfy = evaluation["limit_states"]["compression_flange_yielding_Mn_Nmm"]
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F4-4", "Tension Flange Yielding", "Major Axis"),
            clause="F4-4",
            demand=demand,
            mn_nmm=mn_tfy,
            base_evaluation=evaluation,
            inputs=_common_major_inputs(case, section, demand),
            limit_state_label="tension_flange_yielding_conservative",
        )


class FlexureF5CompressionYieldRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F5-1", "Compression Flange Yielding", "Major Axis"), "F5-1")
        evaluation = flexure_calc.evaluate_f5(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F5-1", "Compression Flange Yielding", "Major Axis"),
            clause="F5-1",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["compression_flange_yielding_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs=_common_major_inputs(case, section, demand),
            limit_state_label="compression_flange_yielding",
        )


class FlexureF5LtbRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F5-2", "Lateral-Torsional Buckling", "Major Axis"), "F5-2")
        evaluation = flexure_calc.evaluate_f5(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F5-2", "Lateral-Torsional Buckling", "Major Axis"),
            clause="F5-2",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["lateral_torsional_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs=_common_major_inputs(case, section, demand),
            limit_state_label="lateral_torsional_buckling",
        )


class FlexureF5FlbRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F5-3", "Compression Flange Local Buckling", "Major Axis"), "F5-3")
        evaluation = flexure_calc.evaluate_f5(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F5-3", "Compression Flange Local Buckling", "Major Axis"),
            clause="F5-3",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["compression_flange_local_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={**_common_major_inputs(case, section, demand), "bf_2tf_ratio": section.bf_2tf_ratio},
            limit_state_label="compression_flange_local_buckling",
        )


class FlexureF5TensionYieldRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _major_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F5-4", "Tension Flange Yielding", "Major Axis"), "F5-4")
        evaluation = flexure_calc.evaluate_f5(case, section)
        mn_tfy = evaluation["limit_states"]["compression_flange_yielding_Mn_Nmm"]
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F5-4", "Tension Flange Yielding", "Major Axis"),
            clause="F5-4",
            demand=demand,
            mn_nmm=mn_tfy,
            base_evaluation=evaluation,
            inputs=_common_major_inputs(case, section, demand),
            limit_state_label="tension_flange_yielding_conservative",
        )


class FlexureF6YieldRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _minor_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F6-1", "Yielding", "Minor Axis"), "F6-1")
        evaluation = flexure_calc.evaluate_f6(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F6-1", "Yielding", "Minor Axis"),
            clause="F6-1",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["yielding_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Muy_kn_m": demand,
                "Zy_mm3": section.zy,
                "Sy_mm3": section.sy,
            },
            limit_state_label="yielding",
        )


class FlexureF6FlbRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand = _minor_demand(case)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F6-2", "Flange Local Buckling", "Minor Axis"), "F6-2")
        evaluation = flexure_calc.evaluate_f6(case, section)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F6-2", "Flange Local Buckling", "Minor Axis"),
            clause="F6-2",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["flange_local_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Muy_kn_m": demand,
                "bf_2tf_ratio": section.bf_2tf_ratio,
            },
            limit_state_label="flange_local_buckling",
        )


class FlexureF7YieldRule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        axis = self.axis
        demand = _axis_demand(case, axis)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F7-1", "Yielding", f"Rectangular HSS {_axis_m_label(axis)}"), "F7-1")
        evaluation = flexure_calc.evaluate_f7(case, section, axis=axis)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F7-1", "Yielding", f"Rectangular HSS {_axis_m_label(axis)}"),
            clause="F7-1",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["yielding_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={"axis": axis, "Fy_mpa": case.material.Fy, "E_mpa": case.material.E, "Mux_kn_m": _major_demand(case), "Muy_kn_m": _minor_demand(case)},
            limit_state_label="yielding",
        )


class FlexureF7YieldMxRule(FlexureF7YieldRule):
    axis = "x"


class FlexureF7YieldMyRule(FlexureF7YieldRule):
    axis = "y"


class FlexureF7FlangeRule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        axis = self.axis
        demand = _axis_demand(case, axis)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F7-2", "Flange Local Buckling", f"Rectangular HSS {_axis_m_label(axis)}"), "F7-2")
        evaluation = flexure_calc.evaluate_f7(case, section, axis=axis)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F7-2", "Flange Local Buckling", f"Rectangular HSS {_axis_m_label(axis)}"),
            clause="F7-2",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["flange_local_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={"axis": axis, "b_tdes_ratio": section.b_tdes_ratio, "h_tdes_ratio": section.h_tdes_ratio},
            limit_state_label="flange_local_buckling",
        )


class FlexureF7FlangeMxRule(FlexureF7FlangeRule):
    axis = "x"


class FlexureF7FlangeMyRule(FlexureF7FlangeRule):
    axis = "y"


class FlexureF7WebRule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        axis = self.axis
        demand = _axis_demand(case, axis)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F7-3", "Web Local Buckling", f"Rectangular HSS {_axis_m_label(axis)}"), "F7-3")
        evaluation = flexure_calc.evaluate_f7(case, section, axis=axis)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F7-3", "Web Local Buckling", f"Rectangular HSS {_axis_m_label(axis)}"),
            clause="F7-3",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["web_local_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={"axis": axis, "b_tdes_ratio": section.b_tdes_ratio, "h_tdes_ratio": section.h_tdes_ratio},
            limit_state_label="web_local_buckling",
        )


class FlexureF7WebMxRule(FlexureF7WebRule):
    axis = "x"


class FlexureF7WebMyRule(FlexureF7WebRule):
    axis = "y"


class FlexureF7LtbRule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        axis = self.axis
        demand = _axis_demand(case, axis)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F7-4", "Lateral-Torsional Buckling", f"Rectangular HSS {_axis_m_label(axis)}"), "F7-4")
        evaluation = flexure_calc.evaluate_f7(case, section, axis=axis)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F7-4", "Lateral-Torsional Buckling", f"Rectangular HSS {_axis_m_label(axis)}"),
            clause="F7-4",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["lateral_torsional_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={"axis": axis, "Cb": case.factors.Cb, "Lb_mm": case.lengths.Lb},
            limit_state_label="lateral_torsional_buckling",
        )


class FlexureF7LtbMxRule(FlexureF7LtbRule):
    axis = "x"


class FlexureF7LtbMyRule(FlexureF7LtbRule):
    axis = "y"


class FlexureF8YieldRule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        axis = self.axis
        demand = _axis_demand(case, axis)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F8-1", "Yielding", f"Circular HSS {_axis_m_label(axis)}"), "F8-1")
        evaluation = flexure_calc.evaluate_f8(case, section, axis=axis)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F8-1", "Yielding", f"Circular HSS {_axis_m_label(axis)}"),
            clause="F8-1",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["yielding_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={"axis": axis, "Fy_mpa": case.material.Fy, "E_mpa": case.material.E},
            limit_state_label="yielding",
        )


class FlexureF8YieldMxRule(FlexureF8YieldRule):
    axis = "x"


class FlexureF8YieldMyRule(FlexureF8YieldRule):
    axis = "y"


class FlexureF8LocalBucklingRule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        axis = self.axis
        demand = _axis_demand(case, axis)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F8-2", "Local Buckling", f"Circular HSS {_axis_m_label(axis)}"), "F8-2")
        evaluation = flexure_calc.evaluate_f8(case, section, axis=axis)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F8-2", "Local Buckling", f"Circular HSS {_axis_m_label(axis)}"),
            clause="F8-2",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["local_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={"axis": axis, "D_t_ratio": section.d_t_ratio},
            limit_state_label="local_buckling",
        )


class FlexureF8LocalBucklingMxRule(FlexureF8LocalBucklingRule):
    axis = "x"


class FlexureF8LocalBucklingMyRule(FlexureF8LocalBucklingRule):
    axis = "y"


class FlexureF10YieldRule:
    axis = "x"

    @staticmethod
    def _resolve_connection(case: SteelCase):
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
        return axis, restraint

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand_axis = self.axis
        demand = _axis_demand(case, demand_axis)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F10-1", "Yielding", f"Single Angle {_axis_m_label(demand_axis)}"), "F10-1")
        angle_axis, restraint = self._resolve_connection(case)
        evaluation = flexure_calc.evaluate_f10(case, section, axis=angle_axis)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F10-1", "Yielding", f"Single Angle {_axis_m_label(demand_axis)}"),
            clause="F10-1",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["yielding_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={"demand_axis": demand_axis, "angle_axis": angle_axis, "restraint": restraint.value},
            limit_state_label="yielding",
        )


class FlexureF10YieldMxRule(FlexureF10YieldRule):
    axis = "x"


class FlexureF10YieldMyRule(FlexureF10YieldRule):
    axis = "y"


class FlexureF10LtbRule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand_axis = self.axis
        demand = _axis_demand(case, demand_axis)
        if demand <= 0.0:
            return _nominal_pass(
                _flexure_name("F10-2", "Lateral-Torsional Buckling", f"Single Angle {_axis_m_label(demand_axis)}"),
                "F10-2",
            )
        angle_axis, restraint = FlexureF10YieldRule._resolve_connection(case)
        evaluation = flexure_calc.evaluate_f10(case, section, axis=angle_axis)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F10-2", "Lateral-Torsional Buckling", f"Single Angle {_axis_m_label(demand_axis)}"),
            clause="F10-2",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["lateral_torsional_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={
                "demand_axis": demand_axis,
                "angle_axis": angle_axis,
                "restraint": restraint.value,
                "Cb": case.factors.Cb,
                "Lb_mm": case.lengths.Lb,
            },
            limit_state_label="lateral_torsional_buckling",
        )


class FlexureF10LtbMxRule(FlexureF10LtbRule):
    axis = "x"


class FlexureF10LtbMyRule(FlexureF10LtbRule):
    axis = "y"


class FlexureF10LegBucklingRule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        demand_axis = self.axis
        demand = _axis_demand(case, demand_axis)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F10-3", "Leg Local Buckling", f"Single Angle {_axis_m_label(demand_axis)}"), "F10-3")
        angle_axis, _ = FlexureF10YieldRule._resolve_connection(case)
        evaluation = flexure_calc.evaluate_f10(case, section, axis=angle_axis)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F10-3", "Leg Local Buckling", f"Single Angle {_axis_m_label(demand_axis)}"),
            clause="F10-3",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["leg_local_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={"demand_axis": demand_axis, "angle_axis": angle_axis, "lambda_leg_b_t": section.b_t_ratio},
            limit_state_label="leg_local_buckling",
        )


class FlexureF10LegBucklingMxRule(FlexureF10LegBucklingRule):
    axis = "x"


class FlexureF10LegBucklingMyRule(FlexureF10LegBucklingRule):
    axis = "y"


class FlexureF11YieldRule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        axis = self.axis
        demand = _axis_demand(case, axis)
        if demand <= 0.0:
            return _nominal_pass(_flexure_name("F11-1", "Yielding", f"Solid Bar/Round {_axis_m_label(axis)}"), "F11-1")
        evaluation = flexure_calc.evaluate_f11(case, section, axis=axis)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F11-1", "Yielding", f"Solid Bar/Round {_axis_m_label(axis)}"),
            clause="F11-1",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["yielding_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={"axis": axis, "section_type": section.type, "Fy_mpa": case.material.Fy},
            limit_state_label="yielding",
        )


class FlexureF11YieldMxRule(FlexureF11YieldRule):
    axis = "x"


class FlexureF11YieldMyRule(FlexureF11YieldRule):
    axis = "y"


class FlexureF11LtbRule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="F")
        axis = self.axis
        demand = _axis_demand(case, axis)
        if demand <= 0.0:
            return _nominal_pass(
                _flexure_name("F11-2", "Lateral-Torsional Buckling", f"Solid Bar/Round {_axis_m_label(axis)}"),
                "F11-2",
            )
        evaluation = flexure_calc.evaluate_f11(case, section, axis=axis)
        return _build_flexure_result_from_mn(
            case=case,
            name=_flexure_name("F11-2", "Lateral-Torsional Buckling", f"Solid Bar/Round {_axis_m_label(axis)}"),
            clause="F11-2",
            demand=demand,
            mn_nmm=evaluation["limit_states"]["lateral_torsional_buckling_Mn_Nmm"],
            base_evaluation=evaluation,
            inputs={"axis": axis, "section_type": section.type, "Cb": case.factors.Cb, "Lb_mm": case.lengths.Lb},
            limit_state_label="lateral_torsional_buckling",
        )


class FlexureF11LtbMxRule(FlexureF11LtbRule):
    axis = "x"


class FlexureF11LtbMyRule(FlexureF11LtbRule):
    axis = "y"


# Backward compatibility aliases used by some tests/imports.
class FlexureRule(FlexureF2YieldRule):
    pass


class FlexureF3Rule(FlexureF3FlbRule):
    pass


class FlexureF4Rule(FlexureF4FlbRule):
    pass


class FlexureF5Rule(FlexureF5FlbRule):
    pass


class FlexureF6Rule(FlexureF6FlbRule):
    pass


class FlexureF7Rule(FlexureF7FlangeMxRule):
    pass


class FlexureF8Rule(FlexureF8LocalBucklingMxRule):
    pass


class FlexureF10Rule(FlexureF10LegBucklingMxRule):
    pass


class FlexureF11Rule(FlexureF11LtbMxRule):
    pass
