"""Interaction diagrams of encased and filled members, reported next to H1.1 or the method in use; they do not decide the status.

I5(a) members: compact filled sections without bars (Manual Tables 6-3, 6-4) and encased sections whose bars fit Tables 6-2a, 6-2b.
Each point is transformed as in Commentary I5: lambda = Pn/Pno on the axial force, then phi_c and phi_b. Formulas: codes/aisc_dg06.
"""
from ..codes.aisc_360_22 import composite as eq
from ..codes.aisc_dg06 import interaction_tables as tables
from ..models import Check, SteelCase
from ..sections.models import Section
from .composite import _encased_geometry, _filled_geometry, composite_materials, uses_appendix_2

TOLERANCE_MM = 1e-6
TITLES = {"6-2a": "Tabla 6-2a del Manual (Guía 6, Fig. 2-7)", "6-2b": "Tabla 6-2b del Manual (Guía 6, Fig. 2-8)",
          "6-3": "Tabla 6-3 del Manual (Guía 6, Fig. 2-13)", "6-4": "Tabla 6-4 del Manual (Guía 6, Fig. 2-16)"}


def _filled_points(case, section, geometry, axis):
    m = composite_materials(case, section)                # at the temperature of a fire case
    Fy, fc = m["Fy"], m["fc"]
    if geometry["shape"] == "round":
        return "6-4", tables.table_6_4(Fy=Fy, fc=fc, d=geometry["D"], t=geometry["t"])
    bi, hi, H, Zs = ((geometry["bi"], geometry["hi"], section.h_out, section.zx) if axis == "x"
                     else (geometry["hi"], geometry["bi"], section.b_out, section.zy))
    return "6-3", tables.table_6_3(Fy=Fy, fc=fc, As=section.area, Ac=geometry["Ac"], bi=bi, hi=hi, r=geometry["r"], H=H, t=geometry["t"], Zs=Zs)


def _encased_points(case, section, geometry, axis):
    """(table, points), or (None, reason) when the bars do not follow the arrangement that the table assumes."""
    e = case.composite.encased
    Fy, fc = case.material.Fy, case.composite.concrete.fc
    distances = [abs(bar.y if axis == "x" else bar.x) for bar in e.bars]
    outer = max(distances)
    if any(TOLERANCE_MM < v < outer - TOLERANCE_MM for v in distances):
        return None, "hay barras entre la línea central y las barras extremas; la tabla no cubre esa disposición."
    Asr = geometry["Asr"]
    Asr_center = sum(bar.area for bar, v in zip(e.bars, distances) if v <= TOLERANCE_MM)
    if axis == "x":
        h1, h2 = e.B, e.H
        return "6-2a", tables.table_6_2a(Fy=Fy, Fyr=e.Fysr, fc=fc, h1=h1, h2=h2, As=section.area, Asr=Asr, Asrs=Asr_center, c=h2 / 2 - outer,
                                         Zs=section.zx, d=section.d, bf=section.bf, tf=section.tf, tw=section.tw)
    h1, h2 = e.H, e.B
    points = tables.table_6_2b(Fy=Fy, Fyr=e.Fysr, fc=fc, h1=h1, h2=h2, As=section.area, Asr=Asr, Asr_outer=Asr - Asr_center, c=h2 / 2 - outer,
                               Zs=section.zy, bf=section.bf, tf=section.tf, tw=section.tw)
    if points is None:
        return None, "el eje neutro plástico cae en el alma; la tabla no cubre ese caso."
    return "6-2b", points


def interaction_diagrams(case: SteelCase, section: Section, checks: list[Check]) -> list[dict]:
    """One diagram per axis with flexure, or the reason why there is none. Empty without an interaction check."""
    composite = case.composite
    if composite is None or composite.kind not in {"filled", "encased"} or not any(c.id == "interaction" for c in checks):
        return []
    by_id = {c.id: c for c in checks}
    flexures = {axis: by_id[f"flexure_{axis}"] for axis in ("x", "y") if f"flexure_{axis}" in by_id}
    axial = by_id.get("axial")
    out = []
    for axis, flexure in flexures.items():
        entry = {"axis": axis}
        reason = None
        table = points = None
        if flexure.result is None or (axial is not None and axial.result is None):
            reason = "falta el resultado de una revisión."
        elif uses_appendix_2(case, section):
            reason = "materiales de alta resistencia: rige el Apéndice 2 (Guía 6, 2.6), sin tablas de diagrama."
        elif composite.kind == "filled":
            geometry = _filled_geometry(case, section)
            classes = {row["class"] for c in (flexure, *([axial] if axial else [])) for row in c.result["classification"]["elements"]}
            if geometry["Asr"] > 0:
                reason = "Asr ≠ 0: las Tablas 6-3 y 6-4 no incluyen barras."
            elif classes - {"compact"}:
                reason = "sección no compacta o esbelta: las tablas se aplican a secciones compactas."
            else:
                table, points = _filled_points(case, section, geometry, axis)
        else:
            table, points = _encased_points(case, section, _encased_geometry(case, section), axis)
            if table is None:
                reason, points = points, None
        if reason:
            out.append({**entry, "reason": reason})
            continue
        lam, note = 1.0, "Sin compresión: sin reducción por longitud (λ = 1)."
        if axial is not None and case.Pu > 0:
            mode = axial.result["modes"][axial.result["governing_mode"]]
            lam, note = mode["Pn_kN"] / mode.get("Pno_kN", mode.get("Pno_T_kN")), "λ = Pn/Pno (Commentary I5)."
        if case.condition == "fire" and case.fire.steel_temperature > 200:
            note += " Con Fy(T) y f'c(T) del case de incendio (decisión DA4-8)."
        rows = [{"point": name, "P_kN": P / 1000.0, "M_kNm": M / 1e6, "lambda_P_kN": lam * P / 1000.0,
                 "design_P_kN": eq.PHI_C * lam * P / 1000.0, "design_M_kNm": eq.PHI_B * M / 1e6} for name, (P, M) in points.items()]
        out.append({**entry, "table": TITLES[table], "lambda": lam, "note": note, "phi_c": eq.PHI_C, "phi_b": eq.PHI_B, "points": rows,
                    "Pr_kN": case.Pu if case.Pu > 0 else None, "Mr_kNm": flexure.demand})
    return out
