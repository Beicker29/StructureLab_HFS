"""Run identical HFS-013 inputs against an explicit checkout/captured source root.

Usage: python docs/audit/hfs013/probes.py ROOT OUTPUT.json
This is behavioral evidence, not the numerical oracle (see the separate tests).
No source import occurs until ROOT is selected; no baseline output is overwritten.
"""
import json
import math
from pathlib import Path
import sys

root, output = map(lambda p: Path(p).resolve(), sys.argv[1:])
if output.exists():
    raise SystemExit("Choose a new output file")
sys.path.insert(0, str(root))

from src.steel_design.models import SteelCase
from src.steel_design.sections.models import Section
from src.steel_design.sections.repository import SectionRepository
from src.steel_design.engine import SteelDesignEngine
from src.steel_design.domain.rules.combined_hss_rules import HssCombinedH3_2Rule, HssTorsionH3_1Rule
from src.steel_design.codes.aisc_360_22 import combined_hss_calc


def box(**updates):
    ix = (70*130**3 - 60*120**3)/12
    iy = (130*70**3 - 120*60**3)/12
    data = dict(name="probe", type="RECTANGULAR_HSS", A=1900, h=120, b=60, tdes=5,
        Ix=ix, Iy=iy, Sx=ix/65, Sy=iy/35, Zx=79750, Zy=51250,
        rx=math.sqrt(ix/1900), ry=math.sqrt(iy/1900), J=1e6,
        C=2*65*125*5-4.5*(4-math.pi)*125, b_tdes_ratio=12, h_tdes_ratio=24)
    data.update(updates)
    return Section(**data)


def case(**loads):
    return SteelCase(section_name="probe", design_method="LRFD",
        material=dict(Fy=320, Fu=450, E=200000), loads=loads,
        lengths=dict(Lx=1000, Ly=2000, Lz=3000, Lb=100),
        connection=dict(An=1900 if loads.get("Pu",0)<0 else None, U=1))


def observed(call):
    try:
        value = call()
        return value.model_dump(mode="json") if hasattr(value,"model_dump") else value
    except Exception as error:
        return {"error": error.to_dict() if hasattr(error,"to_dict") else
                {"type": type(error).__name__, "message": str(error)}}


def engine(section, loads):
    repo = SectionRepository()
    repo.load([section])
    return SteelDesignEngine(repo).run(loads)


tc = .9*192*(2*65*125*5-4.5*(4-math.pi)*125)/1e6
w = Section(name="probe", type="W", A=6000, d=300, tw=10, h_tw_ratio=25)
tube = Section(name="probe", type="CIRCULAR_HSS", A=475*math.pi, OD=100, tdes=5,
               J=math.pi*(100**4-90**4)/32)
specs = {
    "Vux_only": (box(), case(Vux=82.944)),
    "Vuy_only": (box(), case(Vuy=124.416)),
    "both_unequal": (box(), case(Vux=82.944,Vuy=124.416)),
    "Vu_legacy": (box(), case(Vu=-82.944)),
    "shear_torsion": (box(), case(Vux=82.944,Vuy=62.208,Tu=.5*tc)),
    "all_actions": (box(), case(Pu=-109.44,Mux=3.4452,Muy=.738,Vux=82.944,Vuy=62.208,Tu=.5*tc)),
    "missing_C": (box(C=None),case(Vux=1,Vuy=2,Tu=.5*tc)),
    "missing_wall": (box(b=None),case(Vux=1,Vuy=2,Tu=.5*tc)),
    "threshold_10_percent": (box(),case(Vuy=1,Tu=.1*tc)),
    "threshold_20_percent_independent_float": (box(),case(Vuy=1,Tu=.2*tc)),
    "outside_H3_5": (box(h=1301),case(Vuy=1,Tu=1)),
    "round_user_note_C": (tube,case(Vux=1,Vuy=2,Tu=7)),
    "round_unknown_lengths": (Section(name="probe", type="CIRCULAR_HSS", A=1996*math.pi,
                                     OD=1000,tdes=2,J=1e6),case(Vux=1,Vuy=2,Tu=1)),
    "non_HSS_torsion": (w,case(Vux=1,Tu=1)),
    "channel_G6": (Section(name="probe",type="CHANNEL",A=1000,bf=50,tf=5,b_t_ratio=10),case(Vuy=1)),
    "solid_shear": (Section(name="probe",type="SOLID_CIRCULAR",A=1000),case(Vux=1)),
}
results = {}
for name,(section,loads) in specs.items():
    results[name] = {"section":section.model_dump(mode="json"), "case":loads.model_dump(mode="json"),
                     "engine":observed(lambda:engine(section,loads))}
    if loads.loads.Tu and section.type in {"RECTANGULAR_HSS","CIRCULAR_HSS"}:
        results[name]["H3_1"] = observed(lambda:HssTorsionH3_1Rule().check(loads,section))
        results[name]["H3_2"] = observed(lambda:HssCombinedH3_2Rule().check(loads,section))
results["H3_5_coefficient"] = {str(r): observed(lambda:combined_hss_calc.calculate_rectangular_hss_fcr_h3(
    E_mpa=200000,Fy_mpa=320,h_mm=r,t_mm=1)) for r in (100,260,261)}
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps({"source_root":str(root),"probes":results},ensure_ascii=False,indent=2),encoding="utf-8")
print(output)
