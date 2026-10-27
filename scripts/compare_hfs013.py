"""Constrained HFS-013 behavioral comparison, not an independent numeric oracle.

Preserve D/E/F/H1/I checks exactly. Only G/H3 checks may change or be blocked.
Report every numeric/trace difference; no baseline is rewritten. No case may
gain PASS. Numerical validation belongs to test_hfs013_directional_h3.py.
"""
from collections import defaultdict
import json
from pathlib import Path
import sys


def compare(before, after):
    summary = {}
    for filename in sorted(set(before) | set(after)):
        old, new = before.get(filename, []), after.get(filename, [])
        cases = []
        for index in range(max(len(old), len(new))):
            if index >= len(old) or index >= len(new) or old[index]["case"] != new[index]["case"]:
                cases.append({"case_index": index, "compatible": False, "reason": "case identity changed"})
                continue
            a, b = old[index]["result"], new[index]["result"]
            if "error" in a or "error" in b:
                cases.append({"case": old[index]["case"], "compatible": a == b, "before": a, "after": b})
                continue
            fixed_a = [c for c in a["checks"] if not c["clause"].startswith(("G", "H3"))]
            fixed_b = [c for c in b["checks"] if not c["clause"].startswith(("G", "H3"))]
            def grouped(result):
                groups = defaultdict(list)
                for check in result["checks"]:
                    groups[check["clause"]].append(check)
                return groups
            ga, gb = grouped(a), grouped(b)
            differences = []
            for clause in sorted(set(ga) | set(gb)):
                for occurrence in range(max(len(ga[clause]), len(gb[clause]))):
                    ca = ga[clause][occurrence] if occurrence < len(ga[clause]) else None
                    cb = gb[clause][occurrence] if occurrence < len(gb[clause]) else None
                    if ca != cb:
                        differences.append({"clause": clause, "occurrence": occurrence,
                            "before": ca, "after": cb,
                            "numeric_difference": {k: [ca.get(k) if ca else None, cb.get(k) if cb else None]
                                                   for k in ("demand", "capacity", "dcr", "status")
                                                   if ca is None or cb is None or ca.get(k) != cb.get(k)}})
            # Identical obligations/fields except the two revised explanatory reasons.
            def without_reasons(coverage):
                return [{k:v for k,v in obligation.items() if k not in {"reason","executed_checks","accepted_checks"}}
                        for obligation in coverage["obligations"]]
            compatible = (fixed_a == fixed_b and b["status"] == a["status"]
                          and without_reasons(a["coverage"]) == without_reasons(b["coverage"]))
            cases.append({"case": old[index]["case"], "compatible": compatible,
                          "unrelated_checks_identical": fixed_a == fixed_b,
                          "before_status": a["status"], "after_status": b["status"],
                          "checks": differences, "after_evaluation_errors": b["coverage"]["evaluation_errors"]})
        summary[filename] = {"compatible": bool(cases) and all(c["compatible"] for c in cases), "cases": cases}
    return summary


if __name__ == "__main__":
    before, after, output = map(Path, sys.argv[1:])
    if output.exists():
        raise SystemExit("Use a new output path")
    result = compare(json.loads(before.read_text()), json.loads(after.read_text()))
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    raise SystemExit(0 if all(r["compatible"] for r in result.values()) else 1)
