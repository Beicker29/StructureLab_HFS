"""Catalog identity/provenance tests; no AISC capacity oracle is claimed."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import openpyxl
import pytest
from pydantic import ValidationError as PydanticValidationError

from steel_design.domain.errors import AmbiguousSectionError, ValidationError
from steel_design.engine import SteelDesignEngine
from steel_design.models import SteelCase
from steel_design.sections.identity import section_identity
from steel_design.sections.loader import load_sections_from_excel
from steel_design.sections.models import Section, SectionSource
from steel_design.sections.repository import SectionRepository

ROOT = Path(__file__).resolve().parents[1]


def case(name):
    return SteelCase(section_name=name, material={"Fy": 345, "Fu": 450}, loads={"Pu": 1},
                     lengths={"Lx": 1000, "Ly": 1000, "Lz": 1000, "Lb": 1000})


@pytest.mark.parametrize("name", ["HEA 100", "hea 100", " HeA 100 ", "HEA   100", "\thea\t100\r\n"])
def test_shared_identity_whitespace_case_and_idempotence(name):
    assert section_identity(name) == "HEA 100"
    assert section_identity(section_identity(name)) == "HEA 100"
    repo = SectionRepository()
    repo.load([Section(name=name, A=100)])
    assert repo.get("  HEA 100 ").area == 100


@pytest.mark.parametrize("other", ["HEA100", "HEA-100", "HEA_100", "HEA 100MM", "HEA 0100",
                                   "HEA\u00a0100", "HEA 100.0", "HEA 100\u2033"])
def test_no_inferred_equivalence(other):
    assert section_identity(other) != section_identity("HEA 100")
    repo = SectionRepository()
    repo.load([Section(name="HEA 100", A=100)])
    assert repo.get(other) is None


@pytest.mark.parametrize("name", [None, 10, "", " \t\r\n"])
def test_invalid_lookup_has_field_context(name):
    with pytest.raises(ValidationError) as caught:
        SectionRepository().get(name)
    assert caught.value.details["field"] == "section_name"


@pytest.mark.parametrize("second_name", ["HEA 100", "hea 100", " HEA  100\t"])
@pytest.mark.parametrize("second_area", [100, 200])
@pytest.mark.parametrize("reverse", [False, True])
def test_duplicate_selection_never_picks_first_last_or_identical(second_name, second_area, reverse):
    records = [Section(name="HEA 100", A=100), Section(name=second_name, A=second_area)]
    if reverse:
        records.reverse()
    repo = SectionRepository()
    repo.load(records + [Section(name="valid", A=500)])
    with pytest.raises(AmbiguousSectionError) as caught:
        repo.get("hea 100")
    details = caught.value.details
    assert caught.value.code == "AMBIGUOUS_SECTION"
    assert details["identity"] == "HEA 100"
    assert details["record_count"] == 2
    assert sorted(r["area"] for r in details["records"]) == sorted([100, second_area])
    assert all(r["source"] is None for r in details["records"])
    assert len(repo.get_all()) == 3
    assert len(repo.get_duplicates()["HEA 100"]) == 2
    assert repo.get("VALID").area == 500
    json.dumps(caught.value.to_dict(), allow_nan=False)


def test_additive_load_and_failed_batch_are_explicit():
    repo = SectionRepository()
    record = Section(name="unique", A=100)
    repo.load([record])
    assert repo.get("unique").area == 100
    repo.load([record])
    with pytest.raises(AmbiguousSectionError):
        repo.get("unique")
    with pytest.raises(PydanticValidationError):
        repo.load([Section(name="not-added", A=100), record.model_copy(update={"area": float("nan")})])
    assert repo.get("not-added") is None
    assert len(repo.get_all()) == 2


def test_same_identity_across_files_and_types_is_not_disambiguated():
    repo = SectionRepository()
    for index, profile in enumerate(["W", "CHANNEL"], start=1):
        repo.load([Section(name="same", type=profile, A=100, source=SectionSource(
            file=f"source-{index}.xlsx", sha256=str(index)*64, sheet="profiles", row=2,
            original_name="same"))])
    with pytest.raises(AmbiguousSectionError) as caught:
        repo.get("same")
    assert {r["source"]["file"] for r in caught.value.details["records"]} == {"source-1.xlsx", "source-2.xlsx"}
    assert {r["type"] for r in caught.value.details["records"]} == {"W", "CHANNEL"}


def test_snapshot_isolation_on_input_output_lists_and_error_details():
    repo = SectionRepository()
    source = SectionSource(file="fixture.xlsx", sha256="a" * 64, sheet="W", row=2, original_name="a")
    record = Section(name="a", A=100, source=source)
    repo.load([record])
    record.name = "b"
    record.area = 200
    record.source.row = 90
    selected = repo.get("a")
    selected.name = "c"
    selected.source.row = 91
    repo.get_all()[0].area = 500
    assert repo.get("a").area == 100
    assert repo.get("a").source.row == 2
    assert repo.get("b") is None
    repo.load([Section(name="A", A=200)])
    repo.get_duplicates()["A"][0].area = 800
    with pytest.raises(AmbiguousSectionError) as caught:
        repo.get("a")
    caught.value.details["records"][0]["source"]["row"] = 92
    assert repo.get_all()[0].source.row == 2
    assert repo.get_all()[0].area == 100


def test_loader_provenance_and_identity_shared_across_sheets(tmp_path):
    path = tmp_path / "catalog.xlsx"
    wb = openpyxl.Workbook()
    for sheet, name, area in [(wb.active, "  hea\t100 ", 100), (wb.create_sheet("second"), "HEA 100", 200)]:
        sheet.append(["shape", "A", "d"])
        sheet.append([name, area, 10])
    wb.save(path)
    wb.close()
    records = load_sections_from_excel(str(path))
    assert [r.name for r in records] == ["HEA 100", "HEA 100"]
    assert [r.source.original_name for r in records] == ["  hea\t100 ", "HEA 100"]
    assert [r.source.sheet for r in records] == ["Sheet", "second"]
    assert all(r.source.row == 2 for r in records)
    assert all(r.source.file == str(path.resolve()) for r in records)
    assert all(r.source.sha256 == hashlib.sha256(path.read_bytes()).hexdigest() for r in records)
    repo = SectionRepository()
    repo.load(records)
    with pytest.raises(AmbiguousSectionError):
        repo.get("hea 100")


@pytest.fixture(scope="module")
def real_records():
    return load_sections_from_excel(str(ROOT / "data/sections.xlsx"))


def test_real_catalog_preserves_every_record_and_recovers_unique_profiles(real_records):
    repo = SectionRepository()
    repo.load(real_records)
    assert len(real_records) == len(repo.get_all()) == 1228
    assert len({section_identity(r.name) for r in repo.get_all()}) == 1223
    assert {k: len(v) for k, v in repo.get_duplicates().items()} == {"HEA 100": 2, "PTEXXMM": 5}
    unique = [r for r in real_records if r.name not in {"HEA 100", "PTEXXMM"}]
    assert len(unique) == 1221
    for record in unique:
        assert repo.get(record.name) == record
    assert repo.get(" w12x26 ") is not None
    assert repo.get("missing") is None


@pytest.mark.parametrize("name,count,areas", [("HEA 100", 2, [2124, 2534]), ("PTEXXMM", 5, [0]*5)])
def test_real_ambiguity_prevents_engine_calculation_and_has_all_provenance(real_records, name, count, areas):
    for records in (real_records, list(reversed(real_records))):
        repo = SectionRepository()
        repo.load(records)
        with pytest.raises(AmbiguousSectionError) as caught:
            SteelDesignEngine(repo).run(case(name))
        candidates = caught.value.details["records"]
        assert len(candidates) == count
        assert sorted(r["area"] for r in candidates) == areas
        assert len({(r["source"]["sheet"], r["source"]["row"]) for r in candidates}) == count
        assert all(r["source"]["sha256"] == "5aaaf953a32e77e6d9985e9f91db82702d70b3ee0930a2eb6e695e297a5f1359" for r in candidates)


def test_hfs011_physical_invalidity_still_rejected_when_identity_is_unique(real_records):
    invalid = next(r for r in real_records if r.name == "PTEXXMM")
    repo = SectionRepository()
    repo.load([invalid, Section(name="valid", A=100, type="SOLID_RECTANGULAR", rx=10, ry=10)])
    assert repo.get("PTEXXMM").area == 0  # unique identity, still not physically usable
    with pytest.raises(ValidationError, match="zero physical"):
        SteelDesignEngine(repo).run(case("PTEXXMM"))
    assert SteelDesignEngine(repo).run(case("valid")).checks


@pytest.mark.parametrize("name", [" hea  100 ", "PTEXXMM"])
def test_cli_ambiguous_error_and_valid_profile_recovery(tmp_path, name):
    path = tmp_path / "case.json"
    path.write_text(case(name).model_dump_json(), encoding="utf-8")
    command = [sys.executable, "-m", "steel_design.run", str(path), "--results-dir", str(tmp_path / "results")]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 1 and not run.stdout
    error = json.loads(run.stderr)["error"]
    assert error["code"] == "AMBIGUOUS_SECTION"
    assert error["stage"] == "run_engine"
    assert error["details"]["records"][0]["source"]["sheet"]
    path.write_text(case("W12X26").model_dump_json(), encoding="utf-8")
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0
    assert json.loads(run.stdout)["checks"]


@pytest.mark.parametrize("update", [{"row": 0}, {"row": True}, {"sha256": "bad"}, {"sheet": ""}, {"extra": 1}])
def test_provenance_contract(update):
    with pytest.raises(PydanticValidationError):
        SectionSource(**{**dict(file="test.xlsx", sha256="0"*64, sheet="W", row=2, original_name="test"), **update})
