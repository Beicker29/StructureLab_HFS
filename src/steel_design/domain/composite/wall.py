"""Planar composite plate shear walls: I1.6 requirements, I3.5 flexure, I5(c) interaction; 4.2.4d(d) under fire."""
import math

from ...codes.aisc_360_22 import appendix_4 as a4, composite as eq
from ...errors import IncompleteSectionDataError
from ...models import SteelCase
from ...sections.models import Section
from ..fire import SLENDER_BLOCK, steel_at_temperature, with_fire_extension
from .common import blocked, composite_materials, composite_result, concrete_profile, flexure_output, requirement_row


def wall_geometry(case):
    wall = case.composite.wall
    bi, hi = wall.tsc - 2 * wall.t, wall.length - 2 * wall.tf
    return {"bi": bi, "hi": hi, "Ac": bi * hi, "Ag": wall.length * wall.tsc, "Asw": 2 * wall.t * wall.length,
            "Icx": bi * hi**3 / 12, "Icy": hi * bi**3 / 12}



def wall_is_slender(case):
    wall = case.composite.wall
    return wall.b / wall.t > 1.2 * math.sqrt(eq.E_STEEL / case.material.Fy)



def wall_requirements(case, section, geometry, *, compression=False):
    """I1.6, I1.6a, I1.6b. In compression only, allow_slender_plates replaces I1-4 by the strength of Commentary I1.6a."""
    wall = case.composite.wall
    ratio = section.area / geometry["Ag"]
    ties = eq.wall_tie_limit(t=wall.t, tsc=wall.tsc, dtie=wall.dtie)
    return [
        requirement_row("rho_s", "I1.6", 0.01 <= ratio <= 0.10, "Las placas de acero deben ser entre 1 % y 10 % de la sección.", ratio, "0.01 a 0.10"),
        requirement_row("b/t", "I1.6a (I1-4)", (compression and wall.allow_slender_plates) or not wall_is_slender(case),
                     "Esbeltez de la placa: b/t ≤ 1.2·√(E/Fy).", wall.b / wall.t, f"≤ {1.2 * math.sqrt(eq.E_STEEL / case.material.Fy):.1f}"),
        requirement_row("st", "I1.6b", wall.st <= wall.tsc, "Separación de amarres ≤ tsc.", wall.st, f"≤ {wall.tsc:g} mm"),
        requirement_row("st/t", "I1.6b (I1-5M)", wall.st / wall.t <= ties["limit"], "Separación de amarres: st/t ≤ 0.38·√(Es/(2α+1)).",
                     wall.st / wall.t, f"≤ {ties['limit']:.1f}"),
    ]



def wall_strip_at_temperature(case, hot, *, st, t, tsc, layers, Lc) -> dict:
    """A-4-12 on one column of unit width, with the steel at the temperature of the case and the concrete by layers."""
    concrete = case.composite.concrete
    return a4.wall_strip(Fy_T=hot["Fy_T_mpa"], E_T=hot["E_T_mpa"], fc=concrete.fc, Ec=eq.concrete_modulus(wc=concrete.wc, fc=concrete.fc),
                         st=st, t=t, tsc=tsc, layers=layers, Lc=Lc, lightweight=concrete.lightweight)



def wall_fire_modes(case, section, hot):
    """4.2.4d(d) on the column of unit width st, conservative (Commentary), whose buckling is across the thickness (DI-19)."""
    wall = case.composite.wall
    if wall_is_slender(case):
        blocked(SLENDER_BLOCK, section, b_t=wall.b / wall.t)
    composite_materials(case, section)                                                    # the limits of 4.2.3b
    Lc = case.factors.Ky * case.lengths.Ly
    strip = wall_strip_at_temperature(case, hot, st=wall.st, t=wall.t, tsc=wall.tsc, layers=concrete_profile(case, section), Lc=Lc)
    pn = strip["Pn_T"] * wall.length / wall.st
    modes = {"FB": {"limit_state": "flexural_buckling", "provision": "I2.3a; Apéndice 4, 4.2.4d(d)", "applies": True, "equation": strip["equation"], "Pn_equation": strip["equation"], "st_mm": wall.st,
                    "Pno_T_kN": strip["Pno_T"] / 1000.0, "EI_eff_T": strip["EI_eff_T"], "Lc_mm": Lc, "Pe_T_kN": strip["Pe_T"] / 1000.0, "Pno_over_Pe": strip["Pno_over_Pe"],
                    "Pn_T_kN": strip["Pn_T"] / 1000.0, "Pn_kN": pn / 1000.0, "phi_Pn_T_wall_kN": eq.PHI_C_WALL * pn / 1000.0,
                    "available_kN": eq.PHI_C_WALL * pn / 1000.0}}
    return modes, None, wall_requirements(case, section, wall_geometry(case), compression=True)



def _wall_moment(case, section, P_N):
    wall = case.composite.wall
    geometry = wall_geometry(case)
    m = composite_materials(case, section)
    if steel_at_temperature(case) and wall_is_slender(case):
        blocked(SLENDER_BLOCK, section, b_t=wall.b / wall.t)
    return eq.wall_plastic_moment(Fy=m["Fy"], fc=m["fc"], H=wall.length, t=wall.t, tf=wall.tf, bi=geometry["bi"], P=P_N)



def wall_flexure(case, section):
    """I3.5: plastic stress distribution (I1.2a) in the plane of the wall."""
    out = _wall_moment(case, section, 0.0)
    mode = {"provision": "I3.5", "equation": "Distribución plástica (I1.2a)", "a_mm": out["a_mm"], "Mn_kNm": out["Mp"] / 1e6}
    return with_fire_extension(flexure_output(case, section, mn_mode=mode, requirements=wall_requirements(case, section, wall_geometry(case)),
                                     provisions=["I1", "I3.5"]), steel_at_temperature(case))



def composite_wall_interaction(case: SteelCase, section: Section, checks: list) -> dict:
    """I5(c): the plastic stress distribution of I1.2a at the required axial force (DI-11; Design Guide 38, A.1.2, A.1.3)."""
    by_id = {c.id: c for c in checks}
    missing = [c.id for c in checks if c.capacity is None]
    if missing:
        raise IncompleteSectionDataError("La interacción necesita la resistencia de diseño de cada componente.",
                                         code="INTERACTION_COMPONENT_MISSING",
                                         details={"section": section.name, "checks": missing})
    flexure = by_id["flexure_x"]
    P_N = case.Pu * 1000.0
    out = _wall_moment(case, section, P_N)
    if out["within_section"]:
        capacity = eq.PHI_B * out["Mp"] / 1e6
        ratio = flexure.demand / capacity if capacity > 0 else float("inf")
    else:
        limit = out["P_max_N"] if P_N > 0 else out["P_min_N"]
        capacity, ratio = 0.0, P_N / limit
    mode = {"limit_state": "combined_flexure_axial", "provision": "I5(c)", "applies": True, "equation": "I1.2a",
            "Pr_kN": case.Pu, "Mr_kNm": flexure.demand, "a_mm": out["a_mm"], "Mc_at_Pr_kNm": capacity, "ratio": ratio}
    return with_fire_extension(composite_result(case, section, modes={"I5c": mode}, governing="I5c", provisions=["I5(c)", "I1.2a"], ratio=ratio,
                             notes=["Se supone que Pr y Mr incluyen los efectos de segundo orden (Capítulo C, decisión DH-3).",
                                    "I5(c): Mn a la fuerza axial requerida; la estabilidad se verifica en el chequeo axial."]),
                     steel_at_temperature(case))
