"""Independent Chapter D hand calculations (ANSI/AISC 360-22, a360-22w.pdf pp.16.1-32..34).

Decimal arithmetic; Ag is read from data/sections.xlsx with openpyxl; never imports
steel_design. Regenerates tests/fixtures/chapter_d/reference.json:

    python tests/oracles/chapter_d.py
"""
from decimal import Decimal as D
import json
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
SHEETS = {"W": "W_IPE_HEA_HEB", "CHANNEL": "C", "RECTANGULAR_HSS": "PTE_RECT", "CIRCULAR_HSS": "PTE_RED",
          "SINGLE_ANGLE": "L", "DOUBLE_ANGLE": "2L"}


def gross_area(family, name):
    ws = openpyxl.load_workbook(ROOT / "data/sections.xlsx", read_only=True, data_only=True)[SHEETS[family]]
    rows = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else None for h in next(rows)]
    for values in rows:
        if values[0] is not None and str(values[0]).strip().upper() == name:
            return D(repr(values[header.index("A")]))
    raise KeyError(name)


def case(family, name, Fy, Fu, An, U):
    ag, fy, fu, an, u = gross_area(family, name), D(Fy), D(Fu), D(An), D(U)
    ty = fy * ag / 1000                     # D2-1 (kN)
    ae = an * u                             # D3-1
    tr = fu * ae / 1000                     # D2-2 (kN)
    modes = {"TY": {"Pn_kN": ty, "LRFD_kN": D("0.90") * ty, "area_mm2": ag},     # phi_t = 0.90
             "TR": {"Pn_kN": tr, "LRFD_kN": D("0.75") * tr, "area_mm2": ae}}     # phi_t = 0.75
    return {"family": family, "section": name, "Fy": Fy, "Fu": Fu, "An": An, "U": U, "modes": modes,
            "LRFD_kN": min(m["LRFD_kN"] for m in modes.values()),
            "governing": min(modes, key=lambda n: modes[n]["LRFD_kN"])}


CASES = {
    "W-rupture-governs": dict(family="W", name="W14X90", Fy=345, Fu=450, An=15000, U="0.9"),
    "W-yielding-governs": dict(family="W", name="W14X90", Fy=345, Fu=450, An=17100, U=1),
    # Nominal TR/TY = 1.199 < 0.90/0.75 = 1.2: rupture governs although its Pn is the larger one.
    "W-rupture-governs-larger-Pn": dict(family="W", name="W14X90", Fy=345, Fu=450, An=15719, U=1),
    "C-case2-U": dict(family="CHANNEL", name="C15X50", Fy=250, Fu=400, An=8600, U="0.85"),
    "L-case8-U": dict(family="SINGLE_ANGLE", name="L4X4X1/4", Fy=250, Fu=400, An=1100, U="0.6"),
    "2L-welded": dict(family="DOUBLE_ANGLE", name="2L4X4X1/4", Fy=345, Fu=450, An=2490, U="0.87"),
    "RHSS-slotted": dict(family="RECTANGULAR_HSS", name="PTE100X100X4MM", Fy=345, Fu=450, An=1350, U="0.80"),
    "CHSS-slotted": dict(family="CIRCULAR_HSS", name='PTER4"X3.00MM', Fy=345, Fu=450, An=950, U="0.87"),
}


def _plain(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


if __name__ == "__main__":
    target = ROOT / "tests/fixtures/chapter_d/reference.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": "ANSI/AISC 360-22 (a360-22w.pdf) D2, D3; catalog data/sections.xlsx (A)",
               "generator": "tests/oracles/chapter_d.py (Decimal; independent of steel_design)",
               "cases": _plain({cid: case(**spec) for cid, spec in CASES.items()})}
    target.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(target)
