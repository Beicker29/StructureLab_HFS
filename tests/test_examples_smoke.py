import json
import subprocess
import sys
import unittest
from pathlib import Path


class ExampleSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[1]

    def _run_example(self, relative_path: str):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "src.steel_design.run",
                str(self.repo_root / relative_path),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_positive_examples_return_json(self):
        positive_examples = [
            "examples/w_shape_case.json",
            "examples/channel_case.json",
            "examples/single_angle_case.json",
            "examples/rectangular_hss_case.json",
            "examples/circular_hss_case.json",
            "examples/solid_circular_case.json",
            "examples/solid_rectangular_case.json",
        ]
        for example in positive_examples:
            with self.subTest(example=example):
                completed = self._run_example(example)
                self.assertEqual(0, completed.returncode)
                payload = json.loads(completed.stdout)
                self.assertIn("status", payload)
                if payload.get("bundle") is True:
                    self.assertIn("cases", payload)
                    self.assertGreater(len(payload["cases"]), 0)
                else:
                    self.assertIn("checks", payload)

    def test_negative_examples_fail_with_structured_error(self):
        negative_examples = {
            "examples/double_angle_case.json": "INCOMPLETE_SECTION_DATA",
        }
        for example, expected_code in negative_examples.items():
            with self.subTest(example=example):
                completed = self._run_example(example)
                self.assertNotEqual(0, completed.returncode)
                error_payload = json.loads(completed.stderr)
                self.assertEqual(expected_code, error_payload["error"]["code"])


if __name__ == "__main__":
    unittest.main()
