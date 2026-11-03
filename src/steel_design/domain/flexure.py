"""Chapter F for one member and one bending axis: classification, selection, limit states. LRFD.

Families: rolled and welded built-up I-shapes (F2 to F6), compact channels (F2, F6), rectangular HSS (F7), round HSS (F8),
solid bars (F11), double angles in the plane of symmetry (F9) and single angles (F10, geometric
or principal axes), plus F13.1 for I-shapes and channels about x.
Every limit state of the selected section is reported, either evaluated or with the
reason it does not apply; the governing one is the lowest Mn. Formulas live in
codes/aisc_360_22/flexure.py. Missing data or decisions raise structured errors.
"""
from collections.abc import Callable

from ..codes.aisc_360_22 import appendix_4 as a4
from ..codes.aisc_360_22 import flexure as eq
from ..codes.aisc_360_22.constants import is_standard_modulus
from ..errors import blocking_error, incomplete_error
from ..models import FlexureBasis, SteelCase
from ..sections.geometry import i_major_properties, singly_symmetric_i
from ..sections.identity import double_angle_label
from ..sections.models import Section, missing_properties
from .fire import SLENDER_BLOCK, steel_at_temperature, with_fire

_LIMITATIONS = (
    "Lb sale de las longitudes (DF-13) y Cb es dato del usuario; Cb = 1.0 si no se indica (límite inferior de F1-1). Se supone "
    "que los apoyos "
    "restringen la rotación respecto del eje longitudinal (F1(b)).",
    "Flexión respecto de un eje: la flexión biaxial y la combinación con carga axial se verifican en el chequeo de "
    "interacción (Capítulo H).",
)


_blocked = blocking_error("FLEXURE_DOMAIN_BLOCKED")


_incomplete = incomplete_error("FLEXURE_DATA_INCOMPLETE")


def _require(section, *names):
    missing = missing_properties(section, names)
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


def unbraced_length(case, axis):
    """Lb (DF-13): about x (and the major principal axis w), min(Ly, Lz); about y (and the minor principal axis z), min(Lx, Lz)."""
    if case.lengths is None:
        return None
    return min(case.lengths.Ly if axis in {"x", "w"} else case.lengths.Lx, case.lengths.Lz)


def _lb(case, section, axis):
    lb = unbraced_length(case, axis)
    if lb is None:
        _incomplete("El pandeo lateral-torsional requiere lengths (Lb sale de Lx, Ly y Lz).", section, ["lengths"])
    return lb


def _row(element, case, ratio, lim):
    return {"element": element, "b4_case": case, "ratio": ratio, "lambda_p": lim["lambda_p"],
            "lambda_r": lim["lambda_r"], "class": eq.classify(ratio, lim)}


def _channel_major(case, section, basis, E, Fy):
    _require(section, "b_t_ratio", "h_tw_ratio", "sx", "zx", "ry", "iy", "j", "ho")   # B4.1b: full flange of a channel
    flange, web = section.b_t_ratio, section.h_tw_ratio
    lf, lw = eq.limits(10, case.material.E, case.material.Fy), eq.limits(15, case.material.E, case.material.Fy)
    rows = [_row("flange", 10, flange, lf), _row("web", 15, web, lw)]
    if rows[1]["class"] != "compacto":
        _blocked("Canal con alma no compacta o esbelta: F4 y F5 tratan secciones I y el Capítulo F no tiene otra sección "
                 "para canales en el eje mayor.", section, h_tw=web)
    if rows[0]["class"] != "compacto":
        _blocked("Canal con ala no compacta: F2 exige alas compactas y el Capítulo F no tiene otra sección para "
                 "canales en el eje mayor.", section, b_t=flange)
    provision, modes = _f2_f3(case, section, basis, E, Fy, rows[0], lf)
    modes["TFR"] = _tension_flange(case, section, basis, Fy, None)
    return provision, rows, modes


def _i_major(case, section, basis, E, Fy):
    """Doubly symmetric I with a compact web: F2 or F3. Noncompact web or singly symmetric: F4. Slender web: F5."""
    built_up = section.type.upper() == "I_BUILT_UP"
    if built_up:
        _require(section, "d", "tw", "bf", "tf", "bf_bottom", "tf_bottom", "h_tw_ratio", "sx", "zx", "ry", "iy", "j", "ho")
    else:
        _require(section, "bf_2tf_ratio", "h_tw_ratio", "sx", "zx", "ry", "iy", "j", "ho")   # B4.1b: bf/2 of an I
    singly = singly_symmetric_i(section)
    if singly and basis.compression_flange is None:
        _incomplete("I de alas distintas: indique el ala comprimida en esta combinación (flexure.compression_flange).", section,
                    ["flexure.compression_flange"])
    Ea, Fya = case.material.E, case.material.Fy
    props = i_major_properties(section, basis.compression_flange) if built_up else {}   # singly symmetric implies built-up
    if singly:
        lw = eq.limits_singly_symmetric_web(E=Ea, Fy=Fya, hc=props["hc"], hp=props["hp"], Mp=Fya * props["Zx"],
                                            My=Fya * min(props["Sxc"], props["Sxt"]))
        web_row = _row("web", 16, props["hc"] / props["tw"], lw)
    else:
        lw = eq.limits(15, Ea, Fya)
        web_row = _row("web", 15, section.h_tw_ratio, lw)
    if built_up:   # Table B4.1b note [b]: FL = 0.7Fy with a slender web, else F4-6
        fl = 0.7 * Fya if web_row["class"] == "esbelto" else eq.f4_fl(Fy=Fya, Sxc=props["Sxc"], Sxt=props["Sxt"])["FL_mpa"]
        lf = eq.limits_built_up_flange(E=Ea, Fy=Fya, kc=eq.flange_kc(h_tw=section.h_tw_ratio), FL=fl)
        rows = [_row("flange", 11, props["bfc"] / (2 * props["tfc"]), lf), web_row]
    else:
        lf = eq.limits(10, Ea, Fya)
        rows = [_row("flange", 10, section.bf_2tf_ratio, lf), web_row]
    if not singly and web_row["class"] == "compacto":
        provision, modes = _f2_f3(case, section, basis, E, Fy, rows[0], lf)
    else:
        if not built_up:
            _require(section, "bf", "tf", "tw")
            props = i_major_properties(section, None)
        provision, modes = _f4_f5(case, section, basis, E, Fy, props, rows, lf, lw)
    modes["TFR"] = _tension_flange(case, section, basis, Fy, props)
    return provision, rows, modes


def _f2_f3(case, section, basis, E, Fy, flange_row, lf):
    """F2 (compact flange) or F3: doubly symmetric I-shapes and channels with compact webs."""
    channel = section.type.upper() == "CHANNEL"
    if section.cw is None:
        _incomplete("El pandeo lateral-torsional (F2.2) requiere Cw.", section, ["section.cw"])
    flange_class = flange_row["class"]
    provision = "F2" if flange_class == "compacto" else "F3"
    modes = {}
    if provision == "F2":
        modes["Y"] = _evaluated("Y", "F2.1", eq.f2_plastic(Fy=Fy, Zx=section.zx))
        modes["FLB"] = _not_applicable("FLB", "F2", "Ala compacta: el pandeo local del ala no aplica (F2).")
    else:
        modes["Y"] = _not_applicable("Y", "F3", "F3 no incluye fluencia como estado límite; Mn ≤ Mp por F2.2 y F3.2.")
        modes["FLB"] = _evaluated("FLB", "F3.2", eq.f3_flb(E=E, Fy=Fy, Sx=section.sx, Zx=section.zx, bf_2tf=flange_row["ratio"],
                                                           h_tw=section.h_tw_ratio, lim=lf))
    ltb = eq.f2_ltb(E=E, Fy=Fy, Sx=section.sx, Zx=section.zx, ry=section.ry, Iy=section.iy, Cw=section.cw,
                    J=section.j, ho=section.ho, Lb=_lb(case, section, "x"), Cb=basis.Cb, channel=channel)
    modes["LTB"] = _ltb_mode(ltb, "F2.2")
    hot = steel_at_temperature(case)
    if hot and section.type.upper() == "W" and flange_class == "compacto":   # A-4-13: compact rolled wide-flange shapes
        modes["Y"] = _evaluated("Y", "F2.1", a4.plastic_moment(Fy_T=Fy, Zx=section.zx))
        modes["LTB"] = _evaluated(
            "LTB",
            "F2.2",
            a4.ltb(
                E_T=E,
                Fy=case.material.Fy,
                kp=hot["kp"],
                ky=hot["ky"],
                T=hot["T_C"],
                Sx=section.sx,
                Zx=section.zx,
                J=section.j,
                c=1.0,
                ho=section.ho,
                rts=eq.f2_rts(Iy=section.iy, Cw=section.cw, Sx=section.sx),
                Lb=_lb(case, section, "x"),
                Cb=basis.Cb,
            ),
        )
    return provision, modes


def _f4_f5(case, section, basis, E, Fy, props, rows, lf, lw):
    """F4 (compact or noncompact web) or F5 (slender web): CFY, LTB, FLB and TFY referred to the compression flange."""
    flange_row, web_row = rows
    sxc, sxt = props["Sxc"], props["Sxt"]
    hc_tw, h_tw, iyc_iy = props["hc"] / props["tw"], props["h"] / props["tw"], props["Iyc"] / props["Iy"]
    kc = eq.flange_kc(h_tw=h_tw)
    rt = eq.f4_rt(bfc=props["bfc"], tfc=props["tfc"], hc=props["hc"], tw=props["tw"])
    lb = _lb(case, section, "x")
    flange_compact = flange_row["class"] == "compacto"
    modes = {}
    if web_row["class"] != "esbelto":
        provision = "F4"
        fl = eq.f4_fl(Fy=Fy, Sxc=sxc, Sxt=sxt)
        rpc = eq.f4_rpc(Fy=Fy, Zx=props["Zx"], Sxc=sxc, hc_tw=hc_tw, Iyc_Iy=iyc_iy, lim=lw)
        modes["CFY"] = _evaluated("CFY", "F4.1", {"Mn": rpc["Rpc"] * rpc["Myc"], "equation": "F4-1", **rpc, "Sxc": sxc,
                                                  "Iyc_Iy": iyc_iy, "hc_mm": props["hc"]})
        ltb = eq.f4_ltb(E=E, Fy=Fy, FL=fl["FL_mpa"], Rpc=rpc["Rpc"], Sxc=sxc, rt=rt["rt_mm"], J=props["J"], ho=props["ho"],
                        Iyc_Iy=iyc_iy, Lb=lb, Cb=basis.Cb)
        modes["LTB"] = _ltb_mode({**ltb, "FL_equation": fl["equation"], "aw": rt["aw"], "Rpc": rpc["Rpc"]}, "F4.2")
        if flange_compact:
            modes["FLB"] = _not_applicable("FLB", "F4.3(a)", "Ala comprimida compacta: el pandeo local del ala no aplica.")
        else:
            out = eq.f4_flb(E=E, Fy=Fy, FL=fl["FL_mpa"], Rpc=rpc["Rpc"], Sxc=sxc, kc=kc, bfc_2tfc=flange_row["ratio"], lim=lf)
            modes["FLB"] = _evaluated("FLB", "F4.3", {**out, "Rpc": rpc["Rpc"], "Sxc": sxc})
        if sxt >= sxc:
            modes["TFY"] = _not_applicable("TFY", "F4.4(a)", "Sxt ≥ Sxc: la fluencia del ala traccionada no aplica.", Sxc=sxc, Sxt=sxt)
        else:
            rpt = eq.f4_rpt(Fy=Fy, Zx=props["Zx"], Sxt=sxt, hc_tw=hc_tw, h_tw=h_tw, Iyc_Iy=iyc_iy, lim=lw)
            modes["TFY"] = _evaluated("TFY", "F4.4", {"Mn": rpt["Rpt"] * rpt["Myt"], "equation": "F4-15", **rpt, "Sxt": sxt})
        return provision, modes
    rpg = eq.f5_rpg(aw=rt["aw"], hc_tw=hc_tw, E=E, Fy=Fy)
    modes["CFY"] = _evaluated("CFY", "F5.1", {"Mn": rpg["Rpg"] * Fy * sxc, "equation": "F5-1", **rpg, "aw": rt["aw"], "Sxc": sxc})
    ltb = eq.f5_ltb(E=E, Fy=Fy, Rpg=rpg["Rpg"], Sxc=sxc, rt=rt["rt_mm"], Lb=lb, Cb=basis.Cb)
    modes["LTB"] = _ltb_mode({**ltb, "Rpg": rpg["Rpg"]}, "F5.2")
    if flange_compact:
        modes["FLB"] = _not_applicable("FLB", "F5.3(a)", "Ala comprimida compacta: el pandeo local del ala no aplica.")
    else:
        out = eq.f5_flb(E=E, Fy=Fy, Rpg=rpg["Rpg"], Sxc=sxc, kc=kc, bfc_2tfc=flange_row["ratio"], lim=lf)
        modes["FLB"] = _evaluated("FLB", "F5.3", {**out, "Rpg": rpg["Rpg"], "Sxc": sxc})
    if sxt >= sxc:
        modes["TFY"] = _not_applicable("TFY", "F5.4(a)", "Sxt ≥ Sxc: la fluencia del ala traccionada no aplica.", Sxc=sxc, Sxt=sxt)
    else:
        modes["TFY"] = _evaluated("TFY", "F5.4", {"Mn": Fy * sxt, "equation": "F5-10", "Sxt": sxt})
    return "F5", modes


def _tension_flange(case, section, basis, Fy, props):
    if basis.tension_flange_holes is None:
        _incomplete("F13.1: declare si el ala traccionada tiene agujeros (flexure.tension_flange_holes).", section,
                    ["flexure.tension_flange_holes"])
    if not basis.tension_flange_holes:
        return _not_applicable("TFR", "F13.1", "Declarado sin agujeros en el ala traccionada.")
    if case.material.Fu is None:
        _incomplete("F13.1 requiere Fu.", section, ["material.Fu"])
    _require(section, "bf", "tf", "sx")
    afg = props["bft"] * props["tft"] if props else section.bf * section.tf     # the tension flange; Sx is the minimum (F13.1)
    if basis.Afn > afg:
        _blocked("Afn no puede superar el área bruta del ala traccionada Afg = bf·tf.", section, Afn=basis.Afn, Afg=afg)
    hot = steel_at_temperature(case)
    out = eq.f13_tension_flange(Fy=Fy, Fu=hot["Fu_T_mpa"] if hot else case.material.Fu, Afg=afg, Afn=basis.Afn, Sx=section.sx)
    if not out["applies"]:
        return _not_applicable("TFR", "F13.1", out["reason"], **{k: v for k, v in out.items() if k not in {"applies", "reason"}})
    return _evaluated("TFR", "F13.1", {k: v for k, v in out.items() if k != "applies"})


def _i_minor(case, section, basis, E, Fy):
    lim = eq.limits(13, case.material.E, case.material.Fy)
    family = section.type.upper()
    if family == "I_BUILT_UP":
        _require(section, "bf", "tf", "bf_bottom", "tf_bottom", "sy", "zy")
        rows = [_row("top_flange", 13, section.bf / (2 * section.tf), lim),
                _row("bottom_flange", 13, section.bf_bottom / (2 * section.tf_bottom), lim)]
    else:
        ratio_field = "b_t_ratio" if family == "CHANNEL" else "bf_2tf_ratio"   # F6: full flange (channel), bf/2 (I)
        _require(section, ratio_field, "sy", "zy")
        rows = [_row("flange", 13, getattr(section, ratio_field), lim)]
    ratio = max(row["ratio"] for row in rows)        # unequal flanges: the more slender one (decision DF-19)
    modes = {"Y": _evaluated("Y", "F6.1", eq.f6_plastic(Fy=Fy, Zy=section.zy, Sy=section.sy))}
    if all(row["class"] == "compacto" for row in rows):
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
    lf, lw = eq.limits(17, case.material.E, case.material.Fy), eq.limits(19, case.material.E, case.material.Fy)
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
    if depth <= (section.b_out if axis == "x" else section.h_out):
        modes["LTB"] = _not_applicable("LTB", "F7.4", "Flexión respecto del eje menor o sección cuadrada: el pandeo "
                                                      "lateral-torsional no ocurre (Nota de F7.4).")
    else:                                           # the major axis is y in a box wider than deep (DF-14)
        minor_radius = "ry" if axis == "x" else "rx"
        _require(section, minor_radius, "j")
        modes["LTB"] = _ltb_mode(eq.f7_ltb(E=E, Fy=Fy, Sx=S, Zx=Z, ry=getattr(section, minor_radius), J=section.j,
                                           Ag=section.area, Lb=_lb(case, section, axis), Cb=basis.Cb), "F7.4")
    return "F7", rows, modes


def _round_hss(case, section, basis, E, Fy, axis):
    _require(section, "d_t_ratio", "sx" if axis == "x" else "sy", "zx" if axis == "x" else "zy")
    S = section.sx if axis == "x" else section.sy
    Z = section.zx if axis == "x" else section.zy
    dt = section.d_t_ratio
    if dt >= 0.45 * case.material.E / case.material.Fy:
        _blocked("F8 se aplica solo con D/t < 0.45E/Fy.", section, D_t=dt)
    lim = eq.limits(20, case.material.E, case.material.Fy)
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
        modes["LTB"] = _ltb_mode(eq.f11_ltb(E=E, Fy=Fy, S=S, Z=Z, d=depth, t=width, Lb=_lb(case, section, axis),
                                            Cb=basis.Cb), "F11.2")
    return "F11", [], modes


def _angle_data(case, section, field):
    af = case.angle_flexure
    value = getattr(af, field) if af else None
    if value is None:
        _incomplete(f"Indique angle_flexure.{field} para esta combinación (qué parte del ángulo está comprimida).",
                    section, [f"angle_flexure.{field}"])
    return value


def _leg_local(name, provision, b, t, Sc, E, Fy, lim, **extra):
    row = _row(name, 12, b / t, lim)
    if row["class"] == "compacto":
        return row, _not_applicable("LLB", provision, f"{name}: ala compacta, el pandeo local no aplica.",
                                    b_mm=b, t_mm=t, **extra)
    out = eq.f10_leg_local(E=E, Fy=Fy, Sc=Sc, b_t=b / t, lim=lim)
    return row, _evaluated("LLB", provision, {**out, "b_mm": b, "t_mm": t, "Sc": Sc, **extra})


def _double_angle(case, section, basis, E, Fy, axis, catalog):
    if axis != "x":
        _blocked("F9 cubre ángulos dobles cargados en su plano de simetría (flexión respecto de x); la flexión "
                 "respecto del eje de simetría no está cubierta por el Capítulo F.", section, axis=axis)
    web_legs = _angle_data(case, section, "web_legs")
    if catalog is None:
        _blocked("El ángulo doble necesita el catálogo para leer J de su ángulo componente.", section)
    label = double_angle_label(section.name)
    _require(section, "d", "b", "t", "zx", "sx", "ix", "iy", "ry", "y")
    component = catalog(label["component"])
    _require(component, "j")
    long_leg, short_leg = max(section.d, section.b), min(section.d, section.b)
    if long_leg != short_leg and label["configuration"] is None:
        _blocked("Ángulo doble desigual sin LLBB/SLBB: no se puede identificar el ala vertical.", section)
    web = short_leg if label["configuration"] == "SLBB" else long_leg       # legs in the plane of symmetry
    flange = short_leg if web == long_leg and long_leg != short_leg else long_leg
    t, j = section.t, 2 * component.j                                        # J of both angles
    lim = eq.limits(12, case.material.E, case.material.Fy)
    s_flange = section.ix / section.y                                        # to the back of the flange legs
    modes = {"Y": _evaluated("Y", "F9.1", eq.f9_plastic(Fy=Fy, Zx=section.zx, Sx=section.sx, web_legs=web_legs))}
    ltb = eq.f9_ltb(E=E, Fy=Fy, Zx=section.zx, Sx=section.sx, ry=section.ry, Iy=section.iy, J=j, d=web,
                    Lb=_lb(case, section, axis), web_legs=web_legs)
    modes["LTB"] = _ltb_mode({**ltb, "J_mm4": j, "d_web_leg_mm": web}, "F9.2")
    flange_row, flb = _leg_local("flange_legs", "F9.3(b) → F10.3", flange, t, s_flange, E, Fy, lim)
    web_row, wlb = _leg_local("web_legs", "F9.4(b) → F10.3", web, t, section.sx, E, Fy, lim)
    flb["limit_state"], wlb["limit_state"] = "FLB", "WLB"
    if web_legs == "tension":
        modes["FLB"] = flb
        modes["WLB"] = _not_applicable("WLB", "F9.4", "Alas verticales en tracción: su pandeo local no aplica.")
    else:
        modes["FLB"] = _not_applicable("FLB", "F9.3", "Alas horizontales en tracción: su pandeo local no aplica.")
        modes["WLB"] = wlb
    return "F9", [flange_row, web_row], modes


def _single_angle(case, section, basis, E, Fy, axis):
    _require(section, "d", "b", "t", "area")
    long_leg, short_leg, t = max(section.d, section.b), min(section.d, section.b), section.t
    equal = long_leg == short_leg
    lim = eq.limits(12, case.material.E, case.material.Fy)
    restraint = basis.lateral_torsional_restraint
    rows = [_row("long_leg", 12, long_leg / t, lim), _row("short_leg", 12, short_leg / t, lim)]
    if axis in {"x", "y"}:
        if restraint is None:
            _incomplete("Ángulo simple en ejes geométricos: indique flexure.lateral_torsional_restraint.",
                        section, ["flexure.lateral_torsional_restraint"])
        if not equal and restraint != "continuous":
            _blocked("Ángulo de alas desiguales sin restricción lateral-torsional continua: F10 exige ejes "
                     "principales (use Mw o Mz).", section)
        if restraint != "continuous" and case.Pu > 0:
            _blocked("F10.2(2) (ejes geométricos) solo aplica sin compresión axial.", section)
        toe = _angle_data(case, section, "toe")
        _require(section, "ix" if axis == "x" else "iy", "x", "y")
        # Catalog orientation: the long leg is parallel to y. For bending about x the leg perpendicular to the
        # axis is the long (vertical) leg; about y, the short (horizontal) leg.
        inertia = section.ix if axis == "x" else section.iy
        perp, par, centroid = ((long_leg, short_leg, section.y) if axis == "x" else (short_leg, long_leg, section.x))
        s_toe, s_face = inertia / (perp - centroid), inertia / centroid
        # F10.2(2)(i): without restraint, 0.80 reduces My of LTB and Sc of LLB, not F10-1 yielding (DF-11)
        factor = 0.80 if restraint == "none" else 1.0
        my = factor * Fy * s_toe
        provision = "F10 (ejes geométricos)"
        modes = {"Y": _evaluated("Y", "F10.1", eq.f10_plastic(My=Fy * s_toe))}
        if restraint == "continuous":
            modes["LTB"] = _not_applicable("LTB", "F10.2", "Restricción lateral-torsional continua: el pandeo "
                                                           "lateral-torsional no aplica.")
        else:
            mcr = eq.f10_mcr_geometric(E=E, b=long_leg, t=t, Lb=_lb(case, section, axis), Cb=basis.Cb, toe=toe)
            scale = 1.25 if restraint == "at_max_moment" else 1.0    # F10.2(2)(ii)
            out = eq.f10_from_mcr(My=my, Mcr=scale * mcr["Mcr"])
            modes["LTB"] = _evaluated("LTB", "F10.2(2)", {**out, "Mcr": scale * mcr["Mcr"], "Mcr_factor": scale,
                                                          "Mcr_equation": mcr["Mcr_equation"], "My": my, "My_factor": factor,
                                                          "Lb_mm": unbraced_length(case, axis), "Cb": basis.Cb})
        if toe == "compression":
            _, modes["LLB"] = _leg_local("perp_leg", "F10.3", perp, t, factor * s_toe, E, Fy, lim)
        else:
            _, modes["LLB"] = _leg_local("par_leg", "F10.3", par, t, factor * s_face, E, Fy, lim,
                                         note="toe in tension: the leg parallel to the axis is compressed")
        return provision, rows, modes
    if axis == "w":
        _require(section, "rz", "sw_a", "sw_c")
        leg = "long" if equal else _angle_data(case, section, "leg_in_compression")
        sc = section.sw_c if leg == "long" else section.sw_a     # C: long-leg toe, A: short-leg toe
        my = Fy * min(v for v in (section.sw_a, section.sw_b, section.sw_c) if v)
        modes = {"Y": _evaluated("Y", "F10.1", eq.f10_plastic(My=my))}
        if restraint == "continuous":
            modes["LTB"] = _not_applicable("LTB", "F10.2", "Restricción lateral-torsional continua: el pandeo "
                                                           "lateral-torsional no aplica.")
        else:
            if equal:
                beta = 0.0
            elif section.beta_w is None:
                _incomplete("Ángulo de alas desiguales: F10-4 requiere βw del catálogo.", section, ["section.beta_w"])
            else:
                beta = section.beta_w if leg == "short" else -section.beta_w   # + short legs in compression
            mcr = eq.f10_mcr_principal(E=E, Ag=section.area, rz=section.rz, t=t, Lb=_lb(case, section, axis),
                                       Cb=basis.Cb, beta_w=beta)
            out = eq.f10_from_mcr(My=my, Mcr=mcr["Mcr"])
            modes["LTB"] = _evaluated("LTB", "F10.2(1)", {**out, **mcr, "My": my, "Lb_mm": unbraced_length(case, axis)})
        width = long_leg if leg == "long" else short_leg
        _, modes["LLB"] = _leg_local("long_leg" if leg == "long" else "short_leg", "F10.3", width, t, sc, E, Fy, lim)
        return "F10 (eje principal mayor w)", rows, modes
    if axis == "z":
        _require(section, "sz_a", "sz_b", "sz_c")
        toe = _angle_data(case, section, "toe")
        my = Fy * min(section.sz_a, section.sz_b, section.sz_c)
        modes = {"Y": _evaluated("Y", "F10.1", eq.f10_plastic(My=my)),
                 "LTB": _not_applicable("LTB", "F10", "Eje principal menor: solo fluencia y pandeo local del ala "
                                                      "(Nota de F10).")}
        if toe == "compression":
            candidates = [_leg_local("long_leg", "F10.3", long_leg, t, section.sz_c, E, Fy, lim)[1],
                          _leg_local("short_leg", "F10.3", short_leg, t, section.sz_a, E, Fy, lim)[1]]
            evaluated = [c for c in candidates if c["applies"]]
            modes["LLB"] = min(evaluated, key=lambda c: c["Mn"]) if evaluated else candidates[0]
        else:
            modes["LLB"] = _not_applicable("LLB", "F10.3", "Punteras en tracción: el pandeo local del ala no aplica.")
        return "F10 (eje principal menor z)", rows, modes
    _blocked("Eje de flexión no válido.", section, axis=axis)


def _notes(case, section, basis, axis, hot_instability):
    notes = [f"Cb = {basis.Cb:g}" + (" (dato del usuario)." if case.flexure and "Cb" in case.flexure.model_fields_set
                                      else " (valor por defecto, límite inferior de F1-1).")]
    if section.type.upper() == "I_BUILT_UP":
        notes.append("I armada soldada: propiedades de las placas sin radios de soldadura; J, Cw y centro de corte de pared delgada "
                     "(decisión DF-17).")
    if axis == "x" and singly_symmetric_i(section):
        notes.append(f"Ala comprimida: {'superior' if basis.compression_flange == 'top' else 'inferior'} (dato del usuario, "
                     "decisión DF-18).")
    if hot_instability:
        notes.append(
            "Apéndice 4, 4.2.4d(e): Capítulo F con E(T) y Fy(T). El Commentary advierte que esas ecuaciones pueden sobrestimar "
            "los modos de inestabilidad (decisión DA4-3)."
        )
    return notes


def flexure_strength(case: SteelCase, section: Section, axis: str,
                     catalog: Callable[[str], Section] | None = None) -> dict:
    """Nominal and design flexural strength about one axis: x, y (geometric) or w, z (single-angle principal)."""
    family = section.type.upper()
    E, Fy = case.material.E, case.material.Fy
    basis = case.flexure or FlexureBasis()
    if not is_standard_modulus(E):
        _incomplete("El Capítulo F usa E = 200000 MPa.", section, ["material.E"])
    hot = steel_at_temperature(case)
    if hot:                                  # The classification stays at ambient temperature (Commentary 4.2.4d): limits use case.material
        E, Fy = hot["E_T_mpa"], hot["Fy_T_mpa"]
    if axis in {"w", "z"} and family != "SINGLE_ANGLE":
        _blocked("Mw y Mz (ejes principales) solo se usan en ángulos simples; use Mux/Muy.", section)
    if family == "SINGLE_ANGLE":
        provision, rows, modes = _single_angle(case, section, basis, E, Fy, axis)
    elif family == "DOUBLE_ANGLE":
        provision, rows, modes = _double_angle(case, section, basis, E, Fy, axis, catalog)
    elif family == "CHANNEL" and axis == "x":
        provision, rows, modes = _channel_major(case, section, basis, E, Fy)
    elif family in {"W", "CHANNEL", "I_BUILT_UP"}:
        provision, rows, modes = (_i_major if axis == "x" else _i_minor)(case, section, basis, E, Fy)
    elif family == "RECTANGULAR_HSS":
        provision, rows, modes = _rect_hss(case, section, basis, E, Fy, axis)
    elif family == "CIRCULAR_HSS":
        provision, rows, modes = _round_hss(case, section, basis, E, Fy, axis)
    elif family in {"SOLID_RECTANGULAR", "SOLID_CIRCULAR"}:
        provision, rows, modes = _solid(case, section, basis, E, Fy, axis)
    else:
        _blocked("El Capítulo F no está implementado para esta familia.", section)
    if hot:
        if any(row["class"] == "esbelto" for row in rows):
            _blocked(SLENDER_BLOCK, section)
        modes = {k: {**m, "provision": f"{m['provision']}; Apéndice 4, 4.2.4d(e)"} for k, m in modes.items()}

    evaluated = {k: m for k, m in modes.items() if m["applies"]}
    governing = min(evaluated, key=lambda k: evaluated[k]["Mn"])
    gov = evaluated[governing]
    return with_fire({
        "chapter": "F", "code": "ANSI/AISC 360-22", "axis": axis,
        "section": section.name, "family": family,
        "inputs": {"Fy_mpa": case.material.Fy, "E_mpa": case.material.E, "Lb_mm": unbraced_length(case, axis), "Cb": basis.Cb,
                   "tension_flange_holes": basis.tension_flange_holes, "Afn_mm2": basis.Afn,
                   "lateral_torsional_restraint": basis.lateral_torsional_restraint,
                   **({"compression_flange": basis.compression_flange} if basis.compression_flange else {}),
                   "angle_flexure": case.angle_flexure.model_dump() if case.angle_flexure else None},
        "classification": {"elements": rows, "reference": "B4.1b (Tabla B4.1b)"},
        "provisions": ["F1", provision] + (["F13.1"] if "TFR" in modes else []),
        "modes": modes,
        "governing_mode": governing,
        "governing_equation": gov["equation"],
        "Mn_kNm": gov["Mn_kNm"],
        "phi_b": eq.PHI_B,
        "available_kNm": gov["design_kNm"],
        "requirements": [],
        "notes": _notes(case, section, basis, axis, hot and governing not in {"Y", "TFR", "CFY", "TFY"}
                        and not gov["equation"].startswith("A-4")),
        "limitations": list(_LIMITATIONS),
    }, hot, "4.2.4d(e)")
