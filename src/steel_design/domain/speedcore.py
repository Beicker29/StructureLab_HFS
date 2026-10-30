"""Members that AISC 360-22 refers to the plastic distribution of I1.2a and Design Guide 38 writes out: C-shaped walls,
composite coupling beams and walls under fire. LRFD. Formulas in codes/aisc_dg38 and codes/aisc_360_22; not a standard."""
import math

from ..codes.aisc_360_22 import appendix_4 as a4
from ..codes.aisc_360_22 import composite as eq
from ..codes.aisc_dg38 import fire as dg38_fire
from ..codes.aisc_dg38 import walls as dg38
from ..errors import IncompleteSectionDataError
from ..models import SteelCase
from ..sections.models import Section
from .composite import _blocked, _check_family, _incomplete, _requirement, _result

_GUIDE_NOTE = "Fuera de la norma: AISC Design Guide 38. La guía desarrolla la distribución plástica de I1.2a para esta forma."


def _c_wall_data(case):
    wall = case.composite.c_wall
    Ec = eq.concrete_modulus(wc=case.composite.concrete.wc, fc=case.composite.concrete.fc)
    return wall, Ec, dg38.c_wall_properties(L=wall.L, W=wall.W, tsc_w=wall.tsc_w, tsc_f=wall.tsc_f, tp=wall.tp, n=Ec / eq.E_STEEL)


def _c_wall_requirements(case, properties):
    wall = case.composite.c_wall
    tsc = min(wall.tsc_w, wall.tsc_f)
    ratio = properties["As"] / properties["Ag"]
    ties = eq.wall_tie_limit(t=wall.tp, tsc=tsc, dtie=wall.dtie)
    return [
        _requirement("rho_s", "I1.6", 0.01 <= ratio <= 0.10, "Las placas de acero deben ser entre 1 % y 10 % de la sección."),
        _requirement("b/t", "I1.6a (I1-4)", wall.b / wall.tp <= 1.2 * math.sqrt(eq.E_STEEL / case.material.Fy),
                     "Esbeltez de la placa: b/t ≤ 1.2·√(E/Fy)."),
        _requirement("st", "I1.6b", wall.st <= tsc, "Separación de amarres ≤ tsc, con el menor espesor de la sección."),
        _requirement("st/t", "I1.6b (I1-5M)", wall.st / wall.tp <= ties["limit"], "Separación de amarres: st/t ≤ 0.38·√(Es/(2α+1))."),
    ]


def c_wall_compression(case: SteelCase, section: Section) -> dict:
    """I2.3a with the properties of Example 2.3: flexural buckling about both axes."""
    _check_family(case, section)
    wall, Ec, props = _c_wall_data(case)
    fc = case.composite.concrete.fc
    pno = eq.pno_wall(Fy=case.material.Fy, As=props["As"], fc=fc, Ac=props["Ac"])
    f, ln = case.factors, case.lengths
    modes = {}
    for axis, Is, Ic, K, L in (("x", props["Is_x"], props["Ic_x"], f.Kx, ln.Lx), ("y", props["Is_y"], props["Ic_y"], f.Ky, ln.Ly)):
        ei = eq.wall_stiffness(Is=Is, Ec=Ec, Ic=Ic)
        pe = eq.elastic_buckling_load(EI_eff=ei, Lc=K * L)
        out = eq.nominal_compression(Pno=pno, Pe=pe)
        modes[f"FB-{axis}"] = {"limit_state": "flexural_buckling", "provision": "I2.3a", "applies": True, "equation": out["equation"],
                               "Pno_kN": pno / 1000.0, "EI_eff": ei, "Lc_mm": K * L, "Pe_kN": pe / 1000.0,
                               "Pn_kN": out["Pn"] / 1000.0, "available_kN": eq.PHI_C_WALL * out["Pn"] / 1000.0,
                               "EA_eff": eq.wall_axial_stiffness(As=props["As"], Ec=Ec, Ac=props["Ac"]),
                               "GA_eff": eq.wall_shear_stiffness(Asw=props["Asw"], Ec=Ec, Ac=props["Acw"])}
    modes["LB"] = {"limit_state": "local_buckling", "provision": "I1.2", "applies": True, "equation": "No requerido en muros (I1.2)"}
    governing = min(("FB-x", "FB-y"), key=lambda k: modes[k]["Pn_kN"])
    return _result(case, section, modes=modes, governing=governing, provisions=["I1", "I2.3a"],
                   requirements=_c_wall_requirements(case, props), notes=[_GUIDE_NOTE], Pn_kN=modes[governing]["Pn_kN"],
                   phi_c=eq.PHI_C_WALL, available_kN=modes[governing]["available_kN"], y_mm=props["y"])


def c_wall_tension(case: SteelCase, section: Section) -> dict:
    """I2-16."""
    _check_family(case, section)
    _, _, props = _c_wall_data(case)
    pn = eq.tension_yielding(Fy=case.material.Fy, As=props["As"])
    mode = {"limit_state": "tensile_yielding", "provision": "I2.3b", "applies": True, "equation": "I2-16", "Pn_kN": pn / 1000.0,
            "available_kN": eq.PHI_T * pn / 1000.0}
    return _result(case, section, modes={"TY": mode}, governing="TY", provisions=["I1", "I2.3b"], notes=[_GUIDE_NOTE],
                   Pn_kN=pn / 1000.0, phi_t=eq.PHI_T, available_kN=mode["available_kN"])


def _c_wall_moment(case, section, axis, P_N, props):
    wall = case.composite.c_wall
    common = dict(L=wall.L, W=wall.W, tsc_w=wall.tsc_w, tsc_f=wall.tsc_f, tp=wall.tp, Fy=case.material.Fy,
                  fc=case.composite.concrete.fc)
    if axis == "x":
        if P_N:
            _blocked("Muro en C: la Guía 38 no da la flexión en el eje mayor con fuerza axial (A.2.6 es sin axial).", section)
        out = dg38.major_axis(**common)
    elif P_N < 0:
        if wall.minor_axis_compression != "flange_tips":
            _blocked("Muro en C en tracción: la Guía 38 (A.2.3) solo cubre las puntas de las alas en compresión.", section)
        out = dg38.flange_tips_in_compression(**common, T=-P_N, y=props["y"])
    elif P_N > 0:
        if wall.minor_axis_compression != "web":
            _blocked("Muro en C en compresión: la Guía 38 (A.2.4, A.2.5) solo cubre el alma en compresión.", section)
        out = dg38.web_in_compression_with_axial(**common, P=P_N, y=props["y"])
    elif wall.minor_axis_compression == "web":
        out = dg38.web_in_compression(**common)
    else:
        out = dg38.flange_tips_in_compression(**common)
    if not out["valid"]:
        _blocked("Muro en C: el eje neutro plástico cae fuera de la zona que suponen las ecuaciones de la Guía 38.", section,
                 C_mm=out["C"], equation=out["equation"])
    return out


def c_wall_flexure(case: SteelCase, section: Section, axis: str) -> dict:
    """I3.5 by Design Guide 38, A.2.1, A.2.2 and A.2.6, without axial force."""
    _check_family(case, section)
    _, _, props = _c_wall_data(case)
    out = _c_wall_moment(case, section, axis, 0.0, props)
    mn = out["Mp"] / 1e6
    mode = {"limit_state": "flexural_yielding", "provision": "I3.5", "applies": True, "equation": out["equation"],
            "C_mm": out["C"], "Mn_kNm": mn, "available_kNm": eq.PHI_B * mn}
    return _result(case, section, modes={"Y": mode}, governing="Y", provisions=["I1", "I3.5"], Mn_kNm=mn, phi_b=eq.PHI_B,
                   requirements=_c_wall_requirements(case, props), notes=[_GUIDE_NOTE], available_kNm=eq.PHI_B * mn)


def c_wall_shear(case: SteelCase, section: Section, axis: str) -> dict:
    """I4.4 with the shear areas of Example 2.3, for shear along the flange walls."""
    _check_family(case, section)
    if axis != "y":
        _blocked("Muro en C: la Guía 38 da las áreas para cortante a lo largo de las alas (Vuy).", section)
    _, Ec, props = _c_wall_data(case)
    out = eq.wall_shear(Asw=props["Asw"], Fy=case.material.Fy, Ec=Ec, Ac=props["Acw"])
    vn = out["Vn"] / 1000.0
    mode = {"limit_state": "shear", "provision": "I4.4", "applies": True, "equation": "I4-2", "Asw_mm2": props["Asw"],
            "Ac_mm2": props["Acw"], "Vn_kN": vn, "available_kN": eq.PHI_V_WALL * vn}
    return _result(case, section, modes={"V": mode}, governing="V", provisions=["I1", "I4.4"], notes=[_GUIDE_NOTE], Vn_kN=vn,
                   phi_v=eq.PHI_V_WALL, available_kN=mode["available_kN"])


def c_wall_interaction(case: SteelCase, section: Section, checks: list) -> dict:
    """I5(c) by Design Guide 38, A.2.3 to A.2.5: Mn at the required axial force, about the minor axis."""
    missing = [c.id for c in checks if c.capacity is None]
    if missing:
        raise IncompleteSectionDataError("La interacción necesita la resistencia de diseño de cada componente.",
                                         code="INTERACTION_COMPONENT_MISSING", details={"section": section.name, "checks": missing})
    flexures = [c for c in checks if c.id.startswith("flexure")]
    if not case.Pu or len(flexures) != 1 or flexures[0].id != "flexure_y":
        _blocked("Muro en C: la interacción se calcula con fuerza axial y flexión en el eje menor (Muy), sin Mux.", section)
    flexure = flexures[0]
    _, _, props = _c_wall_data(case)
    out = _c_wall_moment(case, section, "y", case.Pu * 1000.0, props)
    capacity = eq.PHI_B * out["Mp"] / 1e6
    ratio = flexure.demand / capacity if capacity > 0 else float("inf")
    mode = {"limit_state": "combined_flexure_axial", "provision": "I5(c)", "applies": True, "equation": out["equation"],
            "Pr_kN": case.Pu, "Mr_kNm": flexure.demand, "C_mm": out["C"], "Mn_at_Pr_kNm": out["Mp"] / 1e6, "Mc_at_Pr_kNm": capacity,
            "ratio": ratio}
    return _result(case, section, modes={"I5c": mode}, governing="I5c", provisions=["I5(c)", "I1.2a"], ratio=ratio,
                   notes=[_GUIDE_NOTE, "Se supone que Pr y Mr incluyen los efectos de segundo orden (Capítulo C, decisión DH-3)."])


def _coupling_requirements(case, section):
    beam = case.composite.coupling_beam
    Ag = beam.b * beam.h
    return [_requirement("rho_s", "I2.2a", section.area / Ag >= 0.01, "El acero debe ser al menos 1 % de la sección compuesta.")]


def coupling_beam_axial(case: SteelCase, section: Section) -> dict:
    _blocked("Viga de acoplamiento: la Guía 38 la diseña a flexión y cortante, sin fuerza axial.", section)


def coupling_beam_flexure(case: SteelCase, section: Section, axis: str) -> dict:
    """I3.4b(a) by Design Guide 38, A.3. Noncompact and slender boxes have no equation in the guide: they are blocked."""
    _check_family(case, section)
    if axis != "x":
        _blocked("Viga de acoplamiento: se calcula en su eje mayor (Mux).", section)
    beam, Fy = case.composite.coupling_beam, case.material.Fy
    root = math.sqrt(eq.E_STEEL / Fy)
    flange, web = (beam.b - 2 * beam.tw) / beam.tf, (beam.h - 2 * beam.tf) / beam.tw
    if flange > 2.26 * root or web > 3.0 * root:
        _blocked("Viga de acoplamiento no compacta (Tabla I1.1b): A.3 de la Guía 38 solo cubre la distribución plástica.", section,
                 flange_ratio=flange, web_ratio=web)
    out = dg38.coupling_beam_moment(b=beam.b, h=beam.h, tf=beam.tf, tw=beam.tw, Fy=Fy, fc=case.composite.concrete.fc)
    if not out["valid"]:
        _blocked("Viga de acoplamiento: el eje neutro plástico cae fuera del alma.", section, C_mm=out["C"])
    mn = out["Mp"] / 1e6
    mode = {"limit_state": "flexural_yielding", "provision": "I3.4b", "applies": True, "equation": out["equation"], "C_mm": out["C"],
            "Mn_kNm": mn, "available_kNm": eq.PHI_B * mn}
    return _result(case, section, modes={"Y": mode}, governing="Y", provisions=["I1", "I3.4b"], Mn_kNm=mn, phi_b=eq.PHI_B,
                   requirements=_coupling_requirements(case, section), notes=[_GUIDE_NOTE], available_kNm=eq.PHI_B * mn)


def coupling_beam_shear(case: SteelCase, section: Section, axis: str) -> dict:
    """I4-1 (Design Guide 38, Equation 2-19), with Kc = 1 as in DI-4."""
    _check_family(case, section)
    if axis != "x":
        _blocked("Viga de acoplamiento: se calcula el cortante en el plano de flexión (Vux).", section)
    beam = case.composite.coupling_beam
    Av = 2 * beam.h * beam.tw
    Ac = (beam.b - 2 * beam.tw) * (beam.h - 2 * beam.tf)
    vn = eq.shear_filled(Av=Av, Fy=case.material.Fy, Kc=1.0, Ac=Ac, fc=case.composite.concrete.fc) / 1000.0
    mode = {"limit_state": "shear", "provision": "I4.2", "applies": True, "equation": "I4-1", "Av_mm2": Av, "Ac_mm2": Ac, "Kc": 1.0,
            "Vn_kN": vn, "available_kN": eq.PHI_V_FILLED * vn}
    return _result(case, section, modes={"V": mode}, governing="V", provisions=["I1", "I4.2"], notes=[_GUIDE_NOTE], Vn_kN=vn,
                   phi_v=eq.PHI_V_FILLED, available_kN=mode["available_kN"])


def wall_fire(case: SteelCase, section: Section) -> dict:
    """Design Guide 38, Chapter 6, on the unit-width column of a planar wall (conservative, Section 6.2.2)."""
    _check_family(case, section)
    if case.Pu <= 0 or case.lengths is None:
        _incomplete("El incendio de la Guía 38 se calcula en compresión (Pu > 0) y con la longitud del miembro.", section,
                    ["Pu", "lengths"])
    wall, concrete, fire = case.composite.wall, case.composite.concrete, case.composite.fire
    Fy, fc = case.material.Fy, concrete.fc
    Ec = eq.concrete_modulus(wc=concrete.wc, fc=fc)
    st, t, tsc = wall.st, wall.t, wall.tsc
    As, Ac = 2 * st * t, (tsc - 2 * t) * st
    Ic = st * (tsc - 2 * t) ** 3 / 12
    Is = st * tsc**3 / 12 - Ic
    L, Lc = case.lengths.Ly, case.factors.Ky * case.lengths.Ly
    pno = eq.pno_wall(Fy=Fy, As=As, fc=fc, Ac=Ac)
    pn = dg38_fire.ambient_strength(Pno=pno, EI_eff=eq.wall_stiffness(Is=Is, Ec=Ec, Ic=Ic), Lc=Lc)
    pu_unit = case.Pu * 1000.0 * st / wall.length
    mode = {"limit_state": "fire", "provision": "AISC Design Guide 38, 6.2", "applies": True, "equation": "DG38 Ec. 6-5",
            "Pu_unit_kN": pu_unit / 1000.0, "Pno_kN": pno / 1000.0, "Pn_kN": pn / 1000.0, "L_over_tsc": L / tsc, "Pu_over_Pn": pu_unit / pn}
    ratios, requirements = [], []
    within_limits = L / tsc <= 20 and pu_unit / pn <= 0.2
    if within_limits:
        rating = dg38_fire.fire_resistance_rating(Pu_over_Pn=pu_unit / pn, L=L, tsc=tsc)
        mode["R_hours"] = rating
        ratios.append(fire.required_rating_hours / rating if rating > 0 else float("inf"))
    if fire.element_thicknesses:
        if abs(sum(fire.element_thicknesses) - (tsc / 2 - t)) > 1.0:
            _incomplete("Los elementos de concreto deben sumar medio espesor de concreto, de la placa al centro del muro.", section,
                        ["composite.fire.element_thicknesses"])
        steel = a4.steel_factors(fire.plate_temperature)
        Fy_T, Es_T = steel["ky"] * Fy, steel["kE"] * eq.E_STEEL
        arm = tsc / 2 - t / 2
        half_pno = Fy_T * st * t
        half_ei = Es_T * (st * t**3 / 12 + st * t * arm**2)
        position = tsc / 2 - t
        for thickness, temperature in zip(fire.element_thicknesses, fire.element_temperatures):
            factors = a4.concrete_factors(temperature, lightweight=concrete.lightweight)
            area = st * thickness
            distance = position - thickness / 2
            position -= thickness
            half_pno += 0.85 * factors["kc"] * fc * area
            half_ei += 0.35 * factors["kEc"] * Ec * (st * thickness**3 / 12 + area * distance**2)
        out = dg38_fire.elevated_strength(Pno_T=2 * half_pno, EI_eff_T=2 * half_ei, Lc=Lc)
        available = eq.PHI_C_WALL * out["Pn_T"] * wall.length / st
        mode.update(Pno_T_kN=2 * half_pno / 1000.0, EI_eff_T=2 * half_ei, Pe_T_kN=out["Pe_T"] / 1000.0, Pn_T_kN=out["Pn_T"] / 1000.0,
                    phi_Pn_T_wall_kN=available / 1000.0)
        mode["equation"] = "DG38 Ec. 6-1"
        ratios.append(case.Pu * 1000.0 / available)
    if not ratios:
        _incomplete("La Ec. 6-5 exige L/tsc ≤ 20 y Pu/Pn ≤ 0.2. Fuera de ellos, indique el perfil de temperaturas (Ecs. 6-1 a 6-4).",
                    section, ["composite.fire.element_thicknesses", "composite.fire.element_temperatures"])
    if fire.vent is not None:
        v = fire.vent
        area = dg38_fire.vent_hole_area(s1=v.s1, s2=v.s2, Tdc=v.dry_thickness, tdc=v.heating_time, omega=v.water_content,
                                        rho_w=v.water_density, rho_c=concrete.wc, hc=v.pour_height)
        required = max(math.sqrt(4 * area / math.pi), dg38_fire.VENT_MIN_DIAMETER)
        mode.update(vent_area_mm2=area, vent_required_d_mm=required)
        requirements += [
            _requirement("vent_d", "DG38 6.3.5", v.diameter >= required, "Diámetro de ventilación ≥ el requerido y ≥ 25 mm."),
            _requirement("vent_s", "DG38 6.3.5", max(v.s1, v.s2) <= min(dg38_fire.VENT_MAX_SPACING, L),
                         "Separación de ventilación ≤ la altura de piso y ≤ 3.66 m.")]
    ratio = max(ratios)
    return _result(case, section, modes={"FIRE": {**mode, "ratio": ratio}}, governing="FIRE", provisions=["AISC Design Guide 38, Cap. 6"],
                   requirements=requirements, ratio=ratio,
                   notes=["Fuera de la norma: AISC Design Guide 38, Capítulo 6, sobre la columna de ancho unitario (st). "
                          "Las temperaturas provienen de un análisis térmico del usuario; Apéndice 4 da las retenciones."])
