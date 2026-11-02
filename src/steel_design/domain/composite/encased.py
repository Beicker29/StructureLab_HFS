"""Encased W-shapes: geometry, I2.1 requirements, I3.3 flexure."""
import math

from ...codes.aisc_360_22 import composite as eq
from .common import flexure_output, incomplete, require_properties, requirement_row
from .filled import tension_control


def encased_geometry(case, section):
    require_properties(section, "area", "ix", "iy", "d", "bf", "tf", "tw", "zx", "zy")
    e = case.composite.encased
    bars = e.bars
    Asr = sum(b.area for b in bars)
    Isrx = sum(math.pi * b.db**4 / 64 + b.area * b.y**2 for b in bars)
    Isry = sum(math.pi * b.db**4 / 64 + b.area * b.x**2 for b in bars)
    return {"Ag": e.H * e.B, "Ac": e.H * e.B - section.area - Asr, "Asr": Asr, "Isrx": Isrx, "Isry": Isry,
            "Icx": e.B * e.H**3 / 12 - section.ix - Isrx, "Icy": e.H * e.B**3 / 12 - section.iy - Isry}



def encased_requirements(case, section, geometry):
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
        requirement_row("As/Ag", "I2.1a(a)", section.area / Ag >= 0.01, "El núcleo de acero debe ser al menos 1 % de la sección.", section.area / Ag, "≥ 0.01"),
        requirement_row("rho_sr", "I2.1a(c)", geometry["Asr"] / Ag >= 0.004, "La cuantía longitudinal mínima es 0.004.", geometry["Asr"] / Ag, "≥ 0.004"),
        requirement_row("transverse", "I2.1a(b)", transverse and t.spacing <= 0.5 * min(e.B, e.H),
                     "Refuerzo transversal: 10 mm a 300 mm o 13 mm a 400 mm, y separación ≤ 0.5 de la menor dimensión."),
        requirement_row("bar_clearance", "I2.1e(a)", all(clear),
                     "Separación libre entre núcleo y barras: al menos 1.5 db y 38 mm."),
        requirement_row("bars_inside", "I2.1a(b)", inside, "Las barras deben quedar dentro del contorno de concreto."),
    ]



def encased_flexure(case, section, axis):
    Fy = case.material.Fy
    e = case.composite.encased
    geometry = encased_geometry(case, section)
    requirements = encased_requirements(case, section, geometry)
    Zs = section.zx if axis == "x" else section.zy
    if e.flexure_method == "steel":
        mn = Fy * Zs
        mode = {"provision": "I3.3a(2)", "equation": "Mn = Fy·Z (acero solo)", "Mn_kNm": mn / 1e6}
        notes = ["I3.3a(2): plástico sobre el perfil de acero solo."]
    else:
        if not e.anchors_provided:
            incomplete("I3.3a(3) exige conectores: declare composite.encased.anchors_provided = true o use "
                        "flexure_method = steel.", section, ["composite.encased.anchors_provided"])
        h, b = (e.H, e.B) if axis == "x" else (e.B, e.H)
        bars = [(bar.area, bar.y if axis == "x" else bar.x) for bar in e.bars]
        out = eq.encased_plastic_moment(axis=axis, Fy=Fy, Fysr=e.Fysr, fc=case.composite.concrete.fc, b=b, h=h, d=section.d,
                                        bf=section.bf, tf=section.tf, tw=section.tw, As=section.area, Zs=Zs, bars=bars)
        pno = eq.pno_encased(Fy=Fy, As=section.area, Fysr=e.Fysr, Asr=geometry["Asr"], fc=case.composite.concrete.fc,
                             Ac=geometry["Ac"])
        control, control_notes = tension_control(case, out["hn_mm"], h, bars, e.Fysr, pno, requirements, "I3.3a(e)")
        mode = {"provision": "I3.3a(3)", "equation": "Distribución plástica compuesta (I1.2a)", "hn_mm": out["hn_mm"],
                "Md_kNm": out["Md"] / 1e6, "Mn_kNm": out["Mp"] / 1e6, **control}
        notes = ["I3.3a(3): plástico sobre la sección compuesta.", *control_notes]
    return flexure_output(case, section, mn_mode=mode, requirements=requirements, notes=notes, provisions=["I1", "I3.3"])
