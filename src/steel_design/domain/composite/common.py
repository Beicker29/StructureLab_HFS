"""Chapter I: what every composite member shares: material limits, properties at temperature, result format and errors."""
from ...codes.aisc_360_22 import appendix_2 as a2
from ...codes.aisc_360_22 import appendix_4 as a4
from ...codes.aisc_360_22 import composite as eq
from ...codes.aisc_360_22.constants import is_standard_modulus
from ...errors import blocking_error, incomplete_error
from ...sections.models import missing_properties
from ..fire import steel_at_temperature

_LIMITATIONS = (
    "Diafragmas (I7) y conexión ensayada (I8.4) no se comprueban. La transferencia de carga (I6) corresponde al diseño de conexiones y queda fuera.",
    "El diseño del concreto y del refuerzo según ACI 318 (I1.1) queda fuera de este cálculo.",
    "Pr y Mr son datos del usuario, salvo con composite.second_order (Apéndice 8.1): se supone que provienen de un análisis "
    "según el Capítulo C con las rigideces de I1.5 (decisión DH-3).",
)



blocked = blocking_error("COMPOSITE_DOMAIN_BLOCKED")



incomplete = incomplete_error("COMPOSITE_DATA_INCOMPLETE", with_type=False)



def require_properties(section, *names):
    missing = missing_properties(section, names)
    if missing:
        incomplete("El Capítulo I requiere estas propiedades de la sección.", section,
                    ["section." + n for n in missing])



def requirement_row(id_, provision, satisfied, message, value=None, limit=None):
    return {"id": id_, "provision": provision, "satisfied": bool(satisfied), "message": message, "value": value, "limit": limit}



def uses_appendix_2(case, section) -> bool:
    """Appendix 2: rectangular filled members of normal weight concrete with a material above the limits of I1.3."""
    composite = case.composite
    if composite.kind != "filled" or section.type.upper() != "RECTANGULAR_HSS" or composite.concrete.lightweight:
        return False
    Fy, fc = case.material.Fy, composite.concrete.fc
    return (Fy > a2.FY_I13 or fc > a2.FC_I13) and Fy <= a2.FY_MAX and fc <= a2.FC_MAX



def check_family(case, section):
    """The declared kind must match the family; I1.3 material limits, or Appendix 2 for rectangular filled members."""
    composite, family = case.composite, section.type.upper()
    allowed = {"filled": {"RECTANGULAR_HSS", "CIRCULAR_HSS"}, "encased": {"W"}, "beam": {"W"},
               "wall": {"COMPOSITE_WALL"}, "c_wall": {"COMPOSITE_WALL"}, "coupling_beam": {"COMPOSITE_WALL"}}[composite.kind]
    if family not in allowed:
        blocked(f"composite.kind = {composite.kind} no se aplica a esta familia en el alcance implementado.", section,
                 kind=composite.kind)
    if not is_standard_modulus(case.material.E):
        incomplete("El Capítulo I usa Es = 200000 MPa.", section, ["material.E"])
    if uses_appendix_2(case, section):
        return
    fc, limit = composite.concrete.fc, 41.0 if composite.concrete.lightweight else 69.0
    failed = []
    if not 21.0 <= fc <= limit:
        failed.append(f"I1.3(a): 21 MPa ≤ f'c ≤ {limit:g} MPa")
    if case.material.Fy > 525.0:
        failed.append("I1.3(b): Fy ≤ 525 MPa")
    bars = composite.encased or composite.filled
    if bars and bars.Fysr > 550.0:
        failed.append("I1.3(c): Fysr ≤ 550 MPa")
    if failed:
        blocked("Materiales fuera de los límites de I1.3 y del alcance del Apéndice 2 (solo rellenos rectangulares de "
                 "concreto normal, con Fy ≤ 690 MPa y f'c ≤ 100 MPa).", section, failed=failed)



def composite_result(case, section, *, modes, governing, provisions, classification=None, requirements=(), notes=(), **values):
    return {"chapter": "I", "code": "ANSI/AISC 360-22", "section": section.name, "family": section.type.upper(),
            "kind": case.composite.kind, "inputs": {"Fy_mpa": case.material.Fy, "fc_mpa": case.composite.concrete.fc,
                                                    "wc_kg_m3": case.composite.concrete.wc},
            "classification": classification or {"elements": [], "slender": False},
            "provisions": provisions, "modes": modes, "governing_mode": governing,
            "governing_equation": modes[governing]["equation"], "requirements": list(requirements),
            "notes": list(notes), "limitations": list(_LIMITATIONS), **values}



def concrete_profile(case, section, part=None) -> list[tuple]:
    """(thickness, T) of the concrete of a fire case, from a plate to mid-thickness: one layer at a uniform temperature, or the profile of the user."""
    composite, fire = case.composite, case.fire
    half, layers = 1.0, None
    if composite.kind == "wall":
        half, layers = composite.wall.tsc / 2 - composite.wall.t, fire.concrete_layers
    elif composite.kind == "coupling_beam":
        half, layers = composite.coupling_beam.b / 2 - composite.coupling_beam.tw, fire.concrete_layers
    elif composite.kind == "c_wall":
        wall = composite.c_wall
        half, layers = (wall.tsc_w / 2 - wall.tp, fire.web_layers) if part == "web" else (wall.tsc_f / 2 - wall.tp, fire.flange_layers)
    if fire.concrete_temperature is not None:
        return [(half, fire.concrete_temperature)]
    if abs(sum(layer.thickness for layer in layers) - half) > 1.0:
        incomplete(f"Las capas de concreto deben sumar medio espesor de concreto, {half:g} mm, de la placa al centro.", section,
                    ["fire.concrete_layers", "fire.web_layers", "fire.flange_layers"])
    return [(layer.thickness, layer.T) for layer in layers]



def composite_materials(case, section, part=None) -> dict:
    """Fy, f'c, Ec, Es, Gs and Fysr of the strength: ambient or, above 200 deg C, at temperature (4.2.3b). With a profile, kc and kEc
    are the mean by thickness (decision DA4-8), the same as adding layers when the profile runs across the thickness and the block along the length."""
    concrete, bars = case.composite.concrete, case.composite.filled
    Ec = eq.concrete_modulus(wc=concrete.wc, fc=concrete.fc)
    out = {"Fy": case.material.Fy, "fc": concrete.fc, "Ec": Ec, "Es": eq.E_STEEL, "Gs": eq.G_STEEL, "Fysr": bars.Fysr if bars else 0.0, "Es_bars": eq.E_STEEL}
    hot = steel_at_temperature(case)
    if not hot:
        return out
    if concrete.fc > a4.FC_MAX:
        blocked(f"Apéndice 4, 4.2.3b: se aplica a concretos con f'c ≤ {a4.FC_MAX:g} MPa.", section, fc=concrete.fc)
    if bars and bars.Fysr > a4.FY_MAX:
        blocked(f"Apéndice 4, 4.2.3b: se aplica a barras con Fy ≤ {a4.FY_MAX:g} MPa.", section, Fysr=bars.Fysr)
    layers = concrete_profile(case, section, part)
    total = sum(thickness for thickness, _ in layers)
    factors = [(thickness, a4.concrete_factors(T, lightweight=concrete.lightweight)) for thickness, T in layers]
    out.update(Fy=hot["Fy_T_mpa"], Es=hot["E_T_mpa"], Gs=hot["G_T_mpa"], fc=concrete.fc * sum(h * k["kc"] for h, k in factors) / total,
               Ec=Ec * sum(h * k["kEc"] for h, k in factors) / total)
    if bars:
        bar = a4.steel_factors(case.fire.bar_temperature)
        out.update(Fysr=bar["ky"] * bars.Fysr, Es_bars=bar["kE"] * eq.E_STEEL)
    return out



def flexure_output(case, section, *, mn_mode, classification=None, requirements=(), notes=(), provisions):
    mn = mn_mode["Mn_kNm"]
    mode = {"limit_state": "flexural_yielding", "applies": True, **mn_mode, "available_kNm": eq.PHI_B * mn}
    modes = {"Y": mode}
    if case.composite.kind == "filled":
        modes["LB"] = {"limit_state": "local_buckling", "provision": "I1.4", "applies": True, "equation": "Tabla I1.1b"}
    return composite_result(case, section, modes=modes, governing="Y", provisions=provisions, classification=classification,
                   requirements=requirements, notes=notes, Mn_kNm=mn, phi_b=eq.PHI_B, available_kNm=eq.PHI_B * mn)
