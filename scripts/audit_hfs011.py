"""Capture HFS-011 suites separately and compare unchanged example results.

This is behavioral regression evidence, not normative validation. Output and
work directories must be new. Reuses the HFS-000 capture utilities unchanged.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

from audit_baseline import ROOT, canonical_hash, engine_snapshot, execute, sha, write_json


def capture(args):
    out, work = Path(args.out).resolve(), Path(args.work).resolve()
    if out.exists() or work.exists():
        raise SystemExit("Use new output and work paths; evidence is never overwritten.")
    out.mkdir(parents=True)
    work.mkdir(parents=True)
    baseline = Path(args.baseline).resolve()
    sources = (list((ROOT / "src").rglob("*.py")) + list((ROOT / "tests").glob("test_*.py"))
               + list((ROOT / "examples").glob("*.json")) + [ROOT / "data/sections.xlsx"])
    inputs = {}
    for source in sources:
        target = work / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert sha(source) == sha(target)
        inputs[source.relative_to(ROOT).as_posix()] = sha(source)
    write_json(out / "copied_inputs.json", inputs)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update(PYTHONNOUSERSITE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONUTF8="1")
    write_json(out / "environment.json", {
        "python": sys.version, "executable": sys.executable,
        "overrides": {k: env[k] for k in ("PYTHONNOUSERSITE", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONUTF8")},
        "branch": execute(["git", "branch", "--show-current"], ROOT),
        "head": execute(["git", "rev-parse", "HEAD"], ROOT),
        "status": execute(["git", "status", "--short"], ROOT),
        "freeze": execute([sys.executable, "-m", "pip", "freeze", "--all"], ROOT, env),
        "baseline": str(baseline), "baseline_sha256": sha(baseline),
    })
    suites = {}
    extra_suites = getattr(args, "extra_suite", [])
    for label, selection in [
        ("original", ["--ignore=tests/test_hfs000_characterization.py", "--ignore=tests/test_hfs011_input_contracts.py",
                      *[f"--ignore={path}" for path in extra_suites]]),
        ("characterization", ["tests/test_hfs000_characterization.py"]),
        ("contracts", ["tests/test_hfs011_input_contracts.py"]),
        *[(Path(path).stem, [path]) for path in extra_suites],
    ]:
        xml = out / f"pytest-{label}.xml"
        command = [sys.executable, "-m", "pytest", "-q", "-ra", "--tb=short", "-p", "no:cacheprovider",
                   *selection, f"--basetemp={work / ('temp-' + label)}", f"--junitxml={xml}"]
        run = execute(command, work, env)
        write_json(out / f"pytest-{label}.json", run)
        suites[label] = {"exit": run["returncode"],
                         "junit": [s.attrib for s in ET.parse(xml).getroot()] if xml.exists() else []}
        print(label, suites[label], flush=True)
    catalog, results = engine_snapshot(work)
    before = json.loads(baseline.read_text(encoding="utf-8"))
    write_json(out / "engine-results.json", results)
    write_json(out / "catalog.json", catalog)
    comparison = {name: {"identical": before.get(name) == value,
                         "before_sha256": canonical_hash(before.get(name)),
                         "after_sha256": canonical_hash(value)} for name, value in results.items()}
    write_json(out / "comparison.json", comparison)
    unchanged = all(sha(ROOT / name) == digest for name, digest in inputs.items())
    summary = {"suites": suites, "source_inputs_unchanged_during_capture": unchanged,
               "examples_identical": before == results, "case_files": len(results),
               "engine_results_sha256": canonical_hash(results)}
    write_json(out / "verification.json", summary)
    write_json(out / "SHA256SUMS.json", {p.relative_to(out).as_posix(): sha(p)
                                         for p in sorted(out.rglob("*")) if p.is_file()})
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if unchanged and before == results and all(s["exit"] == 0 for s in suites.values()) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--extra-suite", action="append", default=[],
                        help="Additional test file to capture separately from the original suite.")
    raise SystemExit(capture(parser.parse_args()))
