"""Chapter E obligations, written from the Specification text independently of the selection.

It never imports domain.compression. An obligation is discharged only when the
compression result contains a mode or classification that matches it; anything
unmatched keeps the result INCOMPLETE, so a missing limit state is never a PASS.
"""
import math

from ..models import Obligation, SteelCase
from ..sections.models import Section

# B4.1a compression elements expected per family (element names of the result).
EXPECTED_ELEMENTS = {
    "W": {"flange", "web"}, "CHANNEL": {"flange", "web"},
    "RECTANGULAR_HSS": {"wall_b", "wall_h"}, "CIRCULAR_HSS": {"wall"},
    "SINGLE_ANGLE": {"long_leg", "short_leg"}, "DOUBLE_ANGLE": {"legs"},
    "SOLID_RECTANGULAR": set(), "SOLID_CIRCULAR": set(),
}


def required_obligations(case: SteelCase, section: Section) -> list[Obligation]:
    family = section.type.upper()
    f, ln = case.factors, case.lengths
    out = [Obligation(id="classification", provision="B4.1a",
                      reason="Every compression element must be classified nonslender/slender.")]
    if family == "SINGLE_ANGLE":
        out.append(Obligation(id="FB", provision="E5 (with E3/E7)",
                              reason="Flexural buckling with E5 effective slenderness, or Chapter H outside E5."))
        legs = [v for v in (section.d, section.b) if v]
        if section.t and legs and max(legs) / section.t > 0.71 * math.sqrt(case.material.E / case.material.Fy):
            out.append(Obligation(id="FTB", provision="E4 / E5",
                                  reason="Single angle with b/t > 0.71*sqrt(E/Fy): flexural-torsional buckling."))
        return out
    out += [Obligation(id="FB-x", provision="E3", reason="Flexural buckling about x."),
            Obligation(id="FB-y", provision="E3", reason="Flexural buckling about y.")]
    offsets = f.xa != 0 or f.ya != 0
    if family in {"CHANNEL", "DOUBLE_ANGLE"}:
        out.append(Obligation(id="FTB", provision="E4(b)", reason="Singly symmetric member: flexural-torsional buckling."))
    elif family in {"W", "RECTANGULAR_HSS", "CIRCULAR_HSS"} and (offsets or ln.Lz > min(ln.Lx, ln.Ly)):
        out.append(Obligation(id="TB", provision="E4(a)/(d)/(e)/(f)",
                              reason="Doubly symmetric member with torsional unbraced length above the lateral one, "
                                     "or lateral bracing offset from the shear center."))
    if family == "DOUBLE_ANGLE":
        out.append(Obligation(id="E6", provision="E6", reason="Built-up member: modified slenderness and detailing."))
    return out


def discharge(obligations: list[Obligation], section: Section, result: dict) -> list[Obligation]:
    """Match obligations to computed modes; returns the obligations still unmet."""
    family = section.type.upper()
    modes = result["modes"]
    elements = {row["element"] for row in result["classification"]["elements"]}
    for item in obligations:
        if item.id == "classification" and elements == EXPECTED_ELEMENTS.get(family):
            item.satisfied_by = "classification"
        elif item.id == "FB" and "FB-E5" in modes:
            item.satisfied_by = "FB-E5"
        elif item.id in modes:
            item.satisfied_by = item.id
    if result["classification"]["slender"]:
        e7 = Obligation(id="LB", provision="E7", reason="Slender elements: Pn = Fn*Ae in every global mode.")
        if all(m["area_basis"] == "Ae" for m in modes.values()):
            e7.satisfied_by = "E7-1 (all modes)"
        obligations.append(e7)
    return [item for item in obligations if item.satisfied_by is None]
