"""Filled rectangular and round HSS: geometry, I2.2 compression basis, I3.4 flexure; 4.2.4d(c) under fire."""
import math

from ...codes.aisc_360_22 import appendix_2 as a2
from ...codes.aisc_360_22 import appendix_4 as a4
from ...codes.aisc_360_22 import composite as eq
from ...codes.aisc_dg06 import filled as dg06
from ...codes.aisc_dg06 import members as dg06_members
from ..fire import SLENDER_BLOCK, steel_at_temperature, with_fire_extension
from .common import (
    blocked,
    composite_materials,
    flexure_output,
    incomplete,
    require_properties,
    requirement_row,
    uses_appendix_2,
)


def filled_geometry(case, section):
    """Concrete fill, net of the bars. Rectangular: inside corner radius t, as in Examples I.3 and I.4 (DI-2)."""
    filled = case.composite.filled
    bars = filled.bars if filled else []
    Asr = sum(b.area for b in bars)
    Isrx = sum(math.pi * b.db**4 / 64 + b.area * b.y**2 for b in bars)
    Isry = sum(math.pi * b.db**4 / 64 + b.area * b.x**2 for b in bars)
    extra = {"Asr": Asr, "Isrx": Isrx, "Isry": Isry, "Fysr": filled.Fysr if filled else 0.0, "bars": bars}
    if section.type.upper() == "CIRCULAR_HSS":
        require_properties(section, "od", "tdes", "area", "ix", "iy")
        ri = section.od / 2 - section.tdes
        ic = math.pi * ri**4 / 4
        return {"shape": "round", "Afill": math.pi * ri**2, "Ac": math.pi * ri**2 - Asr, "Icx": ic - Isrx, "Icy": ic - Isry,
                "t": section.tdes, "D": section.od, "ri": ri, **extra}
    require_properties(section, "h_out", "b_out", "tdes", "b", "h", "area", "ix", "iy")
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



def filled_requirements(case, section, geometry, *, flexure):
    """I2.2a, I3.4a and the clearance of I2.2e, I3.4c."""
    ratio = section.area / (section.area + geometry["Afill"])
    out = [requirement_row("As/Ag", "I3.4a(b)" if flexure else "I2.2a(a)", ratio >= 0.01,
                        "El acero debe ser al menos 1 % de la sección compuesta.", ratio, "≥ 0.01")]
    filled = case.composite.filled
    if not filled:
        return out
    t = filled.transverse
    out.append(requirement_row("transverse", "I2.2a(c)", (t.db >= 13.0 and t.spacing <= 400.0) or (t.db >= 10.0 and t.spacing <= 300.0),
                            "Refuerzo transversal mínimo: 10 mm a 300 mm o 13 mm a 400 mm."))
    if geometry["shape"] == "round":
        gaps = [geometry["ri"] - math.hypot(b.x, b.y) - b.db / 2 for b in filled.bars]
    else:
        gaps = [min(geometry["bi"] / 2 - abs(b.x), geometry["hi"] / 2 - abs(b.y)) - b.db / 2 for b in filled.bars]
    out.append(requirement_row("bar_clearance", "I2.2e, I3.4c", all(g >= max(1.5 * b.db, 38.0) for g, b in zip(gaps, filled.bars)),
                            "Separación libre entre el tubo y las barras: al menos 1.5 db y 38 mm."))
    if flexure:
        out.append(requirement_row("rho_sr", "I3.4a(c)", geometry["Asr"] / (section.area + geometry["Afill"]) >= 0.004,
                                "Con barras, la cuantía longitudinal mínima es 0.004.",
                                geometry["Asr"] / (section.area + geometry["Afill"]), "≥ 0.004"))
    return out



def _axial_class(section, geometry, Fy):
    limits = eq.filled_limits(shape=geometry["shape"], element="axial", Fy=Fy)
    lam = geometry["D"] / geometry["t"] if geometry["shape"] == "round" else max(section.b, section.h) / geometry["t"]
    cls = eq.classify_filled(ratio=lam, limits=limits)
    if cls == "exceeds_maximum":
        blocked("La relación ancho-espesor supera el máximo permitido de la Tabla I1.1a.", section, ratio=lam)
    return {"lam": lam, "limits": limits, "class": cls}



def _appendix_2_compression(case, section, geometry):
    """Appendix 2, Section 2.1.2. The bars are not considered in the strength (2.1.1(e))."""
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    t = geometry["t"]
    b_t = max(section.b, section.h) / t
    if b_t > 5.0 * math.sqrt(eq.E_STEEL / Fy):
        blocked("La relación ancho-espesor supera el máximo de 2.1.1(d): 5.00·√(E/Fy).", section, ratio=b_t)
    lam = a2.slenderness(b_t=b_t, Fy=Fy)
    Fn = a2.critical_stress(lam=lam, Fy=Fy)
    pno = {"Pno": a2.pno(Fn=Fn, As=section.area, fc=fc, Ac=geometry["Ac"]), "equation": "A-2-1", "Fn": Fn, "lambda_A2": lam}
    coefficient = eq.c3_filled(As=section.area, Asr=0.0, Ag=section.area + geometry["Afill"])
    return pno, coefficient, 0.0, 0.0, None, filled_requirements(case, section, geometry, flexure=False)



def filled_compression(case, section, geometry):
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
        filled_requirements(case, section, geometry, flexure=False))



def filled_fire_modes(case, section, hot):
    """4.2.4d(c): I2-9 and I2-12 at temperature, A-4-11 and I2-4 (errata 2025). The classification stays at ambient temperature (Commentary)."""
    geometry = filled_geometry(case, section)
    m = composite_materials(case, section)
    c = _axial_class(section, geometry, case.material.Fy)
    if c["class"] == "slender":
        blocked(SLENDER_BLOCK, section, ratio=c["lam"])
    # I2-9b: Asr*Es/Ec with the Es of the bars and the Ec of the concrete, each at its own temperature (decision DA4-5).
    fc_Ac = m["fc"] * (geometry["Ac"] + (geometry["Asr"] * m["Es_bars"] / m["Ec"] if geometry["Asr"] else 0.0))
    Ec_Icx, Ec_Icy, Es_bars = m["Ec"] * geometry["Icx"], m["Ec"] * geometry["Icy"], m["Es_bars"]
    pno = eq.pno_filled_of_concrete(cls=c["class"], shape=geometry["shape"], Fy=hot["Fy_T_mpa"], As=section.area, fc_Ac=fc_Ac, lam=c["lam"], limits=c["limits"])
    coefficient = eq.c3_filled(As=section.area, Asr=geometry["Asr"], Ag=section.area + geometry["Afill"])
    modes = {}
    for axis, Is, Isr, Ec_Ic, K, L in (("x", section.ix, geometry["Isrx"], Ec_Icx, case.factors.Kx, case.lengths.Lx),
                                       ("y", section.iy, geometry["Isry"], Ec_Icy, case.factors.Ky, case.lengths.Ly)):
        ei = hot["E_T_mpa"] * Is + Es_bars * Isr + coefficient * Ec_Ic                 # I2-12 at temperature
        pe = eq.elastic_buckling_load(EI_eff=ei, Lc=K * L)
        out = a4.filled_compression(Pno_T=pno["Pno"], Pe_T=pe)
        modes[f"FB-{axis}"] = {"limit_state": "flexural_buckling", "provision": "I2.2b; Apéndice 4, 4.2.4d(c)", "applies": True, "equation": out["equation"], "Pn_equation": out["equation"],
                               "Pno_T_kN": pno["Pno"] / 1000.0, "Pno_equation": pno["equation"], "C3": coefficient, "EI_eff_T": ei, "Lc_mm": K * L,
                               "PC_kN": eq.point_c(fc=m["fc"], Ac=geometry["Ac"], c2=0.95 if geometry["shape"] == "round" else 0.85) / 1000.0,
                               "Pe_T_kN": pe / 1000.0, "Pno_over_Pe": out["Pno_over_Pe"], "Pn_kN": out["Pn"] / 1000.0, "available_kN": eq.PHI_C * out["Pn"] / 1000.0}
    row = {"element": "wall", "ratio": c["lam"], "lambda_p": c["limits"]["p"], "lambda_r": c["limits"]["r"], "class": c["class"]}
    return modes, {"elements": [row], "slender": False, "reference": "Tabla I1.1a"}, filled_requirements(case, section, geometry, flexure=False)



def tension_control(case, hn, h, bars, Fysr, pno, requirements, provision):
    """I3.3a(e), I3.4a(d) by Design Guide 6, Section 2.4.1: applies to beam members with Pu < 0.10Pn."""
    out = dg06_members.tension_control(hn=hn, h=h, v_tension=min(v for _, v in bars), Fysr=Fysr)
    fields = {"epsilon_t": out["epsilon_t"], "epsilon_limit": out["epsilon_limit"]}
    notes = []
    if abs(case.Pu) * 1000.0 < 0.10 * pno and case.composite.flexural_member is not False:
        if case.composite.flexural_member:
            requirements.append(requirement_row("tension_controlled", provision, out["tension_controlled"],
                                             "Viga con Pu < 0.10Pn: εt debe alcanzar εy + 0.003 (AISC Design Guide 6, 2.4.1)."))
        else:
            notes.append(f"Si el miembro es una viga, {provision} exige sección controlada por tracción: indique "
                         "composite.flexural_member.")
    return fields, notes



def filled_flexure(case, section, axis):
    """The limits and the classification with the ambient Fy (Commentary 4.2.4d); the strength with the materials of the case."""
    hot = steel_at_temperature(case)
    return with_fire_extension(_filled_flexure_strength(case, section, axis, hot), hot)



def _filled_flexure_strength(case, section, axis, hot):
    Fy = case.material.Fy
    m = composite_materials(case, section)
    fc = m["fc"]
    geometry = filled_geometry(case, section)
    requirement = filled_requirements(case, section, geometry, flexure=True)
    bars = [(b.area, b.y if axis == "x" else b.x) for b in geometry["bars"]]
    Fysr = m["Fysr"]
    if geometry["shape"] == "round":
        lam = geometry["D"] / geometry["t"]
        limits = eq.filled_limits(shape="round", element="flexure_round", Fy=Fy)
        cls = eq.classify_filled(ratio=lam, limits=limits)
        if cls == "exceeds_maximum":
            blocked("D/t supera el máximo permitido de la Tabla I1.1b.", section, ratio=lam)
        out = eq.round_plastic_moment(Fy=m["Fy"], fc=fc, D=geometry["D"], t=geometry["t"], Fysr=Fysr, bars=bars)
        row = {"element": "wall", "ratio": lam, "lambda_p": limits["p"], "lambda_r": limits["r"], "class": cls}
        classification = {"elements": [row], "slender": False, "reference": "Tabla I1.1b"}
        if cls == "compact":
            mode = {"provision": "I3.4b(a)", "equation": "I3-5a", "Mp_kNm": out["Mp"] / 1e6, "hn_mm": out["hn_mm"],
                    "Md_kNm": out["Md"] / 1e6, "Mn_kNm": out["Mp"] / 1e6}
            return flexure_output(case, section, mn_mode=mode, requirements=requirement, provisions=["I1", "I3.4"],
                                   classification=classification)
        # Noncompact (lambda_r = maximum permitted, so there is no slender round section): My by Design Guide 6 (DI-3).
        yielding = dg06.round_yield_moment(Fy=m["Fy"], fc=fc, Ec=m["Ec"], D=geometry["D"], t=geometry["t"], Fysr=Fysr, bars=bars, Es=m["Es_bars"])
        mn = eq.noncompact_moment(Mp=out["Mp"], My=yielding["My"], lam=lam, limits=limits)
        mode = {"provision": "I3.4b(b)", "equation": "I3-5b", "Mp_kNm": out["Mp"] / 1e6, "My_kNm": yielding["My"] / 1e6,
                "yn_mm": yielding["yn_mm"], "Mn_kNm": mn / 1e6}
        notes = ["My de la sección redonda por el procedimiento de AISC Design Guide 6, ejemplo 2.7; no es una ecuación de la "
                 "Specification (decisión DI-3)."]
        return flexure_output(case, section, mn_mode=mode, requirements=requirement, provisions=["I1", "I3.4"],
                               classification=classification, notes=notes)
    t = geometry["t"]
    # Elements: the flange is perpendicular to the bending direction, the web is parallel to it.
    H, bi, hi, flange, web, Zs = ((section.h_out, geometry["bi"], geometry["hi"], section.b, section.h, section.zx)
                                  if axis == "x" else
                                  (section.b_out, geometry["hi"], geometry["bi"], section.h, section.b, section.zy))
    if uses_appendix_2(case, section):
        b_t = max(section.b, section.h) / t
        if b_t > 5.0 * math.sqrt(eq.E_STEEL / Fy):
            blocked("La relación ancho-espesor supera el máximo de 2.1.1(d): 5.00·√(E/Fy).", section, ratio=b_t)
        Fn = a2.critical_stress(lam=a2.slenderness(b_t=b_t, Fy=Fy), Fy=Fy)
        out = a2.nominal_moment(Fy=Fy, Fn=Fn, fc=fc, H=H, tw=t, tf=t, bi=bi)
        mode = {"provision": "Apéndice 2, 2.1.3", "equation": "90 % de la distribución de tensiones (Apéndice 2)", "Fn_mpa": Fn,
                "a_mm": out["a_mm"], "Msd_kNm": out["Msd"] / 1e6, "Mn_kNm": out["Mn"] / 1e6}
        return flexure_output(case, section, mn_mode=mode, requirements=requirement, provisions=["Apéndice 2"])
    if not Zs:
        incomplete("La flexión del relleno requiere Z del perfil.", section, ["section.zx" if axis == "x" else "section.zy"])
    rows, candidates = [], {}
    worst = "compact"
    for name, ratio in (("flange", flange / t), ("web", web / t)):
        limits = eq.filled_limits(shape="rect", element=name, Fy=Fy)
        cls = eq.classify_filled(ratio=ratio, limits=limits)
        if cls == "exceeds_maximum":
            blocked("La relación ancho-espesor supera el máximo permitido de la Tabla I1.1b.", section, element=name, ratio=ratio)
        rows.append({"element": name, "ratio": ratio, "lambda_p": limits["p"], "lambda_r": limits["r"], "class": cls})
        candidates[name] = (ratio, limits, cls)
        worst = max(worst, cls, key=["compact", "noncompact", "slender"].index)
    classification = {"elements": rows, "slender": False, "reference": "Tabla I1.1b"}
    if bars and worst != "compact":
        blocked("Relleno rectangular no compacto o esbelto con barras: Fig. C-I3.8 no las considera y la Specification no da "
                 "un procedimiento (decisión DI-3).", section, classification=worst)
    if hot and worst == "slender":
        blocked(SLENDER_BLOCK, section)
    plastic = eq.rect_plastic_moment(Fy=m["Fy"], fc=fc, Zs=Zs, t=t, bi=bi, hi=hi, r=geometry["r"], Fysr=Fysr, bars=bars)
    if worst == "compact":
        mode = {"provision": "I3.4b(a)", "equation": "I3-5a", "Mp_kNm": plastic["Mp"] / 1e6, "hn_mm": plastic["hn_mm"],
                "Md_kNm": plastic["Md"] / 1e6, "Mn_kNm": plastic["Mp"] / 1e6}
        if bars:
            pno = dg06_members.tension_control_pno(Fy=m["Fy"], As=section.area, Fysr=Fysr, Asr=geometry["Asr"], fc=fc, Ac=geometry["Ac"])
            control, notes = tension_control(case, plastic["hn_mm"], H, bars, geometry["Fysr"], pno, requirement, "I3.4a(d)")
            return flexure_output(case, section, mn_mode={**mode, **control}, classification=classification,
                                   requirements=requirement, notes=notes, provisions=["I1", "I3.4"])
    elif worst == "noncompact":
        yielding = eq.rect_yield_moment(Fy=m["Fy"], fc=fc, H=H, tw=t, tf=t, bi=bi)
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
    return flexure_output(case, section, mn_mode=mode, classification=classification, requirements=requirement,
                           provisions=["I1", "I3.4"])
