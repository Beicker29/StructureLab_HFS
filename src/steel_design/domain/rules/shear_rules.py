import math

from ...tracing import traced_rule
from ..design_methods import require_case_method
from ...codes.aisc_360_22 import shear_calc
from ...models import CheckResult, CheckStatus, SteelCase
from ...sections.models import Section
from ..actions import shear_demand as _shear_demand, shear_trace
from ..errors import RuleNotImplementedError
from ..evaluators.hss_shear import evaluate_hss_shear, require_section_values


def _nominal_pass(name: str, clause: str) -> CheckResult:
    return CheckResult(
        name=name,
        clause=clause,
        demand=0.0,
        capacity=0.0,
        dcr=0.0,
        status=CheckStatus.PASS,
    )


def _positive(value: float | None) -> float:
    return float(value) if isinstance(value, (int, float)) and value > 0.0 else 0.0


def _axis_v_label(axis: str) -> str:
    # Suffix identifies the bending plane; the force acts along the other axis.
    return "local y (Vux/Vu, Mux plane)" if axis == "x" else "local x (Vuy, Muy plane)"


def _shear_name(clause: str, limit_state: str, context: str) -> str:
    return f"Shear {clause} - {limit_state} ({context})"


def _build_result(
    *,
    name: str,
    clause: str,
    demand_kn: float,
    capacity_kn: float,
    details: dict,
) -> CheckResult:
    return CheckResult.from_values(
        unit='kN',
        name=name,
        clause=clause,
        demand=demand_kn,
        capacity=capacity_kn,
        details=details,
    )


def _aw_for_g2(section: Section) -> float:
    tw = _positive(section.tw)
    depth = _positive(section.d)
    if depth <= 0.0:
        h = _positive(section.h)
        tf = _positive(section.tf)
        if h > 0.0 and tf > 0.0:
            depth = h + 2.0 * tf
        elif h > 0.0:
            depth = h
    return depth * tw


def _h_over_tw_for_g2(section: Section) -> float:
    ratio = _positive(section.h_tw_ratio)
    if ratio > 0.0:
        return ratio
    h = _positive(section.h)
    tw = _positive(section.tw)
    if h > 0.0 and tw > 0.0:
        return h / tw
    d = _positive(section.d)
    return d / tw if d > 0.0 and tw > 0.0 else 0.0


def _g2_design_factors(case: SteelCase, profile: str, h_over_tw: float) -> dict:
    fy = case.material.Fy
    e = case.material.E
    compact_limit = 2.24 * math.sqrt(e / fy) if min(e, fy) > 0.0 else 0.0
    special = profile == "W" and h_over_tw > 0.0 and h_over_tw <= compact_limit
    if special:
        return {
            "phi_v": 1.0,
            "omega_v": 1.50,
            "branch": "G2-2",
            "compact_limit": compact_limit,
        }
    return {
        "phi_v": 0.90,
        "omega_v": 1.67,
        "branch": "G1_default",
        "compact_limit": compact_limit,
    }


class ShearG2VxRule:
    """G2: I-shaped members and channels (major-axis web shear)."""

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case)
        demand = _shear_demand(case, "x")
        if demand <= 0.0:
            return _nominal_pass(_shear_name("G2-1", "Web Shear", "Major Axis Vy"), "G2-1")

        fy = case.material.Fy
        e = case.material.E
        kv = 5.34
        h_over_tw = _h_over_tw_for_g2(section)
        cv_data = shear_calc.calculate_cv1_g2_1(h_over_tw=h_over_tw, fy_mpa=fy, e_mpa=e, kv=kv)
        aw = _aw_for_g2(section)
        vn_n = shear_calc.calculate_nominal_shear_strength(fy_mpa=fy, aw_mm2=aw, cv=float(cv_data["Cv1"]))
        profile = section.type.upper()
        factors = _g2_design_factors(case, profile, h_over_tw)
        capacity = shear_calc.calculate_available_shear_strength(
            vn_n=vn_n,
            design_method=case.design_method.value,
            phi_v=float(factors["phi_v"]),
            omega_v=float(factors["omega_v"]),
        )
        return _build_result(
            name=_shear_name("G2-1", "Web Shear", "Major Axis Vy"),
            clause="G2-1",
            demand_kn=demand,
            capacity_kn=capacity,
            details={
                "memory": {
                    "clause": "G2",
                    "inputs": {
                        "Fy_mpa": fy,
                        "E_mpa": e,
                        "Vux_kn": demand,
                        **shear_trace(case, "x"),
                        "tw_mm": section.tw,
                        "d_mm": section.d,
                        "h_over_tw": h_over_tw,
                        "Aw_mm2": aw,
                        "kv": kv,
                    },
                    "intermediate": {
                        "Cv1": cv_data["Cv1"],
                        "Cv1_branch": cv_data["branch"],
                        "Cv1_limit_g2_3": cv_data["limit_g2_3"],
                        "g2_1a_limit_2_24_sqrtE_over_Fy": factors["compact_limit"],
                        "design_branch": factors["branch"],
                        "Vn_N": vn_n,
                        "Vn_kN": vn_n / 1000.0,
                    },
                    "design_factor": {
                        "design_method": case.design_method.value,
                        "phi_v": factors["phi_v"],
                        "omega_v": factors["omega_v"],
                        "capacity_expression": "phi_v*Vn (LRFD) or Vn/omega_v (ASD)",
                    },
                    "capacity_kn": capacity,
                }
            },
        )


class ShearG3Rule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case)
        if _shear_demand(case, self.axis) <= 0:
            return _nominal_pass("G3 no demand", "G3-1")
        raise RuleNotImplementedError(
            "G3 needs the actual resisting leg and force resolved along it; one b/t cannot establish both directions or double-angle sharing.",
            details={"reference": "G3-1", "section": section.name,
                     "profile_type": section.type, **shear_trace(case, self.axis)})


class ShearG3VxRule(ShearG3Rule):
    axis = "x"


class ShearG3VyRule(ShearG3Rule):
    axis = "y"


def _hss_shear_check(case, section, axis, profile):
    if section.type.upper() != profile:
        raise RuleNotImplementedError("Shear rule/profile mismatch.", details={"expected": profile, "section": section.type})
    demand = _shear_demand(case, axis)
    clause = "G4-1" if profile == "RECTANGULAR_HSS" else "G5-1"
    if demand <= 0:
        return _nominal_pass(_shear_name(clause, "HSS Shear", _axis_v_label(axis)), clause)
    evaluation = evaluate_hss_shear(case, section, axis)
    return _build_result(
        name=_shear_name(clause, "HSS Shear", _axis_v_label(axis)), clause=clause,
        demand_kn=demand, capacity_kn=evaluation["capacity_kN"],
        details={"memory": {"clause": clause[:2], "inputs": evaluation["inputs"],
                            "intermediate": evaluation["intermediate"],
                            "design_factor": evaluation["design_factor"],
                            "capacity_kn": evaluation["capacity_kN"]}})


class ShearG4Rule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case)
        return _hss_shear_check(case, section, self.axis, "RECTANGULAR_HSS")


class ShearG4VxRule(ShearG4Rule):
    axis = "x"


class ShearG4VyRule(ShearG4Rule):
    axis = "y"


class ShearG5Rule:
    axis = "x"

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case)
        return _hss_shear_check(case, section, self.axis, "CIRCULAR_HSS")


class ShearG5VxRule(ShearG5Rule):
    axis = "x"


class ShearG5VyRule(ShearG5Rule):
    axis = "y"


class ShearG6VyRule:
    """G6: W minor bending-plane shear (Vuy is a local-x force)."""

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case)
        demand = _shear_demand(case, "y")
        if demand <= 0.0:
            return _nominal_pass(_shear_name("G6-1", "Minor-Axis Shear", "Minor Axis Vx"), "G6-1")

        if case.loads.Tu or section.type.upper() != "W":
            raise RuleNotImplementedError(
                "G6 requires no torsion and a justified distribution to each flange; channel distribution is not represented.",
                details={"reference": "G6-1", "section": section.name, **shear_trace(case, "y")})
        fy = case.material.Fy
        e = case.material.E
        bf, tf = require_section_values(section, ("bf", "tf"), "G6-1")
        h_over_tw = _positive(section.bf_2tf_ratio)
        if h_over_tw <= 0.0 and min(bf, tf) > 0.0:
            h_over_tw = bf / (2.0 * tf)
        elements = 2.0  # two equal flanges in the declared symmetric W domain
        kv = 1.2
        cv_data = shear_calc.calculate_cv2_g2_2(h_over_tw=h_over_tw, fy_mpa=fy, e_mpa=e, kv=kv)
        aw = elements * bf * tf
        vn_n = shear_calc.calculate_nominal_shear_strength(fy_mpa=fy, aw_mm2=aw, cv=float(cv_data["Cv2"]))
        capacity = shear_calc.calculate_available_shear_strength(
            vn_n=vn_n,
            design_method=case.design_method.value,
            phi_v=0.90,
            omega_v=1.67,
        )
        return _build_result(
            name=_shear_name("G6-1", "Minor-Axis Shear", "Minor Axis Vx"),
            clause="G6-1",
            demand_kn=demand,
            capacity_kn=capacity,
            details={
                "memory": {
                    "clause": "G6",
                    "inputs": {
                        "Fy_mpa": fy,
                        "E_mpa": e,
                        "Vuy_kn": demand,
                        **shear_trace(case, "y"),
                        "bf_mm": bf,
                        "tf_mm": tf,
                        "shear_elements": elements,
                        "bf_over_effective_tf": h_over_tw,
                        "kv": kv,
                    },
                    "intermediate": {
                        "Cv2": cv_data["Cv2"],
                        "Cv2_branch": cv_data["branch"],
                        "Cv2_limit_g2_9": cv_data["limit_g2_9"],
                        "Cv2_limit_g2_10": cv_data["limit_g2_10"],
                        "Aw_mm2": aw,
                        "Vn_N": vn_n,
                        "Vn_kN": vn_n / 1000.0,
                    },
                    "design_factor": {
                        "design_method": case.design_method.value,
                        "phi_v": 0.90,
                        "omega_v": 1.67,
                        "capacity_expression": "phi_v*Vn (LRFD) or Vn/omega_v (ASD)",
                    },
                    "capacity_kn": capacity,
                }
            },
        )
