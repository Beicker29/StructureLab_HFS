"""Build/install verification, with all engine execution outside the checkout.

Run with the development tools installed: python scripts/verify_hfs020.py --out NEW.
No source code is copied into the external test root. Only tests, external inputs
and historical capture utilities are copied. Logs survive any failed command.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SUITES = [
    "test_hfs000_characterization", "test_hfs011_input_contracts",
    "test_hfs016_catalog_integrity", "test_hfs010_coverage",
    "test_hfs012_flexure_selection", "test_hfs013_directional_h3",
    "test_hfs013_design_method", "test_hfs014_summary_bundle",
    "test_hfs015_precision_advice", "test_hfs017_design_method",
]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_archives(wheel, sdist):
    """Allowlist executable payload; source distribution must rebuild standalone."""
    expected = {p.relative_to(ROOT).as_posix(): p.read_bytes()
                for p in (ROOT / "src/steel_design").rglob("*.py")}
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        code = {n: archive.read(n) for n in names if n.startswith("src/")}
        assert code == expected, "Wheel must contain exactly the existing namespace Python sources"
        assert all(n in expected or n.startswith("structurelab_hfs-0.1.0.dist-info/") for n in names)
        entry = archive.read("structurelab_hfs-0.1.0.dist-info/entry_points.txt").decode()
        assert "structurelab-hfs = src.steel_design.run:main" in entry
        metadata = archive.read("structurelab_hfs-0.1.0.dist-info/METADATA").decode()
    with tarfile.open(sdist) as archive:
        files = {m.name.split("/", 1)[1]: archive.extractfile(m).read()
                 for m in archive.getmembers() if m.isfile()}
        for name, content in expected.items():
            assert files[name] == content, name
        permitted = {"README.md", "pyproject.toml", "MANIFEST.in", "PKG-INFO", "setup.cfg"}
        assert all(n in expected or n in permitted or n.startswith("structurelab_hfs.egg-info/")
                   for n in files), sorted(files)
    return {"wheel": {"file": wheel.name, "sha256": digest(wheel), "members": names},
            "sdist": {"file": sdist.name, "sha256": digest(sdist), "members": sorted(files)},
            "python_files": len(expected), "metadata": metadata, "entry_points": entry}


def verify(args):
    out = Path(args.out).resolve()
    if out.exists():
        raise SystemExit("Use a new evidence directory")
    out.mkdir(parents=True)
    work = Path(tempfile.mkdtemp(prefix="h20-"))
    assert not work.is_relative_to(ROOT)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env.update(PYTHONNOUSERSITE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONUTF8="1")
    write(out / "environment.json", {"python": sys.version, "executable": sys.executable,
          "root": str(ROOT), "external_work": str(work), "platform": sys.platform,
          "overrides": {k: env[k] for k in ("PYTHONNOUSERSITE", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONUTF8")}})

    def run(label, command, cwd, expected=0):
        command = list(map(str, command))
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=600)
        write(out / f"{label}.json", {"command": command, "cwd": str(cwd),
              "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        print(f"{label}: exit {result.returncode}", flush=True)
        assert result.returncode == expected, f"{label}: see {out / (label + '.json')}"
        return result

    run("head", ["git", "rev-parse", "HEAD"], ROOT)
    run("status", ["git", "status", "--short"], ROOT)
    run("tools-freeze", [sys.executable, "-m", "pip", "freeze", "--all"], ROOT)
    dist = out / "dist"
    run("build", [sys.executable, "-m", "build", "--outdir", dist], ROOT)
    wheel, = dist.glob("*.whl")
    sdist, = dist.glob("*.tar.gz")
    write(out / "archives.json", inspect_archives(wheel, sdist))
    run("twine", [sys.executable, "-m", "twine", "check", "--strict", wheel, sdist], ROOT)
    run("ruff", [sys.executable, "-m", "ruff", "check", "."], ROOT)

    inputs = work / "inputs"
    inputs.mkdir()
    for folder, pattern in (("tests", "test_*.py"), ("examples", "*.json"), ("data", "sections.xlsx")):
        (inputs / folder).mkdir()
        for path in (ROOT / folder).glob(pattern):
            shutil.copyfile(path, inputs / folder / path.name)
    (inputs / "scripts").mkdir()
    for name in ("audit_baseline.py", "audit_hfs014_cli.py"):
        shutil.copyfile(ROOT / "scripts" / name, inputs / "scripts" / name)
    write(out / "external-inputs.json", {p.relative_to(inputs).as_posix(): digest(p)
          for p in inputs.rglob("*") if p.is_file()})
    empty = work / "empty"
    empty.mkdir()
    (work / "tmp").mkdir()
    constraints = ROOT / "requirements/ci-constraints.txt"
    interpreters = {}
    for mode, install_target, cwd in (("project", ".", ROOT), ("wheel", wheel, empty)):
        prefix = work / mode
        venv.EnvBuilder(with_pip=True).create(prefix)
        executable = prefix / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        cli = executable.parent / ("structurelab-hfs.exe" if os.name == "nt" else "structurelab-hfs")
        interpreters[mode] = executable
        run(f"install-{mode}", [executable, "-m", "pip", "install", "-c", constraints, install_target], cwd)
        run(f"check-{mode}", [executable, "-m", "pip", "check"], empty)
        run(f"freeze-{mode}", [executable, "-m", "pip", "freeze", "--all"], empty)
        probe = (
            "import importlib, importlib.metadata, json, pathlib, sys; "
            "mods=[importlib.import_module(n) for n in "
            "['src.steel_design.engine','src.steel_design.run','src.steel_design.models',"
            "'src.steel_design.domain.design_methods','src.steel_design.sections.repository']]; "
            "paths=[pathlib.Path(m.__file__).resolve() for m in mods]; "
            "assert all(p.is_relative_to(pathlib.Path(sys.prefix).resolve()) for p in paths); "
            "assert importlib.util.find_spec('matplotlib') is None; "
            "print(json.dumps({'version':importlib.metadata.version('structurelab-hfs'),"
            "'imports':[str(p) for p in paths],'sys_path':sys.path}))"
        )
        run(f"imports-{mode}", [executable, "-I", "-c", probe], empty)
        for label, command in (("console", [cli]), ("module", [executable, "-m", "src.steel_design.run"])):
            run(f"help-{mode}-{label}", [*command, "--help"], empty)
            result = run(f"external-{mode}-{label}", [*command,
                inputs / "examples/w_shape_case.json", "--sections", inputs / "data/sections.xlsx",
                "--results-dir", work / f"result-{mode}-{label}"], empty)
            assert json.loads(result.stdout)["status"] == "INCOMPLETE"
        missing = run(f"missing-default-{mode}", [cli, inputs / "examples/w_shape_case.json"], empty, expected=1)
        assert json.loads(missing.stderr)["error"]["stage"] == "load_sections"
        assert not (empty / "data").exists()

    executable = interpreters["wheel"]
    run("install-tests", [executable, "-m", "pip", "install", "-c", constraints, "pytest==9.1.1"], empty)
    summary = {}
    selections = [("original", [f"--ignore=tests/{name}.py" for name in SUITES])]
    selections += [(name, [f"tests/{name}.py"]) for name in SUITES]
    for label, selection in selections:
        xml = out / f"pytest-{label}.xml"
        run(f"pytest-{label}", [executable, "-m", "pytest", "-q", "-ra", "--tb=short",
            "-p", "no:cacheprovider", *selection, f"--junitxml={xml}",
            f"--basetemp={work / 'tmp' / label}"], inputs)
        summary[label] = [s.attrib for s in ET.parse(xml).getroot()]
    # These capture tools contain no production source. Imports resolve only to wheel.
    engine_code = (
        "import sys; sys.path.insert(0,'scripts'); "
        "from pathlib import Path; from audit_baseline import engine_snapshot,write_json; "
        "catalog,results=engine_snapshot(Path.cwd()); "
        "write_json(Path(sys.argv[1]),results)"
    )
    run("engine-examples", [executable, "-c", engine_code, out / "engine-results.json"], inputs)
    expected_engine = json.loads((ROOT / "docs/audit/hfs017/evidence/after/engine-results.json").read_text(encoding="utf-8"))
    assert json.loads((out / "engine-results.json").read_text(encoding="utf-8")) == expected_engine
    cli_out = work / "cli"
    run("cli-examples", [executable, inputs / "scripts/audit_hfs014_cli.py", inputs, cli_out], empty)
    shutil.copyfile(cli_out / "cli-examples.json", out / "cli-examples.json")
    expected_cli = json.loads((ROOT / "docs/audit/hfs017/evidence/cli/after.json").read_text(encoding="utf-8"))
    actual_cli = json.loads((out / "cli-examples.json").read_text(encoding="utf-8"))
    assert len(actual_cli) == len(expected_cli) == 24
    for key, actual in actual_cli.items():
        expected = expected_cli[key]
        for field in ("normalized_cli", "normalized_details", "source_sha256"):
            assert actual[field] == expected[field], (key, field)
        assert actual["execution"]["returncode"] == expected["execution"]["returncode"]
    write(out / "verification.json", {"accepted": True, "suites": summary,
          "examples_identical": 12, "cli_memory_scenarios_identical": 24,
          "external_work": str(work), "production_source_copied": False,
          "project_and_wheel_installs": True, "external_catalog_explicit": True})
    write(out / "SHA256SUMS.json", {p.relative_to(out).as_posix(): digest(p)
          for p in sorted(out.rglob("*")) if p.is_file() and p.name != "SHA256SUMS.json"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    verify(parser.parse_args())
