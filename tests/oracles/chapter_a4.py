"""Independent Appendix 4, Section 4.2.4d hand calculations (ANSI/AISC 360-22, a360-22w.pdf pp.16.1-233..244; errata 2025), LRFD.

Decimal arithmetic; never imports steel_design. Tables A-4.2.1, A-4.2.2 and A-4.2.4 are typed here again from the Specification.
Regenerates tests/fixtures/chapter_a4/reference.json:

    python tests/oracles/chapter_a4.py
"""
from decimal import Decimal as D, getcontext
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chapter_e  # noqa: E402
import chapter_f  # noqa: E402
import chapter_i  # noqa: E402

getcontext().prec = 50
ROOT = Path(__file__).resolve().parents[2]
PI = D("3.14159265358979323846264338327950288419716939937510")
E, G = D(200000), D(77200)
#        T     kE      kp      ky
STEEL = (("20", "1", "1", "1"), ("93", "1", "1", "1"), ("200", "0.9", "0.8", "1"), ("320", "0.78", "0.58", "1"), ("400", "0.7", "0.42", "1"),
         ("430", "0.67", "0.4", "0.94"), ("540", "0.49", "0.29", "0.66"), ("650", "0.22", "0.13", "0.35"), ("760", "0.11", "0.06", "0.16"),
         ("870", "0.07", "0.04", "0.07"), ("980", "0.05", "0.03", "0.04"), ("1100", "0.02", "0.01", "0.02"), ("1200", "0", "0", "0"))
#           T     kc      kEc (normal weight)
CONCRETE = (("20", "1", "1"), ("93", "0.95", "0.93"), ("200", "0.9", "0.75"), ("290", "0.86", "0.61"), ("320", "0.83", "0.57"),
            ("430", "0.71", "0.38"), ("540", "0.54", "0.2"), ("650", "0.38", "0.092"), ("760", "0.21", "0.073"), ("870", "0.1", "0.055"),
            ("980", "0.05", "0.036"), ("1100", "0.01", "0.018"), ("1200", "0", "0"))
BEAM = (("20", "1"), ("150", "0.98"), ("320", "0.95"), ("430", "0.89"), ("540", "0.71"), ("650", "0.49"), ("760", "0.26"), ("870", "0.12"),
        ("980", "0.05"), ("1100", "0"))


def table(rows, T, column):
    T = D(str(T))
    for low, high in zip(rows, rows[1:]):
        if T <= D(high[0]):
            a, b = D(low[column]), D(high[column])
            return a + (b - a) * (T - D(low[0])) / (D(high[0]) - D(low[0]))
    raise ValueError(T)


def steel(T):
    return {"kE": table(STEEL, T, 1), "kp": table(STEEL, T, 2), "ky": table(STEEL, T, 3)}


def fn_a4_9(fy_t, fe_t):
    return D("0.42") ** ((fy_t / fe_t).sqrt()) * fy_t


def tension(name, fy, fu, An, U, T):
    """4.2.4d(a): D2 with Fy(T) and Fu(T); Fu(T) = Fy(T) above 400 deg C."""
    ag = chapter_e.row("W", name)["A"]
    fy_t = steel(T)["ky"] * D(fy)
    fu_t = fy_t if D(str(T)) > 400 else D(fu)
    ty, tr = D("0.9") * fy_t * ag, D("0.75") * fu_t * D(An) * D(str(U))
    return {"phiPn_kN": min(ty, tr) / 1000, "Fu_T": fu_t}


def compression(family, name, fy, Lx, Ly, Lz, T):
    """4.2.4d(b): A-4-9 with Fe(T) of E3 and, by the user's decision DA4-2, of E4, with E(T) and G(T)."""
    p = chapter_e.row(family, name)
    k = steel(T)
    Lx, Ly, Lz = D(Lx), D(Ly), D(Lz)
    e_t, g_t, fy_t = k["kE"] * E, k["kE"] * G, k["ky"] * D(fy)
    modes = {"FB-x": PI**2 * e_t / (Lx / p["rx"]) ** 2, "FB-y": PI**2 * e_t / (Ly / p["ry"]) ** 2}
    if family == "W":
        modes["TB"] = (PI**2 * e_t * p["Cw"] / Lz**2 + g_t * p["J"]) / (p["Ix"] + p["Iy"])                 # E4-2
    if family == "CHANNEL":
        fez = (PI**2 * e_t * p["Cw"] / Lz**2 + g_t * p["J"]) / (p["A"] * p["ro"] ** 2)                     # E4-7
        fex = modes["FB-x"]
        modes["FTB"] = (fex + fez) / (2 * p["H"]) * (1 - (1 - 4 * fex * fez * p["H"] / (fex + fez) ** 2).sqrt())  # E4-3
    pn = min(fn_a4_9(fy_t, fe) * p["A"] for fe in modes.values())
    return {"Pn_kN": pn / 1000, "phiPn_kN": D("0.9") * pn / 1000, "mode": min(modes, key=lambda m: fn_a4_9(fy_t, modes[m]))}


def ltb_compact_w(name, fy, T, Lb, Cb=1):
    """4.2.4d(e): A-4-13 to A-4-19M, capped by Mp(T)."""
    p = chapter_f.row("W", name)
    k, T, fy, Lb, Cb = steel(T), D(str(T)), D(fy), D(Lb), D(str(Cb))
    e_t, fy_t = k["kE"] * E, k["ky"] * fy
    fl = fy * (k["kp"] - D("0.3") * k["ky"])
    mp = fy_t * p["Zx"]
    cx = min(D("0.6") + T / 250, D(3))
    rts = ((p["Iy"] * p["Cw"]).sqrt() / p["Sx"]).sqrt()
    jc = p["J"] / (p["Sx"] * p["ho"])
    lr = D("1.95") * rts * e_t / fl * (jc + (jc**2 + D("6.76") * (fl / e_t) ** 2).sqrt()).sqrt()
    if Lb <= lr:
        mn = Cb * (fl * p["Sx"] + (mp - fl * p["Sx"]) * (1 - Lb / lr) ** cx)
        equation = "A-4-13"
    else:
        fcr = Cb * PI**2 * e_t / (Lb / rts) ** 2 * (1 + D("0.078") * jc * (Lb / rts) ** 2).sqrt()
        mn, equation = fcr * p["Sx"], "A-4-14"
    mn = min(mn, mp)
    return {"Lr_T_mm": lr, "Mn_kNm": mn / 10**6, "phiMn_kNm": D("0.9") * mn / 10**6, "equation": equation}


def noncompact_w(name, fy, T, Lb):
    """4.2.4d(e): F3 and F2 with E(T), Fy(T); lambda_p, lambda_r at ambient temperature (Commentary 4.2.4d)."""
    p = chapter_f.row("W", name)
    k, fy, Lb = steel(T), D(fy), D(Lb)
    e_t, fy_t = k["kE"] * E, k["ky"] * fy
    root = (E / fy).sqrt()
    lp, lr = D("0.38") * root, root
    mp = fy_t * p["Zx"]
    flb = mp - (mp - D("0.7") * fy_t * p["Sx"]) * (p["bf/2tf"] - lp) / (lr - lp)                               # F3-1
    rts = ((p["Iy"] * p["Cw"]).sqrt() / p["Sx"]).sqrt()
    jc = p["J"] / (p["Sx"] * p["ho"])
    lbp = D("1.76") * p["ry"] * (e_t / fy_t).sqrt()
    lbr = D("1.95") * rts * e_t / (D("0.7") * fy_t) * (jc + (jc**2 + D("6.76") * (D("0.7") * fy_t / e_t) ** 2).sqrt()).sqrt()
    if Lb <= lbp:
        ltb = mp
    elif Lb <= lbr:
        ltb = min(mp - (mp - D("0.7") * fy_t * p["Sx"]) * (Lb - lbp) / (lbr - lbp), mp)                        # F2-2
    else:
        ltb = min(PI**2 * e_t / (Lb / rts) ** 2 * (1 + D("0.078") * jc * (Lb / rts) ** 2).sqrt() * p["Sx"], mp)  # F2-3, F2-4
    return {"Mn_kNm": min(flb, ltb) / 10**6}


def minor_axis_w(name, fy, T):
    """4.2.4d(e): F6-1 with Fy(T)."""
    p = chapter_f.row("W", name)
    fy_t = steel(T)["ky"] * D(fy)
    return {"Mn_kNm": min(fy_t * p["Zy"], D("1.6") * fy_t * p["Sy"]) / 10**6}


def shear_w(name, fy, T, axis):
    """4.2.4d(g): shear yielding; G2.1(a) phi = 1.0 about x and G6 phi = 0.9 about y, ambient factors (4.1.2)."""
    p = chapter_f.row("W", name)
    fy_t = steel(T)["ky"] * D(fy)
    if axis == "x":
        return {"phiVn_kN": D("0.6") * fy_t * p["d"] * p["tw"] / 1000}
    return {"phiVn_kN": D("0.9") * 2 * D("0.6") * fy_t * p["bf"] * p["tf"] / 1000}


def interaction(name, fy, T, Pu, Mu, L):
    """4.2.4d(h): H1-1a or H1-1b with the fire strengths."""
    pc = compression("W", name, fy, L, L, L, T)["phiPn_kN"]
    mc = ltb_compact_w(name, fy, T, L)["phiMn_kNm"]
    pu, mu = D(Pu), D(Mu)
    ratio = pu / pc + D(8) / 9 * mu / mc if pu / pc >= D("0.2") else pu / pc / 2 + mu / mc
    return {"ratio": ratio}


def _filled(name, fy, fc, wc, L, T, elements, bars=(), bar_T=None, round_=False):
    """4.2.4d(c): I2-9 to I2-13 at temperature, A-4-11, I2-4 (errata 2025). Bars: Asr*Es/Ec at the temperature of the bars (DA4-5)."""
    fy, fc, L = D(fy), D(fc), D(L)
    k = steel(T)
    if round_:
        p = chapter_f.row("CIRCULAR_HSS", name)
        ri = p["OD"] / 2 - p["tdes"]
        afill, lam, lp, lr, c2 = PI * ri**2, p["OD"] / p["tdes"], D("0.15") * E / fy, D("0.19") * E / fy, D("0.95")
    else:
        g = chapter_i.filled_rect(name)
        p, afill = g["p"], g["Ac"]
        root = (E / fy).sqrt()
        lam, lp, lr, c2 = max(p["b"], p["h"]) / g["t"], D("2.26") * root, 3 * root, D("0.85")
    ec = chapter_i.ec(wc, fc)
    fy_t, es_t = k["ky"] * fy, k["kE"] * E
    asr = sum((D(str(a)) for a, *_ in bars), D(0))
    fc_a = sum((table(CONCRETE, t, 1) * fc * D(str(a)) for a, _, _, t in elements), D(0))
    ec_ix = sum((table(CONCRETE, t, 2) * ec * D(str(i)) for _, i, _, t in elements), D(0))
    ec_iy = sum((table(CONCRETE, t, 2) * ec * D(str(i)) for _, _, i, t in elements), D(0))
    es_b = steel(bar_T)["kE"] * E if bars else D(0)
    if bars:
        fc_a += table(CONCRETE, bar_T, 1) * fc * asr * es_b / (table(CONCRETE, bar_T, 2) * ec)
    pp = fy_t * p["A"] + c2 * fc_a
    pno = pp
    if lam > lp:
        py = fy_t * p["A"] + D("0.7") * fc_a
        pno = pp - (pp - py) / (lr - lp) ** 2 * (lam - lp) ** 2
    c3 = min(D("0.45") + 3 * (p["A"] + asr) / (p["A"] + afill), D("0.9"))
    isr_x = sum((PI * D(str(db)) ** 4 / 64 + D(str(a)) * D(str(y)) ** 2 for a, db, x, y in bars), D(0))
    isr_y = sum((PI * D(str(db)) ** 4 / 64 + D(str(a)) * D(str(x)) ** 2 for a, db, x, y in bars), D(0))
    ei_x = es_t * p["Ix"] + es_b * isr_x + c3 * ec_ix
    ei_y = es_t * p["Iy"] + es_b * isr_y + c3 * ec_iy
    pn = min(D("0.54") ** ((pno / (PI**2 * ei / L**2)) ** D("0.3")) * pno for ei in (ei_x, ei_y))
    return {"Pn_kN": pn / 1000, "phiPn_kN": D("0.75") * pn / 1000}


def filled_uniform(name, fy, fc, wc, L, T, Tc):
    g = chapter_i.filled_rect(name)
    return _filled(name, fy, fc, wc, L, T, [(g["Ac"], g["Icx"], g["Icy"], Tc)])


def filled_elements(name, fy, fc, wc, L, T, shares):
    """The concrete as elements with the given (share of Ac and Ic, temperature)."""
    g = chapter_i.filled_rect(name)
    elements = [(g["Ac"] * D(str(s)), g["Icx"] * D(str(s)), g["Icy"] * D(str(s)), t) for s, t in shares]
    return {**_filled(name, fy, fc, wc, L, T, elements), "elements": elements}


def filled_round_bars(name, fy, fc, wc, L, T, Tc, bars, bar_T):
    p = chapter_f.row("CIRCULAR_HSS", name)
    ri = p["OD"] / 2 - p["tdes"]
    asr = sum(D(str(a)) for a, *_ in bars)
    ic = PI * ri**4 / 4
    isr_x = sum(PI * D(str(db)) ** 4 / 64 + D(str(a)) * D(str(y)) ** 2 for a, db, x, y in bars)
    isr_y = sum(PI * D(str(db)) ** 4 / 64 + D(str(a)) * D(str(x)) ** 2 for a, db, x, y in bars)
    return _filled(name, fy, fc, wc, L, T, [(PI * ri**2 - asr, ic - isr_x, ic - isr_y, Tc)], bars=bars, bar_T=bar_T, round_=True)


def wall_uniform(fy, fc, wc, height, wall_length, tsc, t, st, T, Tc):
    """4.2.4d(d) on the column of unit width: I2-15, I1-1, A-4-12, I2-4; one concrete element."""
    tsc, t, st, fy, fc = D(str(tsc)), D(str(t)), D(str(st)), D(fy), D(fc)
    k = steel(T)
    a_s, a_c = 2 * st * t, (tsc - 2 * t) * st
    ic = st * (tsc - 2 * t) ** 3 / 12
    pno = k["ky"] * fy * a_s + D("0.85") * table(CONCRETE, Tc, 1) * fc * a_c
    # The steel plates as in the layered sum of chapter_i.wall_fire_oracle: own inertia plus the parallel axis term.
    i_s = 2 * (st * t**3 / 12 + st * t * (tsc / 2 - t / 2) ** 2)
    ei = k["kE"] * E * i_s + D("0.35") * table(CONCRETE, Tc, 2) * chapter_i.ec(wc, fc) * ic
    pe = PI**2 * ei / D(height) ** 2
    pn = D("0.32") ** ((pno / pe) ** D("0.3")) * pno
    return {"Pno_T_kN": pno / 1000, "Pn_T_kN": pn / 1000, "phiPn_kN": D("0.9") * pn * D(wall_length) / st / 1000}


def beam(T, **member):
    """4.2.4d(f): A-4-20 on the Mn of Chapter I, ambient."""
    mn = chapter_i.beam_flexure(**member)["Mn_kNm"]
    kcb = table(BEAM, T, 1)
    return {"kcb": kcb, "Mn_kNm": kcb * mn, "phiMn_kNm": D("0.9") * kcb * mn}


FUNCTIONS = {"tension": tension, "compression": compression, "ltb_compact_w": ltb_compact_w, "noncompact_w": noncompact_w, "minor_axis_w": minor_axis_w,
             "shear_w": shear_w, "interaction": interaction, "filled_uniform": filled_uniform, "filled_elements": filled_elements,
             "filled_round_bars": filled_round_bars, "wall_uniform": wall_uniform, "beam": beam}
BARS_ROUND = [(200, 16, 0, 55), (200, 16, 0, -55), (200, 16, 55, 0), (200, 16, -55, 0)]
BEAM_MEMBER = dict(name="W21X50", fy=345, fc=28, wc=2320, span=13716, spacing=3048, tc=114, hr=0, n=44, d=19, Fu=450, Rg=1, Rp="0.75")
CASES = {
    "T-W-350": dict(kind="tension", name="W14X90", fy=345, fu=448, An=15000, U=0.9, T=350),
    "T-W-550": dict(kind="tension", name="W14X90", fy=345, fu=448, An=15000, U=0.9, T=550),
    "T-W-1000": dict(kind="tension", name="W14X90", fy=345, fu=448, An=15000, U=0.9, T=1000),
    "C-W-550": dict(kind="compression", family="W", name="W14X90", fy=345, Lx=6000, Ly=4000, Lz=4000, T=550),
    "C-W-torsional": dict(kind="compression", family="W", name="W14X90", fy=345, Lx=2000, Ly=2000, Lz=9000, T=450),
    "C-W-250": dict(kind="compression", family="W", name="W12X72", fy=345, Lx=3000, Ly=1500, Lz=1500, T=250),
    "C-channel": dict(kind="compression", family="CHANNEL", name="C8X18.75", fy=345, Lx=2000, Ly=2000, Lz=2000, T=500),
    "C-HSS": dict(kind="compression", family="RECTANGULAR_HSS", name="PTE200X200X7MM", fy=345, Lx=3000, Ly=3000, Lz=3000, T=600),
    "M-W-A413": dict(kind="ltb_compact_w", name="W18X50", fy=345, T=550, Lb=1500),
    "M-W-A413-Cb": dict(kind="ltb_compact_w", name="W18X50", fy=345, T=300, Lb=3000, Cb=1.3),
    "M-W-A414": dict(kind="ltb_compact_w", name="W18X50", fy=345, T=300, Lb=15000),
    "M-W-cap": dict(kind="ltb_compact_w", name="W18X50", fy=345, T=550, Lb=100, Cb=3),
    "M-W-noncompact": dict(kind="noncompact_w", name="W14X90", fy=345, T=550, Lb=2000),
    "M-W-minor": dict(kind="minor_axis_w", name="W18X50", fy=345, T=650),
    "V-W-x": dict(kind="shear_w", name="W18X50", fy=345, T=600, axis="x"),
    "V-W-y": dict(kind="shear_w", name="W18X50", fy=345, T=600, axis="y"),
    "H-W": dict(kind="interaction", name="W12X72", fy=345, T=500, Pu=300, Mu=60, L=2000),
    "F-rect-compact": dict(kind="filled_uniform", name="PTE100X50X3MM", fy=345, fc=35, wc=2320, L=2000, T=600, Tc=300),
    "F-rect-noncompact": dict(kind="filled_uniform", name="PTE120X60X2MM", fy=345, fc=35, wc=2320, L=2000, T=450, Tc=250),
    "F-rect-elements": dict(kind="filled_elements", name="PTE200X200X7MM", fy=345, fc=35, wc=2320, L=4000, T=700, shares=((0.25, 600), (0.25, 450), (0.5, 200))),
    "F-round-bars": dict(kind="filled_round_bars", name='PTER8"X5.00MM', fy=345, fc=35, wc=2320, L=3000, T=500, Tc=280, bars=BARS_ROUND, bar_T=350),
    "W-uniform": dict(kind="wall_uniform", fy=345, fc=40, wc=2320, height=5000, wall_length=3300, tsc=600, t=14, st=300, T=800, Tc=250),
    "B-650": dict(kind="beam", T=650, **BEAM_MEMBER),
    "B-250": dict(kind="beam", T=250, **BEAM_MEMBER),
}


def _plain(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return {k: _plain(v) for k, v in value.items()} if isinstance(value, dict) else value


if __name__ == "__main__":
    target = ROOT / "tests/fixtures/chapter_a4/reference.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    cases = {cid: {"spec": spec, **FUNCTIONS[spec["kind"]](**{k: v for k, v in spec.items() if k != "kind"})} for cid, spec in CASES.items()}
    payload = {"source": "ANSI/AISC 360-22 (a360-22w.pdf) Appendix 4, 4.2.3b and 4.2.4d; errata 2025; catalog data/sections.xlsx",
               "generator": "tests/oracles/chapter_a4.py (Decimal; independent of steel_design)", "cases": _plain(cases)}
    target.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(target)
