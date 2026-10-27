"""HFS-011 contract tests, not independent AISC capacity validation."""
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from src.steel_design import models as m
from src.steel_design.domain.errors import CatalogSchemaError, SteelDesignError
from src.steel_design.domain.validation import validate_case, validate_section, validate_case_section
from src.steel_design.engine import SteelDesignEngine
from src.steel_design.run import OutputOptions, _extract_output_options, _unique_json_object
from src.steel_design.sections.loader import _coerce_float, _scaled_float
from src.steel_design.sections.models import Section
from src.steel_design.sections.repository import SectionRepository


ROOT = Path(__file__).resolve().parents[1]
CASE = dict(section_name="solid", material=dict(Fy=345, Fu=450), loads=dict(Pu=1),
            lengths=dict(Lx=1000, Ly=1000, Lz=1000, Lb=1000),
            custom_section=dict(type="SOLID_RECTANGULAR", B=100, H=200))
# Explicit valid representatives for every input model, including nested lists.
SAMPLES = {
    m.Material: dict(Fy=345, Fu=450),
    m.Loads: dict(Pu=1),
    m.Lengths: dict(Lx=1000, Ly=1000, Lz=1000, Lb=1000),
    m.CustomSection: dict(type="SOLID_RECTANGULAR", B=100, H=200),
    m.CompositeConcrete: dict(fc=28, wc=2400),
    m.CompositeLongitudinalBar: dict(count=2, db=16, fy=420, x=-10, y=0),
    m.CompositeTransverseReinforcement: dict(db=10, spacing=100, fy=420, type="ties"),
    m.CompositeReinforcement: {},
    m.CompositeGeometry: {},
    m.CompositeAnchorGroup: dict(type="STUD", count=2, d=19, Fu=450, Rg=1, Rp=.75),
    m.CompositeAnchors: {},
    m.CompositeI5Config: {},
    m.CompositeConfig: dict(role="FILLED_MEMBER", nominal_strength_method="PLASTIC",
                            concrete=dict(fc=28, wc=2400)),
    m.Connection: {},
    m.Factors: {},
    m.SteelCase: CASE,
    Section: dict(name="test", A=100),
    OutputOptions: {},
}


@pytest.mark.parametrize("model", SAMPLES, ids=lambda model: model.__name__)
def test_all_input_models_reject_unknown_fields(model):
    with pytest.raises(ValidationError) as caught:
        model.model_validate({**SAMPLES[model], "unknown_input": 10})
    assert any(e["loc"] == ("unknown_input",) and e["type"] == "extra_forbidden"
               for e in caught.value.errors())


# Probe every numerical field, including optional/inactive ones: input validation
# must not depend on whether a load later activates a particular check.
NUMERIC_FIELDS = [(model, name) for model in SAMPLES for name, field in model.model_fields.items()
                  if "float" in str(field.annotation) or "int" in str(field.annotation)
                  and "str" not in str(field.annotation)]


@pytest.mark.parametrize("model,name", NUMERIC_FIELDS, ids=[f"{c.__name__}.{n}" for c, n in NUMERIC_FIELDS])
@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf"), True, "NaN", "12"])
def test_every_numeric_input_rejects_nonfinite_and_ambiguous_types(model, name, invalid):
    payload = {**SAMPLES[model], model.model_fields[name].alias or name: invalid}
    with pytest.raises(ValidationError) as caught:
        model.model_validate(payload)
    field = model.model_fields[name]
    assert any(e["loc"] == (field.alias or name,) for e in caught.value.errors())


@pytest.mark.parametrize("model,field,value", [
    (m.Material, "Fy", 0), (m.Material, "Fu", -1), (m.Material, "E", 0),
    (m.Lengths, "Lb", 0), (m.Lengths, "Lz", -1),
    (m.Factors, "Kx", 0), (m.Factors, "Cb", -1), (m.Factors, "xa", -1),
    (m.Connection, "An", 0), (m.Connection, "U", 0), (m.Connection, "U", 1.01),
    (m.CustomSection, "B", 0), (m.CompositeGeometry, "cover", 0),
    (m.CompositeGeometry, "slab_thickness", -1), (m.CompositeConcrete, "fc", 0),
    (m.CompositeLongitudinalBar, "count", 1.5), (m.CompositeAnchorGroup, "count", 0),
    (m.CompositeAnchorGroup, "Rg", 1.01), (m.CompositeAnchorGroup, "Rp", 0),
    (m.CompositeI5Config, "method2_pc_ratio", 1),
    (m.CompositeI5Config, "method2_mc_ratio", 0), (Section, "Ix", -1),
])
def test_local_domains(model, field, value):
    with pytest.raises(ValidationError):
        model.model_validate({**SAMPLES[model], field: value})


def test_strength_order_and_required_dimensions():
    with pytest.raises(ValidationError, match="Fu.*Fy"):
        m.Material(Fy=450, Fu=345)
    for payload in [dict(type="SOLID_CIRCULAR"), dict(type="SOLID_RECTANGULAR", B=10),
                    dict(type="SOLID_CIRCULAR", diameter=10, B=10)]:
        with pytest.raises(ValidationError):
            m.CustomSection(**payload)


def test_absent_loads_differ_from_explicit_zero_and_sparse_contract():
    with pytest.raises(ValidationError, match="declare at least one"):
        m.Loads()
    loads = m.Loads(Pu=0)
    assert loads.model_fields_set == {"Pu"}
    assert loads.Mux == loads.Muy == loads.Vu == 0
    assert loads.model_dump(exclude_unset=True) == {"Pu": 0}
    # Zero-load aggregation is HFS-010, not a claim of structural compliance here.


@pytest.mark.parametrize("values", [dict(Vu=99, Vux=3, Vuy=4), dict(Vu=5, Vux=3, Vuy=4),
                                    dict(Vu=-3, Vux=-3), dict(Vu=1, Vuy=-1)])
def test_nonzero_mixed_shear_rejected_even_if_resultant_would_match(values):
    with pytest.raises(ValidationError, match="No resultant"):
        m.Loads(**values)


@pytest.mark.parametrize("values", [dict(Vux=3, Vuy=4), dict(Vu=0, Vux=-3, Vuy=4),
                                    dict(Vu=-9), dict(Vu=9, Vux=0, Vuy=0)])
def test_shear_retains_components_signs_and_roundtrips(values):
    loads = m.Loads(**values)
    for key, value in values.items():
        assert getattr(loads, key) == value
    assert m.Loads.model_validate_json(loads.model_dump_json()) == loads
    if "Vu" not in values:
        assert loads.Vu == 0


def test_all_lengths_required_and_no_zero_for_unbraced_length():
    for name in m.Lengths.model_fields:
        payload = dict(SAMPLES[m.Lengths])
        payload.pop(name)
        with pytest.raises(ValidationError) as caught:
            m.Lengths(**payload)
        assert caught.value.errors()[0]["loc"] == (name,)


@pytest.mark.parametrize("field", ["d", "Fu", "Rg", "Rp"])
def test_stud_data_not_inferred(field):
    payload = dict(SAMPLES[m.CompositeAnchorGroup])
    payload.pop(field)
    with pytest.raises(ValidationError, match=field):
        m.CompositeAnchorGroup(**payload)


def test_nested_index_and_unknown_load_location():
    payload = {**SAMPLES[m.CompositeConfig], "anchors": {"groups": [
        {**SAMPLES[m.CompositeAnchorGroup], "Rgg": 1}]}}
    with pytest.raises(ValidationError) as caught:
        m.CompositeConfig(**payload)
    assert caught.value.errors()[0]["loc"] == ("anchors", "groups", 0, "Rgg")
    with pytest.raises(ValidationError) as caught:
        m.SteelCase(**{**CASE, "loads": {"Mxu": 1000000}})
    assert caught.value.errors()[0]["loc"] == ("loads", "Mxu")


@pytest.mark.parametrize("method,loads,accepted", [
    ("LRFD", {"Pu": 1}, True), ("ASD", {"Pu": 1}, True),
    ("ASD", {"Mux": 1}, False), ("ASD", {"Pu": -1}, True),
])
def test_design_method_scope_not_extended(method, loads, accepted):
    case = m.SteelCase(**{**CASE, "design_method": method, "loads": loads,
                          "connection": {"An": 100, "U": 1}})
    if accepted:
        validate_case(case)
    else:
        with pytest.raises(SteelDesignError, match="only for LRFD"):
            validate_case(case)


def test_engine_revalidates_mutations_and_unsafe_copy():
    engine = SteelDesignEngine(SectionRepository())
    case = m.SteelCase(**CASE)
    case.loads.Pu = float("nan")
    with pytest.raises(SteelDesignError) as caught:
        engine.run(case)
    assert caught.value.details["fields"][0]["loc"] == ("loads", "Pu")
    case = m.SteelCase(**CASE).model_copy(update={"lengths": {"Lx": 0}})
    with pytest.raises(SteelDesignError):
        engine.run(case)


@pytest.mark.parametrize("properties", [dict(A=0), dict(A=10, rx=0), dict(A=10, H=1.1),
                                        dict(A=10, OD=10, tdes=5), dict(A=10, d=10, tf=5)])
def test_invalid_selected_physical_section(properties):
    section = Section(name="bad", **properties)
    with pytest.raises(SteelDesignError):
        validate_section(section)


def test_selected_section_defends_against_bypass_and_preserves_meaningful_zero():
    section = Section(name="ok", A=100, Cw=0, x=-1, y=0)
    assert validate_section(section).cw == 0
    with pytest.raises(SteelDesignError):
        validate_section(section.model_copy(update={"ix": float("nan")}))


@pytest.mark.parametrize("name", [name for name in Section.model_fields
                                 if name not in {"name", "type", "x", "y", "eo", "tan_alpha"}])
def test_all_unsigned_section_properties_reject_negative(name):
    field = Section.model_fields[name]
    with pytest.raises(ValidationError):
        Section(**{"name": "test", "A": 100, field.alias or name: -1})


def test_composite_conditional_inputs_and_deck_absence():
    payload = json.loads((ROOT / "examples/composite_encased_case.json").read_text(encoding="utf-8"))
    payload.pop("output")
    for field in ("B", "H", "cover"):
        bad = json.loads(json.dumps(payload))
        del bad["composite"]["geometry"][field]
        with pytest.raises(SteelDesignError) as caught:
            validate_case(m.SteelCase(**bad))
        assert caught.value.details["required_field"] == f"composite.geometry.{field}"
    bad = json.loads(json.dumps(payload))
    bad["composite"]["reinforcement"]["longitudinal_bars"][0]["x"] = 10000
    with pytest.raises(SteelDesignError, match="envelope"):
        validate_case(m.SteelCase(**bad))
    payload = json.loads((ROOT / "examples/composite_beam_case.json").read_text(encoding="utf-8"))
    payload.pop("output")
    del payload["composite"]["geometry"]["deck_present"]
    with pytest.raises(SteelDesignError, match="deck_present"):
        validate_case(m.SteelCase(**payload))
    payload["composite"]["geometry"]["deck_present"] = False
    assert validate_case(m.SteelCase(**payload)).composite.geometry.deck_present is False


def test_composite_section_data_cannot_fall_back_to_zero():
    case = m.SteelCase(**{**CASE, "composite": SAMPLES[m.CompositeConfig]})
    with pytest.raises(SteelDesignError) as caught:
        validate_case_section(case, Section(name="missing", type="CIRCULAR_HSS", A=100))
    assert set(caught.value.details["missing_fields"]) == {"ix", "iy", "rx", "ry"}


def test_net_area_bound_and_custom_overflow():
    case = m.SteelCase(**{**CASE, "connection": {"An": 200, "U": .1}})
    with pytest.raises(SteelDesignError, match="Net area"):
        validate_case_section(case, Section(name="test", A=100))
    case = m.SteelCase(**{**CASE, "custom_section": {"type": "SOLID_CIRCULAR", "diameter": 1e308}})
    with pytest.raises(SteelDesignError, match="floating-point"):
        SteelDesignEngine(SectionRepository()).run(case)


@pytest.mark.parametrize("output", [{"write_results_json": "false"}, {"save_reslts_json": False},
                                     {"write_results_json": False, "save_results_json": True}, None, []])
def test_output_options_do_not_silently_coerce_or_ignore(output):
    with pytest.raises(ValidationError):
        _extract_output_options({"output": output})


def test_output_legacy_aliases_and_duplicate_json():
    for name in ("write_results_json", "write_detailed_json", "save_results_json"):
        assert _extract_output_options({"output": {name: False}})[1] == {"write_results_json": False}
    with pytest.raises(ValueError, match="Duplicate JSON field 'Pu'"):
        json.loads('{"loads":{"Pu":1,"Pu":2}}', object_pairs_hook=_unique_json_object)


@pytest.mark.parametrize("value", ["NaN", "inf", "-inf", float("nan"), float("inf"), True])
def test_catalog_parser_nonfinite_controlled_context(value):
    with pytest.raises(CatalogSchemaError) as caught:
        _coerce_float(value, section_name="bad", field_name="area", row_number=2, required=True)
    assert caught.value.details["field"] == "area"
    assert caught.value.details["row_number"] == 2
    json.dumps(caught.value.to_dict(), allow_nan=False)


def test_catalog_scaling_overflow_controlled():
    with pytest.raises(CatalogSchemaError, match="finite"):
        _scaled_float((1e308,), column_index=0, section_name="bad", field_name="ix",
                      row_number=2, required=True, source_header="Ix")


@pytest.mark.parametrize("loads", [{"Mxu": 1}, {"Pu": "NaN"}, {"Pu": float("inf")},
                                  {"Vu": 99, "Vux": 3}, {}])
def test_cli_errors_have_field_location_and_reason(tmp_path, loads):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({**CASE, "loads": loads}), encoding="utf-8")
    completed = subprocess.run([sys.executable, "-m", "src.steel_design.run", str(path),
                                "--results-dir", str(tmp_path / "results")], cwd=ROOT,
                               capture_output=True, text=True)
    assert completed.returncode == 1
    assert not completed.stdout
    error = json.loads(completed.stderr)["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["fields"][0]["loc"][0] == "loads"
    assert error["details"]["fields"][0]["msg"]
    assert error["details"]["fields"][0]["type"]
