"""Registry integrity and protected software behavior, NOT normative oracles.

The fixture freezes pre-HFS-023 bindings only. It is not an independent source
of expected applicability; HFS-002 remains independently authored.
"""
from dataclasses import replace
import inspect
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from steel_design.domain.routing import registry_metadata as metadata
from steel_design.domain.routing.profile_router import RULE_DEFINITIONS, PROFILE_RULE_MAP
from steel_design.domain.rules import composite_rules, flexure_rule, shear_rules
from scripts.audit_hfs023 import (symbol, resolve_reference, validate_references,
                                 validate_test_reference, render_index)

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / "tests/fixtures/hfs023/runtime-registry.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("key", sorted(BASE["rules"].keys() - {"I2"}))
def test_original_binding_predicate_and_required_fields_are_unchanged(key):
    definition = RULE_DEFINITIONS[key]
    observed = dict(rule_id=definition.rule_id, implementation=symbol(definition.rule_class),
                    implemented=definition.implemented, fields=list(definition.required_section_fields),
                    applicability=symbol(definition.applicability))
    assert observed == BASE["rules"][key]


def test_unused_i2_placeholder_retains_id_without_a_dead_predicate():
    from steel_design.domain.routing import profile_router
    assert BASE["rules"]["I2"]["applicability"].endswith(":_has_interaction")
    assert "I2" not in {key for ids in PROFILE_RULE_MAP.values() for key in ids}
    assert RULE_DEFINITIONS["I2"].rule_class is None
    assert RULE_DEFINITIONS["I2"].applicability is None
    assert not hasattr(profile_router, "_has_interaction")


def test_profile_routes_are_exactly_frozen_and_new_records_cannot_be_selected():
    assert PROFILE_RULE_MAP == BASE["profiles"]
    assert {key for ids in PROFILE_RULE_MAP.values() for key in ids} <= BASE["rules"].keys()
    for key in RULE_DEFINITIONS.keys() - BASE["rules"].keys():
        assert RULE_DEFINITIONS[key].applicability is None


@pytest.mark.parametrize("key", sorted(RULE_DEFINITIONS))
def test_each_record_has_resolvable_references_and_coherent_owner(key):
    definition = RULE_DEFINITIONS[key]
    assert key == definition.rule_id
    metadata.validate_registry([definition], {})
    validate_references(ROOT, [definition])


def test_unique_ids_and_all_independent_matrix_rows_are_indexed():
    metadata.validate_registry(RULE_DEFINITIONS.values(), PROFILE_RULE_MAP)
    ids = [d.rule_id for d in RULE_DEFINITIONS.values()]
    assert len(ids) == len(set(ids))
    # This is a documentary index completeness assertion, NOT case applicability.
    assert {n for d in RULE_DEFINITIONS.values() for n in d.metadata.matrix_ids} == {f"N{i:02}" for i in range(1,46)}


def test_all_procedural_composite_rules_have_exactly_one_descriptive_entry():
    existing = {c for _, c in inspect.getmembers(composite_rules, inspect.isclass)
                if c.__module__ == composite_rules.__name__ and hasattr(c, "check")}
    descriptions = [d.rule_class for d in RULE_DEFINITIONS.values() if d.rule_class in existing]
    assert len(descriptions) == len(existing) == len(set(descriptions))
    assert set(descriptions) == existing


def test_inherited_axis_implementations_and_compatibility_classes_remain_traceable():
    registered = {d.rule_class for d in RULE_DEFINITIONS.values() if d.rule_class}
    for module in (flexure_rule, shear_rules):
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ == module.__name__ and hasattr(cls, "check"):
                assert any(issubclass(cls, c) or issubclass(c, cls) for c in registered)
                assert cls.check.__module__.startswith("steel_design.")


@pytest.mark.parametrize("field", ["citations", "matrix_ids", "family_scope", "conditions", "equation_note",
                                  "implementation_state", "software_verification", "software_tests",
                                  "independent_tests", "independent_scope", "limitations", "findings",
                                  "calculation_refs", "selection_ref", "method_note"])
def test_incomplete_metadata_rejected(field):
    data = RULE_DEFINITIONS["D2-1"].metadata.model_dump()
    del data[field]
    with pytest.raises(ValidationError):
        metadata.RuleMetadata.model_validate(data)


@pytest.mark.parametrize("field,value", [("family_scope", " "), ("conditions", ""), ("citations", ()),
    ("matrix_ids", ()), ("findings", (" ",)), ("software_tests", ("",)), ("normative_validation", "VALIDATED"),
    ("software_verification", "PASSED_THEREFORE_ACCREDITED"), ("independent_scope", " ")])
def test_invalid_or_unjustified_metadata_is_rejected(field, value):
    data = RULE_DEFINITIONS["D2-1"].metadata.model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        metadata.RuleMetadata.model_validate(data)


@pytest.mark.parametrize("field,value", [("edition", "ANSI/AISC 360-16"), ("chapter", "Z"),
    ("source", "UNVERIFIED_INTERNET"), ("provision", " "), ("equations", (" ",)), ("pdf_pages", "")])
def test_incomplete_or_wrong_source_rejected(field, value):
    data = RULE_DEFINITIONS["D2-1"].metadata.citations[0].model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        metadata.Citation.model_validate(data)


@pytest.mark.parametrize("mutation", ["duplicate", "missing_metadata", "wrong_flag", "no_check", "bad_predicate",
                                     "routed_description", "missing_implementation", "wrong_state"])
def test_registry_corruption_is_detected(mutation):
    definition = RULE_DEFINITIONS["D2-1"]
    definitions, profiles = [definition], {}
    if mutation == "duplicate":
        definitions.append(definition)
    elif mutation == "missing_metadata":
        definitions = [replace(definition, metadata=None)]
    elif mutation == "wrong_flag":
        definitions = [replace(definition, implemented=False)]
    elif mutation == "no_check":
        definitions = [replace(definition, rule_class=object)]
    elif mutation == "bad_predicate":
        definitions = [replace(definition, applicability="fallback")]
    elif mutation == "routed_description":
        definitions = [replace(definition, applicability=None)]
        profiles = {"W": [definition.rule_id]}
    elif mutation == "missing_implementation":
        definitions = [replace(definition, rule_class=None, implemented=False)]
    else:
        definitions = [replace(definition, metadata=definition.metadata.model_copy(update={"implementation_state": "NOT_IMPLEMENTED"}))]
    with pytest.raises((ValueError, ValidationError)):
        metadata.validate_registry(definitions, profiles)


def test_unknown_profile_reference_rejected():
    with pytest.raises(ValueError, match="unknown routed ID"):
        metadata.validate_registry(RULE_DEFINITIONS.values(), {"W": ["unknown"]})


@pytest.mark.parametrize("invalid", ["", " ", " D2-1", "D2-1 "])
def test_blank_or_padded_rule_identity_rejected(invalid):
    with pytest.raises(ValueError, match="rule ID"):
        metadata.validate_registry([replace(RULE_DEFINITIONS["D2-1"], rule_id=invalid)], {})


def test_duplicate_or_missing_annotation_rejected(monkeypatch):
    original = metadata.metadata_groups
    monkeypatch.setattr(metadata, "metadata_groups", lambda: [*original(), next(original())])
    with pytest.raises(ValueError, match="Duplicate metadata ID"):
        metadata.attach_metadata(RULE_DEFINITIONS)
    monkeypatch.setattr(metadata, "metadata_groups", lambda: list(original())[1:])
    with pytest.raises(ValueError, match="Incomplete registry"):
        metadata.attach_metadata(RULE_DEFINITIONS)


@pytest.mark.parametrize("field,value", [("matrix_ids", ("N99",)), ("findings", ("F-999",)),
    ("calculation_refs", ("steel_design.codes.aisc_360_22.tension_calc:missing",)),
    ("selection_ref", "src.steel_design.domain.routing.profile_router:ProfileRouter.get_rules"),
    ("software_tests", ("tests/test_does_not_exist.py",)),
    ("independent_tests", ("tests/test_hfs010_coverage.py::does_not_exist",))])
def test_broken_traceability_is_detected(field, value):
    definition = RULE_DEFINITIONS["D2-1"]
    broken = replace(definition, metadata=definition.metadata.model_copy(update={field: value}))
    with pytest.raises(ValueError):
        validate_references(ROOT, [broken])


def test_cross_chapter_owner_mismatch_detected():
    wrong = replace(RULE_DEFINITIONS["D2-1"], rule_class=RULE_DEFINITIONS["E3"].rule_class)
    with pytest.raises(ValueError, match="owner conflict"):
        validate_references(ROOT, [wrong])


def test_no_software_reference_can_implicitly_accredit_a_rule():
    definition = RULE_DEFINITIONS["D2-1"]
    data = definition.metadata.model_dump()
    data["independent_tests"] += ("tests/test_hfs013_directional_h3.py::test_g4_independent_capacity_and_method",)
    assert metadata.RuleMetadata.model_validate(data).normative_validation == "NOT_ACCREDITED"
    data["software_tests"] = ()
    with pytest.raises(ValidationError, match="software_verification"):
        metadata.RuleMetadata.model_validate(data)


def test_annotations_and_citations_are_immutable():
    data = RULE_DEFINITIONS["D2-1"].metadata
    with pytest.raises(ValidationError, match="frozen"):
        data.conditions = "changed"
    with pytest.raises(ValidationError, match="frozen"):
        data.citations[0].provision = "changed"


def test_generated_index_matches_registry_without_regenerating_requirements():
    assert (ROOT / "docs/aisc_360_22_traceability.md").read_text(encoding="utf-8") == render_index()


def test_contract_import_does_not_load_registry_or_router_in_fresh_process():
    code = ("import sys; import steel_design.contracts; "
            "assert 'steel_design.domain.routing.profile_router' not in sys.modules; "
            "assert 'steel_design.domain.routing.registry_metadata' not in sys.modules")
    result = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_reference_resolver_rejects_legacy_import_and_non_test_paths():
    with pytest.raises(ValueError, match="Noncanonical"):
        resolve_reference("src.steel_design.models:SteelCase")
    with pytest.raises(ValueError, match="non-test"):
        validate_test_reference(ROOT, "scripts/audit_baseline.py")
