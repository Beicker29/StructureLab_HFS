from __future__ import annotations

import math
from ...tracing import traced_rule, emit_step, quantity
from ..design_methods import require_case_method
from typing import Dict, Tuple

from ...codes.aisc_360_22 import axial_calc, composite_calc, shear_calc
from ...models import CheckResult, CheckStatus, CompositeI5Method, SteelCase
from ...sections.models import Section
from ..errors import RuleNotImplementedError, ValidationError


def _positive(value: float | None) -> float:
    return float(value) if isinstance(value, (int, float)) and value > 0.0 else 0.0


def _nominal_pass(name: str, clause: str) -> CheckResult:
    return CheckResult(name=name, clause=clause, demand=0.0, capacity=0.0, dcr=0.0, status=CheckStatus.PASS)


def _build_result(*, name: str, clause: str, demand: float, capacity: float, details: dict, unit: str) -> CheckResult:
    return CheckResult.from_values(
        unit=unit,
        name=name,
        clause=clause,
        demand=demand,
        capacity=capacity,
        details=details,
    )


def _ensure_supported_method(case: SteelCase, section: Section) -> str:
    require_case_method(case, chapter="I")
    method = case.composite.nominal_strength_method.value
    if method in {"STRAIN_COMPAT", "EFFECTIVE_STRAIN"}:
        raise RuleNotImplementedError(
            "Selected composite nominal strength method is not implemented in current scope.",
            details={
                "section": section.name,
                "profile_type": section.type,
                "role": case.composite.role.value,
                "nominal_strength_method": method,
                "supported_methods": ["PLASTIC", "ELASTIC"],
            },
        )
    if method not in {"PLASTIC", "ELASTIC"}:
        raise RuleNotImplementedError(
            "Composite nominal strength method is not implemented.",
            details={"nominal_strength_method": method},
        )
    return method


def _composite_role(case: SteelCase) -> str:
    if case.composite is None:
        raise ValidationError("Composite checks require case.composite.")
    return case.composite.role.value


def _bar_totals(case: SteelCase) -> Dict[str, float]:
    bars = case.composite.reinforcement.longitudinal_bars if case.composite else []
    asr = 0.0
    isr_x = 0.0
    isr_y = 0.0
    fy_weighted = 0.0
    for bar in bars:
        area = composite_calc.reinforcement_area_mm2(count=bar.count, db_mm=bar.db)
        inertia = composite_calc.reinforcement_inertia_contribution_mm4(area_mm2=area, x_mm=bar.x, y_mm=bar.y)
        asr += area
        isr_x += inertia["Ix_mm4"]
        isr_y += inertia["Iy_mm4"]
        fy_weighted += area * bar.fy
    fysr = fy_weighted / asr if asr > 0.0 else 0.0
    return {"Asr_mm2": asr, "Isr_x_mm4": isr_x, "Isr_y_mm4": isr_y, "Fysr_mpa": fysr}


def _bar_plastic_modulus(case: SteelCase, *, axis: str) -> float:
    bars = case.composite.reinforcement.longitudinal_bars if case.composite else []
    z = 0.0
    for bar in bars:
        area = composite_calc.reinforcement_area_mm2(count=bar.count, db_mm=bar.db)
        lever = abs(bar.y) if axis == "x" else abs(bar.x)
        z += area * lever
    return z


def _filled_outside_rect_dimensions(section: Section) -> Tuple[float, float]:
    t = _positive(section.tdes) or _positive(section.t)
    b_flat = _positive(section.b)
    h_flat = _positive(section.h)
    if min(t, b_flat, h_flat) <= 0.0:
        return 0.0, 0.0
    return b_flat + 3.0 * t, h_flat + 3.0 * t


def _round_dimensions(section: Section) -> Tuple[float, float]:
    d = _positive(section.od) or _positive(section.d)
    t = _positive(section.tdes) or _positive(section.t)
    return d, t


def _composite_section_components(case: SteelCase, section: Section) -> Dict[str, float]:
    role = _composite_role(case)
    bars = _bar_totals(case)
    as_mm2 = _positive(section.area)
    asr_mm2 = bars["Asr_mm2"]
    is_x = _positive(section.ix)
    is_y = _positive(section.iy)

    if role == "ENCASED_MEMBER":
        b = _positive(case.composite.geometry.B)
        h = _positive(case.composite.geometry.H)
        ag = b * h
        ac = max(ag - as_mm2 - asr_mm2, 0.0)
        ig_x_total = b * (h**3) / 12.0 if min(b, h) > 0.0 else 0.0
        ig_y_total = h * (b**3) / 12.0 if min(b, h) > 0.0 else 0.0
        ic_x = max(ig_x_total - is_x - bars["Isr_x_mm4"], 0.0)
        ic_y = max(ig_y_total - is_y - bars["Isr_y_mm4"], 0.0)
        return {
            "As_mm2": as_mm2,
            "Asr_mm2": asr_mm2,
            "Ac_mm2": ac,
            "Ag_mm2": ag,
            "Is_x_mm4": is_x,
            "Is_y_mm4": is_y,
            "Isr_x_mm4": bars["Isr_x_mm4"],
            "Isr_y_mm4": bars["Isr_y_mm4"],
            "Ic_x_mm4": ic_x,
            "Ic_y_mm4": ic_y,
            "Fysr_mpa": bars["Fysr_mpa"],
            "B_mm": b,
            "H_mm": h,
        }

    if role == "FILLED_MEMBER":
        profile = section.type.upper()
        if profile == "RECTANGULAR_HSS":
            b_out, h_out = _filled_outside_rect_dimensions(section)
            ag = b_out * h_out if min(b_out, h_out) > 0.0 else 0.0
            ig_x_total = b_out * (h_out**3) / 12.0 if min(b_out, h_out) > 0.0 else 0.0
            ig_y_total = h_out * (b_out**3) / 12.0 if min(b_out, h_out) > 0.0 else 0.0
            ac = max(ag - as_mm2 - asr_mm2, 0.0)
            ic_x = max(ig_x_total - is_x - bars["Isr_x_mm4"], 0.0)
            ic_y = max(ig_y_total - is_y - bars["Isr_y_mm4"], 0.0)
            return {
                "As_mm2": as_mm2,
                "Asr_mm2": asr_mm2,
                "Ac_mm2": ac,
                "Ag_mm2": ag,
                "Is_x_mm4": is_x,
                "Is_y_mm4": is_y,
                "Isr_x_mm4": bars["Isr_x_mm4"],
                "Isr_y_mm4": bars["Isr_y_mm4"],
                "Ic_x_mm4": ic_x,
                "Ic_y_mm4": ic_y,
                "Fysr_mpa": bars["Fysr_mpa"],
                "B_out_mm": b_out,
                "H_out_mm": h_out,
            }
        if profile == "CIRCULAR_HSS":
            d_out, _ = _round_dimensions(section)
            ag = math.pi * (d_out**2) / 4.0 if d_out > 0.0 else 0.0
            ig_total = math.pi * (d_out**4) / 64.0 if d_out > 0.0 else 0.0
            ac = max(ag - as_mm2 - asr_mm2, 0.0)
            ic = max(ig_total - max(is_x, is_y) - max(bars["Isr_x_mm4"], bars["Isr_y_mm4"]), 0.0)
            return {
                "As_mm2": as_mm2,
                "Asr_mm2": asr_mm2,
                "Ac_mm2": ac,
                "Ag_mm2": ag,
                "Is_x_mm4": is_x,
                "Is_y_mm4": is_y,
                "Isr_x_mm4": bars["Isr_x_mm4"],
                "Isr_y_mm4": bars["Isr_y_mm4"],
                "Ic_x_mm4": ic,
                "Ic_y_mm4": ic,
                "Fysr_mpa": bars["Fysr_mpa"],
                "D_out_mm": d_out,
            }
        raise RuleNotImplementedError(
            "Filled composite scope supports only rectangular and round HSS in this iteration.",
            details={"section": section.name, "profile_type": section.type, "role": role},
        )

    if role == "COMPOSITE_BEAM":
        be = _positive(case.composite.geometry.slab_effective_width)
        ts = _positive(case.composite.geometry.slab_thickness)
        ac = be * ts if min(be, ts) > 0.0 else 0.0
        ic = be * (ts**3) / 12.0 if min(be, ts) > 0.0 else 0.0
        return {
            "As_mm2": as_mm2,
            "Asr_mm2": asr_mm2,
            "Ac_mm2": ac,
            "Ag_mm2": as_mm2 + asr_mm2 + ac,
            "Is_x_mm4": is_x,
            "Is_y_mm4": is_y,
            "Isr_x_mm4": bars["Isr_x_mm4"],
            "Isr_y_mm4": bars["Isr_y_mm4"],
            "Ic_x_mm4": ic,
            "Ic_y_mm4": ic,
            "Fysr_mpa": bars["Fysr_mpa"],
            "slab_effective_width_mm": be,
            "slab_thickness_mm": ts,
        }

    raise RuleNotImplementedError("Unsupported composite role.", details={"role": role})


def _effective_inertia_and_pe(
    case: SteelCase,
    section: Section,
    *,
    c_factor: float,
    ic_x: float,
    ic_y: float,
    is_x: float,
    is_y: float,
    isr_x: float,
    isr_y: float,
) -> Dict[str, float | str]:
    ec = composite_calc.concrete_modulus_ec_mpa(fc_mpa=case.composite.concrete.fc, wc_kg_m3=case.composite.concrete.wc)
    ei_x = (axial_calc.NORMATIVE_E_MPA * (is_x + isr_x)) + (c_factor * ec * ic_x)
    ei_y = (axial_calc.NORMATIVE_E_MPA * (is_y + isr_y)) + (c_factor * ec * ic_y)
    kx_lx = case.factors.Kx * case.lengths.Lx
    ky_ly = case.factors.Ky * case.lengths.Ly
    pe_x = (math.pi**2 * ei_x / (kx_lx**2)) if min(ei_x, kx_lx) > 0.0 else 0.0
    pe_y = (math.pi**2 * ei_y / (ky_ly**2)) if min(ei_y, ky_ly) > 0.0 else 0.0
    candidates = [("x", pe_x), ("y", pe_y)]
    candidates = [item for item in candidates if item[1] > 0.0]
    if not candidates:
        return {
            "Ec_mpa": ec,
            "EIx_eff_n_mm2": ei_x,
            "EIy_eff_n_mm2": ei_y,
            "Pe_n": 0.0,
            "Pe_axis": "none",
            "Pe_x_n": pe_x,
            "Pe_y_n": pe_y,
        }
    axis, pe = min(candidates, key=lambda item: item[1])
    return {"Ec_mpa": ec, "EIx_eff_n_mm2": ei_x, "EIy_eff_n_mm2": ei_y, "Pe_n": pe, "Pe_axis": axis, "Pe_x_n": pe_x, "Pe_y_n": pe_y}


def _bare_steel_compression_capacity_k_n(case: SteelCase, section: Section) -> float:
    require_case_method(case, chapter="I")
    fe_x = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Kx, case.lengths.Lx, _positive(section.rx))
    fe_y = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Ky, case.lengths.Ly, _positive(section.ry))
    fe_e3_candidates = [value for value in (fe_x, fe_y) if value > 0.0]
    fe_e3 = min(fe_e3_candidates) if fe_e3_candidates else 0.0
    fcr_e3 = axial_calc.calculate_Fcr(case.material.Fy, fe_e3)
    pn_e3 = axial_calc.calculate_Pn(fcr_e3, _positive(section.area))
    p_e3 = axial_calc.calculate_available_compressive_strength(pn_e3, case.design_method.value)

    ro = _positive(section.ro)
    if ro <= 0.0:
        ro = axial_calc.calculate_ro_for_double_symmetric(_positive(section.area), _positive(section.ix), _positive(section.iy))
    fe_e4 = axial_calc.calculate_Fe_torsional(
        case.material.E,
        axial_calc.NORMATIVE_G_MPA,
        _positive(section.j),
        _positive(section.cw),
        case.factors.Kz,
        case.lengths.Lz,
        _positive(section.area),
        ro,
    )
    fcr_e4 = axial_calc.calculate_Fcr(case.material.Fy, fe_e4)
    pn_e4 = axial_calc.calculate_Pn(fcr_e4, _positive(section.area))
    p_e4 = axial_calc.calculate_available_compressive_strength(pn_e4, case.design_method.value)

    classification = axial_calc.classify_compression_elements(
        profile_type=section.type,
        slenderness={
            "bf_2tf_ratio": section.bf_2tf_ratio,
            "b_t_ratio": section.b_t_ratio,
            "b_tdes_ratio": section.b_tdes_ratio,
            "h_tw_ratio": section.h_tw_ratio,
            "h_tdes_ratio": section.h_tdes_ratio,
            "d_t_ratio": section.d_t_ratio,
        },
        E=case.material.E,
        Fy=case.material.Fy,
    )
    p_e7 = 0.0
    if classification.get("is_slender"):
        q = axial_calc.calculate_q_factor(
            section.type,
            {
                "bf_2tf_ratio": section.bf_2tf_ratio,
                "b_t_ratio": section.b_t_ratio,
                "b_tdes_ratio": section.b_tdes_ratio,
                "h_tw_ratio": section.h_tw_ratio,
                "h_tdes_ratio": section.h_tdes_ratio,
                "d_t_ratio": section.d_t_ratio,
            },
            case.material.E,
            case.material.Fy,
        )
        fe_for_e7 = min([value for value in (fe_e3, fe_e4) if value > 0.0], default=0.0)
        fcr_e7 = axial_calc.calculate_Fcr_slender(case.material.Fy, fe_for_e7, q)
        pn_e7 = axial_calc.calculate_Pn(fcr_e7, _positive(section.area))
        p_e7 = axial_calc.calculate_available_compressive_strength(pn_e7, case.design_method.value)

    candidates = [value for value in (p_e3, p_e4, p_e7) if value > 0.0]
    return min(candidates) if candidates else 0.0


def _sum_anchor_qn(case: SteelCase, *, segment: str) -> Dict[str, object]:
    if case.composite is None:
        return {"sum_qn_n": 0.0, "groups": []}
    fc = case.composite.concrete.fc
    wc = case.composite.concrete.wc
    ec = composite_calc.concrete_modulus_ec_mpa(fc_mpa=fc, wc_kg_m3=wc)
    groups_out = []
    total = 0.0
    for group in case.composite.anchors.groups:
        if group.segment.value != segment:
            continue
        if group.type.value == "STUD":
            fu = _positive(group.Fu) if _positive(group.Fu) > 0.0 else case.material.Fu
            stud = composite_calc.stud_qn_i8_1_n(
                d_mm=group.d,
                fu_mpa=fu,
                fc_mpa=fc,
                ec_mpa=ec,
                rg=group.Rg or 1.0,
                rp=group.Rp or 0.75,
            )
            group_qn = stud["Qn_n"] * group.count
            total += group_qn
            groups_out.append(
                {
                    "type": "STUD",
                    "count": group.count,
                    "segment": group.segment.value,
                    "Qn_one_n": stud["Qn_n"],
                    "Qn_group_n": group_qn,
                    "Asa_mm2": stud["Asa_mm2"],
                    "Q_concrete_n": stud["Q_concrete_n"],
                    "Q_steel_n": stud["Q_steel_n"],
                    "Rg": group.Rg,
                    "Rp": group.Rp,
                }
            )
            continue
        qn_one = composite_calc.channel_qn_i8_2_n(
            la_mm=group.la,
            tf_mm=group.tf,
            tw_mm=group.tw,
            fc_mpa=fc,
            ec_mpa=ec,
        )
        group_qn = qn_one * group.count
        total += group_qn
        groups_out.append(
            {
                "type": "CHANNEL",
                "count": group.count,
                "segment": group.segment.value,
                "Qn_one_n": qn_one,
                "Qn_group_n": group_qn,
            }
        )
    return {"sum_qn_n": total, "groups": groups_out, "Ec_mpa": ec}


def _composite_beam_horizontal_shear(case: SteelCase, section: Section) -> Dict[str, float | list]:
    parts = _composite_section_components(case, section)
    as_mm2 = parts["As_mm2"]
    ac_mm2 = parts["Ac_mm2"]
    fc = case.composite.concrete.fc
    v_concrete = 0.85 * fc * ac_mm2 / 1000.0
    v_steel = case.material.Fy * as_mm2 / 1000.0
    v_required = min(v_concrete, v_steel)
    anchors = _sum_anchor_qn(case, segment="positive")
    v_anchor = anchors["sum_qn_n"] / 1000.0
    return {
        "V_required_kN": v_required,
        "V_concrete_kN": v_concrete,
        "V_steel_kN": v_steel,
        "V_anchor_kN": v_anchor,
        "anchor_groups": anchors["groups"],
        "Ac_effective_mm2": ac_mm2,
        "As_mm2": as_mm2,
    }


def _steel_shear_capacity_k_n(case: SteelCase, section: Section) -> Dict[str, float]:
    require_case_method(case, chapter="I")
    fy = case.material.Fy
    e = case.material.E
    profile = section.type.upper()
    if profile in {"W", "CHANNEL"}:
        d = _positive(section.d) or _positive(section.h)
        tw = _positive(section.tw)
        h_tw = d / tw if min(d, tw) > 0.0 else 0.0
        aw = d * tw if min(d, tw) > 0.0 else 0.0
        cv = shear_calc.calculate_cv1_g2_1(h_over_tw=h_tw, fy_mpa=fy, e_mpa=e, kv=5.0)
        vn = shear_calc.calculate_nominal_shear_strength(fy_mpa=fy, aw_mm2=aw, cv=float(cv["Cv1"]))
        phi_v_vn = shear_calc.calculate_available_shear_strength(vn_n=vn, design_method="LRFD", phi_v=0.9, omega_v=1.67)
        return {"Vn_n": vn, "phiVn_kN": phi_v_vn, "h_over_tw": h_tw, "Aw_mm2": aw, "Cv": float(cv["Cv1"]), "cv_branch": cv["branch"]}
    return {"Vn_n": 0.0, "phiVn_kN": 0.0, "h_over_tw": 0.0, "Aw_mm2": 0.0, "Cv": 0.0, "cv_branch": "unsupported"}


def _required_shear(case: SteelCase) -> float:
    if abs(case.loads.Vux) > 0.0 or abs(case.loads.Vuy) > 0.0:
        return max(abs(case.loads.Vux), abs(case.loads.Vuy))
    return abs(case.loads.Vu)


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


def _rect_equivalent_thickness_mm(*, as_mm2: float, b_out_mm: float, h_out_mm: float, t_guess_mm: float) -> float:
    as_mm2 = _positive(as_mm2)
    b_out_mm = _positive(b_out_mm)
    h_out_mm = _positive(h_out_mm)
    t_guess_mm = _positive(t_guess_mm)
    if min(as_mm2, b_out_mm, h_out_mm) <= 0.0:
        return 0.0
    t_max = 0.49 * min(b_out_mm, h_out_mm)
    if t_max <= 0.0:
        return 0.0

    def _area_shell(t: float) -> float:
        return (b_out_mm * h_out_mm) - ((b_out_mm - 2.0 * t) * (h_out_mm - 2.0 * t))

    target = as_mm2
    area_at_max = _area_shell(t_max)
    if area_at_max < target:
        return min(t_guess_mm if t_guess_mm > 0.0 else t_max, t_max)

    low = 0.0
    high = t_max
    for _ in range(80):
        mid = 0.5 * (low + high)
        if _area_shell(mid) >= target:
            high = mid
        else:
            low = mid
    return 0.5 * (low + high)


def _filled_strip_model(case: SteelCase, section: Section, *, axis: str, strips: int = 800) -> Dict[str, object]:
    profile = section.type.upper()
    as_mm2 = _positive(section.area)
    bars = case.composite.reinforcement.longitudinal_bars if case.composite else []
    bar_fibers = []
    for bar in bars:
        area = composite_calc.reinforcement_area_mm2(count=bar.count, db_mm=bar.db)
        coordinate = float(bar.y if axis == "x" else bar.x)
        bar_fibers.append({"A_mm2": area, "y_mm": coordinate, "fy_mpa": bar.fy})

    if profile == "RECTANGULAR_HSS":
        b_out, h_out = _filled_outside_rect_dimensions(section)
        t_guess = _positive(section.tdes) or _positive(section.t)
        t_eq = _rect_equivalent_thickness_mm(as_mm2=as_mm2, b_out_mm=b_out, h_out_mm=h_out, t_guess_mm=t_guess)
        b_in = max(b_out - 2.0 * t_eq, 0.0)
        h_in = max(h_out - 2.0 * t_eq, 0.0)
        if axis == "x":
            depth = h_out
            outer_width = b_out
            inner_depth = h_in
            inner_width = b_in
        else:
            depth = b_out
            outer_width = h_out
            inner_depth = b_in
            inner_width = h_in

        if min(depth, outer_width) <= 0.0:
            raise ValidationError("Invalid geometry for filled rectangular HSS flexural model.", details={"section": section.name})

        dy = depth / strips
        y0 = -0.5 * depth
        y_values = []
        steel_areas = []
        concrete_areas = []
        for i in range(strips):
            y = y0 + (i + 0.5) * dy
            w_outer = outer_width
            w_inner = inner_width if abs(y) <= 0.5 * inner_depth else 0.0
            a_steel = max((w_outer - w_inner) * dy, 0.0)
            a_conc = max(w_inner * dy, 0.0)
            y_values.append(y)
            steel_areas.append(a_steel)
            concrete_areas.append(a_conc)
        return {
            "profile_type": profile,
            "axis": axis,
            "depth_mm": depth,
            "y_mm": y_values,
            "Asteel_mm2": steel_areas,
            "Aconc_mm2": concrete_areas,
            "bars": bar_fibers,
            "outer": {"B_out_mm": b_out, "H_out_mm": h_out},
            "inner": {"B_in_mm": b_in, "H_in_mm": h_in},
            "t_equivalent_mm": t_eq,
        }

    if profile == "CIRCULAR_HSS":
        d_out, _ = _round_dimensions(section)
        if d_out <= 0.0:
            raise ValidationError("Invalid geometry for filled round HSS flexural model.", details={"section": section.name})
        r_out = 0.5 * d_out
        d_in_sq = max((d_out**2) - ((4.0 * as_mm2) / math.pi), 0.0)
        d_in = math.sqrt(d_in_sq)
        r_in = 0.5 * d_in
        depth = d_out
        dy = depth / strips
        y0 = -0.5 * depth
        y_values = []
        steel_areas = []
        concrete_areas = []
        for i in range(strips):
            y = y0 + (i + 0.5) * dy
            w_out = 2.0 * math.sqrt(max(r_out**2 - y**2, 0.0))
            w_in = 2.0 * math.sqrt(max(r_in**2 - y**2, 0.0)) if abs(y) <= r_in else 0.0
            a_steel = max((w_out - w_in) * dy, 0.0)
            a_conc = max(w_in * dy, 0.0)
            y_values.append(y)
            steel_areas.append(a_steel)
            concrete_areas.append(a_conc)
        return {
            "profile_type": profile,
            "axis": axis,
            "depth_mm": depth,
            "y_mm": y_values,
            "Asteel_mm2": steel_areas,
            "Aconc_mm2": concrete_areas,
            "bars": bar_fibers,
            "outer": {"D_out_mm": d_out},
            "inner": {"D_in_mm": d_in},
            "t_equivalent_mm": 0.5 * (d_out - d_in),
        }

    raise RuleNotImplementedError(
        "I5 flexural interaction is currently implemented for filled rectangular and round HSS only.",
        details={"profile_type": section.type},
    )


def _solve_neutral_axis(depth_mm: float, axial_force_fn, *, samples: int = 61) -> float:
    y_min = -0.5 * depth_mm
    y_max = 0.5 * depth_mm
    f_min = axial_force_fn(y_min)
    f_max = axial_force_fn(y_max)
    if f_min == 0.0:
        return y_min
    if f_max == 0.0:
        return y_max
    if f_min * f_max <= 0.0:
        low = y_min
        high = y_max
        for _ in range(80):
            mid = 0.5 * (low + high)
            f_mid = axial_force_fn(mid)
            if f_mid == 0.0:
                return mid
            if f_min * f_mid <= 0.0:
                high = mid
                f_max = f_mid
            else:
                low = mid
                f_min = f_mid
        return 0.5 * (low + high)

    best_y = 0.0
    best_abs = float("inf")
    step = (y_max - y_min) / (samples - 1)
    for i in range(samples):
        y = y_min + i * step
        f_val = abs(axial_force_fn(y))
        if f_val < best_abs:
            best_abs = f_val
            best_y = y
    return best_y


def _filled_plastic_response(
    model: Dict[str, object],
    *,
    fy_mpa: float,
    fc_eff_mpa: float,
) -> Dict[str, float]:
    y_values = model["y_mm"]
    a_steel = model["Asteel_mm2"]
    a_conc = model["Aconc_mm2"]
    bars = model["bars"]
    depth = float(model["depth_mm"])
    fy = _positive(fy_mpa)
    fc_eff = _positive(fc_eff_mpa)

    def _force_moment(y_na: float) -> Tuple[float, float]:
        n = 0.0
        m = 0.0
        for y, as_i, ac_i in zip(y_values, a_steel, a_conc):
            if as_i > 0.0:
                sigma_s = fy if y >= y_na else -fy
                n += sigma_s * as_i
                m += sigma_s * as_i * y
            if ac_i > 0.0 and y >= y_na:
                sigma_c = fc_eff
                n += sigma_c * ac_i
                m += sigma_c * ac_i * y
        for bar in bars:
            area = _positive(bar["A_mm2"])
            if area <= 0.0:
                continue
            y = float(bar["y_mm"])
            fy_bar = _positive(bar["fy_mpa"])
            sigma = fy_bar if y >= y_na else -fy_bar
            n += sigma * area
            m += sigma * area * y
        return n, m

    y_na = _solve_neutral_axis(depth, lambda y: _force_moment(y)[0])
    n_eq, m_eq = _force_moment(y_na)
    return {"y_na_mm": y_na, "N_n": n_eq, "Mn_nmm": abs(m_eq)}


def _filled_first_yield_response(
    model: Dict[str, object],
    *,
    es_mpa: float,
    ec_mpa: float,
    fy_mpa: float,
    fc_mpa: float,
    steel_comp_limit_mpa: float,
) -> Dict[str, float]:
    y_values = model["y_mm"]
    a_steel = model["Asteel_mm2"]
    a_conc = model["Aconc_mm2"]
    bars = model["bars"]
    depth = float(model["depth_mm"])
    es = _positive(es_mpa)
    ec = _positive(ec_mpa)
    fy = _positive(fy_mpa)
    steel_comp_limit = _positive(steel_comp_limit_mpa) or fy
    fc_limit = 0.70 * _positive(fc_mpa)
    if min(es, ec, fy, fc_limit) <= 0.0:
        return {"kappa": 0.0, "y_na_mm": 0.0, "Mn_nmm": 0.0, "governing_ratio": 0.0}

    def _state(kappa: float) -> Dict[str, float]:
        def _axial(y_na: float) -> float:
            n = 0.0
            for y, as_i, ac_i in zip(y_values, a_steel, a_conc):
                eps = kappa * (y - y_na)
                n += es * eps * as_i
                if ac_i > 0.0 and eps > 0.0:
                    n += min(ec * eps, fc_limit) * ac_i
            for bar in bars:
                area = _positive(bar["A_mm2"])
                if area <= 0.0:
                    continue
                eps = kappa * (float(bar["y_mm"]) - y_na)
                fy_bar = _positive(bar["fy_mpa"])
                sigma_bar = max(-fy_bar, min(fy_bar, es * eps))
                n += sigma_bar * area
            return n

        y_na = _solve_neutral_axis(depth, _axial)
        n = 0.0
        m = 0.0
        steel_tension = 0.0
        steel_compression = 0.0
        concrete_compression = 0.0
        for y, as_i, ac_i in zip(y_values, a_steel, a_conc):
            eps = kappa * (y - y_na)
            sigma_s = es * eps
            n += sigma_s * as_i
            m += sigma_s * as_i * y
            steel_tension = max(steel_tension, -sigma_s)
            steel_compression = max(steel_compression, sigma_s)
            if ac_i > 0.0 and eps > 0.0:
                sigma_c = min(ec * eps, fc_limit)
                n += sigma_c * ac_i
                m += sigma_c * ac_i * y
                concrete_compression = max(concrete_compression, sigma_c)
        for bar in bars:
            area = _positive(bar["A_mm2"])
            if area <= 0.0:
                continue
            eps = kappa * (float(bar["y_mm"]) - y_na)
            fy_bar = _positive(bar["fy_mpa"])
            sigma_bar = max(-fy_bar, min(fy_bar, es * eps))
            n += sigma_bar * area
            m += sigma_bar * area * float(bar["y_mm"])

        ratio = max(
            steel_tension / fy if fy > 0.0 else 0.0,
            steel_compression / steel_comp_limit if steel_comp_limit > 0.0 else 0.0,
            concrete_compression / fc_limit if fc_limit > 0.0 else 0.0,
        )
        return {"ratio": ratio, "N_n": n, "Mn_nmm": abs(m), "y_na_mm": y_na}

    k_low = 1e-12
    state_low = _state(k_low)
    k_high = 1e-8
    state_high = _state(k_high)
    while state_high["ratio"] < 1.0 and k_high < 1.0:
        k_high *= 2.0
        state_high = _state(k_high)
    if state_high["ratio"] < 1.0:
        return {"kappa": k_high, "y_na_mm": state_high["y_na_mm"], "Mn_nmm": state_high["Mn_nmm"], "governing_ratio": state_high["ratio"]}

    low = k_low
    high = k_high
    for _ in range(80):
        mid = 0.5 * (low + high)
        state_mid = _state(mid)
        if state_mid["ratio"] >= 1.0:
            high = mid
            state_high = state_mid
        else:
            low = mid
            state_low = state_mid
    return {"kappa": high, "y_na_mm": state_high["y_na_mm"], "Mn_nmm": state_high["Mn_nmm"], "governing_ratio": state_high["ratio"]}


def _filled_flexural_capacity_i3_axis(case: SteelCase, section: Section, *, axis: str) -> Dict[str, float | str | dict]:
    require_case_method(case, chapter="I")
    profile = section.type.upper()
    if profile not in {"RECTANGULAR_HSS", "CIRCULAR_HSS"}:
        raise RuleNotImplementedError(
            "I3.4 flexural strength in current scope supports only rectangular and round filled HSS members.",
            details={"profile_type": section.type},
        )
    parts = _composite_section_components(case, section)
    classification = composite_calc.filled_section_classification_i1_4(
        profile_type=profile,
        b_over_t=section.b_tdes_ratio,
        h_over_t=section.h_tdes_ratio,
        d_over_t=section.d_t_ratio,
        e_mpa=case.material.E,
        fy_mpa=case.material.Fy,
    )
    flex_class = classification["classification_flexure"]
    model = _filled_strip_model(case, section, axis=axis)
    fc_eff = 0.95 * case.composite.concrete.fc if profile == "CIRCULAR_HSS" else 0.85 * case.composite.concrete.fc
    mp_data = _filled_plastic_response(model, fy_mpa=case.material.Fy, fc_eff_mpa=fc_eff)
    mp = mp_data["Mn_nmm"]

    if profile == "RECTANGULAR_HSS":
        lam = max(_positive(section.b_tdes_ratio), _positive(section.h_tdes_ratio))
    else:
        lam = _positive(section.d_t_ratio)
    lp = _positive(classification["limits"].get("flexure_lambda_p"))
    lr = _positive(classification["limits"].get("flexure_lambda_r"))

    fn = case.material.Fy
    fn_clause = None
    if flex_class == "slender":
        if profile == "RECTANGULAR_HSS":
            fn = composite_calc.fn_filled_rectangular_i2_10(es_mpa=case.material.E, lambda_value=lam)
            fn_clause = "I2-10"
        else:
            fn = composite_calc.fn_filled_round_i2_11(fy_mpa=case.material.Fy, es_mpa=case.material.E, d_over_t=lam)
            fn_clause = "I2-11"

    my_data = _filled_first_yield_response(
        model,
        es_mpa=case.material.E,
        ec_mpa=composite_calc.concrete_modulus_ec_mpa(fc_mpa=case.composite.concrete.fc, wc_kg_m3=case.composite.concrete.wc),
        fy_mpa=case.material.Fy,
        fc_mpa=case.composite.concrete.fc,
        steel_comp_limit_mpa=fn,
    )
    my = my_data["Mn_nmm"]

    if flex_class == "compact":
        mn = mp
        branch = "I3-5a"
    elif flex_class == "noncompact":
        ratio = ((lam - lp) / (lr - lp)) if lr > lp else 1.0
        ratio = max(0.0, min(1.0, ratio))
        mn = mp - (mp - my) * ratio
        branch = "I3-5b"
    else:
        mn = my
        branch = "I3-5c"

    mc = 0.90 * mn / 1_000_000.0
    return {
        "axis": axis,
        "profile_type": profile,
        "classification_I1_4": classification,
        "lambda_used": lam,
        "Mn_nmm": mn,
        "Mc_kN_m": mc,
        "Mp_nmm": mp,
        "My_nmm": my,
        "branch": branch,
        "Fn_mpa": fn,
        "Fn_source_clause": fn_clause,
        "plastic_data": mp_data,
        "yield_data": my_data,
    }


def _encased_steel_only_flexural_capacity_axis(case: SteelCase, section: Section, *, axis: str) -> Dict[str, float | str]:
    require_case_method(case, chapter="I")
    z = _positive(section.zx) if axis == "x" else _positive(section.zy)
    if z <= 0.0:
        s = _positive(section.sx) if axis == "x" else _positive(section.sy)
        z = s
    if z <= 0.0:
        raise ValidationError(
            "I5 flexural interaction for encased members requires section modulus data.",
            details={"axis": axis, "section": section.name},
        )
    mn = case.material.Fy * z
    mc = 0.90 * mn / 1_000_000.0
    return {"axis": axis, "Mn_nmm": mn, "Mc_kN_m": mc, "branch": "I3-3a(2)_steel_only"}


def _composite_flexural_capacities_i5(case: SteelCase, section: Section) -> Dict[str, Dict[str, float | str | dict]]:
    require_case_method(case, chapter="I")
    role = _composite_role(case)
    if role == "FILLED_MEMBER":
        return {
            "x": _filled_flexural_capacity_i3_axis(case, section, axis="x"),
            "y": _filled_flexural_capacity_i3_axis(case, section, axis="y"),
        }
    if role == "ENCASED_MEMBER":
        return {
            "x": _encased_steel_only_flexural_capacity_axis(case, section, axis="x"),
            "y": _encased_steel_only_flexural_capacity_axis(case, section, axis="y"),
        }
    raise RuleNotImplementedError(
        "I5 interaction is currently implemented for ENCASED_MEMBER and FILLED_MEMBER.",
        details={"role": role},
    )


def _composite_axial_capacity_i5(case: SteelCase, section: Section) -> Dict[str, float | str]:
    require_case_method(case, chapter="I")
    role = _composite_role(case)
    pu = case.loads.Pu
    if pu > 0.0:
        if role == "ENCASED_MEMBER":
            res = CompositeI2EncasedCompressionRule().check(case, section)
        elif role == "FILLED_MEMBER":
            res = CompositeI2FilledCompressionRule().check(case, section)
        else:
            raise RuleNotImplementedError("I5 axial interaction scope excludes this role.", details={"role": role})
        return {"capacity_kN": float(res.capacity), "mode": "compression", "source_clause": res.clause}
    if pu < 0.0:
        if role == "ENCASED_MEMBER":
            res = CompositeI2EncasedTensionRule().check(case, section)
        elif role == "FILLED_MEMBER":
            res = CompositeI2FilledTensionRule().check(case, section)
        else:
            raise RuleNotImplementedError("I5 axial interaction scope excludes this role.", details={"role": role})
        return {"capacity_kN": float(res.capacity), "mode": "tension", "source_clause": res.clause}
    return {"capacity_kN": math.inf, "mode": "none", "source_clause": "none"}


def _i5_moment_ratio_sum(case: SteelCase, flex_caps: Dict[str, Dict[str, float | str | dict]]) -> Dict[str, float]:
    require_case_method(case, chapter="I")
    mcx = float(flex_caps["x"]["Mc_kN_m"])
    mcy = float(flex_caps["y"]["Mc_kN_m"])
    r_x = _safe_ratio(demand=case.loads.Mux, capacity=mcx, ratio_name="Mrx/Mcx")
    r_y = _safe_ratio(demand=case.loads.Muy, capacity=mcy, ratio_name="Mry/Mcy")
    return {"Mrx_over_Mcx": r_x, "Mry_over_Mcy": r_y, "sum": r_x + r_y, "Mcx_kN_m": mcx, "Mcy_kN_m": mcy}


def _i5_method_1_h1_interaction(case: SteelCase, axial_cap_kN: float, m_ratio_sum: float) -> Dict[str, float | str]:
    require_case_method(case, chapter="I")
    if case.loads.Pu == 0.0:
        return {"ratio": m_ratio_sum, "branch": "H1-no-axial", "Pu_over_P": 0.0}
    p_ratio = _safe_ratio(demand=case.loads.Pu, capacity=axial_cap_kN, ratio_name="Pr/Pc_or_Pt")
    if case.loads.Pu > 0.0:
        if p_ratio >= 0.2:
            ratio = p_ratio + ((8.0 / 9.0) * m_ratio_sum)
            branch = "H1-1a"
        else:
            ratio = (p_ratio / 2.0) + m_ratio_sum
            branch = "H1-1b"
    else:
        ratio = p_ratio + m_ratio_sum
        branch = "H1-2"
    return {"ratio": ratio, "branch": branch, "Pu_over_P": p_ratio}


def _i5_method2_filled_table_points(case: SteelCase, section: Section, parts: Dict[str, float]) -> Dict[str, object]:
    profile = section.type.upper()
    fy = case.material.Fy
    fc = case.composite.concrete.fc
    if profile == "RECTANGULAR_HSS":
        t = _positive(section.tdes) or _positive(section.t)
        zsx = _positive(section.zx) or _positive(section.sx)
        zsy = _positive(section.zy) or _positive(section.sy)
        table_data = composite_calc.i5_method2_table63_points(
            fy_mpa=fy,
            fc_mpa=fc,
            as_mm2=parts["As_mm2"],
            ac_mm2=parts["Ac_mm2"],
            t_mm=t,
            b_out_mm=parts["B_out_mm"],
            h_out_mm=parts["H_out_mm"],
            zs_x_mm3=zsx,
            zs_y_mm3=zsy,
        )
    elif profile == "CIRCULAR_HSS":
        d_out = _positive(section.od) or _positive(section.d)
        t = _positive(section.tdes) or _positive(section.t)
        z_s = _positive(section.zx) or _positive(section.zy) or _positive(section.sx) or _positive(section.sy)
        table_data = composite_calc.i5_method2_table64_points(
            fy_mpa=fy,
            fc_mpa=fc,
            d_out_mm=d_out,
            t_mm=t,
            zs_mm3=z_s,
        )
    else:
        raise RuleNotImplementedError(
            "Method 2 tabulated points are currently implemented for rectangular and round filled HSS.",
            details={"profile_type": section.type},
        )

    if not bool(table_data.get("valid")):
        raise ValidationError(
            "Method 2 table point calculation produced invalid geometry/properties.",
            details={"profile_type": section.type, "table_data": table_data},
        )
    return table_data


def _i5_method2_encased_table_points(
    case: SteelCase,
    section: Section,
    parts: Dict[str, float],
    flex_caps: Dict[str, Dict[str, float | str | dict]],
) -> Dict[str, object]:
    require_case_method(case, chapter="I")
    b = _positive(parts.get("B_mm"))
    h = _positive(parts.get("H_mm"))
    if min(b, h) <= 0.0:
        raise ValidationError(
            "Method 2 for encased members requires composite.geometry.B and composite.geometry.H.",
            details={"B_mm": parts.get("B_mm"), "H_mm": parts.get("H_mm")},
        )

    fy = case.material.Fy
    fc = case.composite.concrete.fc
    fysr = _positive(parts.get("Fysr_mpa")) or fy
    as_area = parts["As_mm2"]
    asr_area = parts["Asr_mm2"]
    ac_area = parts["Ac_mm2"]

    pa_kN = ((fy * as_area) + (fysr * asr_area) + (0.85 * fc * ac_area)) / 1000.0
    pc_kN = (0.85 * fc * ac_area) / 1000.0
    pd_kN = pc_kN / 2.0

    zsx = _positive(section.zx)
    zsy = _positive(section.zy)
    if min(zsx, zsy) <= 0.0:
        raise ValidationError(
            "Method 2 for encased members requires section plastic modulus Zx and Zy.",
            details={"section": section.name, "Zx_mm3": section.zx, "Zy_mm3": section.zy},
        )

    zr_x = _bar_plastic_modulus(case, axis="x")
    zr_y = _bar_plastic_modulus(case, axis="y")
    zc_x = max((b * (h**2) / 4.0) - zsx - zr_x, 0.0)
    zc_y = max((h * (b**2) / 4.0) - zsy - zr_y, 0.0)
    md_x = ((fy * zsx) + (fysr * zr_x) + (0.85 * fc * (zc_x / 2.0))) / 1_000_000.0
    md_y = ((fy * zsy) + (fysr * zr_y) + (0.85 * fc * (zc_y / 2.0))) / 1_000_000.0

    mb_x = _positive(float(flex_caps["x"]["Mc_kN_m"]))
    mb_y = _positive(float(flex_caps["y"]["Mc_kN_m"]))
    if min(mb_x, mb_y) <= 0.0:
        raise ValidationError(
            "Method 2 for encased members requires positive flexural capacities for both axes.",
            details={"Mcx_kN_m": flex_caps["x"]["Mc_kN_m"], "Mcy_kN_m": flex_caps["y"]["Mc_kN_m"]},
        )

    points_x = {
        "A": {"P_kN": pa_kN, "M_kN_m": 0.0},
        "C": {"P_kN": pc_kN, "M_kN_m": mb_x},
        "D": {"P_kN": pd_kN, "M_kN_m": max(0.0, md_x)},
        "B": {"P_kN": 0.0, "M_kN_m": mb_x},
    }
    points_y = {
        "A": {"P_kN": pa_kN, "M_kN_m": 0.0},
        "C": {"P_kN": pc_kN, "M_kN_m": mb_y},
        "D": {"P_kN": pd_kN, "M_kN_m": max(0.0, md_y)},
        "B": {"P_kN": 0.0, "M_kN_m": mb_y},
    }

    bf = _positive(section.bf)
    if bf > 0.0:
        pe_kN = ((fy * as_area) + (0.85 * fc * max(ac_area - ((b / 2.0) * (h - bf)) + (asr_area / 2.0), 0.0))) / 1000.0
        zce = max((h * (bf**2) / 4.0) - zsy, 0.0)
        me_kN_m = max(0.0, md_y - ((fy * zsy) / 1_000_000.0) - ((0.85 * fc * (zce / 2.0)) / 1_000_000.0))
        points_y["E"] = {"P_kN": pe_kN, "M_kN_m": me_kN_m}

    return {
        "valid": True,
        "table": "6-2",
        "source": "SCM16_table_6-2_with_I3_MB",
        "PA_kN": pa_kN,
        "PC_kN": pc_kN,
        "axes": {
            "x": {"points": points_x, "intermediate": {"Zr_mm3": zr_x, "Zc_mm3": zc_x}},
            "y": {"points": points_y, "intermediate": {"Zr_mm3": zr_y, "Zc_mm3": zc_y}},
        },
        "inputs": {"Fy_mpa": fy, "Fyr_mpa": fysr, "fc_mpa": fc, "As_mm2": as_area, "Asr_mm2": asr_area, "Ac_mm2": ac_area},
    }


def _i5_method_2_interaction(
    case: SteelCase,
    section: Section,
    axial_cap_kN: float,
    m_ratios: Dict[str, float],
    flex_caps: Dict[str, Dict[str, float | str | dict]],
) -> Dict[str, object]:
    require_case_method(case, chapter="I")
    if case.loads.Pu <= 0.0:
        raise ValidationError(
            "Method 2 is scoped to combined axial compression and flexure.",
            details={"method": "METHOD_2_PLASTIC_INTERACTION", "Pu_kN": case.loads.Pu},
        )
    role = _composite_role(case)
    parts = _composite_section_components(case, section)
    if role == "FILLED_MEMBER":
        table_data = _i5_method2_filled_table_points(case, section, parts)
        source = f"SCM16_table_{table_data['table']}"
    elif role == "ENCASED_MEMBER":
        table_data = _i5_method2_encased_table_points(case, section, parts, flex_caps)
        source = str(table_data.get("source") or "SCM16_table_6-2")
    else:
        raise RuleNotImplementedError(
            "Method 2 interaction is only available for encased and filled members.",
            details={"role": role},
        )

    pa = _positive(table_data.get("PA_kN")) or axial_cap_kN
    pc = _positive(table_data.get("PC_kN"))
    if min(pa, pc) <= 0.0 or pa <= pc:
        raise ValidationError(
            "Method 2 requires valid PA and PC points with PA > PC.",
            details={"PA_kN": pa, "PC_kN": pc, "table": table_data.get("table")},
        )

    axes = table_data["axes"]
    mcx = _positive(axes["x"]["points"]["C"]["M_kN_m"]) or m_ratios["Mcx_kN_m"]
    mcy = _positive(axes["y"]["points"]["C"]["M_kN_m"]) or m_ratios["Mcy_kN_m"]
    mrx_over_mcx = _safe_ratio(demand=case.loads.Mux, capacity=mcx, ratio_name="Mrx/Mcx_method2")
    mry_over_mcy = _safe_ratio(demand=case.loads.Muy, capacity=mcy, ratio_name="Mry/Mcy_method2")

    ratio_data = composite_calc.i5_commentary_method2_ratio(
        pr_kN=max(case.loads.Pu, 0.0),
        pa_kN=pa,
        pc_kN=pc,
        mrx_over_mcx=mrx_over_mcx,
        mry_over_mcy=mry_over_mcy,
    )
    return {
        "ratio": float(ratio_data["ratio"]),
        "branch": str(ratio_data["branch"]),
        "PA_kN": pa,
        "PC_kN": pc,
        "PC_over_PA": (pc / pa) if pa > 0.0 else 0.0,
        "MCx_kN_m": mcx,
        "MCy_kN_m": mcy,
        "Mrx_over_MCx": mrx_over_mcx,
        "Mry_over_MCy": mry_over_mcy,
        "interaction_points_by_axis": axes,
        "table_reference": table_data.get("table"),
        "table_inputs": table_data.get("inputs"),
        "ratio_source": source,
    }


def _i5_method_4_interaction(case: SteelCase, section: Section, axial_cap_kN: float, m_ratio_sum: float) -> Dict[str, object]:
    require_case_method(case, chapter="I")
    if case.loads.Pu <= 0.0:
        raise ValidationError(
            "Method 4 (Eq. I5-1) is scoped to combined axial compression and flexure.",
            details={"method": "METHOD_4_DIRECT_INTERACTION", "Pu_kN": case.loads.Pu},
        )
    parts = _composite_section_components(case, section)
    classif = composite_calc.filled_section_classification_i1_4(
        profile_type=section.type.upper(),
        b_over_t=section.b_tdes_ratio,
        h_over_t=section.h_tdes_ratio,
        d_over_t=section.d_t_ratio,
        e_mpa=case.material.E,
        fy_mpa=case.material.Fy,
    )
    if classif["classification_flexure"] == "compact":
        raise ValidationError(
            "Method 4 (Eq. I5-1) in Section I5(b) is intended for noncompact/slender filled composite sections.",
            details={"classification_flexure": classif["classification_flexure"]},
        )
    csr = composite_calc.i5_strength_ratio_csr(
        as_mm2=parts["As_mm2"],
        fy_mpa=case.material.Fy,
        asr_mm2=parts["Asr_mm2"],
        fysr_mpa=parts["Fysr_mpa"],
        ac_mm2=parts["Ac_mm2"],
        fc_mpa=case.composite.concrete.fc,
    )
    cp_cm = composite_calc.i5_cp_cm_table(profile_type=section.type.upper(), csr=csr)
    cp = float(cp_cm["cp"])
    cm = float(cp_cm["cm"])
    ratio_data = composite_calc.i5_direct_interaction_ratio(
        pr_kN=max(case.loads.Pu, 0.0),
        pc_kN=axial_cap_kN,
        mr_ratio=m_ratio_sum,
        cp=cp,
        cm=cm,
    )
    return {
        "ratio": float(ratio_data["ratio"]),
        "branch": str(ratio_data["branch"]),
        "Pr_over_Pc": float(ratio_data["Pr_over_Pc"]) if "Pr_over_Pc" in ratio_data else None,
        "cp": cp,
        "cm": cm,
        "cp_cm_branch": cp_cm["branch"],
        "csr": csr,
        "classification_I1_4": classif,
    }


class CompositeI1Rule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        role = _composite_role(case)
        method = _ensure_supported_method(case, section)
        components = _composite_section_components(case, section)
        classification = {}
        if role == "FILLED_MEMBER":
            classification = composite_calc.filled_section_classification_i1_4(
                profile_type=section.type.upper(),
                b_over_t=section.b_tdes_ratio or section.b_t_ratio,
                h_over_t=section.h_tdes_ratio or section.h_tw_ratio,
                d_over_t=section.d_t_ratio,
                e_mpa=case.material.E,
                fy_mpa=case.material.Fy,
            )
        return _build_result(
            unit="ratio",
            name="Composite General Provisions I1",
            clause="I1",
            demand=1.0,
            capacity=1.0,
            details={
                "memory": {
                    "clause": "I1",
                    "inputs": {
                        "role": role,
                        "nominal_strength_method": method,
                        "fc_mpa": case.composite.concrete.fc,
                        "wc_kg_m3": case.composite.concrete.wc,
                        "section": section.name,
                        "profile_type": section.type,
                    },
                    "intermediate": {
                        "Ec_mpa": composite_calc.concrete_modulus_ec_mpa(fc_mpa=case.composite.concrete.fc, wc_kg_m3=case.composite.concrete.wc),
                        "section_components": components,
                        "local_buckling_classification": classification,
                        "i1_2_supported_methods": ["PLASTIC", "ELASTIC"],
                    },
                    "design_factor": {"design_method": case.design_method.value, "capacity_expression": "config_validity"},
                    "capacity": 1.0,
                }
            },
        )


class CompositeI2EncasedCompressionRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        demand = max(case.loads.Pu, 0.0)
        if demand <= 0.0:
            return _nominal_pass("Composite Axial Compression (Encased) I2", "I2-1b")
        _ensure_supported_method(case, section)
        parts = _composite_section_components(case, section)
        as_mm2 = parts["As_mm2"]
        asr_mm2 = parts["Asr_mm2"]
        ac_mm2 = parts["Ac_mm2"]
        ag_mm2 = parts["Ag_mm2"]
        fysr = parts["Fysr_mpa"]
        fc = case.composite.concrete.fc
        pno = (case.material.Fy * as_mm2) + (fysr * asr_mm2) + (0.85 * fc * ac_mm2)
        c1 = composite_calc.c1_encased_i2_6(as_mm2=as_mm2, asr_mm2=asr_mm2, ag_mm2=ag_mm2)
        pe = _effective_inertia_and_pe(
            case,
            section,
            c_factor=c1,
            ic_x=parts["Ic_x_mm4"],
            ic_y=parts["Ic_y_mm4"],
            is_x=parts["Is_x_mm4"],
            is_y=parts["Is_y_mm4"],
            isr_x=parts["Isr_x_mm4"],
            isr_y=parts["Isr_y_mm4"],
        )
        buckling = composite_calc.composite_buckling_strength_i2(pno_n=pno, pe_n=pe["Pe_n"])
        phi_capacity = 0.75 * buckling["Pn_n"] / 1000.0
        steel_floor = _bare_steel_compression_capacity_k_n(case, section)
        available = max(phi_capacity, steel_floor)
        return _build_result(
            unit="kN",
            name="Composite Axial Compression (Encased) I2",
            clause="I2-1b",
            demand=demand,
            capacity=available,
            details={
                "memory": {
                    "clause": "I2-1b",
                    "inputs": {
                        "Pu_kN": case.loads.Pu,
                        "Fy_mpa": case.material.Fy,
                        "fc_mpa": fc,
                        "As_mm2": as_mm2,
                        "Asr_mm2": asr_mm2,
                        "Ac_mm2": ac_mm2,
                        "Ag_mm2": ag_mm2,
                        "Fysr_mpa": fysr,
                        "Kx": case.factors.Kx,
                        "Ky": case.factors.Ky,
                        "Lx_mm": case.lengths.Lx,
                        "Ly_mm": case.lengths.Ly,
                    },
                    "intermediate": {
                        "Pno_n_I2_7": pno,
                        "C1_I2_6": c1,
                        "effective_rigidity": pe,
                        "buckling": buckling,
                        "phiPn_composite_kN": phi_capacity,
                        "steel_floor_kN_chapter_E": steel_floor,
                        "governing_capacity_kN": available,
                    },
                    "design_factor": {
                        "design_method": "LRFD",
                        "phi_c": 0.75,
                        "capacity_expression": "max(phi_c*Pn_composite, steel_floor_E)",
                    },
                    "capacity_kn": available,
                }
            },
        )


class CompositeI2EncasedTensionRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        demand = abs(case.loads.Pu) if case.loads.Pu < 0.0 else 0.0
        if demand <= 0.0:
            return _nominal_pass("Composite Axial Tension (Encased) I2", "I2-8")
        _ensure_supported_method(case, section)
        parts = _composite_section_components(case, section)
        pn = (case.material.Fy * parts["As_mm2"]) + (parts["Fysr_mpa"] * parts["Asr_mm2"])
        capacity = 0.90 * pn / 1000.0
        return _build_result(
            unit="kN",
            name="Composite Axial Tension (Encased) I2",
            clause="I2-8",
            demand=demand,
            capacity=capacity,
            details={
                "memory": {
                    "clause": "I2-8",
                    "inputs": {
                        "Pu_tension_kN": demand,
                        "Fy_mpa": case.material.Fy,
                        "As_mm2": parts["As_mm2"],
                        "Fysr_mpa": parts["Fysr_mpa"],
                        "Asr_mm2": parts["Asr_mm2"],
                    },
                    "intermediate": {"Pn_n": pn},
                    "design_factor": {"design_method": "LRFD", "phi_t": 0.90, "capacity_expression": "phi_t*Pn"},
                    "capacity_kn": capacity,
                }
            },
        )


class CompositeI2FilledCompressionRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        demand = max(case.loads.Pu, 0.0)
        if demand <= 0.0:
            return _nominal_pass("Composite Axial Compression (Filled) I2", "I2-2")
        _ensure_supported_method(case, section)
        parts = _composite_section_components(case, section)
        as_mm2 = parts["As_mm2"]
        asr_mm2 = parts["Asr_mm2"]
        ac_mm2 = parts["Ac_mm2"]
        ag_mm2 = parts["Ag_mm2"]
        fysr = parts["Fysr_mpa"]
        fc = case.composite.concrete.fc
        profile = section.type.upper()
        if profile == "RECTANGULAR_HSS":
            lam = max(_positive(section.b_tdes_ratio), _positive(section.h_tdes_ratio))
        else:
            lam = _positive(section.d_t_ratio)
        classification = composite_calc.filled_section_classification_i1_4(
            profile_type=profile,
            b_over_t=section.b_tdes_ratio,
            h_over_t=section.h_tdes_ratio,
            d_over_t=section.d_t_ratio,
            e_mpa=case.material.E,
            fy_mpa=case.material.Fy,
        )
        c2 = 0.85 if profile == "RECTANGULAR_HSS" else 0.95
        p_p = (case.material.Fy * as_mm2) + (c2 * fc * ac_mm2) + (fysr * asr_mm2)
        p_y = (case.material.Fy * as_mm2) + (0.70 * fc * ac_mm2) + (fysr * asr_mm2)
        fn_clause = None
        if classification["classification_axial"] == "compact":
            pno = p_p
            pno_branch = "I2-9a"
        elif classification["classification_axial"] == "noncompact":
            lp = classification["limits"]["axial_lambda_p"]
            lr = classification["limits"]["axial_lambda_r"]
            ratio = ((lam - lp) / (lr - lp)) if lr > lp else 1.0
            ratio = max(0.0, min(1.0, ratio))
            pno = p_p - (p_p - p_y) * (ratio**2)
            pno_branch = "I2-9c"
        else:
            if profile == "RECTANGULAR_HSS":
                fn = composite_calc.fn_filled_rectangular_i2_10(es_mpa=case.material.E, lambda_value=lam)
                fn_clause = "I2-10"
            else:
                fn = composite_calc.fn_filled_round_i2_11(fy_mpa=case.material.Fy, es_mpa=case.material.E, d_over_t=lam)
                fn_clause = "I2-11"
            pno = (fn * as_mm2) + (0.70 * fc * ac_mm2) + (fysr * asr_mm2)
            pno_branch = "I2-9e"
        c3 = composite_calc.c3_filled_i2_13(as_mm2=as_mm2, asr_mm2=asr_mm2, ag_mm2=ag_mm2)
        pe = _effective_inertia_and_pe(
            case,
            section,
            c_factor=c3,
            ic_x=parts["Ic_x_mm4"],
            ic_y=parts["Ic_y_mm4"],
            is_x=parts["Is_x_mm4"],
            is_y=parts["Is_y_mm4"],
            isr_x=parts["Isr_x_mm4"],
            isr_y=parts["Isr_y_mm4"],
        )
        buckling = composite_calc.composite_buckling_strength_i2(pno_n=pno, pe_n=pe["Pe_n"])
        phi_capacity = 0.75 * buckling["Pn_n"] / 1000.0
        steel_floor = _bare_steel_compression_capacity_k_n(case, section)
        available = max(phi_capacity, steel_floor)
        details_intermediate = {
            "classification_I1_4": classification,
            "lambda_used": lam,
            "Pp_n_I2_9b": p_p,
            "Py_n_I2_9d": p_y,
            "Pno_n": pno,
            "Pno_branch": pno_branch,
            "C2": c2,
            "C3_I2_13": c3,
            "effective_rigidity": pe,
            "buckling": buckling,
            "phiPn_composite_kN": phi_capacity,
            "steel_floor_kN_chapter_E": steel_floor,
            "governing_capacity_kN": available,
        }
        if fn_clause is not None:
            details_intermediate["Fn_source_clause"] = fn_clause
        return _build_result(
            unit="kN",
            name="Composite Axial Compression (Filled) I2",
            clause="I2-2",
            demand=demand,
            capacity=available,
            details={
                "memory": {
                    "clause": "I2-2",
                    "inputs": {
                        "Pu_kN": case.loads.Pu,
                        "profile_type": profile,
                        "Fy_mpa": case.material.Fy,
                        "fc_mpa": fc,
                        "As_mm2": as_mm2,
                        "Asr_mm2": asr_mm2,
                        "Ac_mm2": ac_mm2,
                        "Ag_mm2": ag_mm2,
                        "Fysr_mpa": fysr,
                    },
                    "intermediate": details_intermediate,
                    "design_factor": {
                        "design_method": "LRFD",
                        "phi_c": 0.75,
                        "capacity_expression": "max(phi_c*Pn_composite, steel_floor_E)",
                    },
                    "capacity_kn": available,
                }
            },
        )


class CompositeI2FilledTensionRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        demand = abs(case.loads.Pu) if case.loads.Pu < 0.0 else 0.0
        if demand <= 0.0:
            return _nominal_pass("Composite Axial Tension (Filled) I2", "I2-14")
        _ensure_supported_method(case, section)
        parts = _composite_section_components(case, section)
        pn = (case.material.Fy * parts["As_mm2"]) + (parts["Fysr_mpa"] * parts["Asr_mm2"])
        capacity = 0.90 * pn / 1000.0
        return _build_result(
            unit="kN",
            name="Composite Axial Tension (Filled) I2",
            clause="I2-14",
            demand=demand,
            capacity=capacity,
            details={
                "memory": {
                    "clause": "I2-14",
                    "inputs": {
                        "Pu_tension_kN": demand,
                        "Fy_mpa": case.material.Fy,
                        "As_mm2": parts["As_mm2"],
                        "Fysr_mpa": parts["Fysr_mpa"],
                        "Asr_mm2": parts["Asr_mm2"],
                    },
                    "intermediate": {"Pn_n": pn},
                    "design_factor": {"design_method": "LRFD", "phi_t": 0.90, "capacity_expression": "phi_t*Pn"},
                    "capacity_kn": capacity,
                }
            },
        )


class CompositeI5CombinedRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        role = _composite_role(case)
        if role not in {"ENCASED_MEMBER", "FILLED_MEMBER"}:
            return _nominal_pass("Combined Flexure and Axial Force I5", "I5")

        has_flexure = abs(case.loads.Mux) > 0.0 or abs(case.loads.Muy) > 0.0
        if not has_flexure or abs(case.loads.Pu) <= 0.0:
            return _nominal_pass("Combined Flexure and Axial Force I5", "I5")

        method = case.composite.i5.method
        flex_caps = _composite_flexural_capacities_i5(case, section)
        m_ratios = _i5_moment_ratio_sum(case, flex_caps)
        axial = _composite_axial_capacity_i5(case, section)
        p_available = float(axial["capacity_kN"])

        if method == CompositeI5Method.METHOD_1_H1_1:
            method_data = _i5_method_1_h1_interaction(case, p_available, m_ratios["sum"])
            method_clause = str(method_data["branch"])
            method_reference = "I5(a) -> H1.1"
        elif method == CompositeI5Method.METHOD_2_PLASTIC_INTERACTION:
            method_data = _i5_method_2_interaction(case, section, p_available, m_ratios, flex_caps)
            method_clause = str(method_data["branch"])
            method_reference = "SCM 16th Tables 6-2/6-3/6-4 + C-I5-1a/b"
        elif method == CompositeI5Method.METHOD_4_DIRECT_INTERACTION:
            if role != "FILLED_MEMBER":
                raise ValidationError(
                    "Method 4 (Eq. I5-1a/b) is scoped to filled composite members.",
                    details={"method": method.value, "role": role},
                )
            method_data = _i5_method_4_interaction(case, section, p_available, m_ratios["sum"])
            method_clause = str(method_data["branch"])
            method_reference = "I5(b) Eq. I5-1a/I5-1b"
        else:
            raise ValidationError("Unknown I5 method.", details={"method": str(method)})

        ratio = float(method_data["ratio"])
        emit_step(producer=__name__+":CompositeI5CombinedRule.check", limit_state="composite_axial_biaxial_interaction",
            branch=method_clause, reference=method_reference, equation=None, expression=None, axis="x+y",
            inputs=(quantity("Pu", case.loads.Pu, "kN", "case.loads.Pu"),
                    quantity("Mux", case.loads.Mux, "kN-m", "case.loads.Mux"),
                    quantity("Muy", case.loads.Muy, "kN-m", "case.loads.Muy")),
            intermediates=(quantity("Pc", p_available, "kN", "_composite_axial_capacity_i5"),
                           quantity("Mcx", m_ratios["Mcx_kN_m"], "kN-m"),
                           quantity("Mcy", m_ratios["Mcy_kN_m"], "kN-m")),
            outputs=(quantity("interaction", ratio, "ratio"),),
            assumptions=("Selected I5 method: "+method.value, "Role: "+role),
            unknowns=("Method 2 is auxiliary/Commentary, not a Specification equation; numerical iteration and branch-equation mapping remain pending.",))
        return _build_result(
            unit="ratio",
            name=f"Combined Flexure and Axial Force I5 ({method.value})",
            clause="I5",
            demand=ratio,
            capacity=1.0,
            details={
                "memory": {
                    "clause": "I5",
                    "inputs": {
                        "method": method.value,
                        "role": role,
                        "Pu_kN": case.loads.Pu,
                        "Mux_kN_m": case.loads.Mux,
                        "Muy_kN_m": case.loads.Muy,
                        "axial_capacity_source": axial["source_clause"],
                    },
                    "intermediate": {
                        "method_reference": method_reference,
                        "method_branch": method_clause,
                        "Pu_over_Pavailable": _safe_ratio(demand=case.loads.Pu, capacity=p_available, ratio_name="Pu/Pavailable"),
                        "Mrx_over_Mcx": m_ratios["Mrx_over_Mcx"],
                        "Mry_over_Mcy": m_ratios["Mry_over_Mcy"],
                        "Mr_over_Mc_equivalent_sum": m_ratios["sum"],
                        "method_data": method_data,
                    },
                    "capacities": {
                        "P_available_kN": p_available,
                        "Mcx_kN_m": m_ratios["Mcx_kN_m"],
                        "Mcy_kN_m": m_ratios["Mcy_kN_m"],
                    },
                    "components": {
                        "axial": axial,
                        "flexure": flex_caps,
                    },
                    "design_factor": {
                        "design_method": case.design_method.value,
                        "capacity_expression": "interaction <= 1.0",
                    },
                    "capacity": 1.0,
                }
            },
        )


class CompositeI3_1aRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        if _composite_role(case) != "COMPOSITE_BEAM":
            return _nominal_pass("Load Transfer Concrete Crushing I3-1a", "I3-1a")
        _ensure_supported_method(case, section)
        shear = _composite_beam_horizontal_shear(case, section)
        return _build_result(
            unit="kN",
            name="Load Transfer Concrete Crushing I3-1a",
            clause="I3-1a",
            demand=shear["V_required_kN"],
            capacity=shear["V_concrete_kN"],
            details={
                "memory": {
                    "clause": "I3-1a",
                    "inputs": {
                        "fc_mpa": case.composite.concrete.fc,
                        "Ac_effective_mm2": shear["Ac_effective_mm2"],
                    },
                    "intermediate": {"V_required_kN": shear["V_required_kN"], "V_concrete_kN": shear["V_concrete_kN"]},
                    "capacity_kn": shear["V_concrete_kN"],
                }
            },
        )


class CompositeI3_1bRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        if _composite_role(case) != "COMPOSITE_BEAM":
            return _nominal_pass("Load Transfer Steel Yielding I3-1b", "I3-1b")
        _ensure_supported_method(case, section)
        shear = _composite_beam_horizontal_shear(case, section)
        return _build_result(
            unit="kN",
            name="Load Transfer Steel Yielding I3-1b",
            clause="I3-1b",
            demand=shear["V_required_kN"],
            capacity=shear["V_steel_kN"],
            details={
                "memory": {
                    "clause": "I3-1b",
                    "inputs": {"Fy_mpa": case.material.Fy, "As_mm2": shear["As_mm2"]},
                    "intermediate": {"V_required_kN": shear["V_required_kN"], "V_steel_kN": shear["V_steel_kN"]},
                    "capacity_kn": shear["V_steel_kN"],
                }
            },
        )


class CompositeI3_1cRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        if _composite_role(case) != "COMPOSITE_BEAM":
            return _nominal_pass("Load Transfer Steel Anchors I3-1c", "I3-1c")
        _ensure_supported_method(case, section)
        shear = _composite_beam_horizontal_shear(case, section)
        return _build_result(
            unit="kN",
            name="Load Transfer Steel Anchors I3-1c",
            clause="I3-1c",
            demand=shear["V_required_kN"],
            capacity=shear["V_anchor_kN"],
            details={
                "memory": {
                    "clause": "I3-1c",
                    "inputs": {
                        "anchors_segment": "positive",
                        "groups_count": len(shear["anchor_groups"]),
                    },
                    "intermediate": {
                        "V_required_kN": shear["V_required_kN"],
                        "sum_Qn_kN": shear["V_anchor_kN"],
                        "anchor_groups": shear["anchor_groups"],
                    },
                    "capacity_kn": shear["V_anchor_kN"],
                }
            },
        )


class CompositeI3_3Rule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        if _composite_role(case) != "ENCASED_MEMBER":
            return _nominal_pass("Minimum Reinforcement Ratio I3-3", "I3-3")
        parts = _composite_section_components(case, section)
        rho = (parts["Asr_mm2"] / parts["Ag_mm2"]) if parts["Ag_mm2"] > 0.0 else 0.0
        demand = 0.004
        capacity = rho
        return _build_result(
            unit="ratio",
            name="Minimum Reinforcement Ratio I3-3",
            clause="I3-3",
            demand=demand,
            capacity=capacity,
            details={
                "memory": {
                    "clause": "I3-3",
                    "inputs": {"Asr_mm2": parts["Asr_mm2"], "Ag_mm2": parts["Ag_mm2"]},
                    "intermediate": {"rho_sr": rho, "rho_sr_min_required": 0.004},
                    "capacity": capacity,
                }
            },
        )


class CompositeI3_4Rule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        if _composite_role(case) != "FILLED_MEMBER":
            return _nominal_pass("Minimum Reinforcement Ratio I3-4", "I3-4")
        parts = _composite_section_components(case, section)
        rho = (parts["Asr_mm2"] / parts["Ag_mm2"]) if parts["Ag_mm2"] > 0.0 else 0.0
        if parts["Asr_mm2"] <= 0.0:
            return _build_result(
                unit="ratio",
                name="Minimum Reinforcement Ratio I3-4",
                clause="I3-4",
                demand=0.0,
                capacity=1.0,
                details={
                    "memory": {
                        "clause": "I3-4",
                        "inputs": {"Asr_mm2": 0.0, "Ag_mm2": parts["Ag_mm2"]},
                        "intermediate": {
                            "rho_sr": 0.0,
                            "rho_sr_min_required_when_reinforcement_provided": 0.004,
                            "note": "Longitudinal reinforcement not provided; minimum ratio does not govern.",
                        },
                        "capacity": 1.0,
                    }
                },
            )
        demand = 0.004
        capacity = rho
        return _build_result(
            unit="ratio",
            name="Minimum Reinforcement Ratio I3-4",
            clause="I3-4",
            demand=demand,
            capacity=capacity,
            details={
                "memory": {
                    "clause": "I3-4",
                    "inputs": {"Asr_mm2": parts["Asr_mm2"], "Ag_mm2": parts["Ag_mm2"]},
                    "intermediate": {"rho_sr": rho, "rho_sr_min_required": 0.004},
                    "capacity": capacity,
                }
            },
        )


class CompositeI4_1aEncasedRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        if _composite_role(case) != "ENCASED_MEMBER":
            return _nominal_pass("Encased Shear Steel Only I4-1a", "I4-1a")
        demand = _required_shear(case)
        if demand <= 0.0:
            return _nominal_pass("Encased Shear Steel Only I4-1a", "I4-1a")
        steel = _steel_shear_capacity_k_n(case, section)
        return _build_result(
            unit="kN",
            name="Encased Shear Steel Only I4-1a",
            clause="I4-1a",
            demand=demand,
            capacity=steel["phiVn_kN"],
            details={
                "memory": {
                    "clause": "I4-1a",
                    "inputs": {"Vu_kN": demand, "Fy_mpa": case.material.Fy},
                    "intermediate": steel,
                    "design_factor": {"design_method": "LRFD", "phi_v": 0.90, "capacity_expression": "phi_v*Vn_steel"},
                    "capacity_kn": steel["phiVn_kN"],
                }
            },
        )


class CompositeI4_1bEncasedRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        if _composite_role(case) != "ENCASED_MEMBER":
            return _nominal_pass("Encased Shear RC Only I4-1b", "I4-1b")
        demand = _required_shear(case)
        if demand <= 0.0:
            return _nominal_pass("Encased Shear RC Only I4-1b", "I4-1b")
        b = _positive(case.composite.geometry.B)
        h = _positive(case.composite.geometry.H)
        d_eff = 0.8 * h if h > 0.0 else 0.0
        fc = case.composite.concrete.fc
        vc_n = 0.17 * math.sqrt(fc) * b * d_eff if min(fc, b, d_eff) > 0.0 else 0.0
        transverse = case.composite.reinforcement.transverse
        vs_n = 0.0
        if transverse is not None and transverse.spacing > 0.0:
            av_mm2 = 2.0 * math.pi * (transverse.db**2) / 4.0
            vs_n = av_mm2 * transverse.fy * d_eff / transverse.spacing
        v_n = vc_n + vs_n
        capacity = 0.75 * v_n / 1000.0
        return _build_result(
            unit="kN",
            name="Encased Shear RC Only I4-1b",
            clause="I4-1b",
            demand=demand,
            capacity=capacity,
            details={
                "memory": {
                    "clause": "I4-1b",
                    "inputs": {"Vu_kN": demand, "fc_mpa": fc, "B_mm": b, "H_mm": h},
                    "intermediate": {"d_eff_mm": d_eff, "Vc_n": vc_n, "Vs_n": vs_n, "Vn_n": v_n},
                    "design_factor": {"design_method": "LRFD", "phi_v": 0.75, "capacity_expression": "phi_v*(Vc+Vs)"},
                    "capacity_kn": capacity,
                }
            },
        )


class CompositeI4_1cEncasedRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        if _composite_role(case) != "ENCASED_MEMBER":
            return _nominal_pass("Encased Shear Steel+Transverse I4-1c", "I4-1c")
        demand = _required_shear(case)
        if demand <= 0.0:
            return _nominal_pass("Encased Shear Steel+Transverse I4-1c", "I4-1c")
        steel = _steel_shear_capacity_k_n(case, section)
        vn_steel = steel["Vn_n"]
        h = _positive(case.composite.geometry.H)
        d_eff = 0.8 * h if h > 0.0 else 0.0
        transverse = case.composite.reinforcement.transverse
        vs_n = 0.0
        if transverse is not None and transverse.spacing > 0.0:
            av_mm2 = 2.0 * math.pi * (transverse.db**2) / 4.0
            vs_n = av_mm2 * transverse.fy * d_eff / transverse.spacing
        vn = vn_steel + vs_n
        capacity = 0.75 * vn / 1000.0
        return _build_result(
            unit="kN",
            name="Encased Shear Steel+Transverse I4-1c",
            clause="I4-1c",
            demand=demand,
            capacity=capacity,
            details={
                "memory": {
                    "clause": "I4-1c",
                    "inputs": {"Vu_kN": demand},
                    "intermediate": {"Vn_steel_n": vn_steel, "Vs_n": vs_n, "Vn_n": vn, "steel_component": steel},
                    "design_factor": {"design_method": "LRFD", "phi_v": 0.75, "capacity_expression": "phi_v*(Vn_steel+Vs)"},
                    "capacity_kn": capacity,
                }
            },
        )


class CompositeI4_1EncasedGoverningRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        if _composite_role(case) != "ENCASED_MEMBER":
            return _nominal_pass("Encased Shear Governing I4-1", "I4-1")
        demand = _required_shear(case)
        if demand <= 0.0:
            return _nominal_pass("Encased Shear Governing I4-1", "I4-1")
        a = CompositeI4_1aEncasedRule().check(case, section)
        b = CompositeI4_1bEncasedRule().check(case, section)
        c = CompositeI4_1cEncasedRule().check(case, section)
        capacities = {"I4-1a": a.capacity, "I4-1b": b.capacity, "I4-1c": c.capacity}
        governing = max(capacities, key=capacities.get)
        capacity = capacities[governing]
        return _build_result(
            unit="kN",
            name="Encased Shear Governing I4-1",
            clause="I4-1",
            demand=demand,
            capacity=capacity,
            details={
                "memory": {
                    "clause": "I4-1",
                    "inputs": {"Vu_kN": demand},
                    "intermediate": {"subcheck_capacities_kN": capacities, "governing_subcheck": governing},
                    "design_factor": {"design_method": "LRFD", "capacity_expression": "max(I4-1a, I4-1b, I4-1c)"},
                    "capacity_kn": capacity,
                }
            },
        )


class CompositeI4_1FilledRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        if _composite_role(case) != "FILLED_MEMBER":
            return _nominal_pass("Filled Shear I4-1", "I4-1")
        demand = _required_shear(case)
        if demand <= 0.0:
            return _nominal_pass("Filled Shear I4-1", "I4-1")
        profile = section.type.upper()
        if profile not in {"RECTANGULAR_HSS", "CIRCULAR_HSS"}:
            raise RuleNotImplementedError(
                "I4-1 in current scope supports only rectangular and round filled HSS members.",
                details={"profile_type": section.type},
            )
        parts = _composite_section_components(case, section)
        classification = composite_calc.filled_section_classification_i1_4(
            profile_type=profile,
            b_over_t=section.b_tdes_ratio,
            h_over_t=section.h_tdes_ratio,
            d_over_t=section.d_t_ratio,
            e_mpa=case.material.E,
            fy_mpa=case.material.Fy,
        )
        compact = classification["classification_axial"] == "compact"
        if profile == "RECTANGULAR_HSS":
            h = _positive(section.h)
            t = _positive(section.tdes) or _positive(section.t)
            av = 2.0 * h * t if min(h, t) > 0.0 else 0.0
            d = _positive(section.h) or _positive(section.d)
            round_hss = False
            rectangular = True
        else:
            av = 2.0 * _positive(section.area) / math.pi if _positive(section.area) > 0.0 else 0.0
            d, _ = _round_dimensions(section)
            round_hss = True
            rectangular = False
        mu = max(abs(case.loads.Mux), abs(case.loads.Muy))
        kc = composite_calc.kc_i4_1(
            compact=compact,
            rectangular=rectangular,
            round_hss=round_hss,
            mu_k_nm=mu,
            vu_k_n=demand,
            depth_mm=d,
        )
        v_n = (0.6 * case.material.Fy * av) + (kc["Kc"] * case.composite.concrete.fc * parts["Ac_mm2"])
        capacity = 0.90 * v_n / 1000.0
        return _build_result(
            unit="kN",
            name="Filled Shear I4-1",
            clause="I4-1",
            demand=demand,
            capacity=capacity,
            details={
                "memory": {
                    "clause": "I4-1",
                    "inputs": {
                        "Vu_kN": demand,
                        "Mu_kN_m": mu,
                        "Fy_mpa": case.material.Fy,
                        "fc_mpa": case.composite.concrete.fc,
                        "Av_mm2": av,
                        "Ac_mm2": parts["Ac_mm2"],
                        "d_mm": d,
                        "profile_type": profile,
                    },
                    "intermediate": {
                        "classification_I1_4": classification,
                        "kc_data": kc,
                        "Vn_n": v_n,
                    },
                    "design_factor": {"design_method": "LRFD", "phi_v": 0.90, "capacity_expression": "phi_v*Vn"},
                    "capacity_kn": capacity,
                }
            },
        )


class CompositeI4_3BeamDeckSteelOnlyRule:
    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case, chapter="I")
        if _composite_role(case) != "COMPOSITE_BEAM":
            return _nominal_pass("Composite Beam Shear Steel Only I4-3", "I4-3")
        if not bool(case.composite.geometry.deck_present):
            return _nominal_pass("Composite Beam Shear Steel Only I4-3", "I4-3")
        demand = _required_shear(case)
        if demand <= 0.0:
            return _nominal_pass("Composite Beam Shear Steel Only I4-3", "I4-3")
        steel = _steel_shear_capacity_k_n(case, section)
        return _build_result(
            unit="kN",
            name="Composite Beam Shear Steel Only I4-3",
            clause="I4-3",
            demand=demand,
            capacity=steel["phiVn_kN"],
            details={
                "memory": {
                    "clause": "I4-3",
                    "inputs": {"Vu_kN": demand, "deck_present": True},
                    "intermediate": steel,
                    "design_factor": {"design_method": "LRFD", "phi_v": 0.90, "capacity_expression": "phi_v*Vn_steel_only"},
                    "capacity_kn": steel["phiVn_kN"],
                }
            },
        )
