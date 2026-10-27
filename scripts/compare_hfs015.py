"""HFS-015 behavioral comparison, not an independent AISC oracle.

Accept only raw precision, explicit result metadata/serialization and advisory
presentation. All coverage, statuses, selection, factors and other traces must
remain equal. I4/I5 raw-capacity propagation is verified against its producer.
"""
import argparse
import copy
import json
import math
from pathlib import Path

from audit_baseline import write_json


def clean(value):
    """Normalize only explicitly recorded legacy nonfinite serialization."""
    if isinstance(value, dict):
        if set(value)=={"nonfinite_json_token"}: return None
        return {k:clean(v) for k,v in value.items() if k!="nonfinite_values"}
    if isinstance(value,list): return [clean(v) for v in value]
    return value


def diffs(a,b,path=""):
    if a==b: return []
    if isinstance(a,dict) and isinstance(b,dict):
        return sum((diffs(a.get(k),b.get(k),path+"/"+k) for k in sorted(a.keys()|b.keys())),[])
    if isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        return sum((diffs(x,y,path+"/"+str(i)) for i,(x,y) in enumerate(zip(a,b))),[])
    return [{"path":path,"before":a,"after":b}]


def compare_result(old,new):
    if "error" in old:
        assert old==new,"Existing execution error changed"
        return []
    assert {k:v for k,v in old.items() if k!="checks"}=={k:v for k,v in new.items() if k!="checks"}
    assert len(old["checks"])==len(new["checks"])
    new_checks=new["checks"]
    for index,(a,b) in enumerate(zip(old["checks"],new_checks)):
        assert {k:a[k] for k in ("name","code","clause","status")}=={k:b[k] for k in ("name","code","clause","status")}
        for field in ("demand","capacity","dcr"):
            assert a[field]==b[field] or a[field]==round(b[field],3),(index,field,a[field],b[field])
        if b["capacity"]>0:
            assert b["dcr"]==b["demand"]/b["capacity"]
            assert b["status"]==("PASS" if b["dcr"]<=1 else "FAIL")
        else: assert b["demand"]==b["dcr"]==0  # legacy inactive filler only
        da,db=clean(a.get("details")),clean(b.get("details"))
        if da!=db:
            assert isinstance(da,dict) and isinstance(db,dict)
            ma,mb=da["memory"],db["memory"]
            if a["clause"]=="I5":
                source=mb["inputs"]["axial_capacity_source"]
                producer=next(c for c in new_checks if c["clause"]==source)
                raw=producer["capacity"]
                assert ma["capacities"]["P_available_kN"]==round(raw,3)
                assert mb["capacities"]["P_available_kN"]==raw
                assert mb["components"]["axial"]["capacity_kN"]==raw
                assert mb["intermediate"]["Pu_over_Pavailable"]==abs(mb["inputs"]["Pu_kN"])/raw
                ma["capacities"]["P_available_kN"]=raw
                ma["components"]["axial"]["capacity_kN"]=raw
                ma["intermediate"]["Pu_over_Pavailable"]=mb["intermediate"]["Pu_over_Pavailable"]
            elif a["name"]=="Encased Shear Governing I4-1":
                raw={c["clause"]:c["capacity"] for c in new_checks if c["clause"] in {"I4-1a","I4-1b","I4-1c"}}
                assert mb["intermediate"]["subcheck_capacities_kN"]==raw
                assert ma["intermediate"]["subcheck_capacities_kN"]=={k:round(v,3) for k,v in raw.items()}
                assert mb["capacity_kn"]==max(raw.values())==b["capacity"]
                ma["intermediate"]["subcheck_capacities_kN"]=raw
                ma["capacity_kn"]=mb["capacity_kn"]
            assert da==db,(index,"Unexpected calculation/trace change",diffs(da,db))
    return diffs(old,new)


def verify_summary(item):
    summary=item["global_summary"]
    assert summary["version"]=="HFS-015-v2" and summary["scope"]=="executed_checks_only"
    assert summary["overall_status"]==item["status"]
    checks=item["checks"]
    resistance={i for o in item["coverage"]["obligations"] if o["resistance"] for i in o["executed_checks"]}
    eligible=[i for i,c in enumerate(checks) if i in resistance and c["demand"]!=0 and c["capacity"]>0 and c["dcr"] is not None]
    maximum=max((checks[i]["dcr"] for i in eligible),default=None)
    assert summary["max_dcr_published"]==maximum
    assert [g["check_index"] for g in summary["observed_governing_checks"]]==[i for i in eligible if checks[i]["dcr"]==maximum]
    assert [g["check_index"] for g in summary["failed_checks"]]==item["known_failures"]


def verify_advice(advice):
    assert advice["version"]=="HFS-015-advice-v1" and advice["resistance"] is False
    for key,limit in (("D1",300),("E2",200)):
        a=advice[key]
        assert a["resistance"] is False and a["source_type"]=="User Note"
        assert "admissible" not in a and a["recommended_max"]==limit
        expected=("NOT_APPLICABLE" if a["applicable"] is False else "UNKNOWN"
                  if a["applicable"] is None or a["ratio"] is None else
                  "WITHIN_RECOMMENDATION" if a["ratio"]<=limit else "EXCEEDS_RECOMMENDATION")
        assert a["assessment"]==expected
    # Existing examples have no fabricated member/rod evidence. Do not invent it.
    assert advice["D1"]["ratio"] is None
    assert advice["E2"]["fabricated_member"]["ratio"] is None


def compare_cli(before,after,engine_before,engine_after):
    assert before.keys()==after.keys()
    records={}
    for label,a in before.items():
        b=after[label]; name=label.split('/')[0]
        assert a["source_sha256"]==b["source_sha256"]
        assert a["execution"]["returncode"]==b["execution"]["returncode"]
        ca,cb=copy.deepcopy(a["normalized_cli"]),copy.deepcopy(b["normalized_cli"])
        if a["execution"]["returncode"]:
            assert ca==cb and a["normalized_details"]==b["normalized_details"]
            records[label]={"accepted":True,"existing_error_unchanged":True};continue
        # Every successful CLI check must be exactly the corresponding engine output.
        items_a,items_b=ca.get("cases",[ca]),cb.get("cases",[cb])
        assert len(items_a)==len(items_b)==len(engine_after[name])
        for i,(old,new) in enumerate(zip(items_a,items_b)):
            ea,eb=engine_before[name][i]["result"],engine_after[name][i]["result"]
            assert old["checks"]==[{k:v for k,v in c.items() if k!="details"} for c in ea["checks"]]
            assert new["checks"]==[{k:v for k,v in c.items() if k!="details"} for c in eb["checks"]]
            verify_summary(new);verify_advice(new["admissibility"])
            for field in ("checks","global_summary","admissibility"): old[field]=new[field]
        assert ca==cb,"Unexpected CLI change"
        da,db=copy.deepcopy(a["normalized_details"]),copy.deepcopy(b["normalized_details"])
        assert len(da)==len(db)
        for i,(old,new) in enumerate(zip(da,db)):
            checks=engine_after[name][i]["result"]["checks"]
            out=new["output"];verify_summary(out);verify_advice(new["admissibility"])
            assert new["admissibility"]==out["admissibility"]==new["memory"]["global_summary"]["admissibility"]
            assert out["checks"]==items_b[i]["checks"] and out["global_summary"]==items_b[i]["global_summary"]
            for field in ("checks","global_summary","admissibility"): old["output"][field]=out[field]
            old["admissibility"]=new["admissibility"]
            old["memory"]["global_summary"]=new["memory"]["global_summary"]
            assert len(new["memory"]["clause_results"])==len(checks)
            for index,(x,y) in enumerate(zip(old["memory"]["clause_results"],new["memory"]["clause_results"])):
                c=checks[index]; t=y["check_trace"]
                assert y["clause"]==c["clause"] and y["name"]==c["name"]
                assert y["check_summary"]=={k:c[k] for k in ("demand","capacity","dcr","status")}
                assert t["units"]=={"demand":c["unit"],"capacity":c["unit"]}
                assert t["steps"][0]["value"]==c["demand"]
                assert t["steps"][1]["value_used_for_dcr"]==c["capacity"]
                assert t["steps"][2]["value_raw"]==c["dcr"]
                assert t["steps"][3]["result"]==c["status"]
                if "calculations" in y:
                    assert clean(y["calculations"])==clean(c["details"]["memory"])
                    x["calculations"]=y["calculations"]
                for field in ("check_summary","check_trace"):x[field]=y[field]
            assert clean(old)==clean(new),diffs(clean(old),clean(new))
        # Enforce strict JSON in raw CLI and saved memories; markers only occur before.
        json.loads(b["execution"]["stdout"],parse_constant=lambda token: (_ for _ in ()).throw(AssertionError(token)))
        assert "nonfinite_json_token" not in json.dumps(b["normalized_details"])
        records[label]={"accepted":True,"changes":diffs(a["normalized_cli"],b["normalized_cli"]),
                        "memory_changes":diffs(a["normalized_details"],b["normalized_details"])}
    return records


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("engine-before","engine-after","cli-before","cli-after","out"): parser.add_argument('--'+key,required=True,type=Path)
    args=parser.parse_args()
    if args.out.exists(): raise SystemExit("Use a new output path")
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    a,b=load(args.engine_before),load(args.engine_after)
    report={"accepted":False,"engine":{},"cli":{}}
    try:
        assert a.keys()==b.keys()
        for name in a:
            assert len(a[name])==len(b[name])
            changes=[]
            for x,y in zip(a[name],b[name]):
                assert x["case"]==y["case"]
                changes.extend(compare_result(x["result"],y["result"]))
            report["engine"][name]={"accepted":True,"changes":changes}
        report["cli"]=compare_cli(load(args.cli_before),load(args.cli_after),a,b)
        report["accepted"]=True
    except AssertionError as error:
        report["error"]=str(error)
    write_json(args.out,report)
    print({"accepted":report["accepted"],"engine_examples":len(report["engine"]),"cli_executions":len(report["cli"]),"error":report.get("error")})
    raise SystemExit(0 if report["accepted"] else 1)
