"""Chapter E for one member: classification, selection, execution, governing strength.

Single owner of compression selection (organized after Table User Note E1.1
and checked against the mandatory text of E3-E7). Formulas live only in
codes/aisc_360_22/compression.py. Every computed mode is kept in the result;
the governing mode is the lowest Pn (E1). Domains that need data or decisions
not available here raise structured errors instead of returning a strength.
"""
import math
from typing import Callable

from ..codes.aisc_360_22 import compression as eq
from ..models import SteelCase
from ..sections.identity import double_angle_label
from ..sections.models import Section
from ..errors import IncompleteSectionDataError, RuleNotImplementedError


SUPPORTED_FAMILIES = ("W", "CHANNEL", "RECTANGULAR_HSS", "CIRCULAR_HSS", "SINGLE_ANGLE", "DOUBLE_ANGLE",
                      "SOLID_RECTANGULAR", "SOLID_CIRCULAR")
SOLIDS = ("SOLID_RECTANGULAR", "SOLID_CIRCULAR")

# B4.1a element inventory: (element, ratio source, B4.1a case, thickness field, count, Table E7.1 kind)
_ELEMENTS = {
    "W": (("flange", "bf_2tf_ratio", 1, "tf", 4, "UNSTIFFENED"),
          ("web", "h_tw_ratio", 5, "tw", 1, "STIFFENED")),
    "CHANNEL": (("flange", "b_t_ratio", 1, "tf", 2, "UNSTIFFENED"),
                ("web", "h_tw_ratio", 5, "tw", 1, "STIFFENED")),
    "RECTANGULAR_HSS": (("wall_b", "b_tdes_ratio", 6, "tdes", 2, "HSS_WALL"),
                        ("wall_h", "h_tdes_ratio", 6, "tdes", 2, "HSS_WALL")),
    "CIRCULAR_HSS": (("wall", "d_t_ratio", 9, "tdes", 1, None),),
}

_GENERAL_LIMITATIONS = (
    "Las longitudes efectivas Lc = K·L son datos del usuario; no se verifica su determinación según E2, el Capítulo C o el Apéndice 7.",
    "La resistencia y rigidez del arriostramiento (Apéndice 6) y las conexiones quedan fuera de este cálculo.",
)


def _blocked(reason, section, **details):
    raise RuleNotImplementedError(reason, code="COMPRESSION_DOMAIN_BLOCKED",
                                  details={"section": section.name, "profile_type": section.type, **details})


def _incomplete(reason, section, fields):
    raise IncompleteSectionDataError(reason, code="COMPRESSION_DATA_INCOMPLETE",
                                     details={"section": section.name, "profile_type": section.type,
                                              "fields": fields})


def _require(section, *names):
    missing = [name for name in names if not _positive(getattr(section, name))]
    if missing:
        _incomplete("La compresión requiere estas propiedades de la sección.", section, ["section." + n for n in missing])


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _angle_legs(section):
    _require(section, "d", "b", "t")
    long_leg, short_leg = max(section.d, section.b), min(section.d, section.b)
    return long_leg, short_leg


def classify_elements(section: Section, E: float, Fy: float, *, in_contact: bool | None = None) -> dict:
    """B4.1a classification of every compression element (nonslender/slender).

    Double angles: case 1(3) when the legs are in continuous contact, case 3(2)
    with separators; in_contact comes from the AISC_Manual_Label.
    """
    family = section.type.upper()
    if family in SOLIDS:
        return {"elements": [], "slender": False,
                "reference": "Sección maciza: sin elementos delgados en compresión (Tabla de Nota E1.1, solo E3)"}
    rows = []
    if family == "SINGLE_ANGLE":
        long_leg, short_leg = _angle_legs(section)
        layout = [("long_leg", long_leg / section.t, 3, "t", 1, "UNSTIFFENED"),
                  ("short_leg", short_leg / section.t, 3, "t", 1, "UNSTIFFENED")]
    elif family == "DOUBLE_ANGLE":
        long_leg, short_leg = _angle_legs(section)
        case = 1 if in_contact else 3
        layout = [("long_leg", long_leg / section.t, case, "t", 2, "UNSTIFFENED"),
                  ("short_leg", short_leg / section.t, case, "t", 2, "UNSTIFFENED")]
    elif family in _ELEMENTS:
        layout = []
        for element, source, case, thickness, count, kind in _ELEMENTS[family]:
            _require(section, source)  # thickness is only needed for E7 effective widths
            layout.append((element, getattr(section, source), case, thickness, count, kind))
    else:
        _blocked("No hay inventario de elementos B4.1a implementado para esta familia.", section)
    for element, ratio, case, thickness, count, kind in layout:
        limit = eq.lambda_r(case, E, Fy)
        rows.append({"element": element, "b4_case": case, "ratio": ratio, "lambda_r": limit,
                     "slender": ratio > limit, "t_field": thickness, "count": count, "e7_kind": kind})
    return {"elements": rows, "slender": any(row["slender"] for row in rows),
            "reference": "B4.1a (Table B4.1a)"}


def _flexural_mode(axis, E, K, L, r):
    lc = K * L
    return {"limit_state": "flexural_buckling", "provision": "E3", "axis": axis,
            "Fe_equation": "E3-4", "Lc_mm": lc, "r_mm": r, "Lc_over_r": lc / r,
            "Fe_mpa": eq.elastic_flexural_stress(E, lc, r)}


def _global_modes(case: SteelCase, section: Section) -> tuple[dict, list]:
    """Elastic buckling stresses of every applicable global mode, plus pending notes."""
    family = section.type.upper()
    E, G = case.material.E, eq.G_STEEL
    f, ln = case.factors, case.lengths
    offsets = f.xa != 0 or f.ya != 0
    notes = []
    _require(section, "area", "rx", "ry")
    modes = {"FB-x": _flexural_mode("x", E, f.Kx, ln.Lx, section.rx),
             "FB-y": _flexural_mode("y", E, f.Ky, ln.Ly, section.ry)}
    lcz = f.Kz * ln.Lz

    if family == "W":
        # Table User Note E1.1 lists TB for doubly symmetric I; evaluated in every case.
        if offsets:
            _require(section, "j", "ix", "iy", "ho")
            try:
                offset = eq.torsional_stress_bracing_offset(
                    E=E, G=G, J=section.j, Iy=section.iy, Ix=section.ix, Ag=section.area, rx=section.rx,
                    ry=section.ry, ho=section.ho, Lcz=lcz, xa=f.xa, ya=f.ya)
            except ValueError:
                _blocked("E4(f): un arriostramiento desplazado en ambas direcciones requiere un análisis de pandeo elástico.",
                         section, xa=f.xa, ya=f.ya)
            modes["TB"] = {"limit_state": "constrained_axis_torsional_buckling", "provision": "E4(d)/(e)",
                           "axis": "z", "Fe_equation": offset["equation"], "Lcz_mm": lcz, "xa_mm": f.xa,
                           "ya_mm": f.ya, "ro2_mm2": offset["ro2_mm2"], "Fe_mpa": offset["Fe_mpa"]}
        else:
            _require(section, "j", "ix", "iy")
            if section.cw is None:
                _incomplete("E4-2 requiere la constante de alabeo Cw.", section, ["section.cw"])
            modes["TB"] = {"limit_state": "torsional_buckling", "provision": "E4(a)", "axis": "z",
                           "Fe_equation": "E4-2", "Lcz_mm": lcz, "Cw_mm6": section.cw, "J_mm4": section.j,
                           "Fe_mpa": eq.torsional_stress_doubly_symmetric(
                               E=E, G=G, Cw=section.cw, J=section.j, Lcz=lcz, Ix=section.ix, Iy=section.iy)}
    elif family == "CHANNEL":
        if offsets:
            _blocked("E4(f): un arriostramiento desplazado en un canal requiere un análisis de pandeo elástico.",
                     section, xa=f.xa, ya=f.ya)
        _require(section, "j", "ro", "H")
        if section.cw is None:
            _incomplete("E4-7 requiere la constante de alabeo Cw.", section, ["section.cw"])
        fez = eq.torsional_stress(E=E, G=G, Cw=section.cw, J=section.j, Lcz=lcz, Ag=section.area, ro=section.ro)
        fex = modes["FB-x"]["Fe_mpa"]
        # E4 User Note: x is the channel axis of symmetry, so Fex replaces Fey in E4-3.
        modes["FTB"] = {"limit_state": "flexural_torsional_buckling", "provision": "E4(b)", "axis": "x+z",
                        "Fe_equation": "E4-3", "symmetry_axis": "x", "Fex_mpa": fex, "Fez_mpa": fez,
                        "Fez_equation": "E4-7", "Lcz_mm": lcz, "ro_mm": section.ro, "H": section.H,
                        "Fe_mpa": eq.flexural_torsional_stress_singly_symmetric(fex, fez, section.H)}
    elif family in {"RECTANGULAR_HSS", "CIRCULAR_HSS"}:
        # E4 applies to doubly symmetric members only when the torsional unbraced
        # length exceeds the lateral unbraced length (S22 E4 scope).
        if offsets:
            _blocked("E4(f): un arriostramiento desplazado en un perfil tubular requiere un análisis de pandeo elástico.",
                     section, xa=f.xa, ya=f.ya)
        if ln.Lz > min(ln.Lx, ln.Ly):
            _require(section, "j", "ix", "iy")
            cw = section.cw
            if cw is None and family == "RECTANGULAR_HSS":
                # Decision D-7 (user): E4-2 with the warping term omitted; Cw is not in the
                # catalog and Cw = 0 gives the lowest Fe of E4-2.
                cw = 0.0
                notes.append("E4-2 en PTE rectangular con el término de Cw omitido (no figura en el catálogo; conservador, D-7).")
            if cw is None:
                _incomplete("E4-2 requiere la constante de alabeo Cw.", section, ["section.cw"])
            modes["TB"] = {"limit_state": "torsional_buckling", "provision": "E4(a)", "axis": "z",
                           "Fe_equation": "E4-2", "Lcz_mm": lcz, "Cw_mm6": cw, "J_mm4": section.j,
                           "Fe_mpa": eq.torsional_stress_doubly_symmetric(
                               E=E, G=G, Cw=cw, J=section.j, Lcz=lcz, Ix=section.ix, Iy=section.iy)}
        else:
            notes.append("E4 no aplica: Lz no supera la longitud no arriostrada lateral (alcance de E4).")
    return modes, notes


def _single_angle_modes(case: SteelCase, section: Section) -> tuple[dict, list]:
    """E5 effective slenderness route; eccentricity neglected only when E5 permits it."""
    basis = case.single_angle_e5
    if basis is None:
        _blocked("La compresión de un ángulo simple requiere single_angle_e5; en otro caso E5 remite el "
                 "miembro al Capítulo H (H2), carga axial más flexión, fuera del alcance de este programa.", section)
    conditions = {"E5(1) cargado en los extremos a través de la misma ala": basis.loaded_at_ends_through_same_leg,
                  "E5(2) soldado o con al menos dos pernos": basis.welded_or_two_bolts_min,
                  "E5(3) sin cargas transversales intermedias": basis.no_intermediate_transverse_loads}
    failed = [name for name, value in conditions.items() if value is not True]
    long_leg, short_leg = _angle_legs(section)
    leg_ratio = long_leg / short_leg
    if leg_ratio >= 1.7:
        failed.append("E5(5) relación ala larga/ala corta < 1.7")
    if failed:
        _blocked("No se cumplen las condiciones de E5; evaluar con el Capítulo H (H2), fuera del alcance de este programa.", section, failed=failed)
    _require(section, "area", "rx", "ry", "rz")
    connected = basis.connected_leg if leg_ratio > 1 else "long"
    # Catalog convention: rx > ry, so the long leg is parallel to y. ra is the
    # radius about the geometric axis parallel to the connected leg.
    ra = section.ry if connected == "long" else section.rx
    if leg_ratio > 1 and not section.rx > section.ry:
        _blocked("No se puede identificar el eje geométrico paralelo al ala conectada (se esperaba rx > ry).", section)
    slenderness = eq.e5_effective_slenderness(L_over_ra=basis.L / ra, configuration=basis.configuration,
                                              connected_leg=connected, leg_ratio=leg_ratio,
                                              L_over_rz=basis.L / section.rz)
    if not slenderness["within_200"]:
        _blocked("E5(4): Lc/r de E5 supera 200; evaluar con el Capítulo H (H2), fuera del alcance de este programa.",
                 section, Lc_over_r=slenderness["Lc_over_r"])
    lc_r = slenderness["Lc_over_r"]
    mode = {"limit_state": "flexural_buckling", "provision": "E5(" + basis.configuration + ")", "axis": "a",
            "slenderness_equation": slenderness["equation"], "L_mm": basis.L, "ra_mm": ra, "rz_mm": section.rz,
            "connected_leg": connected, "leg_ratio": leg_ratio, "Lc_over_r": lc_r,
            "Fe_mpa": math.pi**2 * case.material.E / lc_r**2, "Fe_equation": "E3-4"}
    notes = ["E5: excentricidad despreciada según E5(a)/(b); condiciones (1)-(3) declaradas por el usuario."]
    modes = {"FB-E5": mode}
    if long_leg / section.t > 0.71 * math.sqrt(case.material.E / case.material.Fy):
        modes["FTB"] = _single_angle_ftb(case, section, long_leg == short_leg)
    else:
        notes.append("E4 no requerido: b/t del ala más larga ≤ 0.71·√(E/Fy) (E5).")
    return modes, notes


def angle_shear_center(section: Section) -> tuple[float, float]:
    """Shear center (intersection of leg mid-thickness lines) relative to the centroid, principal axes w, z.

    Catalog convention: x, y are centroid distances from the heel along the legs;
    z makes the angle alpha with y. Only squares enter E4-4, so signs are immaterial.
    """
    alpha = math.atan(section.tan_alpha)
    xs, ys = section.x - section.t / 2, section.y - section.t / 2
    return (-(xs * math.cos(alpha) + ys * math.sin(alpha)), xs * math.sin(alpha) - ys * math.cos(alpha))


def _single_angle_ftb(case: SteelCase, section: Section, equal_legs: bool) -> dict:
    """E4 flexural-torsional buckling of a single angle (E5: b/t > 0.71*sqrt(E/Fy)), principal axes."""
    f, ln, E = case.factors, case.lengths, case.material.E
    if ln.Lx != ln.Ly or f.Kx != f.Ky:
        _blocked("E4 en ángulo simple: el pandeo ocurre respecto de los ejes principales w, z; se requiere Lx = Ly y "
                 "Kx = Ky para que la longitud efectiva respecto de esos ejes girados esté definida.", section,
                 Lx=ln.Lx, Ly=ln.Ly, Kx=f.Kx, Ky=f.Ky)
    _require(section, "iw", "iz", "rz", "j", "ro")
    if section.cw is None:
        _incomplete("E4-7 requiere la constante de alabeo Cw.", section, ["section.cw"])
    lc, lcz = f.Kx * ln.Lx, f.Kz * ln.Lz
    rw = math.sqrt(section.iw / section.area)
    few = eq.elastic_flexural_stress(E, lc, rw)
    fez_axis = eq.elastic_flexural_stress(E, lc, section.rz)
    fet = eq.torsional_stress(E=E, G=eq.G_STEEL, Cw=section.cw, J=section.j, Lcz=lcz, Ag=section.area, ro=section.ro)
    mode = {"limit_state": "flexural_torsional_buckling", "axis": "w+z", "Lc_mm": lc, "Lcz_mm": lcz,
            "rw_mm": rw, "rz_mm": section.rz, "Few_mpa": few, "Fez_axis_mpa": fez_axis, "Fe_torsion_mpa": fet,
            "Fe_torsion_equation": "E4-7", "ro_mm": section.ro, "Lc_over_r": lc / section.rz,
            "e7_exempt": "E4 se aplica a ángulos simples con b/t > 0.71·√(E/Fy): Pn = Fn·Ag (E4-1); "
                         "en ángulos simples E7 usa Fn solo de E3."}
    if equal_legs:
        _require(section, "H")
        # Equal legs: the major principal axis w is the axis of symmetry; E4-3 with Few.
        return {**mode, "provision": "E4(b)", "Fe_equation": "E4-3", "symmetry_axis": "w", "H": section.H,
                "Fe_mpa": eq.flexural_torsional_stress_singly_symmetric(few, fet, section.H)}
    _require(section, "x", "y", "tan_alpha")
    wo, zo = angle_shear_center(section)
    ro_geometry = math.sqrt(wo**2 + zo**2 + (section.iw + section.iz) / section.area)
    if abs(ro_geometry / section.ro - 1) > 0.02:
        _incomplete("Las coordenadas del centro de corte obtenidas de x, y, t, tan α no reproducen r̄o del catálogo (E4-9).",
                    section, ["section.x", "section.y", "section.tan_alpha", "section.ro"])
    cubic = eq.flexural_torsional_stress_unsymmetric(Fex=few, Fey=fez_axis, Fez=fet, xo=wo, yo=zo, ro=section.ro)
    return {**mode, "provision": "E4(c)", "Fe_equation": "E4-4", "wo_mm": wo, "zo_mm": zo,
            "ro_from_geometry_mm": ro_geometry, "H": cubic["H"], "Fe_mpa": cubic["Fe_mpa"]}


def _double_angle_modes(case: SteelCase, section: Section, component: Section) -> tuple[dict, list, dict]:
    """E6 built-up double angle: E3 about x, E3 + E6 about y (connector shear), E4-3 flexural-torsional."""
    basis = case.double_angle_e6
    if basis is None:
        _blocked("Los ángulos dobles son miembros armados (E6): se requiere double_angle_e6 "
                 "(conectores, separación a, conexión de extremo).", section)
    if not basis.end_connection_welded_or_pretensioned:
        _blocked("E6.1: la conexión de extremo debe ser soldada o con pernos pretensados (clase A o B).", section)
    _require(section, "area", "rx", "ry", "ro", "H")
    _require(component, "rz", "j")
    f, ln, E = case.factors, case.lengths, case.material.E
    modes = {"FB-x": _flexural_mode("x", E, f.Kx, ln.Lx, section.rx)}  # no shear in connectors
    lcy = f.Ky * ln.Ly
    ri = component.rz
    e6 = eq.e6_modified_slenderness(Lc_over_r_o=lcy / section.ry, a_over_ri=basis.a / ri,
                                    connector=basis.connectors, Ki=0.50)  # Ki: angles back-to-back
    lr_m = e6["Lc_over_r_m"]
    fey = math.pi**2 * E / lr_m**2
    modes["FB-y"] = {"limit_state": "flexural_buckling", "provision": "E3 + E6", "axis": "y", "Lc_mm": lcy,
                     "r_mm": section.ry, "Lc_over_r_o": lcy / section.ry, "a_over_ri": basis.a / ri, "Ki": 0.50,
                     "slenderness_equation": e6["equation"], "Lc_over_r": lr_m, "Fe_equation": "E3-4",
                     "Fe_mpa": fey}
    j, lcz = 2 * component.j, f.Kz * ln.Lz
    # E4 User Note: the Cw term may be omitted for double angles. J = sum of both angles.
    fez = eq.torsional_stress(E=E, G=eq.G_STEEL, Cw=0.0, J=j, Lcz=lcz, Ag=section.area, ro=section.ro)
    modes["FTB"] = {"limit_state": "flexural_torsional_buckling", "provision": "E4(b) + E6", "axis": "y+z",
                    "Fe_equation": "E4-3", "symmetry_axis": "y", "Fey_mpa": fey, "Fez_mpa": fez,
                    "Fez_equation": "E4-7 (Cw term omitted)", "J_mm4": j, "ro_mm": section.ro, "H": section.H,
                    "Fe_mpa": eq.flexural_torsional_stress_singly_symmetric(fey, fez, section.H)}
    governing_slenderness = max(modes["FB-x"]["Lc_over_r"], lr_m)
    requirement = {"id": "E6.2(a)", "a_over_ri": basis.a / ri, "limit": 0.75 * governing_slenderness,
                   "satisfied": basis.a / ri <= 0.75 * governing_slenderness,
                   "text": "a/ri de cada componente ≤ 3/4 de la esbeltez gobernante del miembro armado"}
    built_up = {"component": component.name, "ri_mm": ri, "J_component_mm4": component.j,
                "connectors": basis.connectors, "a_mm": basis.a, "requirements": [requirement]}
    notes = ["E6: esbeltez modificada aplicada al pandeo respecto de y (cortante en conectores); x sin cambio."]
    return modes, notes, built_up


def _effective_area(section: Section, classification: dict, Fn: float, E: float, Fy: float) -> dict:
    """E7-1 Ae: gross area minus (b - be)*t per slender-capable plate, or E7-6/E7-7."""
    if section.type.upper() == "CIRCULAR_HSS":
        _require(section, "od", "tdes")
        # B4.1b(g)/E7.2: D outside diameter, t design thickness.
        return eq.e7_round_hss_area(Ag=section.area, D_over_t=section.od / section.tdes, E=E, Fy=Fy)
    plates, loss = [], 0.0
    _require(section, *{row["t_field"] for row in classification["elements"]})
    for row in classification["elements"]:
        t = getattr(section, row["t_field"])
        width = eq.e7_effective_width(b=row["ratio"] * t, t=t, lambda_r=row["lambda_r"],
                                      Fn=Fn, Fy=Fy, kind=row["e7_kind"])
        plates.append({"element": row["element"], "count": row["count"], **width})
        loss += row["count"] * width["area_loss_mm2"]
    ae = section.area - loss
    if not ae > 0:
        _incomplete("El área efectiva E7 no es positiva; revisar la geometría del catálogo.", section, ["section.area"])
    return {"Ae_mm2": ae, "equation": "E7-1", "plates": plates}


def compression_strength(case: SteelCase, section: Section,
                         catalog: Callable[[str], Section] | None = None) -> dict:
    """Nominal and available compressive strength of one member (Chapter E).

    catalog(name) returns a catalog section; double angles use it for their
    single-angle component (J, rz). Contact vs separators comes from the
    AISC_Manual_Label: no separation suffix means continuous contact (D-11).
    """
    family = section.type.upper()
    E, Fy = case.material.E, case.material.Fy
    if abs(E - eq.E_STEEL) > 1e-6:
        _incomplete("El Capítulo E define E = 200000 MPa.", section, ["material.E"])
    component = in_contact = None
    if family == "DOUBLE_ANGLE":
        if catalog is None:
            _blocked("Los ángulos dobles necesitan el catálogo para leer su ángulo simple componente.", section)
        label = double_angle_label(section.name)
        component, in_contact = catalog(label["component"]), label["in_contact"]
    if family not in SUPPORTED_FAMILIES:
        _blocked("El Capítulo E no está implementado para esta familia.", section)

    classification = classify_elements(section, E, Fy, in_contact=in_contact)
    slender = classification["slender"]
    built_up = None
    if family == "SINGLE_ANGLE":
        elastic, notes = _single_angle_modes(case, section)
    elif family == "DOUBLE_ANGLE":
        elastic, notes, built_up = _double_angle_modes(case, section, component)
    else:
        elastic, notes = _global_modes(case, section)

    modes = {}
    for name, mode in elastic.items():
        stress = eq.nominal_stress(Fy, mode["Fe_mpa"])
        reduced = slender and "e7_exempt" not in mode
        if reduced:
            area = _effective_area(section, classification, stress["Fn_mpa"], E, Fy)
        else:
            area = {"Ae_mm2": section.area, "equation": "E4-1" if mode["provision"].startswith("E4") else "E3-1"}
        pn = stress["Fn_mpa"] * area["Ae_mm2"]
        modes[name] = {**mode, "Fn_mpa": stress["Fn_mpa"], "Fn_equation": stress["equation"],
                       "Fy_over_Fe": stress["Fy_over_Fe"], "area_mm2": area["Ae_mm2"],
                       "Pn_equation": "E7-1" if reduced else area["equation"],
                       "area_basis": "Ae" if reduced else "Ag", "effective_area": area if reduced else None,
                       "Pn_kN": pn / 1000.0, "available_kN": eq.available_strength(pn)}

    governing = min(modes, key=lambda key: modes[key]["Pn_kN"])
    pn_kn = modes[governing]["Pn_kN"]
    provisions = sorted({m["provision"] for m in modes.values()} | ({"E7"} if slender else set()))
    pending = []
    worst = max(m["Lc_over_r"] for m in modes.values() if "Lc_over_r" in m)
    if worst > 200:
        notes.append(f"Nota de E2: Lc/r = {worst:.1f} supera el valor preferible de 200 (recomendación, no límite de resistencia).")
    if family == "RECTANGULAR_HSS":
        pending.append("Los anchos de pared b, h provienen del catálogo (dimensión exterior − 3·tdes, B4.1b(d) cuando no se conoce el radio interior).")
    if slender and family == "CIRCULAR_HSS" and modes[governing]["effective_area"]["bounded_to_Ag"]:
        pending.append("E7-7: Ae limitada a Ag (criterio ingenieril D-2, docs/chapter-e.md).")
    return {
        "chapter": "E", "code": "ANSI/AISC 360-22",
        "section": section.name, "family": family,
        "inputs": {"Fy_mpa": Fy, "E_mpa": E, "G_mpa": eq.G_STEEL, "Ag_mm2": section.area,
                   "Kx": case.factors.Kx, "Ky": case.factors.Ky, "Kz": case.factors.Kz,
                   "Lx_mm": case.lengths.Lx, "Ly_mm": case.lengths.Ly, "Lz_mm": case.lengths.Lz},
        "classification": classification,
        "provisions": ["E1"] + provisions,
        "modes": modes,
        "governing_mode": governing,
        "governing_equation": modes[governing]["Pn_equation"],
        "Fn_mpa": modes[governing]["Fn_mpa"],
        "Pn_kN": pn_kn,
        "phi_c": eq.PHI_C,
        "available_kN": modes[governing]["available_kN"],
        "built_up": built_up,
        "requirements": built_up["requirements"] if built_up else [],
        "notes": notes,
        "limitations": list(_GENERAL_LIMITATIONS) + pending,
    }
