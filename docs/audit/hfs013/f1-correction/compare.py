"""F-43 behavioral comparison. Independent arithmetic belongs to the tests.

python compare.py BEFORE.json AFTER.json NEW_COMPARISON.json
Requires identical inputs, nominal evaluations, other capacities and ALL LRFD
outputs. ASD changes are limited to F1 available moments and resulting ratios.
The public ASD flexure rejection remains byte-for-byte equivalent as JSON data.
"""
import json
from pathlib import Path
import sys


def differences(a, b, path=""):
    if isinstance(a,dict) and isinstance(b,dict):
        for key in sorted(set(a)|set(b)):
            if key not in a or key not in b:
                yield {"path":f"{path}/{key}","before":a.get(key),"after":b.get(key)}
            else:
                yield from differences(a[key],b[key],f"{path}/{key}")
    elif a!=b:
        yield {"path":path,"before":a,"after":b}


def compare(before,after):
    assert before.keys()==after.keys()
    allowed={"/rule/demand","/rule/dcr","/rule/status",
        "/rule/details/memory/intermediate/interaction_ratio",
        "/rule/details/memory/intermediate/normal_ratio_sum"}
    for axis in ("x","y"):
        allowed.update({f"/rule/details/memory/capacities/Mc{axis}_kN_m",
            f"/rule/details/memory/components/flexure_{axis}/available_kN_m",
            f"/rule/details/memory/intermediate/Mr{axis}_over_Mc{axis}",
            f"/rule/details/memory/intermediate/Mu{axis}_over_Mc{axis}"})
    records={}
    for key in before:
        changes=list(differences(before[key],after[key]))
        method=before[key]["case"]["design_method"]
        allowed_changes=all(d["path"] in allowed for d in changes)
        a,b=before[key]["rule"],after[key]["rule"]
        records[key]={"compatible":not changes if method=="LRFD" else allowed_changes,
            "method":method,"public_engine_identical":before[key]["engine"]==after[key]["engine"],
            "before_dcr":a["dcr"],"after_dcr":b["dcr"],
            "before_status":a["status"],"after_status":b["status"],"differences":changes}
    return {"accepted":all(r["compatible"] and r["public_engine_identical"] for r in records.values()),
        "case_count":len(records),"lrfd_identical":sum(r["method"]=="LRFD" and not r["differences"] for r in records.values()),
        "asd_changed":sum(r["method"]=="ASD" and bool(r["differences"]) for r in records.values()),
        "partial_pass_to_fail":sum(r["before_status"]=="PASS" and r["after_status"]=="FAIL" for r in records.values()),
        "cases":records}


if __name__=="__main__":
    before,after,output=map(Path,sys.argv[1:])
    if output.exists():
        raise SystemExit("Use a new output path")
    result=compare(json.loads(before.read_text(encoding="utf-8")),json.loads(after.read_text(encoding="utf-8")))
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print({k:v for k,v in result.items() if k!="cases"})
    raise SystemExit(0 if result["accepted"] else 1)
