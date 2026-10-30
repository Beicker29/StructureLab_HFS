"""Chapter D, E, F, G and H obligations, written from the Specification text independently of the selection.

It never imports domain.compression, domain.tension, domain.flexure, domain.shear or domain.interaction. An obligation is discharged
only when the result contains a mode or classification that matches it; anything
unmatched keeps the result INCOMPLETE, so a missing limit state is never a PASS.
"""
import math

from ..models import Obligation, SteelCase
from ..sections.models import Section

# B4.1a compression elements expected per family (element names of the result).
EXPECTED_ELEMENTS = {
    "W": {"flange", "web"}, "CHANNEL": {"flange", "web"},
    "RECTANGULAR_HSS": {"wall_b", "wall_h"}, "CIRCULAR_HSS": {"wall"},
    "SINGLE_ANGLE": {"long_leg", "short_leg"}, "DOUBLE_ANGLE": {"long_leg", "short_leg"},
    "SOLID_RECTANGULAR": set(), "SOLID_CIRCULAR": set(),
}


# B4.1b flexure elements expected per (family, axis), and limit states per Table User Note F1.1.
FLEXURE_ELEMENTS = {"W": {"flange", "web"}, "CHANNEL": {"flange", "web"}, "RECTANGULAR_HSS": {"flange", "web"},
                    "CIRCULAR_HSS": {"wall"}, "SOLID_RECTANGULAR": set(), "SOLID_CIRCULAR": set(),
                    "SINGLE_ANGLE": {"long_leg", "short_leg"}, "DOUBLE_ANGLE": {"flange_legs", "web_legs"}}
FLEXURE_STATES = {
    ("W", "x"): ("Y", "LTB", "FLB", "TFR"), ("CHANNEL", "x"): ("Y", "LTB", "FLB", "TFR"),
    ("W", "y"): ("Y", "FLB"), ("CHANNEL", "y"): ("Y", "FLB"),
    ("RECTANGULAR_HSS", "x"): ("Y", "FLB", "WLB", "LTB"), ("RECTANGULAR_HSS", "y"): ("Y", "FLB", "WLB", "LTB"),
    ("CIRCULAR_HSS", "x"): ("Y", "LB"), ("CIRCULAR_HSS", "y"): ("Y", "LB"),
}
_STATE_TEXT = {"Y": ("F1.1", "Fluencia (momento plástico)."), "LTB": ("F1.1", "Pandeo lateral-torsional."),
               "FLB": ("F1.1", "Pandeo local del ala comprimida."), "WLB": ("F1.1", "Pandeo local del alma."),
               "LB": ("F8", "Pandeo local de la pared."), "LLB": ("F10", "Pandeo local del ala del ángulo."),
               "TFR": ("F13.1", "Rotura del ala traccionada si tiene agujeros (requiere declararlo).")}


def flexure_obligations(section: Section, axis: str) -> list[Obligation]:
    family = section.type.upper()
    if family in {"SOLID_RECTANGULAR", "SOLID_CIRCULAR"}:
        states = ("Y", "LTB")                     # F11
    elif family == "SINGLE_ANGLE":
        states = ("Y", "LTB", "LLB")              # F10
    elif family == "DOUBLE_ANGLE":
        states = ("Y", "LTB", "FLB", "WLB")       # F9
    else:
        states = FLEXURE_STATES.get((family, axis), ("Y",))
    out = [Obligation(id="classification", provision="B4.1b",
                      reason="Todo elemento comprimido debe clasificarse en flexión (compacto/no compacto/esbelto).")]
    return out + [Obligation(id=k, provision=_STATE_TEXT[k][0], reason=_STATE_TEXT[k][1]) for k in states]


# Chapter G section per family (shear accompanying Mux / Muy).
SHEAR_PROVISIONS = {("W", "x"): "G2.1", ("CHANNEL", "x"): "G2.1", ("W", "y"): "G6", ("CHANNEL", "y"): "G6",
                    ("RECTANGULAR_HSS", "x"): "G4", ("RECTANGULAR_HSS", "y"): "G4",
                    ("CIRCULAR_HSS", "x"): "G5", ("CIRCULAR_HSS", "y"): "G5",
                    ("SINGLE_ANGLE", "x"): "G3", ("SINGLE_ANGLE", "y"): "G3",
                    ("DOUBLE_ANGLE", "x"): "G3", ("DOUBLE_ANGLE", "y"): "G3",
                    ("SOLID_RECTANGULAR", "x"): "G4", ("SOLID_RECTANGULAR", "y"): "G4",
                    ("SOLID_CIRCULAR", "x"): "G4", ("SOLID_CIRCULAR", "y"): "G4"}


def shear_obligations(section: Section, axis: str) -> list[Obligation]:
    """G1: shear yielding and shear buckling of the elements parallel to the shear, in one obligation (Cv)."""
    provision = SHEAR_PROVISIONS.get((section.type.upper(), axis), "G1")
    return [Obligation(id="V", provision=provision, reason="Fluencia y pandeo por cortante (Cv) de los elementos "
                                                           "paralelos al cortante.")]


def interaction_obligations(case: SteelCase, section: Section) -> list[Obligation]:
    """H1 whenever axial force and flexure, or flexure about two axes, act together; H4 for flanges with holes.

    Single angles: F10 sends them to H2, evaluated at every critical point of the section.
    """
    if section.type.upper() == "SINGLE_ANGLE":
        return [Obligation(id=f"H2-{point}", provision="H2", reason=f"H2-1 en el punto {point} del ángulo, con el "
                                                                    "signo de cada tensión.") for point in "ABC"]
    out = [Obligation(id="H1", provision="H1.1" if case.Pu >= 0 else "H1.2",
                      reason="Interacción de fuerza axial y flexión (H1-1a/H1-1b).")]
    flexure = case.flexure
    if (section.type.upper() in {"W", "CHANNEL"} and case.Pu < 0 and case.Mux and flexure
            and flexure.tension_flange_holes):
        out.append(Obligation(id="H4", provision="H4", reason="Rotura del ala traccionada con agujeros bajo tracción "
                                                              "y flexión (H4-1)."))
    return out


def required_obligations(case: SteelCase, section: Section) -> list[Obligation]:
    """Obligations of the axial check (Chapter D or E)."""
    if case.Pu < 0:
        # D2: the lower of tensile yielding in the gross section and rupture in the net section.
        return [Obligation(id="TY", provision="D2(a)", reason="Fluencia en tracción en la sección bruta."),
                Obligation(id="TR", provision="D2(b), D3", reason="Rotura en tracción en la sección neta efectiva.")]
    family = section.type.upper()
    f, ln = case.factors, case.lengths
    out = [Obligation(id="classification", provision="B4.1a",
                      reason="Todo elemento comprimido debe clasificarse como no esbelto o esbelto.")]
    if family == "SINGLE_ANGLE":
        out.append(Obligation(id="FB", provision="E5 (with E3/E7)",
                              reason="Pandeo por flexión con la esbeltez efectiva de E5 o, fuera de E5, respecto del "
                                     "eje principal z con H2."))
        legs = [v for v in (section.d, section.b) if v]
        if section.t and legs and max(legs) / section.t > 0.71 * math.sqrt(case.material.E / case.material.Fy):
            out.append(Obligation(id="FTB", provision="E4 / E5",
                                  reason="Ángulo simple con b/t > 0.71·√(E/Fy): pandeo flexotorsional."))
        return out
    out += [Obligation(id="FB-x", provision="E3", reason="Pandeo por flexión respecto de x."),
            Obligation(id="FB-y", provision="E3", reason="Pandeo por flexión respecto de y.")]
    offsets = f.xa != 0 or f.ya != 0
    if family in {"CHANNEL", "DOUBLE_ANGLE"}:
        out.append(Obligation(id="FTB", provision="E4(b)", reason="Miembro con un eje de simetría: pandeo flexotorsional."))
    elif family in {"W", "RECTANGULAR_HSS", "CIRCULAR_HSS"} and (offsets or ln.Lz > min(ln.Lx, ln.Ly)):
        out.append(Obligation(id="TB", provision="E4(a)/(d)/(e)/(f)",
                              reason="Miembro doblemente simétrico con longitud no arriostrada torsional mayor que la lateral, "
                                     "o arriostramiento lateral desplazado del centro de corte."))
    if family == "DOUBLE_ANGLE":
        out.append(Obligation(id="E6", provision="E6", reason="Miembro armado: esbeltez modificada y detallado."))
    return out


def discharge(obligations: list[Obligation], section: Section, result: dict) -> list[Obligation]:
    """Match obligations to computed modes; returns the obligations still unmet."""
    family = section.type.upper()
    modes = result["modes"]
    classification = result.get("classification") or {"elements": [], "slender": False}
    elements = {row["element"] for row in classification["elements"]}
    expected = (FLEXURE_ELEMENTS if result.get("chapter") == "F" else EXPECTED_ELEMENTS).get(family)
    if result.get("chapter") == "F" and family in {"W", "CHANNEL"} and result.get("axis") == "y":
        expected = {"flange"}
    for item in obligations:
        if item.id == "classification" and elements == expected:
            item.satisfied_by = "clasificación"
        elif item.id == "FB" and "FB-E5" in modes:
            item.satisfied_by = "FB-E5"
        elif item.id == "FB" and "FB-z" in modes:
            item.satisfied_by = "FB-z"
        elif item.id == "E6" and result.get("built_up"):
            item.satisfied_by = "E6, esbeltez modificada (FB-y, FTB)"
        elif item.id in modes:
            item.satisfied_by = item.id
    if classification.get("slender"):
        e7 = Obligation(id="LB", provision="E7", reason="Elementos esbeltos: Pn = Fn·Ae en todo modo global "
                        "(en ángulo simple E4 usa Ag según E4/E7).")
        if all(m["area_basis"] == "Ae" or (family == "SINGLE_ANGLE" and m["limit_state"] == "flexural_torsional_buckling")
               for m in modes.values()):
            e7.satisfied_by = "E7-1 (todos los modos)"
        obligations.append(e7)
    return [item for item in obligations if item.satisfied_by is None]
