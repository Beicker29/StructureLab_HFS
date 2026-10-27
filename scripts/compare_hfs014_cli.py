"""Compare CLI/detailed consumers allowing only HFS-014 summary changes.

No engineering values, coverage, states, checks, admissibility or traces may
change. Volatile timestamps/paths were already normalized by the capturador.
"""
import copy
import json
from pathlib import Path
import sys


def compare(before, after):
    if before.keys() != after.keys():
        return {"accepted": False, "reason": "CLI scenario set changed"}
    records = {}
    for label in before:
        a, b = before[label], after[label]
        cli_a, cli_b = copy.deepcopy(a["normalized_cli"]), copy.deepcopy(b["normalized_cli"])
        da, db = copy.deepcopy(a["normalized_details"]), copy.deepcopy(b["normalized_details"])
        changes=[]
        for old, new in zip(cli_a.get("cases",[cli_a]),cli_b.get("cases",[cli_b])):
            if "global_summary" in new:
                changes.append({"location":"CLI.global_summary","before":old.get("global_summary"),
                                "after":new.pop("global_summary")})
        for old,new in zip(da,db):
            changes.append({"location":"memory.global_summary","before":old["memory"]["global_summary"],
                            "after":new["memory"]["global_summary"]})
            # Only the global-summary contract may differ; preserve existing
            # overall status/admissibility alongside all per-check traces.
            for value in (old,new):
                value["memory"]["global_summary"]={k:v for k,v in value["memory"]["global_summary"].items()
                                                   if k in {"overall_status","admissibility"}}
            new["output"].pop("global_summary",None)
        accepted=(a["source_sha256"]==b["source_sha256"] and
                  a["execution"]["returncode"]==b["execution"]["returncode"] and cli_a==cli_b and da==db)
        records[label]={"accepted":accepted,"exit_before":a["execution"]["returncode"],
            "exit_after":b["execution"]["returncode"],"cli_except_summary_identical":cli_a==cli_b,
            "detailed_except_summary_identical":da==db,"summary_changes":changes}
    return {"accepted":all(r["accepted"] for r in records.values()),"executions":len(records),"cases":records}


if __name__=="__main__":
    before,after,out=map(Path,sys.argv[1:])
    if out.exists():
        raise SystemExit("Choose a new output path")
    result=compare(json.loads(before.read_text(encoding="utf-8")),json.loads(after.read_text(encoding="utf-8")))
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print({k:v for k,v in result.items() if k!="cases"})
    raise SystemExit(0 if result["accepted"] else 1)
