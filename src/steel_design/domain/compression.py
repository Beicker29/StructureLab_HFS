"""Chapter E for one member: classification, selection, execution, governing strength.

Single owner of compression selection (organized after Table User Note E1.1
and checked against the mandatory text of E3-E7). Formulas live only in
codes/aisc_360_22/compression.py. Every computed mode is kept in the result;
the governing mode is the lowest Pn (E1). Domains that need data or decisions
not available here raise structured errors instead of returning a strength.
"""
import math

from ..codes.aisc_360_22 import compression as eq
from ..models import SteelCase
from ..sections.models import Section
from .errors import IncompleteSectionDataError, RuleNotImplementedError


SUPPORTED_FAMILIES = ("W", "CHANNEL", "RECTANGULAR_HSS", "CIRCULAR_HSS", "SINGLE_ANGLE",
                      "SOLID_RECTANGULAR", "SOLID_CIRCULAR")
SOLIDS = ("SOLID_RECTANGULAR", "SOLID_CIRCULAR")

# B4.1a element inventory: (element, ratio source, B4.1a case, thickness field, count, Table E7.1 kind)
_ELEMENTS = {
    "W": (("flange", "bf_2tf_ratio", 1, "tf", 4, "UNSTIFFENED"),
          ("web", "h_tw_ratio", 5, "tw", 1, "STIFFENED")),
    "CHANNEL": (("flange", "b_t_ratio", 1, "tf", 2, "UNSTIFFENED"),
                ("web", "h_tw_ratio", 5, "tw", 1, "STIFFENED")),
    "RECTANGULAR_HSS": (("wall_b", "b_tdes_ratio", 6, "tdes", 2, "HSS_WALL"),
                        ("wall_h", "h_tdes_ratio", 6, "tdes", 2, "HSS_WALL")),
    "CIRCULAR_HSS": (("wall", "d_t_ratio", 9, "tdes", 1, None),),
}

_GENERAL_LIMITATIONS = (
    "Effective lengths Lc = K*L are user inputs; E2/Chapter C or Appendix 7 determination is not verified.",
    "Bracing strength/stiffness (Appendix 6) and connections are outside this calculation.",
)


def _blocked(reason, section, **details):
    raise RuleNotImplementedError(reason, code="COMPRESSION_DOMAIN_BLOCKED",
                                  details={"section": section.name, "profile_type": section.type, **details})


def _incomplete(reason, section, fields):
    raise IncompleteSectionDataError(reason, code="COMPRESSION_DATA_INCOMPLETE",
                                     details={"section": section.name, "profile_type": section.type,
                                              "fields": fields})


def _require(section, *names):
    missing = [name for name in names if not _positive(getattr(section, name))]
    if missing:
        _incomplete("Compression requires these section properties.", section, ["section." + n for n in missing])


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _angle_legs(section):
    _require(section, "d", "b", "t")
    long_leg, short_leg = max(section.d, section.b), min(section.d, section.b)
    return long_leg, short_leg


def classify_elements(section: Section, E: float, Fy: float) -> dict:
    """B4.1a classification of every compression element (nonslender/slender)."""
    family = section.type.upper()
    if family in SOLIDS:
        return {"elements": [], "slender": False,
                "reference": "Solid section: no thin compression elements (Table User Note E1.1, E3 only)"}
    rows = []
    if family == "SINGLE_ANGLE":
        long_leg, short_leg = _angle_legs(section)
        layout = [("long_leg", long_leg / section.t, 3, "t", 1, "UNSTIFFENED"),
                  ("short_leg", short_leg / section.t, 3, "t", 1, "UNSTIFFENED")]
    elif family in _ELEMENTS:
        layout = []
        for element, source, case, thickness, count, kind in _ELEMENTS[family]:
            _require(section, source)  # thickness is only needed for E7 effective widths
            layout.append((element, getattr(section, source), case, thickness, count, kind))
    else:
        _blocked("No B4.1a element inventory is implemented for this family.", section)
    for element, ratio, case, thickness, count, kind in layout:
        limit = eq.lambda_r(case, E, Fy)
        rows.append({"element": element, "b4_case": case, "ratio": ratio, "lambda_r": limit,
                     "slender": ratio > limit, "t_field": thickness, "count": count, "e7_kind": kind})
    return {"elements": rows, "slender": any(row["slender"] for row in rows),
            "reference": "B4.1a (Table B4.1a)"}


def _flexural_mode(axis, E, K, L, r):
    lc = K * L
    return {"limit_state": "flexural_buckling", "provision": "E3", "axis": axis,
            "Fe_equation": "E3-4", "Lc_mm": lc, "r_mm": r, "Lc_over_r": lc / r,
            "Fe_mpa": eq.elastic_flexural_stress(E, lc, r)}


def _global_modes(case: SteelCase, section: Section) -> tuple[dict, list]:
    """Elastic buckling stresses of every applicable global mode, plus pending notes."""
    family = section.type.upper()
    E, G = case.material.E, eq.G_STEEL
    f, ln = case.factors, case.lengths
    offsets = f.xa != 0 or f.ya != 0
    notes = []
    _require(section, "area", "rx", "ry")
    modes = {"FB-x": _flexural_mode("x", E, f.Kx, ln.Lx, section.rx),
             "FB-y": _flexural_mode("y", E, f.Ky, ln.Ly, section.ry)}
    lcz = f.Kz * ln.Lz

    if family == "W":
        # Table User Note E1.1 lists TB for doubly symmetric I; evaluated in every case.
        if offsets:
            _require(section, "j", "ix", "iy", "ho")
            try:
                offset = eq.torsional_stress_bracing_offset(
                    E=E, G=G, J=section.j, Iy=section.iy, Ix=section.ix, Ag=section.area, rx=section.rx,
                    ry=section.ry, ho=section.ho, Lcz=lcz, xa=f.xa, ya=f.ya)
            except ValueError:
                _blocked("E4(f): lateral bracing offset in both directions requires an elastic buckling analysis.",
                         section, xa=f.xa, ya=f.ya)
            modes["TB"] = {"limit_state": "constrained_axis_torsional_buckling", "provision": "E4(d)/(e)",
                           "axis": "z", "Fe_equation": offset["equation"], "Lcz_mm": lcz, "xa_mm": f.xa,
                           "ya_mm": f.ya, "ro2_mm2": offset["ro2_mm2"], "Fe_mpa": offset["Fe_mpa"]}
        else:
            _require(section, "j", "ix", "iy")
            if section.cw is None:
                _incomplete("E4-2 requires the warping constant Cw.", section, ["section.cw"])
            modes["TB"] = {"limit_state": "torsional_buckling", "provision": "E4(a)", "axis": "z",
                           "Fe_equation": "E4-2", "Lcz_mm": lcz, "Cw_mm6": section.cw, "J_mm4": section.j,
                           "Fe_mpa": eq.torsional_stress_doubly_symmetric(
                               E=E, G=G, Cw=section.cw, J=section.j, Lcz=lcz, Ix=section.ix, Iy=section.iy)}
    elif family == "CHANNEL":
        if offsets:
            _blocked("E4(f): bracing offset on a channel requires an elastic buckling analysis.",
                     section, xa=f.xa, ya=f.ya)
        _require(section, "j", "ro", "H")
        if section.cw is None:
            _incomplete("E4-7 requires the warping constant Cw.", section, ["section.cw"])
        fez = eq.torsional_stress(E=E, G=G, Cw=section.cw, J=section.j, Lcz=lcz, Ag=section.area, ro=section.ro)
        fex = modes["FB-x"]["Fe_mpa"]
        # E4 User Note: x is the channel axis of symmetry, so Fex replaces Fey in E4-3.
        modes["FTB"] = {"limit_state": "flexural_torsional_buckling", "provision": "E4(b)", "axis": "x+z",
                        "Fe_equation": "E4-3", "symmetry_axis": "x", "Fex_mpa": fex, "Fez_mpa": fez,
                        "Fez_equation": "E4-7", "Lcz_mm": lcz, "ro_mm": section.ro, "H": section.H,
                        "Fe_mpa": eq.flexural_torsional_stress_singly_symmetric(fex, fez, section.H)}
    elif family in {"RECTANGULAR_HSS", "CIRCULAR_HSS"}:
        # E4 applies to doubly symmetric members only when the torsional unbraced
        # length exceeds the lateral unbraced length (S22 E4 scope).
        if offsets:
            _blocked("E4(f): bracing offset on an HSS requires an elastic buckling analysis.",
                     section, xa=f.xa, ya=f.ya)
        if ln.Lz > min(ln.Lx, ln.Ly):
            _require(section, "j", "ix", "iy")
            if section.cw is None:
                _incomplete("Lz exceeds the lateral unbraced length, so E4-2 is required; Cw is not in the catalog.",
                            section, ["section.cw"])
            modes["TB"] = {"limit_state": "torsional_buckling", "provision": "E4(a)", "axis": "z",
                           "Fe_equation": "E4-2", "Lcz_mm": lcz, "Cw_mm6": section.cw, "J_mm4": section.j,
                           "Fe_mpa": eq.torsional_stress_doubly_symmetric(
                               E=E, G=G, Cw=section.cw, J=section.j, Lcz=lcz, Ix=section.ix, Iy=section.iy)}
        else:
            notes.append("E4 not applicable: Lz does not exceed the lateral unbraced length (S22 E4 scope).")
    return modes, notes


def _single_angle_modes(case: SteelCase, section: Section) -> tuple[dict, list]:
    """E5 effective slenderness route; eccentricity neglected only when E5 permits it."""
    basis = case.single_angle_e5
    if basis is None:
        _blocked("Single-angle compression requires single_angle_e5; otherwise E5 sends the "
                 "member to Chapter H (H2) for axial load plus flexure, which is outside this program.", section)
    conditions = {"E5(1) loaded at the ends through the same leg": basis.loaded_at_ends_through_same_leg,
                  "E5(2) welded or at least two bolts": basis.welded_or_two_bolts_min,
                  "E5(3) no intermediate transverse loads": basis.no_intermediate_transverse_loads}
    failed = [name for name, value in conditions.items() if value is not True]
    long_leg, short_leg = _angle_legs(section)
    leg_ratio = long_leg / short_leg
    if leg_ratio >= 1.7:
        failed.append("E5(5) long/short leg ratio < 1.7")
    if failed:
        _blocked("E5 conditions not met; evaluate with Chapter H (H2), outside this program.", section, failed=failed)
    _require(section, "area", "rx", "ry", "rz")
    connected = basis.connected_leg if leg_ratio > 1 else "long"
    # Catalog convention: rx > ry, so the long leg is parallel to y. ra is the
    # radius about the geometric axis parallel to the connected leg.
    ra = section.ry if connected == "long" else section.rx
    if leg_ratio > 1 and not section.rx > section.ry:
        _blocked("Cannot identify the geometric axis parallel to the connected leg (expected rx > ry).", section)
    slenderness = eq.e5_effective_slenderness(L_over_ra=basis.L / ra, configuration=basis.configuration,
                                              connected_leg=connected, leg_ratio=leg_ratio,
                                              L_over_rz=basis.L / section.rz)
    if not slenderness["within_200"]:
        _blocked("E5(4): Lc/r from E5 exceeds 200; evaluate with Chapter H (H2), outside this program.",
                 section, Lc_over_r=slenderness["Lc_over_r"])
    if long_leg / section.t > 0.71 * math.sqrt(case.material.E / case.material.Fy):
        _blocked("b/t > 0.71*sqrt(E/Fy): E5 requires flexural-torsional buckling per E4, whose principal-axis "
                 "effective lengths are not defined in the input (pending engineering decision).", section,
                 b_over_t=long_leg / section.t)
    lc_r = slenderness["Lc_over_r"]
    mode = {"limit_state": "flexural_buckling", "provision": "E5(" + basis.configuration + ")", "axis": "a",
            "slenderness_equation": slenderness["equation"], "L_mm": basis.L, "ra_mm": ra, "rz_mm": section.rz,
            "connected_leg": connected, "leg_ratio": leg_ratio, "Lc_over_r": lc_r,
            "Fe_mpa": math.pi**2 * case.material.E / lc_r**2, "Fe_equation": "E3-4"}
    notes = ["E5: eccentricity neglected per E5(a)/(b); conditions (1)-(3) declared by the user.",
             "E4 not required: b/t of the longest leg <= 0.71*sqrt(E/Fy)."]
    return {"FB-E5": mode}, notes


def _effective_area(section: Section, classification: dict, Fn: float, E: float, Fy: float) -> dict:
    """E7-1 Ae: gross area minus (b - be)*t per slender-capable plate, or E7-6/E7-7."""
    if section.type.upper() == "CIRCULAR_HSS":
        _require(section, "od", "tdes")
        # B4.1b(g)/E7.2: D outside diameter, t design thickness.
        return eq.e7_round_hss_area(Ag=section.area, D_over_t=section.od / section.tdes, E=E, Fy=Fy)
    plates, loss = [], 0.0
    _require(section, *{row["t_field"] for row in classification["elements"]})
    for row in classification["elements"]:
        t = getattr(section, row["t_field"])
        width = eq.e7_effective_width(b=row["ratio"] * t, t=t, lambda_r=row["lambda_r"],
                                      Fn=Fn, Fy=Fy, kind=row["e7_kind"])
        plates.append({"element": row["element"], "count": row["count"], **width})
        loss += row["count"] * width["area_loss_mm2"]
    ae = section.area - loss
    if not ae > 0:
        _incomplete("E7 effective area is not positive; check catalog geometry.", section, ["section.area"])
    return {"Ae_mm2": ae, "equation": "E7-1", "plates": plates}


def compression_strength(case: SteelCase, section: Section) -> dict:
    """Nominal and available compressive strength of one member (Chapter E)."""
    factor = eq.design_factor(case.design_method)
    family = section.type.upper()
    E, Fy = case.material.E, case.material.Fy
    if abs(E - eq.E_STEEL) > 1e-6:
        _incomplete("Chapter E defines E = 200000 MPa.", section, ["material.E"])
    if family == "DOUBLE_ANGLE":
        _blocked("Double angles are not implemented: contact vs separators (B4.1a case 1/3), E6 connectors "
                 "and J for E4-7 are not defined in catalog/input (pending engineering decision).", section)
    if family not in SUPPORTED_FAMILIES:
        _blocked("Chapter E is not implemented for this family.", section)

    classification = classify_elements(section, E, Fy)
    slender = classification["slender"]
    if family == "SINGLE_ANGLE":
        elastic, notes = _single_angle_modes(case, section)
    else:
        elastic, notes = _global_modes(case, section)

    modes = {}
    for name, mode in elastic.items():
        stress = eq.nominal_stress(Fy, mode["Fe_mpa"])
        if slender:
            area = _effective_area(section, classification, stress["Fn_mpa"], E, Fy)
        else:
            area = {"Ae_mm2": section.area, "equation": "E4-1" if mode["provision"].startswith("E4") else "E3-1"}
        pn = stress["Fn_mpa"] * area["Ae_mm2"]
        modes[name] = {**mode, "Fn_mpa": stress["Fn_mpa"], "Fn_equation": stress["equation"],
                       "Fy_over_Fe": stress["Fy_over_Fe"], "area_mm2": area["Ae_mm2"],
                       "Pn_equation": "E7-1" if slender else area["equation"],
                       "area_basis": "Ae" if slender else "Ag", "effective_area": area if slender else None,
                       "Pn_kN": pn / 1000.0, "available_kN": eq.available_strength(pn)}

    governing = min(modes, key=lambda key: modes[key]["Pn_kN"])
    pn_kn = modes[governing]["Pn_kN"]
    available = eq.available_strength(pn_kn * 1000.0)
    provisions = sorted({m["provision"] for m in modes.values()} | ({"E7"} if slender else set()))
    pending = []
    worst = max(m["Lc_over_r"] for m in modes.values() if "Lc_over_r" in m)
    if worst > 200:
        notes.append(f"E2 User Note: Lc/r = {worst:.1f} exceeds the preferred 200 (recommendation, not a strength limit).")
    if family == "RECTANGULAR_HSS":
        pending.append("Wall widths b, h come from the catalog (outside dimension - 3*tdes, B4.1b(d) when the corner radius is unknown).")
    if slender and family == "CIRCULAR_HSS" and modes[governing]["effective_area"]["bounded_to_Ag"]:
        pending.append("E7-7 Ae limited to Ag (engineering criterion D-2, docs/chapter-e.md).")
    return {
        "chapter": "E", "code": "ANSI/AISC 360-22",
        "section": section.name, "family": family,
        "design_method": case.design_method.value,
        "inputs": {"Fy_mpa": Fy, "E_mpa": E, "G_mpa": eq.G_STEEL, "Ag_mm2": section.area,
                   "Kx": case.factors.Kx, "Ky": case.factors.Ky, "Kz": case.factors.Kz,
                   "Lx_mm": case.lengths.Lx, "Ly_mm": case.lengths.Ly, "Lz_mm": case.lengths.Lz},
        "classification": classification,
        "provisions": ["E1"] + provisions,
        "modes": modes,
        "governing_mode": governing,
        "governing_equation": modes[governing]["Pn_equation"],
        "Fn_mpa": modes[governing]["Fn_mpa"],
        "Pn_kN": pn_kn,
        "available": available,
        "available_kN": available[case.design_method.value],
        "design_factor": factor,
        "notes": notes,
        "limitations": list(_GENERAL_LIMITATIONS) + pending,
    }
