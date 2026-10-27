"""Strict behavioral comparison: only new D2 factor metadata is permitted.

No numeric tolerance, ignored status, or coverage exception. Independent numeric
oracles live in tests; this script checks regressions, not AISC correctness.
"""
import json
from pathlib import Path
import sys


def compare(old,new,path="",method="LRFD"):
    if old==new:
        return []
    changes=[]
    if isinstance(old,dict) and isinstance(new,dict):
        method=new.get("coverage",{}).get("method",new.get("input",{}).get("design_method",method))
        old=dict(old)
        if old.get("clause") in {"D2-1","D2-2"} and "inputs" in old and "design_factor" not in old:
            phi,omega=(.9,1.67) if old["clause"]=="D2-1" else (.75,2.0)
            expected={"design_method":method,"phi":phi if method=="LRFD" else None,
                      "omega":omega if method=="ASD" else None,
                      "capacity_expression":"phi*Pn" if method=="LRFD" else "Pn/omega"}
            assert new.get("design_factor")==expected,(path,new.get("design_factor"),expected)
            old["design_factor"]=expected
            changes.append({"path":path+"/design_factor","added":expected})
        assert old.keys()==new.keys(),(path,"unexpected keys",old.keys(),new.keys())
        for key in old:
            changes.extend(compare(old[key],new[key],path+"/"+key,method))
    elif isinstance(old,list) and isinstance(new,list):
        assert len(old)==len(new),(path,"length")
        for i,(a,b) in enumerate(zip(old,new)):
            changes.extend(compare(a,b,path+"/"+str(i),method))
    else:
        raise AssertionError((path,old,new))
    return changes


def main(before,after,cli_before,cli_after,out):
    read=lambda p:json.loads(Path(p).read_text(encoding="utf-8"))
    output=Path(out)
    if output.exists(): raise SystemExit("Use a new evidence path")
    b,a=read(before),read(after)
    differences=compare(b,a)
    cb,ca=read(cli_before),read(cli_after)
    assert cb.keys()==ca.keys()
    cli={}
    for key in cb:
        x,y=cb[key],ca[key]
        assert x["execution"]["returncode"]==y["execution"]["returncode"]
        assert x["source_sha256"]==y["source_sha256"]
        cli[key]=compare(x["normalized_cli"],y["normalized_cli"])+compare(x["normalized_details"],y["normalized_details"])
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({"accepted":True,"engine_case_files":len(b),
        "engine_changes":differences,"cli_runs":len(cli),"cli_changes":cli,
        "numeric_status_coverage_and_other_trace_changes":0},indent=2),encoding="utf-8")
    print("Accepted: only documented D2 factor traces added; 12 examples and 24 CLI runs preserved.")


if __name__=="__main__":
    main(*sys.argv[1:])
