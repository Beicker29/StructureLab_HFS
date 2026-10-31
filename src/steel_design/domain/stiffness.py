"""Section stiffnesses of a member, whatever its demands. They take no part in the strength. Units N, mm, MPa.

Elastic: E*A, E*I, G*J, E*Cw for bare steel; AISC Design Guide 6, Section 2.8 (not a standard) for filled and encased members.
Effective: Specification I1.5; only composite members. Direct analysis: reduced stiffnesses of C2.3 and I1.5, for when the program
carries out that analysis; tau_b is 1.0 in noncomposite members and a datum of the user in composite ones. A value that does not apply or that the program cannot calculate is an explicit row, so
that the report can say which of the two it is.
"""
import math
from typing import Callable

from ..codes.aisc_360_22 import composite as eq
from ..codes.aisc_360_22.compression import G_STEEL
from ..codes.aisc_dg06 import members as dg06_members
from ..errors import SteelDesignError
from ..models import SteelCase
from ..sections.identity import double_angle_label
from ..sections.models import Section
from .composite import _check_family, _compression_basis, _wall_geometry
from .speedcore import _c_wall_data

NO_APLICA, FALTA, SIN_DATO = "no_aplica", "falta_implementacion", "sin_dato"
C2_FACTOR, NONCOMPOSITE_TAU_B = 0.8, 1.0     # C2.3(a), C2.3(c)


def _value(symbol, dimension, value, source):
    if value is None:
        return _absent(symbol, SIN_DATO, "Sin dato en el catálogo.")
    return {"symbol": symbol, "dimension": dimension, "value": value, "source": source, "status": "calculada"}


def _absent(symbol, status, reason):
    return {"symbol": symbol, "status": status, "reason": reason}


def _times(factor, value):
    return factor * value if value is not None else None


def _bare_steel(case, section, catalog):
    E, j = case.material.E, section.j
    if section.type.upper() == "DOUBLE_ANGLE":
        j = 2 * catalog(double_angle_label(section.name)["component"]).j     # both angles, as in E6 and F9
    rows = [_value("EA", "EA", _times(E, section.area), "E·Ag; E de E3"), _value("EIx", "EI", _times(E, section.ix), "E·Ix; E de E3"),
            _value("EIy", "EI", _times(E, section.iy), "E·Iy; E de E3")]
    if section.type.upper() == "SINGLE_ANGLE":
        rows += [_value("EIw", "EI", _times(E, section.iw), "E·Iw; E de E3"), _value("EIz", "EI", _times(E, section.iz), "E·Iz; E de E3")]
    return rows + [_absent("GA", FALTA, "El programa no define el área de cortante para la rigidez elástica."),
                   _value("GJ", "GJ", _times(G_STEEL, j), "Gs·J; G de E4"), _value("ECw", "ECw", _times(E, section.cw), "E·Cw; E de E3")]


def _flexural_star(tau, symbol, value, source):
    """0.8*tau_b*EI (C2.3(a), (b))."""
    if tau is None:
        return _absent(symbol, SIN_DATO, "Requiere τb.")
    return _value(symbol, "EI", C2_FACTOR * tau * value, source)


def _tau_row(case, literal):
    if case.tau_b is None:
        return _absent("τb", SIN_DATO, f"Indique tau_b en la entrada ({literal}).")
    return _value("τb", "", case.tau_b, f"Dato del usuario; {literal}")


def _direct_steel(case, elastic, prefix=""):
    """C2.3: 0.8*tau_b on flexural stiffnesses and 0.8 on the others. tau_b = 1.0 always in noncomposite members (C2.3(c), DI-20)."""
    if case.composite is None:
        tau = NONCOMPOSITE_TAU_B
        rows = [_value("τb", "", tau, "C2.3(c): fijo en 1.0 para miembros no compuestos (DI-20)")]
    else:
        tau = case.tau_b
        rows = [_tau_row(case, f"{prefix}C2.3(c)")]
    for row in elastic:
        symbol = row["symbol"]
        flexural = symbol.startswith("EI")
        star = f"EI*{symbol[2:]}" if flexural else f"{symbol}*"
        if row["status"] != "calculada":
            rows.append(_absent(star, row["status"], row["reason"]))
        elif flexural:
            rows.append(_flexural_star(tau, star, row["value"], f"{prefix}C2.3(a), (b): 0.8·τb·{symbol}"))
        else:
            rows.append(_value(star, row["dimension"], C2_FACTOR * row["value"], f"{prefix}C2.3(a): 0.8·{symbol}"))
    return rows


def _filled_or_encased(case, section, catalog):
    """Elastic: Design Guide 6, 2.8. Effective: I2-5, I2-12; EA is the elastic one and (GA)eff = Gc*Ac (DI-20). Direct analysis: 0.8 on them."""
    kind = case.composite.kind
    Ec, Es = eq.concrete_modulus(wc=case.composite.concrete.wc, fc=case.composite.concrete.fc), eq.E_STEEL
    basis = _compression_basis(case, section)
    g, C, Isrx, Isry = basis["geometry"], basis["coefficient"], basis["Isrx"], basis["Isry"]
    As, Ac, Asr = section.area, g["Ac"], g.get("Asr", 0.0)
    Gc = 0.4 * Ec
    P_over_Pno = max(case.Pu, 0.0) * 1000.0 / basis["pno"]["Pno"]
    equations = {"encased": "2-7" if P_over_Pno < 0.1 else "2-8", "filled": "2-9" if P_over_Pno < 0.1 else "2-10"}[kind]
    service = {axis: dg06_members.service_stiffness(kind=kind, EsIs=Es * Is, EsIsr=Es * Isr, EcIc=Ec * Ic, C=C, P_over_Pno=P_over_Pno)
               for axis, Is, Isr, Ic in (("x", section.ix, Isrx, g["Icx"]), ("y", section.iy, Isry, g["Icy"]))}
    EA = dg06_members.axial_stiffness(EsAs=Es * As, EsAsr=Es * Asr, EcAc=Ec * Ac)
    elastic = [_value("EA", "EA", EA, "Guía 6, Ec. 2-1"), _value("EIx", "EI", service["x"], f"Guía 6, Ec. {equations}"),
               _value("EIy", "EI", service["y"], f"Guía 6, Ec. {equations}")]
    rect = kind == "filled" and g["shape"] == "rect"
    GAc = Gc * Ac
    alone = "Guía 6, 2.8: sin expresión para la sección, se reporta el componente solo"
    if rect:
        elastic.append(_value("GA", "GA", dg06_members.shear_stiffness_rect(GsAs=G_STEEL * As, GcAc=GAc), "Guía 6, Ec. 2-11"))
    else:
        elastic += [_value("GAs", "GA", G_STEEL * As, f"Gs·As; {alone}"), _value("GAc", "GA", GAc, f"Gc·Ac; {alone}")]
    Js = section.j
    if case.composite.box is not None:
        Js = dg06_members.box_torsional_constant(B=section.b_out, H=section.h_out, t=section.tdes)
    torsion = []                                                               # elastic and effective at once (DI-20)
    if Js is None:
        torsion.append(_absent("GJ", SIN_DATO, "La sección no tiene J."))
    elif kind == "encased":
        encased = case.composite.encased
        Jc = dg06_members.concrete_torsional_constant_rect(width=encased.B, depth=encased.H)
        torsion += [_value("GJs", "GJ", G_STEEL * Js, f"Gs·J; {alone}"), _value("GJc", "GJ", Gc * Jc, f"Gc·Jc; {alone}; Jc de DI-16")]
    else:
        ratio = As / (As + g["Afill"])
        if rect:
            Jc = dg06_members.concrete_torsional_constant_rect(width=g["bi"], depth=g["hi"])
            GJ = dg06_members.torsional_stiffness_rect(GsJs=G_STEEL * Js, GcJc=Gc * Jc, As_over_Ag=ratio)
            source = f"Guía 6, Ec. 2-12 y 2-14; Jc = {Jc:.4e} mm⁴ (DI-16)"
        else:
            GJ = dg06_members.torsional_stiffness_round(GsJs=G_STEEL * Js, GcJc=Gc * math.pi * g["ri"] ** 4 / 2, As_over_Ag=ratio)
            source = "Guía 6, Ec. 2-12 y 2-13"
        torsion.append(_value("GJ", "GJ", GJ, source))
    elastic += torsion

    if case.Pu < 0:                                                           # I1.5(c)
        steel = _bare_steel(case, section, catalog)
        effective = [{**row, "source": "I1.5(c): acero solo"} for row in steel if row["symbol"] in {"EA", "EIx", "EIy"}]
        direct = _direct_steel(case, steel, prefix="I1.5(c); ")
    else:
        equation = "I2-5" if kind == "encased" else "I2-12"
        EIx = eq.effective_stiffness(Is=section.ix, Isr=Isrx, C=C, Ec=Ec, Ic=g["Icx"])
        EIy = eq.effective_stiffness(Is=section.iy, Isr=Isry, C=C, Ec=Ec, Ic=g["Icy"])
        effective = [_value("(EA)eff", "EA", EA, "I1.5(b): EA elástica"), _value("(EI)eff,x", "EI", EIx, f"I1.5(a), Ec. {equation}"),
                     _value("(EI)eff,y", "EI", EIy, f"I1.5(a), Ec. {equation}"),
                     _value("(GA)eff", "GA", GAc, "Gc·Ac; indicación del usuario (DI-20)")] + torsion
        direct = [_tau_row(case, "I1.5(d)"), _value("EA*", "EA", C2_FACTOR * EA, "I1.5, Nota: 0.8·(EA)eff"),
                  _flexural_star(case.tau_b, "EI*x", EIx, "I1.5(a), C2.3: 0.8·τb·(EI)eff"), _flexural_star(case.tau_b, "EI*y", EIy, "I1.5(a), C2.3: 0.8·τb·(EI)eff"),
                  _value("GA*", "GA", C2_FACTOR * GAc, "C2.3(a): 0.8·(GA)eff (DI-20)")]
        for row in torsion:
            star = f"{row['symbol']}*"
            direct.append(_value(star, "GJ", C2_FACTOR * row["value"], f"C2.3(a): 0.8·{row['symbol']} (DI-20)")
                          if row["status"] == "calculada" else _absent(star, row["status"], row["reason"]))
    geometry = {"Ac_mm2": Ac, "Asr_mm2": Asr, "Icx_mm4": g["Icx"], "Icy_mm4": g["Icy"], "Isrx_mm4": Isrx, "Isry_mm4": Isry}
    return Ec, geometry, elastic, effective, direct


def _wall_rows(case, Is_x, Is_y, Ic_x, Ic_y, As, Asw, Ac, Ac_shear, Ec):
    """I1.5(e) with I1-1, I1-2 and I1-3; C2.3 with the tau_b entered by the user."""
    EIx, EIy = eq.wall_stiffness(Is=Is_x, Ec=Ec, Ic=Ic_x), eq.wall_stiffness(Is=Is_y, Ec=Ec, Ic=Ic_y)
    EA, GA = eq.wall_axial_stiffness(As=As, Ec=Ec, Ac=Ac), eq.wall_shear_stiffness(Asw=Asw, Ec=Ec, Ac=Ac_shear)
    effective = [_value("(EI)eff,x", "EI", EIx, "I1.5(e), Ec. I1-1"), _value("(EI)eff,y", "EI", EIy, "I1.5(e), Ec. I1-1"),
                 _value("(EA)eff", "EA", EA, "I1.5(e), Ec. I1-2"), _value("(GA)eff", "GA", GA, "I1.5(e), Ec. I1-3")]
    direct = [_tau_row(case, "I1.5(f)"), _flexural_star(case.tau_b, "EI*x", EIx, "I1.5(f), C2.3(a), (b): 0.8·τb·(EI)eff"),
              _flexural_star(case.tau_b, "EI*y", EIy, "I1.5(f), C2.3(a), (b): 0.8·τb·(EI)eff"), _value("EA*", "EA", C2_FACTOR * EA, "C2.3(a): 0.8·(EA)eff"),
              _value("GA*", "GA", C2_FACTOR * GA, "C2.3(a): 0.8·(GA)eff"), _absent("GJ*", FALTA, "I1.5 no define la rigidez torsional de muros de placas.")]
    return effective, direct


def _composite(case, section, catalog):
    kind = case.composite.kind
    _check_family(case, section)
    Ec = eq.concrete_modulus(wc=case.composite.concrete.wc, fc=case.composite.concrete.fc)
    no_guide = [_absent("EA, EI, GA, GJ", FALTA, "La Guía 6, 2.8, trata columnas rellenas y embebidas; no hay expresión implementada "
                                                 "para este miembro.")]
    if kind in {"filled", "encased"}:
        return _filled_or_encased(case, section, catalog)
    if kind == "wall":
        g = _wall_geometry(case)
        geometry = {"Ac_mm2": g["Ac"], "Icx_mm4": g["Icx"], "Icy_mm4": g["Icy"]}
        return (Ec, geometry, no_guide, *_wall_rows(case, section.ix, section.iy, g["Icx"], g["Icy"], section.area, g["Asw"], g["Ac"], g["Ac"], Ec))
    if kind == "c_wall":
        _, _, p = _c_wall_data(case)
        geometry = {"Ac_mm2": p["Ac"], "Icx_mm4": p["Ic_x"], "Icy_mm4": p["Ic_y"]}
        return (Ec, geometry, no_guide, *_wall_rows(case, p["Is_x"], p["Is_y"], p["Ic_x"], p["Ic_y"], p["As"], p["Asw"], p["Ac"], p["Acw"], Ec))
    no_direct = [_absent("EA*, EI*, GA*, GJ*", FALTA, "I1.5 no da estas rigideces para este miembro y no hay expresión implementada.")]
    if kind == "coupling_beam":
        return Ec, {}, no_guide, [_absent("(EI)eff, (EA)eff, (GA)eff", FALTA, "Sin expresión implementada para vigas de acoplamiento.")], no_direct
    return (Ec, {}, no_guide, [_absent("(EI)eff, EA", NO_APLICA, "I1.5 trata miembros embebidos, rellenos y muros de placas, no vigas compuestas.")],
            no_direct)


def member_stiffness(case: SteelCase, section: Section, catalog: Callable[[str], Section] | None = None) -> dict:
    """{"Es_mpa", "Gs_mpa", "Ec_mpa", "Gc_mpa", "geometry", "elastic", "effective", "direct_analysis"}, or {"error"} when it cannot be evaluated."""
    try:
        if case.composite is None:
            elastic = _bare_steel(case, section, catalog)
            return {"Es_mpa": case.material.E, "Gs_mpa": G_STEEL, "geometry": {}, "elastic": elastic,
                    "effective": [_absent("(EI)eff, (EA)eff", NO_APLICA, "I1.5 corresponde a miembros compuestos.")],
                    "direct_analysis": _direct_steel(case, elastic)}
        Ec, geometry, elastic, effective, direct = _composite(case, section, catalog)
    except SteelDesignError as exc:
        return {"error": str(exc)}
    return {"Es_mpa": eq.E_STEEL, "Gs_mpa": eq.G_STEEL, "Ec_mpa": Ec, "Gc_mpa": 0.4 * Ec, "geometry": geometry,
            "elastic": elastic, "effective": effective, "direct_analysis": direct}
