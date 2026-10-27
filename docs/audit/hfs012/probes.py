"""Before/after behavioral evidence; expected classification is in the tests.

Run with --root pointing to a preserved checkout/copy. Does not write there.
The same synthetic inputs exercise both versions, with no calls to a classifier
to construct expected outputs. Refuse to overwrite previous evidence.
"""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root, out = Path(args.root).resolve(), Path(args.out).resolve()
    if out.exists():
        raise SystemExit("Use a new evidence path")
    sys.path.insert(0, str(root))
    from src.steel_design.domain.routing.profile_router import ProfileRouter
    from src.steel_design.engine import SteelDesignEngine
    from src.steel_design.models import SteelCase
    from src.steel_design.sections.models import Section
    from src.steel_design.sections.repository import SectionRepository

    base = dict(name="probe", type="W", A=8000, Ix=100e6, Iy=20e6, Sx=400000,
                Sy=100000, Zx=500000, Zy=150000, rx=100, ry=50, J=200000,
                Cw=2e11, ho=440, d=450, h=400, bf=160, tf=10, tw=10,
                bf_2tf_ratio=8, h_tw_ratio=40)
    scenarios = [
        ("compact_w", {}, dict(Mux=1)),
        ("noncompact_flange_w", dict(bf=240, bf_2tf_ratio=12), dict(Mux=1)),
        ("noncompact_web_w", dict(d=1250, h=1200, h_tw_ratio=120), dict(Mux=1)),
        ("slender_web_w", dict(d=1650, h=1600, h_tw_ratio=160), dict(Mux=1)),
        ("missing_flange", dict(bf_2tf_ratio=None, bf=None), dict(Mux=1)),
        ("missing_web", dict(h_tw_ratio=None, h=None), dict(Mux=1)),
        ("missing_both", dict(bf_2tf_ratio=None, h_tw_ratio=None, bf=None, h=None), dict(Mux=1)),
        ("derived_compact", dict(bf_2tf_ratio=None, h_tw_ratio=None), dict(Mux=1)),
        ("missing_web_biaxial", dict(h_tw_ratio=None, h=None), dict(Mux=1, Muy=100000)),
        ("compact_channel", dict(type="CHANNEL", bf=80, b_t_ratio=8, bf_2tf_ratio=4), dict(Mux=1)),
        ("full_width_channel", dict(type="CHANNEL", bf=120, b_t_ratio=12, bf_2tf_ratio=6), dict(Mux=1)),
        ("f31_channel_biaxial", dict(type="CHANNEL", bf=120, b_t_ratio=12, bf_2tf_ratio=6,
                                     h_tw_ratio=120, h=1200, d=1250), dict(Mux=1, Muy=1)),
        ("inconsistent_w", dict(bf=600), dict(Mux=1)),
    ]
    results = {}
    for name, changes, loads in scenarios:
        section = Section(**{**base, **changes})
        case = SteelCase(section_name="probe", material=dict(Fy=320, Fu=450, E=200000),
                         loads=loads, lengths=dict(Lx=1000, Ly=1000, Lz=1000, Lb=1000))
        entry = dict(case=case.model_dump(mode="json"), section=section.model_dump(mode="json"))
        try:
            entry["rules"] = [type(r).__name__ for r in ProfileRouter.get_rules(case, section)]
        except Exception as exc:
            entry["routing_error"] = exc.to_dict() if hasattr(exc, "to_dict") else repr(exc)
        repo = SectionRepository()
        repo.load([section])
        try:
            entry["result"] = SteelDesignEngine(repo).run(case).model_dump(mode="json")
        except Exception as exc:
            entry["engine_error"] = exc.to_dict() if hasattr(exc, "to_dict") else repr(exc)
        results[name] = entry
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(root=str(root), python=sys.version, scenarios=results), indent=2), encoding="utf-8")
    print(json.dumps({name: dict(rules=e.get("rules"), status=e.get("result", {}).get("status"))
                      for name, e in results.items()}, indent=2))


if __name__ == "__main__":
    main()
