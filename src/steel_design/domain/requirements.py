"""Technical requirements of a member, by mechanical and geometric properties, whatever check they also feed.

Limits of the materials and of the section that the Specification states apart from the strength equations.
"binding" requirements decide the status: one not met is never a PASS. User Notes are recommendations and do not.
"""
import math

from ..codes.aisc_360_22 import appendix_2 as a2
from ..codes.aisc_360_22 import composite as eq
from ..errors import SteelDesignError
from ..models import Check, SteelCase
from ..sections.models import Section
from .composite import (_beam_requirements, _encased_geometry, _encased_requirements, _filled_geometry, _filled_requirements,
                        _wall_geometry, _wall_requirements, uses_appendix_2)
from .speedcore import _c_wall_data, _c_wall_requirements
from .tension import least_radius

CUMPLE, NO_CUMPLE, NO_APLICA, FALTA, SIN_DATO = "cumple", "no_cumple", "no_aplica", "falta_implementacion", "sin_dato"


def _limit(description, value, limit, provision, satisfied, *, binding=True, qualifier="recomendación"):
    return {"description": description, "value": value, "limit": limit, "provision": provision,
            "status": CUMPLE if satisfied else NO_CUMPLE, "binding": binding, "qualifier": qualifier}


def _absent(description, provision, status, reason):
    return {"description": description, "value": None, "limit": None, "provision": provision, "status": status,
            "binding": False, "reason": reason}


# --- mechanical properties ---------------------------------------------------------------------------

def _common_materials(case):
    E = case.material.E
    rows = [_limit("Módulo de elasticidad del acero (E)", E, "= 200000 MPa", "I2.1b" if case.composite else "E3", abs(E - 200000.0) <= 1e-6)]
    return rows + [_absent("Acero estructural de una especificación ASTM aprobada", "A3.1a", FALTA, "La entrada no recibe la designación del material.")]


def _tensile_strength_row(case):
    flexure = case.flexure
    if case.Pu < 0:
        return _limit("Resistencia a tracción indicada (Fu)", case.material.Fu, "dato obligatorio", "D2(b)", case.material.Fu is not None)
    if flexure and flexure.tension_flange_holes:
        return _limit("Resistencia a tracción indicada (Fu)", case.material.Fu, "dato obligatorio", "F13.1", case.material.Fu is not None)
    return _absent("Resistencia a tracción indicada (Fu)", "D2(b), F13.1", NO_APLICA, "Sin tracción ni agujeros en el ala traccionada.")


def _composite_materials(case, section):
    composite, Fy = case.composite, case.material.Fy
    concrete, fc = composite.concrete, composite.concrete.fc
    if uses_appendix_2(case, section):
        rows = [_limit("Resistencia del concreto (f'c), Apéndice 2", fc, f"≤ {a2.FC_MAX:g} MPa", "Apéndice 2, 2.1.1(b)", fc <= a2.FC_MAX),
                _limit("Fluencia del acero estructural (Fy), Apéndice 2", Fy, f"≤ {a2.FY_MAX:g} MPa", "Apéndice 2, 2.1.1(c)", Fy <= a2.FY_MAX),
                _absent("Límites de materiales de I1.3", "I1.3", NO_APLICA, "Materiales por encima de I1.3: el diseño sigue el Apéndice 2.")]
    else:
        maximum = 41.0 if concrete.lightweight else 69.0
        name = "liviano" if concrete.lightweight else "de peso normal"
        rows = [_limit(f"Resistencia del concreto {name} (f'c)", fc, f"21 a {maximum:g} MPa", "I1.3(a)", 21.0 <= fc <= maximum),
                _limit("Fluencia del acero estructural (Fy)", Fy, "≤ 525 MPa", "I1.3(b)", Fy <= 525.0)]
    bars = composite.encased or composite.filled
    if bars and not uses_appendix_2(case, section):
        rows.append(_limit("Fluencia de las barras de refuerzo (Fysr)", bars.Fysr, "≤ 550 MPa", "I1.3(c)", bars.Fysr <= 550.0))
    elif not uses_appendix_2(case, section):
        rows.append(_absent("Fluencia de las barras de refuerzo (Fysr)", "I1.3(c)", NO_APLICA, "Miembro sin barras de refuerzo."))
    rows.append(_limit("Peso unitario del concreto (wc)", concrete.wc, "1500 a 2500 kg/m³", "I2.1b", 1500.0 <= concrete.wc <= 2500.0))
    rows.append(_absent("Materiales del concreto y del refuerzo según ACI 318", "I1.1", FALTA, "El programa no revisa ACI 318."))
    return rows


# --- geometric properties -----------------------------------------------------------------------------

def _from_section(rows):
    return [_limit(r["message"], r.get("value"), r.get("limit"), r["provision"], r["satisfied"]) for r in rows]


def _merged(*groups):
    """A requirement that two provisions repeat appears once, with both literals."""
    out = {}
    for row in (r for group in groups for r in group):
        if row["id"] in out and row["provision"] not in out[row["id"]]["provision"]:
            out[row["id"]]["provision"] += f", {row['provision']}"
        out.setdefault(row["id"], dict(row))
    return list(out.values())


def _filled_ratio_row(case, section, geometry):
    t, Fy = geometry["t"], case.material.Fy
    if geometry["shape"] == "round":
        limits = eq.filled_limits(shape="round", element="axial", Fy=Fy)
        return _limit("Relación diámetro-espesor del tubo (D/t)", geometry["D"] / t, f"≤ {limits['max']:.1f}", "I1.4, Tabla I1.1a", geometry["D"] / t <= limits["max"])
    ratio = max(section.b, section.h) / t
    maximum = 5.0 * math.sqrt(eq.E_STEEL / Fy)
    return _limit("Relación ancho-espesor de la pared (b/t, h/t)", ratio, f"≤ {maximum:.1f}",
                  "Apéndice 2, 2.1.1(d)" if uses_appendix_2(case, section) else "I1.4, Tabla I1.1a", ratio <= maximum)


def _composite_geometry(case, section):
    kind = case.composite.kind
    moments = bool(case.Mux or case.Muy)
    demand = case.Pu > 0 or moments
    aci = _absent("Detallado del concreto y del refuerzo según ACI 318", "I1.1", FALTA, "El programa no revisa ACI 318.")
    only_shear = "Requisito de miembros con compresión o flexión; la combinación no las tiene."
    if kind == "filled":
        geometry = _filled_geometry(case, section)
        groups = []
        if case.Pu > 0:
            groups.append(_filled_requirements(case, section, geometry, flexure=False))
        if moments:
            groups.append(_filled_requirements(case, section, geometry, flexure=True))
        rows = _from_section(_merged(*groups)) if demand else [_absent("Cuantías y separaciones de I2.2a e I3.4a", "I2.2a, I3.4a", NO_APLICA, only_shear)]
        return [_filled_ratio_row(case, section, geometry)] + rows + [aci]
    if kind == "encased":
        geometry = _encased_geometry(case, section)
        rows = _from_section(_encased_requirements(case, section, geometry)) if demand else [
            _absent("Cuantías y separaciones de I2.1a", "I2.1a", NO_APLICA, only_shear)]
        return rows + [aci]
    if kind == "wall":
        geometry = _wall_geometry(case)
        return _from_section(_wall_requirements(case, section, geometry, compression=case.Pu > 0)) + [aci]
    if kind == "c_wall":
        return _from_section(_c_wall_requirements(case, _c_wall_data(case)[2])) + [aci]
    if kind == "beam":
        return _from_section(_beam_requirements(case.composite.beam, section, case.material.Fy)) + [aci]
    return [_absent("Requisitos de la sección de la viga de acoplamiento", "AISC Design Guide 38", FALTA, "Sin requisitos implementados para este miembro."), aci]


def _tau_b_row(case):
    """The value entered is compared with the one the Specification states; a difference is reported and does not change the status."""
    description = "Parámetro de reducción de rigidez para método directo (τb)"
    kind = case.composite.kind if case.composite else None
    if kind is None:
        return _limit(description, 1.0, "= 1", "C2.3(c)", True, binding=False, qualifier="sin efecto en el estado")
    if kind in {"beam", "coupling_beam"}:
        return _absent(description, "I1.5", NO_APLICA, "Sin rigideces de método directo para este miembro.")
    if kind in {"filled", "encased"} and case.Pu >= 0:
        value, provision = 0.8, "I1.5(d)"
    elif kind in {"wall", "c_wall"}:
        value, provision = 1.0, "I1.5(f)"
    else:
        value, provision = 1.0, "I1.5(c), C2.3(c)"
    if case.tau_b is None:
        return _absent(description, provision, SIN_DATO, "Indique tau_b en la entrada: es un dato obligatorio.")
    return _limit(description, case.tau_b, f"= {value:g}", provision, abs(case.tau_b - value) <= 1e-9, binding=False, qualifier="sin efecto en el estado")


def _steel_geometry(case, section, checks):
    rows = []
    family = section.type.upper()
    axial = next((c for c in checks if c.id == "axial"), None)
    result = (axial.result if axial else None) or {}
    modes = result.get("modes") or {}
    if case.Pu < 0 and case.tension:
        rows.append(_limit("Área neta no mayor que el área bruta (An)", case.tension.An, f"≤ Ag = {section.area:.1f} mm²", "B4.3b", case.tension.An <= section.area))
    else:
        rows.append(_absent("Área neta no mayor que el área bruta (An)", "B4.3b", NO_APLICA, "Sin tracción."))
    if case.tension and case.tension.fabricated_length and least_radius(section):
        ratio = case.tension.fabricated_length / least_radius(section)
        rows.append(_limit("Esbeltez del miembro fabricado (L/r, recomendación)", ratio, "≤ 300", "Nota de D1", ratio <= 300.0, binding=False))
    else:
        rows.append(_absent("Esbeltez del miembro fabricado (L/r, recomendación)", "Nota de D1", NO_APLICA, "No se indicó la longitud fabricada."))
    slenderness = [m["Lc_over_r"] for m in modes.values() if "Lc_over_r" in m]
    if "FB-E5" in modes:
        rows.append(_limit("Esbeltez efectiva del ángulo simple (Lc/r)", modes["FB-E5"]["Lc_over_r"], "≤ 200", "E5(4)", modes["FB-E5"]["Lc_over_r"] <= 200.0))
    elif slenderness:
        rows.append(_limit("Esbeltez efectiva (Lc/r, recomendación)", max(slenderness), "≤ 200", "Nota de E2", max(slenderness) <= 200.0, binding=False))
    else:
        rows.append(_absent("Esbeltez efectiva (Lc/r, recomendación)", "Nota de E2", NO_APLICA, "Sin compresión calculada."))
    if family == "SINGLE_ANGLE" and case.single_angle_e5:
        basis = case.single_angle_e5
        met = basis.loaded_at_ends_through_same_leg and basis.welded_or_two_bolts_min and basis.no_intermediate_transverse_loads
        rows.append(_limit("Carga por una misma ala, soldadura o 2 pernos, sin cargas intermedias", "declarado" if met else "no declarado",
                           "las tres condiciones", "E5(1), (2) y (3)", met))
    for req in result.get("requirements", []):
        if "a_over_ri" in req:
            rows.append(_limit("Esbeltez del componente entre conectores (a/ri)", req["a_over_ri"], f"≤ {req['limit']:.1f}", "E6.2(a)", req["satisfied"]))
    if family == "CIRCULAR_HSS" and section.d_t_ratio:
        maximum = 0.45 * case.material.E / case.material.Fy
        if case.Mux or case.Muy:
            rows.append(_limit("Relación diámetro-espesor del tubo a flexión (D/t)", section.d_t_ratio, f"< {maximum:.1f}", "F8", section.d_t_ratio < maximum))
        else:
            rows.append(_absent("Relación diámetro-espesor del tubo a flexión (D/t)", "F8", NO_APLICA, "Sin flexión."))
    return rows


def member_requirements(case: SteelCase, section: Section, checks: list[Check]) -> dict:
    """{"materials": rows, "geometry": rows}; a group that cannot be evaluated says why in one row."""
    materials = _common_materials(case)
    # I2.1c, I2.2c and I2.3c use Fy and Fysr: Fu is a datum of Chapter D and F13.1, not of composite members.
    materials += _composite_materials(case, section) if case.composite else [_tensile_strength_row(case)]
    try:
        geometry = _composite_geometry(case, section) if case.composite else _steel_geometry(case, section, checks)
    except SteelDesignError as exc:
        geometry = [_absent("Requisitos de la sección", "–", FALTA, f"No se pudieron evaluar: {exc}")]
    return {"materials": materials, "geometry": geometry + [_tau_b_row(case)]}


def unmet(requirements: dict) -> list[dict]:
    return [r for group in requirements.values() for r in group if r["status"] == NO_CUMPLE and r["binding"]]


def missing(requirements: dict) -> list[dict]:
    return [r for group in requirements.values() for r in group if r["status"] == SIN_DATO]
