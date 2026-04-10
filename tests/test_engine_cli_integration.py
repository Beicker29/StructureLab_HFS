import json
import shutil
import subprocess
import sys
import time
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

import openpyxl


@contextmanager
def _temporary_test_dir():
    root = Path(__file__).resolve().parent / ".tmp_tests"
    root.mkdir(exist_ok=True)
    tmp_path = root / f"cli_{uuid.uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=False)
    try:
        yield tmp_path
    finally:
        for _ in range(5):
            try:
                shutil.rmtree(tmp_path)
                break
            except FileNotFoundError:
                break
            except PermissionError:
                time.sleep(0.2)
        else:
            shutil.rmtree(tmp_path, ignore_errors=True)


def _write_excel(path: Path, headers, rows):
    workbook = openpyxl.Workbook()
    try:
        sheet = workbook.active
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        workbook.save(path)
    finally:
        workbook.close()


def _write_case(path: Path, *, pu: float, mux: float, muy: float, vu: float):
    payload = {
        "section_name": "W14X90",
        "design_method": "LRFD",
        "material": {"Fy": 345.0, "Fu": 450.0, "E": 200000.0},
        "loads": {"Pu": pu, "Mux": mux, "Muy": muy, "Vu": vu},
        "lengths": {"Lx": 3000.0, "Ly": 3000.0, "Lz": 3000.0, "Lb": 3000.0},
        "factors": {"Kx": 1.0, "Ky": 1.0, "Kz": 1.0, "Cb": 1.0},
        "connection": {},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class EngineCliIntegrationTests(unittest.TestCase):
    def _run_cli(self, case_path: Path, sections_path: Path, results_dir: Path | None = None):
        repo_root = Path(__file__).resolve().parents[1]
        command = [
            sys.executable,
            "-m",
            "src.steel_design.run",
            str(case_path),
            "--sections",
            str(sections_path),
        ]
        if results_dir is not None:
            command.extend(["--results-dir", str(results_dir)])
        return subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_cli_fails_hard_for_incomplete_catalog_data(self):
        with _temporary_test_dir() as tmp:
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
        with _temporary_test_dir() as tmp:
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
        with _temporary_test_dir() as tmp:
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

    def test_cli_prints_compact_output_and_writes_detailed_results_file(self):
        with _temporary_test_dir() as tmp:
            sections_path = tmp / "sections.xlsx"
            case_path = tmp / "case.json"
            results_dir = tmp / "results"
            _write_excel(
                sections_path,
                headers=[
                    "shape",
                    "A",
                    "rx",
                    "ry",
                    "Ix",
                    "Iy",
                    "J",
                    "Cw",
                    "bf/2tf",
                    "h/tw",
                ],
                rows=[["W14X90", 17000.0, 90.0, 55.0, 100.0, 50.0, 3.0, 4.0, 6.0, 20.0]],
            )
            _write_case(case_path, pu=300.0, mux=0.0, muy=0.0, vu=0.0)

            completed = self._run_cli(case_path, sections_path, results_dir=results_dir)

            self.assertEqual(0, completed.returncode)
            stdout_payload = json.loads(completed.stdout)
            self.assertIn("checks", stdout_payload)
            self.assertNotIn("details", completed.stdout)

            detailed_files = list((results_dir / "W").glob("*.json"))
            self.assertGreater(len(detailed_files), 0)
            detailed_payload = json.loads(detailed_files[0].read_text(encoding="utf-8"))
            self.assertIn("memory", detailed_payload)
            self.assertIn("global_summary", detailed_payload["memory"])
            self.assertIn("shared_context", detailed_payload["memory"])
            self.assertIn("clause_results", detailed_payload["memory"])
            self.assertIn("input", detailed_payload)
            self.assertIn("output", detailed_payload)
            self.assertIn("calculations", json.dumps(detailed_payload))
            self.assertNotIn('"details":', json.dumps(detailed_payload["output"]))
            self.assertIn("element_classification", detailed_payload["memory"]["shared_context"])
            self.assertTrue(all("context" not in clause for clause in detailed_payload["memory"]["clause_results"]))


if __name__ == "__main__":
    unittest.main()
