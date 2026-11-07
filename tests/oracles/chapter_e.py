"""Independent Chapter E hand calculations (ANSI/AISC 360-22, a360-22w.pdf).

Written directly from the Specification text (B4.1a p.16.1-21, E1-E7
pp.16.1-38..49), in Decimal with 50 digits. It reads src/steel_design/data/sections.xlsx with
openpyxl and its own unit scales; it never imports steel_design. Run it to
regenerate tests/fixtures/chapter_e/reference.json; the tests consume that
frozen file:

    python tests/oracles/chapter_e.py
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
PI = D("3.14159265358979323846264338327950288419716939937510")
E, G = D(200000), D(77200)
SHEETS = {"W": "W_IPE_HEA_HEB", "CHANNEL": "C", "RECTANGULAR_HSS": "PTE_RECT",
          "CIRCULAR_HSS": "PTE_RED", "SINGLE_ANGLE": "L", "DOUBLE_ANGLE": "2L"}
# AISC metric database units: 10^6 mm4 (Ix, Iy, Iw, Iz), 10^3 mm4 (J), 10^9 mm6 (Cw).
SCALE = {"Ix": D(10)**6, "Iy": D(10)**6, "Iw": D(10)**6, "Iz": D(10)**6, "J": D(10)**3, "Cw": D(10)**9}
_WORKBOOK = None


def row(family, name):
    global _WORKBOOK
    _WORKBOOK = _WORKBOOK or openpyxl.load_workbook(ROOT / "src/steel_design/data/sections.xlsx", read_only=True, data_only=True)
    rows = _WORKBOOK[SHEETS[family]].iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else None for h in next(rows)]
    for values in rows:
        if values[0] is not None and str(values[0]).strip().upper() == name:
            out = {}
            for key, value in zip(header, values):
                if key and isinstance(value, (int, float)):
                    out[key] = D(repr(value)) * SCALE.get(key, 1)
                elif key and isinstance(value, str):
                    try:
                        out[key] = D(value) * SCALE.get(key, 1)
                    except ArithmeticError:
                        pass
            return out
    raise KeyError(name)


def fn_e3(fy, fe):
    # E3-2 / E3-3
    return (D("0.658") ** (fy / fe)) * fy if fy / fe <= D("2.25") else D("0.877") * fe


def fe_flex(lc, r):
    return PI**2 * E / (lc / r) ** 2  # E3-4


def e4_3(fe_sym, fez, h):
    # E4-3, standard form
    return (fe_sym + fez) / (2 * h) * (1 - sqrt(1 - 4 * fe_sym * fez * h / (fe_sym + fez) ** 2))


def e4_4(fex, fey, fez, xo, yo, ro):
    # E4-4 as printed; lowest root by bisection on (0, min) where the cubic changes sign.
    def f(fe):
        return ((fe - fex) * (fe - fey) * (fe - fez) - fe**2 * (fe - fey) * (xo / ro) ** 2
                - fe**2 * (fe - fex) * (yo / ro) ** 2)
    lo, hi = D(0), min(fex, fey, fez)
    for _ in range(300):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if (f(mid) < 0) == (f(lo) < 0) else (lo, mid)
    return (lo + hi) / 2


def atan(x):
    # arctan by series after argument reduction (x >= 0)
    if x > 1:
        return PI / 2 - atan(1 / x)
    if x > D("0.4"):
        return 2 * atan(x / (1 + sqrt(1 + x * x)))
    term, total, n = x, D(0), 0
    while abs(term) > D(10) ** -45:
        total += term / (2 * n + 1)
        n += 1
        term = -term * x * x
    return total


def cos_sin(a):
    # Taylor series
    c, s, term, n = D(0), D(0), D(1), 0
    while abs(term) > D(10) ** -45:
        if n % 2 == 0:
            c += term if (n // 2) % 2 == 0 else -term
        else:
            s += term if (n // 2) % 2 == 0 else -term
        n += 1
        term = term * a / n
    return c, s


def be_e7(b, t, lam_r, fn, fy, c1):
    # E7-2..E7-5, c2 from E7-4
    c2 = (1 - sqrt(1 - 4 * c1)) / (2 * c1)
    lam = b / t
    if lam <= lam_r * sqrt(fy / fn):
        return b
    fel = (c2 * lam_r / lam) ** 2 * fy
    return b * (1 - c1 * sqrt(fel / fn)) * sqrt(fel / fn)


def plate_i(d, tw, top, bottom):
    """Welded I from its plates (no weld radii): catalog-like keys. Thin-walled J, Cw and shear center (DF-17)."""
    d, tw = D(d), D(tw)
    (bt, tt), (bb, tb) = [(D(b), D(t)) for b, t in (top, bottom)]
    h = d - tt - tb
    parts = [(bb * tb, tb / 2, bb, tb), (h * tw, tb + h / 2, tw, h), (bt * tt, d - tt / 2, bt, tt)]   # (A, y up, width, depth)
    ag = sum(a for a, _, _, _ in parts)
    ybar = sum(a * y for a, y, _, _ in parts) / ag
    ix = sum(w * t**3 / 12 + a * (y - ybar) ** 2 for a, y, w, t in parts)
    it, ib = tt * bt**3 / 12, tb * bb**3 / 12
    iy = it + ib + h * tw**3 / 12
    ho = d - tt / 2 - tb / 2
    yo = tb / 2 + ho * it / (it + ib) - ybar                    # shear center above the bottom flange centroid
    ro2 = yo**2 + (ix + iy) / ag                                 # E4-9, xo = 0
    return {"A": ag, "Ix": ix, "Iy": iy, "rx": sqrt(ix / ag), "ry": sqrt(iy / ag), "J": (bt * tt**3 + bb * tb**3 + h * tw**3) / 3,
            "Cw": ho**2 * it * ib / (it + ib), "ro": sqrt(ro2), "H": 1 - yo**2 / ro2, "h": h, "tw": tw, "bt": bt, "tt": tt,
            "bb": bb, "tb": tb, "singly": (bt, tt) != (bb, tb)}


def case(family, name, fy, Lx_3, Ly_2=None, Lz_1=None, ya_2=0, e5=None, e6=None, girder=None):
    p = plate_i(*girder) if family == "I_BUILT_UP" else row(family, name)
    fy, Lx_3 = D(fy), D(Lx_3)
    Ly_2 = D(Ly_2) if Ly_2 is not None else Lx_3
    Lz_1 = D(Lz_1) if Lz_1 is not None else Lx_3
    ya_2 = D(ya_2)
    ag = p["A"]
    rt = sqrt(E / fy)
    modes, gross_only = {}, set()
    plates = []  # (b, t, lambda_r, c1, count)
    if family == "W":
        lr_f, lr_w = D("0.56") * rt, D("1.49") * rt          # B4.1a cases 1 and 5
        plates = [(p["bf/2tf"] * p["tf"], p["tf"], lr_f, D("0.22"), 4),
                  (p["h/tw"] * p["tw"], p["tw"], lr_w, D("0.18"), 1)]
        modes["FB-x_3"], modes["FB-y_2"] = fe_flex(Lx_3, p["rx"]), fe_flex(Ly_2, p["ry"])
        if ya_2:
            ro2 = p["rx"]**2 + p["ry"]**2 + ya_2**2           # E4-11
            modes["TB"] = (PI**2 * E * p["Iy"] / Lz_1**2 * (p["ho"]**2 / 4 + ya_2**2) + G * p["J"]) / (ag * ro2)  # E4-10
        else:
            modes["TB"] = (PI**2 * E * p["Cw"] / Lz_1**2 + G * p["J"]) / (p["Ix"] + p["Iy"])  # E4-2
    elif family == "I_BUILT_UP":
        kc = min(max(4 / sqrt(p["h"] / p["tw"]), D("0.35")), D("0.76"))
        lr_f, lr_w = D("0.64") * sqrt(kc * E / fy), D("1.49") * rt  # B4.1a case 2 (note [a]) and case 5 or 8
        plates = [(p["bt"] / 2, p["tt"], lr_f, D("0.22"), 2), (p["bb"] / 2, p["tb"], lr_f, D("0.22"), 2),
                  (p["h"], p["tw"], lr_w, D("0.18"), 1)]
        modes["FB-x_3"], modes["FB-y_2"] = fe_flex(Lx_3, p["rx"]), fe_flex(Ly_2, p["ry"])
        if p["singly"]:                                          # E4(b): y is the axis of symmetry
            fez = (PI**2 * E * p["Cw"] / Lz_1**2 + G * p["J"]) / (ag * p["ro"]**2)  # E4-7
            modes["FTB"] = e4_3(modes["FB-y_2"], fez, p["H"])
        else:
            modes["TB"] = (PI**2 * E * p["Cw"] / Lz_1**2 + G * p["J"]) / (p["Ix"] + p["Iy"])  # E4-2
    elif family == "CHANNEL":
        lr_f, lr_w = D("0.56") * rt, D("1.49") * rt
        plates = [(p["b/t"] * p["tf"], p["tf"], lr_f, D("0.22"), 2),   # B4.1a(b): full flange width
                  (p["h/tw"] * p["tw"], p["tw"], lr_w, D("0.18"), 1)]
        fex, fey = fe_flex(Lx_3, p["rx"]), fe_flex(Ly_2, p["ry"])
        fez = (PI**2 * E * p["Cw"] / Lz_1**2 + G * p["J"]) / (ag * p["ro"]**2)  # E4-7
        # E4-3 with Fey replaced by Fex (User Note: x is the axis of symmetry of channels)
        modes.update({"FB-x_3": fex, "FB-y_2": fey, "FTB": e4_3(fex, fez, p["H"])})
    elif family == "RECTANGULAR_HSS":
        lr = D("1.40") * rt                                      # B4.1a case 6
        plates = [(p["b"], p["tdes"], lr, D("0.20"), 2), (p["h"], p["tdes"], lr, D("0.20"), 2)]
        modes["FB-x_3"], modes["FB-y_2"] = fe_flex(Lx_3, p["rx"]), fe_flex(Ly_2, p["ry"])
        if Lz_1 > min(Lx_3, Ly_2):
            modes["TB"] = G * p["J"] / (p["Ix"] + p["Iy"])       # E4-2 with the Cw term omitted (D-7)
    elif family == "CIRCULAR_HSS":
        modes["FB-x_3"], modes["FB-y_2"] = fe_flex(Lx_3, p["rx"]), fe_flex(Ly_2, p["ry"])
        if Lz_1 > min(Lx_3, Ly_2):
            modes["TB"] = (PI**2 * E * p["Cw"] / Lz_1**2 + G * p["J"]) / (p["Ix"] + p["Iy"])  # E4-2
    elif family == "SINGLE_ANGLE":
        bs, bl = sorted([p["d"], p["b"]])
        t = p["t"]
        lr = D("0.45") * rt                                      # B4.1a case 3
        plates = [(bl, t, lr, D("0.22"), 1), (bs, t, lr, D("0.22"), 1)]
        if e5 is None:                                           # outside E5: E3 about z, eccentricity in H2 (DH-8)
            modes["FB-z"] = fe_flex(Lx_3, p["rz"])
        else:
            config, leg, length = e5
            length = D(length)
            ra = p["ry"] if leg == "long" or bl == bs else p["rx"]  # geometric axis parallel to connected leg
            s = length / ra
            if config == "a":
                lcr = 72 + D("0.75") * s if s <= 80 else 32 + D("1.25") * s
                if leg == "short" and bl > bs:
                    lcr = max(lcr + 4 * ((bl / bs)**2 - 1), D("0.95") * length / p["rz"])
            else:
                lcr = 60 + D("0.8") * s if s <= 75 else 45 + s
                if leg == "short" and bl > bs:
                    lcr = max(lcr + 6 * ((bl / bs)**2 - 1), D("0.82") * length / p["rz"])
            assert lcr <= 200
            modes["FB-E5"] = PI**2 * E / lcr**2
        if bl / t > D("0.71") * rt:                              # E5: flexural-torsional per E4
            assert Lx_3 == Ly_2
            few, fe_z = fe_flex(Lx_3, sqrt(p["Iw"] / ag)), fe_flex(Lx_3, p["rz"])
            fet = (PI**2 * E * p["Cw"] / Lz_1**2 + G * p["J"]) / (ag * p["ro"]**2)  # E4-7
            if bl == bs:
                modes["FTB"] = e4_3(few, fet, p["H"])           # w is the axis of symmetry
            else:
                c, s_ = cos_sin(atan(p["tan(α)"]))
                xs, ys = p["x"] - t / 2, p["y"] - t / 2         # shear center at leg mid-thickness lines
                wo, zo = xs * c + ys * s_, xs * s_ - ys * c
                modes["FTB"] = e4_4(few, fe_z, fet, wo, zo, p["ro"])
            gross_only.add("FTB")                                # E4-1 with Ag; E7 Fn from E3 only
    elif family == "DOUBLE_ANGLE":
        m = re.match(r"^2L([^X]+)X([^X]+)X([^X]+?)(?:X([^X]+?))?(LLBB|SLBB)?$", name)
        comp = row("SINGLE_ANGLE", f"L{m[1]}X{m[2]}X{m[3]}")
        contact = m[4] is None
        bs, bl = sorted([p["d"], p["b"]])
        t = p["t"]
        lr = (D("0.56") if contact else D("0.45")) * rt          # B4.1a case 1(3) or 3(2)
        plates = [(bl, t, lr, D("0.22"), 2), (bs, t, lr, D("0.22"), 2)]
        connectors, a = e6
        a, ri = D(a), comp["rz"]
        lr_o = Ly_2 / p["ry"]
        if connectors == "snug_tight":
            lr_m = sqrt(lr_o**2 + (a / ri) ** 2)                 # E6-1
        elif a / ri <= 40:
            lr_m = lr_o                                          # E6-2a
        else:
            lr_m = sqrt(lr_o**2 + (D("0.5") * a / ri) ** 2)      # E6-2b, Ki = 0.50
        fey = PI**2 * E / lr_m**2
        fez = G * 2 * comp["J"] / (ag * p["ro"]**2)              # E4-7, Cw omitted, J of both angles
        modes.update({"FB-x_3": fe_flex(Lx_3, p["rx"]), "FB-y_2": fey, "FTB": e4_3(fey, fez, p["H"])})
    slender = any(b / t > lam_r for b, t, lam_r, _, _ in plates)
    if family == "CIRCULAR_HSS":
        dt = p["OD"] / p["tdes"]
        slender = dt > D("0.11") * E / fy                        # B4.1a case 9
    out = {}
    for mode, fe in modes.items():
        fn = fn_e3(fy, fe)
        if not slender or mode in gross_only:
            ae = ag
        elif family == "CIRCULAR_HSS":
            ae = min(ag, (D("0.038") * E / (fy * dt) + D(2) / 3) * ag)   # E7-7, Ae<=Ag (criterion D-2)
        else:
            ae = ag - sum(n * (b - be_e7(b, t, lam_r, fn, fy, c1)) * t for b, t, lam_r, c1, n in plates)
        pn = fn * ae
        out[mode] = {"Fe_mpa": fe, "Fn_mpa": fn, "A_mm2": ae, "Pn_kN": pn / 1000}
    gov = min(out, key=lambda k: out[k]["Pn_kN"])
    pn = out[gov]["Pn_kN"]
    return {"family": family, "section": name, "girder": girder, "Fy": fy, "Lx_3": Lx_3, "Ly_2": Ly_2, "Lz_1": Lz_1, "ya_2": ya_2, "e5": e5,
            "e6": e6, "slender": slender, "modes": out, "governing_mode": gov, "Pn_kN": pn,
            "LRFD_kN": D("0.90") * pn}


CASES = {
    "RHSS-nonslender": dict(family="RECTANGULAR_HSS", name="PTE100X100X4MM", fy=345, Lx_3=3000),
    "RHSS-slender": dict(family="RECTANGULAR_HSS", name="PTE120X60X2MM", fy=345, Lx_3=1500),
    "RHSS-torsional-length-E4-2": dict(family="RECTANGULAR_HSS", name="PTE150X50X3MM", fy=345, Lx_3=1000, Lz_1=6000),
    "C-flexural": dict(family="CHANNEL", name="C15X50", fy=345, Lx_3=3000),
    "C-flexural-torsional": dict(family="CHANNEL", name="C15X50", fy=345, Lx_3=1000),
    "C-FTB-governs": dict(family="CHANNEL", name="C15X50", fy=345, Lx_3=4000, Ly_2=1000, Lz_1=4000),
    "C-slender": dict(family="CHANNEL", name="C12X20.7", fy=450, Lx_3=1500),
    "W-torsional": dict(family="W", name="W14X90", fy=345, Lx_3=3000),
    "W-slender-web": dict(family="W", name="W8X10", fy=345, Lx_3=3000),
    "W-bracing-offset-E4-10": dict(family="W", name="W14X90", fy=345, Lx_3=6000, ya_2=200),
    "CHSS-nonslender": dict(family="CIRCULAR_HSS", name='PTER4"X3.00MM', fy=345, Lx_3=2500),
    "CHSS-torsional-length": dict(family="CIRCULAR_HSS", name='PTER4"X3.00MM', fy=345, Lx_3=2500, Lz_1=5000),
    "CHSS-slender-E7-7": dict(family="CIRCULAR_HSS", name='PTER24"X12.70MM', fy=450, Lx_3=8000),
    "L-E5a-equal": dict(family="SINGLE_ANGLE", name="L4X4X1/4", fy=250, Lx_3=2000, e5=("a", "long", 2000)),
    "L-E5b-short-leg": dict(family="SINGLE_ANGLE", name="L6X4X3/8", fy=250, Lx_3=2500, e5=("b", "short", 2500)),
    "L-E5a-slender-leg": dict(family="SINGLE_ANGLE", name="L4X4X1/4", fy=345, Lx_3=600, e5=("a", "long", 600)),
    "L-E4-3-equal-legs": dict(family="SINGLE_ANGLE", name="L4X4X1/4", fy=450, Lx_3=2000, e5=("a", "long", 2000)),
    "L-E4-3-governs": dict(family="SINGLE_ANGLE", name="L6X6X5/16", fy=450, Lx_3=600, Lz_1=3000, e5=("b", "long", 600)),
    "L-E4-4-unequal-legs": dict(family="SINGLE_ANGLE", name="L6X4X3/8", fy=450, Lx_3=2000, e5=("a", "short", 2000)),
    "L-H2-FBz-slender": dict(family="SINGLE_ANGLE", name="L8X4X1/2", fy=345, Lx_3=1524),
    "L-H2-FTB-equal": dict(family="SINGLE_ANGLE", name="L4X4X1/4", fy=450, Lx_3=2000),
    "L-H2-FTB-unequal": dict(family="SINGLE_ANGLE", name="L6X4X3/8", fy=450, Lx_3=2000),
    "2L-contact-welded": dict(family="DOUBLE_ANGLE", name="2L4X4X1/4", fy=345, Lx_3=2000, e6=("welded", 500)),
    "2L-separated-snug": dict(family="DOUBLE_ANGLE", name="2L4X4X1/4X3/4", fy=345, Lx_3=2000, e6=("snug_tight", 800)),
    "2L-LLBB-pretensioned": dict(family="DOUBLE_ANGLE", name="2L8X4X1/2LLBB", fy=345, Lx_3=3000, e6=("pretensioned", 1500)),
    "BUI-singly-FTB-slender-web": dict(family="I_BUILT_UP", name="PL900", girder=(900, 8, (350, 22), (250, 16)), fy=345, Lx_3=9000,
                                       Ly_2=3000, Lz_1=3000),
    "BUI-singly-nonslender": dict(family="I_BUILT_UP", name="PL400", girder=(400, 12, (250, 20), (200, 16)), fy=345, Lx_3=6000),
    "BUI-doubly-TB-slender-flange": dict(family="I_BUILT_UP", name="PL500", girder=(500, 10, (300, 10), (300, 10)), fy=345,
                                         Lx_3=4000, Ly_2=2000, Lz_1=4000),
}


if __name__ == "__main__":
    target = ROOT / "tests/fixtures/chapter_e/reference.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": "ANSI/AISC 360-22 (a360-22w.pdf) E1-E7, B4.1a; catalog src/steel_design/data/sections.xlsx",
               "generator": "tests/oracles/chapter_e.py (Decimal, 50 digits; independent of steel_design)",
               "cases": _plain({cid: case(**spec) for cid, spec in CASES.items()})}
    target.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(target)
