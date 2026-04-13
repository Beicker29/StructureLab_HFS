import math

from ...codes.aisc_360_22 import shear_calc
from ...models import CheckResult, CheckStatus, SteelCase
from ...sections.models import Section


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


def _has_directional_shear(case: SteelCase) -> bool:
    return abs(case.loads.Vux) > 0.0 or abs(case.loads.Vuy) > 0.0


def _shear_demand(case: SteelCase, axis: str) -> float:
    if _has_directional_shear(case):
        return abs(case.loads.Vux if axis == "x" else case.loads.Vuy)
    return abs(case.loads.Vu) if axis == "x" else 0.0


def _axis_v_label(axis: str) -> str:
    # Project convention: legacy axis naming in outputs is swapped with respect to
    # internal axis routing. Keep calculations unchanged and only adjust labels.
    return "Vy" if axis == "x" else "Vx"


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
    dcr = demand_kn / capacity_kn if capacity_kn > 0.0 else float("inf")
    return CheckResult(
        name=name,
        clause=clause,
        demand=round(demand_kn, 3),
        capacity=round(capacity_kn, 3),
        dcr=round(dcr, 3),
        status=CheckStatus.PASS if dcr <= 1.0 else CheckStatus.FAIL,
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


def _h_for_rect_hss(section: Section, axis: str) -> float:
    if axis == "x":
        return _positive(section.h) or _positive(section.b)
    return _positive(section.b) or _positive(section.h)


def _round_hss_diameter(section: Section) -> float:
    diameter = _positive(section.od) or _positive(section.d)
    if diameter > 0.0:
        return diameter
    ratio = _positive(section.d_t_ratio)
    t = _positive(section.tdes) or _positive(section.t)
    return ratio * t if ratio > 0.0 and t > 0.0 else 0.0


def _round_hss_thickness(section: Section, diameter: float) -> float:
    t = _positive(section.tdes) or _positive(section.t)
    if t > 0.0:
        return t
    ratio = _positive(section.d_t_ratio)
    return diameter / ratio if diameter > 0.0 and ratio > 0.0 else 0.0


class ShearG2VxRule:
    """G2: I-shaped members and channels (major-axis web shear)."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
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

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        axis = self.axis
        demand = _shear_demand(case, axis)
        if demand <= 0.0:
            return _nominal_pass(_shear_name("G3-1", "Leg/Stem Shear", f"Single Angle/Tee {_axis_v_label(axis)}"), "G3-1")

        fy = case.material.Fy
        e = case.material.E
        b = _positive(section.b)
        t = _positive(section.t)
        ratio = _positive(section.b_t_ratio)
        h_over_tw = ratio if ratio > 0.0 else (b / t if min(b, t) > 0.0 else 0.0)
        kv = 1.2
        cv_data = shear_calc.calculate_cv2_g2_2(h_over_tw=h_over_tw, fy_mpa=fy, e_mpa=e, kv=kv)
        area_bt = b * t
        vn_n = shear_calc.calculate_nominal_shear_strength(fy_mpa=fy, aw_mm2=area_bt, cv=float(cv_data["Cv2"]))
        capacity = shear_calc.calculate_available_shear_strength(
            vn_n=vn_n,
            design_method=case.design_method.value,
            phi_v=0.90,
            omega_v=1.67,
        )
        return _build_result(
            name=_shear_name("G3-1", "Leg/Stem Shear", f"Single Angle/Tee {_axis_v_label(axis)}"),
            clause="G3-1",
            demand_kn=demand,
            capacity_kn=capacity,
            details={
                "memory": {
                    "clause": "G3",
                    "inputs": {
                        "Fy_mpa": fy,
                        "E_mpa": e,
                        f"Vu{axis}_kn": demand,
                        "b_mm": b,
                        "t_mm": t,
                        "b_over_t": h_over_tw,
                        "kv": kv,
                    },
                    "intermediate": {
                        "Cv2": cv_data["Cv2"],
                        "Cv2_branch": cv_data["branch"],
                        "Cv2_limit_g2_9": cv_data["limit_g2_9"],
                        "Cv2_limit_g2_10": cv_data["limit_g2_10"],
                        "bt_mm2": area_bt,
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


class ShearG3VxRule(ShearG3Rule):
    axis = "x"


class ShearG3VyRule(ShearG3Rule):
    axis = "y"


class ShearG4Rule:
    axis = "x"

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        axis = self.axis
        demand = _shear_demand(case, axis)
        if demand <= 0.0:
            return _nominal_pass(_shear_name("G4-1", "Wall Shear", f"Rectangular HSS {_axis_v_label(axis)}"), "G4-1")

        fy = case.material.Fy
        e = case.material.E
        t = _positive(section.tdes)
        h = _h_for_rect_hss(section, axis)
        h_over_t = h / t if min(h, t) > 0.0 else 0.0
        aw = 2.0 * h * t if min(h, t) > 0.0 else 0.0
        kv = 5.0
        cv_data = shear_calc.calculate_cv2_g2_2(h_over_tw=h_over_t, fy_mpa=fy, e_mpa=e, kv=kv)
        vn_n = shear_calc.calculate_nominal_shear_strength(fy_mpa=fy, aw_mm2=aw, cv=float(cv_data["Cv2"]))
        capacity = shear_calc.calculate_available_shear_strength(
            vn_n=vn_n,
            design_method=case.design_method.value,
            phi_v=0.90,
            omega_v=1.67,
        )
        return _build_result(
            name=_shear_name("G4-1", "Wall Shear", f"Rectangular HSS {_axis_v_label(axis)}"),
            clause="G4-1",
            demand_kn=demand,
            capacity_kn=capacity,
            details={
                "memory": {
                    "clause": "G4",
                    "inputs": {
                        "Fy_mpa": fy,
                        "E_mpa": e,
                        "axis": axis,
                        f"Vu{axis}_kn": demand,
                        "h_catalog_mm": section.h,
                        "b_catalog_mm": section.b,
                        "h_resisting_mm": h,
                        "tdes_mm": section.tdes,
                        "t_used_mm": t,
                        "h_over_t": h_over_t,
                        "Aw_mm2": aw,
                        "kv": kv,
                    },
                    "intermediate": {
                        "h_over_t_expression": "h_resisting/tdes",
                        "h_over_t_substitution": f"{h} / {t}" if min(h, t) > 0.0 else None,
                        "Aw_expression": "Aw = 2*h_resisting*tdes",
                        "Aw_substitution": f"2*{h}*{t}" if min(h, t) > 0.0 else None,
                        "Cv2": cv_data["Cv2"],
                        "Cv2_branch": cv_data["branch"],
                        "Cv2_limit_g2_9": cv_data["limit_g2_9"],
                        "Cv2_limit_g2_10": cv_data["limit_g2_10"],
                        "Cv2_reference": "G2-9/G2-10/G2-11 with kv=5 and h/t = h_resisting/tdes",
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


class ShearG4VxRule(ShearG4Rule):
    axis = "x"


class ShearG4VyRule(ShearG4Rule):
    axis = "y"


class ShearG5Rule:
    axis = "x"

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        axis = self.axis
        demand = _shear_demand(case, axis)
        if demand <= 0.0:
            return _nominal_pass(_shear_name("G5-1", "Round HSS Shear", f"Circular HSS {_axis_v_label(axis)}"), "G5-1")

        fy = case.material.Fy
        e = case.material.E
        ag = _positive(section.area)
        diameter = _round_hss_diameter(section)
        thickness = _round_hss_thickness(section, diameter)
        lv = case.lengths.Lx if axis == "x" else case.lengths.Ly
        fcr_data = shear_calc.calculate_round_hss_fcr(
            e_mpa=e,
            fy_mpa=fy,
            lv_mm=lv,
            diameter_mm=diameter,
            thickness_mm=thickness,
        )
        vn_n = shear_calc.calculate_round_hss_nominal_shear_strength(
            fcr_mpa=float(fcr_data["Fcr_mpa"]),
            ag_mm2=ag,
        )
        capacity = shear_calc.calculate_available_shear_strength(
            vn_n=vn_n,
            design_method=case.design_method.value,
            phi_v=0.90,
            omega_v=1.67,
        )
        return _build_result(
            name=_shear_name("G5-1", "Round HSS Shear", f"Circular HSS {_axis_v_label(axis)}"),
            clause="G5-1",
            demand_kn=demand,
            capacity_kn=capacity,
            details={
                "memory": {
                    "clause": "G5",
                    "inputs": {
                        "Fy_mpa": fy,
                        "E_mpa": e,
                        f"Vu{axis}_kn": demand,
                        "Ag_mm2": ag,
                        "D_mm": diameter,
                        "t_mm": thickness,
                        "Lv_mm": lv,
                    },
                    "intermediate": {
                        "Fcr_mpa": fcr_data["Fcr_mpa"],
                        "Fcr_G5_2a_mpa": fcr_data["fcr_g5_2a_mpa"],
                        "Fcr_G5_2b_mpa": fcr_data["fcr_g5_2b_mpa"],
                        "Fcr_branch": fcr_data["branch"],
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


class ShearG5VxRule(ShearG5Rule):
    axis = "x"


class ShearG5VyRule(ShearG5Rule):
    axis = "y"


class ShearG6VyRule:
    """G6: minor-axis shear for W/Channel families (Vy)."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = _shear_demand(case, "y")
        if demand <= 0.0:
            return _nominal_pass(_shear_name("G6-1", "Minor-Axis Shear", "Minor Axis Vx"), "G6-1")

        fy = case.material.Fy
        e = case.material.E
        bf = _positive(section.bf)
        tf = _positive(section.tf)
        profile = section.type.upper()
        if profile == "CHANNEL":
            h_over_tw = _positive(section.b_t_ratio)
            if h_over_tw <= 0.0 and min(bf, tf) > 0.0:
                h_over_tw = bf / tf
            elements = 1.0
        else:
            h_over_tw = _positive(section.bf_2tf_ratio)
            if h_over_tw <= 0.0 and min(bf, tf) > 0.0:
                h_over_tw = bf / (2.0 * tf)
            elements = 2.0
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
