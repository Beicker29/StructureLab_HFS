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


def tee_plastic_moment(bf, tf, tw, de, fy):
    """Mpf (G2.3): flange bf x tf with a web stem tw x de, one yield stress, about the axis parallel to the flange."""
    area = bf * tf + tw * de
    if area / 2 <= bf * tf:                                     # plastic neutral axis in the flange, y from its free face
        y = area / 2 / bf
        return fy * (bf * y**2 / 2 + bf * (tf - y) ** 2 / 2 + tw * de * (tf - y + de / 2))
    y = tf + (area / 2 - bf * tf) / tw                          # in the stem
    return fy * (bf * tf * (y - tf / 2) + tw * (y - tf) ** 2 / 2 + tw * (tf + de - y) ** 2 / 2)


def stiffener_plastic_moment(width, tst, fyst, tw, fyw, e, de):
    """Mpst (G2.3, Fig. C-G2.3): web strip [0, e + de] (tw, Fyw) and stiffener plates [e - tst, e] (width, Fyst), measured from
    the end of the beam; the axis balances the forces (bisection)."""
    pieces = [(D(0), e + de, tw * fyw), (e - tst, e, width * fyst)]

    def force(s):                                               # force between the end of the beam and s
        return sum(rate * max(min(s, s1) - s0, D(0)) for s0, s1, rate in pieces)

    total = force(e + de)
    lo, hi = D(0), e + de
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if force(mid) < total / 2 else (lo, mid)
    sp = (lo + hi) / 2
    moment = D(0)
    for s0, s1, rate in pieces:
        for a, b in ((s0, min(s1, sp)), (max(s0, sp), s1)):
            if b > a:
                moment += rate * (b - a) * abs((a + b) / 2 - sp)
    return moment


def stiffened_web(fy, d, tw, h, flanges, a, panel, stiff, fyst, rolled_ok=False, end=None):
    """G2.1 with kv of G2-5 and, with a/h <= 3, the tension field of G2.2 (interior) or G2.3 (end); the larger Vn governs."""
    fy, d, tw, h, a, fyst = D(fy), D(d), D(tw), D(h), D(a), D(fyst)
    aw, ah, htw = d * tw, a / h, h / tw
    kv = D(5) + 5 / ah**2 if ah <= 3 else D("5.34")            # G2-5
    out = {"kv": kv}
    vn = D("0.6") * fy * aw * cv1(htw, kv, fy)                  # G2-1 with G2-3/G2-4
    out["Vn_G2_1"] = vn
    if ah <= 3:
        c2 = cv2(htw, kv, fy)
        (b1, t1), (b2, t2) = [(D(b), D(t)) for b, t in flanges]
        if panel == "interior":
            if htw <= D("1.10") * sqrt(kv * E / fy):
                tf_vn = D("0.6") * fy * aw                            # G2-6
            elif 2 * aw / (b1 * t1 + b2 * t2) <= D("2.5") and h / b1 <= 6 and h / b2 <= 6:
                tf_vn = D("0.6") * fy * aw * (c2 + (1 - c2) / (D("1.15") * sqrt(1 + ah**2)))            # G2-7
            else:
                tf_vn = D("0.6") * fy * aw * (c2 + (1 - c2) / (D("1.15") * (ah + sqrt(1 + ah**2))))     # G2-8
        else:
            de = 35 * tw * (D("0.8") - c2) ** 2 if c2 <= D("0.8") else D(0)                            # G2-14, G2-15
            width = (2 if end["arrangement"] == "pair" else 1) * D(end["b"])
            e = min(D(end["e"]), D("0.84") * tw * sqrt(E / fy))
            mpf = tee_plastic_moment(b1, t1, tw, de, fy)
            mpst = stiffener_plastic_moment(width, D(end["t"]), fyst, tw, fy, e, de)
            mpm = min(mpf, mpst)
            beta = min(D("2.8") * (sqrt(mpf + mpm) + sqrt(mpst + mpm)) / (h * sqrt(fy * tw * (1 - c2))), D(1))   # G2-13
            tf_vn = D("0.6") * fy * aw * (c2 + beta * (1 - c2) / (D("1.15") * sqrt(1 + ah**2)))                # G2-12
            out.update(beta_v=beta, Mpf=mpf, Mpst=mpst)
        out["Vn_tension_field"] = tf_vn
        vn = max(vn, tf_vn)
    b, t = D(stiff["b"]), D(stiff["t"])
    rho = max(fy / fyst, D(1))
    out.update(b_t_max=D("0.56") * sqrt(E / fyst), Ist1=h**4 * rho ** D("1.3") / 40 * (fy / E) ** D("1.5"),          # G2-16, G2-18
               Ist=t * ((2 * b + tw) ** 3 - tw**3) / 12 if stiff["arrangement"] == "pair" else t * b**3 / 3)
    return vn, D("0.90"), out


def stiffened(fy, a, panel, stiff, fyst, name=None, d=None, tw=None, plus2=None, minus2=None, end=None):
    if name:                                                    # rolled W of the catalog: h from h/tw
        p = row("W", name)
        return stiffened_web(fy, p["d"], p["tw"], p["h/tw"] * p["tw"], [(p["bf"], p["tf"])] * 2, a, panel, stiff, fyst, end=end)
    h = D(d) - D(plus2[1]) - D(minus2[1])
    return stiffened_web(fy, d, tw, h, [plus2, minus2], a, panel, stiff, fyst, end=end)


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
    "ST-G2.2-G2-7": dict(kind="stiff", d=1200, tw=8, plus2=(400, 20), minus2=(400, 20), fy=345, a=1500, panel="interior",
                         stiff={"b": 120, "t": 12, "arrangement": "pair"}, fyst=345),
    "ST-G2.2-G2-8": dict(kind="stiff", d=1200, tw=10, plus2=(200, 12), minus2=(200, 12), fy=345, a=1000, panel="interior",
                         stiff={"b": 120, "t": 12, "arrangement": "pair"}, fyst=250),
    "ST-G2.2-G2-6": dict(kind="stiff", d=600, tw=10, plus2=(250, 20), minus2=(250, 20), fy=345, a=600, panel="interior",
                         stiff={"b": 100, "t": 10, "arrangement": "single"}, fyst=345),
    "ST-G2.3-end": dict(kind="stiff", d=1200, tw=8, plus2=(400, 20), minus2=(400, 20), fy=345, a=1500, panel="end",
                        stiff={"b": 120, "t": 12, "arrangement": "pair"}, fyst=345,
                        end={"b": 150, "t": 20, "arrangement": "pair", "e": 100}),
    "ST-G2.3-end-e-capped": dict(kind="stiff", d=1200, tw=8, plus2=(400, 20), minus2=(400, 20), fy=345, a=1000, panel="end",
                                 stiff={"b": 120, "t": 12, "arrangement": "pair"}, fyst=250,
                                 end={"b": 150, "t": 20, "arrangement": "single", "e": 400}),
    "ST-G2.1-a-over-h-3": dict(kind="stiff", d=1200, tw=8, plus2=(400, 20), minus2=(400, 20), fy=345, a=4000, panel="interior",
                               stiff={"b": 120, "t": 12, "arrangement": "pair"}, fyst=345),
    "ST-W-G2.2": dict(kind="stiff", name="W24X55", fy=345, a=900, panel="interior", stiff={"b": 80, "t": 8, "arrangement": "pair"},
                      fyst=345),
}


def build(spec):
    args = {k: v for k, v in spec.items() if k != "kind"}
    if spec["kind"] == "stiff":
        vn, phi, extra = stiffened(**args)
        return {"spec": spec, "Vn_kN": vn / 1000, "phi_v": phi, "phiVn_kN": phi * vn / 1000, "stiffened": extra}
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
