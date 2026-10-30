"""Chapter F for one member and one bending axis: classification, selection, limit states. LRFD.

Stage 1 families: W/I (F2, F3, F6), compact channels (F2, F6), rectangular HSS (F7),
round HSS (F8) and solid bars (F11), plus F13.1 for I-shapes and channels about x.
Every limit state of the selected section is reported, either evaluated or with the
reason it does not apply; the governing one is the lowest Mn. Formulas live in
codes/aisc_360_22/flexure.py. Missing data or decisions raise structured errors.
"""
import math

from ..codes.aisc_360_22 import flexure as eq
from ..errors import IncompleteSectionDataError, RuleNotImplementedError
from ..models import FlexureBasis, SteelCase
from ..sections.models import Section

LIMIT_STATES = {"Y": "fluencia (momento plástico)", "LTB": "pandeo lateral-torsional", "FLB": "pandeo local del ala",
                "WLB": "pandeo local del alma", "LB": "pandeo local", "TFR": "rotura del ala traccionada (F13.1)"}
_LIMITATIONS = (
    "Lb y Cb son datos del usuario; Cb = 1.0 si no se indica (límite inferior de F1-1). Se supone que los apoyos "
    "restringen la rotación respecto del eje longitudinal (F1(b)).",
    "Flexión simple respecto de un eje principal: la flexión biaxial y la combinación con carga axial requieren el "
    "Capítulo H.",
)


def _blocked(reason, section, **details):
    raise RuleNotImplementedError(reason, code="FLEXURE_DOMAIN_BLOCKED",
                                  details={"section": section.name, "profile_type": section.type, **details})


def _incomplete(reason, section, fields):
    raise IncompleteSectionDataError(reason, code="FLEXURE_DATA_INCOMPLETE",
                                     details={"section": section.name, "profile_type": section.type, "fields": fields})


def _require(section, *names):
    missing = [n for n in names if not (isinstance(getattr(section, n), (int, float))
                                        and math.isfinite(getattr(section, n)) and getattr(section, n) > 0)]
    if missing:
        _incomplete("La flexión requiere estas propiedades de la sección.", section, ["section." + n for n in missing])


def _evaluated(state, provision, out):
    return {"limit_state": state, "provision": provision, "applies": True, **out, "Mn_kNm": out["Mn"] / 1e6,
            "design_kNm": eq.design_strength(out["Mn"])}


def _not_applicable(state, provision, reason, **extra):
    return {"limit_state": state, "provision": provision, "applies": False, "reason": reason, **extra}


def _ltb_mode(result, provision):
    if not result["applies"]:
        return _not_applicable("LTB", provision, result["reason"], **{k: v for k, v in result.items()
                                                                      if k not in {"applies", "reason"}})
    return _evaluated("LTB", provision, {k: v for k, v in result.items() if k != "applies"})


def _lb(basis, section):
    if basis.Lb is None:
        _incomplete("El pandeo lateral-torsional requiere Lb (flexure.Lb).", section, ["flexure.Lb"])
    return basis.Lb


def _row(element, case, ratio, lim):
    return {"element": element, "b4_case": case, "ratio": ratio, "lambda_p": lim["lambda_p"],
            "lambda_r": lim["lambda_r"], "class": eq.classify(ratio, lim)}


def _i_major(case, section, basis, E, Fy):
    channel = section.type.upper() == "CHANNEL"
    ratio_field = "b_t_ratio" if channel else "bf_2tf_ratio"   # B4.1b: full flange (channel), bf/2 (I)
    _require(section, ratio_field, "h_tw_ratio", "sx", "zx", "ry", "iy", "j", "ho")
    flange, web = getattr(section, ratio_field), section.h_tw_ratio
    lf, lw = eq.limits(10, E, Fy), eq.limits(15, E, Fy)
    rows = [_row("flange", 10, flange, lf), _row("web", 15, web, lw)]
    if rows[1]["class"] != "compacto":
        _blocked("Alma no compacta o esbelta: requiere F4/F5, no implementadas en esta etapa.", section, h_tw=web)
    flange_class = rows[0]["class"]
    if channel and flange_class != "compacto":
        _blocked("Canal con ala no compacta: F2 exige alas compactas y el Capítulo F no tiene otra sección para "
                 "canales en el eje mayor.", section, b_t=flange)
    if section.cw is None:
        _incomplete("El pandeo lateral-torsional (F2.2) requiere Cw.", section, ["section.cw"])
    provision = "F2" if flange_class == "compacto" else "F3"
    modes = {}
    if provision == "F2":
        modes["Y"] = _evaluated("Y", "F2.1", eq.f2_plastic(Fy=Fy, Zx=section.zx))
        modes["FLB"] = _not_applicable("FLB", "F2", "Ala compacta: el pandeo local del ala no aplica (F2).")
    else:
        modes["Y"] = _not_applicable("Y", "F3", "F3 no incluye fluencia como estado límite; Mn ≤ Mp por F2.2 y F3.2.")
        modes["FLB"] = _evaluated("FLB", "F3.2", eq.f3_flb(E=E, Fy=Fy, Sx=section.sx, Zx=section.zx, bf_2tf=flange,
                                                           h_tw=web, lim=lf))
    ltb = eq.f2_ltb(E=E, Fy=Fy, Sx=section.sx, Zx=section.zx, ry=section.ry, Iy=section.iy, Cw=section.cw,
                    J=section.j, ho=section.ho, Lb=_lb(basis, section), Cb=basis.Cb, channel=channel)
    modes["LTB"] = _ltb_mode(ltb, "F2.2")
    modes["TFR"] = _tension_flange(case, section, basis, Fy)
    return provision, rows, modes


def _tension_flange(case, section, basis, Fy):
    if basis.tension_flange_holes is None:
        _incomplete("F13.1: declare si el ala traccionada tiene agujeros (flexure.tension_flange_holes).", section,
                    ["flexure.tension_flange_holes"])
    if not basis.tension_flange_holes:
        return _not_applicable("TFR", "F13.1", "Declarado sin agujeros en el ala traccionada.")
    if case.material.Fu is None:
        _incomplete("F13.1 requiere Fu.", section, ["material.Fu"])
    _require(section, "bf", "tf", "sx")
    afg = section.bf * section.tf
    if basis.Afn > afg:
        _blocked("Afn no puede superar el área bruta del ala Afg = bf·tf.", section, Afn=basis.Afn, Afg=afg)
    out = eq.f13_tension_flange(Fy=Fy, Fu=case.material.Fu, Afg=afg, Afn=basis.Afn, Sx=section.sx)
    if not out["applies"]:
        return _not_applicable("TFR", "F13.1", out["reason"], **{k: v for k, v in out.items() if k not in {"applies", "reason"}})
    return _evaluated("TFR", "F13.1", {k: v for k, v in out.items() if k != "applies"})


def _i_minor(case, section, basis, E, Fy):
    channel = section.type.upper() == "CHANNEL"
    ratio_field = "b_t_ratio" if channel else "bf_2tf_ratio"   # F6: full flange (channel), bf/2 (I)
    _require(section, ratio_field, "sy", "zy")
    ratio = getattr(section, ratio_field)
    lim = eq.limits(13, E, Fy)
    rows = [_row("flange", 13, ratio, lim)]
    modes = {"Y": _evaluated("Y", "F6.1", eq.f6_plastic(Fy=Fy, Zy=section.zy, Sy=section.sy))}
    if rows[0]["class"] == "compacto":
        modes["FLB"] = _not_applicable("FLB", "F6.2(a)", "Ala compacta: el pandeo local del ala no aplica.")
    else:
        modes["FLB"] = _evaluated("FLB", "F6.2", eq.f6_flb(E=E, Fy=Fy, Zy=section.zy, Sy=section.sy, b_t=ratio, lim=lim))
    return "F6", rows, modes


def _rect_hss(case, section, basis, E, Fy, axis):
    _require(section, "b_tdes_ratio", "h_tdes_ratio", "tdes", "area", "h_out", "b_out")
    if axis == "x":
        flange, web, S, Z, inertia, depth, width = "b_tdes_ratio", "h_tdes_ratio", "sx", "zx", "ix", "h_out", "b"
    else:
        flange, web, S, Z, inertia, depth, width = "h_tdes_ratio", "b_tdes_ratio", "sy", "zy", "iy", "b_out", "h"
    _require(section, S, Z, inertia, width)
    S, Z, inertia, depth = getattr(section, S), getattr(section, Z), getattr(section, inertia), getattr(section, depth)
    lf, lw = eq.limits(17, E, Fy), eq.limits(19, E, Fy)
    bf_t, hw_t = getattr(section, flange), getattr(section, web)
    rows = [_row("flange", 17, bf_t, lf), _row("web", 19, hw_t, lw)]
    modes = {"Y": _evaluated("Y", "F7.1", eq.f7_plastic(Fy=Fy, Z=Z))}
    if rows[0]["class"] == "compacto":
        modes["FLB"] = _not_applicable("FLB", "F7.2(a)", "Ala compacta: el pandeo local del ala no aplica.")
    elif rows[0]["class"] == "no compacto":
        modes["FLB"] = _evaluated("FLB", "F7.2(b)", eq.f7_flb(Fy=Fy, S=S, Z=Z, b_t=bf_t, lim=lf))
    else:
        b, t = getattr(section, width), section.tdes   # B4.1b(d): flat width, design thickness
        be = eq.f7_effective_width(E=E, Fy=Fy, b=b, t=t)
        se = eq.effective_section_modulus(inertia=inertia, A=section.area, depth=depth, t=t, b=b, be=be["be_mm"])
        out = eq.f7_flb(Fy=Fy, S=S, Z=Z, b_t=bf_t, lim=lf, Se=se["Se"])
        modes["FLB"] = _evaluated("FLB", "F7.2(c)", {**out, "b_mm": b, "t_mm": t, "be_mm": be["be_mm"],
                                                     "be_equation": be["equation"], **se})
    if rows[1]["class"] == "compacto":
        modes["WLB"] = _not_applicable("WLB", "F7.3(a)", "Alma compacta: el pandeo local del alma no aplica.")
    elif rows[1]["class"] == "no compacto":
        modes["WLB"] = _evaluated("WLB", "F7.3(b)", eq.f7_wlb(Fy=Fy, S=S, Z=Z, h_t=hw_t, lim=lw))
    else:
        _blocked("Alma esbelta en PTE (F7-7): no implementada; ningún PTE estándar tiene alma esbelta.", section)
    if axis == "y" or section.h_out <= section.b_out:
        modes["LTB"] = _not_applicable("LTB", "F7.4", "Flexión respecto del eje menor o sección cuadrada: el pandeo "
                                                      "lateral-torsional no ocurre (Nota de F7.4).")
    else:
        _require(section, "ry", "j", "sx", "zx")
        modes["LTB"] = _ltb_mode(eq.f7_ltb(E=E, Fy=Fy, Sx=section.sx, Zx=section.zx, ry=section.ry, J=section.j,
                                           Ag=section.area, Lb=_lb(basis, section), Cb=basis.Cb), "F7.4")
    return "F7", rows, modes


def _round_hss(case, section, basis, E, Fy, axis):
    _require(section, "d_t_ratio", "sx" if axis == "x" else "sy", "zx" if axis == "x" else "zy")
    S = section.sx if axis == "x" else section.sy
    Z = section.zx if axis == "x" else section.zy
    dt = section.d_t_ratio
    if dt >= 0.45 * E / Fy:
        _blocked("F8 se aplica solo con D/t < 0.45E/Fy.", section, D_t=dt)
    lim = eq.limits(20, E, Fy)
    rows = [_row("wall", 20, dt, lim)]
    modes = {"Y": _evaluated("Y", "F8.1", eq.f8_plastic(Fy=Fy, Z=Z))}
    if rows[0]["class"] == "compacto":
        modes["LB"] = _not_applicable("LB", "F8.2(a)", "Sección compacta: el pandeo local no aplica.")
    else:
        modes["LB"] = _evaluated("LB", "F8.2", eq.f8_local_buckling(E=E, Fy=Fy, S=S, D_t=dt, lim=lim))
    modes["LTB"] = _not_applicable("LTB", "F8", "Los PTE redondos no presentan pandeo lateral-torsional (F8).")
    return "F8", rows, modes


def _solid(case, section, basis, E, Fy, axis):
    round_bar = section.type.upper() == "SOLID_CIRCULAR"
    S = section.sx if axis == "x" else section.sy
    Z = section.zx if axis == "x" else section.zy
    _require(section, "sx" if axis == "x" else "sy", "zx" if axis == "x" else "zy")
    modes = {"Y": _evaluated("Y", "F11.1", eq.f11_plastic(Fy=Fy, Z=Z, S=S, round_bar=round_bar))}
    if round_bar:
        modes["LTB"] = _not_applicable("LTB", "F11.2(a)", "Barras redondas: el pandeo lateral-torsional no aplica.")
        return "F11", [], modes
    _require(section, "h", "b")
    depth, width = (section.h, section.b) if axis == "x" else (section.b, section.h)
    if depth <= width:
        modes["LTB"] = _not_applicable("LTB", "F11.2(a)", "Barra rectangular en su eje menor: el pandeo "
                                                          "lateral-torsional no aplica.")
    else:
        modes["LTB"] = _ltb_mode(eq.f11_ltb(E=E, Fy=Fy, S=S, Z=Z, d=depth, t=width, Lb=_lb(basis, section),
                                            Cb=basis.Cb), "F11.2")
    return "F11", [], modes


def flexure_strength(case: SteelCase, section: Section, axis: str) -> dict:
    """Nominal and design flexural strength about one axis ("x" or "y")."""
    family = section.type.upper()
    E, Fy = case.material.E, case.material.Fy
    basis = case.flexure or FlexureBasis()
    if abs(E - eq.E_STEEL) > 1e-6:
        _incomplete("El Capítulo F usa E = 200000 MPa.", section, ["material.E"])
    if family in {"SINGLE_ANGLE", "DOUBLE_ANGLE"}:
        _blocked("Flexión de ángulos (F9/F10): prevista para la etapa 2 del Capítulo F.", section)
    if family in {"W", "CHANNEL"}:
        provision, rows, modes = (_i_major if axis == "x" else _i_minor)(case, section, basis, E, Fy)
    elif family == "RECTANGULAR_HSS":
        provision, rows, modes = _rect_hss(case, section, basis, E, Fy, axis)
    elif family == "CIRCULAR_HSS":
        provision, rows, modes = _round_hss(case, section, basis, E, Fy, axis)
    elif family in {"SOLID_RECTANGULAR", "SOLID_CIRCULAR"}:
        provision, rows, modes = _solid(case, section, basis, E, Fy, axis)
    else:
        _blocked("El Capítulo F no está implementado para esta familia.", section)

    evaluated = {k: m for k, m in modes.items() if m["applies"]}
    governing = min(evaluated, key=lambda k: evaluated[k]["Mn"])
    gov = evaluated[governing]
    notes = [f"Cb = {basis.Cb:g}" + (" (dato del usuario)." if case.flexure and "Cb" in case.flexure.model_fields_set
                                      else " (valor por defecto, límite inferior de F1-1).")]
    return {
        "chapter": "F", "code": "ANSI/AISC 360-22", "axis": axis,
        "section": section.name, "family": family,
        "inputs": {"Fy_mpa": Fy, "E_mpa": E, "Lb_mm": basis.Lb, "Cb": basis.Cb,
                   "tension_flange_holes": basis.tension_flange_holes, "Afn_mm2": basis.Afn},
        "classification": {"elements": rows, "reference": "B4.1b (Tabla B4.1b)"},
        "provisions": ["F1", provision] + (["F13.1"] if "TFR" in modes else []),
        "modes": modes,
        "governing_mode": governing,
        "governing_equation": gov["equation"],
        "Mn_kNm": gov["Mn_kNm"],
        "phi_b": eq.PHI_B,
        "available_kNm": gov["design_kNm"],
        "requirements": [],
        "notes": notes,
        "limitations": list(_LIMITATIONS),
    }
