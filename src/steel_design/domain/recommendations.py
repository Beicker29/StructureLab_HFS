"""D1/E2 User Notes (S22 pp. 16.1-32/40), never resistance obligations."""
import math


def _ratio(length, radius):
    if radius is None or not all(math.isfinite(v) and v > 0 for v in (length, radius)):
        return None
    value = length / radius
    return value if math.isfinite(value) else None


def slenderness_recommendations(case, section):
    """Report supplied geometry; no unbraced/fabricated-length equivalence is assumed."""
    x = _ratio(case.factors.Kx * case.lengths.Lx, section.rx if section else None)
    y = _ratio(case.factors.Ky * case.lengths.Ly, section.ry if section else None)
    observed = {axis: value for axis, value in (("x", x), ("y", y)) if value is not None}
    maximum = max(observed.values(), default=None)
    axes = [axis for axis, value in observed.items() if value == maximum]
    basis = case.slenderness_advice_basis
    fabricated = (_ratio(basis.fabricated_length, basis.least_radius)
                  if basis and basis.fabricated_length is not None else None)

    def advice(applicable, ratio, limit, expression, reason):
        assessment = ("NOT_APPLICABLE" if applicable is False else "UNKNOWN"
                      if applicable is None or ratio is None else
                      "WITHIN_RECOMMENDATION" if ratio <= limit else "EXCEEDS_RECOMMENDATION")
        return {"source_type": "User Note", "resistance": False, "applicable": applicable,
                "assessment": assessment, "ratio": ratio, "recommended_max": limit,
                "expression": expression, "reason": reason}

    d1_applicable = (False if case.loads.Pu >= 0 else
                     None if basis is None or basis.is_rod is None else not basis.is_rod)
    d1 = advice(d1_applicable, fabricated, 300.0, "fabricated_length / least_radius",
                "D1 has no maximum mandatory tension slenderness. Rods are excepted from this recommendation; unknown rod status or fabricated geometry is not inferred.")
    e2 = advice(case.loads.Pu > 0, maximum if len(observed) == 2 else None, 200.0,
                "max(Kx*Lx/rx, Ky*Ly/ry), supplied local axes only",
                "E2 recommendation only. Both local axes must be available; principal/torsional stability and E5 applicability are separate requirements.")
    e2["fabricated_member"] = advice(case.loads.Pu > 0, fabricated, 300.0,
                "fabricated_length / least_radius", "Second E2 User Note recommendation; not a resistance limit.")
    return {"version": "HFS-015-advice-v1", "resistance": False,
            "short": f"D1: {d1['assessment']} | E2: {e2['assessment']} (recommendations only)",
            "D1": d1, "E2": e2,
            "inputs": {"KL_over_r_x": x, "KL_over_r_y": y,
                       "KL_over_r_governing_observed": maximum, "governing_axes": axes,
                       "fabricated_length_over_least_radius": fabricated},
            "limits": {"D1_recommended_max": 300.0, "E2_effective_recommended_max": 200.0,
                       "E2_fabricated_recommended_max": 300.0},
            "mandatory_conditions": ([{"reference": "E5(4), pp. 16.1-43/44",
                "source_type": "Specification", "assessment": "NOT_EVALUATED",
                "reason": "Lc/r as determined by the applicable E5 alternative must not exceed 200, together with all other E5 conditions. General KL/r advice does not establish that alternative; HFS-010 N08 remains authoritative for pending coverage."}]
                if section is not None and section.type.upper() in {"L", "ANGLE", "SINGLE_ANGLE"} and case.loads.Pu > 0 else [])}
