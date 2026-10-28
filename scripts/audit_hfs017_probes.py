"""Behavioral before/after probes; use explicit source root and new output file."""
import json
from pathlib import Path
import sys


def capture(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise SystemExit("Use a new evidence file")
    sys.path.insert(0, str(root / "src"))
    from steel_design.models import SteelCase
    from steel_design.sections.models import Section
    from steel_design.domain.rules.flexure_rule import FlexureF11YieldMxRule
    from steel_design.domain.rules.composite_rules import CompositeI2EncasedTensionRule, _steel_shear_capacity_k_n
    from steel_design.codes.aisc_360_22 import axial_calc, tension_calc, shear_calc, combined_hss_calc
    case = SteelCase(section_name="probe", design_method="ASD", material=dict(Fy=320,Fu=450),
                     loads=dict(Mux=1), lengths=dict(Lx=1000,Ly=1000,Lz=1000,Lb=100))
    section = Section(name="probe",type="SOLID_RECTANGULAR",A=20000,Zx=1000000,Sx=666666.6666666666,
                      Zy=500000,Sy=333333.3333333333,d=200,b=100,tw=8,h=180,tf=10)
    empty = case.model_copy(deep=True); empty.loads.Mux=0
    steel_web = section.model_copy(update={"type":"W"})
    probes = {
        "F11_direct_ASD": lambda: FlexureF11YieldMxRule().check(case,section),
        "F11_inactive_ASD": lambda: FlexureF11YieldMxRule().check(empty,section),
        "I2_inactive_ASD": lambda: CompositeI2EncasedTensionRule().check(empty,steel_web),
        "I_steel_shear_ASD": lambda: _steel_shear_capacity_k_n(case,steel_web),
        "D_unknown": lambda: tension_calc.calculate_available_tensile_strength(100000,"LFRD","yielding"),
        "E_unknown": lambda: axial_calc.calculate_available_compressive_strength(100000,"LFRD"),
        "E_zero_unknown": lambda: axial_calc.calculate_available_compressive_strength(0,"LFRD"),
        "G_unknown": lambda: shear_calc.calculate_available_shear_strength(vn_n=100000,design_method="LFRD",phi_v=.9,omega_v=1.67),
        "H_unknown": lambda: combined_hss_calc.calculate_available_torsional_strength(tn_nmm=100000000,design_method="LFRD"),
    }
    records = {}
    for name, call in probes.items():
        try:
            value=call()
            records[name]={"value":value.model_dump(mode="json") if hasattr(value,"model_dump") else value}
        except Exception as exc:
            records[name]={"error":exc.to_dict() if hasattr(exc,"to_dict") else {"type":type(exc).__name__,"message":str(exc)}}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(records,indent=2,allow_nan=False),encoding="utf-8")


if __name__ == "__main__":
    capture(*sys.argv[1:])
