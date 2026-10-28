"""Audit integrity tests; no structural formula or normative expectations."""
import copy
import json

import pytest

from scripts.hfs020_comparison import (assert_json_equal, canonical_json,
                                      compare_cli_records, parse_json, sha256,
                                      verify_input_provenance)


SOURCE = b'{\n  "loads": {"Pu": 10}, "material": {"Fy": 345},\n  "geometry": {"A": 100}, "design_method": "LRFD"\n}\n'


def setup_records(data=SOURCE):
    legacy = sha256(SOURCE.replace(b"\n", b"\r\n"))
    reference = {"case.json": {"git_blob_utf8": SOURCE.decode(),
                              "git_blob_sha256": sha256(SOURCE), "historical_source_sha256": legacy}}
    expected = {}
    for mode in ("original", "detailed"):
        expected[f"case.json/{mode}"] = {
            "source_sha256": legacy, "transport_only_detailed_variant": mode == "detailed",
            "execution": {"returncode": 0},
            "normalized_cli": {"status": "INCOMPLETE", "coverage": {"complete": False},
                               "checks": [{"capacity": 100.125, "demand": 10, "dcr": .1}]},
            "normalized_details": [{"nominal": 125, "trace": {"method": "LRFD", "factor": .9}}],
        }
    actual = copy.deepcopy(expected)
    for record in actual.values():
        record["source_sha256"] = sha256(data)
    return reference, expected, actual


def proof_for(data=SOURCE):
    reference, expected, actual = setup_records(data)
    proof = verify_input_provenance({"case.json": SOURCE}, {"case.json": data},
                                    {"case.json": data}, reference, expected)
    return expected, actual, proof


@pytest.mark.parametrize("data", [SOURCE, SOURCE.replace(b"\n", b"\r\n"),
    json.dumps(json.loads(SOURCE), separators=(",", ":"), sort_keys=True).encode(),
    SOURCE.replace(b'"Pu": 10', b'"Pu": 1.000e1')])
def test_line_endings_and_format_preserve_semantics_and_raw_hashes(data):
    assert canonical_json(SOURCE) == canonical_json(data)
    expected, actual, proof = proof_for(data)
    compare_cli_records(actual, expected, proof)
    assert proof["case.json"]["executed_sha256"] == sha256(data)
    assert expected["case.json/original"]["source_sha256"] == sha256(SOURCE.replace(b"\n", b"\r\n"))


@pytest.mark.parametrize("old,new", [(b'"Pu": 10', b'"Pu": 11'), (b'"Fy": 345', b'"Fy": 346'),
                                    (b'"A": 100', b'"A": 101'), (b'"LRFD"', b'"ASD"')])
@pytest.mark.parametrize("location", ["HEAD", "working", "executed", "all"])
def test_input_mutations_rejected_even_if_versioned(old, new, location):
    changed = SOURCE.replace(old, new)
    reference, expected, _ = setup_records()
    data = [{"case.json": SOURCE} for _ in range(3)]
    for index, label in enumerate(("HEAD", "working", "executed")):
        if location in {label, "all"}:
            data[index]["case.json"] = changed
    with pytest.raises(AssertionError, match="input content changed"):
        verify_input_provenance(*data, reference, expected)


@pytest.mark.parametrize("field", ["git_blob_utf8", "git_blob_sha256", "historical_source_sha256"])
def test_reference_integrity_is_not_bypassed(field):
    reference, expected, _ = setup_records()
    reference["case.json"][field] += "x"
    with pytest.raises(AssertionError):
        verify_input_provenance(*[{"case.json": SOURCE}] * 3, reference, expected)


def test_copied_input_must_remain_byte_identical_to_working_input():
    reference, expected, _ = setup_records()
    with pytest.raises(AssertionError, match="copied input byte integrity"):
        verify_input_provenance({"case.json": SOURCE}, {"case.json": SOURCE},
                                {"case.json": SOURCE.replace(b"\n", b"\r\n")}, reference, expected)


@pytest.mark.parametrize("field", ["capacity", "demand", "dcr"])
def test_resistant_output_mutation_rejected(field):
    expected, actual, proof = proof_for()
    actual["case.json/original"]["normalized_cli"]["checks"][0][field] += 1e-10
    with pytest.raises(AssertionError, match="normalized_cli"):
        compare_cli_records(actual, expected, proof)


@pytest.mark.parametrize("field,value", [("status", "PASS"), ("status", "FAIL"),
    ("coverage", {"complete": True}), ("coverage", {"complete": False, "obligation": "EVALUATED"})])
def test_status_or_coverage_mutation_rejected(field, value):
    expected, actual, proof = proof_for()
    actual["case.json/original"]["normalized_cli"][field] = value
    with pytest.raises(AssertionError, match="normalized_cli"):
        compare_cli_records(actual, expected, proof)


@pytest.mark.parametrize("target", ["nominal", "trace", "exit", "raw_hash", "variant", "scenario", "field"])
def test_memory_trace_exit_hash_and_capture_changes_rejected(target):
    expected, actual, proof = proof_for()
    record = actual["case.json/detailed"]
    if target == "nominal":
        record["normalized_details"][0]["nominal"] += 1
    elif target == "trace":
        record["normalized_details"][0]["trace"]["method"] = "ASD"
    elif target == "exit":
        record["execution"]["returncode"] = 1
    elif target == "raw_hash":
        record["source_sha256"] = "0" * 64
    elif target == "variant":
        record["transport_only_detailed_variant"] = False
    elif target == "scenario":
        del actual["case.json/original"]
    else:
        record["new_field"] = 1
    with pytest.raises(AssertionError):
        compare_cli_records(actual, expected, proof)


@pytest.mark.parametrize("left,right", [
    (b'{"v":1.0000000000000000000000000000000000001}', b'{"v":1}'),
    (b'{"v":9007199254740993}', b'{"v":9007199254740992}'),
    (b'{"v":1e-400}', b'{"v":0}'),
    (b'{"v":true}', b'{"v":1}'),
    (b'{"v":false}', b'{"v":0}'),
    (b'{"v":-0}', b'{"v":0}'),
    (b'{"v":[1,2]}', b'{"v":[2,1]}'),
    (b'{"v":"a\\r\\nb"}', b'{"v":"a\\nb"}'),
])
def test_no_float_rounding_type_coercion_or_value_normalization(left, right):
    assert canonical_json(left) != canonical_json(right)
    with pytest.raises(AssertionError):
        assert_json_equal(parse_json(left), parse_json(right), "different")


@pytest.mark.parametrize("data", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":-Infinity}'])
def test_ambiguous_or_nonfinite_json_rejected(data):
    with pytest.raises(ValueError):
        canonical_json(data)
