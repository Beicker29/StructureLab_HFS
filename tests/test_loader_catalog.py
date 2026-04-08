import tempfile
import unittest
from pathlib import Path

import openpyxl

from src.steel_design.domain.errors import CatalogSchemaError
from src.steel_design.sections.loader import load_sections_from_excel


def _write_excel(path: Path, headers, rows):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    workbook.save(path)


class CatalogLoaderTests(unittest.TestCase):
    def test_catalog_loader_supports_aliases_and_profile_classification(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            excel_path = Path(tmp_dir) / "sections.xlsx"
            _write_excel(
                excel_path,
                headers=["shape", "area [mm2]", "Zx [mm3]", "rx [mm]", "ry [mm]"],
                rows=[
                    ["PTE 150X300X8.0mm", 6332.0, 120000.0, 91.0, 51.0],
                    ["PTE 200X8.0mm", 4800.0, 85000.0, 75.0, 75.0],
                    ["L6X6X1_2", 2500.0, 45000.0, 22.0, 22.0],
                ],
            )

            sections = load_sections_from_excel(str(excel_path))

            self.assertEqual(3, len(sections))
            self.assertEqual("RECTANGULAR_HSS", sections[0].type)
            self.assertEqual("CIRCULAR_HSS", sections[1].type)
            self.assertEqual("SINGLE_ANGLE", sections[2].type)

    def test_catalog_loader_fails_when_required_headers_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            excel_path = Path(tmp_dir) / "sections.xlsx"
            _write_excel(
                excel_path,
                headers=["shape", "Zx [mm3]"],
                rows=[["W14X90", 123000.0]],
            )

            with self.assertRaises(CatalogSchemaError) as raised:
                load_sections_from_excel(str(excel_path))

            self.assertEqual("CATALOG_SCHEMA_ERROR", raised.exception.code)

    def test_catalog_loader_fails_for_unknown_profile_name(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            excel_path = Path(tmp_dir) / "sections.xlsx"
            _write_excel(
                excel_path,
                headers=["shape", "area [mm2]", "Zx [mm3]"],
                rows=[["UNKNOWN_PROFILE", 1000.0, 100.0]],
            )

            with self.assertRaises(CatalogSchemaError) as raised:
                load_sections_from_excel(str(excel_path))

            self.assertIn("shape", raised.exception.details)


if __name__ == "__main__":
    unittest.main()
