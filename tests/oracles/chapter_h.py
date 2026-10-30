"""Independent Chapter H hand calculations (ANSI/AISC 360-22, a360-22w.pdf pp.16.1-82..88), LRFD.

Component strengths come from the independent oracles of Chapters D, E and F (same folder);
H1-1a/H1-1b, H1-2, H4-1 and H2-1 are written here. Decimal arithmetic; never imports steel_design.
H2: the sense of the stress at A, B and C comes from the coordinates of the points in principal
axes (x, y, tan(alpha) of the catalog), not from a table.
Regenerates tests/fixtures/chapter_h/reference.json:

    python tests/oracles/chapter_h.py
"""
from decimal import Decimal as D
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chapter_d  # noqa: E402
import chapter_e  # noqa: E402
import chapter_f  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
E, PI = chapter_f.E, chapter_f.PI


def h1(pr, pc, mrx, mcx, mry, mcy):
    ax = pr / pc if pr else D(0)
    m = (mrx / mcx if mrx else D(0)) + (mry / mcy if mry else D(0))
    return (ax + D(8) / 9 * m, "H1-1a") if ax >= D("0.2") else (ax / 2 + m, "H1-1b")


def phi_mn(spec):
    return chapter_f.build(spec)["phiMn_kNm"]


def case(family, name, fy, Pu=0, Mux=0, Muy=0, L=None, Lb=None, Cb=1, tension=None, holes=None, e6=None,
         web_legs=None, cb_amplification=False):
    fy, pu, mux, muy = D(fy), D(Pu), D(Mux), D(Muy)
    pc = None
    if pu > 0:
        pc = chapter_e.case(family, name, fy, L, e6=e6)["LRFD_kN"]
    elif pu < 0:
        d_case = chapter_d.case(family, name, fy, tension["Fu"], tension["An"], tension["U"])
        pc = d_case["LRFD_kN"]
    cb, factor = D(Cb), None
    if cb_amplification:                                                        # H1.2, H1-2, alpha = 1.0
        iy = chapter_f.row(family, name)["Iy"]
        pey = PI**2 * E * iy / D(Lb) ** 2
        factor = (1 + (-pu * 1000) / pey).sqrt()
        cb = cb * factor
    kind = {"W": "w", "CHANNEL": "w", "RECTANGULAR_HSS": "rhss", "DOUBLE_ANGLE": "2l"}[family]
    base = {"kind": kind, "name": name, "fy": fy}
    if kind == "w":
        base["family"] = family
    mcx = mcy = None
    if mux:
        spec = {**base, "axis": "x", "Lb": Lb, "Cb": cb} if kind != "2l" else {**base, "Lb": Lb, "web_legs": web_legs}
        if holes is not None:                                                   # F13.1 is a Chapter F limit state
            spec.update(holes=holes, Fu=tension["Fu"])
        mcx = phi_mn(spec)
    if muy:
        mcy = phi_mn({**base, "axis": "y", **({"Lb": Lb} if kind == "rhss" else {})})
    ratio, equation = h1(abs(pu), pc, mux, mcx, muy, mcy)
    out = {"Pc_kN": pc, "Mcx_kNm": mcx, "Mcy_kNm": mcy, "Cb_factor": factor, "H1": ratio, "H1_equation": equation}
    if holes is not None:                                                        # H4-1 for the tension flange
        p = chapter_f.row(family, name)
        fu, afn, afg = D(tension["Fu"]), D(holes), p["bf"] * p["tf"]
        yt = D(1) if fy / fu <= D("0.8") else D("1.1")
        if fu * afn >= yt * fy * afg:
            mcx_r = D("0.90") * fy * p["Zx"] / 10**6                             # Mp, F13.1 does not apply
        else:
            mcx_r = D("0.90") * fu * afn / afg * p["Sx"] / 10**6                 # F13-1
        pc_r = chapter_d.case(family, name, fy, tension["Fu"], tension["An"], tension["U"])["modes"]["TR"]["LRFD_kN"]
        out.update(H4=-pu / pc_r + mux / mcx_r, H4_Pc_kN=pc_r, H4_Mcx_kNm=mcx_r)
    out["governing"] = max((k for k in ("H1", "H4") if k in out), key=lambda k: out[k])
    out["ratio"] = out[out["governing"]]
    return out


def angle_points(p):
    """Signed distances of A, B, C to the w axis (along z) and to the z axis (along w).

    Heel at the origin, long leg along y, short leg along x; z makes alpha with y (catalog convention).
    """
    short, long_ = sorted([p["d"], p["b"]])
    c, s = chapter_e.cos_sin(chapter_e.atan(p["tan(α)"]))
    coordinates = {"A": (short, D(0)), "B": (D(0), D(0)), "C": (D(0), long_)}
    out = {}
    for point, (x, y) in coordinates.items():
        dx, dy = x - p["x"], y - p["y"]
        out[point] = (-dx * s + dy * c, dx * c + dy * s)
    return out


def _sign(value):
    return D(0) if abs(value) < D("1e-9") else D(1 if value > 0 else -1)


def h2_case(name, fy, Pu=0, Mw=0, Mz=0, L=None, Lb=None, Cb=1, beta=0, leg="long", toe=None, tension=None):
    p, fy, pu, mw, mz = chapter_f.row("SINGLE_ANGLE", name), D(fy), D(Pu), D(Mw), D(Mz)
    pc = mcw = mcz = None
    if pu > 0:
        pc = chapter_e.case("SINGLE_ANGLE", name, fy, L)["LRFD_kN"]
    elif pu < 0:
        pc = chapter_d.case("SINGLE_ANGLE", name, fy, tension["Fu"], tension["An"], tension["U"])["LRFD_kN"]
    if mw:
        mcw = phi_mn({"kind": "lp", "name": name, "fy": fy, "axis": "w", "Lb": Lb, "Cb": Cb, "beta": beta, "leg": leg})
    if mz:
        mcz = phi_mn({"kind": "lp", "name": name, "fy": fy, "axis": "z", "toe": toe})
    points = angle_points(p)
    compressed_w = _sign(points["C" if leg == "long" else "A"][0])              # side of w in compression
    toe_side = _sign(points["C"][1])
    compressed_z = toe_side if toe == "compression" else -toe_side              # side of z in compression
    axial = (pu / pc) if pu else D(0)                                           # + compression, - tension
    ratios = {}
    for point, (to_w, to_z) in points.items():
        w = _sign(to_w) * compressed_w * mw / mcw if mw else D(0)
        z = _sign(to_z) * compressed_z * mz / mcz if mz else D(0)
        ratios[point] = abs(axial + w + z)                                      # H2-1
    governing = max(ratios, key=ratios.get)
    return {"Pc_kN": pc, "Mcw_kNm": mcw, "Mcz_kNm": mcz, "ratios": ratios, "governing": f"H2-{governing}",
            "ratio": ratios[governing]}


TENSION = {"Fu": 450, "An": 15000, "U": "0.9"}
H2_CASES = {
    "L-H2-comp-long-toe": dict(name="L6X4X3/8", fy=345, Pu=100, Mw=5, Mz=2, L=2000, Lb=2000, beta="79.8", leg="long",
                               toe="tension"),
    "L-H2-comp-short-toe": dict(name="L6X4X3/8", fy=345, Pu=100, Mw=5, Mz=2, L=2000, Lb=2000, beta="79.8", leg="short",
                                toe="compression"),
    "L-H2-comp-axial-Mw": dict(name="L8X4X1/2", fy=345, Pu=300, Mw=20, L=1524, Lb=1524, beta="139.2", leg="long"),
    "L-H2-comp-heel-governs": dict(name="L8X4X1/2", fy=345, Pu=150, Mz=5, L=1524, toe="tension"),
    "L-H2-comp-FAIL": dict(name="L4X4X1/4", fy=450, Pu=120, Mz=4, L=2000, toe="compression"),
    "L-H2-tension": dict(name="L6X4X3/8", fy=345, Pu=-300, Mw=8, Mz=3, Lb=2000, beta="79.8", leg="short", toe="tension",
                         tension={"Fu": 450, "An": 1900, "U": "0.85"}),
    "L-H2-biaxial-equal": dict(name="L4X4X1/4", fy=345, Mw=3, Mz=3, Lb=3000, toe="compression"),
}
CASES = {
    "W-H1-1a": dict(family="W", name="W14X90", fy=345, Pu=1500, Mux=200, Muy=50, L=4000, Lb=4000),
    "W-H1-1b": dict(family="W", name="W14X90", fy=345, Pu=300, Mux=200, Muy=50, L=4000, Lb=4000),
    "W-biaxial-no-axial": dict(family="W", name="W14X90", fy=345, Mux=300, Muy=100, Lb=3000),
    "W-H1.2-tension": dict(family="W", name="W14X90", fy=345, Pu=-800, Mux=400, Muy=50, Lb=8000, Cb="1.14",
                           tension=TENSION),
    "W-H1.2-Cb-amplified": dict(family="W", name="W14X90", fy=345, Pu=-800, Mux=400, Muy=50, Lb=8000, Cb="1.14",
                                tension=TENSION, cb_amplification=True),
    "W-H4-holes": dict(family="W", name="W14X90", fy=345, Pu=-1500, Mux=300, Lb=3000, tension=TENSION, holes=4500),
    "C-H1-1a": dict(family="CHANNEL", name="C15X50", fy=345, Pu=800, Mux=100, L=3000, Lb=2000),
    "RHSS-H1-1a": dict(family="RECTANGULAR_HSS", name="PTE100X100X4MM", fy=345, Pu=200, Mux=5, Muy=3, L=3000,
                       Lb=3000),
    "2L-H1-1b": dict(family="DOUBLE_ANGLE", name="2L4X4X1/4", fy=345, Pu=40, Mux=5, L=2000, Lb=2000,
                     e6=("welded", 500), web_legs="tension"),
}


def _plain(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


if __name__ == "__main__":
    target = ROOT / "tests/fixtures/chapter_h/reference.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": "ANSI/AISC 360-22 (a360-22w.pdf) H1, H2, H4; components from the D, E and F oracles",
               "generator": "tests/oracles/chapter_h.py (Decimal; independent of steel_design)",
               "cases": _plain({cid: {"spec": spec, **case(**spec)} for cid, spec in CASES.items()}),
               "h2_cases": _plain({cid: {"spec": spec, **h2_case(**spec)} for cid, spec in H2_CASES.items()})}
    target.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(target)
