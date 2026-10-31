"""Calculation report: built from the engine result only, readable as text and as PDF."""
import json
import subprocess
import sys

import pytest

from steel_design.engine import SteelDesignEngine
from steel_design.execution import prepare_cases
from steel_design.models import SteelCase
from steel_design.reporting import _fmt, calculation_report, pdf_bytes, report_blocks
from steel_design.sections.loader import load_sections_from_excel
from steel_design.sections.repository import SectionRepository

from conftest import CATALOG, ROOT, steel_case


def test_report_shows_inputs_modes_and_governing_values(engine):
    case = steel_case("C15X50", Pu=300, L=4000, Ly=1000)
    result = engine.run(case)
    text = calculation_report(case, result)
    c = result.compression
    assert "RESULTADO: PASS" in text and "catálogo C fila" in text
    for heading in ("## 5. Revisión de capacidad a carga de compresión", "### 5.1 Compresión (Capítulo E)",
                    "#### Clasificación de elementos (B4.1a)", "#### Disposiciones aplicadas", "#### Estados límite",
                    "#### Resistencia", "#### Obligaciones del Capítulo E", "### 10.4 Notas y limitaciones"):
        assert heading in text
    for name, mode in c["modes"].items():
        assert f"Modo {name}:" in text and _fmt(mode["Pn_kN"]) in text and mode["Fe_equation"] in text
    assert "Modo gobernante: FTB" in text
    assert _fmt(c["available_kN"]) in text and "Pn/Ω" not in text and "ASD" not in text
    assert _fmt(result.ratio) in text


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
    documents = [report_blocks(c, engine.run(c)) for c in (steel_case("W14X90"), steel_case("2L4X4X1/4"))]
    assert pdf_bytes(documents).startswith(b"%PDF")


def test_cli_writes_report_and_pdf_only_on_request(tmp_path):
    run = subprocess.run([sys.executable, "-m", "steel_design.run", str(ROOT / "examples/w_shape.json"),
                          "--sections", str(CATALOG), "--report", "m.txt", "--pdf", "m.pdf"],
                         cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stderr
    text = (tmp_path / "m.txt").read_text(encoding="utf-8")
    assert "compresión W14X90 · Combinación 1 — compresión" in text
    assert "tracción W14X90 · Combinación 2 — tracción" in text
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
    assert _fmt(value) == expected


CHAPTERS = ("## 1. Propiedades mecánicas de los materiales", "### 1.1 Acero estructural", "### 1.2 Concreto estructural",
            "### 1.3 Acero de refuerzo", "## 2. Propiedades geométricas", "### 2.1 Geometría", "### 2.2 Rigideces elásticas",
            "### 2.3 Rigideces efectivas", "### 2.4 Rigideces para método directo: rigideces efectivas (análisis de estabilidad, DAM)", "## 3. Solicitaciones", "### 3.1 Cargas últimas", "### 3.2 Desplazamientos",
            "## 4. Revisión de requerimientos técnicos", "### 4.1 Propiedades mecánicas de los materiales", "### 4.2 Propiedades geométricas",
            "## 5. Revisión de capacidad a carga de compresión", "## 6. Revisión de capacidad a carga de tracción",
            "## 7. Revisión de capacidad a fuerza cortante", "## 8. Revisión de capacidad a momento flector",
            "## 9. Revisión de capacidad a momento torsional", "## 10. Índices DCR")


def example_documents():
    repository = SectionRepository()
    repository.load(load_sections_from_excel(str(CATALOG)))
    engine = SteelDesignEngine(repository)
    for path in sorted((ROOT / "examples").glob("*.json")):
        for tag, case in prepare_cases(json.loads(path.read_text(encoding="utf-8"))):
            yield path.name, tag, case, engine.run(case)


def test_every_report_has_its_ten_chapters_in_order():
    for name, tag, case, result in example_documents():
        text = calculation_report(case, result)
        positions = [text.find(f"{heading}\n") for heading in CHAPTERS]
        assert -1 not in positions and positions == sorted(positions), (name, tag)


def test_what_does_not_apply_or_is_missing_is_said_explicitly(engine):
    tension_only = SteelCase(tau_b=1.0, section_name="W14X90", material={"Fy": 345, "Fu": 450}, Pu=-100, tension={"An": 15000, "U": 0.9})
    text = calculation_report(tension_only, engine.run(tension_only))
    for sentence in ("No aplica: miembro sin concreto.", "No aplica: miembro sin barras de refuerzo.",
                     "No aplica: la combinación no tiene carga de compresión", "No aplica: la combinación no tiene fuerza cortante",
                     "No aplica: la combinación no tiene momento flector", "No aplica: la combinación no combina",
                     "Falta implementación: la entrada no admite desplazamientos", "Falta implementación: la entrada no admite momento torsional"):
        assert sentence in text
    assert "### 6.1 Tracción (Capítulo D)" in text


def test_symbols_are_named_in_words(engine):
    case = steel_case("W14X90", L=4000)
    text = calculation_report(case, engine.run(case))
    for words in ("Área bruta (Ag)", "Momento de inercia respecto de x (Ix)", "Esfuerzo de fluencia mínimo especificado (Fy)",
                  "Lx: para pandeo por flexión respecto del eje x", "Ly: para pandeo por flexión respecto del eje y",
                  "Lz: para pandeo torsional respecto del eje longitudinal", "Esfuerzo de pandeo elástico, Fe (MPa)"):
        assert words in text


def test_every_calculated_parameter_has_words_unit_and_literal():
    seen = 0
    for name, tag, case, result in example_documents():
        for block in report_blocks(case, result):
            if block["kind"] == "table" and block["headers"][0] == "Parámetro":
                for label, _, unit, literal in block["rows"]:
                    seen += 1
                    assert "_" not in label and unit and literal and literal != "–", (name, tag, label)
    assert seen > 500


def test_literals_come_from_the_equation_applied(engine):
    case = steel_case("W14X90", L=4000)
    blocks = report_blocks(case, engine.run(case))
    rows = [row for b in blocks if b["kind"] == "table" and b["headers"][0] == "Parámetro" for row in b["rows"]]
    assert ["Longitud efectiva (Lc)", 4000.0, "mm", "E2"] in rows
    assert any(row[0].startswith("Resistencia nominal (Pn") and row[3] == "E3, Ec. E3-1" for row in rows)


def test_elastic_stiffness_of_bare_steel_by_hand(engine):
    # W14X90: E*Ix = 200000*4.16e8 N*mm2 = 83200 kN*m2; G*J = 77200*1.69e6 N*mm2 = 130.468 kN*m2
    result = engine.run(SteelCase(tau_b=1.0, section_name="W14X90", material={"Fy": 345}, Vux=1))
    rows = {r["symbol"]: r for r in result.stiffness["elastic"]}
    assert rows["EIx"]["value"] == pytest.approx(83200e9) and rows["GJ"]["value"] == pytest.approx(130.468e9)
    assert rows["EA"]["value"] == pytest.approx(200000 * 17100) and rows["GA"]["status"] == "falta_implementacion"
    assert result.stiffness["effective"][0]["status"] == "no_aplica"


def test_double_angle_stiffness_uses_both_angles(engine, sections):
    result = engine.run(SteelCase(tau_b=1.0, section_name="2L4X4X1/4", material={"Fy": 345}, Vux=1))
    gj = next(r for r in result.stiffness["elastic"] if r["symbol"] == "GJ")
    assert gj["value"] == pytest.approx(77200 * 2 * sections["L4X4X1/4"].j)


def test_inconsistent_catalog_data_give_no_stiffness(engine):
    case = SteelCase(tau_b=1.0, section_name="IPE 80", material={"Fy": 345}, Vux=1)
    result = engine.run(case)
    assert "error" in result.stiffness and "No calculadas" in calculation_report(case, result)


def _filled_case(**demands):
    return SteelCase(tau_b=0.8, section_name="PTE200X200X7MM", material={"Fy": 345},
                     composite={"kind": "filled", "concrete": {"fc": 35, "wc": 2320, "lightweight": False}}, **demands)


def test_composite_stiffness_does_not_need_compression(engine):
    rows = {r["symbol"]: r for r in engine.run(_filled_case(Mux=1)).stiffness["effective"]}
    direct = {r["symbol"]: r for r in engine.run(_filled_case(Mux=1)).stiffness["direct_analysis"]}
    assert direct["EI*x"]["value"] == pytest.approx(0.64 * rows["(EI)eff,x"]["value"])
    assert direct["EA*"]["value"] == pytest.approx(0.8 * rows["(EA)eff"]["value"])


def test_net_tension_uses_the_bare_steel(engine, sections):
    # I1.5(c)
    rows = {r["symbol"]: r for r in engine.run(_filled_case(Pu=-10, tension={"An": 5000, "U": 1.0})).stiffness["effective"]}
    assert rows["EIx"]["value"] == pytest.approx(200000 * sections["PTE200X200X7MM"].ix)


def test_reference_documents_of_composite_stiffnesses_are_stated(engine):
    case = _filled_case(Pu=100, lengths={"Lx": 3000, "Ly": 3000, "Lz": 3000})
    text = calculation_report(case, engine.run(case))
    for words in ("Guía 6, Ec. 2-9", "no es norma", "I1.5(a), Ec. I2-12", "I1.5(a), C2.3: 0.8·τb·(EI)eff", "2.4 Rigideces para método directo", "Módulo de elasticidad del concreto (Ec)"):
        assert words in text
