import json
import argparse
import sys
import re
import math
import copy
from datetime import datetime, timezone
from pathlib import Path

from .models import CustomSectionType, SteelCase
from .engine import SteelDesignEngine
from .sections.models import Section
from .sections.loader import load_sections_from_excel
from .sections.repository import SectionRepository
from .domain.errors import SteelDesignError


def _print_structured_error(error: Exception, *, stage: str):
    payload = {
        "error": {
            "type": error.__class__.__name__,
            "message": str(error),
            "stage": stage,
        }
    }
    if isinstance(error, SteelDesignError):
        payload["error"].update(
            {
                "code": error.code,
                "details": error.details,
            }
        )
    print(json.dumps(payload, indent=2), file=sys.stderr)


def _sanitize_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", text)


def _build_global_summary(result) -> dict:
    checks = result.checks or []
    positive_capacity_checks = [
        check
        for check in checks
        if (check.capacity or 0.0) > 0.0 and not str(check.clause).upper().startswith(("H1", "H3-2"))
    ]
    if not positive_capacity_checks:
        return {
            "governing_capacity_kn_or_knm": None,
            "governing_clauses": [],
            "governing_check_names": [],
        }

    min_capacity = min(check.capacity for check in positive_capacity_checks)
    governing_checks = [check for check in positive_capacity_checks if abs(check.capacity - min_capacity) <= 1e-9]
    return {
        "governing_capacity_kn_or_knm": min_capacity,
        "governing_clauses": [check.clause for check in governing_checks],
        "governing_check_names": [check.name for check in governing_checks],
    }


def _build_case_section(case: SteelCase, repo: SectionRepository) -> Section | None:
    if case.custom_section is None:
        return repo.get(case.section_name)

    custom = case.custom_section
    if custom.type == CustomSectionType.SOLID_CIRCULAR:
        diameter = custom.diameter or 0.0
        area = math.pi * (diameter**2) / 4.0
        inertia = math.pi * (diameter**4) / 64.0
        radius_of_gyration = diameter / 4.0
        elastic_modulus = math.pi * (diameter**3) / 32.0
        plastic_modulus = (diameter**3) / 6.0
        return Section(
            name=case.section_name,
            type=custom.type.value,
            A=area,
            OD=diameter,
            Ix=inertia,
            Iy=inertia,
            Sx=elastic_modulus,
            Sy=elastic_modulus,
            Zx=plastic_modulus,
            Zy=plastic_modulus,
            rx=radius_of_gyration,
            ry=radius_of_gyration,
        )

    height = custom.H or 0.0
    width = custom.B or 0.0
    area = width * height
    inertia_x = width * (height**3) / 12.0
    inertia_y = height * (width**3) / 12.0
    radius_of_gyration_x = math.sqrt(inertia_x / area) if area > 0.0 else 0.0
    radius_of_gyration_y = math.sqrt(inertia_y / area) if area > 0.0 else 0.0
    section_modulus_x = width * (height**2) / 6.0
    section_modulus_y = height * (width**2) / 6.0
    plastic_modulus_x = width * (height**2) / 4.0
    plastic_modulus_y = height * (width**2) / 4.0
    return Section(
        name=case.section_name,
        type=custom.type.value,
        A=area,
        h=height,
        b=width,
        Ix=inertia_x,
        Iy=inertia_y,
        Sx=section_modulus_x,
        Sy=section_modulus_y,
        Zx=plastic_modulus_x,
        Zy=plastic_modulus_y,
        rx=radius_of_gyration_x,
        ry=radius_of_gyration_y,
    )


def _safe_klr(k: float, length: float, radius: float | None) -> float | None:
    if radius is None or radius <= 0.0 or k <= 0.0 or length <= 0.0:
        return None
    return (k * length) / radius


def _build_chapter_admissibility(case: SteelCase, section: Section | None) -> dict:
    pure_axial = (
        abs(case.loads.Mux) <= 1e-9
        and abs(case.loads.Muy) <= 1e-9
        and abs(case.loads.Tu) <= 1e-9
        and abs(case.loads.Vu) <= 1e-9
        and abs(case.loads.Vux) <= 1e-9
        and abs(case.loads.Vuy) <= 1e-9
    )
    klr_x = _safe_klr(case.factors.Kx, case.lengths.Lx, section.rx if section else None)
    klr_y = _safe_klr(case.factors.Ky, case.lengths.Ly, section.ry if section else None)
    valid_klr = [value for value in (klr_x, klr_y) if value is not None]
    max_klr = max(valid_klr) if valid_klr else None
    governing_axis = None
    if max_klr is not None:
        governing_axis = "x" if klr_x is not None and abs(klr_x - max_klr) <= 1e-9 else "y"

    d1_applicable = pure_axial and case.loads.Pu < 0.0
    e2_applicable = pure_axial and case.loads.Pu > 0.0
    d1 = bool(d1_applicable and max_klr is not None and max_klr <= 300.0)
    e2 = bool(e2_applicable and max_klr is not None and max_klr <= 200.0)
    return {
        "D1": d1,
        "E2": e2,
        "short": f"D.1:{'SI' if d1 else 'NO'} | E.2:{'SI' if e2 else 'NO'}",
        "inputs": {
            "KL_over_r_x": klr_x,
            "KL_over_r_y": klr_y,
            "KL_over_r_governing": max_klr,
            "governing_axis": governing_axis,
        },
        "limits": {
            "D1_max": 300.0,
            "E2_max": 200.0,
        },
        "applicability": {
            "D1": d1_applicable,
            "E2": e2_applicable,
        },
    }


def _build_compact_admissibility(admissibility: dict) -> dict:
    return {
        "short": admissibility["short"],
        "D1": {
            "applicable": admissibility["applicability"]["D1"],
            "admissible": admissibility["D1"],
        },
        "E2": {
            "applicable": admissibility["applicability"]["E2"],
            "admissible": admissibility["E2"],
        },
    }


def _extract_shared_context(clause_results: list[dict]) -> dict:
    entries_with_context = [entry for entry in clause_results if "context" in entry]
    if not entries_with_context:
        return {}
    contexts = [entry.get("context", {}) for entry in entries_with_context]

    shared_keys = set(contexts[0].keys())
    for context in contexts[1:]:
        shared_keys &= set(context.keys())

    shared_context = {}
    for key in sorted(shared_keys):
        value = contexts[0][key]
        if all(context[key] == value for context in contexts[1:]):
            shared_context[key] = value

    if not shared_context:
        return {}

    for entry in entries_with_context:
        context = entry.get("context", {})
        for key in shared_context:
            context.pop(key, None)
        if not context and "context" in entry:
            entry.pop("context")

    return shared_context


def _infer_check_units(clause: str) -> dict:
    clause_upper = (clause or "").upper()
    if clause_upper.startswith("H1") or clause_upper.startswith("H3-2"):
        return {"demand": "ratio", "capacity": "ratio"}
    if clause_upper.startswith("H3-1"):
        return {"demand": "kN-m", "capacity": "kN-m"}
    if clause_upper.startswith("F"):
        return {"demand": "kN-m", "capacity": "kN-m"}
    return {"demand": "kN", "capacity": "kN"}


def _extract_capacity_from_memory(memory: dict | None) -> float | None:
    if not isinstance(memory, dict):
        return None
    for key in ("capacity_kn", "capacity_kn_m", "capacity_kn_or_knm", "capacity"):
        value = memory.get(key)
        if isinstance(value, (int, float)) and value > 0.0:
            return float(value)
    return None


def _build_dcr_trace(check) -> dict:
    details = check.details or {}
    memory = details.get("memory") if isinstance(details, dict) else None
    units = _infer_check_units(check.clause)
    demand = float(check.demand or 0.0)
    capacity_reported = float(check.capacity or 0.0)
    capacity_from_memory = _extract_capacity_from_memory(memory)
    capacity_for_dcr = capacity_from_memory if isinstance(capacity_from_memory, float) and capacity_from_memory > 0.0 else capacity_reported
    dcr_raw = demand / capacity_for_dcr if capacity_for_dcr > 0.0 else math.inf
    dcr_rounded = round(dcr_raw, 3) if math.isfinite(dcr_raw) else None
    design_factor = memory.get("design_factor") if isinstance(memory, dict) and isinstance(memory.get("design_factor"), dict) else {}
    capacity_expression = design_factor.get("capacity_expression", "rule_capacity")

    if capacity_for_dcr > 0.0:
        substitution = f"DCR = {demand:.6f} / {capacity_for_dcr:.6f}"
    else:
        substitution = "DCR = demand / 0.0 (undefined -> inf)"

    return {
        "units": units,
        "steps": [
            {
                "id": 1,
                "name": "Demand",
                "expression": "demand = required action from input loads",
                "value": demand,
                "unit": units["demand"],
            },
            {
                "id": 2,
                "name": "Available Capacity",
                "expression": f"capacity = {capacity_expression}",
                "value_used_for_dcr": capacity_for_dcr,
                "value_reported_in_check": capacity_reported,
                "value_from_rule_memory": capacity_from_memory,
                "unit": units["capacity"],
            },
            {
                "id": 3,
                "name": "Demand-Capacity Ratio",
                "expression": "DCR = demand / capacity",
                "substitution": substitution,
                "value_raw": dcr_raw if math.isfinite(dcr_raw) else None,
                "value_rounded_3dec": dcr_rounded,
                "value_reported_in_check": check.dcr,
                "is_infinite": not math.isfinite(dcr_raw),
            },
            {
                "id": 4,
                "name": "Status",
                "expression": "PASS if DCR <= 1.0 else FAIL",
                "result": check.status.value,
                "threshold": 1.0,
            },
        ],
    }


def _write_detailed_results_file(
    *,
    result,
    case: SteelCase,
    input_payload: dict,
    input_file: str,
    sections_file: str,
    profile_type: str,
    results_dir: str,
    section: Section | None,
    case_tag: str | None = None,
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    safe_section = _sanitize_filename(case.section_name.upper())
    safe_profile = _sanitize_filename((profile_type or "UNKNOWN").upper())
    safe_case_tag = _sanitize_filename(case_tag.upper()) if case_tag else None
    admissibility = _build_chapter_admissibility(case, section)

    output_dir = Path(results_dir) / safe_profile
    output_dir.mkdir(parents=True, exist_ok=True)
    if safe_case_tag:
        output_path = output_dir / f"{safe_section}__{safe_case_tag}__{timestamp}.json"
    else:
        output_path = output_dir / f"{safe_section}__{timestamp}.json"
    output_summary = result.model_dump(exclude={"checks": {"__all__": {"details"}}})
    output_summary["admissibility"] = admissibility

    clause_results = []
    for check in result.checks:
        details = check.details or {}
        entry = {
            "clause": check.clause,
            "name": check.name,
            "calculations": details.get("memory"),
            "check_summary": {
                "demand": check.demand,
                "capacity": check.capacity,
                "dcr": check.dcr,
                "status": check.status.value,
            },
            "check_trace": _build_dcr_trace(check),
        }
        context = {key: value for key, value in details.items() if key != "memory"}
        if context:
            entry["context"] = context
        clause_results.append(entry)
    shared_context = _extract_shared_context(clause_results)

    payload = {
        "meta": {
            "generated_at_utc": timestamp,
            "profile_type": safe_profile,
            "section_name": case.section_name,
            "case_tag": case_tag,
            "input_file": str(input_file),
            "sections_file": str(sections_file),
        },
        "memory": {
            "global_summary": {
                **_build_global_summary(result),
                "overall_status": result.status.value,
                "admissibility": admissibility,
            },
            "shared_context": shared_context,
            "clause_results": clause_results,
        },
        "admissibility": admissibility,
        "input": input_payload,
        "output": output_summary,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def _merge_case_payload(base_payload: dict, override_payload: dict) -> dict:
    merged = copy.deepcopy(base_payload)
    for key, value in override_payload.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_case_payload(merged[key], value)
        else:
            merged[key] = value
    return merged


def _run_single_case(
    *,
    engine: SteelDesignEngine,
    repo: SectionRepository,
    case: SteelCase,
    input_payload: dict,
    input_file: str,
    sections_file: str,
    results_dir: str,
    case_tag: str | None = None,
) -> dict:
    result = engine.run(case)
    section = _build_case_section(case, repo)
    if case.custom_section is not None:
        profile_type = case.custom_section.type.value
    else:
        profile_type = section.type if section is not None else "UNKNOWN"
    _write_detailed_results_file(
        result=result,
        case=case,
        input_payload=input_payload,
        input_file=input_file,
        sections_file=sections_file,
        profile_type=profile_type,
        results_dir=results_dir,
        section=section,
        case_tag=case_tag,
    )

    raw_summary = result.model_dump(exclude={"checks": {"__all__": {"details"}}})
    organized_summary = {
        "status": raw_summary.get("status"),
        "admissibility": _build_compact_admissibility(_build_chapter_admissibility(case, section)),
        "checks": raw_summary.get("checks", []),
    }
    if case_tag is not None:
        return {"case": case_tag, **organized_summary}
    return organized_summary


def main():
    parser = argparse.ArgumentParser(description="AISC 360-22 Steel Design Engine CLI")
    parser.add_argument("input_file", type=str, help="Path to the JSON input case file.")
    parser.add_argument("--sections", type=str, default="data/sections.xlsx", help="Path to the sections Excel file.")
    parser.add_argument("--results-dir", type=str, default="results", help="Directory to store detailed JSON results.")
    args = parser.parse_args()

    # Load sections
    try:
        sections = load_sections_from_excel(args.sections)
    except Exception as e:
        _print_structured_error(e, stage="load_sections")
        sys.exit(1)
        
    # Init repository
    repo = SectionRepository()
    repo.load(sections)
    
    # Init Engine
    engine = SteelDesignEngine(repository=repo)
    
    # Read input payload
    try:
        with open(args.input_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        _print_structured_error(e, stage="parse_input")
        sys.exit(1)

    # Run
    try:
        if isinstance(payload, dict) and isinstance(payload.get("cases"), list):
            case_definitions = payload.get("cases", [])
            base_payload = {key: value for key, value in payload.items() if key != "cases"}
            summaries = []
            aggregate_pass = True
            for index, case_definition in enumerate(case_definitions):
                if not isinstance(case_definition, dict):
                    raise ValueError(f"cases[{index}] must be an object.")
                case_tag = str(case_definition.get("name") or f"case_{index+1}")
                case_override = {k: v for k, v in case_definition.items() if k != "name"}
                merged_payload = _merge_case_payload(base_payload, case_override)
                case = SteelCase(**merged_payload)
                summary = _run_single_case(
                    engine=engine,
                    repo=repo,
                    case=case,
                    input_payload=merged_payload,
                    input_file=args.input_file,
                    sections_file=args.sections,
                    results_dir=args.results_dir,
                    case_tag=case_tag,
                )
                summaries.append(summary)
                if summary.get("status") != "PASS":
                    aggregate_pass = False

            print(
                json.dumps(
                    {
                        "bundle": True,
                        "total_cases": len(summaries),
                        "status": "PASS" if aggregate_pass else "FAIL",
                        "cases": summaries,
                    },
                    indent=2,
                )
            )
        else:
            case = SteelCase(**payload)
            summary = _run_single_case(
                engine=engine,
                repo=repo,
                case=case,
                input_payload=payload,
                input_file=args.input_file,
                sections_file=args.sections,
                results_dir=args.results_dir,
            )
            print(json.dumps(summary, indent=2))

    except Exception as e:
        _print_structured_error(e, stage="run_engine")
        sys.exit(1)

if __name__ == "__main__":
    main()
