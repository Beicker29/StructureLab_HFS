"""Chapter G for one member and one shear direction. LRFD.

Axes of ETABS (docs/axes.md): "y_2" is the shear along y, axis 2 (Vy_2, with Mx_3; resisted by the web of I-shapes and
channels, the H walls of rectangular HSS and the legs parallel to axis 2 of angles); "x_3" is the shear along x, axis 3
(Vx_3, with My_2). Families: rolled and welded built-up I-shapes and channels (G2.1, G6), single and
double angles (G3), rectangular HSS and solid bars (G4), round HSS (G5). Webs without transverse
stiffeners. Formulas live in codes/aisc_360_22/shear.py. Missing data or decisions raise structured errors.
"""

from ..codes.aisc_360_22 import shear as eq
from ..codes.aisc_360_22.constants import is_standard_modulus
from ..errors import IncompleteSectionDataError, blocking_error
from ..models import SteelCase
from ..sections.identity import double_angle_label
from ..sections.models import Section, missing_properties
from .fire import steel_at_temperature, with_fire

_LIMITATIONS = (
    "Rigidizadores transversales: G2.4(b) y (c) (terminación de las soldaduras, separación de pernos y soldaduras intermitentes, "
    "torsión del ala comprimida) y los rigidizadores de apoyo (J10.8) no se verifican.",
    "Cortante sin torsión; la interacción de cortante con torsión (H3) no está cubierta.",
)


_blocked = blocking_error("SHEAR_DOMAIN_BLOCKED")


def _require(section, *names):
    missing = missing_properties(section, names)
    if missing:
        raise IncompleteSectionDataError("El cortante requiere estas propiedades de la sección.",
                                         code="SHEAR_DATA_INCOMPLETE",
                                         details={"section": section.name, "profile_type": section.type,
                                                  "fields": ["section." + n for n in missing]})


def _element(name, ratio, cv, kv):
    return {"element": name, "ratio": ratio, "kv": kv, "limit": cv["limit"], "Cv": cv["Cv"],
            "Cv_equation": cv["equation"]}


def _incomplete(reason, section, fields):
    raise IncompleteSectionDataError(reason, code="SHEAR_DATA_INCOMPLETE",
                                     details={"section": section.name, "profile_type": section.type, "fields": fields})


def _flanges(section):
    """(bf, tf) of the +2 and -2 flanges; rolled shapes and channels have two equal flanges."""
    _require(section, "bf", "tf")
    return (section.bf, section.tf), (section.bf_minus2 or section.bf, section.tf_minus2 or section.tf)


def _tension_field(case, section, E, Fy, aw, h, kv):
    """G2.2 (interior panel) or G2.3 (end panel, I-shapes with equal flange areas), a/h <= 3."""
    stiff, h_tw = case.stiffeners, section.h_tw_ratio
    panel = case.shear.panel if case.shear else None
    if panel is None:
        _incomplete("Alma con rigidizadores y a/h ≤ 3: indique el panel de esta combinación (shear.panel: interior o end).",
                    section, ["shear.panel"])
    (b1, t1), (b2, t2) = _flanges(section)
    row = _element("web", h_tw, eq.cv2(h_tw=h_tw, kv=kv, E=E, Fy=Fy), kv)
    if panel == "interior":
        out = eq.tension_field_interior(Fy=Fy, E=E, Aw=aw, h_tw=h_tw, kv=kv, a_h=stiff.a / h, Afc=b1 * t1, Aft=b2 * t2,
                                        h_bfc=h / b1, h_bft=h / b2)
        return "G2.2", [row], out
    if section.type.upper() == "CHANNEL":
        _blocked("G2.3(a) da el panel extremo con campo de tensión para perfiles I; en canales no está cubierto.", section)
    if abs(b1 * t1 - b2 * t2) > 1e-9 * b1 * t1:
        _blocked("G2.3(b): con alas de áreas distintas la resistencia del panel extremo se determina por análisis.", section,
                 Af_plus2=b1 * t1, Af_minus2=b2 * t2)
    end = stiff.end
    if end is None:
        _incomplete("El panel extremo con campo de tensión (G2.3) requiere el rigidizador extremo (stiffeners.end).", section,
                    ["stiffeners.end"])
    if end.e < end.t:
        _blocked("stiffeners.end.e va de la cara interior del rigidizador al extremo de la viga: no puede ser menor que su espesor.",
                 section, e=end.e, t=end.t)
    width = 2 * end.b if end.arrangement == "pair" else end.b
    out = eq.tension_field_end(Fyw=Fy, E=E, Fy=Fy, Aw=aw, h=h, tw=section.tw, h_tw=h_tw, kv=kv, a_h=stiff.a / h, bf=b1, tf=t1,
                               Fyf=Fy, stiffener_width=width, tst=end.t, Fyst=stiff.material.Fy, e=end.e)
    return "G2.3", [row], out


def _i_web(case, section, E, Fy, hot):
    """G2.1, shear along the web of an I-shape or channel; G2.1(a) only for rolled I-shapes. With transverse stiffeners and
    a/h <= 3, the tension field of G2.2 or G2.3 is an alternative and the larger strength is taken (decision DG-6)."""
    _require(section, "d", "tw", "h_tw_ratio")
    h_tw, aw = section.h_tw_ratio, section.d * section.tw
    if section.type.upper() == "W" and h_tw <= eq.rolled_web_limit(E=E, Fy=Fy):
        cv = {"Cv": 1.0, "equation": "G2-2", "limit": eq.rolled_web_limit(E=E, Fy=Fy)}
        out = eq.web_strength(Fy=Fy, Aw=aw, Cv=cv["Cv"], equation="G2-1")
        return "G2.1(a)", eq.PHI_V_ROLLED, [_element("web", h_tw, cv, None)], {
            **out, "Aw_mm2": aw, "Cv1": cv["Cv"], "Cv_equation": cv["equation"]}
    stiff, h = case.stiffeners, h_tw * section.tw
    kv_info = eq.kv_stiffened(a_h=stiff.a / h) if stiff else {"kv": eq.KV_UNSTIFFENED, "kv_equation": "G2.1(b)(2)(i)"}
    kv = kv_info["kv"]
    cv = eq.cv1(h_tw=h_tw, kv=kv, E=E, Fy=Fy)
    web = {**eq.web_strength(Fy=Fy, Aw=aw, Cv=cv["Cv"], equation="G2-1"), "Aw_mm2": aw, "Cv1": cv["Cv"],
           "Cv_equation": cv["equation"], **kv_info}
    if stiff:
        web["a_h"] = stiff.a / h
    candidates = [("G2.1(b)", [_element("web", h_tw, cv, kv)], web, False)]
    if stiff and stiff.a / h <= 3.0:
        provision, rows, field = _tension_field(case, section, E, Fy, aw, h, kv)
        candidates.append((provision, rows, {**field, "Aw_mm2": aw, "a_h": stiff.a / h, **kv_info}, True))
    if hot:     # 4.2.4d(g): G2.1 only while the web yields; the tension field is used with Fy(T) (decision DA4-11)
        candidates = [c for c in candidates if c[3] or all(r["Cv"] >= 1.0 for r in c[1])] or candidates[:1]
    provision, rows, out, tension_field = max(candidates, key=lambda c: c[2]["Vn"])
    if len(candidates) > 1:
        out = {**out, "Vn_G2_1_N": candidates[0][2]["Vn"], "Vn_tension_field_N": candidates[1][2]["Vn"]}
    return provision, eq.PHI_V, rows, {**out, "tension_field": tension_field}


def _stiffener_requirements(case, section, E, Fy, Fy_hot):
    """G2.4(d) and (e) for the intermediate stiffeners, with Ist >= Ist1 (decision DG-7); the tension flange limit of G2.3."""
    stiff = case.stiffeners
    h = section.h_tw_ratio * section.tw
    lim = eq.stiffener_limits(E=E, Fyst=stiff.material.Fy, Fyw=Fy, b=stiff.b, t=stiff.t, h=h, tw=section.tw,
                              pair=stiff.arrangement == "pair")
    out = [{"id": "G2-16", "provision": "G2.4(d)", "message": "Relación ancho-espesor del rigidizador, (b/t)st ≤ 0.56·√(E/Fyst)",
            "value": lim["b_t"], "limit": lim["b_t_max"], "satisfied": lim["b_t"] <= lim["b_t_max"]},
           {"id": "G2-17", "provision": "G2.4(e)", "message": "Inercia del rigidizador, Ist ≥ Ist1 (G2-18; User Note de G2.4)",
            "value": lim["Ist_mm4"], "limit": lim["Ist1_mm4"], "satisfied": lim["Ist_mm4"] >= lim["Ist1_mm4"]}]
    if case.shear and case.shear.panel == "end" and stiff.a / h <= 3.0:
        _require(section, "sx")
        stress = abs(case.Mx_3) * 1e6 / section.sx            # alpha = 1.0 (LRFD); equal flange areas: Sxt = Sx
        out.append({"id": "G2.3", "provision": "G2.3(a)", "message": "Esfuerzo en el ala traccionada del panel extremo, αMr/Sxt ≤ 0.35Fy",
                    "value": stress, "limit": 0.35 * Fy_hot, "satisfied": stress <= 0.35 * Fy_hot})
    return out, lim


def _built_up_flanges(section, E, Fy):
    """G6 for a built-up I: each flange with its own bf/2tf and Cv2."""
    _require(section, "bf", "tf", "bf_minus2", "tf_minus2")
    rows, out = [], {"Vn": 0.0, "equation": "G6-1 (2 alas)", "flanges": 2}
    for name, bf, tf in (("flange_plus2", section.bf, section.tf), ("flange_minus2", section.bf_minus2, section.tf_minus2)):
        cv = eq.cv2(h_tw=bf / (2 * tf), kv=eq.KV_LEG, E=E, Fy=Fy)
        rows.append(_element(name, bf / (2 * tf), cv, eq.KV_LEG))
        one = eq.flange_strength(Fy=Fy, bf=bf, tf=tf, Cv=cv["Cv"])["Vn"]
        out[f"Vn_{name}_N"] = one
        out["Vn"] += one
    return "G6", eq.PHI_V, rows, out


def _i_flanges(section, E, Fy):
    """G6, minor-axis shear: both flanges resist (G6-1 per flange)."""
    if section.type.upper() == "I_BUILT_UP":
        return _built_up_flanges(section, E, Fy)
    _require(section, "bf", "tf")
    channel = section.type.upper() == "CHANNEL"
    ratio = section.bf / section.tf if channel else section.bf / (2 * section.tf)
    cv = eq.cv2(h_tw=ratio, kv=eq.KV_LEG, E=E, Fy=Fy)
    one = eq.flange_strength(Fy=Fy, bf=section.bf, tf=section.tf, Cv=cv["Cv"])
    return "G6", eq.PHI_V, [_element("flange", ratio, cv, eq.KV_LEG)], {
        "Vn": 2 * one["Vn"], "equation": "G6-1 (2 alas)", "flanges": 2, "Vn_per_flange_N": one["Vn"],
        "Cv2": cv["Cv"], "Cv_equation": cv["equation"]}


def _rect_hss(section, E, Fy, axis):
    """G4: Aw = 2ht, h = flat width of the walls parallel to the shear (B4.1b(d))."""
    _require(section, "tdes", "h" if axis == "y_2" else "b")
    h, t = (section.h if axis == "y_2" else section.b), section.tdes
    cv = eq.cv2(h_tw=h / t, kv=eq.KV_HSS, E=E, Fy=Fy)
    out = eq.web_strength(Fy=Fy, Aw=2 * h * t, Cv=cv["Cv"], equation="G4-1")
    return "G4", eq.PHI_V, [_element("walls", h / t, cv, eq.KV_HSS)], {
        **out, "h_mm": h, "t_mm": t, "Aw_mm2": 2 * h * t, "Cv2": cv["Cv"], "Cv_equation": cv["equation"]}


def _round_hss(case, section, E, Fy):
    _require(section, "od", "tdes", "area")
    lv = case.shear.Lv if case.shear else None
    out = eq.round_hss_strength(E=E, Fy=Fy, Ag=section.area, D=section.od, t=section.tdes, Lv=lv)
    return "G5", eq.PHI_V, [], {**out, "Lv_mm": lv, "Ag_mm2": section.area}


def _legs(section, E, Fy, b, count, name):
    """G3 applied to each angle leg parallel to the shear."""
    t = section.t
    cv = eq.cv2(h_tw=b / t, kv=eq.KV_LEG, E=E, Fy=Fy)
    one = eq.leg_strength(Fy=Fy, b=b, t=t, Cv=cv["Cv"])
    return "G3", eq.PHI_V, [_element(name, b / t, cv, eq.KV_LEG)], {
        "Vn": count * one["Vn"], "equation": "G3-1" + (f" ({count} alas)" if count > 1 else ""), "legs": count,
        "b_mm": b, "t_mm": t, "Cv2": cv["Cv"], "Cv_equation": cv["equation"]}


def _single_angle(section, E, Fy, axis):
    _require(section, "d", "b", "t")
    long_leg, short_leg = max(section.d, section.b), min(section.d, section.b)
    # Catalog orientation: the long leg is parallel to y (axis 2) and resists Vy_2.
    return _legs(section, E, Fy, long_leg if axis == "y_2" else short_leg, 1,
                 "long_leg" if axis == "y_2" else "short_leg")


def _double_angle(section, E, Fy, axis):
    _require(section, "d", "b", "t")
    long_leg, short_leg = max(section.d, section.b), min(section.d, section.b)
    configuration = double_angle_label(section.name)["configuration"]
    if long_leg != short_leg and configuration is None:
        _blocked("Ángulo doble desigual sin LLBB/SLBB: no se puede identificar el ala vertical.", section)
    web = short_leg if configuration == "SLBB" else long_leg          # legs in the plane of symmetry (y)
    flange = long_leg if web == short_leg else short_leg
    return _legs(section, E, Fy, web if axis == "y_2" else flange, 2, "web_legs" if axis == "y_2" else "flange_legs")


def _solid(section, E, Fy, axis):
    """G4, other doubly symmetric shapes (DG-4): Aw = d*t, h = d parallel to the shear, t across it."""
    if section.type.upper() == "SOLID_CIRCULAR":
        _require(section, "area")
        aw = 0.5 * section.area
        out = eq.web_strength(Fy=Fy, Aw=aw, Cv=1.0, equation="G4-1")
        return "G4", eq.PHI_V, [], {**out, "Aw_mm2": aw, "Cv2": 1.0}
    _require(section, "h", "b")
    d, t = (section.h, section.b) if axis == "y_2" else (section.b, section.h)
    cv = eq.cv2(h_tw=d / t, kv=eq.KV_HSS, E=E, Fy=Fy)
    out = eq.web_strength(Fy=Fy, Aw=d * t, Cv=cv["Cv"], equation="G4-1")
    return "G4", eq.PHI_V, [_element("bar", d / t, cv, eq.KV_HSS)], {
        **out, "h_mm": d, "t_mm": t, "Aw_mm2": d * t, "Cv2": cv["Cv"], "Cv_equation": cv["equation"]}


def _yielding_at_temperature(section, rows, out, ky):
    """4.2.4d(g): shear yielding only; Cv and Fcr keep their ambient values (Commentary). The strength is then proportional to Fy."""
    if any(row["Cv"] < 1.0 for row in rows) or out.get("Fcr_equation", "0.6Fy") != "0.6Fy":
        _blocked(
            "Apéndice 4, 4.2.4d(g): solo cubre la fluencia por cortante; aquí rige el pandeo por cortante, que exige un método "
            "alternativo.",
            section,
        )
    scaled = ("Vn", "Vn_per_flange_N", "Vn_flange_plus2_N", "Vn_flange_minus2_N", "Fcr")
    return {**out, **{key: ky * out[key] for key in scaled if key in out}}


def shear_strength(case: SteelCase, section: Section, axis: str) -> dict:
    """Nominal and design shear strength along one axis: "y_2" (Vy_2, with Mx_3) or "x_3" (Vx_3, with My_2)."""
    family = section.type.upper()
    E, Fy = case.material.E, case.material.Fy
    if not is_standard_modulus(E):
        raise IncompleteSectionDataError("El Capítulo G usa E = 200000 MPa.", code="SHEAR_DATA_INCOMPLETE",
                                         details={"section": section.name, "fields": ["material.E"]})
    hot = steel_at_temperature(case)
    requirements, notes = [], []
    if family in {"W", "CHANNEL", "I_BUILT_UP"}:
        provision, phi, rows, out = _i_web(case, section, E, Fy, bool(hot)) if axis == "y_2" else _i_flanges(section, E, Fy)
        if axis == "y_2" and case.stiffeners:
            requirements, lim = _stiffener_requirements(case, section, E, Fy, hot["Fy_T_mpa"] if hot else Fy)
            out = {**out, "Ist_mm4": lim["Ist_mm4"], "Ist1_mm4": lim["Ist1_mm4"], "rho_st": lim["rho_st"]}
            if section.h_tw_ratio <= 2.46 * (E / Fy) ** 0.5:
                notes.append("G2.4(a): con h/tw ≤ 2.46·√(E/Fy) los rigidizadores transversales no son necesarios.")
    elif family == "RECTANGULAR_HSS":
        provision, phi, rows, out = _rect_hss(section, E, Fy, axis)
    elif family == "CIRCULAR_HSS":
        provision, phi, rows, out = _round_hss(case, section, E, Fy)
    elif family == "SINGLE_ANGLE":
        provision, phi, rows, out = _single_angle(section, E, Fy, axis)
    elif family == "DOUBLE_ANGLE":
        provision, phi, rows, out = _double_angle(section, E, Fy, axis)
    elif family in {"SOLID_RECTANGULAR", "SOLID_CIRCULAR"}:
        provision, phi, rows, out = _solid(section, E, Fy, axis)
    else:
        _blocked("Familia sin disposición de cortante en este cálculo.", section)
    if hot and out.get("tension_field"):
        # Decision DA4-11: the tension field with Fy(T) and the Cv of ambient temperature; every term is proportional to Fy
        out = {**out, **{key: hot["ky"] * out[key] for key in ("Vn", "Vn_G2_1_N", "Vn_tension_field_N", "Mpf_Nmm", "Mpst_Nmm",
                                                                "Mpm_Nmm") if key in out}}
        provision = f"{provision}; Apéndice 4, 4.2.4d(g), decisión DA4-11"
        notes.append("Campo de tensión a temperatura con Fy(T) y los Cv de temperatura ambiente: extrapola 4.2.4d(g), que solo "
                     "trata la fluencia (decisión DA4-11).")
    elif hot:
        out = _yielding_at_temperature(section, rows, out, hot["ky"])
        provision = f"{provision}; Apéndice 4, 4.2.4d(g)"
    if out.get("tension_field") is not None:
        out = {k: val for k, val in out.items() if k != "tension_field"}

    mode = {"limit_state": "shear", "provision": provision, "applies": True, **out, "Vn_kN": out["Vn"] / 1000.0,
            "phi_v": phi, "available_kN": eq.design_strength(out["Vn"], phi)}
    if family == "CIRCULAR_HSS" and out["Lv_mm"] is None:
        notes.append("Lv no indicado: Fcr con G5-2b solamente (límite inferior de G5, conservador; decisión DG-2).")
    if family == "SOLID_CIRCULAR":
        notes.append("Barra redonda: G4 define Aw = d·tw y esta sección no tiene espesor de alma; se usa "
                     "Aw = 0.5·Ag y Cv2 = 1, criterio del usuario (decisión DG-4).")
    return with_fire({
        "chapter": "G", "code": "ANSI/AISC 360-22", "axis": axis, "section": section.name, "family": family,
        "inputs": {"Fy_mpa": Fy, "E_mpa": E, "Lv_mm": case.shear.Lv if case.shear else None,
                   **({"stiffeners": case.stiffeners.model_dump(exclude={"material"}), "Fyst_mpa": case.stiffeners.material.Fy,
                       "panel": case.shear.panel if case.shear else None} if case.stiffeners and axis == "y_2" else {})},
        "classification": {"elements": rows, "reference": "G2.1 / G2.2 (Cv)"},
        "provisions": ["G1", provision],
        "modes": {"V": mode},
        "governing_mode": "V",
        "governing_equation": out["equation"],
        "Vn_kN": mode["Vn_kN"],
        "phi_v": phi,
        "available_kN": mode["available_kN"],
        "requirements": requirements,
        "notes": notes,
        "limitations": list(_LIMITATIONS),
    }, hot, "4.2.4d(g)")
