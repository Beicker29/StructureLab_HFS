import math

from ...codes.aisc_360_22 import axial_calc
from ...models import CheckResult, CheckStatus, SteelCase
from ...sections.models import Section


def _compression_demand(case: SteelCase) -> float:
    return max(0.0, case.loads.Pu)


def _pass_result(name: str, clause: str) -> CheckResult:
    return CheckResult(name=name, clause=clause, demand=0.0, capacity=0.0, dcr=0.0, status=CheckStatus.PASS)


def _result(name: str, clause: str, demand: float, capacity: float, details: dict | None = None) -> CheckResult:
    return CheckResult.from_values(
        unit='kN',
        name=name,
        clause=clause,
        demand=demand,
        capacity=capacity,
        details=details,
    )


def _design_factor(method: str) -> dict:
    method_upper = method.upper()
    if method_upper == "LRFD":
        return {"design_method": method_upper, "phi": 0.90, "omega": None, "capacity_expression": "phi*Pn"}
    return {"design_method": method_upper, "phi": None, "omega": 1.67, "capacity_expression": "Pn/omega"}


def _safe_klr(K: float, L: float, r: float | None) -> float | None:
    if r is None or r <= 0.0 or K <= 0.0 or L <= 0.0:
        return None
    return (K * L) / r


def _fcr_branch_info(Fy: float, Fe: float) -> dict:
    if Fy <= 0.0 or Fe <= 0.0:
        return {"fy_over_fe": None, "branch": "invalid"}
    ratio = Fy / Fe
    branch = "inelastic_E3_2" if ratio <= 2.25 else "elastic_E3_3"
    return {"fy_over_fe": ratio, "branch": branch}


def _governing_fe_e3(case: SteelCase, section: Section) -> float:
    fe_x = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Kx, case.lengths.Lx, section.rx or 0.0)
    fe_y = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Ky, case.lengths.Ly, section.ry or 0.0)
    candidates = [value for value in (fe_x, fe_y) if value > 0.0]
    return min(candidates) if candidates else 0.0


def _e3_components(case: SteelCase, section: Section) -> dict:
    klr_x = _safe_klr(case.factors.Kx, case.lengths.Lx, section.rx)
    klr_y = _safe_klr(case.factors.Ky, case.lengths.Ly, section.ry)
    fe_x = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Kx, case.lengths.Lx, section.rx or 0.0)
    fe_y = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Ky, case.lengths.Ly, section.ry or 0.0)
    axis = "x"
    fe = fe_x
    if (fe_y > 0.0 and fe_x <= 0.0) or (fe_y > 0.0 and fe_y <= fe_x):
        axis = "y"
        fe = fe_y
    if fe <= 0.0:
        axis = "none"
    return {
        "klr_x": klr_x,
        "klr_y": klr_y,
        "fe_x_mpa": fe_x,
        "fe_y_mpa": fe_y,
        "fe_governing_mpa": fe,
        "governing_axis": axis,
    }


def _governing_fe_e4(case: SteelCase, section: Section) -> float:
    ro = section.ro
    if ro is None or ro <= 0.0:
        ro = axial_calc.calculate_ro_for_double_symmetric(section.area, section.ix or 0.0, section.iy or 0.0)

    fe_z = axial_calc.calculate_Fe_torsional(
        case.material.E,
        axial_calc.NORMATIVE_G_MPA,
        section.j or 0.0,
        section.cw or 0.0,
        case.factors.Kz,
        case.lengths.Lz,
        section.area,
        ro,
    )
    fe_y = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Ky, case.lengths.Ly, section.ry or 0.0)

    profile_type = section.type.upper()
    if profile_type in {"CHANNEL", "DOUBLE_ANGLE"}:
        return axial_calc.calculate_Fe_flexural_torsional(fe_y, fe_z, section.H or 1.0)

    if profile_type in {"RECTANGULAR_HSS", "CIRCULAR_HSS", "W"}:
        # E4 for these families is evaluated with torsional elastic buckling stress Fez.
        return fe_z if fe_z > 0.0 else 0.0

    return fe_z


def _e4_components(case: SteelCase, section: Section) -> dict:
    ro_raw = section.ro
    ro_source = "catalog"
    ro_value = ro_raw
    if ro_value is None or ro_value <= 0.0:
        ro_value = axial_calc.calculate_ro_for_double_symmetric(section.area, section.ix or 0.0, section.iy or 0.0)
        ro_source = "derived_from_ix_iy_ag"

    fe_z = axial_calc.calculate_Fe_torsional(
        case.material.E,
        axial_calc.NORMATIVE_G_MPA,
        section.j or 0.0,
        section.cw or 0.0,
        case.factors.Kz,
        case.lengths.Lz,
        section.area,
        ro_value,
    )
    fe_x = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Kx, case.lengths.Lx, section.rx or 0.0)
    fe_y = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Ky, case.lengths.Ly, section.ry or 0.0)
    klr_x = _safe_klr(case.factors.Kx, case.lengths.Lx, section.rx)
    klr_y = _safe_klr(case.factors.Ky, case.lengths.Ly, section.ry)
    klr_z = _safe_klr(case.factors.Kz, case.lengths.Lz, ro_value)

    kz_lz = case.factors.Kz * case.lengths.Lz
    warping_term = None
    stvenant_term = None
    torsional_stiffness = None
    torsional_denominator = None
    if kz_lz > 0.0 and section.cw and section.cw > 0.0:
        warping_term = ((math.pi**2 * case.material.E * section.cw) / (kz_lz**2))
    if section.j and section.j > 0.0:
        stvenant_term = axial_calc.NORMATIVE_G_MPA * section.j
    if warping_term is not None and stvenant_term is not None:
        torsional_stiffness = warping_term + stvenant_term
    if section.area > 0.0 and ro_value and ro_value > 0.0:
        torsional_denominator = section.area * (ro_value**2)

    profile_type = section.type.upper()
    flexural_torsional_terms = None
    if profile_type in {"CHANNEL", "DOUBLE_ANGLE"}:
        fe_governing = axial_calc.calculate_Fe_flexural_torsional(fe_y, fe_z, section.H or 1.0)
        mode = "flexural_torsional"
        sum_fe = fe_y + fe_z
        radicand = None
        if sum_fe > 0.0:
            h_val = section.H if section.H and section.H > 0.0 else 1.0
            radicand = 1.0 - ((4.0 * fe_y * fe_z * h_val) / (sum_fe**2))
        flexural_torsional_terms = {"sum_fe": sum_fe, "radicand_before_clamp": radicand, "H": section.H or 1.0}
    else:
        fe_governing = fe_z if fe_z > 0.0 else 0.0
        mode = "torsional"

    return {
        "ro_mm": ro_value,
        "ro_source": ro_source,
        "klr_x": klr_x,
        "klr_y": klr_y,
        "klr_z": klr_z,
        "fe_x_mpa": fe_x,
        "fe_y_mpa": fe_y,
        "fe_z_mpa": fe_z,
        "fe_governing_mpa": fe_governing,
        "e4_mode": mode,
        "warping_term_n": warping_term,
        "stvenant_term_n": stvenant_term,
        "torsional_stiffness_n": torsional_stiffness,
        "torsional_denominator_mm4": torsional_denominator,
        "flexural_torsional_terms": flexural_torsional_terms,
    }


def _slenderness_values(section: Section) -> dict:
    return {
        "bf_2tf_ratio": section.bf_2tf_ratio,
        "b_t_ratio": section.b_t_ratio,
        "b_tdes_ratio": section.b_tdes_ratio,
        "h_tw_ratio": section.h_tw_ratio,
        "h_tdes_ratio": section.h_tdes_ratio,
        "d_t_ratio": section.d_t_ratio,
    }


def _compression_details(case: SteelCase, section: Section) -> dict:
    return {
        "element_classification": axial_calc.classify_compression_elements(
            profile_type=section.type,
            slenderness=_slenderness_values(section),
            E=case.material.E,
            Fy=case.material.Fy,
        )
    }


class AxialE3Rule:
    """Flexural buckling of members without slender elements (E3)."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = _compression_demand(case)
        if demand <= 0.0:
            return _pass_result("Axial Compression E3", "E3")

        components = _e3_components(case, section)
        fe = components["fe_governing_mpa"]
        fcr = axial_calc.calculate_Fcr(case.material.Fy, fe)
        pn = axial_calc.calculate_Pn(fcr, section.area)
        capacity = axial_calc.calculate_available_compressive_strength(pn, case.design_method)
        details = _compression_details(case, section)
        details["memory"] = {
            "clause": "E3",
            "inputs": {
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Ag_mm2": section.area,
                "Kx": case.factors.Kx,
                "Ky": case.factors.Ky,
                "Lx_mm": case.lengths.Lx,
                "Ly_mm": case.lengths.Ly,
                "rx_mm": section.rx,
                "ry_mm": section.ry,
            },
            "intermediate": {
                "KL_over_r_x": components["klr_x"],
                "KL_over_r_y": components["klr_y"],
                "governing_axis": components["governing_axis"],
                "Fex_mpa": components["fe_x_mpa"],
                "Fey_mpa": components["fe_y_mpa"],
                "Fe_mpa": components["fe_governing_mpa"],
                **_fcr_branch_info(case.material.Fy, components["fe_governing_mpa"]),
                "fcr_mpa": fcr,
                "pn_n": pn,
                "pn_kn": pn / 1000.0,
                "be_mm": None,
                "be_note": "Not required in current E3 implementation.",
            },
            "design_factor": _design_factor(case.design_method),
            "capacity_kn": capacity,
        }
        return _result(
            "Axial Compression (Flexural Buckling)",
            "E3-1",
            demand,
            capacity,
            details=details,
        )


class AxialE4Rule:
    """Torsional and flexural-torsional buckling (E4)."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = _compression_demand(case)
        if demand <= 0.0:
            return _pass_result("Axial Compression E4", "E4")

        components = _e4_components(case, section)
        fe = components["fe_governing_mpa"]
        fcr = axial_calc.calculate_Fcr(case.material.Fy, fe)
        pn = axial_calc.calculate_Pn(fcr, section.area)
        capacity = axial_calc.calculate_available_compressive_strength(pn, case.design_method)
        details = _compression_details(case, section)
        details["memory"] = {
            "clause": "E4",
            "inputs": {
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "G_mpa": axial_calc.NORMATIVE_G_MPA,
                "Ag_mm2": section.area,
                "Kz": case.factors.Kz,
                "Lz_mm": case.lengths.Lz,
                "Ky": case.factors.Ky,
                "Ly_mm": case.lengths.Ly,
                "ry_mm": section.ry,
                "J_mm4": section.j,
                "Cw_mm6": section.cw,
                "H": section.H,
                "xa_mm": case.factors.xa,
                "ya_mm": case.factors.ya,
            },
            "intermediate": {
                "KL_over_r_x": components["klr_x"],
                "KL_over_r_y": components["klr_y"],
                "KL_over_r_z": components["klr_z"],
                "ro_mm": components["ro_mm"],
                "ro_source": components["ro_source"],
                "Fex_mpa": components["fe_x_mpa"],
                "Fey_mpa": components["fe_y_mpa"],
                "Fez_mpa": components["fe_z_mpa"],
                "Fe_mpa": components["fe_governing_mpa"],
                "e4_mode": components["e4_mode"],
                "warping_term_n": components["warping_term_n"],
                "stvenant_term_n": components["stvenant_term_n"],
                "torsional_stiffness_n": components["torsional_stiffness_n"],
                "torsional_denominator_mm4": components["torsional_denominator_mm4"],
                "flexural_torsional_terms": components["flexural_torsional_terms"],
                **_fcr_branch_info(case.material.Fy, components["fe_governing_mpa"]),
                "fcr_mpa": fcr,
                "pn_n": pn,
                "pn_kn": pn / 1000.0,
                "be_mm": None,
                "be_note": "be is not explicitly modeled in current E4 implementation.",
            },
            "design_factor": _design_factor(case.design_method),
            "capacity_kn": capacity,
        }
        return _result("Axial Compression (Torsional/Flexural-Torsional)", "E4-1", demand, capacity, details=details)


class AxialE5Rule:
    """Single-angle compression members (E5)."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = _compression_demand(case)
        if demand <= 0.0:
            return _pass_result("Axial Compression E5", "E5")

        mode = (case.connection.angle_compression_mode.value if case.connection.angle_compression_mode else "both_legs")
        slender_x = (case.factors.Kx * case.lengths.Lx) / (section.rx or 1.0)
        slender_y = (case.factors.Ky * case.lengths.Ly) / (section.ry or 1.0)
        slender_governing = max(slender_x, slender_y)
        effective_slenderness = axial_calc.calculate_e5_effective_slenderness(slender_governing, mode)
        fe = (3.141592653589793**2 * case.material.E) / (effective_slenderness**2) if effective_slenderness > 0 else 0.0
        fcr = axial_calc.calculate_Fcr(case.material.Fy, fe)
        pn = axial_calc.calculate_Pn(fcr, section.area)
        capacity = axial_calc.calculate_available_compressive_strength(pn, case.design_method)
        clause = "E5-1a" if mode == "one_leg" else "E5-1b"
        details = _compression_details(case, section)
        details["memory"] = {
            "clause": "E5",
            "inputs": {
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Ag_mm2": section.area,
                "mode": mode,
                "Kx": case.factors.Kx,
                "Ky": case.factors.Ky,
                "Lx_mm": case.lengths.Lx,
                "Ly_mm": case.lengths.Ly,
                "rx_mm": section.rx,
                "ry_mm": section.ry,
            },
            "intermediate": {
                "slenderness_x": slender_x,
                "slenderness_y": slender_y,
                "governing_slenderness": slender_governing,
                "effective_slenderness": effective_slenderness,
                "effective_slenderness_expression": "72 + 0.75*(KL/r) for one_leg; KL/r for both_legs",
                "Fe_mpa": fe,
                **_fcr_branch_info(case.material.Fy, fe),
                "fcr_mpa": fcr,
                "pn_n": pn,
                "pn_kn": pn / 1000.0,
                "be_mm": None,
                "be_note": "be is not explicitly modeled in current E5 implementation.",
            },
            "design_factor": _design_factor(case.design_method),
            "capacity_kn": capacity,
        }
        return _result("Axial Compression (Single Angle)", clause, demand, capacity, details=details)


class AxialE7Rule:
    """Members with slender elements (E7)."""

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = _compression_demand(case)
        if demand <= 0.0:
            return _pass_result("Axial Compression E7", "E7")

        e3_components = _e3_components(case, section)
        e4_components = _e4_components(case, section)
        fe_e3 = e3_components["fe_governing_mpa"]
        fe_e4 = e4_components["fe_governing_mpa"]
        fe_candidates = [value for value in (fe_e3, fe_e4) if value > 0.0]
        fe = min(fe_candidates) if fe_candidates else 0.0

        q = axial_calc.calculate_q_factor(section.type, _slenderness_values(section), case.material.E, case.material.Fy)
        fcr = axial_calc.calculate_Fcr_slender(case.material.Fy, fe, q)
        pn = axial_calc.calculate_Pn(fcr, section.area)
        capacity = axial_calc.calculate_available_compressive_strength(pn, case.design_method)
        details = _compression_details(case, section)
        details["memory"] = {
            "clause": "E7",
            "inputs": {
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Ag_mm2": section.area,
                "slenderness_ratios": _slenderness_values(section),
            },
            "intermediate": {
                "KL_over_r_x": e3_components["klr_x"],
                "KL_over_r_y": e3_components["klr_y"],
                "Fex_mpa": e3_components["fe_x_mpa"],
                "Fey_mpa": e3_components["fe_y_mpa"],
                "Fez_mpa": e4_components["fe_z_mpa"],
                "Fe_mpa": fe,
                "fe_e3_mpa": fe_e3,
                "fe_e4_mpa": fe_e4,
                "q_factor": q,
                "qFy_mpa": q * case.material.Fy,
                **_fcr_branch_info(q * case.material.Fy, fe),
                "fcr_mpa": fcr,
                "pn_n": pn,
                "pn_kn": pn / 1000.0,
                "be_mm": None,
                "be_note": "be is not explicitly modeled in current E7 implementation.",
            },
            "design_factor": _design_factor(case.design_method),
            "capacity_kn": capacity,
        }
        return _result("Axial Compression (Slender Elements)", "E7-1", demand, capacity, details=details)
