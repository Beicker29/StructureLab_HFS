"""Representation-only comparison; all engineering/graphic changes must fail."""
import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from hfs021a_svg_comparison import assert_svg_equal


SVG = (b'<svg xmlns="http://www.w3.org/2000/svg" width="900">\n'
       b'<polyline points="90.00,550.00 120.25,340.50" stroke="#222"/>\n'
       b'<text x="24" y="50">Capacity 123.456 kN</text>\n</svg>')


@pytest.mark.parametrize("data", [SVG, SVG.replace(b"\n", b"\r\n")])
def test_identical_bytes(data):
    proof = assert_svg_equal(data, data, "same.svg")
    assert proof["byte_identical"] is True
    assert proof["actual"]["sha256"] == hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize("reverse", [False, True])
def test_only_crlf_lf_difference(reverse):
    crlf = SVG.replace(b"\n", b"\r\n")
    actual, expected = (SVG, crlf) if reverse else (crlf, SVG)
    proof = assert_svg_equal(actual, expected, "platform.svg")
    assert proof["byte_identical"] is False
    assert proof["actual"]["sha256"] == hashlib.sha256(actual).hexdigest()
    assert proof["expected"]["sha256"] == hashlib.sha256(expected).hexdigest()
    assert proof["normalized_sha256"] == hashlib.sha256(SVG).hexdigest()
    assert proof["actual"]["bytes"] == len(actual)
    assert proof["expected"]["bytes"] == len(expected)


@pytest.mark.parametrize("changed", [
    SVG.replace(b"120.25", b"120.26"),  # coordinate
    SVG.replace(b"123.456", b"123.457"),  # value in text
    SVG.replace(b"123.456", b"123.4560"),  # no numeric-equivalence tolerance
    SVG.replace(b"</svg>", b'<circle cx="1" cy="2"/>\n</svg>'),
    SVG.replace(b'<text x="24" y="50">Capacity 123.456 kN</text>\n', b""),
    SVG.replace(b'width="900"', b'width="901"'),
    SVG.replace(b'#222', b'#223'),
    SVG.replace(b"Capacity", b"Demand"),
    SVG.replace(b' x="24" y="50"', b' y="50" x="24"'),  # no XML canonicalization
    SVG.replace(b"\n<text", b"\n <text"),  # no whitespace stripping
    SVG.replace(b"\n", b"\r"),  # lone CR is not accepted as LF
    b"\xef\xbb\xbf" + SVG,  # no BOM/encoding normalization
])
@pytest.mark.parametrize("with_crlf", [False, True])
def test_rejects_every_other_difference(changed, with_crlf):
    if with_crlf:
        changed = changed.replace(b"\n", b"\r\n")
    with pytest.raises(AssertionError, match=r"case-7\.svg: SVG differs beyond CRLF/LF"):
        assert_svg_equal(changed, SVG, "case-7.svg")


def test_comparison_preserves_both_files(tmp_path):
    actual = tmp_path / "actual.svg"
    expected = tmp_path / "expected.svg"
    actual.write_bytes(SVG.replace(b"\n", b"\r\n"))
    expected.write_bytes(SVG)
    before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in (actual, expected)]
    assert_svg_equal(actual.read_bytes(), expected.read_bytes(), "files.svg")
    assert [(p.read_bytes(), p.stat().st_mtime_ns) for p in (actual, expected)] == before
