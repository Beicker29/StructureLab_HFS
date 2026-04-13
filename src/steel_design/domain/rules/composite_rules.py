from __future__ import annotations

import math
from typing import Dict, Tuple

from ...codes.aisc_360_22 import axial_calc, composite_calc, shear_calc
from ...models import CheckResult, CheckStatus, SteelCase
from ...sections.models import Section
from ..errors import RuleNotImplementedError, ValidationError


def _positive(value: float | None) -> float:
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


def _ensure_supported_method(case: SteelCase, section: Section) -> str:
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


class CompositeI1Rule:
    def check(self, case: SteelCase, section: Section) -> CheckResult:
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = abs(case.loads.Pu) if case.loads.Pu < 0.0 else 0.0
        if demand <= 0.0:
            return _nominal_pass("Composite Axial Tension (Encased) I2", "I2-8")
        _ensure_supported_method(case, section)
        parts = _composite_section_components(case, section)
        pn = (case.material.Fy * parts["As_mm2"]) + (parts["Fysr_mpa"] * parts["Asr_mm2"])
        capacity = 0.90 * pn / 1000.0
        return _build_result(
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = abs(case.loads.Pu) if case.loads.Pu < 0.0 else 0.0
        if demand <= 0.0:
            return _nominal_pass("Composite Axial Tension (Filled) I2", "I2-14")
        _ensure_supported_method(case, section)
        parts = _composite_section_components(case, section)
        pn = (case.material.Fy * parts["As_mm2"]) + (parts["Fysr_mpa"] * parts["Asr_mm2"])
        capacity = 0.90 * pn / 1000.0
        return _build_result(
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


class CompositeI3_1aRule:
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if _composite_role(case) != "COMPOSITE_BEAM":
            return _nominal_pass("Load Transfer Concrete Crushing I3-1a", "I3-1a")
        _ensure_supported_method(case, section)
        shear = _composite_beam_horizontal_shear(case, section)
        return _build_result(
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if _composite_role(case) != "COMPOSITE_BEAM":
            return _nominal_pass("Load Transfer Steel Yielding I3-1b", "I3-1b")
        _ensure_supported_method(case, section)
        shear = _composite_beam_horizontal_shear(case, section)
        return _build_result(
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if _composite_role(case) != "COMPOSITE_BEAM":
            return _nominal_pass("Load Transfer Steel Anchors I3-1c", "I3-1c")
        _ensure_supported_method(case, section)
        shear = _composite_beam_horizontal_shear(case, section)
        return _build_result(
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if _composite_role(case) != "ENCASED_MEMBER":
            return _nominal_pass("Minimum Reinforcement Ratio I3-3", "I3-3")
        parts = _composite_section_components(case, section)
        rho = (parts["Asr_mm2"] / parts["Ag_mm2"]) if parts["Ag_mm2"] > 0.0 else 0.0
        demand = 0.004
        capacity = rho
        return _build_result(
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if _composite_role(case) != "FILLED_MEMBER":
            return _nominal_pass("Minimum Reinforcement Ratio I3-4", "I3-4")
        parts = _composite_section_components(case, section)
        rho = (parts["Asr_mm2"] / parts["Ag_mm2"]) if parts["Ag_mm2"] > 0.0 else 0.0
        if parts["Asr_mm2"] <= 0.0:
            return _build_result(
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if _composite_role(case) != "ENCASED_MEMBER":
            return _nominal_pass("Encased Shear Steel Only I4-1a", "I4-1a")
        demand = _required_shear(case)
        if demand <= 0.0:
            return _nominal_pass("Encased Shear Steel Only I4-1a", "I4-1a")
        steel = _steel_shear_capacity_k_n(case, section)
        return _build_result(
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
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
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if _composite_role(case) != "COMPOSITE_BEAM":
            return _nominal_pass("Composite Beam Shear Steel Only I4-3", "I4-3")
        if not bool(case.composite.geometry.deck_present):
            return _nominal_pass("Composite Beam Shear Steel Only I4-3", "I4-3")
        demand = _required_shear(case)
        if demand <= 0.0:
            return _nominal_pass("Composite Beam Shear Steel Only I4-3", "I4-3")
        steel = _steel_shear_capacity_k_n(case, section)
        return _build_result(
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
