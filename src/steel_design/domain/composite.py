"""Chapter I for one member and one load combination. LRFD.

Filled rectangular and round HSS (I2.2, I3.4, I4.2), encased W-shapes (I2.1, I3.3, I4.1(a)), composite beams
with steel anchors (I3.2, I4.3, I8.2), planar composite plate shear walls (I1.6, I2.3, I3.5, I4.4, I5(c)) and
anchors of composite components (I8.3). The member type is declared in case.composite. Formulas live in
codes/aisc_360_22/composite.py. Missing data or decisions raise structured errors.
"""
import math

from ..codes.aisc_360_22 import appendix_2 as a2
from ..codes.aisc_360_22 import appendix_8 as a8
from ..codes.aisc_360_22 import composite as eq
from ..codes.aisc_dg06 import filled as dg06
from ..codes.aisc_dg06 import members as dg06_members
from ..errors import IncompleteSectionDataError, RuleNotImplementedError
from ..models import SteelCase
from ..sections.models import Section

_LIMITATIONS = (
    "Diafragmas (I7) y conexión ensayada (I8.4) no se comprueban; I6 solo si se indica composite.load_transfer.",
    "El diseño del concreto y del refuerzo según ACI 318 (I1.1) queda fuera de este cálculo.",
    "Pr y Mr son datos del usuario, salvo con composite.second_order (Apéndice 8.1): se supone que provienen de un análisis "
    "según el Capítulo C con las rigideces de I1.5 (decisión DH-3).",
)


def _blocked(reason, section, **details):
    raise RuleNotImplementedError(reason, code="COMPOSITE_DOMAIN_BLOCKED",
                                  details={"section": section.name, "profile_type": section.type, **details})


def _incomplete(reason, section, fields):
    raise IncompleteSectionDataError(reason, code="COMPOSITE_DATA_INCOMPLETE",
                                     details={"section": section.name, "fields": fields})


def _require(section, *names):
    missing = [n for n in names if not (isinstance(getattr(section, n), (int, float)) and getattr(section, n) > 0)]
    if missing:
        _incomplete("El Capítulo I requiere estas propiedades de la sección.", section,
                    ["section." + n for n in missing])


def _requirement(id_, provision, satisfied, message):
    return {"id": id_, "provision": provision, "satisfied": bool(satisfied), "message": message}


def uses_appendix_2(case, section) -> bool:
    """Appendix 2: rectangular filled members of normal weight concrete with a material above the limits of I1.3."""
    composite = case.composite
    if composite.kind != "filled" or section.type.upper() != "RECTANGULAR_HSS" or composite.concrete.lightweight:
        return False
    Fy, fc = case.material.Fy, composite.concrete.fc
    return (Fy > a2.FY_I13 or fc > a2.FC_I13) and Fy <= a2.FY_MAX and fc <= a2.FC_MAX


def _check_family(case, section):
    """The declared kind must match the family; I1.3 material limits, or Appendix 2 for rectangular filled members."""
    composite, family = case.composite, section.type.upper()
    allowed = {"filled": {"RECTANGULAR_HSS", "CIRCULAR_HSS"}, "encased": {"W"}, "beam": {"W"},
               "wall": {"COMPOSITE_WALL"}, "c_wall": {"COMPOSITE_WALL"}, "coupling_beam": {"COMPOSITE_WALL"}}[composite.kind]
    if family not in allowed:
        _blocked(f"composite.kind = {composite.kind} no se aplica a esta familia en el alcance implementado.", section,
                 kind=composite.kind)
    if abs(case.material.E - eq.E_STEEL) > 1e-6:
        _incomplete("El Capítulo I usa Es = 200000 MPa.", section, ["material.E"])
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
        _blocked("Materiales fuera de los límites de I1.3 y del alcance del Apéndice 2 (solo rellenos rectangulares de "
                 "concreto normal, con Fy ≤ 690 MPa y f'c ≤ 100 MPa).", section, failed=failed)


def _result(case, section, *, modes, governing, provisions, classification=None, requirements=(), notes=(), **values):
    return {"chapter": "I", "code": "ANSI/AISC 360-22", "section": section.name, "family": section.type.upper(),
            "kind": case.composite.kind, "inputs": {"Fy_mpa": case.material.Fy, "fc_mpa": case.composite.concrete.fc,
                                                    "wc_kg_m3": case.composite.concrete.wc},
            "classification": classification or {"elements": [], "slender": False},
            "provisions": provisions, "modes": modes, "governing_mode": governing,
            "governing_equation": modes[governing]["equation"], "requirements": list(requirements),
            "notes": list(notes), "limitations": list(_LIMITATIONS), **values}


# --- filled sections ------------------------------------------------------------------------

def _filled_geometry(case, section):
    """Concrete fill, net of the bars. Rectangular: inside corner radius t, as in Examples I.3 and I.4 (DI-2)."""
    filled = case.composite.filled
    bars = filled.bars if filled else []
    Asr = sum(b.area for b in bars)
    Isrx = sum(math.pi * b.db**4 / 64 + b.area * b.y**2 for b in bars)
    Isry = sum(math.pi * b.db**4 / 64 + b.area * b.x**2 for b in bars)
    extra = {"Asr": Asr, "Isrx": Isrx, "Isry": Isry, "Fysr": filled.Fysr if filled else 0.0, "bars": bars}
    if section.type.upper() == "CIRCULAR_HSS":
        _require(section, "od", "tdes", "area", "ix", "iy")
        ri = section.od / 2 - section.tdes
        ic = math.pi * ri**4 / 4
        return {"shape": "round", "Afill": math.pi * ri**2, "Ac": math.pi * ri**2 - Asr, "Icx": ic - Isrx, "Icy": ic - Isry,
                "t": section.tdes, "D": section.od, "ri": ri, **extra}
    _require(section, "h_out", "b_out", "tdes", "b", "h", "area", "ix", "iy")
    t = section.tdes
    r = 0.0 if case.composite.box else t                         # welded box: sharp corners (Design Guide 6, 2.5)
    bi, hi = section.b_out - 2 * t, section.h_out - 2 * t

    def inertia(width, depth):
        """Rounded inside rectangle about the axis parallel to width (squares less quarter circles at the corners)."""
        c = depth / 2 - r
        square = r * ((depth / 2) ** 3 - c**3) / 3
        quarter = c**2 * math.pi * r**2 / 4 + 2 * c * r**3 / 3 + math.pi * r**4 / 16
        return width * depth**3 / 12 - 4 * (square - quarter)

    fill = bi * hi - (4 - math.pi) * r**2
    return {"shape": "rect", "Afill": fill, "Ac": fill - Asr, "Icx": inertia(bi, hi) - Isrx, "Icy": inertia(hi, bi) - Isry,
            "t": t, "r": r, "bi": bi, "hi": hi, **extra}


def _filled_requirements(case, section, geometry, *, flexure):
    """I2.2a, I3.4a and the clearance of I2.2e, I3.4c."""
    ratio = section.area / (section.area + geometry["Afill"])
    out = [_requirement("As/Ag", "I3.4a(b)" if flexure else "I2.2a(a)", ratio >= 0.01,
                        "El acero debe ser al menos 1 % de la sección compuesta.")]
    filled = case.composite.filled
    if not filled:
        return out
    t = filled.transverse
    out.append(_requirement("transverse", "I2.2a(c)", (t.db >= 13.0 and t.spacing <= 400.0) or (t.db >= 10.0 and t.spacing <= 300.0),
                            "Refuerzo transversal mínimo: 10 mm a 300 mm o 13 mm a 400 mm."))
    if geometry["shape"] == "round":
        gaps = [geometry["ri"] - math.hypot(b.x, b.y) - b.db / 2 for b in filled.bars]
    else:
        gaps = [min(geometry["bi"] / 2 - abs(b.x), geometry["hi"] / 2 - abs(b.y)) - b.db / 2 for b in filled.bars]
    out.append(_requirement("bar_clearance", "I2.2e, I3.4c", all(g >= max(1.5 * b.db, 38.0) for g, b in zip(gaps, filled.bars)),
                            "Separación libre entre el tubo y las barras: al menos 1.5 db y 38 mm."))
    if flexure:
        out.append(_requirement("rho_sr", "I3.4a(c)", geometry["Asr"] / (section.area + geometry["Afill"]) >= 0.004,
                                "Con barras, la cuantía longitudinal mínima es 0.004."))
    return out


def _axial_class(section, geometry, Fy):
    limits = eq.filled_limits(shape=geometry["shape"], element="axial", Fy=Fy)
    lam = geometry["D"] / geometry["t"] if geometry["shape"] == "round" else max(section.b, section.h) / geometry["t"]
    cls = eq.classify_filled(ratio=lam, limits=limits)
    if cls == "exceeds_maximum":
        _blocked("La relación ancho-espesor supera el máximo permitido de la Tabla I1.1a.", section, ratio=lam)
    return {"lam": lam, "limits": limits, "class": cls}


def _appendix_2_compression(case, section, geometry):
    """Appendix 2, Section 2.1.2. The bars are not considered in the strength (2.1.1(e))."""
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    t = geometry["t"]
    b_t = max(section.b, section.h) / t
    if b_t > 5.0 * math.sqrt(eq.E_STEEL / Fy):
        _blocked("La relación ancho-espesor supera el máximo de 2.1.1(d): 5.00·√(E/Fy).", section, ratio=b_t)
    lam = a2.slenderness(b_t=b_t, Fy=Fy)
    Fn = a2.critical_stress(lam=lam, Fy=Fy)
    pno = {"Pno": a2.pno(Fn=Fn, As=section.area, fc=fc, Ac=geometry["Ac"]), "equation": "A-2-1", "Fn": Fn, "lambda_A2": lam}
    coefficient = eq.c3_filled(As=section.area, Asr=0.0, Ag=section.area + geometry["Afill"])
    return pno, coefficient, 0.0, 0.0, None, _filled_requirements(case, section, geometry, flexure=False)


def _filled_compression(case, section, geometry):
    if uses_appendix_2(case, section):
        return _appendix_2_compression(case, section, geometry)
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    As, Ac = section.area, geometry["Ac"]
    Asr = geometry["Asr"]
    Ec = eq.concrete_modulus(wc=case.composite.concrete.wc, fc=fc)
    c = _axial_class(section, geometry, Fy)
    Fn = None
    if c["class"] == "slender":
        Fn = (eq.critical_stress_round(D_t=c["lam"], Fy=Fy) if geometry["shape"] == "round"
              else eq.critical_stress_rectangular(lam=c["lam"]))
    pno = eq.pno_filled(cls=c["class"], shape=geometry["shape"], Fy=Fy, As=As, fc=fc, Ac=Ac, lam=c["lam"],
                        limits=c["limits"], Fn=Fn, Asr=Asr, Ec=Ec)
    coefficient = eq.c3_filled(As=As, Asr=Asr, Ag=As + geometry["Afill"])
    row = {"element": "wall", "ratio": c["lam"], "lambda_p": c["limits"]["p"], "lambda_r": c["limits"]["r"],
           "class": c["class"]}
    return pno, coefficient, geometry["Isrx"], geometry["Isry"], {"elements": [row], "slender": False, "reference": "Tabla I1.1a"}, (
        _filled_requirements(case, section, geometry, flexure=False))


# --- encased sections -----------------------------------------------------------------------

def _encased_geometry(case, section):
    _require(section, "area", "ix", "iy", "d", "bf", "tf", "tw", "zx", "zy")
    e = case.composite.encased
    bars = e.bars
    Asr = sum(b.area for b in bars)
    Isrx = sum(math.pi * b.db**4 / 64 + b.area * b.y**2 for b in bars)
    Isry = sum(math.pi * b.db**4 / 64 + b.area * b.x**2 for b in bars)
    return {"Ag": e.H * e.B, "Ac": e.H * e.B - section.area - Asr, "Asr": Asr, "Isrx": Isrx, "Isry": Isry,
            "Icx": e.B * e.H**3 / 12 - section.ix - Isrx, "Icy": e.H * e.B**3 / 12 - section.iy - Isry}


def _encased_requirements(case, section, geometry):
    """I2.1a, I2.1e (I3.3a and I3.3b repeat them): the limits that do not depend on ACI 318."""
    e, Ag = case.composite.encased, geometry["Ag"]
    t = e.transverse
    transverse = (t.db >= 13.0 and t.spacing <= 400.0) or (t.db >= 10.0 and t.spacing <= 300.0)
    clear = []
    for bar in e.bars:
        dx, dy = abs(bar.x) - section.bf / 2, abs(bar.y) - section.d / 2
        gap = math.hypot(max(dx, 0.0), max(dy, 0.0)) if dx > 0 or dy > 0 else -1.0
        clear.append(gap - bar.db / 2 >= max(1.5 * bar.db, 38.0))
    inside = all(abs(b.x) + b.db / 2 < e.B / 2 and abs(b.y) + b.db / 2 < e.H / 2 for b in e.bars)
    return [
        _requirement("As/Ag", "I2.1a(a)", section.area / Ag >= 0.01, "El núcleo de acero debe ser al menos 1 % de la sección."),
        _requirement("rho_sr", "I2.1a(c)", geometry["Asr"] / Ag >= 0.004, "La cuantía longitudinal mínima es 0.004."),
        _requirement("transverse", "I2.1a(b)", transverse and t.spacing <= 0.5 * min(e.B, e.H),
                     "Refuerzo transversal: 10 mm a 300 mm o 13 mm a 400 mm, y separación ≤ 0.5 de la menor dimensión."),
        _requirement("bar_clearance", "I2.1e(a)", all(clear),
                     "Separación libre entre núcleo y barras: al menos 1.5 db y 38 mm."),
        _requirement("bars_inside", "I2.1a(b)", inside, "Las barras deben quedar dentro del contorno de concreto."),
    ]


def _wall_geometry(case):
    wall = case.composite.wall
    bi, hi = wall.tsc - 2 * wall.t, wall.length - 2 * wall.tf
    return {"bi": bi, "hi": hi, "Ac": bi * hi, "Ag": wall.length * wall.tsc, "Asw": 2 * wall.t * wall.length,
            "Icx": bi * hi**3 / 12, "Icy": hi * bi**3 / 12}


def _wall_is_slender(case):
    wall = case.composite.wall
    return wall.b / wall.t > 1.2 * math.sqrt(eq.E_STEEL / case.material.Fy)


def _wall_requirements(case, section, geometry, *, compression=False):
    """I1.6, I1.6a, I1.6b. In compression only, allow_slender_plates replaces I1-4 by the strength of Commentary I1.6a."""
    wall = case.composite.wall
    ratio = section.area / geometry["Ag"]
    ties = eq.wall_tie_limit(t=wall.t, tsc=wall.tsc, dtie=wall.dtie)
    return [
        _requirement("rho_s", "I1.6", 0.01 <= ratio <= 0.10, "Las placas de acero deben ser entre 1 % y 10 % de la sección."),
        _requirement("b/t", "I1.6a (I1-4)", (compression and wall.allow_slender_plates) or not _wall_is_slender(case),
                     "Esbeltez de la placa: b/t ≤ 1.2·√(E/Fy)."),
        _requirement("st", "I1.6b", wall.st <= wall.tsc, "Separación de amarres ≤ tsc."),
        _requirement("st/t", "I1.6b (I1-5M)", wall.st / wall.t <= ties["limit"], "Separación de amarres: st/t ≤ 0.38·√(Es/(2α+1))."),
    ]


def _service_stiffnesses(case, section, geometry, kind, Is, Isr, Ec, Ic, coefficient, Pno) -> dict:
    """Design Guide 6, Section 2.8, for serviceability analyses; they take no part in the strength. Gc = 0.4Ec as in I1-3."""
    As, Ac = section.area, geometry["Ac"]
    out = {"EI_service": dg06_members.service_stiffness(kind=kind, EsIs=eq.E_STEEL * Is, EsIsr=eq.E_STEEL * Isr, EcIc=Ec * Ic,
                                                        C=coefficient, P_over_Pno=abs(case.Pu) * 1000.0 / Pno),
           "EA_service": dg06_members.axial_stiffness(EsAs=eq.E_STEEL * As, EsAsr=eq.E_STEEL * geometry["Asr"], EcAc=Ec * Ac)}
    if kind == "filled" and geometry["shape"] == "rect":
        out["GA_service"] = dg06_members.shear_stiffness_rect(GsAs=eq.G_STEEL * As, GcAc=0.4 * Ec * Ac)
    if kind == "filled" and geometry["shape"] == "round" and section.j is not None:
        out["GJ_service"] = dg06_members.torsional_stiffness_round(
            GsJs=eq.G_STEEL * section.j, GcJc=0.4 * Ec * math.pi * geometry["ri"] ** 4 / 2,
            As_over_Ag=As / (As + geometry["Afill"]))
    return out


def composite_compression(case: SteelCase, section: Section, bare_steel=None) -> dict:
    """I2.1b, I2.2b and I2.3a: flexural buckling about both axes; not less than the bare steel of Chapter E."""
    _check_family(case, section)
    kind = case.composite.kind
    if kind == "beam":
        _blocked("La viga compuesta con fuerza axial no está cubierta por I3.2.", section)
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    Ec = eq.concrete_modulus(wc=case.composite.concrete.wc, fc=fc)
    f, ln = case.factors, case.lengths
    phi = eq.PHI_C_WALL if kind == "wall" else eq.PHI_C
    point_c = 0.0
    if kind == "wall":
        geometry = _wall_geometry(case)
        wall = case.composite.wall
        if wall.allow_slender_plates and _wall_is_slender(case):
            Fn = eq.wall_slender_plate_stress(b_t=wall.b / wall.t, Fy=Fy)
            pno = {"Pno": eq.pno_wall_slender(Fn=Fn, As=section.area, fc=fc, Ac=geometry["Ac"]), "equation": "C-I1-2"}
        else:
            pno = {"Pno": eq.pno_wall(Fy=Fy, As=section.area, fc=fc, Ac=geometry["Ac"]), "equation": "I2-15"}
        coefficient, Isrx, Isry, classification = 0.35, 0.0, 0.0, None
        requirements = _wall_requirements(case, section, geometry, compression=True)
        c_name = "C_I1_1"
    elif kind == "filled":
        geometry = _filled_geometry(case, section)
        pno, coefficient, Isrx, Isry, classification, requirements = _filled_compression(case, section, geometry)
        c_name = "C3"
        point_c = (0.95 if geometry["shape"] == "round" else 0.85) * fc * geometry["Ac"]
    else:
        geometry = _encased_geometry(case, section)
        point_c = 0.85 * fc * geometry["Ac"]
        e = case.composite.encased
        pno = {"Pno": eq.pno_encased(Fy=Fy, As=section.area, Fysr=e.Fysr, Asr=geometry["Asr"], fc=fc, Ac=geometry["Ac"]),
               "equation": "I2-7"}
        coefficient = eq.c1_encased(As=section.area, Asr=geometry["Asr"], Ag=geometry["Ag"])
        Isrx, Isry = geometry["Isrx"], geometry["Isry"]
        classification, requirements = None, _encased_requirements(case, section, geometry)
        c_name = "C1"
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
        if kind == "wall":
            modes[f"FB-{axis}"].update(EA_eff=eq.wall_axial_stiffness(As=section.area, Ec=Ec, Ac=geometry["Ac"]),
                                       GA_eff=eq.wall_shear_stiffness(Asw=geometry["Asw"], Ec=Ec, Ac=geometry["Ac"]))
        else:
            modes[f"FB-{axis}"].update(_service_stiffnesses(case, section, geometry, kind, Is, Isr, Ec, Ic, coefficient, pno["Pno"]))
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
    return _result(case, section, modes=modes, governing=governing, provisions=["I1", modes[governing]["provision"]],
                   classification=classification, requirements=requirements, notes=notes,
                   Pn_kN=modes[governing]["Pn_kN"], phi_c=phi, available_kN=available)


def composite_tension(case: SteelCase, section: Section) -> dict:
    """I2-8 and I2-14: yielding of the steel section and the bars (concrete neglected, I1.2)."""
    _check_family(case, section)
    kind = case.composite.kind
    if kind == "beam":
        _blocked("La viga compuesta con fuerza axial no está cubierta por I3.2.", section)
    _require(section, "area")
    e = case.composite.encased or case.composite.filled
    Asr, Fysr = (sum(b.area for b in e.bars), e.Fysr) if e else (0.0, 0.0)
    if uses_appendix_2(case, section):
        Asr, Fysr = 0.0, 0.0                                         # Appendix 2, 2.1.1(e)
    pn = eq.tension_yielding(Fy=case.material.Fy, As=section.area, Fysr=Fysr, Asr=Asr)
    provision, equation = {"encased": ("I2.1c", "I2-8"), "filled": ("I2.2c", "I2-14"), "wall": ("I2.3b", "I2-16")}[kind]
    mode = {"limit_state": "tensile_yielding", "provision": provision, "applies": True,
            "equation": equation, "Pn_kN": pn / 1000.0, "available_kN": eq.PHI_T * pn / 1000.0}
    return _result(case, section, modes={"TY": mode}, governing="TY", provisions=["I1", mode["provision"]],
                   Pn_kN=pn / 1000.0, phi_t=eq.PHI_T, available_kN=mode["available_kN"])


# --- flexure --------------------------------------------------------------------------------

def _flexure_output(case, section, *, mn_mode, classification=None, requirements=(), notes=(), provisions):
    mn = mn_mode["Mn_kNm"]
    mode = {"limit_state": "flexural_yielding", "applies": True, **mn_mode, "available_kNm": eq.PHI_B * mn}
    modes = {"Y": mode}
    if case.composite.kind == "filled":
        modes["LB"] = {"limit_state": "local_buckling", "provision": "I1.4", "applies": True, "equation": "Tabla I1.1b"}
    return _result(case, section, modes=modes, governing="Y", provisions=provisions, classification=classification,
                   requirements=requirements, notes=notes, Mn_kNm=mn, phi_b=eq.PHI_B, available_kNm=eq.PHI_B * mn)


def _tension_control(case, hn, h, bars, Fysr, pno, requirements, provision):
    """I3.3a(e), I3.4a(d) by Design Guide 6, Section 2.4.1: applies to beam members with Pu < 0.10Pn."""
    out = dg06_members.tension_control(hn=hn, h=h, v_tension=min(v for _, v in bars), Fysr=Fysr)
    fields = {"epsilon_t": out["epsilon_t"], "epsilon_limit": out["epsilon_limit"]}
    notes = []
    if abs(case.Pu) * 1000.0 < 0.10 * pno and case.composite.flexural_member is not False:
        if case.composite.flexural_member:
            requirements.append(_requirement("tension_controlled", provision, out["tension_controlled"],
                                             "Viga con Pu < 0.10Pn: εt debe alcanzar εy + 0.003 (AISC Design Guide 6, 2.4.1)."))
        else:
            notes.append(f"Si el miembro es una viga, {provision} exige sección controlada por tracción: indique "
                         "composite.flexural_member.")
    return fields, notes


def _filled_flexure(case, section, axis):
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    geometry = _filled_geometry(case, section)
    requirement = _filled_requirements(case, section, geometry, flexure=True)
    bars = [(b.area, b.y if axis == "x" else b.x) for b in geometry["bars"]]
    Fysr = geometry["Fysr"]
    if geometry["shape"] == "round":
        lam = geometry["D"] / geometry["t"]
        limits = eq.filled_limits(shape="round", element="flexure_round", Fy=Fy)
        cls = eq.classify_filled(ratio=lam, limits=limits)
        if cls == "exceeds_maximum":
            _blocked("D/t supera el máximo permitido de la Tabla I1.1b.", section, ratio=lam)
        out = eq.round_plastic_moment(Fy=Fy, fc=fc, D=geometry["D"], t=geometry["t"], Fysr=Fysr, bars=bars)
        row = {"element": "wall", "ratio": lam, "lambda_p": limits["p"], "lambda_r": limits["r"], "class": cls}
        classification = {"elements": [row], "slender": False, "reference": "Tabla I1.1b"}
        if cls == "compact":
            mode = {"provision": "I3.4b(a)", "equation": "I3-5a", "Mp_kNm": out["Mp"] / 1e6, "hn_mm": out["hn_mm"],
                    "Md_kNm": out["Md"] / 1e6, "Mn_kNm": out["Mp"] / 1e6}
            return _flexure_output(case, section, mn_mode=mode, requirements=requirement, provisions=["I1", "I3.4"],
                                   classification=classification)
        # Noncompact (lambda_r = maximum permitted, so there is no slender round section): My by Design Guide 6 (DI-3).
        Ec = eq.concrete_modulus(wc=case.composite.concrete.wc, fc=fc)
        yielding = dg06.round_yield_moment(Fy=Fy, fc=fc, Ec=Ec, D=geometry["D"], t=geometry["t"], Fysr=Fysr, bars=bars)
        mn = eq.noncompact_moment(Mp=out["Mp"], My=yielding["My"], lam=lam, limits=limits)
        mode = {"provision": "I3.4b(b)", "equation": "I3-5b", "Mp_kNm": out["Mp"] / 1e6, "My_kNm": yielding["My"] / 1e6,
                "yn_mm": yielding["yn_mm"], "Mn_kNm": mn / 1e6}
        notes = ["My de la sección redonda por el procedimiento de AISC Design Guide 6, ejemplo 2.7; no es una ecuación de la "
                 "Specification (decisión DI-3)."]
        return _flexure_output(case, section, mn_mode=mode, requirements=requirement, provisions=["I1", "I3.4"],
                               classification=classification, notes=notes)
    t = geometry["t"]
    # Elements: the flange is perpendicular to the bending direction, the web is parallel to it.
    H, bi, hi, flange, web, Zs = ((section.h_out, geometry["bi"], geometry["hi"], section.b, section.h, section.zx)
                                  if axis == "x" else
                                  (section.b_out, geometry["hi"], geometry["bi"], section.h, section.b, section.zy))
    if uses_appendix_2(case, section):
        b_t = max(section.b, section.h) / t
        if b_t > 5.0 * math.sqrt(eq.E_STEEL / Fy):
            _blocked("La relación ancho-espesor supera el máximo de 2.1.1(d): 5.00·√(E/Fy).", section, ratio=b_t)
        Fn = a2.critical_stress(lam=a2.slenderness(b_t=b_t, Fy=Fy), Fy=Fy)
        out = a2.nominal_moment(Fy=Fy, Fn=Fn, fc=fc, H=H, tw=t, tf=t, bi=bi)
        mode = {"provision": "Apéndice 2, 2.1.3", "equation": "90 % de la distribución de tensiones (Apéndice 2)", "Fn_mpa": Fn,
                "a_mm": out["a_mm"], "Msd_kNm": out["Msd"] / 1e6, "Mn_kNm": out["Mn"] / 1e6}
        return _flexure_output(case, section, mn_mode=mode, requirements=requirement, provisions=["Apéndice 2"])
    if not Zs:
        _incomplete("La flexión del relleno requiere Z del perfil.", section, ["section.zx" if axis == "x" else "section.zy"])
    rows, candidates = [], {}
    worst = "compact"
    for name, ratio in (("flange", flange / t), ("web", web / t)):
        limits = eq.filled_limits(shape="rect", element=name, Fy=Fy)
        cls = eq.classify_filled(ratio=ratio, limits=limits)
        if cls == "exceeds_maximum":
            _blocked("La relación ancho-espesor supera el máximo permitido de la Tabla I1.1b.", section, element=name, ratio=ratio)
        rows.append({"element": name, "ratio": ratio, "lambda_p": limits["p"], "lambda_r": limits["r"], "class": cls})
        candidates[name] = (ratio, limits, cls)
        worst = max(worst, cls, key=["compact", "noncompact", "slender"].index)
    classification = {"elements": rows, "slender": False, "reference": "Tabla I1.1b"}
    if bars and worst != "compact":
        _blocked("Relleno rectangular no compacto o esbelto con barras: Fig. C-I3.8 no las considera y la Specification no da "
                 "un procedimiento (decisión DI-3).", section, classification=worst)
    plastic = eq.rect_plastic_moment(Fy=Fy, fc=fc, Zs=Zs, t=t, bi=bi, hi=hi, r=geometry["r"], Fysr=Fysr, bars=bars)
    if worst == "compact":
        mode = {"provision": "I3.4b(a)", "equation": "I3-5a", "Mp_kNm": plastic["Mp"] / 1e6, "hn_mm": plastic["hn_mm"],
                "Md_kNm": plastic["Md"] / 1e6, "Mn_kNm": plastic["Mp"] / 1e6}
        if bars:
            pno = Fy * section.area + Fysr * geometry["Asr"] + 0.85 * fc * geometry["Ac"]
            control, notes = _tension_control(case, plastic["hn_mm"], H, bars, Fysr, pno, requirement, "I3.4a(d)")
            return _flexure_output(case, section, mn_mode={**mode, **control}, classification=classification,
                                   requirements=requirement, notes=notes, provisions=["I1", "I3.4"])
    elif worst == "noncompact":
        yielding = eq.rect_yield_moment(Fy=Fy, fc=fc, H=H, tw=t, tf=t, bi=bi)
        values = [eq.noncompact_moment(Mp=plastic["Mp"], My=yielding["My"], lam=ratio, limits=limits)
                  for ratio, limits, cls in candidates.values() if cls == "noncompact"]
        mn = min(values)
        mode = {"provision": "I3.4b(b)", "equation": "I3-5b", "Mp_kNm": plastic["Mp"] / 1e6,
                "My_kNm": yielding["My"] / 1e6, "a_y_mm": yielding["a_mm"], "Mn_kNm": mn / 1e6}
    else:
        Fn = eq.critical_stress_rectangular(lam=flange / t)
        first = eq.rect_first_yield_moment(Fy=Fy, Fn=min(Fn, Fy), fc=fc, H=H, tw=t, tf=t, bi=bi)
        mode = {"provision": "I3.4b(c)", "equation": "I3.4b(c), Fig. C-I3.8(c)", "Fn_mpa": min(Fn, Fy),
                "a_cr_mm": first["a_mm"], "Mcr_kNm": first["Mcr"] / 1e6, "Mn_kNm": first["Mcr"] / 1e6}
    return _flexure_output(case, section, mn_mode=mode, classification=classification, requirements=requirement,
                           provisions=["I1", "I3.4"])


def _encased_flexure(case, section, axis):
    Fy = case.material.Fy
    e = case.composite.encased
    geometry = _encased_geometry(case, section)
    requirements = _encased_requirements(case, section, geometry)
    Zs = section.zx if axis == "x" else section.zy
    if e.flexure_method == "steel":
        mn = Fy * Zs
        mode = {"provision": "I3.3a(2)", "equation": "Mn = Fy·Z (acero solo)", "Mn_kNm": mn / 1e6}
        notes = ["I3.3a(2): plástico sobre el perfil de acero solo."]
    else:
        if not e.anchors_provided:
            _incomplete("I3.3a(3) exige conectores: declare composite.encased.anchors_provided = true o use "
                        "flexure_method = steel.", section, ["composite.encased.anchors_provided"])
        h, b = (e.H, e.B) if axis == "x" else (e.B, e.H)
        bars = [(bar.area, bar.y if axis == "x" else bar.x) for bar in e.bars]
        out = eq.encased_plastic_moment(axis=axis, Fy=Fy, Fysr=e.Fysr, fc=case.composite.concrete.fc, b=b, h=h, d=section.d,
                                        bf=section.bf, tf=section.tf, tw=section.tw, As=section.area, Zs=Zs, bars=bars)
        pno = eq.pno_encased(Fy=Fy, As=section.area, Fysr=e.Fysr, Asr=geometry["Asr"], fc=case.composite.concrete.fc,
                             Ac=geometry["Ac"])
        control, control_notes = _tension_control(case, out["hn_mm"], h, bars, e.Fysr, pno, requirements, "I3.3a(e)")
        mode = {"provision": "I3.3a(3)", "equation": "Distribución plástica compuesta (I1.2a)", "hn_mm": out["hn_mm"],
                "Md_kNm": out["Md"] / 1e6, "Mn_kNm": out["Mp"] / 1e6, **control}
        notes = ["I3.3a(3): plástico sobre la sección compuesta.", *control_notes]
    return _flexure_output(case, section, mn_mode=mode, requirements=requirements, notes=notes, provisions=["I1", "I3.3"])


def _anchor_factors(beam, section):
    """Rg and Rp of I8.2a."""
    deck = beam.deck
    if deck is None:
        return 1.0, 0.75
    if deck.orientation == "parallel":
        return (1.0 if deck.wr / deck.hr >= 1.5 else 0.85), 0.75
    if deck.emid_ht_at_least_50 is None:
        _incomplete("Deck perpendicular a la viga: indique composite.beam.deck.emid_ht_at_least_50 (I8.2a).", section,
                    ["composite.beam.deck.emid_ht_at_least_50"])
    per_rib = beam.studs.per_rib
    return (1.0 if per_rib == 1 else 0.85 if per_rib == 2 else 0.7), (0.75 if deck.emid_ht_at_least_50 else 0.6)


def _beam_requirements(beam, section, Fy):
    """I3.2c and I8.1 to I8.2: the geometric limits that the input declares."""
    out = []
    deck, studs = beam.deck, beam.studs
    if deck:
        out += [_requirement("hr", "I3.2c.1(a)", deck.hr <= 75.0, "Altura nominal de nervio ≤ 75 mm."),
                _requirement("wr", "I3.2c.1(a)", deck.wr >= 50.0, "Ancho medio de nervio ≥ 50 mm."),
                _requirement("tc", "I3.2c.1(c)", beam.tc >= 50.0, "Espesor de losa sobre el deck ≥ 50 mm.")]
    if studs:
        out.append(_requirement("dsa_max", "I8.1", studs.d <= (19.0 if deck else 25.0),
                                "Diámetro de perno ≤ 19 mm (hasta 25 mm solo en losa maciza)."))
        out.append(_requirement("dsa_tf", "I8.1", studs.over_web or studs.d <= 2.5 * section.tf,
                                "Diámetro ≤ 2.5 tf si el perno no está sobre el alma."))
        out.append(_requirement("length", "I8.2", studs.length >= 4 * studs.d, "Longitud del perno ≥ 4 diámetros."))
        if deck:
            out += [_requirement("stud_above_deck", "I3.2c.1(b)", studs.length - deck.hr >= 38.0,
                                 "El perno debe sobresalir al menos 38 mm del deck."),
                    _requirement("stud_cover", "I3.2c.1(b)", deck.hr + beam.tc - studs.length >= 13.0,
                                 "Recubrimiento sobre el perno ≥ 13 mm.")]
    return out


def _beam_flexure(case, section, flexure_strength):
    """I3.2a(a) positive flexure; I3.2b steel section alone for negative flexure (Chapter F)."""
    beam, Fy = case.composite.beam, case.material.Fy
    if beam.moment == "negative":
        return None
    _require(section, "area", "d", "bf", "tf", "tw", "h_tw_ratio")
    if section.h_tw_ratio > 3.76 * math.sqrt(eq.E_STEEL / Fy):
        _blocked("h/tw > 3.76·√(E/Fy): I3.2a(b) exige superposición elástica con datos de apuntalamiento, no implementada.",
                 section, h_tw=section.h_tw_ratio)
    if beam.studs is None and beam.channels is None:
        _incomplete("La viga compuesta requiere conectores: indique composite.beam.studs o channels (I3.2d).", section,
                    ["composite.beam.studs", "composite.beam.channels"])
    if beam.channels is not None and beam.deck is not None:
        _blocked("I8.2b cubre conectores de canal en losa maciza, no sobre deck.", section)
    concrete = case.composite.concrete
    Ec = eq.concrete_modulus(wc=concrete.wc, fc=concrete.fc)
    left = beam.left_beam_spacing / 2 if beam.left_beam_spacing else beam.left_edge_distance
    right = beam.right_beam_spacing / 2 if beam.right_beam_spacing else beam.right_edge_distance
    width = eq.effective_slab_width(span=beam.span, left=left, right=right)
    b, hr = width["b_mm"], beam.deck.hr if beam.deck else 0.0
    sum_qn, anchors = 0.0, {}
    if beam.studs:
        Rg, Rp = _anchor_factors(beam, section)
        Asa = math.pi * beam.studs.d**2 / 4
        stud = eq.stud_strength(Asa=Asa, fc=concrete.fc, Ec=Ec, Rg=Rg, Rp=Rp, Fu=beam.studs.Fu)
        sum_qn += beam.studs.count * stud["Qn"]
        anchors.update(Rg=Rg, Rp=Rp, Qn_stud_kN=stud["Qn"] / 1000.0)
    if beam.channels:
        c = beam.channels
        qn = eq.channel_strength(tf=c.tf, tw=c.tw, la=c.la, fc=concrete.fc, Ec=Ec)
        sum_qn += c.count * qn
        anchors["Qn_channel_kN"] = qn / 1000.0
    crushing, steel = 0.85 * concrete.fc * b * beam.tc, Fy * section.area       # I3-1a, I3-1b; ribs neglected (I3.2c)
    C = min(crushing, steel, sum_qn)                                            # I3-1c
    a = C / (0.85 * concrete.fc * b)
    out = eq.beam_plastic_moment(C=C, a=a, Ycon=beam.tc + hr, Fy=Fy, As=section.area, d=section.d, bf=section.bf,
                                 tf=section.tf, tw=section.tw)
    degree = sum_qn / min(crushing, steel)
    mode = {"provision": "I3.2a(a)", "equation": "Distribución plástica (I3.2a)", "b_mm": b, "Ycon_mm": beam.tc + hr,
            "Vp_crushing_kN": crushing / 1000.0, "Vp_steel_kN": steel / 1000.0, "SumQn_kN": sum_qn / 1000.0,
            "C_kN": C / 1000.0, "a_mm": a, "PNA": out["pna"], "x_mm": out["x_mm"], "degree_of_composite_action": degree,
            **anchors, "Mn_kNm": out["Mn"] / 1e6}
    requirements = _beam_requirements(beam, section, Fy)
    notes = []
    # Commentary I3.2d: conditions under which slip capacity is not a concern.
    if not (beam.span <= 9100.0 or degree >= 0.5 or sum_qn / (beam.span / 2) >= 230.0):
        notes.append("I3.2d: revise la ductilidad de la conexión; no se cumple ninguna condición del Commentary "
                     "(luz ≤ 9.1 m, acción compuesta ≥ 50 %, o conectores ≥ 230 kN/m).")
    if not beam.shored:
        if beam.Mu_construction is None:
            _incomplete("Viga sin apuntalar: indique composite.beam.Mu_construction (I3.1b).", section,
                        ["composite.beam.Mu_construction"])
        bare = flexure_strength()
        mode["construction_available_kNm"] = bare["available_kNm"]
        requirements.append(_requirement("construction", "I3.1b", beam.Mu_construction <= bare["available_kNm"],
                                         "La sección de acero sola debe resistir las cargas de construcción."))
    return _flexure_output(case, section, mn_mode=mode, requirements=requirements, notes=notes, provisions=["I1", "I3.2", "I8.2"])


def _wall_moment(case, P_N):
    wall = case.composite.wall
    geometry = _wall_geometry(case)
    return eq.wall_plastic_moment(Fy=case.material.Fy, fc=case.composite.concrete.fc, H=wall.length, t=wall.t, tf=wall.tf,
                                  bi=geometry["bi"], P=P_N)


def _wall_flexure(case, section):
    """I3.5: plastic stress distribution (I1.2a) in the plane of the wall."""
    out = _wall_moment(case, 0.0)
    mode = {"provision": "I3.5", "equation": "Distribución plástica (I1.2a)", "a_mm": out["a_mm"], "Mn_kNm": out["Mp"] / 1e6}
    return _flexure_output(case, section, mn_mode=mode, requirements=_wall_requirements(case, section, _wall_geometry(case)),
                           provisions=["I1", "I3.5"])


def composite_flexure(case: SteelCase, section: Section, axis: str, flexure_strength) -> dict:
    """I3: flexure about x or y. flexure_strength is the Chapter F calculation of the steel section alone."""
    _check_family(case, section)
    kind = case.composite.kind
    if axis not in {"x", "y"}:
        _blocked("Mw y Mz no se aplican a miembros compuestos.", section, axis=axis)
    if kind == "wall":
        if axis != "x":
            _blocked("Muro: solo se calcula la flexión en su plano (Mux); la flexión fuera del plano no está cubierta.", section)
        return _wall_flexure(case, section)
    if kind == "beam":
        if axis != "x":
            _blocked("La viga compuesta se calcula en su eje mayor (I3.2).", section, axis=axis)
        result = _beam_flexure(case, section, flexure_strength)
        return flexure_strength() if result is None else result
    return _filled_flexure(case, section, axis) if kind == "filled" else _encased_flexure(case, section, axis)


def composite_shear(case: SteelCase, section: Section, axis: str, shear_strength) -> dict:
    """I4.1(a) and I4.3: steel section alone (Chapter G). I4.2: filled sections with Kc = 1 (DI-4)."""
    _check_family(case, section)
    if case.composite.kind == "wall":
        if axis != "x":
            _blocked("Muro: I4.4 cubre el cortante en su plano (Vux); fuera del plano no está cubierto.", section)
        geometry = _wall_geometry(case)
        Ec = eq.concrete_modulus(wc=case.composite.concrete.wc, fc=case.composite.concrete.fc)
        out = eq.wall_shear(Asw=geometry["Asw"], Fy=case.material.Fy, Ec=Ec, Ac=geometry["Ac"])
        vn = out["Vn"] / 1000.0
        mode = {"limit_state": "shear", "provision": "I4.4", "applies": True, "equation": "I4-2", "Asw_mm2": geometry["Asw"],
                "Ac_mm2": geometry["Ac"], "Ks_N": out["Ks_N"], "Ksc_N": out["Ksc_N"], "Vn_kN": vn,
                "available_kN": eq.PHI_V_WALL * vn}
        return _result(case, section, modes={"V": mode}, governing="V", provisions=["I1", "I4.4"], Vn_kN=vn,
                       phi_v=eq.PHI_V_WALL, available_kN=mode["available_kN"])
    if case.composite.kind != "filled":
        return shear_strength()
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    geometry = _filled_geometry(case, section)
    if geometry["shape"] == "round":
        Av = 2 * section.area / math.pi
    elif case.composite.box:
        Av = 2 * (section.h_out if axis == "x" else section.b_out) * geometry["t"]   # Design Guide 6, Example 2.5
    else:
        Av = 2 * (section.h if axis == "x" else section.b) * geometry["t"]
    vn = eq.shear_filled(Av=Av, Fy=Fy, Kc=1.0, Ac=geometry["Ac"], fc=fc)
    mode = {"limit_state": "shear", "provision": "I4.2", "applies": True, "equation": "I4-1", "Av_mm2": Av,
            "Ac_mm2": geometry["Ac"], "Kc": 1.0, "Vn_kN": vn / 1000.0, "available_kN": eq.PHI_V_FILLED * vn / 1000.0}
    return _result(case, section, modes={"V": mode}, governing="V", provisions=["I1", "I4.2"],
                   notes=["Kc = 1: límite inferior de I4.2 (decisión DI-4)."], Vn_kN=vn / 1000.0,
                   phi_v=eq.PHI_V_FILLED, available_kN=mode["available_kN"])


def composite_method2(case: SteelCase, section: Section, checks: list) -> dict:
    """Commentary I5, Method 2 (M2) and Method 2 simplified (M2S), from the strengths of the component checks."""
    by_id = {c.id: c for c in checks}
    composite, simplified = case.composite, case.composite.interaction == "M2S"
    if composite.kind not in {"filled", "encased"}:
        _blocked("El Método 2 se aplica a miembros embebidos y rellenos compactos.", section, kind=composite.kind)
    if case.Pu < 0:
        _blocked("El Método 2 del Commentary cubre compresión con flexión; use interaction = H1 con tracción.", section)
    missing = [c.id for c in checks if c.capacity is None]
    if missing:
        raise IncompleteSectionDataError("La interacción necesita la resistencia de diseño de cada componente.",
                                         code="INTERACTION_COMPONENT_MISSING",
                                         details={"section": section.name, "checks": missing})
    axial = by_id.get("axial")
    if axial is None and not simplified:
        _blocked("El Método 2 requiere fuerza axial; use interaction = M2S o H1 para flexión biaxial.", section)
    if case.Mux and case.Muy and not simplified:
        _blocked("El Método 2 con puntos A, B, C y D es para flexión en un eje; use interaction = M2S (C-I5-1).", section)
    flexures = [by_id[i] for i in ("flexure_x", "flexure_y") if i in by_id]
    classes = {row["class"] for c in [*flexures, *([axial] if axial else [])] for row in c.result["classification"]["elements"]}
    if classes - {"compact"}:
        _blocked("El Método 2 exige una sección rellena compacta (Commentary I5); use H1 o I5.", section)
    if any("Md_kNm" not in f.result["modes"]["Y"] for f in flexures):
        _blocked("El Método 2 usa la distribución plástica compuesta: indique flexure_method = composite.", section)

    fx, fy = by_id.get("flexure_x"), by_id.get("flexure_y")
    Pr = axial.demand if axial else 0.0
    A = axial.result["modes"][axial.result["governing_mode"]] if axial else None
    lam = A["Pn_kN"] / A["Pno_kN"] if A else None                    # the same slenderness factor for A, C and D
    PA = eq.PHI_C * A["Pn_kN"] if A else 0.0
    PC = eq.PHI_C * lam * A["PC_kN"] if A else 0.0
    terms = {"lambda": lam, "Pr_kN": Pr, "PA_kN": PA, "PC_kN": PC}
    if simplified and composite.biaxial_shape_factor and fx and fy:
        shape = composite.kind if composite.kind == "encased" else _filled_geometry(case, section)["shape"]
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
        nominal = [(0.0, Y["Mn_kNm"]), (A["PC_kN"] / 2, Y["Md_kNm"]), (A["PC_kN"], Y["Mn_kNm"]), (A["Pno_kN"], 0.0)]
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
    return _result(case, section, modes={"M2": mode}, governing="M2", provisions=[mode["provision"]], ratio=mode["ratio"],
                   notes=notes)


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
    out = _wall_moment(case, P_N)
    if out["within_section"]:
        capacity = eq.PHI_B * out["Mp"] / 1e6
        ratio = flexure.demand / capacity if capacity > 0 else float("inf")
    else:
        limit = out["P_max_N"] if P_N > 0 else out["P_min_N"]
        capacity, ratio = 0.0, P_N / limit
    mode = {"limit_state": "combined_flexure_axial", "provision": "I5(c)", "applies": True, "equation": "I1.2a",
            "Pr_kN": case.Pu, "Mr_kNm": flexure.demand, "a_mm": out["a_mm"], "Mc_at_Pr_kNm": capacity, "ratio": ratio}
    return _result(case, section, modes={"I5c": mode}, governing="I5c", provisions=["I5(c)", "I1.2a"], ratio=ratio,
                   notes=["Se supone que Pr y Mr incluyen los efectos de segundo orden (Capítulo C, decisión DH-3).",
                          "I5(c): Mn a la fuerza axial requerida; la estabilidad se verifica en el chequeo axial."])


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


def composite_load_transfer(case: SteelCase, section: Section) -> dict:
    """I6: required longitudinal shear and the largest available transfer mechanism; they are not superimposed."""
    _check_family(case, section)
    composite, transfer = case.composite, case.composite.load_transfer
    if composite.kind not in {"filled", "encased"}:
        _blocked("I6 se aplica a miembros embebidos y rellenos.", section, kind=composite.kind)
    Fy, fc = case.material.Fy, composite.concrete.fc
    slender = False
    if composite.kind == "encased":
        geometry = _encased_geometry(case, section)
        pno = eq.pno_encased(Fy=Fy, As=section.area, Fysr=composite.encased.Fysr, Asr=geometry["Asr"], fc=fc, Ac=geometry["Ac"])
        fs_as = Fy * section.area
    else:
        geometry = _filled_geometry(case, section)
        pno = _filled_compression(case, section, geometry)[0]["Pno"]
        slender = pno and _axial_class(section, geometry, Fy)["class"] == "slender" and not uses_appendix_2(case, section)
        Fn = _filled_compression(case, section, geometry)[0].get("Fn")
        fs_as = (Fn if slender else Fy) * section.area
        if slender and transfer.applied_to != "concrete":
            _blocked("Relleno esbelto: la fuerza no puede aplicarse al acero (Nota de I6.2a y Commentary I6.2).", section)
    force = eq.transfer_force(Pr=transfer.Pr * 1000.0, Fs_As=fs_as, Pno=pno, applied_to=transfer.applied_to,
                              steel_fraction=transfer.steel_fraction)
    available, requirements = {}, []
    if transfer.bearing_area:
        available["bearing"] = 0.65 * eq.bearing_transfer(fc=fc, A1=transfer.bearing_area)
    if transfer.anchor_count:
        if composite.anchor is None:
            _incomplete("I6.3b: indique composite.anchor para calcular la resistencia de los anclajes.", section, ["composite.anchor"])
        result = composite_anchor(case.model_copy(update={"composite": composite.model_copy(update={"anchor": composite.anchor.model_copy(
            update={"Qrv": 1.0, "Qrt": 0.0})})}), section)
        mode = next(iter(result["modes"].values()))
        available["anchors"] = transfer.anchor_count * mode.get("Qcv_kN", 0.0) * 1000.0
    if transfer.bond_length:
        if composite.kind != "filled" or slender:
            _blocked("I6.3: la adherencia directa no se usa en embebidos ni en rellenos esbeltos (Commentary I6.3).", section)
        if transfer.bond_slip_controlled is not True:
            _incomplete("I6.3: declare composite.load_transfer.bond_slip_controlled = true para usar adherencia directa.", section,
                        ["composite.load_transfer.bond_slip_controlled"])
        t = geometry["t"]
        if geometry["shape"] == "rect":
            r = geometry["r"]
            pb = 2 * (geometry["bi"] + geometry["hi"]) - 8 * r + 2 * math.pi * r
            depth, limit = max(section.h_out, section.b_out), 2 * min(section.h_out, section.b_out)
        else:
            pb, depth, limit = 2 * math.pi * geometry["ri"], geometry["D"], 2 * geometry["D"]
        fin = eq.bond_stress(t=t, H=depth, rectangular=geometry["shape"] == "rect")
        available["bond"] = 0.50 * eq.bond_transfer(pb=pb, Lin=transfer.bond_length, Fin=fin)
        requirements.append(_requirement("Lin", "I6.4b", transfer.bond_length <= limit, "Longitud de introducción ≤ 2 veces la menor dimensión."))
    if not available:
        _incomplete("I6.3: indique al menos un mecanismo de transferencia.", section,
                    ["composite.load_transfer.bearing_area", "composite.load_transfer.anchor_count", "composite.load_transfer.bond_length"])
    mechanism = max(available, key=available.get)
    ratio = force["Vr"] / available[mechanism]
    mode = {"limit_state": "load_transfer", "provision": "I6", "applies": True, "equation": force["equation"], "Pno_kN": pno / 1000.0,
            "Vr_kN": force["Vr"] / 1000.0, **{f"{k}_kN": v / 1000.0 for k, v in available.items()}, "mechanism": mechanism,
            "ratio": ratio}
    return _result(case, section, modes={"LT": mode}, governing="LT", provisions=["I6"], requirements=requirements, ratio=ratio)


def composite_anchor(case: SteelCase, section: Section) -> dict:
    """I8.3: one steel headed stud or channel anchor of a composite component."""
    _check_family(case, section)
    if case.composite.kind == "beam":
        _blocked("Los anclajes de vigas compuestas se calculan con I8.2 (composite.beam), no con I8.3.", section)
    anchor, concrete = case.composite.anchor, case.composite.concrete
    Qrv, Qrt = anchor.Qrv, anchor.Qrt
    if anchor.type == "channel":
        if Qrt:
            _blocked("I8.3d cubre conectores de canal a cortante; la tracción no está cubierta.", section)
        Ec = eq.concrete_modulus(wc=concrete.wc, fc=concrete.fc)
        qn = eq.channel_strength(tf=anchor.tf, tw=anchor.tw, la=anchor.la, fc=concrete.fc, Ec=Ec) / 1000.0
        qcv = eq.PHI_CHANNEL * qn
        mode = {"limit_state": "anchor_shear", "provision": "I8.3d", "applies": True, "equation": "I8-2", "Qnv_kN": qn,
                "phi_v": eq.PHI_CHANNEL, "Qcv_kN": qcv, "Qrv_kN": Qrv, "ratio": Qrv / qcv}
        requirements = [_requirement("spacing", "I8.3e(d)", anchor.spacing <= 600.0, "Separación de canales ≤ 600 mm.")]
        return _result(case, section, modes={"V": mode}, governing="V", provisions=["I8.3d"], requirements=requirements,
                       ratio=mode["ratio"])
    d, h = anchor.d, anchor.height
    Asa = math.pi * d**2 / 4
    lightweight = concrete.lightweight
    if Qrt and Qrv and lightweight:
        _blocked("Perno a cortante y tracción en concreto liviano: I8.3 remite a ACI 318, Capítulo 17.", section)
    if Qrt and (anchor.head_diameter is None or anchor.head_diameter < 1.6 * d):
        _blocked("Perno a tracción: el diámetro de la cabeza debe declararse y ser ≥ 1.6·d; si no, I8.3 remite a ACI 318.",
                 section, fields=["composite.anchor.head_diameter"])
    near_edge = anchor.edge_distance is not None and anchor.edge_distance < 1.5 * h
    close = anchor.spacing < 3 * h
    qcv = qct = None
    terms = {}
    if Qrv:
        qnv = eq.stud_shear_strength(Fu=anchor.Fu, Asa=Asa) / 1000.0
        if anchor.breakout_in_shear:
            if anchor.reinforcement_shear is None:
                _blocked("Rotura del concreto a cortante aplicable: indique composite.anchor.reinforcement_shear (I8.3a(a)); "
                         "la alternativa de ACI 318, Capítulo 17, no está implementada.", section)
            qnv = min(qnv, anchor.reinforcement_shear)
        qcv = eq.PHI_STUD_V * qnv
        terms.update(Qnv_kN=qnv, Qcv_kN=qcv, Qrv_kN=Qrv)
    if Qrt:
        qnt = eq.stud_tension_strength(Fu=anchor.Fu, Asa=Asa) / 1000.0
        if near_edge or close:
            if anchor.reinforcement_tension is None:
                _blocked("Borde o separación por debajo de 1.5h o 3h: indique composite.anchor.reinforcement_tension (I8.3b(a)); "
                         "la alternativa de ACI 318, Capítulo 17, no está implementada.", section)
            qnt = min(qnt, anchor.reinforcement_tension)
        qct = eq.PHI_STUD_T * qnt
        terms.update(Qnt_kN=qnt, Qct_kN=qct, Qrt_kN=Qrt)
    if Qrv and Qrt:
        ratio, equation, provision = eq.stud_interaction(Qrv=Qrv, Qcv=qcv, Qrt=Qrt, Qct=qct), "I8-5", "I8.3c"
    elif Qrv:
        ratio, equation, provision = Qrv / qcv, "I8-3", "I8.3a"
    else:
        ratio, equation, provision = Qrt / qct, "I8-4", "I8.3b"
    minimum = ((10 if lightweight else 8) if Qrt else (7 if lightweight else 5))
    d_limit = 25.0 if anchor.solid_slab and not Qrt else 19.0
    requirements = [
        _requirement("h/d", "I8.3", h / d >= minimum, f"Altura del perno ≥ {minimum} diámetros."),
        _requirement("spacing_min", "I8.3e(b)", anchor.spacing >= 4 * d, "Separación de pernos ≥ 4 diámetros."),
        _requirement("spacing_max", "I8.3e(c)", anchor.spacing <= 32 * d, "Separación de pernos ≤ 32 diámetros."),
        _requirement("dsa_max", "I8.1", d <= d_limit, f"Diámetro de perno ≤ {d_limit:g} mm."),
        _requirement("dsa_t", "I8.1", anchor.over_web or d <= 2.5 * anchor.base_thickness,
                     "Diámetro ≤ 2.5 veces el espesor del metal base, salvo sobre un alma."),
    ]
    mode = {"limit_state": "anchor_strength", "provision": provision, "applies": True, "equation": equation, "Asa_mm2": Asa,
            **terms, "ratio": ratio}
    return _result(case, section, modes={"Q": mode}, governing="Q", provisions=[provision], requirements=requirements,
                   ratio=ratio)


def composite_appendix_2_interaction(case: SteelCase, section: Section, checks: list) -> dict:
    """Appendix 2, Section 2.1.4: Equations I5-1a/b with cp and cm of A-2-3 and A-2-4."""
    by_id = {c.id: c for c in checks}
    if case.Mux and case.Muy:
        _blocked("Apéndice 2: las ecuaciones I5-1 cubren flexión en un eje.", section)
    missing = [c.id for c in checks if c.capacity is None]
    if missing:
        raise IncompleteSectionDataError("La interacción necesita la resistencia de diseño de cada componente.",
                                         code="INTERACTION_COMPONENT_MISSING",
                                         details={"section": section.name, "checks": missing})
    axial = by_id["axial"]
    flexure = by_id.get("flexure_x") or by_id.get("flexure_y")
    A = axial.result["modes"][axial.result["governing_mode"]]
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    t = section.tdes
    lam = a2.slenderness(b_t=max(section.b, section.h) / t, Fy=Fy)
    B, H = (section.b_out, section.h_out) if flexure.id == "flexure_x" else (section.h_out, section.b_out)
    coefficients = a2.interaction_coefficients(B=B, H=H, lam=lam, Pn=A["Pn_kN"], Pno=A["Pno_kN"], fc=fc, Fy=Fy)
    out = eq.i5_interaction(Pr_Pc=axial.demand / axial.capacity, Mr_Mc=flexure.demand / flexure.capacity, **coefficients)
    mode = {"limit_state": "combined_flexure_axial", "provision": "Apéndice 2, 2.1.4", "applies": True, **coefficients,
            "Pr_kN": axial.demand, "Pc_kN": axial.capacity, "Mr_kNm": flexure.demand, "Mc_kNm": flexure.capacity, **out}
    return _result(case, section, modes={"A2": mode}, governing="A2", provisions=["Apéndice 2"], ratio=out["ratio"],
                   notes=["Se supone que Pr y Mr incluyen los efectos de segundo orden (Capítulo C, decisión DH-3)."])


def composite_i5(case: SteelCase, section: Section, checks: list) -> dict:
    """I5(b): Equations I5-1a/b, for filled noncompact or slender sections under compression and flexure."""
    by_id = {c.id: c for c in checks}
    composite = case.composite
    if composite.kind != "filled":
        _blocked("Las ecuaciones I5-1 solo se aplican a miembros rellenos.", section, kind=composite.kind)
    if case.Pu < 0 or (case.Mux and case.Muy):
        _blocked("Las ecuaciones I5-1 cubren compresión con flexión en un eje; use interaction = H1.", section)
    missing = [c.id for c in checks if c.capacity is None]
    if missing:
        raise IncompleteSectionDataError("La interacción necesita la resistencia de diseño de cada componente.",
                                         code="INTERACTION_COMPONENT_MISSING",
                                         details={"section": section.name, "checks": missing})
    flexure = by_id.get("flexure_x") or by_id.get("flexure_y")
    axial = by_id["axial"]
    classes = {row["class"] for c in (axial, flexure) for row in c.result["classification"]["elements"]}
    if classes == {"compact"}:
        _blocked("Sección compacta: I5(a) no admite las ecuaciones I5-1; use interaction = H1.", section)
    geometry = _filled_geometry(case, section)
    csr = eq.strength_ratio(As=section.area, Fy=case.material.Fy, Asr=geometry["Asr"], Fysr=geometry["Fysr"], Ac=geometry["Ac"],
                            fc=composite.concrete.fc)
    coefficients = eq.i5_coefficients(shape=geometry["shape"], csr=csr)
    terms = {"Pr_kN": axial.demand, "Pc_kN": axial.capacity, "Mr_kNm": flexure.demand, "Mc_kNm": flexure.capacity}
    out = eq.i5_interaction(Pr_Pc=axial.demand / axial.capacity, Mr_Mc=flexure.demand / flexure.capacity, **coefficients)
    mode = {"limit_state": "combined_flexure_axial", "provision": "I5(b)", "applies": True, "csr": csr, **coefficients, **terms, **out}
    return _result(case, section, modes={"I5": mode}, governing="I5", provisions=["I5"], ratio=out["ratio"],
                   notes=["Se supone que Pr y Mr incluyen los efectos de segundo orden (Capítulo C, decisión DH-3)."])
