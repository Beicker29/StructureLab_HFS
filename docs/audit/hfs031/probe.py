"""Compare independent sheets with current D/E only; no expected value generation."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]


def probe():
    spec=importlib.util.spec_from_file_location('hfs031_tests',ROOT/'tests/test_hfs031_de_audit.py')
    t=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    results={}

    def entry(key,method,actual,expected,**context):
        results[f'{key}/{method}']={'actual':actual,'expected':float(expected),
            'difference':actual-float(expected),'relative_percent':100*(actual/float(expected)-1),**context}

    for key,o in t.BANK.items():
        if key.startswith('E7-round-'):
            q=t.axial_calc.calculate_q_factor('CIRCULAR_HSS',{'d_t_ratio':float(o['D_over_t'])},200000,345)
        elif key.startswith(('E7-W-','E7-CHANNEL-','E7-RECTANGULAR_HSS-','E7-SINGLE_ANGLE-')):
            ratios={'W':dict(bf_2tf_ratio=20,h_tw_ratio=75),'CHANNEL':dict(b_t_ratio=10,h_tw_ratio=75),
                'RECTANGULAR_HSS':dict(b_tdes_ratio=400/6,h_tdes_ratio=250/6),'SINGLE_ANGLE':dict(b_t_ratio=50)}
            q=t.axial_calc.calculate_q_factor(o['family'],ratios[o['family']],200000,345)
        else:
            continue
        actual_pn=t.axial_calc.calculate_Fcr_slender(345,float(o['Fe']),q)*float(o['Ag'])
        for method in t.METHODS:
            entry(key,method,t.axial_calc.calculate_available_compressive_strength(actual_pn,method),
                  o[method+'_kN'],Q=q,source=o['reference'],independent=o)
    for method in t.METHODS:
        for name,setup,oracle in [('E4-channel',lambda:t.channel(method),'E4-channel'),
                    ('E4-offset-x',lambda:t.symmetric(method,xa=100),'E4-offset-x'),
                    ('E4-offset-y',lambda:t.symmetric(method,ya=200),'E4-offset-y')]:
            c,s=setup()
            actual=t.AxialE4Rule().check(c,s).capacity
            entry(name,method,actual,t.BANK[oracle][method+'_kN'],case=c.model_dump(mode='json'),
                  section=s.model_dump(mode='json'),engine=t.run(c,s).model_dump(mode='json'))
        for key in ['E5-a-60','E5-a-80','E5-a-120','E5-a-180','E5-b-75','E5-b-120']:
            o=t.BANK[key]
            length=float(o['s'])*30
            c=t.case(method,lengths=dict(Lx=length,Ly=length,Lz=length))
            s=t.Section(name='audit',type='SINGLE_ANGLE',A=2000,rx=30,ry=30,b_t_ratio=8)
            entry(key,method,t.AxialE5Rule().check(c,s).capacity,o[method+'_kN'],
                  eligibility=o['eligible_if_other_conditions_met'],independent=o)
        o=t.BANK['E5-centric-angle']
        c=t.case(method,lengths={k:float(o['L']) for k in ['Lx','Ly','Lz']},
                 connection=dict(angle_compression_mode='both_legs'))
        s=t.Section(name='audit',type='SINGLE_ANGLE',A=float(o['Ag']),Ix=float(o['Ix']),Iy=float(o['Iy']),
                    rx=float(o['ra']),ry=float(o['ra']),rz=float(o['rz']),b_t_ratio=10)
        entry('E5-centric-angle',method,t.AxialE5Rule().check(c,s).capacity,o[method+'_kN'],
              independent=o,engine=t.run(c,s).model_dump(mode='json'))
        c,s=t.round_e7(method)
        norm=float(t.BANK['E7-round-100-80'][method+'_kN'])
        actual=t.AxialE7Rule().check(c,s).capacity
        c.loads.Pu=(norm+actual)/2
        entry('E7-public-false-local-pass',method,actual,norm,case=c.model_dump(mode='json'),
              section=s.model_dump(mode='json'),direct=t.AxialE7Rule().check(c,s).model_dump(mode='json'),
              engine=t.run(c,s).model_dump(mode='json'))
    # Every production file must match HEAD; no E/F/G/H/I or transport changes.
    paths=subprocess.check_output(['git','ls-files','src','examples','schemas','data'],cwd=ROOT,text=True).splitlines()
    changed=subprocess.check_output(['git','diff','--name-only','HEAD','--','src','examples','schemas','data'],cwd=ROOT,text=True).splitlines()
    return {'sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'python':sys.version,'comparisons':results,'protected_changes':changed,
            'protected_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
            'oracle_sha256':hashlib.sha256((ROOT/'tests/fixtures/hfs031/oracles.json').read_bytes()).hexdigest(),
            'warning':'A matching number is not full-domain accreditation. xfails remain open.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=probe()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(f'{len(result["comparisons"])} comparisons; protected changes: {result["protected_changes"]}')
