"""Reproduce F-09/F-07 against any explicit source root (no formulas modified)."""
import json
from pathlib import Path
import sys


root,out=map(lambda x:Path(x).resolve(),sys.argv[1:])
if out.exists(): raise SystemExit("Choose a new output path")
sys.path.insert(0,str(root))
from src.steel_design.engine import SteelDesignEngine
from src.steel_design.models import SteelCase
from src.steel_design.sections.models import Section
from src.steel_design.sections.repository import SectionRepository
from src.steel_design.run import _build_chapter_admissibility, _build_global_summary

payload=dict(section_name="solid",material=dict(Fy=345,Fu=450),
             custom_section=dict(type="SOLID_RECTANGULAR",B=10,H=100),
             connection=dict(An=1000,U=1),loads=dict(Pu=-310.53105),
             lengths=dict(Lx=3000,Ly=3000,Lz=3000,Lb=3000))
case=SteelCase(**payload)
result=SteelDesignEngine(SectionRepository()).run(case)
check=next(c for c in result.checks if c.clause=="D2-1")
records={"source_root":str(root),"command":[sys.executable,*sys.argv],"input":payload,
    "F09":{"independent_D2_capacity_kN":310.5,"independent_ratio":1.0001,
           "check":check.model_dump(mode="json"),"summary":_build_global_summary(result)},"F07":[]}
section=Section(name="advice geometry only",A=1000,rx=20,ry=10)
for pu,ratios in [(-1,[299.999,300,300.001]),(1,[199.999,200,200.001])]:
    for ratio in ratios:
        data={**payload,"loads":{"Pu":pu},"lengths":dict(Lx=ratio*10,Ly=ratio*10,Lz=ratio*10,Lb=100)}
        advice=_build_chapter_admissibility(SteelCase(**data),section)
        records["F07"].append({"Pu":pu,"KL_over_r":ratio,"advice":advice})
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(records,indent=2,allow_nan=False)+'\n',encoding="utf-8")
print(f"F09: {check.status.value}, published DCR={check.dcr}; 6 F07 cases -> {out}")
