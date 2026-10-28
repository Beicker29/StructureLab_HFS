"""Compare SVG bytes allowing only the demonstrated Windows/Linux CRLF/LF difference.

This audit utility does not parse/reserialize XML, round numbers, strip whitespace,
or write files. Original hashes always describe original bytes, never normalized data.
"""
import hashlib


def assert_svg_equal(actual: bytes, expected: bytes, context: str) -> dict:
    """Require byte equality after CRLF -> LF only; retain original-byte evidence."""
    normalized_actual = actual.replace(b"\r\n", b"\n")
    normalized_expected = expected.replace(b"\r\n", b"\n")
    assert normalized_actual == normalized_expected, f"{context}: SVG differs beyond CRLF/LF"

    def evidence(data):
        crlf = data.count(b"\r\n")
        return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "crlf": crlf, "bare_lf": data.count(b"\n") - crlf,
                "bare_cr": data.count(b"\r") - crlf}

    return {"policy": "CRLF_to_LF_only", "byte_identical": actual == expected,
            "actual": evidence(actual), "expected": evidence(expected),
            "normalized_sha256": hashlib.sha256(normalized_actual).hexdigest()}
