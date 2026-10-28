"""Exact JSON comparisons and input provenance for HFS-020 audit tools only.

Not an engine serializer. Decimal parsing preserves every input number; no
rounding, tolerances, omitted fields or OS-dependent semantic normalization.
"""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"Non-finite JSON number: {value}")


def parse_json(data):
    return json.loads(data, parse_float=Decimal, parse_int=Decimal, object_pairs_hook=_object,
                      parse_constant=_invalid_constant)


def canonical_value(value):
    """Canonical JSON text with exact numeric value, independent of formatting.

    Numbers use integer coefficient/exponent, with no Decimal context rounding.
    1 and 1.0 are equal; booleans are distinct from numbers. Preserve signed zero.
    Object order is irrelevant; array order, strings and all fields are retained.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value)) if not isinstance(value, Decimal) else value
        if not number.is_finite():
            raise ValueError("Non-finite JSON number")
        sign, digits, exponent = number.as_tuple()
        coefficient = "".join(map(str, digits))
        if not any(digits):
            return "-0" if sign else "0"
        while coefficient.endswith("0"):
            coefficient = coefficient[:-1]
            exponent += 1
        return ("-" if sign else "") + coefficient + "e" + str(exponent)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, list):
        return "[" + ",".join(canonical_value(v) for v in value) + "]"
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return "{" + ",".join(json.dumps(k, ensure_ascii=True) + ":" + canonical_value(value[k])
                              for k in sorted(value)) + "}"
    raise TypeError(f"Not a JSON value: {type(value).__name__}")


def canonical_json(data):
    return canonical_value(parse_json(data)).encode("ascii")


def assert_json_equal(actual, expected, context):
    assert canonical_value(actual) == canonical_value(expected), context


def versioned_examples(root):
    """Read tracked inputs from HEAD, never bless an arbitrary working-tree edit."""
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", "examples"],
        cwd=root, text=True, encoding="utf-8").splitlines()
    return {Path(name).name: subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=root)
            for name in names if Path(name).parent == Path("examples") and name.endswith(".json")}


def verify_input_provenance(versioned, working, executed, reference, expected_cli):
    """Link historical raw hashes -> frozen bytes -> HEAD -> copied inputs.

    The new frozen reference retains the actual Git blob text proven against
    the historical hashes. It permits later formatting changes, never new values.
    Raw hashes stay independent of the semantic hash and are all recorded.
    """
    assert set(versioned) == set(working) == set(executed) == set(reference), "Example file set changed"
    assert set(expected_cli) == {f"{name}/{mode}" for name in reference
                                 for mode in ("original", "detailed")}, "Reference CLI scenario set changed"
    proof = {}
    for name, record in reference.items():
        frozen = record["git_blob_utf8"].encode("utf-8")
        assert sha256(frozen) == record["git_blob_sha256"], (name, "reference blob integrity")
        # Bridge the legacy byte-only capture with the preserved, proven input.
        # This is not the semantic comparator: no replacement touches JSON values.
        lf = frozen.replace(b"\r\n", b"\n")
        forms = {sha256(frozen), sha256(lf), sha256(lf.replace(b"\n", b"\r\n"))}
        legacy = record["historical_source_sha256"]
        assert legacy in forms, (name, "historical hash not linked to reference bytes")
        for mode in ("original", "detailed"):
            assert expected_cli[f"{name}/{mode}"]["source_sha256"] == legacy, (name, "reference capture integrity")
        expected = canonical_json(frozen)
        for label, data in (("HEAD", versioned[name]), ("working", working[name]), ("executed", executed[name])):
            assert canonical_json(data) == expected, (name, label, "input content changed")
        assert working[name] == executed[name], (name, "copied input byte integrity")
        proof[name] = {"historical_source_sha256": legacy,
                       "reference_blob_sha256": sha256(frozen),
                       "head_blob_sha256": sha256(versioned[name]),
                       "working_sha256": sha256(working[name]),
                       "executed_sha256": sha256(executed[name]),
                       "canonical_json_sha256": sha256(expected)}
    return proof


def compare_cli_records(actual_cli, expected_cli, proof):
    assert set(actual_cli) == set(expected_cli), "CLI scenario set changed"
    for key, actual in actual_cli.items():
        expected = expected_cli[key]
        name, _ = key.split("/")
        assert set(actual) == set(expected), (key, "capture field set changed")
        assert actual["source_sha256"] == proof[name]["executed_sha256"], (key, "executed byte hash")
        assert expected["source_sha256"] == proof[name]["historical_source_sha256"], (key, "historical byte hash")
        for field in ("normalized_cli", "normalized_details", "transport_only_detailed_variant"):
            assert_json_equal(actual[field], expected[field], (key, field))
        assert_json_equal(actual["execution"]["returncode"], expected["execution"]["returncode"],
                          (key, "returncode"))
