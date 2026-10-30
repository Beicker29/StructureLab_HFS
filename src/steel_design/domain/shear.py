"""Chapter G for one member and one shear direction. LRFD.

Axis convention: "x" is the shear that accompanies bending about x (parallel to y, resisted by the
web of I-shapes and channels, the H walls of rectangular HSS and the legs parallel to y of angles);
"y" accompanies bending about y. Families: rolled I-shapes and channels (G2.1, G6), single and
double angles (G3), rectangular HSS and solid bars (G4), round HSS (G5). Webs without transverse
stiffeners. Formulas live in codes/aisc_360_22/shear.py. Missing data or decisions raise structured errors.
"""
import math

from ..codes.aisc_360_22 import shear as eq
from ..errors import IncompleteSectionDataError, RuleNotImplementedError
from ..models import SteelCase
from ..sections.identity import double_angle_label
from ..sections.models import Section

_LIMITATIONS = (
    "Almas sin rigidizadores transversales (kv = 5.34); el campo de tracción (G2.2, G2.3) y los rigidizadores "
    "(G2.4) quedan fuera de este cálculo.",
    "Cortante sin torsión; la interacción de cortante con torsión (H3) no está cubierta.",
)


def _blocked(reason, section, **details):
    raise RuleNotImplementedError(reason, code="SHEAR_DOMAIN_BLOCKED",
                                  details={"section": section.name, "profile_type": section.type, **details})


def _require(section, *names):
    missing = [n for n in names if not (isinstance(getattr(section, n), (int, float))
                                        and math.isfinite(getattr(section, n)) and getattr(section, n) > 0)]
    if missing:
        raise IncompleteSectionDataError("El cortante requiere estas propiedades de la sección.",
                                         code="SHEAR_DATA_INCOMPLETE",
                                         details={"section": section.name, "profile_type": section.type,
                                                  "fields": ["section." + n for n in missing]})


def _element(name, ratio, cv, kv):
    return {"element": name, "ratio": ratio, "kv": kv, "limit": cv["limit"], "Cv": cv["Cv"],
            "Cv_equation": cv["equation"]}


def _i_web(section, E, Fy):
    """G2.1, shear parallel to the web of a rolled I-shape or channel."""
    _require(section, "d", "tw", "h_tw_ratio")
    channel = section.type.upper() == "CHANNEL"
    h_tw, aw = section.h_tw_ratio, section.d * section.tw
    if not channel and h_tw <= eq.rolled_web_limit(E=E, Fy=Fy):
        cv = {"Cv": 1.0, "equation": "G2-2", "limit": eq.rolled_web_limit(E=E, Fy=Fy)}
        phi, provision, kv = eq.PHI_V_ROLLED, "G2.1(a)", None
    else:
        kv = eq.KV_UNSTIFFENED
        cv = eq.cv1(h_tw=h_tw, kv=kv, E=E, Fy=Fy)
        phi, provision = eq.PHI_V, "G2.1(b)"
    out = eq.web_strength(Fy=Fy, Aw=aw, Cv=cv["Cv"], equation="G2-1")
    return provision, phi, [_element("web", h_tw, cv, kv)], {**out, "Aw_mm2": aw, "Cv1": cv["Cv"],
                                                            "Cv_equation": cv["equation"]}


def _i_flanges(section, E, Fy):
    """G6, minor-axis shear: both flanges resist (G6-1 per flange)."""
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
    _require(section, "tdes", "h" if axis == "x" else "b")
    h, t = (section.h if axis == "x" else section.b), section.tdes
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
    # Catalog orientation: the long leg is parallel to y and resists the shear that accompanies Mux.
    return _legs(section, E, Fy, long_leg if axis == "x" else short_leg, 1,
                 "long_leg" if axis == "x" else "short_leg")


def _double_angle(section, E, Fy, axis):
    _require(section, "d", "b", "t")
    long_leg, short_leg = max(section.d, section.b), min(section.d, section.b)
    configuration = double_angle_label(section.name)["configuration"]
    if long_leg != short_leg and configuration is None:
        _blocked("Ángulo doble desigual sin LLBB/SLBB: no se puede identificar el ala vertical.", section)
    web = short_leg if configuration == "SLBB" else long_leg          # legs in the plane of symmetry (y)
    flange = long_leg if web == short_leg else short_leg
    return _legs(section, E, Fy, web if axis == "x" else flange, 2, "web_legs" if axis == "x" else "flange_legs")


def _solid(section, E, Fy, axis):
    """G4, other doubly symmetric shapes (DG-4): Aw = d*t, h = d parallel to the shear, t across it."""
    if section.type.upper() == "SOLID_CIRCULAR":
        _require(section, "area")
        aw = 0.5 * section.area
        out = eq.web_strength(Fy=Fy, Aw=aw, Cv=1.0, equation="G4-1")
        return "G4", eq.PHI_V, [], {**out, "Aw_mm2": aw, "Cv2": 1.0}
    _require(section, "h", "b")
    d, t = (section.h, section.b) if axis == "x" else (section.b, section.h)
    cv = eq.cv2(h_tw=d / t, kv=eq.KV_HSS, E=E, Fy=Fy)
    out = eq.web_strength(Fy=Fy, Aw=d * t, Cv=cv["Cv"], equation="G4-1")
    return "G4", eq.PHI_V, [_element("bar", d / t, cv, eq.KV_HSS)], {
        **out, "h_mm": d, "t_mm": t, "Aw_mm2": d * t, "Cv2": cv["Cv"], "Cv_equation": cv["equation"]}


def shear_strength(case: SteelCase, section: Section, axis: str) -> dict:
    """Nominal and design shear strength in one direction ("x": accompanies Mux; "y": accompanies Muy)."""
    family = section.type.upper()
    E, Fy = case.material.E, case.material.Fy
    if abs(E - eq.E_STEEL) > 1e-6:
        raise IncompleteSectionDataError("El Capítulo G usa E = 200000 MPa.", code="SHEAR_DATA_INCOMPLETE",
                                         details={"section": section.name, "fields": ["material.E"]})
    if family in {"W", "CHANNEL"}:
        provision, phi, rows, out = _i_web(section, E, Fy) if axis == "x" else _i_flanges(section, E, Fy)
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

    mode = {"limit_state": "shear", "provision": provision, "applies": True, **out, "Vn_kN": out["Vn"] / 1000.0,
            "phi_v": phi, "available_kN": eq.design_strength(out["Vn"], phi)}
    notes = []
    if family == "CIRCULAR_HSS" and out["Lv_mm"] is None:
        notes.append("Lv no indicado: Fcr con G5-2b solamente (límite inferior de G5, conservador; decisión DG-2).")
    if family == "SOLID_CIRCULAR":
        notes.append("Barra redonda: G4 define Aw = d·tw y esta sección no tiene espesor de alma; se usa "
                     "Aw = 0.5·Ag y Cv2 = 1, criterio del usuario (decisión DG-4).")
    return {
        "chapter": "G", "code": "ANSI/AISC 360-22", "axis": axis, "section": section.name, "family": family,
        "inputs": {"Fy_mpa": Fy, "E_mpa": E, "Lv_mm": case.shear.Lv if case.shear else None},
        "classification": {"elements": rows, "reference": "G2.1 / G2.2 (Cv)"},
        "provisions": ["G1", provision],
        "modes": {"V": mode},
        "governing_mode": "V",
        "governing_equation": out["equation"],
        "Vn_kN": mode["Vn_kN"],
        "phi_v": phi,
        "available_kN": mode["available_kN"],
        "requirements": [],
        "notes": notes,
        "limitations": list(_LIMITATIONS),
    }
