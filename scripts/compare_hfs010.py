"""Compare all legacy check values/traces, separately from HFS-010 state changes."""


def compare_coverage_transition(before, after):
    comparison = {}
    for filename in sorted(before.keys() | after.keys()):
        old_cases, new_cases = before.get(filename, []), after.get(filename, [])
        rows = []
        compatible = filename in before and filename in after and len(old_cases) == len(new_cases)
        for old, new in zip(old_cases, new_cases):
            a, b = old["result"], new["result"]
            error_case = "error" in a or "error" in b
            preserved = (a == b if error_case else
                         {k: v for k, v in a.items() if k != "status"} ==
                         {k: v for k, v in b.items() if k not in {"status", "coverage", "known_failures"}})
            known = [i for i, c in enumerate(a.get("checks", [])) if c["status"] == "FAIL"]
            expected_state = (a == b if error_case else
                              b.get("status") == "INCOMPLETE" and b.get("known_failures") == known
                              and b.get("coverage", {}).get("complete") is False)
            compatible = compatible and preserved and expected_state and old["case"] == new["case"]
            rows.append({"case": old["case"], "before_status": a.get("status", "ERROR"),
                         "after_status": b.get("status", "ERROR"), "checks_and_traces_identical": preserved,
                         "known_failures": b.get("known_failures", []),
                         "pending": [{"id": o["id"], "reason": o["reason"]}
                                     for o in b.get("coverage", {}).get("obligations", []) if o["status"] == "PENDING"],
                         "expected_legacy_transition": expected_state})
        comparison[filename] = {"compatible": compatible, "cases": rows}
    return comparison
