"""Presentation/export of existing results; no engine calls or capacity calculations."""
import json
import re
import math
from datetime import datetime, timezone
from pathlib import Path

from .models import SteelCase, finite_json_payload
from .sections.models import Section
from .domain.recommendations import slenderness_recommendations
from .execution import CaseExecution


def calculation_trace_document(trace) -> dict:
    """Export only producer observations; never infer equations or rerun checks.

    This opt-in sidecar is HFS-024-v1, not a new payload in JSON contract 1.0.
    Raw values remain raw. Consumers may format separate display values.
    """
    return trace.model_dump(mode="json")


def _sanitize_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", text)



def _build_global_summary(result) -> dict:
    """Observed ranking only: consume published DCR, never recompute resistance.

    Coverage links identify executed resistance checks, not accreditation. When
    no coverage metadata exists (legacy/direct caller), numeric checks are only
    provisional candidates. No units or roles are inferred from clause text.
    """
    checks = result.checks or []
    resistance_indices = None
    if result.coverage is not None:
        resistance_indices = {index for obligation in result.coverage.obligations if obligation.resistance
                              for index in obligation.executed_checks}
    candidates, failures, excluded = [], [], []
    for index, check in enumerate(checks):
        entry = {"check_index": index, "clause": check.clause, "name": check.name,
                 "dcr_published": check.dcr if math.isfinite(check.dcr) else None,
                 "status": check.status.value}
        if check.status.value == "FAIL":
            failures.append(entry)
        reason = None
        if resistance_indices is not None and index not in resistance_indices:
            reason = "no_executed_resistance_obligation"
        elif not (math.isfinite(check.demand) and abs(check.demand) > 0
                  and math.isfinite(check.capacity) and check.capacity > 0):
            reason = "no_positive_resistance_with_active_demand"
        elif not math.isfinite(check.dcr) or check.dcr < 0:
            reason = "no_finite_nonnegative_published_dcr"
        if reason:
            excluded.append({"check_index": index, "reason": reason})
        else:
            candidates.append(entry)
    maximum = max((c["dcr_published"] for c in candidates), default=None)
    return {
        "version": "HFS-015-v2",
        "overall_status": result.status.value,
        "scope": "executed_checks_only",
        "description": "Observed governing checks among executed checks; not a definitive governing limit state for the structure.",
        "ranking_basis": "original_unrounded_dcr; exact raw ties retained; published numbers are raw",
        "eligibility_basis": "executed_resistance_obligations" if resistance_indices is not None
                             else "provisional_numeric_checks_without_coverage",
        "max_dcr_published": maximum,
        "observed_governing_checks": [c for c in candidates if c["dcr_published"] == maximum],
        "failed_checks": failures,
        "excluded_checks": excluded,
    }



def _build_chapter_admissibility(case: SteelCase, section: Section | None) -> dict:
    # Legacy transport key/name retained; content is advisory, never admissibility.
    return slenderness_recommendations(case, section)



def _build_compact_admissibility(admissibility: dict) -> dict:
    # One advisory source for compact and detailed consumers; no lost diagnostics.
    return admissibility



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
    if clause_upper.startswith("H1") or clause_upper.startswith("H3-2") or clause_upper.startswith("I5"):
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
    """Project actual result values, including interactions; no reconstruction."""
    units = {"demand": check.unit, "capacity": check.unit}
    return finite_json_payload({
        "version": "HFS-015-raw-v1", "units": units,
        "source": "CheckResult original values; not reconstructed from memory/display",
        "unit_diagnostic": None if check.unit else "Unit not supplied by producer (legacy/inactive check)",
        "numeric_issue": check.numeric_issue,
        "steps": [
            {"id": 1, "name": "Demand", "value": check.demand, "unit": check.unit},
            {"id": 2, "name": "Available Capacity", "value_used_for_dcr": check.capacity,
             "value_reported_in_check": check.capacity, "unit": check.unit},
            {"id": 3, "name": "Demand-Capacity Ratio", "value_raw": check.dcr,
             "value_reported_in_check": check.dcr, "display": check.display["dcr_label"]},
            {"id": 4, "name": "Status", "result": check.status.value, "threshold": 1.0,
             "expression": "Producer decision using original DCR, no tolerance or display rounding"},
        ],
    })



def _extract_i5_method2_points(result) -> tuple[dict, dict] | None:
    for check in result.checks:
        if str(check.clause).upper() != "I5":
            continue
        details = check.details or {}
        memory = details.get("memory") if isinstance(details, dict) else None
        if not isinstance(memory, dict):
            continue
        inputs = memory.get("inputs")
        if not isinstance(inputs, dict) or inputs.get("method") != "METHOD_2_PLASTIC_INTERACTION":
            continue
        intermediate = memory.get("intermediate")
        if not isinstance(intermediate, dict):
            continue
        method_data = intermediate.get("method_data")
        if not isinstance(method_data, dict):
            continue
        points = method_data.get("interaction_points_by_axis")
        if isinstance(points, dict):
            return points, method_data
    return None



def _ordered_pm_points(point_payload: dict) -> list[dict]:
    if not isinstance(point_payload, dict):
        return []
    points = point_payload.get("points", point_payload)
    if not isinstance(points, dict):
        return []
    order = ["A", "E", "C", "D", "B"]
    return [points[key] for key in order if key in points and isinstance(points[key], dict)]



def _write_i5_interaction_diagram_svg(
    *,
    points_by_axis: dict,
    case: SteelCase,
    output_path: Path,
) -> str:
    width = 900
    height = 620
    pad_left = 90
    pad_right = 30
    pad_top = 50
    pad_bottom = 70
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    all_m = [abs(float(case.loads.Mux)), abs(float(case.loads.Muy))]
    all_p = [max(0.0, float(case.loads.Pu))]
    for axis_key in ("x", "y"):
        axis_payload = points_by_axis.get(axis_key)
        for point in _ordered_pm_points(axis_payload) if isinstance(axis_payload, dict) else []:
            all_m.append(max(0.0, float(point.get("M_kN_m", 0.0))))
            all_p.append(max(0.0, float(point.get("P_kN", 0.0))))

    max_m = max(all_m) if any(value > 0.0 for value in all_m) else 1.0
    max_p = max(all_p) if any(value > 0.0 for value in all_p) else 1.0

    def _x(m_kN_m: float) -> float:
        return pad_left + (max(0.0, m_kN_m) / max_m) * plot_w

    def _y(p_kN: float) -> float:
        return pad_top + (1.0 - (max(0.0, p_kN) / max_p)) * plot_h

    axis_styles = {
        "x": {"label": "x-axis", "color": "#1f77b4", "demand_m": abs(float(case.loads.Mux))},
        "y": {"label": "y-axis", "color": "#d62728", "demand_m": abs(float(case.loads.Muy))},
    }
    demand_p = max(float(case.loads.Pu), 0.0)
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        f'<line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{height - pad_bottom}" stroke="#222" stroke-width="1.5"/>',
        f'<line x1="{pad_left}" y1="{height - pad_bottom}" x2="{width - pad_right}" y2="{height - pad_bottom}" stroke="#222" stroke-width="1.5"/>',
        f'<text x="{width/2:.1f}" y="24" text-anchor="middle" font-family="Arial" font-size="18">I5 Method 2 Interaction Diagram</text>',
        f'<text x="{width/2:.1f}" y="{height-20}" text-anchor="middle" font-family="Arial" font-size="14">Moment M (kN-m)</text>',
        f'<text x="24" y="{height/2:.1f}" text-anchor="middle" font-family="Arial" font-size="14" transform="rotate(-90 24 {height/2:.1f})">Axial Compression P (kN)</text>',
    ]

    for idx in range(6):
        frac = idx / 5.0
        gx = pad_left + frac * plot_w
        gy = pad_top + frac * plot_h
        m_tick = frac * max_m
        p_tick = (1.0 - frac) * max_p
        svg_parts.append(f'<line x1="{gx:.1f}" y1="{pad_top}" x2="{gx:.1f}" y2="{height-pad_bottom}" stroke="#e5e5e5" stroke-width="1"/>')
        svg_parts.append(f'<line x1="{pad_left}" y1="{gy:.1f}" x2="{width-pad_right}" y2="{gy:.1f}" stroke="#e5e5e5" stroke-width="1"/>')
        svg_parts.append(f'<text x="{gx:.1f}" y="{height-pad_bottom+18}" text-anchor="middle" font-family="Arial" font-size="11">{m_tick:.1f}</text>')
        svg_parts.append(f'<text x="{pad_left-10}" y="{gy+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{p_tick:.1f}</text>')

    legend_y = pad_top + 12
    for axis_key, style in axis_styles.items():
        axis_payload = points_by_axis.get(axis_key)
        if not isinstance(axis_payload, dict):
            continue
        ordered = _ordered_pm_points(axis_payload)
        if not ordered:
            continue
        coords = " ".join(f"{_x(float(point.get('M_kN_m', 0.0))):.2f},{_y(float(point.get('P_kN', 0.0))):.2f}" for point in ordered)
        svg_parts.append(
            f'<polyline fill="none" stroke="{style["color"]}" stroke-width="2" points="{coords}"/>'
        )
        for point in ordered:
            px = _x(float(point.get("M_kN_m", 0.0)))
            py = _y(float(point.get("P_kN", 0.0)))
            svg_parts.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3.5" fill="{style["color"]}"/>')

        dx = _x(style["demand_m"])
        dy = _y(demand_p)
        svg_parts.append(f'<line x1="{dx-5:.2f}" y1="{dy-5:.2f}" x2="{dx+5:.2f}" y2="{dy+5:.2f}" stroke="{style["color"]}" stroke-width="2"/>')
        svg_parts.append(f'<line x1="{dx-5:.2f}" y1="{dy+5:.2f}" x2="{dx+5:.2f}" y2="{dy-5:.2f}" stroke="{style["color"]}" stroke-width="2"/>')

        svg_parts.append(f'<line x1="{width-220}" y1="{legend_y}" x2="{width-190}" y2="{legend_y}" stroke="{style["color"]}" stroke-width="2"/>')
        svg_parts.append(f'<text x="{width-185}" y="{legend_y+4}" font-family="Arial" font-size="11">Interaction {style["label"]}</text>')
        legend_y += 20
        svg_parts.append(f'<line x1="{width-220}" y1="{legend_y-4}" x2="{width-210}" y2="{legend_y+6}" stroke="{style["color"]}" stroke-width="2"/>')
        svg_parts.append(f'<line x1="{width-220}" y1="{legend_y+6}" x2="{width-210}" y2="{legend_y-4}" stroke="{style["color"]}" stroke-width="2"/>')
        svg_parts.append(f'<text x="{width-185}" y="{legend_y+4}" font-family="Arial" font-size="11">Demand {style["label"]}</text>')
        legend_y += 22

    svg_parts.append("</svg>")
    output_path.write_text("\n".join(svg_parts), encoding="utf-8")
    return str(output_path)



def _write_i5_interaction_diagram_png(
    *,
    result,
    case: SteelCase,
    results_dir: str,
    safe_profile: str,
    safe_section: str,
    timestamp: str,
    safe_case_tag: str | None,
) -> str | None:
    extracted = _extract_i5_method2_points(result)
    if extracted is None:
        return None
    points_by_axis, _ = extracted
    output_dir = Path(results_dir) / safe_profile
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        if safe_case_tag:
            svg_path = output_dir / f"{safe_section}__{safe_case_tag}__{timestamp}__I5_METHOD2.svg"
        else:
            svg_path = output_dir / f"{safe_section}__{timestamp}__I5_METHOD2.svg"
        return _write_i5_interaction_diagram_svg(points_by_axis=points_by_axis, case=case, output_path=svg_path)
    if safe_case_tag:
        output_path = output_dir / f"{safe_section}__{safe_case_tag}__{timestamp}__I5_METHOD2.png"
    else:
        output_path = output_dir / f"{safe_section}__{timestamp}__I5_METHOD2.png"

    fig, ax = plt.subplots(figsize=(7, 5), dpi=160)
    axis_styles = {
        "x": {"label": "x-axis", "color": "#1f77b4", "demand_m": abs(float(case.loads.Mux))},
        "y": {"label": "y-axis", "color": "#d62728", "demand_m": abs(float(case.loads.Muy))},
    }
    demand_p = max(float(case.loads.Pu), 0.0)
    for axis_key, style in axis_styles.items():
        axis_payload = points_by_axis.get(axis_key)
        if not isinstance(axis_payload, dict):
            continue
        ordered = _ordered_pm_points(axis_payload)
        if not ordered:
            continue
        m_values = [max(0.0, float(point.get("M_kN_m", 0.0))) for point in ordered]
        p_values = [max(0.0, float(point.get("P_kN", 0.0))) for point in ordered]
        ax.plot(m_values, p_values, marker="o", linewidth=1.6, label=f"Interaction {style['label']}", color=style["color"])
        ax.scatter(
            [style["demand_m"]],
            [demand_p],
            color=style["color"],
            marker="x",
            s=60,
            linewidths=2.0,
            label=f"Demand {style['label']}",
        )

    ax.set_xlabel("Moment M (kN-m)")
    ax.set_ylabel("Axial Compression P (kN)")
    ax.set_title("I5 Method 2 Interaction Diagram")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return str(output_path)



def build_detailed_results_payload(
    *,
    result,
    case: SteelCase,
    input_payload: dict,
    input_file: str,
    sections_file: str,
    profile_type: str,
    section: Section | None,
    timestamp: str,
    interaction_diagram_path: str | None = None,
    case_tag: str | None = None,
) -> dict:
    safe_profile = _sanitize_filename((profile_type or "UNKNOWN").upper())
    admissibility = _build_chapter_admissibility(case, section)

    output_summary = result.model_dump(exclude={"checks": {"__all__": {"details"}}})
    output_summary["admissibility"] = admissibility
    global_summary = _build_global_summary(result)
    output_summary["global_summary"] = global_summary

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
                **global_summary,
                "admissibility": admissibility,
            },
            "shared_context": shared_context,
            "clause_results": clause_results,
        },
        "admissibility": admissibility,
        "input": input_payload,
        "output": output_summary,
    }
    if interaction_diagram_path:
        payload["meta"]["interaction_diagram_i5_method2_image"] = interaction_diagram_path
    return finite_json_payload(payload)


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
    timestamp: str,
    interaction_diagram_path: str | None = None,
    case_tag: str | None = None,
) -> Path:
    safe_section = _sanitize_filename(case.section_name.upper())
    safe_profile = _sanitize_filename((profile_type or "UNKNOWN").upper())
    safe_case_tag = _sanitize_filename(case_tag.upper()) if case_tag else None

    output_dir = Path(results_dir) / safe_profile
    output_dir.mkdir(parents=True, exist_ok=True)
    if safe_case_tag:
        output_path = output_dir / f"{safe_section}__{safe_case_tag}__{timestamp}.json"
    else:
        output_path = output_dir / f"{safe_section}__{timestamp}.json"
    payload = build_detailed_results_payload(
        result=result, case=case, input_payload=input_payload, input_file=input_file,
        sections_file=sections_file, profile_type=profile_type, section=section,
        timestamp=timestamp, interaction_diagram_path=interaction_diagram_path, case_tag=case_tag)
    output_path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    return output_path


def _build_execution_results_dir(*, base_results_dir: str, input_file: str) -> str:
    run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    example_name = _sanitize_filename(Path(input_file).stem.upper())
    run_dir = Path(base_results_dir) / example_name / run_timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return str(run_dir)



def build_compact_summary(execution: CaseExecution, *, results_dir: str | None = None,
                          interaction_diagram_path: str | None = None,
                          detailed_path: str | None = None) -> dict:
    result, case, section = execution.result, execution.case, execution.section
    case_tag = execution.case_tag
    write_results_json = execution.output_options["write_results_json"]
    raw_summary = result.model_dump(exclude={"checks": {"__all__": {"details"}}})
    organized_summary = {
        "status": raw_summary.get("status"),
        "coverage": raw_summary.get("coverage"),
        "known_failures": raw_summary.get("known_failures", []),
        "global_summary": _build_global_summary(result),
        "admissibility": _build_compact_admissibility(_build_chapter_admissibility(case, section)),
        "checks": raw_summary.get("checks", []),
        "artifacts": {
            "results_run_dir": results_dir,
            "interaction_diagram_i5_method2_image": interaction_diagram_path,
            "detailed_results_json": detailed_path,
            "write_results_json": write_results_json,
        },
    }
    if case_tag is not None:
        return {"case": case_tag, **organized_summary}
    return organized_summary



def export_execution(execution: CaseExecution, *, input_file: str,
                     sections_file: str, results_dir: str) -> dict:
    result, case, section = execution.result, execution.case, execution.section
    input_payload, case_tag = execution.input_payload, execution.case_tag
    write_results_json = execution.output_options["write_results_json"]
    profile_type = case.custom_section.type.value if case.custom_section is not None else section.type
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    safe_section = _sanitize_filename(case.section_name.upper())
    safe_profile = _sanitize_filename((profile_type or "UNKNOWN").upper())
    safe_case_tag = _sanitize_filename(case_tag.upper()) if case_tag else None
    interaction_diagram_path = _write_i5_interaction_diagram_png(
        result=result,
        case=case,
        results_dir=results_dir,
        safe_profile=safe_profile,
        safe_section=safe_section,
        timestamp=timestamp,
        safe_case_tag=safe_case_tag,
    )
    detailed_path = None
    if write_results_json:
        detailed_path = _write_detailed_results_file(
            result=result,
            case=case,
            input_payload=input_payload,
            input_file=input_file,
            sections_file=sections_file,
            profile_type=profile_type,
            results_dir=results_dir,
            section=section,
            timestamp=timestamp,
            interaction_diagram_path=interaction_diagram_path,
            case_tag=case_tag,
        )

    return build_compact_summary(execution, results_dir=results_dir,
                                 interaction_diagram_path=interaction_diagram_path,
                                 detailed_path=str(detailed_path) if detailed_path else None)
