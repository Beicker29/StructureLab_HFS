"""Calculation report (memoria de cálculo) of one member, from the results of all its load cases: plain text and PDF.

Presentation only: every value comes from the engine result; nothing is recomputed. Each review shows the load case
with the largest DCR. report_blocks() builds one neutral document model (title, summary, headings, key-value lists,
tables, notes); render_text() and pdf_bytes() draw that same model.
"""
from datetime import datetime, timezone
import math
from pathlib import Path
import re
from typing import NamedTuple

from .execution import overall_status
from .models import DesignResult, SteelCase
from .report_glossary import (EQUATION_OF, FIXED_LITERALS, MODE_NAMES, PARAMETERS, SECTION_PROPERTIES, STIFFNESS_NAMES,
                              parameter_label)

LIMIT_STATES = {"tensile_yielding": "fluencia en la sección bruta", "tensile_rupture": "rotura en la sección neta",
                "flexural_buckling": "pandeo por flexión", "torsional_buckling": "pandeo torsional",
                "flexural_torsional_buckling": "pandeo flexotorsional",
                "constrained_axis_torsional_buckling": "pandeo torsional con arriostramiento desplazado"}
STATUS_TEXT = {"PASS": "CUMPLE", "FAIL": "NO CUMPLE", "INCOMPLETE": "INCOMPLETO"}
# Mode keys shown in the mode table; other scalar keys of a mode are listed as intermediate values.
_MODE_KEYS = {"limit_state", "provision", "axis", "Fe_equation", "Fe_mpa", "Fn_mpa", "Fn_equation",
              "Fy_over_Fe", "area_mm2", "Pn_equation", "area_basis", "effective_area", "Pn_kN", "available_kN",
              "e7_exempt"}
_SECTION_UNITS = {"area": "mm²", "ix": "mm⁴", "iy": "mm⁴", "iw": "mm⁴", "iz": "mm⁴", "j": "mm⁴", "cw": "mm⁶",
                  "sx": "mm³", "sy": "mm³", "zx": "mm³", "zy": "mm³", "sw_a": "mm³", "sw_b": "mm³", "sw_c": "mm³",
                  "sz_a": "mm³", "sz_b": "mm³", "sz_c": "mm³", "H": "–", "tan_alpha": "–"}
_ELEMENTS = {"flange": "ala", "web": "alma", "wall_b": "pared b", "wall_h": "pared h", "wall": "pared",
             "long_leg": "ala larga", "short_leg": "ala corta", "flange_legs": "alas horizontales",
             "web_legs": "alas verticales", "walls": "paredes paralelas al cortante", "bar": "barra"}
def _fmt(value) -> str:
    if isinstance(value, bool):
        return "sí" if value else "no"
    if isinstance(value, int) or not isinstance(value, float):
        return str(value)
    if value != 0 and (abs(value) >= 1e7 or abs(value) < 1e-3):
        return f"{value:.4e}"
    return f"{value:.3f}"


# --- document model ------------------------------------------------------------------------

CHECK_TITLES = {"axial": None, "flexure_x": "Flexión respecto de x", "flexure_y": "Flexión respecto de y",
                "flexure_w": "Flexión respecto del eje principal w", "flexure_z": "Flexión respecto del eje principal z",
                "shear_x": "Cortante paralelo a y (con Mux)", "shear_y": "Cortante paralelo a x (con Muy)",
                "interaction": "Interacción de fuerzas combinadas", "anchor": "Anclaje de componente",
                "fire": "Incendio (Guía 38)"}
FLEXURE_STATES = {"Y": "fluencia (momento plástico)", "LTB": "pandeo lateral-torsional", "FLB": "pandeo local del ala",
                  "WLB": "pandeo local del alma", "LB": "pandeo local", "TFR": "rotura del ala traccionada",
                  "LLB": "pandeo local del ala del ángulo"}


def _check_title(check) -> str:
    if check.id == "axial" and check.chapter == "I":
        return f"{'Tracción' if check.obligations and check.obligations[0].id == 'TY' else 'Compresión'} (Capítulo I)"
    if check.id == "axial":
        return "Compresión (Capítulo E)" if check.chapter == "E" else "Tracción (Capítulo D)"
    return f"{CHECK_TITLES[check.id]} (Capítulo {check.chapter})"


def _capacity_label(check) -> str:
    if check.chapter == "I":
        return {"kN": "φ·Rn", "kN·m": "φb·Mn"}[check.unit]
    return {"E": "φc·Pn", "D": "φt·Pn", "F": "φb·Mn", "G": "φv·Vn", "H": "1.0"}[check.chapter]


_DEMAND_SYMBOL = {"D": "|Pu|", "E": "Pu", "F": "Mu", "G": "Vu", "H": "H", "I": "Demanda"}


def _literal(key: str, mode: dict) -> str:
    """Literal of the reference document for one value of a limit state: fixed definition, else its provision and equation."""
    if key in FIXED_LITERALS:
        return FIXED_LITERALS[key]
    provision = str(mode.get("provision") or "–")
    equation = mode.get(EQUATION_OF.get(key, ""))
    return f"{provision}, Ec. {equation}" if equation else provision


def _parameters(mode: dict, skip: set) -> dict:
    """Parameter, value, unit and literal of every scalar of one limit state."""
    rows = []
    for key, value in mode.items():
        if key in skip or key.endswith("_equation") or isinstance(value, bool) or not isinstance(value, (int, float, str)):
            continue
        unit = PARAMETERS.get(key, ("", "", "–"))[2]
        rows.append([parameter_label(key), value, unit, _literal(key, mode)])
    return {"kind": "table", "headers": ["Parámetro", "Valor", "Unidad", "Literal"], "rows": rows}


NO_APLICA = "No aplica"
FALTA = "Falta implementación"
_ABSENT_TEXT = {"no_aplica": NO_APLICA, "falta_implementacion": FALTA, "sin_dato": "Sin dato"}
_STIFFNESS_UNITS = {"EA": (1e3, "kN"), "GA": (1e3, "kN"), "EI": (1e9, "kN·m²"), "GJ": (1e9, "kN·m²"), "ECw": (1e15, "kN·m⁴"),
                    "": (1.0, "–")}
_REQUIREMENT_TEXT = {"cumple": "CUMPLE", "no_cumple": "NO CUMPLE", "no_aplica": NO_APLICA, "falta_implementacion": FALTA, "sin_dato": "Sin dato"}
_COMPLEMENTARY = ("anchor", "fire")


def _nested(blocks: list[dict]) -> list[dict]:
    """Headings of one check, one level below its numbered title."""
    return [{**b, "kind": "h3"} if b["kind"] == "h2" else b for b in blocks]


def _check_blocks(case: SteelCase, check, notes: list, limitations: list) -> list[dict]:
    r = check.result
    if r is None:
        blocks = [{"kind": "alert", "text": f"{error.get('code')}: {error.get('message')}",
                   "detail": str(error["details"]) if error.get("details") else None} for error in check.errors]
        return blocks + [{"kind": "p", "text": "Comprobación INCOMPLETA: no se informa ninguna resistencia supuesta."}]
    fire = r.get("fire")
    temperature = [{"kind": "kv", "items": [("Propiedades a temperatura elevada (Apéndice 4, 4.2.3b)", f"T = {_fmt(fire['T_C'])} °C; Fy(T) = {_fmt(fire['Fy_T_mpa'])} MPa; "
                                                                                                    f"E(T) = {_fmt(fire['E_T_mpa'])} MPa")]}] if fire else []
    if check.chapter == "E":
        blocks = _compression_blocks(case, check, r)
    elif check.chapter == "D":
        blocks = _tension_blocks(case, check, r)
    elif check.chapter == "G":
        blocks = _shear_blocks(case, check, r)
    elif check.chapter == "H":
        blocks = _interaction_blocks(case, check, r)
    elif check.chapter == "I":
        blocks = _composite_blocks(check, r)
    else:
        blocks = _flexure_blocks(case, check, r)
    blocks = temperature + blocks
    blocks.append({"kind": "h2", "text": f"Obligaciones del Capítulo {check.chapter} (comprobación independiente)"})
    blocks.append({"kind": "table", "headers": ["Obligación", "Disposición", "Atendida por"],
                   "rows": [[o.id, o.provision, o.satisfied_by or "NO ATENDIDA"] for o in check.obligations]})
    for error in check.errors:
        blocks.append({"kind": "alert", "text": f"{error.get('code')}: {error.get('id', '')} "
                                                f"{error.get('message', '')}".strip(), "detail": None})
    notes += [n for n in r["notes"] if n not in notes]
    limitations += [x for x in r["limitations"] if x not in limitations]
    return blocks


class _Governing(NamedTuple):
    tag: str | None
    case: SteelCase
    result: DesignResult
    check: object


_CONDITIONS = (("construction", "construcción"), ("ultimate", "últimas"), ("fire", "incendio"))
_CONDITION_TITLE = {"construcción": "Condiciones de construcción", "últimas": "Condiciones últimas", "incendio": "Condiciones de incendio"}
_CHECK_ORDER = ("flexure_x", "flexure_w", "flexure_y", "flexure_z", "shear_y", "shear_x", "interaction", "anchor", "fire")
_REQUIREMENT_RANK = {"sin_dato": 0, "no_cumple": 1, "falta_implementacion": 2, "cumple": 3, "no_aplica": 4}


def _governing(executions: list, check_id: str, *, condition: str, tension: bool | None = None) -> _Governing | None:
    """The load case of one review with the largest DCR; one that could not be calculated, or that fails, is never hidden."""
    found = []
    for tag, case, result in executions:
        check = result.check(check_id)
        if check and case.condition == condition and (tension is None or (case.Pu < 0) == tension):
            found.append(_Governing(tag, case, result, check))
    return max(found, key=lambda g: (g.check.ratio is None, g.check.status.value == "FAIL", g.check.ratio or 0.0), default=None)


def _all_governing(executions: list) -> list[tuple[str, _Governing]]:
    """Every review of the member, by condition."""
    out = []
    for condition, label in _CONDITIONS:
        found = [_governing(executions, "axial", condition=condition, tension=False), _governing(executions, "axial", condition=condition, tension=True)]
        found += [_governing(executions, check_id, condition=condition) for check_id in _CHECK_ORDER]
        out += [(label, g) for g in found if g]
    return out


def _case_name(tag: str | None) -> str:
    return tag or "única"


def _axial_review(number, title, tension, executions, data, absent, notes, limitations) -> list[dict]:
    """The governing case of the axial force, in ultimate and in fire conditions."""
    blocks = [{"kind": "h1", "text": f"{number}. {title}"}]
    found = [(g, suffix) for g, suffix in ((_governing(executions, "axial", condition="ultimate", tension=tension), ""),
                                           (_governing(executions, "axial", condition="fire", tension=tension), ", condiciones de incendio")) if g]
    if not found:
        return blocks + [{"kind": "p", "text": f"{NO_APLICA}: {absent}"}]
    for index, (governing, suffix) in enumerate(found, start=1):
        blocks += data(governing.case)
        blocks.append({"kind": "h2", "text": f"{number}.{index} {_check_title(governing.check)}{suffix}; case gobernante: {_case_name(governing.tag)}"})
        blocks += _nested(_check_blocks(governing.case, governing.check, notes, limitations))
    return blocks


def _condition_chapter(number, title, axes, data, executions, notes, limitations) -> list[dict]:
    """Construction, ultimate and fire conditions, each one about the X and Y axes."""
    blocks = [{"kind": "h1", "text": f"{number}. {title}"}]
    for index, (condition, label) in enumerate(_CONDITIONS, start=1):
        blocks.append({"kind": "h2", "text": f"{number}.{index} {_CONDITION_TITLE[label]}"})
        for axis_index, (axis_label, check_ids, demand) in enumerate(axes, start=1):
            blocks.append({"kind": "h3", "text": f"{number}.{index}.{axis_index} {axis_label}"})
            found = [g for g in (_governing(executions, i, condition=condition) for i in check_ids) if g]
            if not found:
                blocks.append({"kind": "p", "text": f"{NO_APLICA}: ningún case en {_CONDITION_TITLE[label].lower()} tiene {demand}."})
            for governing in found:
                blocks.append({"kind": "p", "text": f"{_check_title(governing.check)}; case gobernante: {_case_name(governing.tag)}."})
                blocks += data(governing)
                blocks += _nested(_check_blocks(governing.case, governing.check, notes, limitations))
    return blocks


def report_blocks(executions: list) -> list[dict]:
    """Neutral document model of the report of one member: executions are its (name, case, result), one per load case (Spanish)."""
    tag, case, result = next((e for e in executions if e[1].condition != "construction"), executions[0])
    results = [r for _, _, r in executions]
    governing = _all_governing(executions)
    chapters = sorted({g.check.chapter for _, g in governing})
    action = " + ".join(dict.fromkeys(_check_title(g.check).split(" (")[0].lower() for _, g in governing))
    ratios = [r.ratio for r in results if r.ratio is not None]
    ratio = max(ratios) if ratios else None
    simple_method = "; Apéndice 4, 4.2.4d" if any(r.fire and r.fire["simple_method"] for r in results) else ""
    blocks = [{"kind": "title", "member": result.section, "case": None, "status": overall_status(results).value,
               "action": action,
               "meta": [("Norma", f"ANSI/AISC 360-22, Capítulo{'s' if len(chapters) > 1 else ''} {', '.join(chapters)}{simple_method}"),
                                                ("Método", "LRFD"), ("Cases de carga", str(len(executions))), ("Fecha", f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC"),
                        ("Programa", "StructureLab_HFS")],
               "ratio": ratio}]
    cards = []
    for label, g in governing:
        c = g.check
        prefix = "" if label == "últimas" else f"{label.capitalize()}, "
        dcr = f"DCR={c.ratio:.3f}" if c.ratio is not None else "DCR no calculado"
        if c.unit == "–":
            name = "Interacción" if c.id == "interaction" else CHECK_TITLES[c.id]
            cards.append((f"{prefix}{name} ({c.result['governing_equation'] if c.result else c.chapter}):", [dcr]))
        else:
            strength = [f"{_capacity_label(c)}={_fmt(c.capacity)} {c.unit}"] if c.capacity is not None else []
            cards.append((f"{prefix}{_check_title(c).split(' (')[0]}:", strength + [dcr]))
    if cards:
        blocks.append({"kind": "summary", "items": cards})
    notes, limitations = [], []
    blocks += _material_blocks(case, result)
    blocks += _temperature_blocks(executions)
    blocks += _geometry_blocks(case, result, tag, executions)
    blocks += _demand_blocks(executions)
    blocks += _requirement_blocks(executions)
    blocks += _service_blocks(result, governing)
    blocks += _axial_review(6, "Revisión de capacidad a carga de compresión", False, executions, _compression_data,
                            "ningún case tiene carga de compresión (Pu > 0).", notes, limitations)
    blocks += _axial_review(7, "Revisión de capacidad a carga de tracción", True, executions, _tension_data,
                            "ningún case tiene carga de tracción (Pu < 0).", notes, limitations)
    blocks += _condition_chapter(8, "Revisión de capacidad a fuerza cortante", (
        ("Paralelo al eje X (Vuy)", ("shear_y",), "Vuy"), ("Paralelo al eje Y (Vux)", ("shear_x",), "Vux")),
        lambda g: _shear_data(g.case), executions, notes, limitations)
    blocks += _condition_chapter(9, "Revisión de capacidad a momento flector", (
        ("Respecto del eje X (Mux, Mw)", ("flexure_x", "flexure_w"), "Mux ni Mw"), ("Respecto del eje Y (Muy, Mz)", ("flexure_y", "flexure_z"), "Muy ni Mz")),
        lambda g: _flexure_data(g.case, g.check), executions, notes, limitations)
    blocks += [{"kind": "h1", "text": "10. Revisión de capacidad a momento torsional"},
               {"kind": "p", "text": f"{FALTA}: la entrada no admite momento torsional y la sección H3 no está programada."}]
    blocks += _dcr_blocks(executions, governing, ratio, notes, limitations)
    return [_with_references(block) for block in blocks]


_REFERENCE_HEADERS = {"Literal": "Referencia literal", "Disposición": "Referencia literal", "Literal u observación": "Referencia literal u observación"}
_GUIDES = (("Guía 38", "AISC Design Guide 38"), ("Guía 6", "AISC Design Guide 6"), ("DG38", "AISC Design Guide 38"), ("DG6", "AISC Design Guide 6"))
_STANDARD_TOKEN = re.compile(r"(?<![\w.-])(Commentary\b|Apéndice\b|Capítulo [A-N]\b|Nota de\b|Tabla\b|[A-N]\d+(?:\.\d+)*(?:[a-z](?![a-z]))?(?:\([a-z0-9]+\))*(?![\w-]))")


def _reference(text: str) -> str:
    """Each literal with its document: AISC 360-22 unless the literal names another one."""
    parts = []
    for part in text.split("; "):
        for short, full in _GUIDES:
            part = part.replace(short, full)
        if "AISC" not in part:
            part = _STANDARD_TOKEN.sub(lambda m: f"AISC 360-22 {m[1]}", part, count=1)
        parts.append(part)
    return "; ".join(parts)


def _with_references(block: dict) -> dict:
    if block["kind"] != "table":
        return block
    columns = [i for i, header in enumerate(block["headers"]) if header in _REFERENCE_HEADERS]
    if not columns:
        return block
    rows = [[_reference(cell) if i in columns and isinstance(cell, str) else cell for i, cell in enumerate(row)] for row in block["rows"]]
    return {**block, "headers": [_REFERENCE_HEADERS.get(h, h) for h in block["headers"]], "rows": rows}


def _property_table(rows: list) -> dict:
    return {"kind": "table", "headers": ["Propiedad", "Valor", "Unidad", "Literal"], "rows": rows}


def _material_blocks(case: SteelCase, result: DesignResult) -> list[dict]:
    mat, st = case.material, result.stiffness
    composite = case.composite
    blocks = [{"kind": "h1", "text": "1. Propiedades mecánicas de los materiales"}, {"kind": "h2", "text": "1.1 Acero estructural"}]
    origin = "Catálogo Materiales.xlsx" if mat.name else "Dato del usuario"
    rows = [["Material", mat.name, "–", origin]] if mat.name else []
    rows += [["Esfuerzo de fluencia mínimo especificado (Fy)", mat.Fy, "MPa", origin],
             ["Resistencia a tracción mínima especificada (Fu)", mat.Fu if mat.Fu else "no indicado", "MPa", origin],
             ["Módulo de elasticidad del acero (Es)", st.get("Es_mpa", mat.E), "MPa", "I2.1b" if composite else "E3"]]
    if st.get("Gs_mpa"):
        rows.append(["Módulo de cortante del acero (Gs)", st["Gs_mpa"], "MPa", "I1.5(e)" if composite else "E4"])
    blocks.append(_property_table(rows))
    blocks.append({"kind": "h2", "text": "1.2 Concreto estructural"})
    if composite:
        concrete = composite.concrete
        rows = [["Resistencia a compresión especificada (f'c)", concrete.fc, "MPa", "Dato del usuario; límites en I1.3(a)"],
                ["Peso unitario del concreto (wc)", concrete.wc, "kg/m³", "Dato del usuario; rango en I2.1b"],
                ["Concreto liviano", concrete.lightweight, "–", "Dato del usuario; I1.3(a)"]]
        if st.get("Ec_mpa"):
            rows += [["Módulo de elasticidad del concreto (Ec)", st["Ec_mpa"], "MPa", "I2.1b"],
                     ["Módulo de cortante del concreto (Gc = 0.4·Ec)", st["Gc_mpa"], "MPa", "I1.5(e)"]]
        blocks.append(_property_table(rows))
    else:
        blocks.append({"kind": "p", "text": f"{NO_APLICA}: miembro sin concreto."})
    blocks.append({"kind": "h2", "text": "1.3 Acero de refuerzo"})
    bars = composite and (composite.encased or composite.filled)
    if bars:
        literal = "I1.3(c)"
        blocks.append(_property_table([
            ["Esfuerzo de fluencia de las barras (Fysr)", bars.Fysr, "MPa", f"Dato del usuario; límite en {literal}"],
            ["Número de barras longitudinales", len(bars.bars), "–", "Dato del usuario"],
            ["Área total de barras longitudinales (Asr)", sum(b.area for b in bars.bars), "mm²", "Dato del usuario"],
            ["Diámetro del refuerzo transversal (db)", bars.transverse.db, "mm", "Dato del usuario"],
            ["Separación del refuerzo transversal (s)", bars.transverse.spacing, "mm", "Dato del usuario"]]))
    else:
        blocks.append({"kind": "p", "text": f"{NO_APLICA}: miembro sin barras de refuerzo."})
    return blocks


def _temperature_blocks(executions: list) -> list[dict]:
    """1.4: the temperatures of each fire case, data of the user, with their retention factors (Appendix 4, 4.2.3b)."""
    blocks = [{"kind": "h2", "text": "1.4 Propiedades a temperatura elevada"}]
    fires = [(tag, r.fire) for tag, _, r in executions if r.fire]
    if not fires:
        return blocks + [{"kind": "p", "text": f"{NO_APLICA}: ningún case de incendio."}]
    steel, concrete, bars = [], [], []
    for tag, fire in fires:
        s = fire["steel"]
        steel.append([_case_name(tag), fire["T_C"], s["kE"], s["kp"], s["ky"], s["Fy_T_mpa"], s["Fu_T_mpa"] if s["Fu_T_mpa"] else "no indicado", s["E_T_mpa"], s["G_T_mpa"], "Tabla A-4.2.1"] if s
                     else [_case_name(tag), fire["T_C"]] + ["sin efecto"] * 7 + ["Apéndice 4, 4.2.4d"])
        concrete += [[_case_name(tag), c["T_C"], c["kc"], c["kEc"], c["fc_T_mpa"], "Tabla A-4.2.2"] for c in fire["concrete"]]
        if fire["bars"]:
            bars.append([_case_name(tag), fire["bars"]["T_C"], fire["bars"]["kE"], fire["bars"]["ky"], "Tabla A-4.2.1"])
    blocks.append({"kind": "p", "text": "Temperaturas del análisis térmico del usuario (Apéndice 4, 4.2.2). Con T del acero ≤ 200 °C las resistencias no consideran la temperatura (4.2.4d)."})
    blocks.append({"kind": "table", "headers": ["Case", "T del acero (°C)", "kE", "kp", "ky", "Fy(T) (MPa)", "Fu(T) (MPa)", "E(T) (MPa)", "G(T) (MPa)", "Literal"], "rows": steel})
    if concrete:
        blocks.append({"kind": "table", "headers": ["Case", "T del concreto (°C)", "kc", "kEc", "f'c(T) (MPa)", "Literal"], "rows": concrete})
    if bars:
        blocks.append({"kind": "table", "headers": ["Case", "T de las barras (°C)", "kE", "ky", "Literal"], "rows": bars})
    return blocks


def _stiffness_table(rows: list[dict]) -> dict:
    out = []
    for row in rows:
        if row["status"] == "calculada":
            scale, unit = _STIFFNESS_UNITS[row["dimension"]]
            out.append([f"{STIFFNESS_NAMES[row['symbol']]} ({row['symbol']})", row["value"] / scale, unit, row["source"]])
        else:
            out.append([f"{STIFFNESS_NAMES[row['symbol']]} ({row['symbol']})", _ABSENT_TEXT[row["status"]], "–", row["reason"]])
    return {"kind": "table", "headers": ["Rigidez", "Valor", "Unidad", "Literal u observación"], "rows": out}


def _lengths_table(executions: list) -> dict | None:
    rows = {}
    for _, case, _ in executions:
        if case.lengths:
            name = "construcción" if case.condition == "construction" else "últimas e incendio"
            rows[(name, case.lengths.Lx, case.lengths.Ly, case.lengths.Lz)] = None
    return {"kind": "table", "headers": ["Condición", "Lx: no arriostrada respecto de x (mm)", "Ly: no arriostrada respecto de y (mm)",
                                         "Lz: no arriostrada para torsión (mm)"], "rows": [list(k) for k in rows]} if rows else None


def _geometry_blocks(case: SteelCase, result: DesignResult, tag: str | None, executions: list) -> list[dict]:
    source = result.section_data.get("source") or {}
    origin = (f"catálogo {source.get('sheet')} fila {source.get('row')} (sha256 {source.get('sha256', '')[:12]})"
              if source else "sección definida en la entrada")
    items = [("Perfil", f"{result.section} ({result.family})"), ("Origen", origin)]
    st = result.stiffness
    if case.composite:
        items.append(("Miembro compuesto", case.composite.kind))
    blocks = [{"kind": "h1", "text": "2. Propiedades geométricas"}, {"kind": "h2", "text": "2.1 Geometría"}, {"kind": "kv", "items": items},
              {"kind": "table", "headers": ["Propiedad", "Valor", "Unidad", "Fuente"], "rows": [
                  ["{} ({})".format(*SECTION_PROPERTIES[k]), v, _SECTION_UNITS.get(k, "–" if k.endswith("ratio") else "mm"),
                   "Catálogo" if source else "Entrada"]
                  for k, v in result.section_data.items() if k not in {"name", "type", "source"}]}]
    if st.get("geometry"):
        provision = {"filled": "I2.2b", "encased": "I2.1b", "wall": "I1.5(e)", "c_wall": "I1.5(e)"}.get(case.composite.kind, "–")
        blocks.append({"kind": "table", "headers": ["Propiedad", "Valor", "Unidad", "Literal"], "rows": [
            [parameter_label(k), v, PARAMETERS[k][2], provision] for k, v in st["geometry"].items()]})
    lengths = _lengths_table(executions)
    if lengths:
        blocks.append(lengths)
    blocks.append({"kind": "h2", "text": "2.2 Rigideces elásticas"})
    if "error" in st:
        blocks.append({"kind": "alert", "text": f"No calculadas: {st['error']}", "detail": None})
    else:
        if case.composite:
            blocks.append({"kind": "p", "text": "AISC Design Guide 6, sección 2.8 (deriva y servicio): no es norma y no interviene "
                                                f"en la resistencia. P = Pu del case {_case_name(tag)} si es compresión; en otro caso P = 0."})
        blocks.append(_stiffness_table(st["elastic"]))
    blocks.append({"kind": "h2", "text": "2.3 Rigideces efectivas"})
    if "error" in st:
        blocks.append({"kind": "alert", "text": f"No calculadas: {st['error']}", "detail": None})
    else:
        blocks.append({"kind": "p", "text": "I1.5, rigideces nominales para el cálculo de resistencias requeridas." if case.composite
                                            else "En miembros no compuestos, las rigideces efectivas son iguales a las elásticas (2.2)."})
        blocks.append(_stiffness_table(st["effective"]))
    blocks.append({"kind": "h2", "text": "2.4 Rigideces para método directo: rigideces efectivas (análisis de estabilidad, DAM)"})
    if "error" in st:
        blocks.append({"kind": "alert", "text": f"No calculadas: {st['error']}", "detail": None})
    else:
        blocks.append({"kind": "p", "text": "Rigideces reducidas para un análisis por el método directo (C2.3 e I1.5). El programa no hace ese análisis: "
                                            "deben usarse en el modelo. " + ("En miembros compuestos, τb es el valor indicado por el usuario." if case.composite
                                                                              else "En miembros no compuestos, τb es siempre 1.0.")})
        if not case.composite or case.Pu < 0:
            blocks.append({"kind": "p", "text": "C2.3(c): se permite τb = 1.0 aunque Pr/Pns > 0.5, si se aplica una carga ficticia de 0.001·Yi en todos los "
                                                "niveles y en todas las combinaciones. El programa no evalúa Pr/Pns ni aplica esa carga: es parte del modelo."})
        blocks.append(_stiffness_table(st["direct_analysis"]))
    return blocks


def _requirement_table(rows: list[dict]) -> dict:
    out = []
    for row in rows:
        if row["status"] in {"cumple", "no_cumple"}:
            text = _REQUIREMENT_TEXT[row["status"]] + ("" if row["binding"] else f" ({row['qualifier']})")
            out.append([row["description"], "–" if row["value"] is None else row["value"], row["limit"] or "ver requisito", row["provision"], text])
        else:
            out.append([row["description"], "–", row["reason"], row["provision"], _REQUIREMENT_TEXT[row["status"]]])
    return {"kind": "table", "headers": ["Requisito", "Valor", "Límite u observación", "Literal", "Resultado"], "rows": out}


def _merged_requirements(executions: list, group: str) -> list[dict]:
    """Each requirement once, as its least favorable load case leaves it; construction cases have the steel section alone."""
    rows = {}
    for _, case, result in executions:
        for row in result.requirements[group] if case.condition != "construction" else []:
            key = (row["description"], row["provision"])
            if key not in rows or _REQUIREMENT_RANK[row["status"]] < _REQUIREMENT_RANK[rows[key]["status"]]:
                rows[key] = row
    return list(rows.values())


def _requirement_blocks(executions: list) -> list[dict]:
    return [{"kind": "h1", "text": "4. Revisión de requerimientos técnicos"},
            {"kind": "h2", "text": "4.1 Propiedades mecánicas de los materiales"}, _requirement_table(_merged_requirements(executions, "materials")),
            {"kind": "h2", "text": "4.2 Propiedades geométricas"}, _requirement_table(_merged_requirements(executions, "geometry"))]


def _demand_table(executions: list, condition: str, label: str) -> list[dict]:
    cases = [(tag, case, result) for tag, case, result in executions if case.condition == condition]
    if not cases:
        return [{"kind": "p", "text": f"{NO_APLICA}: ningún case de {label}."}]
    angle = any(result.family.upper() == "SINGLE_ANGLE" for _, _, result in cases)
    moments = ["Mw (kN·m)", "Mz (kN·m)"] if angle else []
    rows = [[_case_name(tag), case.Pu, case.Mux, case.Muy] + ([case.Mw, case.Mz] if angle else []) + [case.Vux, case.Vuy] for tag, case, _ in cases]
    blocks = [{"kind": "table", "headers": ["Case", "Pu (kN)", "Mux (kN·m)", "Muy (kN·m)"] + moments + ["Vux (kN)", "Vuy (kN)"], "rows": rows}]
    if condition == "fire":
        blocks.insert(0, {"kind": "p", "text": "Del análisis del usuario con la combinación A-4-1 (Apéndice 4, 4.1.4). Temperaturas: 1.4."})
    for tag, _, result in cases:
        info = next(((c.result or {}).get("second_order") for c in result.checks if (c.result or {}).get("second_order")), None)
        if info:
            blocks.append({"kind": "p", "text": f"Apéndice 8.1, case {_case_name(tag)}: las revisiones usan Pr = {_fmt(info['Pr_kN'])} kN y Mr = {_fmt(info['Mr_kNm'])} kN·m "
                                                f"(B1 = {_fmt(info['B1'])}, B2 = {_fmt(info['B2'])})."})
    return blocks


def _demand_blocks(executions: list) -> list[dict]:
    blocks = [{"kind": "h1", "text": "3. Solicitaciones"},
              {"kind": "p", "text": "Pu > 0: compresión; Pu < 0: tracción. Mux y Muy, respecto de los ejes geométricos; Mw y Mz, respecto de los ejes principales de ángulos simples. "
                                    "Vux acompaña a Mux y es paralela a y; Vuy acompaña a Muy y es paralela a x. El momento torsional (Tu): " + f"{FALTA.lower()}, la entrada no lo admite."}]
    for number, condition, title, label in ((1, "ultimate", "Cargas últimas", "cargas últimas"), (2, "construction", "Cargas de construcción", "construcción"),
                                            (3, "fire", "Cargas en condición de incendio", "incendio")):
        blocks.append({"kind": "h2", "text": f"3.{number} {title}"})
        blocks += _demand_table(executions, condition, label)
    blocks.append({"kind": "h2", "text": "3.4 Deflexiones"})
    basis = executions[0][1].serviceability
    if basis:
        d = basis.deflections
        blocks.append(_property_table([["Luz real", basis.actual_span, "mm", "Dato del usuario"],
                                       ["Luz efectiva (deflexiones), L", basis.effective_span, "mm", "Dato del usuario"],
                                       ["Deflexión por carga viva a corto plazo", d.live_short, "mm", "Dato del usuario"],
                                       ["Deflexión por carga muerta a corto plazo", d.dead_short, "mm", "Dato del usuario"],
                                       ["Deflexión por carga viva + muerta a largo plazo", d.total_long, "mm", "Dato del usuario"]]))
    else:
        blocks.append({"kind": "p", "text": f"{NO_APLICA}: la entrada no indica deflexiones (serviceability)."})
    return blocks


def _service_blocks(result: DesignResult, governing: list) -> list[dict]:
    blocks = [{"kind": "h1", "text": "5. Revisión de condiciones de funcionalidad y/o servicio"}, {"kind": "h2", "text": "5.1 Revisión de deflexiones"}]
    if result.serviceability:
        blocks.append({"kind": "p", "text": "Capítulo L: la norma no fija límites numéricos; L/n son criterios del usuario, con L la luz efectiva. "
                                            "Exceder un límite se reporta y no cambia el estado."})
        blocks.append({"kind": "table", "headers": ["Deflexión", "Valor (mm)", "n", "Límite, L/n (mm)", "Literal", "Resultado"], "rows": [
            [r["description"], r["value_mm"], r["divisor"], r["limit_mm"], "Capítulo L; límite del usuario", "CUMPLE" if r["satisfied"] else "NO CUMPLE (no cambia el estado)"]
            for r in result.serviceability]})
    else:
        blocks.append({"kind": "p", "text": f"{NO_APLICA}: la entrada no indica deflexiones (serviceability)."})
    blocks.append({"kind": "h2", "text": "5.2 Condición de construcción"})
    rows = [g for label, g in governing if label == "construcción"]
    if not rows:
        return blocks + [{"kind": "p", "text": f"{NO_APLICA}: ningún case de construcción."}]
    blocks.append({"kind": "p", "text": "Resistencia de la sección de acero sola (I3.1b en vigas compuestas), con las longitudes de construcción. El detalle está en 8.1 y 9.1."})
    blocks.append({"kind": "table", "headers": ["Revisión", "Case", "Demanda", "Resistencia", "DCR", "Estado"], "rows": [
        [_check_title(g.check), _case_name(g.tag), f"{_fmt(g.check.demand)} {g.check.unit}",
         f"{_fmt(g.check.capacity)} {g.check.unit}" if g.check.capacity is not None else "no calculada",
         g.check.ratio if g.check.ratio is not None else "no calculado", STATUS_TEXT[g.check.status.value]] for g in rows]})
    return blocks


def _compression_data(case: SteelCase) -> list[dict]:
    f, ln = case.factors, case.lengths
    items = []
    if f.xa or f.ya:
        items.append(("Arriostramiento desplazado", f"xa = {_fmt(f.xa)} mm; ya = {_fmt(f.ya)} mm"))
    if case.single_angle_e5:
        b = case.single_angle_e5
        items.append(("Base E5", f"configuración E5({b.configuration}); ala conectada {b.connected_leg}; "
                                 f"L = {_fmt(b.L)} mm; condiciones (1) {_fmt(b.loaded_at_ends_through_same_leg)}, "
                                 f"(2) {_fmt(b.welded_or_two_bolts_min)}, (3) {_fmt(b.no_intermediate_transverse_loads)}"))
    if case.double_angle_e6:
        b = case.double_angle_e6
        items.append(("Base E6", f"conectores {b.connectors}; a = {_fmt(b.a)} mm; conexión de extremo "
                                 f"soldada o pretensada: {_fmt(b.end_connection_welded_or_pretensioned)}"))
    blocks = [{"kind": "kv", "items": items}] if items else []
    if ln is not None:
        blocks.append({"kind": "table", "headers": ["Longitud no arriostrada (L)", "Valor (mm)", "Factor de longitud efectiva (K)",
                                                    "Longitud efectiva, Lc = K·L (mm)", "Literal"], "rows": [
            ["Lx: para pandeo por flexión respecto del eje x", ln.Lx, f.Kx, f.Kx * ln.Lx, "E2"],
            ["Ly: para pandeo por flexión respecto del eje y", ln.Ly, f.Ky, f.Ky * ln.Ly, "E2"],
            ["Lz: para pandeo torsional respecto del eje longitudinal", ln.Lz, f.Kz, f.Kz * ln.Lz, "E4"]]})
    return blocks


def _tension_data(case: SteelCase) -> list[dict]:
    t = case.tension
    if not t:
        return []
    rows = [["Área neta (An)", t.An, "mm²", "Dato del usuario; B4.3b"], ["Factor de rezago de cortante (U)", t.U, "–", "Dato del usuario; D3, Tabla D3.1"]]
    if t.fabricated_length:
        rows.append(["Longitud fabricada (L)", t.fabricated_length, "mm", "Nota de D1"])
    return [_property_table(rows)]


def _shear_data(case: SteelCase) -> list[dict]:
    if not (case.shear and case.shear.Lv):
        return []
    return [_property_table([["Distancia del cortante máximo al cortante nulo (Lv)", case.shear.Lv, "mm", "Dato del usuario; G5"]])]


def _flexure_data(case: SteelCase, check) -> list[dict]:
    fl = case.flexure
    holes = "no declarado" if not fl or fl.tension_flange_holes is None else _fmt(fl.tension_flange_holes)
    lb = ((check.result or {}).get("inputs") or {}).get("Lb_mm")
    rule = "min(Ly, Lz)" if check.id in {"flexure_x", "flexure_w"} else "min(Lx, Lz)"
    rows = [["Longitud no arriostrada lateralmente (Lb)", lb if lb else NO_APLICA, "mm", f"{rule}, de las longitudes de la condición"],
            ["Factor de modificación por pandeo lateral-torsional (Cb)", fl.Cb if fl else 1.0, "–", "F1, Ec. F1-1"],
            ["Agujeros en el ala traccionada", holes, "–", "F13.1"]]
    if fl and fl.Afn:
        rows.append(["Área neta del ala traccionada (Afn)", fl.Afn, "mm²", "Dato del usuario; F13.1"])
    if fl and fl.lateral_torsional_restraint:
        rows.append(["Restricción lateral-torsional del ángulo", fl.lateral_torsional_restraint, "–", "F10.2"])
    if fl and fl.tension_cb_amplification:
        rows.append(["Amplificación de Cb por tracción", "solicitada", "–", "H1.2"])
    if case.angle_flexure:
        af = case.angle_flexure
        for name, value, literal in (("Alas verticales del ángulo doble", af.web_legs, "F9"), ("Punta del ángulo", af.toe, "F10"),
                                     ("Ala comprimida del ángulo", af.leg_in_compression, "F10.2(1)")):
            if value:
                rows.append([name, value, "–", f"Dato del usuario; {literal}"])
    return [_property_table(rows)]


def _axis_scale(largest: float) -> tuple[float, float]:
    """Round axis maximum and step, about four intervals: 1, 2, 2.5 or 5 times a power of ten."""
    raw = (largest or 1.0) / 4
    power = 10 ** math.floor(math.log10(raw))
    step = next(s * power for s in (1, 2, 2.5, 5, 10) if s * power >= raw)
    return step * math.ceil(largest / step + 1e-9) if largest else step * 4, step


def _diagram_blocks(result: DesignResult) -> list[dict]:
    blocks = []
    for d in result.interaction_diagrams:
        name = f"Diagrama de interacción respecto de {d['axis']}"
        if "reason" in d:
            blocks += [{"kind": "h3", "text": name}, {"kind": "p", "text": f"{NO_APLICA}: {d['reason']}"}]
            continue
        rows = [[p["point"], p["P_kN"], p["M_kNm"], p["lambda_P_kN"], p["design_P_kN"], p["design_M_kNm"]] for p in d["points"]]
        order = sorted(d["points"], key=lambda p: -p["P_kN"])
        demand = (d["Mr_kNm"], d["Pr_kN"]) if d["Pr_kN"] is not None else None
        blocks += [{"kind": "h3", "text": f"{name}: {d['table']}"},
                   {"kind": "p", "text": f"Distribución plástica, I1.2a. Es informativo y no decide el estado: el índice lo da la revisión anterior. {d['note']} "
                                         f"λ = {_fmt(d['lambda'])}; φc = {d['phi_c']:.2f}; φb = {d['phi_b']:.2f}."},
                   {"kind": "table", "headers": ["Punto", "Fuerza axial nominal, P (kN)", "Momento nominal, M (kN·m)", "Con longitud, λ·P (kN)",
                                                 "De diseño, φc·λ·P (kN)", "De diseño, φb·M (kN·m)"], "rows": rows},
                   {"kind": "chart", "title": f"Fuerza axial y momento respecto de {d['axis']}", "x_label": "Momento (kN·m)", "y_label": "Fuerza axial (kN)",
                    "series": [{"name": "Nominal", "points": [(p["M_kNm"], p["P_kN"], p["point"]) for p in order], "dash": True},
                               {"name": "De diseño (con λ y φ)", "points": [(p["design_M_kNm"], p["design_P_kN"], None) for p in order], "dash": False}],
                    "demand": demand}]
    return blocks


def _dcr_blocks(executions: list, governing: list, ratio, notes: list, limitations: list) -> list[dict]:
    rows, ratios = [], []
    for label, g in governing:
        c = g.check
        if c.unit == "–":
            demand, capacity = "–", "1.000"
        else:
            demand, capacity = f"{_fmt(c.demand)} {c.unit}", f"{_fmt(c.capacity)} {c.unit}" if c.capacity is not None else "no calculada"
        rows.append([label.capitalize(), _check_title(c), _case_name(g.tag), demand, capacity, c.ratio if c.ratio is not None else "no calculado", STATUS_TEXT[c.status.value]])
        ratios.append(c.ratio if c.ratio is not None else -1.0)
    table = {"kind": "table", "headers": ["Condición", "Revisión", "Case gobernante", "Demanda", "Capacidad", "Índice demanda/capacidad (DCR)", "Estado"], "rows": rows}
    if ratios and max(ratios) >= 0:
        table["highlight"] = ratios.index(max(ratios))
    items = [("Índice demanda/capacidad máximo (DCR)", _fmt(ratio) if ratio is not None else "no calculado")]
    if ratios and max(ratios) >= 0:
        items.append(("Case del DCR máximo", rows[ratios.index(max(ratios))][2]))
    items.append(("Estado global", STATUS_TEXT[overall_status([r for _, _, r in executions]).value]))
    blocks = [{"kind": "h1", "text": "11. Índices DCR"}, {"kind": "h2", "text": "11.1 Demanda/capacidad por revisión, con el case de mayor DCR"}, table,
              {"kind": "kv", "items": items}, {"kind": "h2", "text": "11.2 Interacción de fuerzas combinadas"}]
    interactions = [(label, g) for label, g in governing if g.check.id == "interaction"]
    for label, g in interactions:
        blocks.append({"kind": "h3", "text": f"{_check_title(g.check)}; {_CONDITION_TITLE[label].lower()}; case gobernante: {_case_name(g.tag)}"})
        blocks += _nested(_check_blocks(g.case, g.check, notes, limitations))
        blocks += _diagram_blocks(g.result)
    if not interactions:
        blocks.append({"kind": "p", "text": f"{NO_APLICA}: ningún case combina fuerza axial y flexión ni flexión en dos ejes."})
    blocks.append({"kind": "h2", "text": "11.3 Revisiones complementarias"})
    extra = [g for _, g in governing if g.check.id in _COMPLEMENTARY]
    for g in extra:
        blocks.append({"kind": "h3", "text": f"{_check_title(g.check)}; case gobernante: {_case_name(g.tag)}"})
        blocks += _nested(_check_blocks(g.case, g.check, notes, limitations))
    if not extra:
        blocks.append({"kind": "p", "text": f"{NO_APLICA}: sin anclajes de componente ni incendio."})
    blocks.append({"kind": "h2", "text": "11.4 Notas y limitaciones"})
    return blocks + [{"kind": "note", "text": text} for text in notes + limitations + [executions[0][2].scope]]


def _verification(check) -> tuple:
    symbol = _DEMAND_SYMBOL[check.chapter] if check.chapter in "FG" else "|Pu|"
    return ("Verificación", f"{symbol} / {_capacity_label(check)} = {_fmt(check.demand)} / {_fmt(check.capacity)} "
                            f"= {_fmt(check.ratio)}")


def _tension_blocks(case: SteelCase, check, c: dict) -> list[dict]:
    blocks = [{"kind": "h2", "text": "Área neta efectiva (D3)"},
              {"kind": "p", "text": f"Área neta efectiva: Ae = An·U = {_fmt(c['inputs']['An_mm2'])} · {_fmt(c['inputs']['U'])} = "
                                    f"{_fmt(c['modes']['TR']['area_mm2'])} mm² (D3, Ec. D3-1)"},
              {"kind": "h2", "text": "Disposiciones aplicadas"},
              {"kind": "p", "text": ", ".join(c["provisions"])},
              {"kind": "h2", "text": "Estados límite (D2)"}]
    rows = []
    for name, m in c["modes"].items():
        rows.append([name, LIMIT_STATES.get(m["limit_state"], m["limit_state"]), f"{m['provision']}, Ec. {m['Pn_equation']}",
                     f"{'Fy' if name == 'TY' else 'Fu'}{'(T)' if c.get('fire') else ''} = {_fmt(m['stress_mpa'])}", f"{m['area_basis']} = {_fmt(m['area_mm2'])}",
                     m["Pn_kN"], f"{m['phi_t']:.2f}", m["available_kN"]])
    blocks.append({"kind": "table", "headers": ["Modo", "Estado límite", "Literal", "Esfuerzo resistente (MPa)", "Área resistente (mm²)",
                                                "Resistencia nominal, Pn (kN)", "Factor de resistencia, φt", "Resistencia de diseño, φt·Pn (kN)"],
                   "rows": rows, "highlight": list(c["modes"]).index(c["governing_mode"])})
    blocks.append({"kind": "p", "text": "Cada estado límite tiene su propio factor (D2), por lo que gobierna la menor "
                                        "resistencia de diseño φt·Pn, no la menor Pn."})
    gov = c["modes"][c["governing_mode"]]
    blocks += [{"kind": "h2", "text": "Resistencia"},
               {"kind": "kv", "items": [
                   ("Modo gobernante", f"{c['governing_mode']} — {LIMIT_STATES.get(gov['limit_state'], gov['limit_state'])}"),
                   ("Resistencia de diseño (D2)", f"min(φt·Pn) = {_fmt(c['available_kN'])} kN ({c['governing_mode']})"),
                   _verification(check)]}]
    return blocks


def _compression_blocks(case: SteelCase, check, c: dict) -> list[dict]:
    blocks = [{"kind": "h2", "text": "Clasificación de elementos (B4.1a)"}]
    rows = [[_ELEMENTS.get(r["element"], r["element"]), r["b4_case"], r["ratio"], r["lambda_r"],
             "esbelto" if r["slender"] else "no esbelto"] for r in c["classification"]["elements"]]
    if rows:
        blocks.append({"kind": "table", "headers": ["Elemento", "Caso de la Tabla B4.1a", "Relación ancho-espesor (λ = b/t)",
                                                    "Límite de elemento no esbelto (λr)", "Clase"], "rows": rows})
    else:
        blocks.append({"kind": "p", "text": c["classification"]["reference"]})
    blocks.append({"kind": "p", "text": f"Sección {'con' if c['classification']['slender'] else 'sin'} "
                                        "elementos esbeltos."})
    blocks.append({"kind": "h2", "text": "Disposiciones aplicadas"})
    blocks.append({"kind": "p", "text": ", ".join(c["provisions"])})
    blocks.append({"kind": "h2", "text": "Estados límite"})
    blocks.append({"kind": "table",
                   "headers": ["Modo", "Literal", "Ec. de Fe", "Esfuerzo de pandeo elástico, Fe (MPa)", "Ec. de Fn",
                               "Esfuerzo nominal, Fn (MPa)", "Área resistente (mm²)", "Resistencia nominal, Pn (kN)"],
                   "rows": [[f"{name}: {MODE_NAMES.get(name, name)}", m["provision"], m["Fe_equation"], m["Fe_mpa"], m["Fn_equation"], m["Fn_mpa"],
                             f"{m['area_basis']} = {_fmt(m['area_mm2'])}", m["Pn_kN"]]
                            for name, m in c["modes"].items()],
                   "highlight": list(c["modes"]).index(c["governing_mode"])})
    for name, m in c["modes"].items():
        blocks.append({"kind": "h3", "text": f"Modo {name}: {LIMIT_STATES.get(m['limit_state'], m['limit_state'])} "
                                             f"({m['provision']}, eje {m['axis']})"})
        table = _parameters(m, _MODE_KEYS - {"Fy_over_Fe"})
        table["rows"].append([f"Resistencia nominal (Pn = Fn · {m['area_basis']})", m["Pn_kN"], "kN", _literal("Pn_kN", m)])
        blocks.append(table)
        if m.get("e7_exempt"):
            blocks.append({"kind": "note", "text": m["e7_exempt"]})
        area = m.get("effective_area") or {}
        if area.get("plates"):
            blocks.append({"kind": "table",
                           "headers": ["Elemento", "n", "b (mm)", "t (mm)", "Ec.", "be (mm)", "(b − be)·t (mm²)"],
                           "rows": [[_ELEMENTS.get(p["element"], p["element"]), p["count"], p["b_mm"], p["t_mm"],
                                     p["equation"], p["be_mm"], p["area_loss_mm2"]] for p in area["plates"]]})
            blocks.append({"kind": "p", "text": f"Ae = Ag − Σ n·(b − be)·t = {_fmt(area['Ae_mm2'])} mm² (E7-1)"})
        elif area.get("equation") in {"E7-6", "E7-7"}:
            blocks.append({"kind": "p", "text": f"Ae = {_fmt(area['Ae_mm2'])} mm² ({area['equation']}; valor de "
                                                f"la ecuación {_fmt(area['Ae_equation_mm2'])}, limitado a Ag: "
                                                f"{_fmt(area['bounded_to_Ag'])})"})
    gov = c["modes"][c["governing_mode"]]
    items = [("Modo gobernante", f"{c['governing_mode']} — {LIMIT_STATES.get(gov['limit_state'], gov['limit_state'])}"),
             ("Resistencia nominal (Pn)", f"{_fmt(c['Pn_kN'])} kN ({gov['provision']}, Ec. {c['governing_equation']})"),
             ("Resistencia de diseño (E1)", f"φc·Pn = 0.90 · Pn = {_fmt(c['available_kN'])} kN"),
             _verification(check)]
    for req in c["requirements"]:
        items.append((f"Requisito {req['id']} (E6.2)", f"a/ri = {_fmt(req['a_over_ri'])} ≤ {_fmt(req['limit'])} → "
                                                f"{'cumple' if req['satisfied'] else 'NO cumple'}"))
    blocks += [{"kind": "h2", "text": "Resistencia"}, {"kind": "kv", "items": items}]
    return blocks


_FLEXURE_KEYS = {"limit_state", "provision", "applies", "reason", "Mn", "Mn_kNm", "design_kNm", "equation"}


def _flexure_blocks(case: SteelCase, check, c: dict) -> list[dict]:
    blocks = [{"kind": "h2", "text": "Clasificación de elementos (B4.1b)"}]
    rows = [[_ELEMENTS.get(r["element"], r["element"]), r["b4_case"], r["ratio"], r["lambda_p"], r["lambda_r"], r["class"]]
            for r in c["classification"]["elements"]]
    if rows:
        blocks.append({"kind": "table", "headers": ["Elemento", "Caso de la Tabla B4.1b", "Relación ancho-espesor (λ)", "Límite compacto (λp)",
                                                    "Límite no compacto (λr)", "Clase"], "rows": rows})
    else:
        blocks.append({"kind": "p", "text": "Barra maciza: sin elementos esbeltos (F11)."})
    blocks += [{"kind": "h2", "text": "Disposiciones aplicadas"}, {"kind": "p", "text": ", ".join(c["provisions"])},
               {"kind": "h2", "text": "Estados límite"}]
    names = list(c["modes"])
    blocks.append({"kind": "table", "headers": ["Estado límite", "Literal", "Ec.", "Resistencia nominal, Mn (kN·m)", "Resistencia de diseño, φb·Mn (kN·m)"],
                   "rows": [[f"{k} — {FLEXURE_STATES.get(k, k)}", m["provision"],
                             m["equation"] if m["applies"] else "no aplica",
                             m["Mn_kNm"] if m["applies"] else "–", m["design_kNm"] if m["applies"] else "–"]
                            for k, m in c["modes"].items()],
                   "highlight": names.index(c["governing_mode"])})
    for name, m in c["modes"].items():
        table = _parameters(m, _FLEXURE_KEYS)
        if m["applies"] or table["rows"]:
            blocks.append({"kind": "h3", "text": f"{name}: {FLEXURE_STATES.get(name, name)} ({m['provision']})"})
            if not m["applies"]:
                blocks.append({"kind": "note", "text": m["reason"]})
            if m["applies"]:
                table["rows"].append(["Resistencia nominal a flexión (Mn)", m["Mn_kNm"], "kN·m", f"{m['provision']}, Ec. {m['equation']}"])
            if table["rows"]:
                blocks.append(table)
        else:
            blocks.append({"kind": "note", "text": f"{name}: {m['reason']} ({m['provision']})"})
    gov = c["modes"][c["governing_mode"]]
    blocks += [{"kind": "h2", "text": "Resistencia"}, {"kind": "kv", "items": [
        ("Estado límite gobernante", f"{c['governing_mode']} — {FLEXURE_STATES.get(c['governing_mode'], '')} "
                                     f"({gov['provision']}, Ec. {gov['equation']})"),
        ("Resistencia nominal a flexión (Mn)", f"{_fmt(c['Mn_kNm'])} kN·m"),
        ("Resistencia de diseño (F1)", f"φb·Mn = 0.90 · Mn = {_fmt(c['available_kNm'])} kN·m"),
        _verification(check)]}]
    return blocks


_SHEAR_KEYS = {"limit_state", "provision", "applies", "Vn", "Vn_kN", "phi_v", "available_kN", "equation"}


def _shear_blocks(case: SteelCase, check, c: dict) -> list[dict]:
    blocks = [{"kind": "h2", "text": "Disposiciones aplicadas"}, {"kind": "p", "text": ", ".join(c["provisions"])}]
    rows = [[_ELEMENTS.get(r["element"], r["element"]), r["ratio"], "–" if r["kv"] is None else r["kv"], r["limit"],
             r["Cv"], f"G2, Ec. {r['Cv_equation']}"] for r in c["classification"]["elements"]]
    if rows:
        blocks += [{"kind": "h2", "text": "Coeficiente de cortante"},
                   {"kind": "table", "headers": ["Elemento", "Relación ancho-espesor (h/t)", "Coeficiente de pandeo por cortante (kv)",
                                                 "Límite de la relación h/t", "Coeficiente de cortante (Cv)", "Literal"], "rows": rows}]
    m = c["modes"]["V"]
    table = _parameters(m, _SHEAR_KEYS)
    items = [("Resistencia nominal a cortante (Vn)", f"{_fmt(m['Vn_kN'])} kN ({m['provision']}, Ec. {m['equation']})"),
             (f"Resistencia de diseño ({m['provision']})", f"φv·Vn = {m['phi_v']:.2f} · Vn = {_fmt(c['available_kN'])} kN"),
             _verification(check)]
    blocks += [{"kind": "h2", "text": "Resistencia"}, table, {"kind": "kv", "items": items}]
    return blocks


_COMPOSITE_KEYS = {"limit_state", "provision", "applies", "equation"}


def _composite_blocks(check, c: dict) -> list[dict]:
    blocks = [{"kind": "h2", "text": "Disposiciones aplicadas"}, {"kind": "p", "text": ", ".join(c["provisions"])}]
    rows = [[_ELEMENTS.get(r["element"], r["element"]), r["ratio"], r["lambda_p"], r["lambda_r"], r["class"]]
            for r in c["classification"]["elements"]]
    if rows:
        blocks += [{"kind": "h2", "text": f"Clasificación ({c['classification']['reference']})"},
                   {"kind": "table", "headers": ["Elemento", "Relación ancho-espesor (λ)", "Límite compacto (λp)", "Límite no compacto (λr)", "Clase"], "rows": rows}]
    m = c["modes"][c["governing_mode"]]
    blocks += [{"kind": "h2", "text": f"Resistencia: modo {c['governing_mode']}"}, _parameters(m, _COMPOSITE_KEYS)]
    if "A2-otro" in c["modes"]:
        blocks += [{"kind": "h2", "text": "Revisión con cp y cm del otro eje (no gobierna)"}, _parameters(c["modes"]["A2-otro"], _COMPOSITE_KEYS)]
    if check.ratio is not None:
        blocks.append({"kind": "kv", "items": [("Verificación", f"{_fmt(check.demand)} / {_fmt(check.capacity)} = {_fmt(check.ratio)}")]})
    if c["requirements"]:
        blocks += [{"kind": "h2", "text": "Limitaciones del Capítulo I"},
                   {"kind": "table", "headers": ["Requisito", "Disposición", "Cumple"],
                    "rows": [[r["message"], r["provision"], "sí" if r["satisfied"] else "NO"] for r in c["requirements"]]}]
    return blocks


def _h2_blocks(c: dict) -> list[dict]:
    rows = [[f"{m['point']} ({m['location']})", m["Pr_Pc"], m["Mrw_Mcw"], m["Mrz_Mcz"], m["ratio"]]
            for m in c["modes"].values()]
    m = c["modes"][c["governing_mode"]]
    return [{"kind": "h2", "text": "Ecuación H2-1 en los puntos del ángulo"},
            {"kind": "table", "headers": ["Punto", "Pr/Pc", "Mrw/Mcw", "Mrz/Mcz", "|Suma|"], "rows": rows,
             "highlight": list(c["modes"]).index(c["governing_mode"])},
            {"kind": "kv", "items": [
                ("Fuerza axial requerida y de diseño (Pr, Pc)", f"{_fmt(m['Pr_kN'])} kN; {_fmt(m['Pc_kN']) if m['Pc_kN'] else '–'} kN ({m['axial']})"),
                ("Momento en w requerido y de diseño (Mrw, Mcw)", f"{_fmt(m['Mrw_kNm'])}; {_fmt(m['Mcw_kNm']) if m['Mcw_kNm'] else '–'} kN·m"),
                ("Momento en z requerido y de diseño (Mrz, Mcz)", f"{_fmt(m['Mrz_kNm'])}; {_fmt(m['Mcz_kNm']) if m['Mcz_kNm'] else '–'} kN·m"),
                ("Criterio (H2)", "Términos con el signo de su tensión: compresión positiva, tracción negativa"),
                ("Verificación", f"{c['governing_mode']}: {_fmt(c['ratio'])} ≤ 1.0 → "
                                 f"{'cumple' if c['ratio'] <= 1.0 else 'NO cumple'}")]}]


def _interaction_blocks(case: SteelCase, check, c: dict) -> list[dict]:
    blocks = [{"kind": "h2", "text": "Disposiciones aplicadas"}, {"kind": "p", "text": ", ".join(c["provisions"])}]
    if "H1" not in c["modes"]:
        return blocks + _h2_blocks(c)
    rows = []
    for name, m in c["modes"].items():
        if name == "H1":
            terms = f"Pr/Pc = {_fmt(m['Pr_Pc'])}; Mrx/Mcx = {_fmt(m['Mrx_Mcx'])}; Mry/Mcy = {_fmt(m['Mry_Mcy'])}"
        else:
            terms = f"Pr/Pc = {_fmt(m['Pr_Pc'])}; Mrx/Mcx = {_fmt(m['Mrx_Mcx'])} ({m['Mcx_basis']})"
        rows.append([name, m["provision"], m["equation"], terms, m["ratio"]])
    blocks += [{"kind": "h2", "text": "Ecuaciones de interacción"},
               {"kind": "table", "headers": ["Comprobación", "Literal", "Ec.", "Términos", "Valor de la interacción"], "rows": rows,
                "highlight": list(c["modes"]).index(c["governing_mode"])}]
    h1 = c["modes"]["H1"]
    blocks.append({"kind": "kv", "items": [
        ("Fuerza axial requerida y de diseño (Pr, Pc)", f"{_fmt(h1['Pr_kN'])} kN; {_fmt(h1['Pc_kN']) if h1['Pc_kN'] else '–'} kN ({h1['axial']})"),
        ("Momento en x requerido y de diseño (Mrx, Mcx)", f"{_fmt(h1['Mrx_kNm'])}; {_fmt(h1['Mcx_kNm']) if h1['Mcx_kNm'] else '–'} kN·m"),
        ("Momento en y requerido y de diseño (Mry, Mcy)", f"{_fmt(h1['Mry_kNm'])}; {_fmt(h1['Mcy_kNm']) if h1['Mcy_kNm'] else '–'} kN·m"),
        ("Criterio (H1.1)", "Ec. H1-1a si Pr/Pc ≥ 0.2; si no, Ec. H1-1b"),
        ("Verificación", f"{c['governing_mode']}: {_fmt(c['ratio'])} ≤ 1.0 → "
                         f"{'cumple' if c['ratio'] <= 1.0 else 'NO cumple'}")]})
    return blocks


# --- plain text ----------------------------------------------------------------------------

def _text_table(headers, rows) -> list[str]:
    cells = [[str(h) for h in headers]] + [[_fmt(v) for v in row] for row in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(headers))]
    line = lambda row: "  ".join(c.ljust(w) for c, w in zip(row, widths)).rstrip()  # noqa: E731
    return [line(cells[0]), "  ".join("-" * w for w in widths)] + [line(r) for r in cells[1:]]


def render_text(blocks: list[dict]) -> str:
    out = []
    for b in blocks:
        kind = b["kind"]
        if kind == "title":
            out.append(f"# Memoria de cálculo — {b['action']} {b['member']}"
                       + (f" · {b['case']}" if b.get("case") else ""))
            out += [f"{k}: {v}" for k, v in b["meta"]]
            out += ["", f"RESULTADO: {b['status']} ({STATUS_TEXT[b['status']]})"
                    + (f"   Demanda/capacidad máx. = {_fmt(b['ratio'])}" if b["ratio"] is not None else "")]
        elif kind == "summary":
            out.append("  |  ".join(f"{title} {', '.join(lines)}" for title, lines in b["items"]))
        elif kind == "h1":
            out += ["", f"## {b['text']}"]
        elif kind == "h2":
            out += ["", f"### {b['text']}"]
        elif kind == "h3":
            out += ["", f"#### {b['text']}"]
        elif kind == "kv":
            out += [("  " if b.get("compact") else "") + f"{k}: {v}" for k, v in b["items"]]
        elif kind == "table":
            out += _text_table(b["headers"], b["rows"])
        elif kind == "p":
            out.append(b["text"])
        elif kind == "note":
            out.append(f"- {b['text']}")
        elif kind == "alert":
            out.append(f"! {b['text']}" + (f"\n  Detalle: {b['detail']}" if b.get("detail") else ""))
    return "\n".join(out) + "\n"


def calculation_report(case: SteelCase, result: DesignResult, *, title: str | None = None) -> str:
    """Plain-text calculation report of one member."""
    return render_text(report_blocks([(title, case, result)]))


# --- PDF ---------------------------------------------------------------------------------------

_INK, _MUTED, _RULE, _NAVY = (31, 41, 55), (107, 114, 128), (209, 213, 219), (23, 50, 84)
_HEAD_FILL, _ZEBRA, _CARD, _HIGHLIGHT = (234, 239, 245), (248, 250, 252), (243, 246, 250), (255, 248, 225)
_STATUS_COLOR = {"PASS": (46, 125, 50), "FAIL": (183, 28, 28), "INCOMPLETE": (178, 106, 0)}
_FONT_CANDIDATES = [  # (regular, bold); first pair found on this machine is embedded
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
]
_LATIN1 = {"φ": "phi", "λ": "lambda", "Σ": "sum", "≤": "<=", "→": "->", "—": "-", "–": "-",
           "−": "-", "²": "2", "⁴": "4", "⁶": "6", "r̄o": "ro", "α": "alpha"}


def _column_widths(minimums: list[float], weights: list[float], total: float) -> list[float]:
    """Column widths (mm): each one holds its longest word; what remains is shared by weight. A word breaks only if they exceed the total."""
    spare = total - sum(minimums)
    if spare <= 0:
        return [total * m / sum(minimums) for m in minimums]
    return [m + spare * w / sum(weights) for m, w in zip(minimums, weights)]


def pdf_bytes(documents: list[list[dict]]) -> bytes:
    """PDF in memory from report_blocks() documents (one page sequence each). Requires fpdf2 ([pdf] extra)."""
    try:
        from fpdf import FPDF
        from fpdf.fonts import FontFace
    except ImportError as exc:
        raise RuntimeError('PDF output requires fpdf2: pip install -e ".[pdf]"') from exc
    import logging
    logging.getLogger("fontTools").setLevel(logging.ERROR)  # font subsetting chatter

    class Report(FPDF):
        member = ""

        def header(self):
            if self.page_no() == 1 or self.member is None:
                return
            self.set_font(FONT, "", 7.5)
            self.set_text_color(*_MUTED)
            self.cell(0, 5, clean(f"Memoria de cálculo — {self.member}"), new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(*_RULE)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(4)

        def footer(self):
            self.set_y(-12)
            self.set_draw_color(*_RULE)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.set_font(FONT, "", 7.5)
            self.set_text_color(*_MUTED)
            self.cell(0, 6, clean("StructureLab_HFS · ANSI/AISC 360-22"))
            self.cell(0, 6, f"{self.page_no()} / {{nb}}", align="R")

    pdf = Report(format="A4")
    pdf.set_margins(18, 16, 18)
    pdf.set_auto_page_break(True, margin=18)
    FONT = "Helvetica"
    unicode_font = next(((r, b) for r, b in _FONT_CANDIDATES if Path(r).is_file() and Path(b).is_file()), None)
    if unicode_font:
        pdf.add_font("Body", "", unicode_font[0])
        pdf.add_font("Body", "B", unicode_font[1])
        FONT = "Body"

    def clean(text: str) -> str:
        if unicode_font:
            return text
        for k, v in _LATIN1.items():
            text = text.replace(k, v)
        return text.encode("latin-1", "replace").decode("latin-1")

    width = lambda: pdf.w - pdf.l_margin - pdf.r_margin  # noqa: E731

    def heading(text, size, space):
        if pdf.get_y() > pdf.h - (85 if size >= 11 else 60):   # keep a heading with its first lines; a chapter also with its subheading
            pdf.add_page()
        pdf.ln(space)
        pdf.set_font(FONT, "B", size)
        pdf.set_text_color(*(_NAVY if size >= 9.5 else _INK))
        pdf.multi_cell(0, size * 0.5, clean(text), new_x="LMARGIN", new_y="NEXT")
        if size >= 11:
            pdf.set_draw_color(*_NAVY)
            pdf.set_line_width(0.4)
            pdf.line(pdf.l_margin, pdf.get_y() + 0.8, pdf.l_margin + 14, pdf.get_y() + 0.8)
            pdf.set_line_width(0.2)
            pdf.ln(3)
        else:
            pdf.ln(1)

    def chart(b):
        """P-M diagram: thin lines, one axis, legend for the two series, direct labels on the nominal points only."""
        w, h = 120.0, 70.0
        if pdf.get_y() + h + 22 > pdf.h - pdf.b_margin:
            pdf.add_page()
        x0, y0 = pdf.l_margin + 16, pdf.get_y() + 12
        all_points = [q for series in b["series"] for q in series["points"]]
        demand = b.get("demand")
        top_x, step_x = _axis_scale(max([q[0] for q in all_points] + ([demand[0]] if demand else [])))
        top_y, step_y = _axis_scale(max([q[1] for q in all_points] + ([demand[1]] if demand else [])))
        to_xy = lambda m, p: (x0 + m / top_x * w, y0 + h - p / top_y * h)  # noqa: E731
        pdf.set_font(FONT, "B", 8)
        pdf.set_text_color(*_INK)
        pdf.set_xy(pdf.l_margin, y0 - 11)
        pdf.cell(w + 16, 4, clean(b["title"]))
        pdf.set_font(FONT, "", 7)
        pdf.set_text_color(*_MUTED)
        pdf.set_draw_color(*_RULE)
        pdf.set_line_width(0.1)
        for i in range(round(top_y / step_y) + 1):
            gy = y0 + h - i * step_y / top_y * h
            pdf.line(x0, gy, x0 + w, gy)
            pdf.set_xy(x0 - 15, gy - 2)
            pdf.cell(14, 4, f"{i * step_y:g}", align="R")
        for i in range(round(top_x / step_x) + 1):
            gx = x0 + i * step_x / top_x * w
            pdf.set_xy(gx - 10, y0 + h + 0.5)
            pdf.cell(20, 4, f"{i * step_x:g}", align="C")
        pdf.set_xy(x0, y0 + h + 4.5)
        pdf.cell(w, 4, clean(b["x_label"]), align="C")
        pdf.set_xy(pdf.l_margin, y0 - 7)
        pdf.cell(30, 3, clean(b["y_label"]))
        pdf.set_draw_color(*_MUTED)
        pdf.line(x0, y0, x0, y0 + h)
        pdf.line(x0, y0 + h, x0 + w, y0 + h)
        colors = {True: (42, 120, 214), False: (235, 104, 52)}             # first two hues of the validated palette
        for series in b["series"]:
            color = colors[series["dash"]]
            pdf.set_draw_color(*color)
            pdf.set_fill_color(*color)
            pdf.set_line_width(0.5)
            if series["dash"]:
                pdf.set_dash_pattern(dash=1.6, gap=1.0)
            line = [to_xy(q[0], q[1]) for q in series["points"]]
            for a, c in zip(line, line[1:]):
                pdf.line(a[0], a[1], c[0], c[1])
            pdf.set_dash_pattern()
            pdf.set_font(FONT, "", 7.5)
            pdf.set_text_color(*_INK)
            for (x, y), q in zip(line, series["points"]):
                pdf.ellipse(x - 0.8, y - 0.8, 1.6, 1.6, style="F")
                if q[2]:
                    pdf.set_xy(x + 0.8, y - 4.2)
                    pdf.cell(4, 3.5, q[2])
        legend_y = y0 + h + 9
        cursor = x0
        pdf.set_font(FONT, "", 7.5)
        pdf.set_text_color(*_INK)
        for series in b["series"]:
            pdf.set_draw_color(*colors[series["dash"]])
            pdf.set_line_width(0.5)
            if series["dash"]:
                pdf.set_dash_pattern(dash=1.6, gap=1.0)
            pdf.line(cursor, legend_y + 2, cursor + 7, legend_y + 2)
            pdf.set_dash_pattern()
            pdf.set_xy(cursor + 8, legend_y)
            label = clean(series["name"])
            pdf.cell(pdf.get_string_width(label) + 1, 4, label)
            cursor += pdf.get_string_width(label) + 13
        if demand:
            mx, my = to_xy(demand[0], demand[1])
            pdf.set_fill_color(*_INK)
            pdf.set_draw_color(255, 255, 255)
            pdf.set_line_width(0.3)
            pdf.ellipse(mx - 1.2, my - 1.2, 2.4, 2.4, style="DF")
            pdf.set_xy(mx + 1.4, my - 1.8)
            pdf.cell(16, 3.5, "(Mu, Pu)")
            pdf.ellipse(cursor, legend_y + 0.9, 2.2, 2.2, style="DF")
            pdf.set_xy(cursor + 3, legend_y)
            pdf.cell(25, 4, "Demanda (Mu, Pu)")
        pdf.set_line_width(0.2)
        pdf.set_draw_color(*_RULE)
        pdf.set_xy(pdf.l_margin, legend_y + 7)

    def table(headers, rows, highlight=None, compact=False, kv=False):
        texts = [[clean(_fmt(v)) for v in row] for row in rows]
        if len(rows) <= 12 and pdf.get_y() + (len(rows) + 1) * 6.5 > pdf.h - pdf.b_margin:
            pdf.add_page()
        # Wide enough for the longest word of the column, with a cap so that a long cell does not squeeze the others.
        cap = max(14, 150 // len(headers))
        weights = [max(8, max((len(w) for w in " ".join([str(h)] + [r[i] for r in texts]).split()), default=1),
                       min(max([len(str(h))] + [len(r[i]) for r in texts]), cap)) + 2 for i, h in enumerate(headers)]
        numeric = [all(isinstance(r[i], (int, float)) for r in rows) for i in range(len(headers))]
        pdf.set_font(FONT, "", 8.5 if not compact else 8)
        pdf.set_text_color(*_INK)
        pdf.set_draw_color(*_RULE)
        fill = _CARD if kv else _ZEBRA
        pdf.set_fill_color(*fill)  # never inherit a previous fill (status badge, cards)
        natural = sum(weights) * 2.1  # mm, about one character of 8.5 pt per weight unit
        pdf.set_font(FONT, "B", 8.5)  # headings and the highlighted row are bold, so the widest case
        minimums = [max(pdf.get_string_width(word) for word in " ".join([clean(str(h))] + [r[i] for r in texts]).split() or [""]) + 3.2 + 0.6
                    for i, h in enumerate(headers)]
        pdf.set_font(FONT, "", 8.5 if not compact else 8)
        total = min(width(), max(natural, 70, sum(minimums)))
        style = dict(width=total, col_widths=_column_widths(minimums, weights, total), line_height=5.2, padding=(1, 1.6),
                     text_align=["RIGHT" if n else "LEFT" for n in numeric], align="LEFT",
                     cell_fill_color=fill)
        if kv:
            style.update(width=width(), borders_layout="NONE", first_row_as_headings=False, col_widths=(28, 72),
                         cell_fill_mode="ALL")
        else:
            style.update(borders_layout="HORIZONTAL_LINES", cell_fill_mode="ROWS",
                         headings_style=FontFace(emphasis="BOLD", color=_NAVY, fill_color=_HEAD_FILL),
                         repeat_headings=1)
        with pdf.table(**style) as t:
            if not kv:
                head = t.row()
                for h in headers:
                    head.cell(clean(h))
            for i, row in enumerate(texts):
                r = t.row()
                for j, cell in enumerate(row):
                    if kv and j == 0:
                        r.cell(cell, style=FontFace(color=_MUTED))
                    elif i == highlight:
                        r.cell(cell, style=FontFace(emphasis="BOLD", fill_color=_HIGHLIGHT))
                    else:
                        r.cell(cell)
        pdf.ln(2)

    def keep_headings_with_table(blocks, index):
        """Headings go to the next page with the short table that they announce, which table() would move there alone."""
        needed, following = 0.0, index
        while following < len(blocks) and blocks[following]["kind"] in {"h1", "h2", "h3"}:
            needed += {"h1": 16.0, "h2": 10.0, "h3": 8.0}[blocks[following]["kind"]]
            following += 1
        short_table = following < len(blocks) and blocks[following]["kind"] == "table" and len(blocks[following]["rows"]) <= 12
        rows = (len(blocks[following]["rows"]) + 1) * 6.5 if short_table else 0.0
        if pdf.get_y() + needed + rows > pdf.h - pdf.b_margin or pdf.get_y() + needed > pdf.h - 60:
            pdf.add_page()

    for blocks in documents:
        pdf.member = None
        pdf.add_page()
        for index, b in enumerate(blocks):
            kind = b["kind"]
            if kind in {"h1", "h2", "h3"} and blocks[index - 1]["kind"] not in {"h1", "h2", "h3"}:
                keep_headings_with_table(blocks, index)
            if kind == "title":
                pdf.member = b["member"] + (f" · {b['case']}" if b.get("case") else "")
                pdf.set_fill_color(*_NAVY)
                pdf.rect(0, 0, pdf.w, 4, style="F")
                pdf.set_y(14)
                pdf.set_font(FONT, "", 9)
                pdf.set_text_color(*_MUTED)
                pdf.multi_cell(width() - 42, 4.2, clean(f"MEMORIA DE CÁLCULO · {b['action'].upper()}"), align="L", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font(FONT, "B", 18)
                pdf.set_text_color(*_NAVY)
                pdf.multi_cell(width() - 42, 9, clean(b["member"]), new_x="LMARGIN", new_y="NEXT")
                if b.get("case"):
                    pdf.set_font(FONT, "", 10.5)
                    pdf.set_text_color(*_INK)
                    pdf.multi_cell(width() - 42, 5.5, clean(b["case"]), new_x="LMARGIN", new_y="NEXT")
                    pdf.ln(1.5)
                title_bottom = pdf.get_y()                           # the status badge below moves the cursor
                color = _STATUS_COLOR[b["status"]]
                pdf.set_fill_color(*color)
                pdf.rect(pdf.w - pdf.r_margin - 38, 19, 38, 10, style="F", round_corners=True, corner_radius=2)
                pdf.set_xy(pdf.w - pdf.r_margin - 38, 19)
                pdf.set_font(FONT, "B", 10)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(38, 10, clean(STATUS_TEXT[b["status"]]), align="C")
                pdf.set_xy(pdf.l_margin, max(title_bottom, 31) + 2)
                pdf.set_font(FONT, "", 8.5)
                pdf.set_text_color(*_MUTED)
                for key, value in b["meta"]:
                    pdf.multi_cell(0, 4.5, clean(f"{key}: {value}"), align="L", new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(*_RULE)
                pdf.line(pdf.l_margin, pdf.get_y() + 2, pdf.w - pdf.r_margin, pdf.get_y() + 2)
                pdf.ln(6)
            elif kind == "summary":
                gap, n = 3, min(len(b["items"]), 3)                  # at most three cards per row
                card_w, y = (width() - gap * (n - 1)) / n, pdf.get_y()
                pdf.set_font(FONT, "", 7.5)
                labels = [pdf.multi_cell(card_w - 6, 3.4, clean(label), dry_run=True, output="LINES") for label, _ in b["items"]]
                for start in range(0, len(b["items"]), n):           # each row as tall as its longest label
                    label_h = 3.4 * max(len(lines) for lines in labels[start:start + n])
                    height = label_h + 5.0 + 5.0 * max(len(values) for _, values in b["items"][start:start + n])
                    for i, (_, values) in enumerate(b["items"][start:start + n]):
                        x = pdf.l_margin + i * (card_w + gap)
                        pdf.set_fill_color(*_CARD)
                        pdf.rect(x, y, card_w, height, style="F", round_corners=True, corner_radius=1.5)
                        pdf.set_font(FONT, "", 7.5)
                        pdf.set_text_color(*_MUTED)
                        for row, line in enumerate(labels[start + i]):
                            pdf.set_xy(x + 3, y + 2 + row * 3.4)
                            pdf.cell(card_w - 6, 3.4, line)
                        size = 10.5
                        pdf.set_font(FONT, "B", size)
                        while max(pdf.get_string_width(clean(value)) for value in values) > card_w - 6 and size > 6:
                            size -= 0.5
                            pdf.set_font(FONT, "B", size)
                        pdf.set_text_color(*_INK)
                        for row, value in enumerate(values):
                            pdf.set_xy(x + 3, y + 3 + label_h + row * 5.0)
                            pdf.cell(card_w - 6, 5.0, clean(value))
                    y += height + 3
                pdf.set_xy(pdf.l_margin, y + 1)
            elif kind == "h1":
                heading(b["text"], 12, 4)
            elif kind == "h2":
                heading(b["text"], 10, 2.5)
            elif kind == "h3":
                heading(b["text"], 8.8, 1.5)
            elif kind == "kv":
                table(["", ""], [list(item) for item in b["items"]], kv=True, compact=b.get("compact", False))
            elif kind == "table":
                table(b["headers"], b["rows"], highlight=b.get("highlight"))
            elif kind in {"p", "note"}:
                pdf.set_font(FONT, "", 8.5 if kind == "p" else 8)
                pdf.set_text_color(*(_INK if kind == "p" else _MUTED))
                text = clean(("•  " if kind == "note" else "") + b["text"])
                pdf.multi_cell(0, 4.6, text, align="L", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)
            elif kind == "chart":
                chart(b)
            elif kind == "alert":
                pdf.set_fill_color(255, 243, 224)
                pdf.set_draw_color(*_STATUS_COLOR["INCOMPLETE"])
                pdf.set_font(FONT, "B", 8.5)
                pdf.set_text_color(*_INK)
                text = b["text"] + (f"\nDetalle: {b['detail']}" if b.get("detail") else "")
                pdf.multi_cell(0, 4.8, clean(text), border="L", fill=True, padding=2.5, align="L",
                               new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
    return bytes(pdf.output())
