"""Chapter H for one member and one load combination: H1.1, H1.2 and H4. LRFD.

It combines the design strengths of the component checks (Chapters D, E and F); it never recomputes
them. Single angles need H2 (stresses at the points of the section) and are blocked. Torsion (H3)
and the H1.3 alternative are not implemented. Formulas live in codes/aisc_360_22/interaction.py.
"""
from ..codes.aisc_360_22 import interaction as eq
from ..codes.aisc_360_22.flexure import PHI_B
from ..errors import IncompleteSectionDataError, RuleNotImplementedError
from ..models import Check, SteelCase
from ..sections.models import Section

COMBINED = ("axial", "flexure_x", "flexure_y", "flexure_w", "flexure_z")
DOUBLY_SYMMETRIC = {"W", "RECTANGULAR_HSS", "CIRCULAR_HSS", "SOLID_RECTANGULAR", "SOLID_CIRCULAR"}
_LIMITATIONS = (
    "Pr y Mr se toman como datos del usuario: se supone que provienen de un análisis de segundo orden según el "
    "Capítulo C (decisión DH-3); el programa no amplifica los momentos.",
    "El cortante no interviene en H1; la torsión (H3) y la alternativa H1.3 no están implementadas.",
)


def _incomplete(reason, section, code, **details):
    raise IncompleteSectionDataError(reason, code=code, details={"section": section.name, **details})


def tension_cb_factor(case: SteelCase, section: Section) -> dict:
    """H1.2: factor sqrt(1 + alpha*Pr/Pey) on Cb, only for doubly symmetric members in axial tension."""
    family = section.type.upper()
    if family not in DOUBLY_SYMMETRIC:
        return {"applies": False, "reason": "H1.2 solo permite amplificar Cb en miembros doblemente simétricos; "
                                            "se usa Cb sin amplificar."}
    lb = case.flexure.Lb
    if lb is None or not section.iy:
        _incomplete("La amplificación de Cb (H1-2) requiere flexure.Lb e Iy.", section, "INTERACTION_DATA_INCOMPLETE",
                    fields=["flexure.Lb", "section.iy"])
    out = eq.tension_cb_factor(Pr_N=-case.Pu * 1000.0, E=case.material.E, Iy=section.iy, Lb=lb)
    return {"applies": True, **out, "Cb_user": case.flexure.Cb, "Cb": case.flexure.Cb * out["factor"]}


def amplified_cb_case(case: SteelCase, factor: dict) -> SteelCase:
    """The same combination with Cb multiplied by the H1.2 factor (for the flexure checks)."""
    flexure = case.flexure.model_copy(update={"Cb": factor["Cb"]})
    return case.model_copy(update={"flexure": flexure})


def combined_strength(case: SteelCase, section: Section, checks: list[Check]) -> dict:
    """H1-1a/H1-1b and, for flanges with holes under tension, H4-1. Ratio <= 1 complies."""
    by_id = {c.id: c for c in checks}
    involved = [by_id[i] for i in COMBINED if i in by_id]
    family = section.type.upper()
    if family == "SINGLE_ANGLE":
        raise RuleNotImplementedError("Ángulo simple con fuerzas combinadas: requiere H2 (tensiones en los puntos A, "
                                      "B y C), aún no implementado.", code="INTERACTION_DOMAIN_BLOCKED",
                                      details={"section": section.name, "checks": [c.id for c in involved]})
    missing = [c.id for c in involved if c.capacity is None]
    if missing:
        _incomplete("La interacción necesita la resistencia de diseño de cada componente.", section,
                    "INTERACTION_COMPONENT_MISSING", checks=missing)

    axial, fx, fy = by_id.get("axial"), by_id.get("flexure_x"), by_id.get("flexure_y")
    terms = {"Pr_kN": axial.demand if axial else 0.0, "Pc_kN": axial.capacity if axial else None,
             "Mrx_kNm": fx.demand if fx else 0.0, "Mcx_kNm": fx.capacity if fx else None,
             "Mry_kNm": fy.demand if fy else 0.0, "Mcy_kNm": fy.capacity if fy else None}
    h1 = eq.h1(Pr=terms["Pr_kN"], Pc=terms["Pc_kN"], Mrx=terms["Mrx_kNm"], Mcx=terms["Mcx_kNm"],
               Mry=terms["Mry_kNm"], Mcy=terms["Mcy_kNm"])
    sense = "compresión" if case.Pu > 0 else ("tracción" if case.Pu < 0 else "sin carga axial")
    modes = {"H1": {"limit_state": "combined_flexure_axial", "provision": "H1.1" if case.Pu >= 0 else "H1.2",
                    "applies": True, **terms, **h1, "axial": sense}}
    notes = []
    if case.Pu > 0:
        notes.append("Se supone que Pr y Mr incluyen los efectos de segundo orden (Capítulo C, decisión DH-3).")

    flexure = case.flexure
    if family in {"W", "CHANNEL"} and case.Pu < 0 and fx and flexure and flexure.tension_flange_holes:
        rupture = axial.result["modes"]["TR"]
        tfr = fx.result["modes"]["TFR"]
        if tfr["applies"]:
            mcx, basis = tfr["design_kNm"], "F13.1 (rotura del ala traccionada)"
        else:
            mcx, basis = PHI_B * case.material.Fy * section.zx / 1e6, "φb·Mp (F13.1 no aplica)"
        h4 = eq.h4(Pr=axial.demand, Pc=rupture["available_kN"], Mrx=fx.demand, Mcx=mcx)
        modes["H4"] = {"limit_state": "flange_rupture_combined", "provision": "H4", "applies": True,
                       "Pr_kN": axial.demand, "Pc_kN": rupture["available_kN"], "Mrx_kNm": fx.demand,
                       "Mcx_kNm": mcx, "Mcx_basis": basis, **h4}
    governing = max(modes, key=lambda k: modes[k]["ratio"])
    return {
        "chapter": "H", "code": "ANSI/AISC 360-22", "section": section.name, "family": family,
        "provisions": [modes[k]["provision"] for k in modes],
        "modes": modes,
        "governing_mode": governing,
        "governing_equation": modes[governing]["equation"],
        "ratio": modes[governing]["ratio"],
        "requirements": [],
        "notes": notes,
        "limitations": list(_LIMITATIONS),
    }
