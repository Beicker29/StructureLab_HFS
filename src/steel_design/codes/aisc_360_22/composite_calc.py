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


def i5_strength_ratio_csr(*, as_mm2: float, fy_mpa: float, asr_mm2: float, fysr_mpa: float, ac_mm2: float, fc_mpa: float) -> float:
    """
    AISC 360-22 Eq. I5-2:
      csr = (As*Fy + Asr*Fysr) / (Ac*fc')
    """
    as_area = _positive(as_mm2)
    fy = _positive(fy_mpa)
    asr_area = _positive(asr_mm2)
    fysr = _positive(fysr_mpa)
    ac_area = _positive(ac_mm2)
    fc = _positive(fc_mpa)
    denominator = ac_area * fc
    if min(denominator, as_area, fy) <= 0.0:
        return 0.0
    numerator = (as_area * fy) + (asr_area * fysr)
    return numerator / denominator


def i5_cp_cm_table(*, profile_type: str, csr: float) -> Dict[str, float | str]:
    """
    AISC 360-22 Table I5.1 coefficients for Eq. I5-1a/I5-1b.
    """
    c = _positive(csr)
    if c <= 0.0:
        return {"cp": 0.0, "cm": 0.0, "branch": "invalid_csr"}

    ptype = (profile_type or "").upper()
    if ptype == "RECTANGULAR_HSS":
        cp = 0.17 / (c**0.4)
        if c >= 0.5:
            cm_raw = 1.06 / (c**0.11)
            cm = max(cm_raw, 1.0)
            branch = "rect_csr>=0.5"
        else:
            cm_raw = 0.90 / (c**0.36)
            cm = min(cm_raw, 1.67)
            branch = "rect_csr<0.5"
        return {"cp": cp, "cm": cm, "cm_raw": cm_raw, "branch": branch}

    if ptype == "CIRCULAR_HSS":
        cp = 0.27 / (c**0.4)
        if c >= 0.5:
            cm_raw = 1.10 / (c**0.08)
            cm = max(cm_raw, 1.0)
            branch = "round_csr>=0.5"
        else:
            cm_raw = 0.95 / (c**0.32)
            cm = min(cm_raw, 1.67)
            branch = "round_csr<0.5"
        return {"cp": cp, "cm": cm, "cm_raw": cm_raw, "branch": branch}

    return {"cp": 0.0, "cm": 0.0, "branch": "unsupported_profile"}


def i5_direct_interaction_ratio(*, pr_kN: float, pc_kN: float, mr_ratio: float, cp: float, cm: float) -> Dict[str, float | str]:
    """
    AISC 360-22 Eq. I5-1a / I5-1b.
    `mr_ratio` is Mr/Mc (or equivalent biaxial aggregation).
    """
    pr = _positive(pr_kN)
    pc = _positive(pc_kN)
    cp_val = _positive(cp)
    cm_val = _positive(cm)
    m_ratio = max(0.0, float(mr_ratio))
    if min(pc, cp_val, cm_val) <= 0.0:
        return {"ratio": float("inf"), "branch": "invalid"}

    p_ratio = pr / pc
    if p_ratio >= cp_val:
        ratio = p_ratio + ((1.0 - cp_val) / (cp_val * cm_val)) * m_ratio
        return {"ratio": ratio, "branch": "I5-1a", "Pr_over_Pc": p_ratio}

    ratio = (((1.0 - cm_val) / cp_val) * p_ratio) + m_ratio
    return {"ratio": ratio, "branch": "I5-1b", "Pr_over_Pc": p_ratio}


def i5_commentary_method2_ratio(
    *,
    pr_kN: float,
    pa_kN: float,
    pc_kN: float,
    mrx_over_mcx: float,
    mry_over_mcy: float,
) -> Dict[str, float | str]:
    """
    Commentary Eq. C-I5-1a / C-I5-1b (simplified Method 2).
    """
    pr = _positive(pr_kN)
    pa = _positive(pa_kN)
    pc = _positive(pc_kN)
    rx = max(0.0, float(mrx_over_mcx))
    ry = max(0.0, float(mry_over_mcy))
    m_sum = rx + ry
    if min(pa, pc) <= 0.0:
        return {"ratio": float("inf"), "branch": "invalid"}

    if pr < pc:
        ratio = (pr / pc) + m_sum
        return {"ratio": ratio, "branch": "C-I5-1a"}

    denominator = pa - pc
    if denominator <= 0.0:
        return {"ratio": float("inf"), "branch": "invalid_PA_PC"}
    ratio = ((pr - pc) / denominator) + m_sum
    return {"ratio": ratio, "branch": "C-I5-1b"}


def _n_to_kn(value_n: float) -> float:
    return float(value_n) / 1000.0


def _nmm_to_kn_m(value_n_mm: float) -> float:
    return float(value_n_mm) / 1_000_000.0


def _pm_point(*, p_n: float, m_n_mm: float) -> Dict[str, float]:
    return {"P_kN": _n_to_kn(p_n), "M_kN_m": _nmm_to_kn_m(m_n_mm)}


def i5_method2_table63_points(
    *,
    fy_mpa: float,
    fc_mpa: float,
    as_mm2: float,
    ac_mm2: float,
    t_mm: float,
    b_out_mm: float,
    h_out_mm: float,
    zs_x_mm3: float,
    zs_y_mm3: float,
) -> Dict[str, object]:
    """
    Steel Construction Manual 16th (2023), Table 6-3.
    Cross-section strength points for composite filled rectangular HSS.
    """
    fy = _positive(fy_mpa)
    fc = _positive(fc_mpa)
    as_area = _positive(as_mm2)
    ac_area = _positive(ac_mm2)
    t = _positive(t_mm)
    b_out = _positive(b_out_mm)
    h_out = _positive(h_out_mm)
    zsx = _positive(zs_x_mm3)
    zsy = _positive(zs_y_mm3)
    if min(fy, fc, as_area, ac_area, t, b_out, h_out, zsx, zsy) <= 0.0:
        return {"valid": False, "reason": "invalid_inputs"}

    b_i = b_out - (2.0 * t)
    h_i = h_out - (2.0 * t)
    r_i = t
    if min(b_i, h_i) <= 0.0:
        return {"valid": False, "reason": "invalid_inner_dimensions"}

    p_a_n = (fy * as_area) + (0.85 * fc * ac_area)
    p_c_n = 0.85 * fc * ac_area
    p_d_n = p_c_n / 2.0

    def _axis_points(*, width_i: float, depth_i: float, depth_out: float, z_s: float) -> Dict[str, object]:
        z_c = (width_i * (depth_i**2) / 4.0) - (0.429 * (r_i**2) * depth_i) + (0.192 * (r_i**3))
        m_d_n_mm = (fy * z_s) + (0.85 * fc * (z_c / 2.0))
        denom = 2.0 * ((0.85 * fc * width_i) + (4.0 * fy * t))
        h_n = (0.85 * fc * ac_area) / denom if denom > 0.0 else 0.0
        h_n = max(0.0, min(h_n, depth_i / 2.0))

        z_sn = 2.0 * t * (h_n**2)
        z_cn = width_i * (h_n**2)
        m_b_n_mm = m_d_n_mm - (fy * z_sn) - (0.85 * fc * (z_cn / 2.0))
        m_b_n_mm = max(0.0, m_b_n_mm)

        h_e = (h_n / 2.0) + (depth_out / 4.0)
        z_se = 2.0 * t * (h_e**2)
        z_ce = width_i * (h_e**2)
        p_e_n = (0.85 * fc * ac_area / 2.0) + (0.85 * fc * width_i * h_e) + (4.0 * fy * t * h_e)
        m_e_n_mm = m_d_n_mm - (fy * z_se) - (0.85 * fc * (z_ce / 2.0))
        m_e_n_mm = max(0.0, m_e_n_mm)

        return {
            "points": {
                "A": _pm_point(p_n=p_a_n, m_n_mm=0.0),
                "E": _pm_point(p_n=p_e_n, m_n_mm=m_e_n_mm),
                "C": _pm_point(p_n=p_c_n, m_n_mm=m_b_n_mm),
                "D": _pm_point(p_n=p_d_n, m_n_mm=m_d_n_mm),
                "B": _pm_point(p_n=0.0, m_n_mm=m_b_n_mm),
            },
            "intermediate": {
                "b_i_mm": width_i,
                "h_i_mm": depth_i,
                "r_i_mm": r_i,
                "h_n_mm": h_n,
                "h_e_mm": h_e,
                "Zc_mm3": z_c,
                "Zsn_mm3": z_sn,
                "Zcn_mm3": z_cn,
                "ZsE_mm3": z_se,
                "ZcE_mm3": z_ce,
            },
        }

    axis_x = _axis_points(width_i=b_i, depth_i=h_i, depth_out=h_out, z_s=zsx)
    axis_y = _axis_points(width_i=h_i, depth_i=b_i, depth_out=b_out, z_s=zsy)
    return {
        "valid": True,
        "table": "6-3",
        "PA_kN": _n_to_kn(p_a_n),
        "PC_kN": _n_to_kn(p_c_n),
        "axes": {"x": axis_x, "y": axis_y},
        "inputs": {
            "Fy_mpa": fy,
            "fc_mpa": fc,
            "As_mm2": as_area,
            "Ac_mm2": ac_area,
            "B_mm": b_out,
            "H_mm": h_out,
            "t_mm": t,
        },
    }


def i5_method2_table64_points(
    *,
    fy_mpa: float,
    fc_mpa: float,
    d_out_mm: float,
    t_mm: float,
    zs_mm3: float,
) -> Dict[str, object]:
    """
    Steel Construction Manual 16th (2023), Table 6-4.
    Cross-section strength points for composite filled round HSS.
    """
    fy = _positive(fy_mpa)
    fc = _positive(fc_mpa)
    d = _positive(d_out_mm)
    t = _positive(t_mm)
    z_s = _positive(zs_mm3)
    if min(fy, fc, d, t, z_s) <= 0.0:
        return {"valid": False, "reason": "invalid_inputs"}

    h = d - (2.0 * t)
    if h <= 0.0:
        return {"valid": False, "reason": "invalid_inner_diameter"}

    as_area = math.pi * ((d * t) - (t**2))
    ac_area = math.pi * (h**2) / 4.0
    p_a_n = (fy * as_area) + (0.95 * fc * ac_area)
    p_c_n = 0.95 * fc * ac_area
    p_d_n = p_c_n / 2.0

    z_c_d = h**3 / 6.0
    m_d_n_mm = (fy * z_s) + (0.95 * fc * (z_c_d / 2.0))

    k_c = fc * (h**2)
    k_s = fy * ((d - t) / 2.0) * t
    if k_c <= 0.0:
        theta = math.pi / 2.0
    else:
        term1 = ((0.0260 * k_c) - (2.0 * k_s)) / (0.0848 * k_c)
        radicand = (0.0260 * ((k_c + (2.0 * k_s)) ** 2) + (0.857 * k_c * k_s)) / (0.0848 * k_c)
        theta = term1 + math.sqrt(max(0.0, radicand))
    theta = max(1e-6, min(math.pi - 1e-6, theta))

    sin_half_theta = math.sin(theta / 2.0)
    h_n = (h / 2.0) * math.sin((math.pi - theta) / 2.0)
    z_s_b = (d**3 / 6.0) - ((h**3 / 6.0) * (sin_half_theta**3))
    z_c_b = (h**3 / 6.0) * (sin_half_theta**3)
    m_b_n_mm = (fy * z_s_b) + (0.95 * fc * (z_c_b / 2.0))

    h_e = (h_n / 2.0) + (h / 4.0)
    arg = (2.0 * h_e / h) if h > 0.0 else 0.0
    arg = max(-1.0, min(1.0, arg))
    theta2 = math.pi - (2.0 * math.asin(arg))
    shape_factor = (theta2 - math.sin(theta2)) / 8.0
    p_e_n = p_a_n - (fy * ((d**2) - (h**2)) * shape_factor) - (0.95 * fc * (h**2) * shape_factor)
    sin_half_theta2 = math.sin(theta2 / 2.0)
    z_c_e = (h**3 / 6.0) * (sin_half_theta2**3)
    z_s_e = (d**3 / 6.0) - ((h**3 / 6.0) * (sin_half_theta2**3))
    m_e_n_mm = (fy * z_s_e) + (0.95 * fc * (z_c_e / 2.0))

    points = {
        "A": _pm_point(p_n=p_a_n, m_n_mm=0.0),
        "E": _pm_point(p_n=p_e_n, m_n_mm=m_e_n_mm),
        "C": _pm_point(p_n=p_c_n, m_n_mm=m_b_n_mm),
        "D": _pm_point(p_n=p_d_n, m_n_mm=m_d_n_mm),
        "B": _pm_point(p_n=0.0, m_n_mm=m_b_n_mm),
    }
    axis_data = {
        "points": points,
        "intermediate": {
            "h_mm": h,
            "h_n_mm": h_n,
            "h_e_mm": h_e,
            "theta_rad": theta,
            "theta2_rad": theta2,
            "Ks": k_s,
            "Kc": k_c,
            "Zc_D_mm3": z_c_d,
            "Zs_B_mm3": z_s_b,
            "Zc_B_mm3": z_c_b,
            "Zs_E_mm3": z_s_e,
            "Zc_E_mm3": z_c_e,
        },
    }
    return {
        "valid": True,
        "table": "6-4",
        "PA_kN": _n_to_kn(p_a_n),
        "PC_kN": _n_to_kn(p_c_n),
        "axes": {"x": axis_data, "y": axis_data},
        "inputs": {
            "Fy_mpa": fy,
            "fc_mpa": fc,
            "d_mm": d,
            "t_mm": t,
            "As_mm2": as_area,
            "Ac_mm2": ac_area,
        },
    }
