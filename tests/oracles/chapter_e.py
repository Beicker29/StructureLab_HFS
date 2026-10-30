"""Independent Chapter E hand calculations (ANSI/AISC 360-22, a360-22w.pdf).

Written directly from the Specification text (B4.1a p.16.1-21, E1-E7
pp.16.1-38..49), in Decimal with 50 digits. It reads data/sections.xlsx with
openpyxl and its own unit scales; it never imports steel_design. Run it to
regenerate tests/fixtures/chapter_e/reference.json; the tests consume that
frozen file:

    python tests/oracles/chapter_e.py
"""
from decimal import Decimal as D, getcontext
import json
from pathlib import Path

import openpyxl

getcontext().prec = 50
ROOT = Path(__file__).resolve().parents[2]
PI = D("3.14159265358979323846264338327950288419716939937510")
E, G = D(200000), D(77200)
SHEETS = {"W": "W_IPE_HEA_HEB", "CHANNEL": "C", "RECTANGULAR_HSS": "PTE_RECT",
          "CIRCULAR_HSS": "PTE_RED", "SINGLE_ANGLE": "L"}
# AISC metric database units: 10^6 mm4, 10^3 mm4 (J), 10^9 mm6 (Cw).
SCALE = {"Ix": D(10)**6, "Iy": D(10)**6, "J": D(10)**3, "Cw": D(10)**9}


def row(family, name):
    ws = openpyxl.load_workbook(ROOT / "data/sections.xlsx", read_only=True, data_only=True)[SHEETS[family]]
    rows = ws.iter_rows(values_only=True)
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


def sqrt(x):
    return x.sqrt()


def fn_e3(fy, fe):
    # E3-2 / E3-3
    return (D("0.658") ** (fy / fe)) * fy if fy / fe <= D("2.25") else D("0.877") * fe


def fe_flex(lc, r):
    return PI**2 * E / (lc / r) ** 2  # E3-4


def be_e7(b, t, lam_r, fn, fy, c1):
    # E7-2..E7-5, c2 from E7-4
    c2 = (1 - sqrt(1 - 4 * c1)) / (2 * c1)
    lam = b / t
    if lam <= lam_r * sqrt(fy / fn):
        return b
    fel = (c2 * lam_r / lam) ** 2 * fy
    return b * (1 - c1 * sqrt(fel / fn)) * sqrt(fel / fn)


def case(cid, family, name, fy, L, Lz=None, ya=D(0), e5=None, Ly=None):
    p = row(family, name)
    fy, L = D(fy), D(L)
    Lz = D(Lz) if Lz is not None else L
    Ly = D(Ly) if Ly is not None else L
    ag = p["A"]
    rt = sqrt(E / fy)
    modes = {}
    plates = []  # (b, t, lambda_r, c1, count)
    if family == "W":
        lr_f, lr_w = D("0.56") * rt, D("1.49") * rt          # B4.1a cases 1 and 5
        plates = [(p["bf/2tf"] * p["tf"], p["tf"], lr_f, D("0.22"), 4),
                  (p["h/tw"] * p["tw"], p["tw"], lr_w, D("0.18"), 1)]
        modes["FB-x"] = fe_flex(L, p["rx"])
        modes["FB-y"] = fe_flex(L, p["ry"])
        if ya:
            ro2 = p["rx"]**2 + p["ry"]**2 + ya**2           # E4-11
            modes["TB"] = (PI**2 * E * p["Iy"] / Lz**2 * (p["ho"]**2 / 4 + ya**2) + G * p["J"]) / (ag * ro2)  # E4-10
        else:
            modes["TB"] = (PI**2 * E * p["Cw"] / Lz**2 + G * p["J"]) / (p["Ix"] + p["Iy"])  # E4-2
    elif family == "CHANNEL":
        lr_f, lr_w = D("0.56") * rt, D("1.49") * rt
        plates = [(p["b/t"] * p["tf"], p["tf"], lr_f, D("0.22"), 2),   # B4.1a(b): full flange width
                  (p["h/tw"] * p["tw"], p["tw"], lr_w, D("0.18"), 1)]
        fex, fey = fe_flex(L, p["rx"]), fe_flex(Ly, p["ry"])
        fez = (PI**2 * E * p["Cw"] / Lz**2 + G * p["J"]) / (ag * p["ro"]**2)  # E4-7
        h = p["H"]
        # E4-3, Fey replaced by Fex (User Note: x is the axis of symmetry of channels)
        ftb = (fex + fez) / (2 * h) * (1 - sqrt(1 - 4 * fex * fez * h / (fex + fez)**2))
        modes.update({"FB-x": fex, "FB-y": fey, "FTB": ftb})
    elif family == "RECTANGULAR_HSS":
        lr = D("1.40") * rt                                      # B4.1a case 6
        plates = [(p["b"], p["tdes"], lr, D("0.20"), 2), (p["h"], p["tdes"], lr, D("0.20"), 2)]
        modes["FB-x"], modes["FB-y"] = fe_flex(L, p["rx"]), fe_flex(L, p["ry"])
    elif family == "CIRCULAR_HSS":
        modes["FB-x"], modes["FB-y"] = fe_flex(L, p["rx"]), fe_flex(L, p["ry"])
        if Lz > L:
            modes["TB"] = (PI**2 * E * p["Cw"] / Lz**2 + G * p["J"]) / (p["Ix"] + p["Iy"])  # E4-2
    elif family == "SINGLE_ANGLE":
        legs = sorted([p["d"], p["b"]])
        bs, bl, t = legs[0], legs[1], p["t"]
        lr = D("0.45") * rt                                      # B4.1a case 3
        plates = [(bl, t, lr, D("0.22"), 1), (bs, t, lr, D("0.22"), 1)]
        assert bl / t <= D("0.71") * rt, "E4 would be required"
        config, leg, length = e5
        length = D(length)
        ra = p["ry"] if leg == "long" else p["rx"]               # axis parallel to connected leg
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
    slender = any(b / t > lam_r for b, t, lam_r, _, _ in plates)
    if family == "CIRCULAR_HSS":
        dt = p["OD"] / p["tdes"]
        slender = dt > D("0.11") * E / fy                        # B4.1a case 9
    out = {}
    for mode, fe in modes.items():
        fn = fn_e3(fy, fe)
        if not slender:
            ae = ag
        elif family == "CIRCULAR_HSS":
            ae = min(ag, (D("0.038") * E / (fy * dt) + D(2) / 3) * ag)   # E7-7, Ae<=Ag (criterion D-2)
        else:
            ae = ag - sum(n * (b - be_e7(b, t, lam_r, fn, fy, c1)) * t for b, t, lam_r, c1, n in plates)
        pn = fn * ae
        out[mode] = {"Fe_mpa": fe, "Fn_mpa": fn, "A_mm2": ae, "Pn_kN": pn / 1000}
    gov = min(out, key=lambda k: out[k]["Pn_kN"])
    pn = out[gov]["Pn_kN"]
    return cid, {"family": family, "section": name, "Fy": fy, "Lx": L, "Ly": Ly, "Lz": Lz, "ya": ya, "e5": e5,
                 "slender": slender, "modes": out, "governing_mode": gov, "Pn_kN": pn,
                 "LRFD_kN": D("0.90") * pn, "ASD_kN": pn / D("1.67")}


CASES = [
    ("RHSS-nonslender", "RECTANGULAR_HSS", "PTE100X100X4MM", 345, 3000),
    ("RHSS-slender", "RECTANGULAR_HSS", "PTE120X60X2MM", 345, 1500),
    ("C-flexural", "CHANNEL", "C15X50", 345, 3000),
    ("C-flexural-torsional", "CHANNEL", "C15X50", 345, 1000),
    ("C-FTB-governs", "CHANNEL", "C15X50", 345, 4000, 4000, D(0), None, 1000),
    ("C-slender", "CHANNEL", "C12X20.7", 450, 1500),
    ("W-torsional", "W", "W14X90", 345, 3000),
    ("W-slender-web", "W", "W8X10", 345, 3000),
    ("W-bracing-offset-E4-10", "W", "W14X90", 345, 6000, 6000, D(200)),
    ("CHSS-nonslender", "CIRCULAR_HSS", 'PTER4"X3.00MM', 345, 2500),
    ("CHSS-torsional-length", "CIRCULAR_HSS", 'PTER4"X3.00MM', 345, 2500, 5000),
    ("CHSS-slender-E7-7", "CIRCULAR_HSS", 'PTER24"X12.70MM', 450, 8000),
    ("L-E5a-equal", "SINGLE_ANGLE", "L4X4X1/4", 250, None, None, D(0), ("a", "long", 2000)),
    ("L-E5b-short-leg", "SINGLE_ANGLE", "L6X4X3/8", 250, None, None, D(0), ("b", "short", 2500)),
    ("L-E5a-slender-leg", "SINGLE_ANGLE", "L4X4X1/4", 345, None, None, D(0), ("a", "long", 600)),
]


def build():
    result = {}
    for spec in CASES:
        cid, family, name, fy, L, *rest = spec
        Lz = rest[0] if rest else None
        ya = rest[1] if len(rest) > 1 else D(0)
        e5 = rest[2] if len(rest) > 2 else None
        ly = rest[3] if len(rest) > 3 else None
        key, value = case(cid, family, name, fy, L if L is not None else e5[2], Lz, ya, e5, ly)
        result[key] = value
    return result


def _plain(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


if __name__ == "__main__":
    target = ROOT / "tests/fixtures/chapter_e/reference.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": "ANSI/AISC 360-22 (a360-22w.pdf) E1-E7, B4.1a; catalog data/sections.xlsx",
               "generator": "tests/oracles/chapter_e.py (Decimal, 50 digits; independent of steel_design)",
               "cases": _plain(build())}
    target.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(target)
