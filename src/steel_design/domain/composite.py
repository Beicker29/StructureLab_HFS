"""Chapter I for one member and one load combination. LRFD.

Filled rectangular and round HSS (I2.2, I3.4, I4.2), encased W-shapes (I2.1, I3.3, I4.1(a)) and composite beams
with steel anchors (I3.2, I4.3, I8.2). The member type is declared in case.composite. Formulas live in
codes/aisc_360_22/composite.py. Missing data or decisions raise structured errors.
"""
import math

from ..codes.aisc_360_22 import composite as eq
from ..errors import IncompleteSectionDataError, RuleNotImplementedError
from ..models import SteelCase
from ..sections.models import Section

_LIMITATIONS = (
    "Transferencia de carga (I6), diafragmas (I7) y anclajes de componentes (I8.3, I8.4) no se comprueban.",
    "El diseño del concreto y del refuerzo según ACI 318 (I1.1) queda fuera de este cálculo.",
    "Pr y Mr se toman como datos del usuario: se supone que provienen de un análisis según el Capítulo C con las "
    "rigideces de I1.5 (decisión DH-3).",
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


def _check_family(case, section):
    """The declared kind must match the family; I1.3 material limits (Appendix 2 is out of scope)."""
    composite, family = case.composite, section.type.upper()
    allowed = {"filled": {"RECTANGULAR_HSS", "CIRCULAR_HSS"}, "encased": {"W"}, "beam": {"W"}}[composite.kind]
    if family not in allowed:
        _blocked(f"composite.kind = {composite.kind} no se aplica a esta familia en el alcance implementado.", section,
                 kind=composite.kind)
    if abs(case.material.E - eq.E_STEEL) > 1e-6:
        _incomplete("El Capítulo I usa Es = 200000 MPa.", section, ["material.E"])
    fc, limit = composite.concrete.fc, 41.0 if composite.concrete.lightweight else 69.0
    failed = []
    if not 21.0 <= fc <= limit:
        failed.append(f"I1.3(a): 21 MPa ≤ f'c ≤ {limit:g} MPa")
    if case.material.Fy > 525.0:
        failed.append("I1.3(b): Fy ≤ 525 MPa")
    if composite.encased and composite.encased.Fysr > 550.0:
        failed.append("I1.3(c): Fysr ≤ 550 MPa")
    if failed:
        _blocked("Materiales fuera de los límites de I1.3; el Apéndice 2 no está implementado.", section, failed=failed)


def _result(case, section, *, modes, governing, provisions, classification=None, requirements=(), notes=(), **values):
    return {"chapter": "I", "code": "ANSI/AISC 360-22", "section": section.name, "family": section.type.upper(),
            "kind": case.composite.kind, "inputs": {"Fy_mpa": case.material.Fy, "fc_mpa": case.composite.concrete.fc,
                                                    "wc_kg_m3": case.composite.concrete.wc},
            "classification": classification or {"elements": [], "slender": False},
            "provisions": provisions, "modes": modes, "governing_mode": governing,
            "governing_equation": modes[governing]["equation"], "requirements": list(requirements),
            "notes": list(notes), "limitations": list(_LIMITATIONS), **values}


# --- filled sections ------------------------------------------------------------------------

def _filled_geometry(section):
    """Concrete fill. Rectangular: inside corner radius t, as in Examples I.3 and I.4 (DI-2)."""
    if section.type.upper() == "CIRCULAR_HSS":
        _require(section, "od", "tdes", "area", "ix", "iy")
        ri = section.od / 2 - section.tdes
        ic = math.pi * ri**4 / 4
        return {"shape": "round", "Ac": math.pi * ri**2, "Icx": ic, "Icy": ic, "t": section.tdes, "D": section.od}
    _require(section, "h_out", "b_out", "tdes", "b", "h", "area", "ix", "iy")
    t = section.tdes
    bi, hi = section.b_out - 2 * t, section.h_out - 2 * t

    def inertia(width, depth):
        """Rounded inside rectangle about the axis parallel to width (squares less quarter circles at the corners)."""
        c = depth / 2 - t
        square = t * ((depth / 2) ** 3 - c**3) / 3
        quarter = c**2 * math.pi * t**2 / 4 + 2 * c * t**3 / 3 + math.pi * t**4 / 16
        return width * depth**3 / 12 - 4 * (square - quarter)

    return {"shape": "rect", "Ac": bi * hi - (4 - math.pi) * t**2, "Icx": inertia(bi, hi), "Icy": inertia(hi, bi),
            "t": t, "bi": bi, "hi": hi}


def _axial_class(section, geometry, Fy):
    limits = eq.filled_limits(shape=geometry["shape"], element="axial", Fy=Fy)
    lam = geometry["D"] / geometry["t"] if geometry["shape"] == "round" else max(section.b, section.h) / geometry["t"]
    cls = eq.classify_filled(ratio=lam, limits=limits)
    if cls == "exceeds_maximum":
        _blocked("La relación ancho-espesor supera el máximo permitido de la Tabla I1.1a.", section, ratio=lam)
    return {"lam": lam, "limits": limits, "class": cls}


def _filled_compression(case, section, geometry):
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    As, Ac = section.area, geometry["Ac"]
    c = _axial_class(section, geometry, Fy)
    Fn = None
    if c["class"] == "slender":
        Fn = (eq.critical_stress_round(D_t=c["lam"], Fy=Fy) if geometry["shape"] == "round"
              else eq.critical_stress_rectangular(lam=c["lam"]))
    pno = eq.pno_filled(cls=c["class"], shape=geometry["shape"], Fy=Fy, As=As, fc=fc, Ac=Ac, lam=c["lam"],
                        limits=c["limits"], Fn=Fn)
    coefficient = eq.c3_filled(As=As, Asr=0.0, Ag=As + Ac)
    row = {"element": "wall", "ratio": c["lam"], "lambda_p": c["limits"]["p"], "lambda_r": c["limits"]["r"],
           "class": c["class"]}
    return pno, coefficient, 0.0, 0.0, {"elements": [row], "slender": False, "reference": "Tabla I1.1a"}, [
        _requirement("As/Ag", "I2.2a(a)", As / (As + Ac) >= 0.01, "El acero debe ser al menos 1 % de la sección compuesta.")]


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


def composite_compression(case: SteelCase, section: Section, bare_steel=None) -> dict:
    """I2.1b and I2.2b: flexural buckling about both axes; not less than the bare steel of Chapter E."""
    _check_family(case, section)
    kind = case.composite.kind
    if kind == "beam":
        _blocked("La viga compuesta con fuerza axial no está cubierta por I3.2.", section)
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    Ec = eq.concrete_modulus(wc=case.composite.concrete.wc, fc=fc)
    f, ln = case.factors, case.lengths
    if kind == "filled":
        geometry = _filled_geometry(section)
        pno, coefficient, Isrx, Isry, classification, requirements = _filled_compression(case, section, geometry)
        c_name = "C3"
    else:
        geometry = _encased_geometry(case, section)
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
        ei = eq.effective_stiffness(Is=Is, Isr=Isr, C=coefficient, Ec=Ec, Ic=Ic)
        pe = eq.elastic_buckling_load(EI_eff=ei, Lc=K * L)
        out = eq.nominal_compression(Pno=pno["Pno"], Pe=pe)
        modes[f"FB-{axis}"] = {"limit_state": "flexural_buckling", "provision": "I2.2b" if kind == "filled" else "I2.1b",
                               "applies": True, "equation": out["equation"], "Pno_kN": pno["Pno"] / 1000.0,
                               "Pno_equation": pno["equation"], c_name: coefficient, "Ec_mpa": Ec,
                               "EI_eff": ei, "Lc_mm": K * L, "Pe_kN": pe / 1000.0, "Pno_over_Pe": out["Pno_over_Pe"],
                               "Pn_kN": out["Pn"] / 1000.0, "available_kN": eq.PHI_C * out["Pn"] / 1000.0}
    governing = min(modes, key=lambda k: modes[k]["Pn_kN"])
    available, notes = modes[governing]["available_kN"], []
    if bare_steel is not None:
        try:
            bare = bare_steel()
        except (RuleNotImplementedError, IncompleteSectionDataError) as exc:
            notes.append(f"Resistencia del acero solo (Capítulo E) no disponible: {exc}")
        else:
            if bare["available_kN"] > available:
                available = bare["available_kN"]
                notes.append(f"Gobierna el acero solo: I2 permite no tomar menos que el Capítulo E ({bare['governing_mode']}).")
    modes["LB"] = {"limit_state": "local_buckling", "provision": "I1.4" if kind == "filled" else "I1.2", "applies": True,
                   "equation": "Tabla I1.1a" if kind == "filled" else "No requerido en embebidos (I1.2)"}
    return _result(case, section, modes=modes, governing=governing, provisions=["I1", modes[governing]["provision"]],
                   classification=classification, requirements=requirements, notes=notes,
                   Pn_kN=modes[governing]["Pn_kN"], phi_c=eq.PHI_C, available_kN=available)


def composite_tension(case: SteelCase, section: Section) -> dict:
    """I2-8 and I2-14: yielding of the steel section and the bars (concrete neglected, I1.2)."""
    _check_family(case, section)
    kind = case.composite.kind
    if kind == "beam":
        _blocked("La viga compuesta con fuerza axial no está cubierta por I3.2.", section)
    _require(section, "area")
    e = case.composite.encased
    Asr, Fysr = (sum(b.area for b in e.bars), e.Fysr) if e else (0.0, 0.0)
    pn = eq.tension_yielding(Fy=case.material.Fy, As=section.area, Fysr=Fysr, Asr=Asr)
    mode = {"limit_state": "tensile_yielding", "provision": "I2.1c" if e else "I2.2c", "applies": True,
            "equation": "I2-8" if e else "I2-14", "Pn_kN": pn / 1000.0, "available_kN": eq.PHI_T * pn / 1000.0}
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


def _filled_flexure(case, section, axis):
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    geometry = _filled_geometry(section)
    requirement = _requirement("As/Ag", "I3.4a(b)", section.area / (section.area + geometry["Ac"]) >= 0.01,
                               "El acero debe ser al menos 1 % de la sección compuesta.")
    if geometry["shape"] == "round":
        lam = geometry["D"] / geometry["t"]
        limits = eq.filled_limits(shape="round", element="flexure_round", Fy=Fy)
        cls = eq.classify_filled(ratio=lam, limits=limits)
        if cls != "compact":
            _blocked("Relleno redondo no compacto o esbelto en flexión: el Commentary solo da bloques de tensiones para "
                     "secciones rectangulares (decisión DI-3).", section, ratio=lam, classification=cls)
        out = eq.round_plastic_moment(Fy=Fy, fc=fc, D=geometry["D"], t=geometry["t"])
        row = {"element": "wall", "ratio": lam, "lambda_p": limits["p"], "lambda_r": limits["r"], "class": cls}
        mode = {"provision": "I3.4b(a)", "equation": "I3-5a", "Mp_kNm": out["Mp"] / 1e6, "hn_mm": out["hn_mm"],
                "Mn_kNm": out["Mp"] / 1e6}
        return _flexure_output(case, section, mn_mode=mode, requirements=[requirement], provisions=["I1", "I3.4"],
                               classification={"elements": [row], "slender": False, "reference": "Tabla I1.1b"})
    t = geometry["t"]
    # Elements: the flange is perpendicular to the bending direction, the web is parallel to it.
    H, bi, hi, flange, web, Zs = ((section.h_out, geometry["bi"], geometry["hi"], section.b, section.h, section.zx)
                                  if axis == "x" else
                                  (section.b_out, geometry["hi"], geometry["bi"], section.h, section.b, section.zy))
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
    plastic = eq.rect_plastic_moment(Fy=Fy, fc=fc, Zs=Zs, t=t, bi=bi, hi=hi, r=t)
    if worst == "compact":
        mode = {"provision": "I3.4b(a)", "equation": "I3-5a", "Mp_kNm": plastic["Mp"] / 1e6, "hn_mm": plastic["hn_mm"],
                "Mn_kNm": plastic["Mp"] / 1e6}
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
    return _flexure_output(case, section, mn_mode=mode, classification=classification, requirements=[requirement],
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
        mode = {"provision": "I3.3a(3)", "equation": "Distribución plástica compuesta (I1.2a)", "hn_mm": out["hn_mm"],
                "Mn_kNm": out["Mp"] / 1e6}
        notes = ["I3.3a(3): plástico sobre la sección compuesta. I3.3a(e), sección controlada por tracción según ACI 318, "
                 "no se comprueba."]
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


def composite_flexure(case: SteelCase, section: Section, axis: str, flexure_strength) -> dict:
    """I3: flexure about x or y. flexure_strength is the Chapter F calculation of the steel section alone."""
    _check_family(case, section)
    kind = case.composite.kind
    if axis not in {"x", "y"}:
        _blocked("Mw y Mz no se aplican a miembros compuestos.", section, axis=axis)
    if kind == "beam":
        if axis != "x":
            _blocked("La viga compuesta se calcula en su eje mayor (I3.2).", section, axis=axis)
        result = _beam_flexure(case, section, flexure_strength)
        return flexure_strength() if result is None else result
    return _filled_flexure(case, section, axis) if kind == "filled" else _encased_flexure(case, section, axis)


def composite_shear(case: SteelCase, section: Section, axis: str, shear_strength) -> dict:
    """I4.1(a) and I4.3: steel section alone (Chapter G). I4.2: filled sections with Kc = 1 (DI-4)."""
    _check_family(case, section)
    if case.composite.kind != "filled":
        return shear_strength()
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    geometry = _filled_geometry(section)
    if geometry["shape"] == "round":
        Av = 2 * section.area / math.pi
    else:
        Av = 2 * (section.h if axis == "x" else section.b) * geometry["t"]
    vn = eq.shear_filled(Av=Av, Fy=Fy, Kc=1.0, Ac=geometry["Ac"], fc=fc)
    mode = {"limit_state": "shear", "provision": "I4.2", "applies": True, "equation": "I4-1", "Av_mm2": Av,
            "Ac_mm2": geometry["Ac"], "Kc": 1.0, "Vn_kN": vn / 1000.0, "available_kN": eq.PHI_V_FILLED * vn / 1000.0}
    return _result(case, section, modes={"V": mode}, governing="V", provisions=["I1", "I4.2"],
                   notes=["Kc = 1: límite inferior de I4.2 (decisión DI-4)."], Vn_kN=vn / 1000.0,
                   phi_v=eq.PHI_V_FILLED, available_kN=mode["available_kN"])


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
    geometry = _filled_geometry(section)
    csr = eq.strength_ratio(As=section.area, Fy=case.material.Fy, Asr=0.0, Fysr=0.0, Ac=geometry["Ac"], fc=composite.concrete.fc)
    coefficients = eq.i5_coefficients(shape=geometry["shape"], csr=csr)
    terms = {"Pr_kN": axial.demand, "Pc_kN": axial.capacity, "Mr_kNm": flexure.demand, "Mc_kNm": flexure.capacity}
    out = eq.i5_interaction(Pr_Pc=axial.demand / axial.capacity, Mr_Mc=flexure.demand / flexure.capacity, **coefficients)
    mode = {"limit_state": "combined_flexure_axial", "provision": "I5(b)", "applies": True, "csr": csr, **coefficients, **terms, **out}
    return _result(case, section, modes={"I5": mode}, governing="I5", provisions=["I5"], ratio=out["ratio"],
                   notes=["Se supone que Pr y Mr incluyen los efectos de segundo orden (Capítulo C, decisión DH-3)."])
