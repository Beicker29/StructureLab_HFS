"""Chapter H for one member and one load combination: H1.1, H1.2, H2 (single angles) and H4. LRFD.

It combines the design strengths of the component checks (Chapters D, E and F); it never recomputes
them. Single angles use H2 at points A, B and C with principal-axis moments. Torsion (H3) and the
H1.3 alternative are not implemented. Formulas live in codes/aisc_360_22/interaction.py.
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
    "El cortante no interviene en H1 ni en H2; la torsión (H3) y la alternativa H1.3 no están implementadas.",
)
_POINTS = {"A": "punta del ala corta", "B": "talón", "C": "punta del ala larga"}


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


def _single_angle_senses(case, section):
    """Sense of the flexural stress at each point (w, z): +1 compression, -1 tension, 0 none (Example E.14B).

    Mw: the toes have opposite senses and the heel lies on the side of the short-leg toe; with equal legs w is
    the axis of symmetry and the heel has no stress (Example F.11C). Mz: both toes alike, the heel opposite.
    """
    flexure = case.angle_flexure
    long_toe = -1 if flexure and flexure.leg_in_compression == "short" else 1
    toes = 1 if flexure and flexure.toe == "compression" else -1
    return {"A": (-long_toe, toes), "B": (0 if section.d == section.b else -long_toe, -toes), "C": (long_toe, toes)}


def _h2_modes(case, section, by_id):
    """H2-1 at points A, B and C with the governing design strength of each component (Example E.14B)."""
    axial, fw, fz = by_id.get("axial"), by_id.get("flexure_w"), by_id.get("flexure_z")
    terms = {"Pr_kN": axial.demand if axial else 0.0, "Pc_kN": axial.capacity if axial else None,
             "Mrw_kNm": fw.demand if fw else 0.0, "Mcw_kNm": fw.capacity if fw else None,
             "Mrz_kNm": fz.demand if fz else 0.0, "Mcz_kNm": fz.capacity if fz else None}
    ax = 0.0
    if axial:
        ax = (axial.demand if case.Pu > 0 else -axial.demand) / axial.capacity
    rw = fw.demand / fw.capacity if fw else None
    rz = fz.demand / fz.capacity if fz else None
    sense = "compresión" if case.Pu > 0 else ("tracción" if case.Pu < 0 else "sin carga axial")
    modes = {}
    for point, (sw, sz) in _single_angle_senses(case, section).items():
        out = eq.h2(axial=ax, w=sw * rw if rw else 0.0, z=sz * rz if rz else 0.0)
        modes[f"H2-{point}"] = {"limit_state": "combined_stress", "provision": "H2", "applies": True, "point": point,
                                "location": _POINTS[point], **terms, **out, "axial": sense}
    return modes


def _h1_h4_modes(case, section, by_id):
    """H1-1a/H1-1b and, for flanges with holes under tension, H4-1."""
    family = section.type.upper()
    axial, fx, fy = by_id.get("axial"), by_id.get("flexure_x"), by_id.get("flexure_y")
    terms = {"Pr_kN": axial.demand if axial else 0.0, "Pc_kN": axial.capacity if axial else None,
             "Mrx_kNm": fx.demand if fx else 0.0, "Mcx_kNm": fx.capacity if fx else None,
             "Mry_kNm": fy.demand if fy else 0.0, "Mcy_kNm": fy.capacity if fy else None}
    h1 = eq.h1(Pr=terms["Pr_kN"], Pc=terms["Pc_kN"], Mrx=terms["Mrx_kNm"], Mcx=terms["Mcx_kNm"],
               Mry=terms["Mry_kNm"], Mcy=terms["Mcy_kNm"])
    sense = "compresión" if case.Pu > 0 else ("tracción" if case.Pu < 0 else "sin carga axial")
    modes = {"H1": {"limit_state": "combined_flexure_axial", "provision": "H1.1" if case.Pu >= 0 else "H1.2",
                    "applies": True, **terms, **h1, "axial": sense}}
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
    return modes


def combined_strength(case: SteelCase, section: Section, checks: list[Check]) -> dict:
    """The interaction of the component checks; ratio <= 1 complies."""
    by_id = {c.id: c for c in checks}
    involved = [by_id[i] for i in COMBINED if i in by_id]
    family = section.type.upper()
    if family == "SINGLE_ANGLE" and ("flexure_x" in by_id or "flexure_y" in by_id):
        raise RuleNotImplementedError("H2-1 se evalúa en los ejes principales: indique las componentes Mw y Mz en lugar "
                                      "de Mux y Muy (decisión DH-7).", code="INTERACTION_DOMAIN_BLOCKED",
                                      details={"section": section.name, "checks": [c.id for c in involved]})
    missing = [c.id for c in involved if c.capacity is None]
    if missing:
        _incomplete("La interacción necesita la resistencia de diseño de cada componente.", section,
                    "INTERACTION_COMPONENT_MISSING", checks=missing)
    modes = _h2_modes(case, section, by_id) if family == "SINGLE_ANGLE" else _h1_h4_modes(case, section, by_id)
    notes = []
    if case.Pu > 0:
        notes.append("Se supone que Pr y Mr incluyen los efectos de segundo orden (Capítulo C, decisión DH-3).")
    governing = max(modes, key=lambda k: modes[k]["ratio"])
    return {
        "chapter": "H", "code": "ANSI/AISC 360-22", "section": section.name, "family": family,
        "provisions": list(dict.fromkeys(m["provision"] for m in modes.values())),
        "modes": modes,
        "governing_mode": governing,
        "governing_equation": modes[governing]["equation"],
        "ratio": modes[governing]["ratio"],
        "requirements": [],
        "notes": notes,
        "limitations": list(_LIMITATIONS),
    }
