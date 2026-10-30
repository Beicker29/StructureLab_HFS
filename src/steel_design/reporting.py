"""Calculation report (memoria de cálculo) from a DesignResult: plain text and PDF.

Presentation only: every value comes from the engine result; nothing is recomputed.
report_blocks() builds one neutral document model (title, summary, headings,
key-value lists, tables, notes); render_text() and pdf_bytes() draw that same model.
"""
from datetime import datetime, timezone
from pathlib import Path

from .models import DesignResult, SteelCase

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
                  "H": "–", "tan_alpha": "–"}
_SECTION_NAMES = {"area": "Ag", "ix": "Ix", "iy": "Iy", "iw": "Iw", "iz": "Iz", "j": "J", "cw": "Cw", "ro": "r̄o",
                  "tan_alpha": "tan α", "od": "D", "bf_2tf_ratio": "bf/2tf", "b_t_ratio": "b/t",
                  "b_tdes_ratio": "b/tdes", "h_tw_ratio": "h/tw", "h_tdes_ratio": "h/tdes", "d_t_ratio": "D/t"}
_ELEMENTS = {"flange": "ala", "web": "alma", "wall_b": "pared b", "wall_h": "pared h", "wall": "pared",
             "long_leg": "ala larga", "short_leg": "ala corta"}
_LABELS = {"Lc_over_r_o": "(Lc/r)o", "a_over_ri": "a/ri", "slenderness_equation": "Ec. de esbeltez",
           "Fez_equation": "Ec. Fez", "Fe_torsion_equation": "Ec. Fe torsional", "symmetry_axis": "Eje de simetría",
           "connected_leg": "Ala conectada", "leg_ratio": "bl/bs", "ro_mm": "r̄o (mm)",
           "ro_from_geometry_mm": "r̄o geométrico (mm)", "ro2_mm2": "r̄o² (mm²)", "H": "H", "Ki": "Ki"}
_UNIT_SUFFIX = {"_mm2": " (mm²)", "_mm4": " (mm⁴)", "_mm6": " (mm⁶)", "_mm": " (mm)", "_mpa": " (MPa)"}


def _label(key: str) -> str:
    """Engineering notation for a result key: Lc_over_r -> Lc/r, Fez_mpa -> Fez (MPa)."""
    if key in _LABELS:
        return _LABELS[key]
    unit = next((u for suffix, u in _UNIT_SUFFIX.items() if key.endswith(suffix)), "")
    if unit:
        key = key[: key.rindex("_")]
    return key.replace("_over_", "/").replace("_", " ") + unit


def _fmt(value) -> str:
    if isinstance(value, bool):
        return "sí" if value else "no"
    if isinstance(value, int) or not isinstance(value, float):
        return str(value)
    if value != 0 and (abs(value) >= 1e7 or abs(value) < 1e-3):
        return f"{value:.4e}"
    return f"{value:.3f}"


# --- document model ------------------------------------------------------------------------

CHECK_TITLES = {"axial": None, "flexure_x": "Flexión respecto de x", "flexure_y": "Flexión respecto de y"}
FLEXURE_STATES = {"Y": "fluencia (momento plástico)", "LTB": "pandeo lateral-torsional", "FLB": "pandeo local del ala",
                  "WLB": "pandeo local del alma", "LB": "pandeo local", "TFR": "rotura del ala traccionada"}


def _check_title(check) -> str:
    if check.id == "axial":
        return "Compresión (Capítulo E)" if check.chapter == "E" else "Tracción (Capítulo D)"
    return f"{CHECK_TITLES[check.id]} (Capítulo F)"


def _capacity_label(check) -> str:
    return {"E": "φc·Pn", "D": "φt·Pn", "F": "φb·Mn"}[check.chapter]


def report_blocks(case: SteelCase, result: DesignResult, *, title: str | None = None) -> list[dict]:
    """Neutral document model of the report of one member and one load combination (Spanish)."""
    chapters = sorted({c.chapter for c in result.checks})
    action = " + ".join(_check_title(c).split(" (")[0].lower() for c in result.checks)
    blocks = [{"kind": "title", "member": result.section, "case": title, "status": result.status.value,
               "action": action,
               "meta": [("Norma", f"ANSI/AISC 360-22, Capítulo{'s' if len(chapters) > 1 else ''} {', '.join(chapters)}"),
                        ("Método", "LRFD"), ("Fecha", f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC"),
                        ("Programa", "StructureLab_HFS")],
               "ratio": result.ratio}]
    cards = []
    for c in result.checks:
        value = (f"{_fmt(c.capacity)} {c.unit} · {c.ratio:.3f}" if c.capacity is not None else "no calculada")
        cards.append((f"{_check_title(c).split(' (')[0]}: {_capacity_label(c)} · Pu/cap.".replace(
            "Pu/cap.", "Mu/cap." if c.chapter == "F" else "Pu/cap."), value))
    if cards:
        blocks.append({"kind": "summary", "items": cards[:4]})
    blocks += _data_blocks(case, result)
    notes, limitations = [], []
    for number, check in enumerate(result.checks, start=2):
        blocks.append({"kind": "h1", "text": f"{number}. {_check_title(check)}"})
        r = check.result
        if r is None:
            for error in check.errors:
                blocks.append({"kind": "alert", "text": f"{error.get('code')}: {error.get('message')}",
                               "detail": str(error["details"]) if error.get("details") else None})
            blocks.append({"kind": "p", "text": "Comprobación INCOMPLETA: no se informa ninguna resistencia supuesta."})
            continue
        if check.chapter == "E":
            blocks += _compression_blocks(case, check, r)
        elif check.chapter == "D":
            blocks += _tension_blocks(case, check, r)
        else:
            blocks += _flexure_blocks(case, check, r)
        blocks.append({"kind": "h2", "text": f"Obligaciones del Capítulo {check.chapter} (comprobación independiente)"})
        blocks.append({"kind": "table", "headers": ["Obligación", "Disposición", "Atendida por"],
                       "rows": [[o.id, o.provision, o.satisfied_by or "NO ATENDIDA"] for o in check.obligations]})
        for error in check.errors:
            blocks.append({"kind": "alert", "text": f"{error.get('code')}: {error.get('id', '')} "
                                                    f"{error.get('message', '')}".strip(), "detail": None})
        notes += [n for n in r["notes"] if n not in notes]
        limitations += [x for x in r["limitations"] if x not in limitations]
    final = len(result.checks) + 2
    if result.interaction_pending:
        blocks.append({"kind": "h1", "text": f"{final}. Interacción"})
        blocks.append({"kind": "alert", "text": "La combinación tiene más de una demanda. La interacción del Capítulo H "
                                                "aún no está implementada: el estado no puede ser CUMPLE.", "detail": None})
        final += 1
    blocks.append({"kind": "h1", "text": f"{final}. Notas y limitaciones"})
    for text in notes + limitations + [result.scope]:
        blocks.append({"kind": "note", "text": text})
    return blocks


def _data_blocks(case: SteelCase, result: DesignResult) -> list[dict]:
    blocks = [{"kind": "h1", "text": "1. Datos"}]
    source = result.section_data.get("source") or {}
    origin = (f"catálogo {source.get('sheet')} fila {source.get('row')} (sha256 {source.get('sha256', '')[:12]})"
              if source else "sección definida en la entrada")
    f, ln, mat = case.factors, case.lengths, case.material
    material = f"Fy = {_fmt(mat.Fy)} MPa" + (f"; Fu = {_fmt(mat.Fu)} MPa" if mat.Fu else "") + f"; E = {_fmt(mat.E)} MPa"
    demands = [f"Pu = {_fmt(case.Pu)} kN ({'compresión' if case.Pu > 0 else 'tracción'})"] if case.Pu else []
    demands += [f"Mu{a} = {_fmt(m)} kN·m" for a, m in (("x", case.Mux), ("y", case.Muy)) if m]
    items = [("Perfil", f"{result.section} ({result.family})"), ("Origen", origin), ("Material", material),
             ("Demandas (LRFD)", "; ".join(demands))]
    ids = {c.id for c in result.checks}
    if case.Pu < 0 and case.tension:
        t = case.tension
        items.append(("Sección neta", f"An = {_fmt(t.An)} mm² (B4.3b); U = {_fmt(t.U)} (Tabla D3.1); datos del usuario"))
        if t.fabricated_length:
            items.append(("Longitud fabricada", f"{_fmt(t.fabricated_length)} mm (Nota de D1)"))
    if case.Pu > 0:
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
    if ids & {"flexure_x", "flexure_y"}:
        fl = case.flexure
        items.append(("Flexión", f"Lb = {_fmt(fl.Lb) + ' mm' if fl and fl.Lb else 'no indicado'}; "
                                 f"Cb = {_fmt(fl.Cb if fl else 1.0)}; agujeros en el ala traccionada: "
                                 f"{'no declarado' if not fl or fl.tension_flange_holes is None else _fmt(fl.tension_flange_holes)}"
                                 + (f" (Afn = {_fmt(fl.Afn)} mm²)" if fl and fl.Afn else "")))
    blocks.append({"kind": "kv", "items": items})
    if case.Pu > 0 and ln is not None:
        blocks.append({"kind": "table", "headers": ["Eje", "K", "L (mm)", "Lc = K·L (mm)"], "rows": [
            ["x", f.Kx, ln.Lx, f.Kx * ln.Lx], ["y", f.Ky, ln.Ly, f.Ky * ln.Ly],
            ["z (torsión)", f.Kz, ln.Lz, f.Kz * ln.Lz]]})
    blocks.append({"kind": "h2", "text": "Propiedades de la sección utilizadas"})
    blocks.append({"kind": "table", "headers": ["Propiedad", "Valor", "Unidad"], "rows": [
        [_SECTION_NAMES.get(k, k), v, _SECTION_UNITS.get(k, "–" if k.endswith("ratio") else "mm")]
        for k, v in result.section_data.items() if k not in {"name", "type", "source"}]})
    return blocks


def _verification(check) -> tuple:
    symbol = "Mu" if check.chapter == "F" else "|Pu|"
    return ("Verificación", f"{symbol} / {_capacity_label(check)} = {_fmt(check.demand)} / {_fmt(check.capacity)} "
                            f"= {_fmt(check.ratio)}")


def _tension_blocks(case: SteelCase, check, c: dict) -> list[dict]:
    blocks = [{"kind": "h2", "text": "Área neta efectiva (D3)"},
              {"kind": "p", "text": f"Ae = An·U = {_fmt(c['inputs']['An_mm2'])} · {_fmt(c['inputs']['U'])} = "
                                    f"{_fmt(c['modes']['TR']['area_mm2'])} mm² (D3-1)"},
              {"kind": "h2", "text": "Disposiciones aplicadas"},
              {"kind": "p", "text": ", ".join(c["provisions"])},
              {"kind": "h2", "text": "Estados límite (D2)"}]
    rows = []
    for name, m in c["modes"].items():
        rows.append([name, LIMIT_STATES.get(m["limit_state"], m["limit_state"]), m["Pn_equation"],
                     f"{'Fy' if name == 'TY' else 'Fu'} = {_fmt(m['stress_mpa'])}", f"{m['area_basis']} = {_fmt(m['area_mm2'])}",
                     m["Pn_kN"], f"{m['phi_t']:.2f}", m["available_kN"]])
    blocks.append({"kind": "table", "headers": ["Modo", "Estado límite", "Ec.", "Tensión (MPa)", "Área (mm²)",
                                                "Pn (kN)", "φt", "φt·Pn (kN)"],
                   "rows": rows, "highlight": list(c["modes"]).index(c["governing_mode"])})
    blocks.append({"kind": "p", "text": "Cada estado límite tiene su propio factor (D2), por lo que gobierna la menor "
                                        "resistencia de diseño φt·Pn, no la menor Pn."})
    gov = c["modes"][c["governing_mode"]]
    blocks += [{"kind": "h2", "text": "Resistencia"},
               {"kind": "kv", "items": [
                   ("Modo gobernante", f"{c['governing_mode']} — {LIMIT_STATES.get(gov['limit_state'], gov['limit_state'])}"),
                   ("Resistencia de diseño", f"min(φt·Pn) = {_fmt(c['available_kN'])} kN ({c['governing_mode']})"),
                   _verification(check)]}]
    return blocks


def _compression_blocks(case: SteelCase, check, c: dict) -> list[dict]:
    blocks = [{"kind": "h2", "text": "Clasificación de elementos (B4.1a)"}]
    rows = [[_ELEMENTS.get(r["element"], r["element"]), r["b4_case"], r["ratio"], r["lambda_r"],
             "esbelto" if r["slender"] else "no esbelto"] for r in c["classification"]["elements"]]
    if rows:
        blocks.append({"kind": "table", "headers": ["Elemento", "Caso", "λ = b/t", "λr", "Clase"], "rows": rows})
    else:
        blocks.append({"kind": "p", "text": c["classification"]["reference"]})
    blocks.append({"kind": "p", "text": f"Sección {'con' if c['classification']['slender'] else 'sin'} "
                                        "elementos esbeltos."})
    blocks.append({"kind": "h2", "text": "Disposiciones aplicadas"})
    blocks.append({"kind": "p", "text": ", ".join(c["provisions"])})
    blocks.append({"kind": "h2", "text": "Estados límite"})
    blocks.append({"kind": "table",
                   "headers": ["Modo", "Disposición", "Ec. Fe", "Fe (MPa)", "Ec. Fn", "Fn (MPa)", "Área (mm²)", "Pn (kN)"],
                   "rows": [[name, m["provision"], m["Fe_equation"], m["Fe_mpa"], m["Fn_equation"], m["Fn_mpa"],
                             f"{m['area_basis']} = {_fmt(m['area_mm2'])}", m["Pn_kN"]]
                            for name, m in c["modes"].items()],
                   "highlight": list(c["modes"]).index(c["governing_mode"])})
    for name, m in c["modes"].items():
        blocks.append({"kind": "h3", "text": f"Modo {name}: {LIMIT_STATES.get(m['limit_state'], m['limit_state'])} "
                                             f"({m['provision']}, eje {m['axis']})"})
        items = [(_label(k), _fmt(v)) for k, v in m.items()
                 if k not in _MODE_KEYS and isinstance(v, (int, float, str)) and not isinstance(v, bool)]
        items += [("Fy/Fe", f"{_fmt(m['Fy_over_Fe'])} → {m['Fn_equation']}"),
                  ("Pn", f"Fn · {m['area_basis']} = {_fmt(m['Pn_kN'])} kN ({m['Pn_equation']})")]
        blocks.append({"kind": "kv", "items": items, "compact": True})
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
             ("Pn", f"{_fmt(c['Pn_kN'])} kN ({c['governing_equation']})"),
             ("Resistencia de diseño", f"φc·Pn = 0.90 · Pn = {_fmt(c['available_kN'])} kN"),
             _verification(check)]
    for req in c["requirements"]:
        items.append((f"Requisito {req['id']}", f"a/ri = {_fmt(req['a_over_ri'])} ≤ {_fmt(req['limit'])} → "
                                                f"{'cumple' if req['satisfied'] else 'NO cumple'}"))
    blocks += [{"kind": "h2", "text": "Resistencia"}, {"kind": "kv", "items": items}]
    return blocks


_FLEXURE_KEYS = {"limit_state", "provision", "applies", "reason", "Mn", "Mn_kNm", "design_kNm", "equation"}


def _flexure_blocks(case: SteelCase, check, c: dict) -> list[dict]:
    blocks = [{"kind": "h2", "text": "Clasificación de elementos (B4.1b)"}]
    rows = [[_ELEMENTS.get(r["element"], r["element"]), r["b4_case"], r["ratio"], r["lambda_p"], r["lambda_r"], r["class"]]
            for r in c["classification"]["elements"]]
    if rows:
        blocks.append({"kind": "table", "headers": ["Elemento", "Caso", "λ", "λp", "λr", "Clase"], "rows": rows})
    else:
        blocks.append({"kind": "p", "text": "Barra maciza: sin elementos esbeltos (F11)."})
    blocks += [{"kind": "h2", "text": "Disposiciones aplicadas"}, {"kind": "p", "text": ", ".join(c["provisions"])},
               {"kind": "h2", "text": "Estados límite"}]
    names = list(c["modes"])
    blocks.append({"kind": "table", "headers": ["Estado límite", "Disposición", "Ec.", "Mn (kN·m)", "φb·Mn (kN·m)"],
                   "rows": [[f"{k} — {FLEXURE_STATES.get(k, k)}", m["provision"],
                             m["equation"] if m["applies"] else "no aplica",
                             m["Mn_kNm"] if m["applies"] else "–", m["design_kNm"] if m["applies"] else "–"]
                            for k, m in c["modes"].items()],
                   "highlight": names.index(c["governing_mode"])})
    for name, m in c["modes"].items():
        extra = [(_label(k), _fmt(v)) for k, v in m.items()
                 if k not in _FLEXURE_KEYS and isinstance(v, (int, float, str)) and not isinstance(v, bool) and v is not None]
        if m["applies"] or extra:
            blocks.append({"kind": "h3", "text": f"{name}: {FLEXURE_STATES.get(name, name)} ({m['provision']})"})
            if not m["applies"]:
                blocks.append({"kind": "note", "text": m["reason"]})
            items = extra + ([("Mn", f"{_fmt(m['Mn_kNm'])} kN·m ({m['equation']})")] if m["applies"] else [])
            if items:
                blocks.append({"kind": "kv", "items": items, "compact": True})
        else:
            blocks.append({"kind": "note", "text": f"{name}: {m['reason']}"})
    gov = c["modes"][c["governing_mode"]]
    blocks += [{"kind": "h2", "text": "Resistencia"}, {"kind": "kv", "items": [
        ("Estado límite gobernante", f"{c['governing_mode']} — {FLEXURE_STATES.get(c['governing_mode'], '')} "
                                     f"({gov['equation']})"),
        ("Mn", f"{_fmt(c['Mn_kNm'])} kN·m"),
        ("Resistencia de diseño", f"φb·Mn = 0.90 · Mn = {_fmt(c['available_kNm'])} kN·m"),
        _verification(check)]}]
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
                    + (f"   Pu/capacidad = {_fmt(b['ratio'])}" if b["ratio"] is not None else "")]
        elif kind == "summary":
            out.append("  |  ".join(f"{k}: {v}" for k, v in b["items"]))
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
    return render_text(report_blocks(case, result, title=title))


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
        if pdf.get_y() > pdf.h - 45:
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

    def table(headers, rows, highlight=None, compact=False, kv=False):
        texts = [[clean(_fmt(v)) for v in row] for row in rows]
        if len(rows) <= 12 and pdf.get_y() + (len(rows) + 1) * 6.5 > pdf.h - pdf.b_margin:
            pdf.add_page()
        weights = [max([len(str(h))] + [len(r[i]) for r in texts]) + 2 for i, h in enumerate(headers)]
        numeric = [all(isinstance(r[i], (int, float)) for r in rows) for i in range(len(headers))]
        pdf.set_font(FONT, "", 8.5 if not compact else 8)
        pdf.set_text_color(*_INK)
        pdf.set_draw_color(*_RULE)
        fill = _CARD if kv else _ZEBRA
        pdf.set_fill_color(*fill)  # never inherit a previous fill (status badge, cards)
        natural = sum(weights) * 2.1  # mm, about one character of 8.5 pt per weight unit
        style = dict(width=min(width(), max(natural, 70)), col_widths=weights, line_height=5.2, padding=(1, 1.6),
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

    for blocks in documents:
        pdf.member = None
        pdf.add_page()
        for b in blocks:
            kind = b["kind"]
            if kind == "title":
                pdf.member = b["member"] + (f" · {b['case']}" if b.get("case") else "")
                pdf.set_fill_color(*_NAVY)
                pdf.rect(0, 0, pdf.w, 4, style="F")
                pdf.set_y(14)
                pdf.set_font(FONT, "", 9)
                pdf.set_text_color(*_MUTED)
                pdf.cell(0, 5, clean(f"MEMORIA DE CÁLCULO · {b['action'].upper()}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font(FONT, "B", 18)
                pdf.set_text_color(*_NAVY)
                pdf.multi_cell(width() - 42, 9, clean(b["member"]), new_x="LMARGIN", new_y="NEXT")
                if b.get("case"):
                    pdf.set_font(FONT, "", 10.5)
                    pdf.set_text_color(*_INK)
                    pdf.multi_cell(width() - 42, 5.5, clean(b["case"]), new_x="LMARGIN", new_y="NEXT")
                    pdf.ln(1.5)
                color = _STATUS_COLOR[b["status"]]
                pdf.set_fill_color(*color)
                pdf.rect(pdf.w - pdf.r_margin - 38, 19, 38, 10, style="F", round_corners=True, corner_radius=2)
                pdf.set_xy(pdf.w - pdf.r_margin - 38, 19)
                pdf.set_font(FONT, "B", 10)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(38, 10, clean(STATUS_TEXT[b["status"]]), align="C")
                pdf.set_xy(pdf.l_margin, max(pdf.get_y(), 31) + 2)
                pdf.set_font(FONT, "", 8.5)
                pdf.set_text_color(*_MUTED)
                pdf.cell(0, 5, clean("   ·   ".join(f"{k}: {v}" for k, v in b["meta"])), new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(*_RULE)
                pdf.line(pdf.l_margin, pdf.get_y() + 2, pdf.w - pdf.r_margin, pdf.get_y() + 2)
                pdf.ln(6)
            elif kind == "summary":
                gap, n = 3, len(b["items"])
                card_w, y = (width() - gap * (n - 1)) / n, pdf.get_y()
                for i, (label, value) in enumerate(b["items"]):
                    x = pdf.l_margin + i * (card_w + gap)
                    pdf.set_fill_color(*_CARD)
                    pdf.rect(x, y, card_w, 17, style="F", round_corners=True, corner_radius=1.5)
                    pdf.set_xy(x + 3, y + 2.5)
                    pdf.set_font(FONT, "", 7.5)
                    pdf.set_text_color(*_MUTED)
                    pdf.cell(card_w - 6, 4, clean(label))
                    pdf.set_xy(x + 3, y + 8)
                    pdf.set_font(FONT, "B", 11.5)
                    pdf.set_text_color(*_INK)
                    pdf.cell(card_w - 6, 6, clean(value))
                pdf.set_xy(pdf.l_margin, y + 21)
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
