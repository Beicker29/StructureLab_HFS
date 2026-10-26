"""Read-only HFS-002 probes. Run from repository root: python -m docs.audit.hfs002.probes.

Outputs JSON to stdout; never modifies the catalog, engine, cases or expectations.
Engine outputs are characterization, not independent numerical validation.
The H3 ratio example is independent arithmetic on stipulated directional values.
"""
import json
from pathlib import Path

from src.steel_design.engine import SteelDesignEngine
from src.steel_design.models import SteelCase
from src.steel_design.sections.loader import load_sections_from_excel
from src.steel_design.sections.repository import SectionRepository


def main():
    root = Path.cwd()
    repo = SectionRepository()
    repo.load(load_sections_from_excel(str(root / "data/sections.xlsx")))
    engine = SteelDesignEngine(repo)
    captures = []
    common = {
        "section_name": "W12X26", "design_method": "LRFD",
        "material": {"Fy": 345, "Fu": 450, "E": 200000},
        "lengths": {"Lx": 1000, "Ly": 1000, "Lz": 1000, "Lb": 1000},
    }
    for loads in ({"Pu": 0, "Mux": 1, "Muy": 1},):
        payload = dict(common, loads=loads)
        result = engine.run(SteelCase(**payload))
        captures.append({"finding": "F-33", "input": payload,
                         "observed": result.model_dump(mode="json")})
    for name in ("composite_encased_case", "composite_filled_rectangular_hss_case", "composite_beam_case"):
        original = json.loads((root / "examples" / f"{name}.json").read_text(encoding="utf-8-sig"))
        for moment in (1.0, 1000000.0):
            payload = dict(original, loads={"Pu": 0, "Mux": moment, "Muy": 0, "Vux": 0, "Vuy": 0, "Tu": 0})
            result = engine.run(SteelCase(**payload))
            captures.append({"finding": "F-34", "base_example": name,
                             "input": payload, "observed": result.model_dump(mode="json")})
    directional = {"Vrx_kN": 50.0, "Vry_kN": 0.0, "Vcx_kN": 100.0, "Vcy_kN": 200.0}
    normative_ratio = max(directional["Vrx_kN"] / directional["Vcx_kN"],
                          directional["Vry_kN"] / directional["Vcy_kN"])
    independent_max_ratio = max(directional["Vrx_kN"], directional["Vry_kN"]) / max(
        directional["Vcx_kN"], directional["Vcy_kN"])
    print(json.dumps({"purpose": "Characterization, not AISC validation or physical profile oracle",
                      "captures": captures,
                      "F-06-independent-arithmetic": {"inputs": directional,
                          "reference": "S22 H3.2 H3-6, PDF154, printed16.1-86",
                          "max_directional_ratios": normative_ratio,
                          "ratio_of_independent_maxima": independent_max_ratio,
                          "scope": "Algebraic counterexample only; capacities stipulated, not validated HSS capacities"}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
