"""Chapter I by required strength: compression, tension, flexure and shear of each member; Appendix 8.1 demands."""
import math

from ...codes.aisc_360_22 import appendix_8 as a8
from ...codes.aisc_360_22 import composite as eq
from ...errors import IncompleteSectionDataError, RuleNotImplementedError
from ...models import SteelCase
from ...sections.models import Section
from ..fire import steel_at_temperature, with_fire, with_fire_extension
from .beam import beam_flexure
from .common import (
    blocked,
    check_family,
    composite_materials,
    composite_result,
    require_properties,
    uses_appendix_2,
)
from .encased import encased_flexure, encased_geometry, encased_requirements
from .filled import (
    filled_compression,
    filled_fire_modes,
    filled_flexure,
    filled_geometry,
)
from .wall import (
    wall_fire_modes,
    wall_flexure,
    wall_geometry,
    wall_is_slender,
    wall_requirements,
)


def compression_basis(case, section) -> dict:
    """Pno, stiffness coefficient and section data of filled, encased and planar wall members."""
    kind = case.composite.kind
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    point_c = 0.0
    if kind == "wall":
        geometry = wall_geometry(case)
        wall = case.composite.wall
        if wall.allow_slender_plates and wall_is_slender(case):
            Fn = eq.wall_slender_plate_stress(b_t=wall.b / wall.t, Fy=Fy)
            pno = {"Pno": eq.pno_wall_slender(Fn=Fn, As=section.area, fc=fc, Ac=geometry["Ac"]), "equation": "C-I1-2"}
        else:
            pno = {"Pno": eq.pno_wall(Fy=Fy, As=section.area, fc=fc, Ac=geometry["Ac"]), "equation": "I2-15"}
        coefficient, Isrx, Isry, classification = 0.35, 0.0, 0.0, None
        requirements = wall_requirements(case, section, geometry, compression=True)
        c_name = "C_I1_1"
    elif kind == "filled":
        geometry = filled_geometry(case, section)
        pno, coefficient, Isrx, Isry, classification, requirements = filled_compression(case, section, geometry)
        c_name = "C3"
        point_c = eq.point_c(fc=fc, Ac=geometry["Ac"], c2=0.95 if geometry["shape"] == "round" else 0.85)
    else:
        geometry = encased_geometry(case, section)
        point_c = eq.point_c(fc=fc, Ac=geometry["Ac"])
        e = case.composite.encased
        pno = {"Pno": eq.pno_encased(Fy=Fy, As=section.area, Fysr=e.Fysr, Asr=geometry["Asr"], fc=fc, Ac=geometry["Ac"]),
               "equation": "I2-7"}
        coefficient = eq.c1_encased(As=section.area, Asr=geometry["Asr"], Ag=geometry["Ag"])
        Isrx, Isry = geometry["Isrx"], geometry["Isry"]
        classification, requirements = None, encased_requirements(case, section, geometry)
        c_name = "C1"
    return {"geometry": geometry, "pno": pno, "coefficient": coefficient, "Isrx": Isrx, "Isry": Isry, "classification": classification,
            "requirements": requirements, "c_name": c_name, "point_c": point_c}



def composite_compression(case: SteelCase, section: Section, bare_steel=None) -> dict:
    """I2.1b, I2.2b and I2.3a: flexural buckling about both axes; not less than the bare steel of Chapter E."""
    check_family(case, section)
    kind = case.composite.kind
    if kind == "beam":
        blocked("La viga compuesta con fuerza axial no está cubierta por I3.2.", section)
    Ec = eq.concrete_modulus(wc=case.composite.concrete.wc, fc=case.composite.concrete.fc)
    f, ln = case.factors, case.lengths
    phi = eq.PHI_C_WALL if kind == "wall" else eq.PHI_C
    hot = steel_at_temperature(case)
    if hot:
        modes, classification, requirements = (filled_fire_modes if kind == "filled" else wall_fire_modes)(case, section, hot)
    else:
        basis = compression_basis(case, section)
        geometry, pno, coefficient, Isrx, Isry = basis["geometry"], basis["pno"], basis["coefficient"], basis["Isrx"], basis["Isry"]
        classification, requirements, c_name, point_c = basis["classification"], basis["requirements"], basis["c_name"], basis["point_c"]
        modes = {}
        for axis, Is, Isr, Ic, K, L in (("x", section.ix, Isrx, geometry["Icx"], f.Kx, ln.Lx),
                                        ("y", section.iy, Isry, geometry["Icy"], f.Ky, ln.Ly)):
            ei = (eq.wall_stiffness(Is=Is, Ec=Ec, Ic=Ic) if kind == "wall"
                  else eq.effective_stiffness(Is=Is, Isr=Isr, C=coefficient, Ec=Ec, Ic=Ic))
            pe = eq.elastic_buckling_load(EI_eff=ei, Lc=K * L)
            out = eq.nominal_compression(Pno=pno["Pno"], Pe=pe)
            provision = {"wall": "I2.3a", "filled": "I2.2b", "encased": "I2.1b"}[kind]
            if pno["equation"] == "A-2-1":
                provision = "Apéndice 2, 2.1.2"
            modes[f"FB-{axis}"] = {"limit_state": "flexural_buckling", "provision": provision,
                                   "applies": True, "equation": out["equation"], "Pno_kN": pno["Pno"] / 1000.0,
                                   "Pno_equation": pno["equation"], c_name: coefficient, "Ec_mpa": Ec, "PC_kN": point_c / 1000.0,
                                   "EI_eff": ei, "Lc_mm": K * L, "Pe_kN": pe / 1000.0, "Pno_over_Pe": out["Pno_over_Pe"],
                                   "Pn_kN": out["Pn"] / 1000.0, "available_kN": phi * out["Pn"] / 1000.0}
    governing = min(modes, key=lambda k: modes[k]["Pn_kN"])
    available, notes = modes[governing]["available_kN"], []
    if bare_steel is not None and kind != "wall":
        try:
            bare = bare_steel()
        except (RuleNotImplementedError, IncompleteSectionDataError) as exc:
            notes.append(f"Resistencia del acero solo (Capítulo E) no disponible: {exc}")
        else:
            if bare["available_kN"] > available:
                available = bare["available_kN"]
                notes.append(f"Gobierna el acero solo: I2 permite no tomar menos que el Capítulo E ({bare['governing_mode']}).")
    modes["LB"] = {"limit_state": "local_buckling", "provision": "I1.4" if kind == "filled" else "I1.2", "applies": True,
                   "equation": "Tabla I1.1a" if kind == "filled" else "No requerido en embebidos ni en muros (I1.2)"}
    return with_fire(composite_result(case, section, modes=modes, governing=governing, provisions=["I1", modes[governing]["provision"].split(";")[0]],
                             classification=classification, requirements=requirements, notes=notes,
                             Pn_kN=modes[governing]["Pn_kN"], phi_c=phi, available_kN=available),
                     hot, "4.2.4d(c)" if kind == "filled" else "4.2.4d(d)")



def composite_tension(case: SteelCase, section: Section) -> dict:
    """I2-8 and I2-14: yielding of the steel section and the bars (concrete neglected, I1.2)."""
    check_family(case, section)
    kind = case.composite.kind
    if kind == "beam":
        blocked("La viga compuesta con fuerza axial no está cubierta por I3.2.", section)
    require_properties(section, "area")
    e = case.composite.encased or case.composite.filled
    Asr, Fysr = (sum(b.area for b in e.bars), e.Fysr) if e else (0.0, 0.0)
    if uses_appendix_2(case, section):
        Asr, Fysr = 0.0, 0.0                                         # Appendix 2, 2.1.1(e)
    hot, m = steel_at_temperature(case), composite_materials(case, section)
    pn = eq.tension_yielding(Fy=m["Fy"], As=section.area, Fysr=m["Fysr"] if hot and Asr else Fysr, Asr=Asr)
    provision, equation = {"encased": ("I2.1c", "I2-8"), "filled": ("I2.2c", "I2-14"), "wall": ("I2.3b", "I2-16")}[kind]
    mode = {"limit_state": "tensile_yielding", "provision": provision, "applies": True,
            "equation": equation, "Pn_kN": pn / 1000.0, "available_kN": eq.PHI_T * pn / 1000.0}
    return with_fire_extension(composite_result(case, section, modes={"TY": mode}, governing="TY", provisions=["I1", mode["provision"]],
                             Pn_kN=pn / 1000.0, phi_t=eq.PHI_T, available_kN=mode["available_kN"]), hot)



def composite_flexure(case: SteelCase, section: Section, axis: str, flexure_strength) -> dict:
    """I3: flexure about x or y. flexure_strength is the Chapter F calculation of the steel section alone."""
    check_family(case, section)
    kind = case.composite.kind
    if axis not in {"x", "y"}:
        blocked("Mw y Mz no se aplican a miembros compuestos.", section, axis=axis)
    if kind == "wall":
        if axis != "x":
            blocked("Muro: solo se calcula la flexión en su plano (Mux); la flexión fuera del plano no está cubierta.", section)
        return wall_flexure(case, section)
    if kind == "beam":
        if axis != "x":
            blocked("La viga compuesta se calcula en su eje mayor (I3.2).", section, axis=axis)
        result = beam_flexure(case, section)
        return flexure_strength() if result is None else result
    return filled_flexure(case, section, axis) if kind == "filled" else encased_flexure(case, section, axis)



def composite_shear(case: SteelCase, section: Section, axis: str, shear_strength) -> dict:
    """I4.1(a) and I4.3: steel section alone (Chapter G). I4.2: filled sections with Kc = 1 (DI-4)."""
    check_family(case, section)
    if case.composite.kind == "wall":
        if axis != "x":
            blocked("Muro: I4.4 cubre el cortante en su plano (Vux); fuera del plano no está cubierto.", section)
        geometry = wall_geometry(case)
        m = composite_materials(case, section)
        out = eq.wall_shear(Asw=geometry["Asw"], Fy=m["Fy"], Ec=m["Ec"], Ac=geometry["Ac"], Es=m["Es"], Gs=m["Gs"])
        vn = out["Vn"] / 1000.0
        mode = {"limit_state": "shear", "provision": "I4.4", "applies": True, "equation": "I4-2", "Asw_mm2": geometry["Asw"],
                "Ac_mm2": geometry["Ac"], "Ks_N": out["Ks_N"], "Ksc_N": out["Ksc_N"], "Vn_kN": vn,
                "available_kN": eq.PHI_V_WALL * vn}
        return with_fire_extension(composite_result(case, section, modes={"V": mode}, governing="V", provisions=["I1", "I4.4"], Vn_kN=vn,
                                 phi_v=eq.PHI_V_WALL, available_kN=mode["available_kN"]), steel_at_temperature(case))
    if case.composite.kind != "filled":
        return shear_strength()
    m = composite_materials(case, section)
    geometry = filled_geometry(case, section)
    if geometry["shape"] == "round":
        Av = 2 * section.area / math.pi
    elif case.composite.box:
        Av = 2 * (section.h_out if axis == "x" else section.b_out) * geometry["t"]   # Design Guide 6, Example 2.5
    else:
        Av = 2 * (section.h if axis == "x" else section.b) * geometry["t"]
    vn = eq.shear_filled(Av=Av, Fy=m["Fy"], Kc=1.0, Ac=geometry["Ac"], fc=m["fc"])
    mode = {"limit_state": "shear", "provision": "I4.2", "applies": True, "equation": "I4-1", "Av_mm2": Av,
            "Ac_mm2": geometry["Ac"], "Kc": 1.0, "Vn_kN": vn / 1000.0, "available_kN": eq.PHI_V_FILLED * vn / 1000.0}
    return with_fire_extension(composite_result(case, section, modes={"V": mode}, governing="V", provisions=["I1", "I4.2"],
                             notes=["Kc = 1: límite inferior de I4.2 (decisión DI-4)."], Vn_kN=vn / 1000.0,
                             phi_v=eq.PHI_V_FILLED, available_kN=mode["available_kN"]), steel_at_temperature(case))



def second_order_demands(case: SteelCase, section: Section) -> tuple[SteelCase, dict]:
    """Appendix 8.1: Pu and Mux or Muy from B1 and B2, with EI* = 0.8*tau_b*(EI)eff (I1.5(d), (f))."""
    basis = case.composite.second_order
    first_order = (basis.Pnt + basis.Plt) * 1000.0
    probe = case.model_copy(update={"Pu": max(first_order / 1000.0, 1.0)})
    mode = composite_compression(probe, section)["modes"][f"FB-{basis.axis}"]
    tau_b = 1.0 if case.composite.kind == "wall" else 0.8
    ei_star = 0.8 * tau_b * mode["EI_eff"]
    pe1 = a8.member_buckling_load(EI_star=ei_star, Lc1=basis.Lc1 or mode["Lc_mm"])
    cm = a8.cm_factor(M1_M2=basis.M1_M2)
    b1 = a8.b1_factor(Cm=cm, Pr=first_order, Pe1=pe1)
    pe_story = a8.story_buckling_load(Pstory=basis.Pstory, Pmf=basis.Pmf, H=basis.H, L=basis.L, drift=basis.drift)
    b2 = a8.b2_factor(Pstory=basis.Pstory, Pe_story=pe_story)
    out = a8.required_strengths(B1=b1, B2=b2, Mnt=basis.Mnt, Mlt=basis.Mlt, Pnt=basis.Pnt, Plt=basis.Plt)
    update = {"Pu": out["Pr"], "Mux" if basis.axis == "x" else "Muy": out["Mr"]}
    info = {"Cm": cm, "Pe1_kN": pe1 / 1000.0, "B1": b1, "Pe_story_kN": pe_story, "B2": b2, "Pr_kN": out["Pr"], "Mr_kNm": out["Mr"]}
    return case.model_copy(update=update), info
