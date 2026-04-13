import math
from typing import Dict, Optional


ES_MPA = 200000.0


def _positive(value: Optional[float]) -> float:
    return float(value) if isinstance(value, (int, float)) and value > 0.0 else 0.0


def concrete_modulus_ec_mpa(*, fc_mpa: float, wc_kg_m3: float) -> float:
    fc = _positive(fc_mpa)
    wc = _positive(wc_kg_m3)
    if min(fc, wc) <= 0.0:
        return 0.0
    # AISC 360-22 Eq. I1-1/I2 references (SI): Ec = 0.043*wc^1.5*sqrt(fc)
    return 0.043 * (wc**1.5) * math.sqrt(fc)


def reinforcement_area_mm2(*, count: int, db_mm: float) -> float:
    if count <= 0:
        return 0.0
    db = _positive(db_mm)
    if db <= 0.0:
        return 0.0
    return count * math.pi * (db**2) / 4.0


def reinforcement_inertia_contribution_mm4(*, area_mm2: float, x_mm: float, y_mm: float) -> Dict[str, float]:
    area = _positive(area_mm2)
    if area <= 0.0:
        return {"Ix_mm4": 0.0, "Iy_mm4": 0.0}
    return {
        "Ix_mm4": area * (float(y_mm) ** 2),
        "Iy_mm4": area * (float(x_mm) ** 2),
    }


def c1_encased_i2_6(*, as_mm2: float, asr_mm2: float, ag_mm2: float) -> float:
    as_total = _positive(as_mm2) + _positive(asr_mm2)
    ag = _positive(ag_mm2)
    if min(as_total, ag) <= 0.0:
        return 0.0
    # Interpreted from Eq. I2-6 OCR form.
    return min(0.2 + 3.0 * (as_total / ag), 0.7)


def c3_filled_i2_13(*, as_mm2: float, asr_mm2: float, ag_mm2: float) -> float:
    as_total = _positive(as_mm2) + _positive(asr_mm2)
    ag = _positive(ag_mm2)
    if min(as_total, ag) <= 0.0:
        return 0.0
    # Interpreted from Eq. I2-13 OCR form.
    return min(0.4 + 3.0 * (as_total / ag), 0.9)


def composite_buckling_strength_i2(*, pno_n: float, pe_n: float) -> Dict[str, float | str]:
    pno = _positive(pno_n)
    pe = _positive(pe_n)
    if min(pno, pe) <= 0.0:
        return {"Pn_n": 0.0, "ratio_pno_over_pe": 0.0, "branch": "invalid"}
    ratio = pno / pe
    if ratio <= 2.25:
        pn = pno * (0.658 ** ratio)
        return {"Pn_n": pn, "ratio_pno_over_pe": ratio, "branch": "I2-2"}
    pn = 0.877 * pe
    return {"Pn_n": pn, "ratio_pno_over_pe": ratio, "branch": "I2-3"}


def filled_section_classification_i1_4(*, profile_type: str, b_over_t: Optional[float], h_over_t: Optional[float], d_over_t: Optional[float], e_mpa: float, fy_mpa: float) -> Dict[str, object]:
    e = _positive(e_mpa)
    fy = _positive(fy_mpa)
    if min(e, fy) <= 0.0:
        return {"classification_axial": "unknown", "classification_flexure": "unknown", "limits": {}}

    ptype = (profile_type or "").upper()
    sqrt_e_fy = math.sqrt(e / fy)
    if ptype == "RECTANGULAR_HSS":
        # Table I1.1a (axial): lambda_p=2.26*sqrt(E/Fy), lambda_r=3.0*sqrt(E/Fy)
        axial_lp = 2.26 * sqrt_e_fy
        axial_lr = 3.0 * sqrt_e_fy
        lam_axial = max(_positive(b_over_t), _positive(h_over_t))
        # Table I1.1b (flexure): flange b/t -> 2.26,3.0 ; web h/t -> 3.0,5.7
        flex_lp = max(2.26 * sqrt_e_fy, 3.0 * sqrt_e_fy)
        flex_lr = max(3.0 * sqrt_e_fy, 5.7 * sqrt_e_fy)
        lam_flex = max(_positive(b_over_t), _positive(h_over_t))
    else:
        # Round HSS: Table I1.1a axial 0.15E/Fy / 0.19E/Fy ; I1.1b flexure 0.09E/Fy / 0.13E/Fy
        axial_lp = 0.15 * e / fy
        axial_lr = 0.19 * e / fy
        lam_axial = _positive(d_over_t)
        flex_lp = 0.09 * e / fy
        flex_lr = 0.13 * e / fy
        lam_flex = _positive(d_over_t)

    def _classify(lam: float, lp: float, lr: float) -> str:
        if lam <= 0.0:
            return "unknown"
        if lam <= lp:
            return "compact"
        if lam <= lr:
            return "noncompact"
        return "slender"

    return {
        "classification_axial": _classify(lam_axial, axial_lp, axial_lr),
        "classification_flexure": _classify(lam_flex, flex_lp, flex_lr),
        "limits": {
            "axial_lambda_p": axial_lp,
            "axial_lambda_r": axial_lr,
            "flexure_lambda_p": flex_lp,
            "flexure_lambda_r": flex_lr,
            "lambda_axial_used": lam_axial,
            "lambda_flexure_used": lam_flex,
        },
    }


def fn_filled_rectangular_i2_10(*, es_mpa: float, lambda_value: float) -> float:
    es = _positive(es_mpa)
    lam = _positive(lambda_value)
    if min(es, lam) <= 0.0:
        return 0.0
    return 9.0 * es / (lam**2)


def fn_filled_round_i2_11(*, fy_mpa: float, es_mpa: float, d_over_t: float) -> float:
    fy = _positive(fy_mpa)
    es = _positive(es_mpa)
    lam = _positive(d_over_t)
    if min(fy, es, lam) <= 0.0:
        return 0.0
    # Conservative interpreted form using the same trend of Eq. I2-11.
    candidate = 0.70 * fy * ((2.0 * es) / (fy * lam))
    return min(fy, max(0.0, candidate))


def stud_qn_i8_1_n(*, d_mm: float, fu_mpa: float, fc_mpa: float, ec_mpa: float, rg: float, rp: float) -> Dict[str, float]:
    d = _positive(d_mm)
    fu = _positive(fu_mpa)
    fc = _positive(fc_mpa)
    ec = _positive(ec_mpa)
    rg_val = _positive(rg)
    rp_val = _positive(rp)
    asa = math.pi * (d**2) / 4.0 if d > 0.0 else 0.0
    if min(asa, fu, fc, ec, rg_val, rp_val) <= 0.0:
        return {"Qn_n": 0.0, "Asa_mm2": asa, "Q_concrete_n": 0.0, "Q_steel_n": 0.0}
    q_conc = 0.5 * asa * math.sqrt(fc * ec) * rg_val * rp_val
    q_steel = fu * asa
    return {"Qn_n": min(q_conc, q_steel), "Asa_mm2": asa, "Q_concrete_n": q_conc, "Q_steel_n": q_steel}


def channel_qn_i8_2_n(*, la_mm: float, tf_mm: float, tw_mm: float, fc_mpa: float, ec_mpa: float) -> float:
    la = _positive(la_mm)
    tf = _positive(tf_mm)
    tw = _positive(tw_mm)
    fc = _positive(fc_mpa)
    ec = _positive(ec_mpa)
    if min(la, tf, tw, fc, ec) <= 0.0:
        return 0.0
    return 0.30 * (tw + 0.5 * tf) * la * math.sqrt(fc * ec)


def kc_i4_1(*, compact: bool, rectangular: bool, round_hss: bool, mu_k_nm: float, vu_k_n: float, depth_mm: float) -> Dict[str, float | str]:
    mu = _positive(mu_k_nm)
    vu = _positive(vu_k_n)
    depth = _positive(depth_mm)
    if min(vu, depth) <= 0.0:
        return {"Kc": 1.0, "ratio_mu_over_vd": 0.0, "branch": "default"}
    ratio = (mu * 1_000_000.0) / (vu * 1000.0 * depth)
    if ratio >= 0.7:
        return {"Kc": 1.0, "ratio_mu_over_vd": ratio, "branch": "I4-1_ratio>=0.7"}
    if not compact:
        return {"Kc": 1.0, "ratio_mu_over_vd": ratio, "branch": "I4-1_noncompact_or_slender"}
    if ratio < 0.5:
        if rectangular:
            return {"Kc": 10.0, "ratio_mu_over_vd": ratio, "branch": "I4-1_rect_compact_ratio<0.5"}
        if round_hss:
            return {"Kc": 9.0, "ratio_mu_over_vd": ratio, "branch": "I4-1_round_compact_ratio<0.5"}
        return {"Kc": 1.0, "ratio_mu_over_vd": ratio, "branch": "I4-1_compact_other"}
    # 0.5 <= ratio < 0.7, linear interpolation to 1.0
    k0 = 10.0 if rectangular else 9.0 if round_hss else 1.0
    kc = k0 + (1.0 - k0) * ((ratio - 0.5) / (0.7 - 0.5))
    return {"Kc": kc, "ratio_mu_over_vd": ratio, "branch": "I4-1_interpolated"}
