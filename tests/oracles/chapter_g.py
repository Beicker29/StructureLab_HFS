"""Independent Chapter G hand calculations (ANSI/AISC 360-22, a360-22w.pdf pp.16.1-75..81), LRFD.

Decimal arithmetic (50 digits); reads src/steel_design/data/sections.xlsx with openpyxl; never imports steel_design.
Webs without stiffeners. HSS: h = hi - 2*ri (clear distance less the inside corner radius, G4).
Solid bars: G4 other symmetric shapes, Aw = d*t, h/t = d/t, kv = 5; round bars Aw = 0.5*Ag, Cv2 = 1
(user decision DG-4 in docs/chapter-g.md).
Regenerates tests/fixtures/chapter_g/reference.json:

    python tests/oracles/chapter_g.py
"""
import json
import re
from decimal import Decimal as D
from decimal import getcontext
from pathlib import Path

import openpyxl
from _common import _plain, sqrt

getcontext().prec = 50
ROOT = Path(__file__).resolve().parents[2]
E = D(200000)
PI = D("3.14159265358979323846264338327950288419716939937510")
SHEETS = {"W": "W_IPE_HEA_HEB", "CHANNEL": "C", "RECTANGULAR_HSS": "PTE_RECT", "CIRCULAR_HSS": "PTE_RED",
          "SINGLE_ANGLE": "L", "DOUBLE_ANGLE": "2L"}
_WB = None


def row(family, name):
    global _WB
    _WB = _WB or openpyxl.load_workbook(ROOT / "src/steel_design/data/sections.xlsx", read_only=True, data_only=True)
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
    if axis == "y_2":
        if family == "W" and p["h/tw"] <= D("2.24") * sqrt(E / fy):            # G2.1(a)
            return D("0.6") * fy * p["d"] * p["tw"], D("1.00")                 # G2-1, G2-2
        return D("0.6") * fy * p["d"] * p["tw"] * cv1(p["h/tw"], D("5.34"), fy), D("0.90")
    ratio = p["bf"] / p["tf"] if family == "CHANNEL" else p["bf"] / (2 * p["tf"])
    return 2 * D("0.6") * fy * p["bf"] * p["tf"] * cv2(ratio, D("1.2"), fy), D("0.90")   # G6-1, two flanges


def built_up_i(d, tw, plus2, minus2, fy, axis):
    """Welded I: G2.1(b) always (G2.1(a) is for rolled shapes), Aw = d*tw; G6 per flange with its own bf/2tf."""
    d, tw, fy = D(d), D(tw), D(fy)
    (bt, tt), (bb, tb) = [(D(b), D(t)) for b, t in (plus2, minus2)]
    if axis == "y_2":
        return D("0.6") * fy * d * tw * cv1((d - tt - tb) / tw, D("5.34"), fy), D("0.90")   # G2-1, G2-3/G2-4
    return sum(D("0.6") * fy * b * t * cv2(b / (2 * t), D("1.2"), fy) for b, t in ((bt, tt), (bb, tb))), D("0.90")   # G6-1


def rect_hss(name, fy, axis):
    p, fy = row("RECTANGULAR_HSS", name), D(fy)
    t = p["tdes"]
    h = (p["hi"] if axis == "y_2" else p["bi"]) - 2 * p["ri_1"]                  # G4
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
        b, n = (vertical if axis == "y_2" else horizontal), 2
    else:
        b, n = (long_ if axis == "y_2" else short), 1                              # catalog: long leg parallel to y
    t = p["t"]
    return n * D("0.6") * fy * b * t * cv2(b / t, D("1.2"), fy), D("0.90")      # G3-1


def bar(H, B, fy, axis):
    fy = D(fy)
    d, t = (D(H), D(B)) if axis == "y_2" else (D(B), D(H))                        # d parallel to the shear
    return D("0.6") * fy * d * t * cv2(d / t, D(5), fy), D("0.90")              # G4-1


def solid_round(D_, fy):
    return D("0.6") * D(fy) * (PI * D(D_) ** 2 / 4) / 2, D("0.90")              # G4-1, Aw = Ag/2, Cv2 = 1 (DG-4)


CASES = {
    "W-G2.1a": dict(kind="i", name="W24X62", family="W", fy=345, axis="y_2"),
    "W-G2.1b": dict(kind="i", name="W24X55", family="W", fy=345, axis="y_2"),
    "W-G2.1b-Cv1": dict(kind="i", name="W16X26", family="W", fy=450, axis="y_2"),
    "C-G2.1b": dict(kind="i", name="C15X33.9", family="CHANNEL", fy=345, axis="y_2"),
    "W-G6": dict(kind="i", name="W21X48", family="W", fy=345, axis="x_3"),
    "C-G6": dict(kind="i", name="C9X20", family="CHANNEL", fy=345, axis="x_3"),
    "RHSS-G4-y_2": dict(kind="rhss", name="PTE100X50X3MM", fy=345, axis="y_2"),
    "RHSS-G4-x_3": dict(kind="rhss", name="PTE100X50X3MM", fy=345, axis="x_3"),
    "RHSS-G4-slender": dict(kind="rhss", name="PTE100X40X1.5MM", fy=345, axis="y_2"),
    "CHSS-G5-no-Lv": dict(kind="chss", name='PTER4"X3.00MM', fy=345),
    "CHSS-G5-Lv": dict(kind="chss", name='PTER4"X3.00MM', fy=345, Lv=1000),
    "L-G3-long": dict(kind="angle", name="L5X3X1/4", fy=345, axis="y_2"),
    "L-G3-short": dict(kind="angle", name="L5X3X1/4", fy=345, axis="x_3"),
    "2L-G3-LLBB-y_2": dict(kind="angle", name="2L4X3-1/2X3/8LLBB", fy=345, axis="y_2"),
    "2L-G3-SLBB-y_2": dict(kind="angle", name="2L4X3-1/2X3/8SLBB", fy=345, axis="y_2"),
    "2L-G3-LLBB-x_3": dict(kind="angle", name="2L4X3-1/2X3/8LLBB", fy=345, axis="x_3"),
    "BAR-G4-y_2": dict(kind="bar", H=100, B=20, fy=345, axis="y_2"),
    "BAR-G4-x_3": dict(kind="bar", H=100, B=20, fy=345, axis="x_3"),
    "BAR-G4-G2-10": dict(kind="bar", H=650, B=10, fy=345, axis="y_2"),
    "BAR-G4-G2-11": dict(kind="bar", H=10, B=750, fy=345, axis="x_3"),
    "ROUND-G4": dict(kind="round", D_=50, fy=250),
    "BUI-G2.1b-stocky-web": dict(kind="bui", d=400, tw=12, plus2=(250, 20), minus2=(200, 16), fy=345, axis="y_2"),
    "BUI-G2.1b-Cv1": dict(kind="bui", d=1200, tw=8, plus2=(400, 20), minus2=(400, 20), fy=345, axis="y_2"),
    "BUI-G6-unequal": dict(kind="bui", d=900, tw=8, plus2=(350, 22), minus2=(600, 10), fy=345, axis="x_3"),
}


def build(spec):
    args = {k: v for k, v in spec.items() if k != "kind"}
    modes = {"i": i_shape, "rhss": rect_hss, "chss": round_hss, "angle": angle, "bar": bar, "round": solid_round, "bui": built_up_i}
    vn, phi = modes[spec["kind"]](**args)
    return {"spec": spec, "Vn_kN": vn / 1000, "phi_v": phi, "phiVn_kN": phi * vn / 1000}


if __name__ == "__main__":
    target = ROOT / "tests/fixtures/chapter_g/reference.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": "ANSI/AISC 360-22 (a360-22w.pdf) G1-G6; catalog src/steel_design/data/sections.xlsx",
               "generator": "tests/oracles/chapter_g.py (Decimal; independent of steel_design)",
               "cases": _plain({cid: build(spec) for cid, spec in CASES.items()})}
    target.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(target)
