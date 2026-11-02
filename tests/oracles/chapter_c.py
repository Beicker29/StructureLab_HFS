"""Independent Section C2.3 hand calculations (ANSI/AISC 360-22, a360-22w.pdf pp.16.1-30..31), LRFD.

Reduced stiffnesses of noncomposite members: 0.8*EI and 0.8 times the others, with tau_b = 1.0 always (C2.3(c)).
Decimal arithmetic; never imports steel_design. Regenerates tests/fixtures/chapter_c/reference.json:

    python tests/oracles/chapter_c.py
"""
from decimal import Decimal as D
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chapter_f  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
E, G = D(200000), D(77200)


def case(family, name):
    p = chapter_f.row(family, name)                                             # tau_b = 1.0, C2.3(c)
    return {"EA_star": D("0.8") * E * p["A"], "EI_star_x": D("0.8") * E * p["Ix"],
            "EI_star_y": D("0.8") * E * p["Iy"], "GJ_star": D("0.8") * G * p["J"]}


CASES = {
    "W": dict(family="W", name="W14X90"),
    "RHSS": dict(family="RECTANGULAR_HSS", name="PTE120X60X2MM"),
}


def _plain(value):
    if isinstance(value, D):
        return str(value)
    return {k: _plain(v) for k, v in value.items()} if isinstance(value, dict) else value


if __name__ == "__main__":
    target = ROOT / "tests/fixtures/chapter_c/reference.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": "ANSI/AISC 360-22 (a360-22w.pdf) C2.3; catalog src/steel_design/data/sections.xlsx",
               "generator": "tests/oracles/chapter_c.py (Decimal; independent of steel_design)",
               "cases": _plain({cid: {"spec": spec, **case(**spec)} for cid, spec in CASES.items()})}
    target.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(target)
