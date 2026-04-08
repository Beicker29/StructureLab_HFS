import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl


def _write_excel(path: Path, headers, rows):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def _write_case(path: Path, *, pu: float, mux: float, muy: float, vu: float):
    payload = {
        "section_name": "W14X90",
        "design_method": "LRFD",
        "material": {"Fy": 345.0, "Fu": 450.0, "E": 200000.0},
        "loads": {"Pu": pu, "Mux": mux, "Muy": muy, "Vu": vu},
        "lengths": {"Lx": 3000.0, "Ly": 3000.0, "Lb": 3000.0},
        "factors": {"Kx": 1.0, "Ky": 1.0, "Cb": 1.0},
        "connection": {"Ae": None},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class EngineCliIntegrationTests(unittest.TestCase):
    def _run_cli(self, case_path: Path, sections_path: Path):
        repo_root = Path(__file__).resolve().parents[1]
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "src.steel_design.run",
                str(case_path),
                "--sections",
                str(sections_path),
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_cli_fails_hard_for_incomplete_catalog_data(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            sections_path = tmp / "sections.xlsx"
            case_path = tmp / "case.json"
            _write_excel(
                sections_path,
                headers=["shape", "area [mm2]", "rx [mm]", "ry [mm]"],
                rows=[["W14X90", 17000.0, 90.0, 55.0]],
            )
            _write_case(case_path, pu=0.0, mux=200.0, muy=0.0, vu=0.0)

            completed = self._run_cli(case_path, sections_path)

            self.assertNotEqual(0, completed.returncode)
            self.assertIn('"code": "INCOMPLETE_SECTION_DATA"', completed.stderr)
            self.assertIn('"stage": "run_engine"', completed.stderr)

    def test_cli_fails_hard_for_non_implemented_rule(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            sections_path = tmp / "sections.xlsx"
            case_path = tmp / "case.json"
            _write_excel(
                sections_path,
                headers=["shape", "area [mm2]", "Zx [mm3]", "rx [mm]", "ry [mm]"],
                rows=[["W14X90", 17000.0, 1500000.0, 90.0, 55.0]],
            )
            _write_case(case_path, pu=0.0, mux=0.0, muy=0.0, vu=50.0)

            completed = self._run_cli(case_path, sections_path)

            self.assertNotEqual(0, completed.returncode)
            self.assertIn('"code": "RULE_NOT_IMPLEMENTED"', completed.stderr)
            self.assertIn('"rule_id": "G2"', completed.stderr)

    def test_cli_returns_json_for_fully_supported_case(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            sections_path = tmp / "sections.xlsx"
            case_path = tmp / "case.json"
            _write_excel(
                sections_path,
                headers=["shape", "area [mm2]", "Zx [mm3]", "rx [mm]", "ry [mm]"],
                rows=[["W14X90", 17000.0, 1500000.0, 90.0, 55.0]],
            )
            _write_case(case_path, pu=0.0, mux=200.0, muy=0.0, vu=0.0)

            completed = self._run_cli(case_path, sections_path)

            self.assertEqual(0, completed.returncode)
            self.assertIn('"status":"PASS"', completed.stdout.replace(" ", ""))
            self.assertIn("Flexure Major F2", completed.stdout)


if __name__ == "__main__":
    unittest.main()
