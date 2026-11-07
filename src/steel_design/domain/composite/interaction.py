"""Interaction of filled and encased members: I5, Commentary I5 Method 2 and Appendix 2."""
from ...codes.aisc_360_22 import appendix_2 as a2
from ...codes.aisc_360_22 import composite as eq
from ...codes.aisc_dg06 import members as dg06_members
from ...errors import IncompleteSectionDataError
from ...models import SteelCase
from ...sections.models import Section
from ..fire import steel_at_temperature, with_fire_extension
from .common import blocked, composite_materials, composite_result, uses_appendix_2
from .filled import filled_geometry


def composite_method2(case: SteelCase, section: Section, checks: list) -> dict:
    """Commentary I5, Method 2 (M2) and Method 2 simplified (M2S), from the strengths of the component checks."""
    by_id = {c.id: c for c in checks}
    composite, simplified = case.composite, case.composite.interaction == "M2S"
    if composite.kind not in {"filled", "encased"}:
        blocked("El Método 2 se aplica a miembros embebidos y rellenos compactos.", section, kind=composite.kind)
    if case.P > 0:
        blocked("El Método 2 del Commentary cubre compresión con flexión; use interaction = H1 con tracción.", section)
    missing = [c.id for c in checks if c.capacity is None]
    if missing:
        raise IncompleteSectionDataError("La interacción necesita la resistencia de diseño de cada componente.",
                                         code="INTERACTION_COMPONENT_MISSING",
                                         details={"section": section.name, "checks": missing})
    axial = by_id.get("axial")
    if axial is None and not simplified:
        blocked("El Método 2 requiere fuerza axial; use interaction = M2S o H1 para flexión biaxial.", section)
    if case.Mx_3 and case.My_2 and not simplified:
        blocked("El Método 2 con puntos A, B, C y D es para flexión en un eje; use interaction = M2S (C-I5-1).", section)
    flexures = [by_id[i] for i in ("flexure_x_3", "flexure_y_2") if i in by_id]
    classes = {row["class"] for c in [*flexures, *([axial] if axial else [])] for row in c.result["classification"]["elements"]}
    if classes - {"compact"}:
        blocked("El Método 2 exige una sección rellena compacta (Commentary I5); use H1 o I5.", section)
    if any("Md_kNm" not in f.result["modes"]["Y"] for f in flexures):
        blocked("El Método 2 usa la distribución plástica compuesta: indique flexure_method = composite.", section)

    fx, fy = by_id.get("flexure_x_3"), by_id.get("flexure_y_2")
    Pr = axial.demand if axial else 0.0
    A = axial.result["modes"][axial.result["governing_mode"]] if axial else None
    pno = A.get("Pno_kN", A.get("Pno_T_kN")) if A else None          # at temperature, the Pno of the case (user's decision)
    lam = A["Pn_kN"] / pno if A else None                            # the same slenderness factor for A, C and D
    PA = eq.PHI_C * A["Pn_kN"] if A else 0.0
    PC = eq.PHI_C * lam * A["PC_kN"] if A else 0.0
    terms = {"lambda": lam, "Pr_kN": Pr, "PA_kN": PA, "PC_kN": PC}
    if simplified and composite.biaxial_shape_factor and fx and fy:
        shape = composite.kind if composite.kind == "encased" else filled_geometry(case, section)["shape"]
        alpha = dg06_members.BIAXIAL_ALPHA[shape]
        out = dg06_members.biaxial_interaction(Pr=Pr, Pc=PA, Pcc=PC, x=fx.demand / fx.capacity, y=fy.demand / fy.capacity, alpha=alpha)
        mode = {"limit_state": "combined_flexure_axial", "provision": "AISC Design Guide 6, 2.3.2", "applies": True,
                **terms, "alpha": alpha, **out}
    elif simplified:
        out = eq.method2_simplified(Pr=Pr, PA=PA, PC=PC, Mrx=fx.demand if fx else 0.0, Mcx=fx.capacity if fx else None,
                                    Mry=fy.demand if fy else 0.0, Mcy=fy.capacity if fy else None)
        mode = {"limit_state": "combined_flexure_axial", "provision": "Commentary I5, Método 2 simplificado", "applies": True,
                **terms, **out}
    else:
        flexure = flexures[0]
        Y = flexure.result["modes"]["Y"]
        design = [(0.0, eq.PHI_B * Y["Mn_kNm"]), (PC / 2, eq.PHI_B * Y["Md_kNm"]), (PC, eq.PHI_B * Y["Mn_kNm"]), (PA, 0.0)]
        # Commentary I5: the design curve may leave the nominal curve near D; that zone is not permitted.
        nominal = [(0.0, Y["Mn_kNm"]), (A["PC_kN"] / 2, Y["Md_kNm"]), (A["PC_kN"], Y["Mn_kNm"]), (pno, 0.0)]
        ratio_design = eq.method2_ratio(Pr=Pr, Mr=flexure.demand, points=design)
        ratio_nominal = eq.method2_ratio(Pr=Pr, Mr=flexure.demand, points=nominal)
        mode = {"limit_state": "combined_flexure_axial", "provision": "Commentary I5, Método 2", "applies": True,
                **terms, "Mr_kNm": flexure.demand, "MB_kNm": design[0][1], "MD_kNm": design[1][1],
                "ratio_design": ratio_design, "ratio_nominal": ratio_nominal,
                "ratio": max(ratio_design, ratio_nominal), "equation": "Curva A-C-D-B (Fig. C-I5.2)"}
    notes = ["Se supone que Pr y Mr incluyen los efectos de segundo orden (Capítulo C, decisión DH-3).",
             "Método 2 del Commentary de I5: no es una ecuación de la Specification, que lo permite por I1.2."]
    if not simplified:
        notes.append("AISC Design Guide 6 (2.ª ed., 2.3.2) excluye el punto D por posible error del lado inseguro; "
                     "considere interaction = M2S.")
    return with_fire_extension(
        composite_result(
            case, section, modes={"M2": mode}, governing="M2", provisions=[mode["provision"]], ratio=mode["ratio"], notes=notes
        ),
        steel_at_temperature(case),
    )



def composite_appendix_2_interaction(case: SteelCase, section: Section, checks: list) -> dict:
    """Appendix 2, Section 2.1.4: Equations I5-1a/b with cp and cm of A-2-3 and A-2-4.

    Two axes (DI-22, not in the Appendix): Mr/Mc becomes Mrx/Mcx + Mry/Mcy. B/H depends on the axis, so the equation is evaluated with
    the cp and cm of each axis and the greater value governs.
    """
    by_id = {c.id: c for c in checks}
    missing = [c.id for c in checks if c.capacity is None]
    if missing:
        raise IncompleteSectionDataError("La interacción necesita la resistencia de diseño de cada componente.",
                                         code="INTERACTION_COMPONENT_MISSING",
                                         details={"section": section.name, "checks": missing})
    axial = by_id["axial"]
    flexures = [by_id[i] for i in ("flexure_x_3", "flexure_y_2") if i in by_id]
    A = axial.result["modes"][axial.result["governing_mode"]]
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    t = section.tdes
    lam = a2.slenderness(b_t=max(section.b, section.h) / t, Fy=Fy)
    Mr_Mc = sum(f.demand / f.capacity for f in flexures)
    biaxial = len(flexures) > 1
    terms = {"Pr_kN": axial.demand, "Pc_kN": axial.capacity}
    if biaxial:
        fx, fy = flexures
        terms.update(Mrx_kNm=fx.demand, Mcx_kNm=fx.capacity, Mry_kNm=fy.demand, Mcy_kNm=fy.capacity, Mr_Mc_sum=Mr_Mc)
    else:
        terms.update(Mr_kNm=flexures[0].demand, Mc_kNm=flexures[0].capacity)
    provision = "Apéndice 2, 2.1.4" + (", extendida a dos ejes (DI-22)" if biaxial else "")
    candidates = []
    for flexure in flexures:
        B, H = (section.b_out, section.h_out) if flexure.id == "flexure_x_3" else (section.h_out, section.b_out)
        coefficients = a2.interaction_coefficients(B=B, H=H, lam=lam, Pn=A["Pn_kN"], Pno=A["Pno_kN"], fc=fc, Fy=Fy)
        out = eq.i5_interaction(Pr_Pc=axial.demand / axial.capacity, Mr_Mc=Mr_Mc, **coefficients)
        candidates.append({"limit_state": "combined_flexure_axial", "provision": provision, "applies": True, **coefficients, **terms, **out,
                           **({"coefficients_axis": flexure.id.removeprefix("flexure_")} if biaxial else {})})
    candidates.sort(key=lambda mode: -mode["ratio"])
    modes = {"A2": candidates[0], **({"A2-otro": candidates[1]} if biaxial else {})}
    notes = ["Se supone que Pr y Mr incluyen los efectos de segundo orden (Capítulo C, decisión DH-3)."]
    if biaxial:
        notes.append(
            "Extensión a dos ejes de I5-1a y I5-1b (Mrx/Mcx + Mry/Mcy), indicada por el usuario: el Apéndice 2 y la Guía 6 solo "
            "tratan un eje. "
            "Se evalúa con cp y cm de cada eje y gobierna el mayor (DI-22)."
        )
    return composite_result(case, section, modes=modes, governing="A2", provisions=[provision], ratio=candidates[0]["ratio"], notes=notes)



def default_interaction(case: SteelCase, checks: list) -> str:
    """I5: H1.1 under I5(a); I5-1 under I5(b) where those equations apply (compression with flexure about one axis), otherwise H1.1."""
    flexures = [c for c in checks if c.id in {"flexure_x_3", "flexure_y_2"}]
    axial = next((c for c in checks if c.id == "axial"), None)
    if (
        case.composite.kind != "filled"
        or case.P >= 0
        or len(flexures) != 1
        or axial is None
        or axial.result is None
        or flexures[0].result is None
    ):
        return "H1"
    classes = {row["class"] for c in (axial, flexures[0]) for row in c.result["classification"]["elements"]}
    return "I5" if classes - {"compact"} else "H1"



def requested_interaction_replaced(case: SteelCase) -> bool:
    """Method 2 is optional, except in filled members with bars: Asr != 0 leaves H1.1 only (DI-22)."""
    return case.composite.interaction in {"M2", "M2S"} and case.composite.filled is not None



def composite_i5(case: SteelCase, section: Section, checks: list) -> dict:
    """I5(b): Equations I5-1a/b, for filled noncompact or slender sections under compression and flexure."""
    by_id = {c.id: c for c in checks}
    composite = case.composite
    if composite.kind != "filled":
        blocked("Las ecuaciones I5-1 solo se aplican a miembros rellenos.", section, kind=composite.kind)
    if case.P > 0 or (case.Mx_3 and case.My_2):
        blocked("Las ecuaciones I5-1 cubren compresión con flexión en un eje; use interaction = H1.", section)
    missing = [c.id for c in checks if c.capacity is None]
    if missing:
        raise IncompleteSectionDataError("La interacción necesita la resistencia de diseño de cada componente.",
                                         code="INTERACTION_COMPONENT_MISSING",
                                         details={"section": section.name, "checks": missing})
    flexure = by_id.get("flexure_x_3") or by_id.get("flexure_y_2")
    axial = by_id["axial"]
    classes = {row["class"] for c in (axial, flexure) for row in c.result["classification"]["elements"]}
    if classes == {"compact"}:
        blocked("Sección compacta: I5(a) no admite las ecuaciones I5-1; use interaction = H1.", section)
    geometry = filled_geometry(case, section)
    m = composite_materials(case, section)
    csr = eq.strength_ratio(As=section.area, Fy=m["Fy"], Asr=geometry["Asr"], Fysr=m["Fysr"], Ac=geometry["Ac"], fc=m["fc"])
    coefficients = eq.i5_coefficients(shape=geometry["shape"], csr=csr)
    terms = {"Pr_kN": axial.demand, "Pc_kN": axial.capacity, "Mr_kNm": flexure.demand, "Mc_kNm": flexure.capacity}
    out = eq.i5_interaction(Pr_Pc=axial.demand / axial.capacity, Mr_Mc=flexure.demand / flexure.capacity, **coefficients)
    mode = {"limit_state": "combined_flexure_axial", "provision": "I5(b)", "applies": True, "csr": csr, **coefficients, **terms, **out}
    return with_fire_extension(composite_result(case, section, modes={"I5": mode}, governing="I5", provisions=["I5"], ratio=out["ratio"],
                             notes=["Se supone que Pr y Mr incluyen los efectos de segundo orden (Capítulo C, decisión DH-3)."]),
                     steel_at_temperature(case))


def interaction_method(case: SteelCase, section: Section, checks: list) -> tuple[str, bool]:
    """The method of a composite member, and whether a requested Method 2 had to be replaced by H1.1 (DI-22)."""
    method = "wall" if case.composite.kind == "wall" else (case.composite.interaction or default_interaction(case, checks))
    if uses_appendix_2(case, section) and case.P < 0:
        method = "A2"
    replaced = method in {"M2", "M2S"} and requested_interaction_replaced(case)
    return ("H1" if replaced else method), replaced
