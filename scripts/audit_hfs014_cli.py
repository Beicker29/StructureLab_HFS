"""Capture HFS-014 CLI examples, detailed consumers and F-05/F-29 probes.

Run against an explicit source copy: python scripts/audit_hfs014_cli.py ROOT OUT.
Outputs must be new. Original examples are run verbatim; a second transport-only
variant enables detailed JSON without changing engineering input. No production
formula is used as an independent expected value.
"""
import json
import os
from pathlib import Path
import sys

from audit_baseline import execute, normalize, sha, write_json


def parse_record(text):
    # Detailed legacy memories may contain Infinity. Preserve that token
    # explicitly in evidence; do not fix production serialization in HFS-014.
    return json.loads(text, parse_constant=lambda token: {"nonfinite_json_token": token})


def capture(root, out):
    root, out = root.resolve(), out.resolve()
    if out.exists():
        raise SystemExit("Use a new evidence path")
    out.mkdir(parents=True)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update(PYTHONNOUSERSITE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONUTF8="1")
    records = {}
    for number, path in enumerate(sorted((root / "examples").glob("*.json"))):
        for detailed in (False, True):
            source = path
            if detailed:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                payload["output"] = {"write_results_json": True}
                source = out / "inputs" / path.name
                write_json(source, payload)
            label = f"{path.name}/{'detailed' if detailed else 'original'}"
            command = [sys.executable, "-m", "src.steel_design.run", str(source),
                "--sections", str(root / "data/sections.xlsx"),
                "--results-dir", str(out / "artifacts" / f"{number:02d}{'d' if detailed else 'o'}")]
            run = execute(command, root, env)
            parsed = parse_record(run["stderr"] if run["returncode"] else run["stdout"])
            details = []
            if run["returncode"] == 0:
                for case in parsed.get("cases", [parsed]):
                    target = case.get("artifacts", {}).get("detailed_results_json")
                    if target:
                        details.append(normalize(parse_record(Path(target).read_text(encoding="utf-8"))))
            records[label] = {"source_sha256": sha(path), "transport_only_detailed_variant": detailed,
                "execution": run, "normalized_cli": normalize(parsed), "normalized_details": details}
    write_json(out / "cli-examples.json", records)
    sys.path.insert(0, str(root))
    from src.steel_design.models import CheckResult
    from src.steel_design.results_model import EngineResult, aggregate_case_statuses
    from src.steel_design.run import _build_global_summary
    checks = [CheckResult(name="axial",clause="E3-1",demand=90,capacity=100,dcr=.90,status="PASS"),
              CheckResult(name="flexure",clause="F2-1",demand=1,capacity=50,dcr=.02,status="PASS")]
    try:
        empty = {"status": aggregate_case_statuses([])}
    except Exception as error:
        empty = {"error": error.to_dict() if hasattr(error, "to_dict") else str(error)}
    empty_input = out / "empty.json"
    write_json(empty_input, {"cases": []})
    empty_results = out / "empty-results"
    empty_cli = execute([sys.executable, "-m", "src.steel_design.run", str(empty_input),
        "--sections", str(root / "data/sections.xlsx"), "--results-dir", str(empty_results)], root, env)
    write_json(out / "defect-probes.json", {"F05": {"checks": [c.model_dump(mode="json") for c in checks],
        "summary": _build_global_summary(EngineResult(checks=checks))},
        "F29_direct": empty, "F29_cli": empty_cli, "F29_created_output_directory": empty_results.exists()})
    print(f"Captured {len(records)} CLI executions plus empty-bundle probe in {out}")


if __name__ == "__main__":
    capture(*map(Path, sys.argv[1:]))
