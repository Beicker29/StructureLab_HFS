import json
import argparse
import sys
import re
import math
import copy
from datetime import datetime, timezone
from pathlib import Path

from pydantic import AliasChoices, Field, StrictBool, ValidationError as PydanticValidationError

from .models import CustomSectionType, SteelCase
from .results_model import AnalysisStatus, aggregate_case_statuses
from .input_contracts import InputModel
from .engine import SteelDesignEngine
from .sections.models import Section
from .sections.loader import load_sections_from_excel
from .sections.repository import SectionRepository
from .domain.errors import SteelDesignError, ValidationError


class OutputOptions(InputModel):
    """CLI transport options; the engineering contract remains SteelCase."""

    write_results_json: StrictBool = Field(True, validation_alias=AliasChoices(
        "write_results_json", "write_detailed_json", "save_results_json"))


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field {key!r}; supply exactly one value per field.")
        result[key] = value
    return result


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
    if isinstance(error, PydanticValidationError):
        payload["error"]["code"] = "VALIDATION_ERROR"
        payload["error"]["details"] = {"fields": error.errors(
            include_url=False, include_context=False, include_input=False)}
    print(json.dumps(payload, indent=2, allow_nan=False), file=sys.stderr)


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
        "version": "HFS-014-v1",
        "overall_status": result.status.value,
        "scope": "executed_checks_only",
        "description": "Observed governing checks among executed checks; not a definitive governing limit state for the structure.",
        "ranking_basis": "published_dcr; exact ties retained; raw DCR not reconstructed",
        "eligibility_basis": "executed_resistance_obligations" if resistance_indices is not None
                             else "provisional_numeric_checks_without_coverage",
        "max_dcr_published": maximum,
        "observed_governing_checks": [c for c in candidates if c["dcr_published"] == maximum],
        "failed_checks": failures,
        "excluded_checks": excluded,
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
    admissibility = _build_chapter_admissibility(case, section)

    output_dir = Path(results_dir) / safe_profile
    output_dir.mkdir(parents=True, exist_ok=True)
    if safe_case_tag:
        output_path = output_dir / f"{safe_section}__{safe_case_tag}__{timestamp}.json"
    else:
        output_path = output_dir / f"{safe_section}__{timestamp}.json"
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


def _extract_output_options(payload: dict) -> tuple[dict, dict]:
    cleaned = copy.deepcopy(payload)
    output_cfg = cleaned.pop("output", {})
    try:
        options = OutputOptions.model_validate(output_cfg)
    except PydanticValidationError as exc:
        errors = [dict(error, loc=("output", *error["loc"])) for error in exc.errors(include_url=False)]
        raise PydanticValidationError.from_exception_data("OutputOptions", errors) from exc
    return cleaned, options.model_dump()


def _build_execution_results_dir(*, base_results_dir: str, input_file: str) -> str:
    run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    example_name = _sanitize_filename(Path(input_file).stem.upper())
    run_dir = Path(base_results_dir) / example_name / run_timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return str(run_dir)


def _run_single_case(
    *,
    engine: SteelDesignEngine,
    repo: SectionRepository,
    case: SteelCase,
    input_payload: dict,
    input_file: str,
    sections_file: str,
    results_dir: str,
    write_results_json: bool,
    case_tag: str | None = None,
) -> dict:
    result = engine.run(case)
    section = _build_case_section(case, repo)
    if case.custom_section is not None:
        profile_type = case.custom_section.type.value
    else:
        profile_type = section.type if section is not None else "UNKNOWN"
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
            "detailed_results_json": str(detailed_path) if detailed_path else None,
            "write_results_json": write_results_json,
        },
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
            payload = json.load(f, object_pairs_hook=_unique_json_object)
    except Exception as e:
        _print_structured_error(e, stage="parse_input")
        sys.exit(1)

    # Run
    try:
        is_bundle = isinstance(payload, dict) and "cases" in payload
        if is_bundle:
            case_definitions = payload["cases"]
            if not isinstance(case_definitions, list):
                raise ValidationError("cases must be a list of case objects.", code="INVALID_CASE_BUNDLE",
                                      details={"field": "cases", "received_type": type(case_definitions).__name__})
            if not case_definitions:
                aggregate_case_statuses([])  # canonical empty-bundle policy, before any execution/output
            for index, definition in enumerate(case_definitions):
                if not isinstance(definition, dict):
                    raise ValidationError("Each bundle case must be an object.", code="INVALID_CASE_BUNDLE",
                                          details={"field": f"cases[{index}]", "received_type": type(definition).__name__})
        execution_results_dir = _build_execution_results_dir(base_results_dir=args.results_dir, input_file=args.input_file)
        if is_bundle:
            base_payload = {key: value for key, value in payload.items() if key != "cases"}
            summaries = []
            for index, case_definition in enumerate(case_definitions):
                case_tag = str(case_definition.get("name") or f"case_{index+1}")
                case_override = {k: v for k, v in case_definition.items() if k != "name"}
                merged_payload = _merge_case_payload(base_payload, case_override)
                case_payload, output_options = _extract_output_options(merged_payload)
                case = SteelCase(**case_payload)
                summary = _run_single_case(
                    engine=engine,
                    repo=repo,
                    case=case,
                    input_payload=case_payload,
                    input_file=args.input_file,
                    sections_file=args.sections,
                    results_dir=execution_results_dir,
                    write_results_json=output_options["write_results_json"],
                    case_tag=case_tag,
                )
                summaries.append(summary)

            print(
                json.dumps(
                    {
                        "bundle": True,
                        "total_cases": len(summaries),
                        "status": aggregate_case_statuses([AnalysisStatus(s["status"]) for s in summaries]),
                        "results_run_dir": execution_results_dir,
                        "cases": summaries,
                    },
                    indent=2,
                )
            )
        else:
            case_payload, output_options = _extract_output_options(payload)
            case = SteelCase(**case_payload)
            summary = _run_single_case(
                engine=engine,
                repo=repo,
                case=case,
                input_payload=case_payload,
                input_file=args.input_file,
                sections_file=args.sections,
                results_dir=execution_results_dir,
                write_results_json=output_options["write_results_json"],
            )
            print(json.dumps(summary, indent=2))

    except Exception as e:
        _print_structured_error(e, stage="run_engine")
        sys.exit(1)

if __name__ == "__main__":
    main()
