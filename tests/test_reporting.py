"""Calculation report: built from the engine result only, readable as text and as PDF."""
import json
import subprocess
import sys

import pytest

from steel_design.reporting import _fmt, calculation_report, pdf_bytes, report_blocks

from conftest import CATALOG, ROOT, steel_case


def test_report_shows_inputs_modes_and_governing_values(engine):
    case = steel_case("C15X50", Pu=300, L=4000, Ly=1000)
    result = engine.run(case)
    text = calculation_report(case, result)
    c = result.compression
    assert "RESULTADO: PASS" in text and "catálogo C fila" in text
    for heading in ("## 1. Datos", "## 2. Clasificación", "## 3. Disposiciones", "## 4. Estados límite",
                    "## 5. Resistencia", "## 6. Obligaciones", "## 7. Notas"):
        assert heading in text
    for name, mode in c["modes"].items():
        assert f"Modo {name}:" in text and _fmt(mode["Pn_kN"]) in text and mode["Fe_equation"] in text
    assert "Modo gobernante: FTB" in text
    assert _fmt(c["available"]["LRFD"]) in text and _fmt(c["available"]["ASD"]) in text
    assert _fmt(result.ratio) in text


def test_report_lists_effective_widths_of_slender_elements(engine):
    case = steel_case("PTE120X60X2MM", L=1500)
    text = calculation_report(case, engine.run(case))
    assert "E7-3" in text and "Ae = Ag − Σ n·(b − be)·t" in text


def test_report_of_blocked_case_has_no_strength(engine):
    case = steel_case("2L4X4X1/4")
    text = calculation_report(case, engine.run(case))
    assert "RESULTADO: INCOMPLETE" in text and "Cálculo no realizado" in text
    assert "## 5. Resistencia" not in text and "double_angle_e6" in text


def test_pdf_is_built_in_memory(engine):
    documents = [report_blocks(c, engine.run(c)) for c in (steel_case("W14X90"), steel_case("2L4X4X1/4"))]
    assert pdf_bytes(documents).startswith(b"%PDF")


def test_cli_writes_report_and_pdf_only_on_request(tmp_path):
    run = subprocess.run([sys.executable, "-m", "steel_design.run", str(ROOT / "examples/bundle_case.json"),
                          "--sections", str(CATALOG), "--report", "m.txt", "--pdf", "m.pdf"],
                         cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stderr
    text = (tmp_path / "m.txt").read_text(encoding="utf-8")
    assert "compresión W8X10 slender web" in text and "compresión W14X90 minor-axis offset bracing" in text
    assert (tmp_path / "m.pdf").read_bytes().startswith(b"%PDF")
    assert json.loads(run.stdout)["status"] == "PASS"


def test_cli_default_report_location_is_ignored_results_folder(tmp_path):
    run = subprocess.run([sys.executable, "-m", "steel_design.run", str(ROOT / "examples/w_shape_case.json"),
                          "--sections", str(CATALOG), "--pdf", "--report"],
                         cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stderr
    assert sorted(p.name for p in (tmp_path / "results").iterdir()) == ["w_shape_case.pdf", "w_shape_case.txt"]


@pytest.mark.parametrize("value, expected", [(1, "1"), (True, "sí"), (2.5, "2.500"), (4.3e12, "4.3000e+12"), (200000.0, "200000.000")])
def test_number_format(value, expected):
    assert _fmt(value) == expected
