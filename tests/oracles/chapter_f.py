"""Independent Chapter F hand calculations (ANSI/AISC 360-22, a360-22w.pdf pp.16.1-50..73, B4.1b), LRFD.

Decimal arithmetic (50 digits); reads data/sections.xlsx with openpyxl and its own unit
scales; never imports steel_design. F7 LTB numbering per errata E25-02 (F7-8..F7-11).
Regenerates tests/fixtures/chapter_f/reference.json:

    python tests/oracles/chapter_f.py
"""
from decimal import Decimal as D, getcontext
import json
from pathlib import Path

import openpyxl

getcontext().prec = 50
ROOT = Path(__file__).resolve().parents[2]
PI = D("3.14159265358979323846264338327950288419716939937510")
E = D(200000)
SHEETS = {"W": "W_IPE_HEA_HEB", "CHANNEL": "C", "RECTANGULAR_HSS": "PTE_RECT", "CIRCULAR_HSS": "PTE_RED",
          "SINGLE_ANGLE": "L", "DOUBLE_ANGLE": "2L"}
SCALE = {"Ix": 10**6, "Iy": 10**6, "Iw": 10**6, "Iz": 10**6, "J": 10**3, "Cw": 10**9, "Sx": 10**3, "Sy": 10**3,
         "Zx": 10**3, "Zy": 10**3, "SwA": 10**3, "SwB": 10**3, "SwC": 10**3, "SzA": 10**3, "SzB": 10**3, "SzC": 10**3}
SHEET_SCALE = {"PTE_RED": {"Sx": 1, "Sy": 1}}   # that sheet stores S in mm3 (S = I/c)
_WB = None


def row(family, name):
    global _WB
    _WB = _WB or openpyxl.load_workbook(ROOT / "data/sections.xlsx", read_only=True, data_only=True)
    sheet = SHEETS[family]
    rows = _WB[sheet].iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else None for h in next(rows)]
    scale = {**SCALE, **SHEET_SCALE.get(sheet, {})}
    for values in rows:
        if values[0] is not None and str(values[0]).strip().upper() == name:
            out = {}
            for key, value in zip(header, values):
                if key and isinstance(value, (int, float)) and not isinstance(value, bool):
                    out[key] = D(repr(value)) * scale.get(key, 1)
                elif key and isinstance(value, str):
                    try:
                        out[key] = D(value) * scale.get(key, 1)
                    except ArithmeticError:
                        pass
            return out
    raise KeyError(name)


def sqrt(x):
    return x.sqrt()


def interp(mp, mlow, x, xp, xr):
    return mp - (mp - mlow) * (x - xp) / (xr - xp)


def w_or_channel(name, family, fy, axis, Lb=None, Cb=1, holes=None, Fu=None):
    p, fy, Cb = row(family, name), D(fy), D(Cb)
    rt = sqrt(E / fy)
    modes = {}
    if axis == "x":
        flange = p["b/t"] if family == "CHANNEL" else p["bf/2tf"]
        lpf, lrf = D("0.38") * rt, D("1.0") * rt                                 # B4.1b case 10
        assert p["h/tw"] <= D("3.76") * rt                                      # compact web (case 15)
        mp = fy * p["Zx"]                                                       # F2-1
        if flange <= lpf:
            modes["Y"] = mp
        elif flange <= lrf:
            modes["FLB"] = interp(mp, D("0.7") * fy * p["Sx"], flange, lpf, lrf)  # F3-1
        else:
            kc = min(max(4 / sqrt(p["h/tw"]), D("0.35")), D("0.76"))
            modes["FLB"] = D("0.9") * E * kc * p["Sx"] / flange**2              # F3-2
        Lb = D(Lb)
        rts = sqrt(sqrt(p["Iy"] * p["Cw"]) / p["Sx"])                            # F2-7
        c = p["ho"] / 2 * sqrt(p["Iy"] / p["Cw"]) if family == "CHANNEL" else D(1)  # F2-8
        jc = p["J"] * c / (p["Sx"] * p["ho"])
        lp = D("1.76") * p["ry"] * rt                                           # F2-5
        lr = D("1.95") * rts * E / (D("0.7") * fy) * sqrt(jc + sqrt(jc**2 + D("6.76") * (D("0.7") * fy / E) ** 2))
        if Lb > lr:
            fcr = Cb * PI**2 * E / (Lb / rts) ** 2 * sqrt(1 + D("0.078") * jc * (Lb / rts) ** 2)  # F2-4
            modes["LTB"] = min(fcr * p["Sx"], mp)                               # F2-3
        elif Lb > lp:
            modes["LTB"] = min(Cb * interp(mp, D("0.7") * fy * p["Sx"], Lb, lp, lr), mp)  # F2-2
        if holes:
            fu, afn = D(Fu), D(holes)
            afg = p["bf"] * p["tf"]
            yt = D(1) if fy / fu <= D("0.8") else D("1.1")
            if fu * afn < yt * fy * afg:
                modes["TFR"] = fu * afn / afg * p["Sx"]                         # F13-1
    else:
        ratio = p["b/t"] if family == "CHANNEL" else p["bf/2tf"]
        lp, lr = D("0.38") * rt, D("1.0") * rt                                   # B4.1b case 13
        mp = min(fy * p["Zy"], D("1.6") * fy * p["Sy"])                          # F6-1
        modes["Y"] = mp
        if lp < ratio <= lr:
            modes["FLB"] = interp(mp, D("0.7") * fy * p["Sy"], ratio, lp, lr)    # F6-2
        elif ratio > lr:
            modes["FLB"] = D("0.70") * E / ratio**2 * p["Sy"]                    # F6-3, F6-4
    return modes


def rect_hss(name, fy, axis, Lb=None, Cb=1):
    p, fy, Cb = row("RECTANGULAR_HSS", name), D(fy), D(Cb)
    rt = sqrt(E / fy)
    t = p["tdes"]
    # B4.1b(d): flat widths are the outside dimension less 3t (catalog b, h columns)
    if axis == "x":
        bf, hw, S, Z, inertia, depth = p["b"], p["h"], p["Sx"], p["Zx"], p["Ix"], p["Ht"]
    else:
        bf, hw, S, Z, inertia, depth = p["h"], p["b"], p["Sy"], p["Zy"], p["Iy"], p["B"]
    lf, lw = bf / t, hw / t
    lpf, lrf = D("1.12") * rt, D("1.40") * rt                                   # case 17
    lpw, lrw = D("2.42") * rt, D("5.70") * rt                                   # case 19
    mp = fy * Z
    modes = {"Y": mp}                                                           # F7-1
    if lpf < lf <= lrf:
        modes["FLB"] = min(interp(mp, fy * S, lf, lpf, lrf), mp)                 # F7-2
    elif lf > lrf:
        be = min(D("1.92") * t * rt * (1 - D("0.38") / lf * rt), bf)             # F7-4
        lost = (bf - be) * t
        a = (depth - t) / 2
        area = p["A"] - lost
        shift = lost * a / area
        i_eff = inertia - lost * a**2 - (bf - be) * t**3 / 12 - area * shift**2  # shifted neutral axis
        modes["FLB"] = fy * i_eff / (depth / 2 + shift)                          # F7-3
    assert lw <= lrw
    if lpw < lw:
        modes["WLB"] = min(interp(mp, fy * S, lw, lpw, lrw), mp)                 # F7-6
    if axis == "x" and p["Ht"] > p["B"]:
        Lb = D(Lb)
        root = sqrt(p["J"] * p["A"])
        lp = D("0.13") * E * p["ry"] * root / mp                                 # F7-10
        lr = 2 * E * p["ry"] * root / (D("0.7") * fy * p["Sx"])                  # F7-11
        if lp < Lb <= lr:
            modes["LTB"] = min(Cb * interp(mp, D("0.7") * fy * p["Sx"], Lb, lp, lr), mp)  # F7-8
        elif Lb > lr:
            modes["LTB"] = min(2 * E * Cb * root / (Lb / p["ry"]), mp)            # F7-9
    return modes


def round_hss(name, fy):
    p, fy = row("CIRCULAR_HSS", name), D(fy)
    dt = p["OD"] / p["tdes"]
    modes = {"Y": fy * p["Zx"]}                                                 # F8-1
    if D("0.07") * E / fy < dt <= D("0.31") * E / fy:
        modes["LB"] = (D("0.021") * E / dt + fy) * p["Sx"]                       # F8-2
    elif dt > D("0.31") * E / fy:
        modes["LB"] = D("0.33") * E / dt * p["Sx"]                               # F8-3
    return modes


def solid_rect(H, B, fy, axis, Lb=None, Cb=1):
    H, B, fy, Cb = D(H), D(B), D(fy), D(Cb)
    d, t = (H, B) if axis == "x" else (B, H)
    S, Z = t * d**2 / 6, t * d**2 / 4
    modes = {"Y": min(fy * Z, D("1.5") * fy * S)}                                # F11-1
    if d > t:
        x = D(Lb) * d / t**2
        if D("0.08") * E / fy < x <= D("1.9") * E / fy:
            modes["LTB"] = min(Cb * (D("1.52") - D("0.274") * x * fy / E) * fy * S, modes["Y"])  # F11-3
        elif x > D("1.9") * E / fy:
            modes["LTB"] = min(D("1.9") * E * Cb / x * S, modes["Y"])                         # F11-4, F11-5
    return modes


def solid_round(D_, fy):
    d, fy = D(D_), D(fy)
    return {"Y": min(fy * d**3 / 6, D("1.6") * fy * PI * d**3 / 32)}             # F11-2


def f10_ltb(my, mcr):
    if my / mcr <= 1:
        return min((D("1.92") - D("1.17") * sqrt(my / mcr)) * my, D("1.5") * my)   # F10-2
    return (D("0.92") - D("0.17") * mcr / my) * mcr                               # F10-3


def leg_buckling(b, t, sc, fy):
    lam, rt = b / t, sqrt(E / fy)
    if lam <= D("0.54") * rt:                                                     # B4.1b case 12
        return None
    if lam <= D("0.91") * rt:
        return fy * sc * (D("2.43") - D("1.72") * lam * sqrt(fy / E))            # F10-6
    return D("0.71") * E / lam**2 * sc                                            # F10-7, F10-8


def double_angle(name, fy, Lb, web_legs):
    import re
    p, fy, Lb = row("DOUBLE_ANGLE", name), D(fy), D(Lb)
    m = re.match(r"^2L([^X]+)X([^X]+)X([^X]+?)(?:X([^X]+?))?(LLBB|SLBB)?$", name)
    comp = row("SINGLE_ANGLE", f"L{m[1]}X{m[2]}X{m[3]}")
    legs = sorted([p["d"], p["b"]])
    web = legs[0] if m[5] == "SLBB" else legs[1]          # legs in the plane of symmetry
    flange = legs[1] if web == legs[0] else legs[0]
    j, t, my = 2 * comp["J"], p["t"], fy * p["Sx"]       # F9-3
    sign = 1 if web_legs == "tension" else -1
    bb = sign * D("2.3") * web / Lb * sqrt(p["Iy"] / j)                           # F9-11 / F9-12
    mcr = D("1.95") * E / Lb * sqrt(p["Iy"] * j) * (bb + sqrt(1 + bb**2))        # F9-10
    modes = {}
    if web_legs == "tension":
        mp = min(fy * p["Zx"], D("1.6") * my)                                     # F9-2
        modes["Y"] = mp
        lp = D("1.76") * p["ry"] * sqrt(E / fy)                                   # F9-8
        lr = D("1.95") * (E / fy) * sqrt(p["Iy"] * j) / p["Sx"] * sqrt(D("2.36") * (fy / E) * web * p["Sx"] / j + 1)
        if lp < Lb <= lr:
            modes["LTB"] = mp - (mp - my) * (Lb - lp) / (lr - lp)                 # F9-6
        elif Lb > lr:
            modes["LTB"] = mcr                                                    # F9-7
        flb = leg_buckling(flange, t, p["Ix"] / p["y"], fy)                       # F9.3(b): Sc to flange legs
        if flb is not None:
            modes["FLB"] = flb
    else:
        modes["Y"] = D("1.5") * my                                                # F9-5
        modes["LTB"] = f10_ltb(my, mcr)                                           # F9.2(b)(2)
        wlb = leg_buckling(web, t, p["Sx"], fy)                                   # F9.4(b)
        if wlb is not None:
            modes["WLB"] = wlb
    return modes


def single_angle_geometric(name, fy, axis, restraint, toe, Lb=None, Cb=1):
    p, fy, Cb = row("SINGLE_ANGLE", name), D(fy), D(Cb)
    legs = sorted([p["d"], p["b"]])
    short, long_, t = legs[0], legs[1], p["t"]
    inertia, perp, par, cen = ((p["Ix"], long_, short, p["y"]) if axis == "x" else (p["Iy"], short, long_, p["x"]))
    s_toe, s_face = inertia / (perp - cen), inertia / cen
    k = D("0.80") if restraint == "none" else D(1)                               # F10.2(2)(i): LTB and LLB only
    my = k * fy * s_toe
    modes = {"Y": D("1.5") * fy * s_toe}                                          # F10-1, unreduced My
    if restraint != "continuous":
        Lb = D(Lb)
        root = sqrt(1 + D("0.88") * (Lb * t / long_**2) ** 2)
        mcr = D("0.58") * E * long_**4 * t * Cb / Lb**2 * (root - 1 if toe == "compression" else root + 1)  # F10-5
        if restraint == "at_max_moment":
            mcr *= D("1.25")
        modes["LTB"] = f10_ltb(my, mcr)
    if toe == "compression":
        llb = leg_buckling(perp, t, k * s_toe, fy)
    else:
        llb = leg_buckling(par, t, k * s_face, fy)
    if llb is not None:
        modes["LLB"] = llb
    return modes


def single_angle_principal(name, fy, axis, Lb=None, Cb=1, beta=0, leg=None, toe=None):
    p, fy = row("SINGLE_ANGLE", name), D(fy)
    legs = sorted([p["d"], p["b"]])
    short, long_, t = legs[0], legs[1], p["t"]
    modes = {}
    if axis == "w":
        my = fy * min(v for k, v in p.items() if k in ("SwA", "SwB", "SwC"))
        modes["Y"] = D("1.5") * my
        b_w = D(beta) if leg == "short" else -D(beta)                             # + short leg in compression
        Lb, cb = D(Lb), min(D(Cb), D("1.5"))
        kk = D("4.4") * b_w * p["rz"] / (Lb * t)
        mcr = 9 * E * p["A"] * p["rz"] * t * cb / (8 * Lb) * (sqrt(1 + kk**2) + kk)   # F10-4
        modes["LTB"] = f10_ltb(my, mcr)
        llb = leg_buckling(long_, t, p["SwC"], fy) if leg == "long" else leg_buckling(short, t, p["SwA"], fy)
    else:
        my = fy * min(p["SzA"], p["SzB"], p["SzC"])
        modes["Y"] = D("1.5") * my
        llb = None
        if toe == "compression":
            options = [v for v in (leg_buckling(long_, t, p["SzC"], fy), leg_buckling(short, t, p["SzA"], fy)) if v]
            llb = min(options) if options else None
    if llb is not None:
        modes["LLB"] = llb
    return modes


def summarize(modes):
    gov = min(modes, key=modes.get)
    return {"modes_kNm": {k: v / 10**6 for k, v in modes.items()}, "governing": gov,
            "Mn_kNm": modes[gov] / 10**6, "phiMn_kNm": D("0.90") * modes[gov] / 10**6}


CASES = {
    "W-F2-yielding": dict(kind="w", name="W18X50", family="W", fy=345, axis="x", Lb=1500),
    "W-F2-inelastic-LTB": dict(kind="w", name="W18X50", family="W", fy=345, axis="x", Lb=4000),
    "W-F2-elastic-LTB-Cb": dict(kind="w", name="W18X50", family="W", fy=345, axis="x", Lb=12000, Cb="1.3"),
    "W-F3-FLB": dict(kind="w", name="W14X90", family="W", fy=345, axis="x", Lb=3000),
    "W-F3-LTB": dict(kind="w", name="W14X90", family="W", fy=345, axis="x", Lb=8000, Cb="1.14"),
    "W-F13-holes": dict(kind="w", name="W14X90", family="W", fy=345, axis="x", Lb=3000, holes=4500, Fu=450),
    "W-F6-minor": dict(kind="w", name="W14X90", family="W", fy=345, axis="y"),
    "C-F2-inelastic-LTB": dict(kind="w", name="C15X50", family="CHANNEL", fy=345, axis="x", Lb=2000),
    "C-F2-elastic-LTB": dict(kind="w", name="C15X50", family="CHANNEL", fy=345, axis="x", Lb=6000),
    "C-F6-minor": dict(kind="w", name="C15X50", family="CHANNEL", fy=345, axis="y"),
    "RHSS-F7-LTB": dict(kind="rhss", name="PTE100X50X3MM", fy=345, axis="x", Lb=3000),
    "RHSS-F7-noncompact": dict(kind="rhss", name="PTE120X60X2MM", fy=345, axis="x", Lb=500),
    "RHSS-F7-minor": dict(kind="rhss", name="PTE120X60X2MM", fy=345, axis="y"),
    "RHSS-F7-3-slender-flange": dict(kind="rhss", name="PTE100X40X1.5MM", fy=345, axis="y"),
    "CHSS-F8-noncompact": dict(kind="chss", name='PTER4"X3.00MM', fy=345),
    "CHSS-F8-compact": dict(kind="chss", name='PTER2"X4.00MM', fy=345),
    "BAR-F11-LTB": dict(kind="bar", H=100, B=20, fy=250, axis="x", Lb=1500),
    "BAR-F11-minor": dict(kind="bar", H=100, B=20, fy=250, axis="y", Lb=1500),
    "ROUND-F11": dict(kind="round", D_=50, fy=250),
    "2L-F9-web-tension": dict(kind="2l", name="2L4X4X1/4", fy=345, Lb=2000, web_legs="tension"),
    "2L-F9-web-compression": dict(kind="2l", name="2L4X4X1/4", fy=345, Lb=2000, web_legs="compression"),
    "2L-F9-LLBB-tension": dict(kind="2l", name="2L6X4X3/8LLBB", fy=345, Lb=3000, web_legs="tension"),
    "2L-F9-SLBB-compression": dict(kind="2l", name="2L6X4X3/8SLBB", fy=345, Lb=3000, web_legs="compression"),
    "2L-F9-elastic-LTB": dict(kind="2l", name="2L4X4X1/4", fy=345, Lb=9000, web_legs="tension"),
    "L-F10-geom-none-toe-comp": dict(kind="lg", name="L4X4X1/4", fy=345, axis="x", restraint="none",
                                     toe="compression", Lb=2000),
    "L-F10-geom-none-toe-tens": dict(kind="lg", name="L4X4X1/4", fy=345, axis="x", restraint="none",
                                     toe="tension", Lb=2000),
    "L-F10-geom-at-max": dict(kind="lg", name="L4X4X1/4", fy=345, axis="y", restraint="at_max_moment",
                              toe="compression", Lb=2000, Cb="1.2"),
    "L-F10-geom-continuous-unequal": dict(kind="lg", name="L6X4X3/8", fy=345, axis="x", restraint="continuous",
                                          toe="compression"),
    "L-F10-w-short-comp": dict(kind="lp", name="L6X4X3/8", fy=345, axis="w", Lb=2000, beta="79.8", leg="short"),
    "L-F10-w-long-comp": dict(kind="lp", name="L6X4X3/8", fy=345, axis="w", Lb=2000, beta="79.8", leg="long"),
    "L-F10-w-equal-Cb-capped": dict(kind="lp", name="L4X4X1/4", fy=345, axis="w", Lb=3000, Cb="1.8", leg="long"),
    "L-F10-z-toes-comp": dict(kind="lp", name="L6X4X3/8", fy=345, axis="z", toe="compression"),
}


def build(spec):
    kind = spec["kind"]
    args = {k: v for k, v in spec.items() if k != "kind"}
    modes = {"w": w_or_channel, "rhss": rect_hss, "chss": round_hss, "bar": solid_rect, "round": solid_round,
             "2l": double_angle, "lg": single_angle_geometric, "lp": single_angle_principal}[kind](**args)
    return {"spec": spec, **summarize(modes)}


def _plain(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


if __name__ == "__main__":
    target = ROOT / "tests/fixtures/chapter_f/reference.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": "ANSI/AISC 360-22 (a360-22w.pdf) F1-F13, B4.1b, errata E25-02; catalog data/sections.xlsx",
               "generator": "tests/oracles/chapter_f.py (Decimal; independent of steel_design)",
               "cases": _plain({cid: build(spec) for cid, spec in CASES.items()})}
    target.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(target)
