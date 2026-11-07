"""Calculation report: built from the engine result only, readable as text and as PDF."""
import json
import re
import subprocess
import sys

import pytest
from conftest import CATALOG, ROOT, calculation_report, steel_case

from steel_design.execution import execute_payload, load_engine, member_groups
from steel_design.models import SteelCase
from steel_design.reporting import document
from steel_design.reporting import pdf as pdf_module
from steel_design.reporting.document import report_blocks
from steel_design.reporting.glossary import fmt
from steel_design.reporting.pdf import pdf_bytes
from steel_design.reporting.text import render_text


def test_report_shows_inputs_modes_and_governing_values(engine):
    case = steel_case("C15X50", P=-300, L=4000, Ly_2=1000)
    result = engine.run(case)
    text = calculation_report(case, result)
    c = result.compression
    assert "RESULTADO: PASS" in text and "catálogo C fila" in text
    for heading in ("## 6. Revisión de capacidad a carga de compresión", "### 6.1 Compresión (Capítulo E); case gobernante: única",
                    "#### Clasificación de elementos (B4.1a)", "#### Disposiciones aplicadas", "#### Estados límite",
                    "#### Resistencia", "#### Obligaciones del Capítulo E", "### 11.4 Notas y limitaciones"):
        assert heading in text
    for name, mode in c["modes"].items():
        assert f"Modo {name}:" in text and fmt(mode["Pn_kN"]) in text and mode["Fe_equation"] in text
    assert "Modo gobernante: FTB" in text
    assert fmt(c["available_kN"]) in text and "Pn/Ω" not in text and "ASD" not in text
    assert fmt(result.ratio) in text


def test_report_lists_effective_widths_of_slender_elements(engine):
    case = steel_case("PTE120X60X2MM", L=1500)
    text = calculation_report(case, engine.run(case))
    assert "E7-3" in text and "Ae = Ag − Σ n·(b − be)·t" in text


def test_report_of_blocked_case_has_no_strength(engine):
    case = steel_case("2L4X4X1/4")
    text = calculation_report(case, engine.run(case))
    assert "RESULTADO: INCOMPLETE" in text and "Comprobación INCOMPLETA" in text
    assert "#### Resistencia" not in text and "double_angle_e6" in text


def test_pdf_is_built_in_memory(engine):
    documents = [report_blocks([(None, c, engine.run(c))]) for c in (steel_case("W14X90"), steel_case("2L4X4X1/4"))]
    assert pdf_bytes(documents).startswith(b"%PDF")


def test_cli_writes_report_and_pdf_only_on_request(tmp_path):
    run = subprocess.run([sys.executable, "-m", "steel_design.run", str(ROOT / "examples/w_shape.json"),
                          "--sections", str(CATALOG), "--report", "m.txt", "--pdf", "m.pdf"],
                         cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stderr
    text = (tmp_path / "m.txt").read_text(encoding="utf-8")
    assert text.count("# Memoria de cálculo") == 1 and "\f" not in text
    assert "Combinación 1 — compresión" in text and "Combinación 2 — tracción" in text
    assert (tmp_path / "m.pdf").read_bytes().startswith(b"%PDF")
    assert json.loads(run.stdout)["status"] == "PASS"


def test_cli_default_report_location_is_ignored_results_folder(tmp_path):
    run = subprocess.run([sys.executable, "-m", "steel_design.run", str(ROOT / "examples/w_shape.json"),
                          "--sections", str(CATALOG), "--pdf", "--report"],
                         cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stderr
    assert sorted(p.name for p in (tmp_path / "results").iterdir()) == ["w_shape.pdf", "w_shape.txt"]


@pytest.mark.parametrize("value, expected", [(1, "1"), (True, "sí"), (2.5, "2.500"), (4.3e12, "4.3000e+12"), (200000.0, "200000.000")])
def test_number_format(value, expected):
    assert fmt(value) == expected


CHAPTERS = (
    "## 1. Propiedades mecánicas de los materiales",
    "### 1.1 Acero estructural",
    "### 1.2 Concreto estructural",
    "### 1.3 Acero de refuerzo",
    "## 2. Propiedades geométricas",
    "### 2.1 Geometría",
    "### 2.2 Rigideces elásticas",
    "### 2.3 Rigideces efectivas",
    "### 2.4 Rigideces para método directo: rigideces efectivas (análisis de estabilidad, DAM)",
    "## 3. Solicitaciones",
    "### 3.1 Cargas últimas",
    "### 3.2 Cargas de construcción",
    "### 3.3 Cargas en condición de incendio",
    "### 3.4 Deflexiones",
    "## 4. Revisión de requerimientos técnicos",
    "### 4.1 Propiedades mecánicas de los materiales",
    "### 4.2 Propiedades geométricas",
    "## 5. Revisión de condiciones de funcionalidad y/o servicio",
    "### 5.1 Revisión de deflexiones",
    "### 5.2 Condición de construcción",
    "## 6. Revisión de capacidad a carga de compresión",
    "## 7. Revisión de capacidad a carga de tracción",
    "## 8. Revisión de capacidad a fuerza cortante",
    "### 8.1 Condiciones de construcción",
    "#### 8.1.1 A lo largo de x, eje 3 (Vx_3)",
    "#### 8.1.2 A lo largo de y, eje 2 (Vy_2)",
    "### 8.2 Condiciones últimas",
    "### 8.3 Condiciones de incendio",
    "## 9. Revisión de capacidad a momento flector",
    "### 9.1 Condiciones de construcción",
    "#### 9.1.1 Respecto de x, eje 3 (Mx_3; en ángulos simples, eje principal w)",
    "#### 9.1.2 Respecto de y, eje 2 (My_2; en ángulos simples, eje principal z)",
    "### 9.2 Condiciones últimas",
    "### 9.3 Condiciones de incendio",
    "## 10. Revisión de capacidad a momento torsional",
    "## 11. Índices DCR",
)


def example_documents():
    engine = load_engine()
    for path in sorted((ROOT / "examples").glob("*.json")):
        for group in member_groups(execute_payload(json.loads(path.read_text(encoding="utf-8")), engine)):
            yield path.name, group


def test_every_report_has_its_eleven_chapters_in_order():
    for name, group in example_documents():
        text = render_text(report_blocks(group))
        positions = [text.find(f"{heading}\n") for heading in CHAPTERS]
        assert -1 not in positions and positions == sorted(positions), name
        assert "3.5" not in [line.split()[1] for line in text.splitlines() if line.startswith("### ")], name


def test_what_does_not_apply_or_is_missing_is_said_explicitly(engine):
    tension_only = SteelCase(tau_b=1.0, section_name="W14X90", material={"Fy": 345, "Fu": 450}, P=100, tension={"An": 15000, "U": 0.9})
    text = calculation_report(tension_only, engine.run(tension_only))
    for sentence in ("No aplica: miembro sin concreto.", "No aplica: miembro sin barras de refuerzo.",
                     "No aplica: ningún case tiene carga de compresión", "No aplica: ningún case en condiciones últimas tiene Vx_3",
                     "No aplica: ningún case en condiciones últimas tiene Mx_3", "No aplica: ningún case combina",
                     "No aplica: la entrada no indica deflexiones", "No aplica: ningún case de construcción",
                     "No aplica: ningún case en condiciones de incendio tiene Vx_3", "No aplica: ningún case de incendio.",
                     "Falta implementación: la entrada no admite momento torsional"):
        assert sentence in text
    assert "### 7.1 Tracción (Capítulo D); case gobernante: única" in text


def test_symbols_are_named_in_words(engine):
    case = steel_case("W14X90", L=4000)
    text = calculation_report(case, engine.run(case))
    for words in ("Área bruta (Ag)", "Momento de inercia respecto de x (eje 3) (Ix)", "Esfuerzo de fluencia mínimo especificado (Fy)",
                  "Lx_3: para pandeo por flexión respecto de x, eje 3", "Ly_2: para pandeo por flexión respecto de y, eje 2",
                  "Lz_1: para pandeo torsional respecto del eje 1", "Esfuerzo de pandeo elástico, Fe (MPa)"):
        assert words in text


def test_every_calculated_parameter_has_words_unit_and_literal():
    seen = 0
    for name, group in example_documents():
        tag = group[0][0]
        for block in report_blocks(group):
            if block["kind"] == "table" and block["headers"][0] == "Parámetro":
                for label, _, unit, literal in block["rows"]:
                    seen += 1
                    assert "_" not in label and unit and literal and literal != "–", (name, tag, label)
    assert seen > 400


def test_literals_come_from_the_equation_applied(engine):
    case = steel_case("W14X90", L=4000)
    blocks = report_blocks([(None, case, engine.run(case))])
    rows = [row for b in blocks if b["kind"] == "table" and b["headers"][0] == "Parámetro" for row in b["rows"]]
    assert ["Longitud efectiva (Lc)", 4000.0, "mm", "AISC 360-22 E2"] in rows
    assert any(row[0].startswith("Resistencia nominal (Pn") and row[3] == "AISC 360-22 E3, Ec. E3-1" for row in rows)


def test_elastic_stiffness_of_bare_steel_by_hand(engine):
    # W14X90: E*Ix = 200000*4.16e8 N*mm2 = 83200 kN*m2; G*J = 77200*1.69e6 N*mm2 = 130.468 kN*m2
    result = engine.run(SteelCase(tau_b=1.0, section_name="W14X90", material={"Fy": 345}, Vy_2=1))
    rows = {r["symbol"]: r for r in result.stiffness["elastic"]}
    assert rows["EIx_3"]["value"] == pytest.approx(83200e9) and rows["GJ"]["value"] == pytest.approx(130.468e9)
    assert rows["EA"]["value"] == pytest.approx(200000 * 17100) and rows["GA"]["status"] == "falta_implementacion"
    assert result.stiffness["effective"] == result.stiffness["elastic"]


def test_report_of_a_noncomposite_member_repeats_the_elastic_stiffness_as_effective(engine):
    case = SteelCase(tau_b=1.0, section_name="W14X90", material={"Fy": 345}, Vy_2=1)
    blocks = report_blocks([(None, case, engine.run(case))])
    start = next(i for i, b in enumerate(blocks) if b.get("text") == "2.2 Rigideces elásticas")
    end = next(i for i, b in enumerate(blocks) if b.get("text") == "2.3 Rigideces efectivas")
    elastic = next(b for b in blocks[start:end] if b["kind"] == "table")
    following = blocks[end + 1:end + 3]
    assert following[0]["text"] == "En miembros no compuestos, las rigideces efectivas son iguales a las elásticas (2.2)."
    assert following[1]["rows"] == elastic["rows"] and len(elastic["rows"]) == 6


def test_double_angle_stiffness_uses_both_angles(engine, sections):
    result = engine.run(SteelCase(tau_b=1.0, section_name="2L4X4X1/4", material={"Fy": 345}, Vy_2=1))
    gj = next(r for r in result.stiffness["elastic"] if r["symbol"] == "GJ")
    assert gj["value"] == pytest.approx(77200 * 2 * sections["L4X4X1/4"].j)


def test_inconsistent_catalog_data_give_no_stiffness(engine):
    case = SteelCase(tau_b=1.0, section_name="IPE 80", material={"Fy": 345}, Vy_2=1)
    result = engine.run(case)
    assert "error" in result.stiffness and "No calculadas" in calculation_report(case, result)


def _filled_case(**demands):
    return SteelCase(tau_b=0.8, section_name="PTE200X200X7MM", material={"Fy": 345},
                     composite={"kind": "filled", "concrete": {"fc": 35, "wc": 2320, "lightweight": False}}, **demands)


def test_composite_stiffness_does_not_need_compression(engine):
    rows = {r["symbol"]: r for r in engine.run(_filled_case(Mx_3=1)).stiffness["effective"]}
    direct = {r["symbol"]: r for r in engine.run(_filled_case(Mx_3=1)).stiffness["direct_analysis"]}
    assert direct["EI*x_3"]["value"] == pytest.approx(0.64 * rows["(EI)eff,x_3"]["value"])
    assert direct["EA*"]["value"] == pytest.approx(0.8 * rows["(EA)eff"]["value"])


def test_net_tension_uses_the_bare_steel(engine, sections):
    # I1.5(c)
    rows = {r["symbol"]: r for r in engine.run(_filled_case(P=10, tension={"An": 5000, "U": 1.0})).stiffness["effective"]}
    assert rows["EIx_3"]["value"] == pytest.approx(200000 * sections["PTE200X200X7MM"].ix)


def test_reference_documents_of_composite_stiffnesses_are_stated(engine):
    case = _filled_case(P=-100, lengths={"Lx_3": 3000, "Ly_2": 3000, "Lz_1": 3000})
    text = calculation_report(case, engine.run(case))
    for words in (
        "AISC Design Guide 6, Ec. 2-9",
        "no es norma",
        "I1.5(a), Ec. I2-12",
        "I1.5(a), C2.3: 0.8·τb·(EI)eff",
        "2.4 Rigideces para método directo",
        "Módulo de elasticidad del concreto (Ec)",
    ):
        assert words in text


def member_text(engine, example):
    groups = member_groups(execute_payload(json.loads((ROOT / "examples" / example).read_text(encoding="utf-8")), engine))
    return groups, [render_text(report_blocks(group)) for group in groups]


def test_one_report_per_member_however_many_load_cases(engine):
    assert [len(g) for g in member_text(engine, "w_shape.json")[0]] == [10]
    assert [len(g) for g in member_text(engine, "multi_member.json")[0]] == [1, 1]


def test_each_review_reports_the_case_with_the_largest_dcr(engine):
    groups, (text,) = member_text(engine, "w_shape.json")
    ratios = {
        tag: result.check("flexure_x_3").ratio
        for tag, case, result in groups[0]
        if result.check("flexure_x_3") and case.condition == "ultimate"
    }
    worst = max(ratios, key=ratios.get)
    assert f"Flexión respecto de x (eje 3) (Capítulo F); case gobernante: {worst}." in text
    table = next(b for b in report_blocks(groups[0]) if b["kind"] == "table" and "Case gobernante" in b["headers"])
    row = next(r for r in table["rows"] if r[0] == "Últimas" and r[1].startswith("Flexión respecto de x"))
    assert row[2] == worst and row[5] == ratios[worst]
    interaction = {tag: result.check("interaction").ratio for tag, _, result in groups[0] if result.check("interaction")}
    assert f"Case del DCR máximo: {max(interaction, key=interaction.get)}" in text


def test_a_load_case_without_strength_is_not_hidden_by_a_larger_dcr(engine):
    data = {"section_name": "W14X90", "material": "ASTM A572 Gr 50", "flexure": {"tension_flange_holes": False}, "cases": [
        {"name": "Con datos", "Mx_3": 100, "lengths": {"Lx_3": 3000, "Ly_2": 3000, "Lz_1": 3000}},
        {"name": "Sin datos", "Mx_3": 10}]}
    group = member_groups(execute_payload(data, engine))[0]
    assert "Flexión respecto de x (eje 3) (Capítulo F); case gobernante: Sin datos." in render_text(report_blocks(group))


def test_composite_beam_report_has_construction_and_deflections(engine):
    _, (text,) = member_text(engine, "composite_beam.json")
    for sentence in ("Luz efectiva (deflexiones), L", "Carga viva a corto plazo", "38.100", "Carga viva + muerta a largo plazo", "57.150",
                     "558.900 kN·m", "Flexión respecto de x (eje 3) (Capítulo F); case gobernante: Concrete pour.",
                     "Flexión respecto de x (eje 3) (Capítulo I); case gobernante: Flexure and shear."):
        assert sentence in text
    construction = text[text.index("### 9.1 Condiciones de construcción"):text.index("### 9.2 Condiciones últimas")]
    assert "Concrete pour" in construction and "Flexure and shear" not in construction


FULL = (
    "w_shape",
    "channel",
    "circular_hss",
    "rectangular_hss",
    "rectangular_hss_slender",
    "double_angle",
    "single_angle",
    "solid_rectangular",
    "composite_beam",
    "composite_filled",
    "composite_filled_bars",
    "composite_high_strength",
    "composite_method2",
    "composite_encased",
    "composite_box",
)


@pytest.mark.parametrize("stem", FULL)
def test_examples_show_deflections_and_construction(engine, stem):
    groups, (text,) = member_text(engine, f"{stem}.json")
    construction = [r for _, case, r in groups[0] if case.condition == "construction"]
    assert construction and all(r.status.value == "PASS" for r in construction)
    assert len(groups[0][0][2].serviceability) == 3
    section = text[text.index("### 9.1 Condiciones de construcción"):text.index("### 9.2 Condiciones últimas")]
    assert "case gobernante" in section and "No aplica: la entrada no indica deflexiones" not in text


@pytest.mark.parametrize("stem", ("composite_wall", "composite_c_wall"))
def test_wall_examples_have_neither_deflections_nor_construction(engine, stem):
    _, (text,) = member_text(engine, f"{stem}.json")
    assert "No aplica: la entrada no indica deflexiones" in text and "No aplica: ningún case de construcción." in text


def test_coupling_beam_example_has_deflections_only(engine):
    _, (text,) = member_text(engine, "composite_coupling_beam.json")
    assert "Carga viva a corto plazo" in text and "No aplica: ningún case de construcción." in text


def test_pdf_text_stays_inside_its_cell_and_the_page(engine, monkeypatch):
    """Long titles and labels wrap; fpdf2 draws a single line of cell() without checking that it fits."""
    fpdf = pytest.importorskip("fpdf")
    original, overflows = fpdf.FPDF.cell, []

    def checked(self, w=None, h=None, text="", *args, **kwargs):
        if text and "{nb}" not in str(text):                # the page number is right-aligned from the margin
            room = (self.w - self.r_margin - self.get_x()) if not w else w
            if self.get_string_width(str(text)) > room + 0.5:
                overflows.append(str(text))
        return original(self, w, h, text, *args, **kwargs)

    monkeypatch.setattr(fpdf.FPDF, "cell", checked)
    for name, group in example_documents():
        assert pdf_bytes([report_blocks(group)]).startswith(b"%PDF"), name
    assert overflows == []


def test_pdf_header_data_are_one_per_line(engine, monkeypatch):
    fpdf = pytest.importorskip("fpdf")
    original, lines = fpdf.FPDF.multi_cell, []

    def recorded(self, w, h=None, text="", *args, **kwargs):
        lines.append(text)
        return original(self, w, h, text, *args, **kwargs)

    monkeypatch.setattr(fpdf.FPDF, "multi_cell", recorded)
    case = steel_case("W14X90", L=4000)
    pdf_bytes([report_blocks([(None, case, engine.run(case))])])
    for start in ("Norma:", "Método:", "Cases de carga:", "Fecha:", "Programa:"):
        assert any(str(line).startswith(start) and " · " not in str(line) for line in lines), start


def test_pdf_columns_hold_their_longest_word(monkeypatch):
    original, tight = pdf_module._column_widths, []

    def recorded(minimums, weights, total):
        if sum(minimums) > total:
            tight.append((minimums, total))
        return original(minimums, weights, total)

    monkeypatch.setattr(pdf_module, "_column_widths", recorded)
    for _name, group in example_documents():
        pdf_bytes([report_blocks(group)])
    assert tight == []


def test_column_widths_respect_the_minimums():
    widths = pdf_module._column_widths([10.0, 20.0], [1.0, 3.0], 70.0)
    assert widths == pytest.approx([20.0, 50.0])
    assert sum(pdf_module._column_widths([50.0, 50.0], [1.0, 1.0], 80.0)) == pytest.approx(80.0)


def test_every_reference_of_every_report_names_its_document():
    for name, group in example_documents():
        for block in report_blocks(group):
            if block["kind"] != "table":
                continue
            assert not {"Literal", "Disposición", "Literal u observación"} & set(block["headers"]), name
            for i, header in enumerate(block["headers"]):
                if not header.startswith("Referencia literal"):
                    continue
                for row in block["rows"]:
                    cell = str(row[i])
                    # Without a document only the origin of a datum, or an observation that cites no provision
                    if "AISC" not in cell:
                        assert not re.search(r"(?<![\w.-])[A-N]\d+(\.\d+)*(\([a-z0-9]+\))?(?![\w-])|Guía|Commentary", cell), (name, cell)


@pytest.mark.parametrize("text, expected", [
    ("E3", "AISC 360-22 E3"),
    ("F6.1, Ec. F6-1", "AISC 360-22 F6.1, Ec. F6-1"),
    ("Guía 6, 4.3; Commentary C-I2-1", "AISC Design Guide 6, 4.3; AISC 360-22 Commentary C-I2-1"),
    ("Guía 38, 2.2.1.2", "AISC Design Guide 38, 2.2.1.2"),
    ("Dato del usuario; límites en I1.3(a)", "Dato del usuario; límites en AISC 360-22 I1.3(a)"),
    ("Apéndice 2, 2.1.1(b)", "AISC 360-22 Apéndice 2, 2.1.1(b)"),
    ("Nota de E2", "AISC 360-22 Nota de E2"),
    ("AISC Design Guide 38, Cap. 6", "AISC Design Guide 38, Cap. 6"),
    ("Dato del usuario", "Dato del usuario"),
])
def test_reference_names_the_document(text, expected):
    assert document._reference(text) == expected


def test_report_names_the_material_and_its_catalog(engine):
    _, (text,) = member_text(engine, "single_angle.json")
    for sentence in ("ASTM A36", "Catálogo Materiales.xlsx", "248.000", "410.000", "Referencia literal"):
        assert sentence in text


def test_summary_cards_show_the_strength_and_the_dcr_on_their_own_lines(engine):
    groups, _ = member_text(engine, "w_shape.json")
    blocks = report_blocks(groups[0])
    items = dict(next(b for b in blocks if b["kind"] == "summary")["items"])
    check = next(r for _, c, r in groups[0] if c.condition == "construction").check("flexure_x_3")
    assert items["Construcción, Flexión respecto de x:"] == [f"φb·Mn={check.capacity:.3f} kN·m", f"DCR={check.ratio:.3f}"]


def test_summary_card_of_an_interaction_has_only_the_dcr(engine):
    case = SteelCase(
        tau_b=1.0, section_name="L4X4X1/4", material={"Fy": 345}, Mx_3=1, My_2=0.5, heel={"axis_2": "-", "axis_3": "-"},
        lengths={"Lx_3": 1500, "Ly_2": 1500, "Lz_1": 1500})
    result = engine.run(case)
    items = next(b for b in report_blocks([(None, case, result)]) if b["kind"] == "summary")["items"]
    title, lines = next(item for item in items if item[0].startswith("Interacción"))
    assert lines == [f"DCR={result.check('interaction').ratio:.3f}"] and title.endswith(":")


def test_summary_has_a_card_for_every_review_with_the_governing_interaction(engine):
    groups, _ = member_text(engine, "w_shape.json")
    blocks = report_blocks(groups[0])
    items = next(b for b in blocks if b["kind"] == "summary")["items"]
    table = next(b for b in blocks if b["kind"] == "table" and "Case gobernante" in b["headers"])
    assert len(items) == len(table["rows"])
    interaction = next(lines for title, lines in items if title.startswith("Interacción"))
    assert interaction == ["DCR=0.745"]


def test_summary_card_without_strength_has_only_the_dcr_line(engine):
    case = steel_case("2L4X4X1/4")
    items = next(b for b in report_blocks([(None, case, engine.run(case))]) if b["kind"] == "summary")["items"]
    assert items[0][1] == ["DCR no calculado"]
