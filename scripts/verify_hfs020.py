"""Build/install verification, with all engine execution outside the checkout.

Run with the development tools installed: python scripts/verify_hfs020.py --out NEW.
No source code is copied into the external test root. Only tests, external inputs
and historical capture utilities are copied. Logs survive any failed command.
"""
import argparse
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import venv
import zipfile
import xml.etree.ElementTree as ET

from hfs020_comparison import (assert_json_equal, compare_cli_records, parse_json,
                              verify_input_provenance, versioned_examples)
from audit_baseline import normalize
from hfs021a_svg_comparison import assert_svg_equal

ROOT = Path(__file__).resolve().parents[1]
SUITES = [
    "test_hfs000_characterization", "test_hfs011_input_contracts",
    "test_hfs016_catalog_integrity", "test_hfs010_coverage",
    "test_hfs012_flexure_selection", "test_hfs013_directional_h3",
    "test_hfs013_design_method", "test_hfs014_summary_bundle",
    "test_hfs015_precision_advice", "test_hfs017_design_method",
    "test_hfs020_comparison",
    "test_hfs021_execution",
    "test_hfs021a_public_api",
    "test_hfs021a_svg_comparison",
]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_archives(wheel, sdist):
    """Allowlist executable payload; source distribution must rebuild standalone."""
    expected = {p.relative_to(ROOT / "src").as_posix(): p.read_bytes()
                for p in (ROOT / "src/steel_design").rglob("*.py")}
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    dist_name = project["name"].replace("-", "_")
    dist_info = f"{dist_name}-{project['version']}.dist-info/"
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        code = {n: archive.read(n) for n in names if n.startswith("steel_design/")}
        assert code == expected, "Wheel must contain exactly the conventional package sources"
        assert not any(n.startswith("src/") for n in names)
        assert all(n in expected or n.startswith(dist_info) for n in names)
        entry = archive.read(dist_info + "entry_points.txt").decode()
        assert "structurelab-hfs = steel_design.run:main" in entry
        metadata = archive.read(dist_info + "METADATA").decode()
        assert Parser().parsestr(metadata)["Version"] == project["version"]
    with tarfile.open(sdist) as archive:
        files = {m.name.split("/", 1)[1]: archive.extractfile(m).read()
                 for m in archive.getmembers() if m.isfile()}
        for name, content in expected.items():
            assert files["src/" + name] == content, name
        permitted = {"README.md", "pyproject.toml", "MANIFEST.in", "PKG-INFO", "setup.cfg"}
        assert all((n.startswith("src/") and n[4:] in expected) or n in permitted
                   or n.startswith(f"src/{dist_name}.egg-info/")
                   for n in files), sorted(files)
    return {"wheel": {"file": wheel.name, "sha256": digest(wheel), "members": names},
            "sdist": {"file": sdist.name, "sha256": digest(sdist), "members": sorted(files)},
            "python_files": len(expected), "metadata": metadata, "entry_points": entry}


def verify(args):
    out = Path(args.out).resolve()
    if out.exists():
        raise SystemExit("Use a new evidence directory")
    out.mkdir(parents=True)
    legacy_build = ROOT / "build/lib/src"
    if legacy_build.exists():
        write(out / "legacy-build-detected.json", {
            "path": str(legacy_build), "reason": "Setuptools can retain the retired package in an in-place wheel build",
            "action": "Archive the generated build directory with hashes, then move it out of build/ before retrying. No automatic deletion."})
        raise RuntimeError("Legacy build/lib/src detected; preserve and relocate the generated build directory before packaging.")
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
    for name in ("audit_baseline.py", "audit_hfs014_cli.py", "hfs020_comparison.py",
                 "hfs021a_invariants.py", "probe_hfs021a_imports.py",
                 "hfs021a_svg_comparison.py"):
        shutil.copyfile(ROOT / "scripts" / name, inputs / "scripts" / name)
    write(out / "external-inputs.json", {p.relative_to(inputs).as_posix(): digest(p)
          for p in inputs.rglob("*") if p.is_file()})
    expected_cli = parse_json((ROOT / "docs/audit/hfs017/evidence/cli/after.json").read_bytes())
    reference = parse_json((ROOT / "docs/audit/hfs020/compatibility/input-reference.json").read_bytes())

    def input_proof():
        return verify_input_provenance(
            versioned_examples(ROOT),
            {p.name: p.read_bytes() for p in (ROOT / "examples").glob("*.json")},
            {p.name: p.read_bytes() for p in (inputs / "examples").glob("*.json")},
            reference["files"], expected_cli)

    provenance = input_proof()
    write(out / "input-provenance.json", provenance)
    empty = work / "empty"
    empty.mkdir()
    (work / "tmp").mkdir()
    constraints = ROOT / "requirements/ci-constraints.txt"
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    interpreters = {}
    for mode, install_target, cwd in (("project", ".", ROOT), ("wheel", wheel, empty),
                                      ("editable", ".", ROOT)):
        prefix = work / mode
        venv.EnvBuilder(with_pip=True).create(prefix)
        executable = prefix / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        cli = executable.parent / ("structurelab-hfs.exe" if os.name == "nt" else "structurelab-hfs")
        interpreters[mode] = executable
        editable = ["-e"] if mode == "editable" else []
        run(f"install-{mode}", [executable, "-m", "pip", "install", "-c", constraints, *editable, install_target], cwd)
        run(f"check-{mode}", [executable, "-m", "pip", "check"], empty)
        run(f"freeze-{mode}", [executable, "-m", "pip", "freeze", "--all"], empty)
        origin = ROOT / "src" if mode == "editable" else prefix
        probe = (
            "import importlib, importlib.metadata, json, pathlib, sys; "
            "mods=[importlib.import_module(n) for n in "
            "['steel_design.engine','steel_design.run','steel_design.models',"
            "'steel_design.domain.design_methods','steel_design.sections.repository']]; "
            "paths=[pathlib.Path(m.__file__).resolve() for m in mods]; "
            f"assert all(p.is_relative_to(pathlib.Path({str(origin)!r}).resolve()) for p in paths); "
            f"assert importlib.metadata.version('structurelab-hfs') == {version!r}; "
            "assert not any(str(f).startswith('src/') for f in importlib.metadata.files('structurelab-hfs')); "
            "assert importlib.util.find_spec('matplotlib') is None; "
            "print(json.dumps({'version':importlib.metadata.version('structurelab-hfs'),"
            "'imports':[str(p) for p in paths],'sys_path':sys.path}))"
        )
        run(f"imports-{mode}", [executable, "-I", "-c", probe], empty)
        for location, probe_cwd in (("outside", empty), ("checkout", ROOT)):
            for order in ("canonical-first", "legacy-first"):
                run(f"identity-{mode}-{location}-{order}",
                    [executable, "-B", inputs / "scripts/probe_hfs021a_imports.py",
                     "--root", probe_cwd, "--order", order], probe_cwd)
        legacy = run(f"legacy-cli-{mode}", [executable, "-m", "src.steel_design.run", "--help"], ROOT, expected=1)
        assert "namespace has been retired" in legacy.stderr and not legacy.stdout
        cli_outputs = []
        for label, command in (("console", [cli]), ("module", [executable, "-m", "steel_design.run"])):
            run(f"help-{mode}-{label}", [*command, "--help"], empty)
            result = run(f"external-{mode}-{label}", [*command,
                inputs / "examples/w_shape_case.json", "--sections", inputs / "data/sections.xlsx",
                "--results-dir", work / f"result-{mode}-{label}"], empty)
            assert json.loads(result.stdout)["status"] == "INCOMPLETE"
            cli_outputs.append(normalize(json.loads(result.stdout)))
        assert_json_equal(*cli_outputs, f"{mode} console/module outputs differ")
        missing = run(f"missing-default-{mode}", [cli, inputs / "examples/w_shape_case.json"], empty, expected=1)
        assert json.loads(missing.stderr)["error"]["stage"] == "load_sections"
        assert not (empty / "data").exists()

    executable = interpreters["wheel"]
    run("install-tests", [executable, "-m", "pip", "install", "-c", constraints, "pytest==9.1.1"], empty)
    run("install-editable-tests", [interpreters["editable"], "-m", "pip", "install", "-c", constraints, "pytest==9.1.1"], empty)
    run("editable-api-tests", [interpreters["editable"], "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "tests/test_hfs021a_public_api.py", f"--basetemp={work / 'tmp' / 'editable-api'}"], inputs)
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
    expected_engine = parse_json((ROOT / "docs/audit/hfs017/evidence/after/engine-results.json").read_bytes())
    assert_json_equal(parse_json((out / "engine-results.json").read_bytes()), expected_engine, "engine results changed")
    cli_out = work / "cli"
    run("cli-examples", [executable, inputs / "scripts/audit_hfs014_cli.py", inputs, cli_out], empty)
    shutil.copyfile(cli_out / "cli-examples.json", out / "cli-examples.json")
    actual_cli = parse_json((out / "cli-examples.json").read_bytes())
    assert len(actual_cli) == len(expected_cli) == 24
    assert input_proof() == provenance, "Input bytes changed during execution"
    compare_cli_records(actual_cli, expected_cli, provenance)
    # Historical references stay intact. Preserve original SVGs even on failure;
    # only the demonstrated CRLF/LF platform representation may differ.
    graph_proof = {}
    raw_cli = json.loads((out / "cli-examples.json").read_text(encoding="utf-8"))
    with (zipfile.ZipFile(ROOT / "docs/audit/hfs021/evidence/diagrams.zip") as diagrams,
          zipfile.ZipFile(out / "svg-originals.zip", "w", zipfile.ZIP_DEFLATED) as originals):
        expected_graphs = {n for n in diagrams.namelist() if n.startswith("after/")}
        for label, record in raw_cli.items():
            if record["execution"]["returncode"]:
                continue
            output = json.loads(record["execution"]["stdout"])
            for index, case in enumerate(output.get("cases", [output])):
                graph = case["artifacts"]["interaction_diagram_i5_method2_image"]
                if graph is None:
                    continue
                member = f"after/{label}/case-{index}.svg"
                data = Path(graph).read_bytes()
                reference_svg = diagrams.read(member)
                originals.writestr(f"generated/{member}", data)
                originals.writestr(f"reference/{member}", reference_svg)
                graph_proof[member] = assert_svg_equal(data, reference_svg, member)
        assert set(graph_proof) == expected_graphs
    write(out / "svg-comparison.json", graph_proof)
    write(out / "verification.json", {"accepted": True, "suites": summary,
          "examples_identical": 12, "cli_memory_scenarios_identical": 24,
          "external_work": str(work), "production_source_copied": False,
          "project_and_wheel_installs": True, "editable_install": True,
          "canonical_package": "steel_design", "external_catalog_explicit": True})
    write(out / "SHA256SUMS.json", {p.relative_to(out).as_posix(): digest(p)
          for p in sorted(out.rglob("*")) if p.is_file() and p.name != "SHA256SUMS.json"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    verify(parser.parse_args())
