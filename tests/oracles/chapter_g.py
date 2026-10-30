"""Independent Chapter G hand calculations (ANSI/AISC 360-22, a360-22w.pdf pp.16.1-75..81), LRFD.

Decimal arithmetic (50 digits); reads data/sections.xlsx with openpyxl; never imports steel_design.
Webs without stiffeners. HSS: h = hi - 2*ri (clear distance less the inside corner radius, G4).
Regenerates tests/fixtures/chapter_g/reference.json:

    python tests/oracles/chapter_g.py
"""
from decimal import Decimal as D, getcontext
import json
import re
from pathlib import Path

import openpyxl

getcontext().prec = 50
ROOT = Path(__file__).resolve().parents[2]
E = D(200000)
SHEETS = {"W": "W_IPE_HEA_HEB", "CHANNEL": "C", "RECTANGULAR_HSS": "PTE_RECT", "CIRCULAR_HSS": "PTE_RED",
          "SINGLE_ANGLE": "L", "DOUBLE_ANGLE": "2L"}
_WB = None


def row(family, name):
    global _WB
    _WB = _WB or openpyxl.load_workbook(ROOT / "data/sections.xlsx", read_only=True, data_only=True)
    rows = _WB[SHEETS[family]].iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else None for h in next(rows)]
    for values in rows:
        if values[0] is not None and str(values[0]).strip().upper() == name:
            out = {}
            for key, value in zip(header, values):
                if key and isinstance(value, (int, float)) and not isinstance(value, bool):
                    out[key] = D(repr(value))
                elif key and isinstance(value, str):
                    try:
                        out[key] = D(value)            # numbers stored as text in some sheets
                    except ArithmeticError:
                        pass
            return out
    raise KeyError(name)


def sqrt(x):
    return x.sqrt()


def cv1(htw, kv, fy):
    lim = D("1.10") * sqrt(kv * E / fy)
    return D(1) if htw <= lim else lim / htw                                    # G2-3, G2-4


def cv2(htw, kv, fy):
    root = sqrt(kv * E / fy)
    if htw <= D("1.10") * root:
        return D(1)                                                             # G2-9
    if htw <= D("1.37") * root:
        return D("1.10") * root / htw                                           # G2-10
    return D("1.51") * kv * E / (htw**2 * fy)                                   # G2-11


def i_shape(name, family, fy, axis):
    p, fy = row(family, name), D(fy)
    if axis == "x":
        if family == "W" and p["h/tw"] <= D("2.24") * sqrt(E / fy):            # G2.1(a)
            return D("0.6") * fy * p["d"] * p["tw"], D("1.00")                 # G2-1, G2-2
        return D("0.6") * fy * p["d"] * p["tw"] * cv1(p["h/tw"], D("5.34"), fy), D("0.90")
    ratio = p["bf"] / p["tf"] if family == "CHANNEL" else p["bf"] / (2 * p["tf"])
    return 2 * D("0.6") * fy * p["bf"] * p["tf"] * cv2(ratio, D("1.2"), fy), D("0.90")   # G6-1, two flanges


def rect_hss(name, fy, axis):
    p, fy = row("RECTANGULAR_HSS", name), D(fy)
    t = p["tdes"]
    h = (p["hi"] if axis == "x" else p["bi"]) - 2 * p["ri_1"]                  # G4
    return D("0.6") * fy * 2 * h * t * cv2(h / t, D(5), fy), D("0.90")         # G4-1


def round_hss(name, fy, Lv=None):
    p, fy = row("CIRCULAR_HSS", name), D(fy)
    d, t = p["OD"], p["tdes"]
    fcr = D("0.78") * E / (d / t) ** D("1.5")                                   # G5-2b
    if Lv is not None:
        fcr = max(fcr, D("1.60") * E / (sqrt(D(Lv) / d) * (d / t) ** D("1.25")))  # G5-2a
    fcr = min(fcr, D("0.6") * fy)
    return fcr * p["A"] / 2, D("0.90")                                          # G5-1


def angle(name, fy, axis):
    fy = D(fy)
    double = name.startswith("2L")
    p = row("DOUBLE_ANGLE" if double else "SINGLE_ANGLE", name)
    long_, short = max(p["d"], p["b"]), min(p["d"], p["b"])
    if double:
        suffix = re.search(r"(LLBB|SLBB)$", name)
        vertical = short if suffix and suffix[1] == "SLBB" else long_           # legs in the plane of symmetry
        horizontal = long_ if vertical == short else short
        b, n = (vertical if axis == "x" else horizontal), 2
    else:
        b, n = (long_ if axis == "x" else short), 1                              # catalog: long leg parallel to y
    t = p["t"]
    return n * D("0.6") * fy * b * t * cv2(b / t, D("1.2"), fy), D("0.90")      # G3-1


CASES = {
    "W-G2.1a": dict(kind="i", name="W24X62", family="W", fy=345, axis="x"),
    "W-G2.1b": dict(kind="i", name="W24X55", family="W", fy=345, axis="x"),
    "W-G2.1b-Cv1": dict(kind="i", name="W16X26", family="W", fy=450, axis="x"),
    "C-G2.1b": dict(kind="i", name="C15X33.9", family="CHANNEL", fy=345, axis="x"),
    "W-G6": dict(kind="i", name="W21X48", family="W", fy=345, axis="y"),
    "C-G6": dict(kind="i", name="C9X20", family="CHANNEL", fy=345, axis="y"),
    "RHSS-G4-x": dict(kind="rhss", name="PTE100X50X3MM", fy=345, axis="x"),
    "RHSS-G4-y": dict(kind="rhss", name="PTE100X50X3MM", fy=345, axis="y"),
    "RHSS-G4-slender": dict(kind="rhss", name="PTE100X40X1.5MM", fy=345, axis="x"),
    "CHSS-G5-no-Lv": dict(kind="chss", name='PTER4"X3.00MM', fy=345),
    "CHSS-G5-Lv": dict(kind="chss", name='PTER4"X3.00MM', fy=345, Lv=1000),
    "L-G3-long": dict(kind="angle", name="L5X3X1/4", fy=345, axis="x"),
    "L-G3-short": dict(kind="angle", name="L5X3X1/4", fy=345, axis="y"),
    "2L-G3-LLBB-x": dict(kind="angle", name="2L4X3-1/2X3/8LLBB", fy=345, axis="x"),
    "2L-G3-SLBB-x": dict(kind="angle", name="2L4X3-1/2X3/8SLBB", fy=345, axis="x"),
    "2L-G3-LLBB-y": dict(kind="angle", name="2L4X3-1/2X3/8LLBB", fy=345, axis="y"),
}


def build(spec):
    args = {k: v for k, v in spec.items() if k != "kind"}
    vn, phi = {"i": i_shape, "rhss": rect_hss, "chss": round_hss, "angle": angle}[spec["kind"]](**args)
    return {"spec": spec, "Vn_kN": vn / 1000, "phi_v": phi, "phiVn_kN": phi * vn / 1000}


def _plain(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


if __name__ == "__main__":
    target = ROOT / "tests/fixtures/chapter_g/reference.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": "ANSI/AISC 360-22 (a360-22w.pdf) G1-G6; catalog data/sections.xlsx",
               "generator": "tests/oracles/chapter_g.py (Decimal; independent of steel_design)",
               "cases": _plain({cid: build(spec) for cid, spec in CASES.items()})}
    target.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(target)
