"""Conservative executable projection of HFS-002, independent of routing.

The Markdown matrix remains the normative requirements source. This module
interprets a bounded subset; it neither imports implementations nor calculates
capacities. Unresolved branches stay pending, rather than inferred from checks.
"""
from ..models import SteelCase
from ..results_model import CoverageObligation, CoverageReport, CoverageStatus
from ..sections.models import Section


def build_coverage_plan(case: SteelCase, section: Section) -> CoverageReport:
    obligations = []

    def add(key, ids, state, component, condition, reason, required=(), *,
            unknown=False, resistance=True, alternatives=()):
        item = CoverageObligation(
            id=key, normative_ids=ids.split(), limit_state=state, component=component,
            condition=condition, reason=reason, required=list(required),
            applicability="UNKNOWN" if unknown else "TRUE", resistance=resistance,
            alternatives=list(alternatives))
        obligations.append(item)
        return item

    loads = case.loads
    family = section.type.upper()
    solid = case.custom_section is not None and family in {"SOLID_CIRCULAR", "SOLID_RECTANGULAR"}
    composite = case.composite
    pure_tension = loads.Pu < 0 and not any((loads.Mux, loads.Muy, loads.Vu, loads.Vux, loads.Vuy, loads.Tu))
    eligible = solid and composite is None and pure_tension
    scope = case.tension_scope
    missing = []
    for field in ("ordinary_prismatic_member", "concentric_axial_force", "no_special_conditions"):
        if scope is None or getattr(scope, field) is not True:
            missing.append(f"tension_scope.{field}=true with engineering evidence")
    for field in ("material_reference", "demand_reference", "net_area_reference",
                  "connection_reference", "external_checks_reference"):
        if scope is None or getattr(scope, field) is None:
            missing.append(f"tension_scope.{field}")

    basis = add("scope.basis", "N01 N02 N03 N34 N35", "applicability_basis", "member",
                "Ordinary member, qualified properties/material, demand/connection basis and external responsibilities",
                "Applicability evidence is absent or outside the independently bounded domain.",
                missing if eligible else ["Reviewed applicability and numerical evidence for this family/combination; tension_scope cannot qualify it"],
                unknown=True, resistance=False)
    if eligible and not missing:
        basis.status = CoverageStatus.EVALUATED
        basis.applicability = "TRUE"
        basis.reason = "Explicit external declarations checked for the ordinary concentric solid tie; references are not authenticated."
        basis.required = []

    if not any(loads.model_dump().values()):
        add("scope.nonempty", "N01", "nonempty_resistance_scope", "member", "At least one active resistance demand",
            "F-02: zero demand and zero resistance obligations cannot demonstrate compliance.",
            ["A nonzero demand and a defined resistance scope"])

    if composite is not None:
        role = composite.role.value
        add("I.eligibility", "N36", "composite_eligibility", "member", "Steel-concrete composite member",
            "I1 metadata/ratio checks do not establish materials, detailing, stages and classification.",
            ["I1 material/detailing evidence, stage, classification and independent validation"], unknown=True,
            resistance=False)
        add("I.transfer", "N44", "force_introduction_and_anchors", "member", "Force transfer between materials",
            "Force-introduction region/mechanism and I6/I8 coverage are not established.",
            ["Load introduction, region, anchor detailing and validated I6/I8 route"], unknown=True)
        axial_id = "N37" if role == "ENCASED_MEMBER" else "N38"
        if loads.Pu:
            add("I.axial.Pu", axial_id if role != "COMPOSITE_BEAM" else "N42", "composite_axial", "Pu",
                "Nonzero axial demand", "Composite axial implementation has no complete domain accreditation.",
                ["Validated axial route, material/detailing and stability conditions"])
        moment_id = {"ENCASED_MEMBER": "N39", "FILLED_MEMBER": "N40", "COMPOSITE_BEAM": "N43"}[role]
        for component in ("Mux", "Muy"):
            if getattr(loads, component):
                add(f"I.flexure.{component}", moment_id, "composite_flexural_resistance", component,
                    f"Nonzero {component}, each required stage/sign",
                    "F-34: reinforcement ratio or horizontal transfer does not verify required moment.",
                    ["Moment resistance for this axis/sign/stage and validated permitted method"])
        for component in ("Vu", "Vux", "Vuy"):
            if getattr(loads, component):
                add(f"I.shear.{component}", "N41", "composite_shear", component, f"Nonzero {component}",
                    "Direction, route eligibility and independent validation are unresolved; not all alternatives are mandatory.",
                    ["One complete permitted I4 route for this role/direction"],
                    alternatives=("I4.1(a) steel only", "I4.1(b) RC only", "I4.1(c) steel + reinforcement")
                    if role == "ENCASED_MEMBER" else ())
        if (loads.Pu and (loads.Mux or loads.Muy)) or (loads.Mux and loads.Muy):
            add("I.interaction", "N42", "composite_interaction", "Pu+Mux+Muy",
                "Axial-flexure or biaxial flexure, including Pu=0",
                "F-33/F-20: class-dependent I5 route and biaxial coverage are not accredited.",
                ["Validated I5/I1.2 alternative, all axes, stages and capacity dependencies"],
                alternatives=("I5(a) eligible H1.1/I1.2 route", "I5(b) class-dependent alternative"))
        if loads.Tu:
            add("I.torsion.Tu", "N45", "composite_torsion", "Tu", "Nonzero torsion",
                "Composite torsion is outside the studied/implemented domain.", ["Specific composite torsion study"])
    else:
        if loads.Pu < 0:
            for state in ("yielding", "rupture"):
                add(f"N04.{state}.Pu", "N04", state, "Pu", "Pu < 0: gross yielding AND effective-net rupture",
                    "Required tension evaluation has not yet been matched to a qualified implementation.",
                    ["D2-1" if state == "yielding" else "D2-2/D3 with supported An and U"])
            if family == "DOUBLE_ANGLE":
                add("N05.assembly", "N05", "built_up_tension_detailing", "Pu", "Built-up tension member",
                    "D4 assembly is not implemented.", ["Connectors/spacing and D4 assessment"])
        if loads.Pu > 0:
            for axis in ("x", "y"):
                add(f"N06.buckling.{axis}", "N06 N10", "flexural_buckling", axis, "Pu > 0, pertinent principal modes",
                    "Non-slender/E7 route and independent compression validation remain unresolved.",
                    ["Validated global mode, effective lengths and element classification"])
            if not solid:
                add("N07.torsional_buckling", "N07", "torsional_flexural_torsional_buckling", "z",
                    "Compression with symmetry, offsets and restraints making E4 applicable",
                    "Family label and an E4 check do not establish all E4 conditions.",
                    ["Symmetry, shear centre, restraints, offsets and validated E4 branch"], unknown=True)
                add("N10.effective_area", "N10", "effective_area_buckling", "Pu", "Slender compressed elements",
                    "F-35: QFy/Ag implementation is not accredited as Fn*Ae under E7.",
                    ["Element classification; validated E7 effective areas and global stress"], unknown=True)
            if family == "SINGLE_ANGLE":
                add("N08.angle_alternative", "N08", "angle_compression_alternative", "Pu", "Single-angle compression",
                    "F-36: five E5 conditions, configurations and piecewise branches are not established.",
                    ["Connection/loading conditions and all applicable E5 branches or H2 route"], unknown=True,
                    alternatives=("Eligible E5(a)/(b)", "General eccentric loading with Chapter H"))
            if family == "DOUBLE_ANGLE":
                add("N09.assembly", "N09", "built_up_compression", "Pu", "Built-up compression member",
                    "E6 slip/relative deformation and detailing are not covered by E3/E4 checks.",
                    ["Component spacing, connection and validated E6 route"])

        for component in ("Mux", "Muy"):
            if not getattr(loads, component):
                continue
            add(f"N11.conditions.{component}", "N02 N11", "flexure_conditions", component,
                "Nonzero moment: section classification, axes, load point and restraints",
                "F-03: absent ratios never prove compactness; family alone does not prove F1 eligibility.",
                ["Fabrication, widths/classification, load point, restraints, Lb/Cb basis"], unknown=True, resistance=False)
            ids = {"W": "N12 N13 N14 N15" if component == "Mux" else "N16",
                   "CHANNEL": "N12" if component == "Mux" else "N16",
                   "RECTANGULAR_HSS": "N17", "CIRCULAR_HSS": "N18",
                   "SINGLE_ANGLE": "N20", "DOUBLE_ANGLE": "N19",
                   "SOLID_RECTANGULAR": "N21", "SOLID_CIRCULAR": "N21"}.get(family, "N34")
            states = ["yielding", "local_buckling", "lateral_torsional_buckling"]
            if family == "RECTANGULAR_HSS":
                states = ["yielding", "flange_local_buckling", "web_local_buckling", "lateral_torsional_buckling"]
            elif family == "W" and component == "Mux":
                states.extend(["compression_flange_yielding", "tension_flange_yielding"])
            for state in states:
                item = add(f"F.{state}.{component}", ids, state, component,
                           "Flexure: determine the applicable branch per family, element, axis and restraint",
                           "Flexural branch or full implementation validation remains unresolved.",
                           ["Qualified F branch and each constituent limit state"], unknown=True)
                if solid and (state == "local_buckling" or
                              state == "lateral_torsional_buckling" and (family == "SOLID_CIRCULAR" or component == "Muy")):
                    item.status, item.applicability = CoverageStatus.NOT_APPLICABLE, "FALSE"
                    item.reason = "N21: no thin walls in a solid; F11 LTB is limited to rectangular major-axis bending."
                    item.required = []
            if family in {"W", "CHANNEL"}:
                add(f"N22.detailing.{component}", "N22", "flexural_complementary_requirements", component,
                    "Flange holes, proportions, cover plates and built-up details as applicable",
                    "F13 conditions are unknown; absence of input is not absence of holes/details.",
                    ["Hole/proportion/detailing evidence and required F13 checks"], unknown=True)

        for component in ("Vu", "Vux", "Vuy"):
            if not getattr(loads, component):
                continue
            ids = {"W": "N23 N27", "CHANNEL": "N23 N27", "SINGLE_ANGLE": "N24", "DOUBLE_ANGLE": "N24",
                   "RECTANGULAR_HSS": "N25", "CIRCULAR_HSS": "N26"}.get(family, "N35")
            add(f"G.shear.{component}", ids, "shear_yielding_buckling", component,
                f"Nonzero {component}; physical direction must be established without transforming axes",
                "F-08/F-11: directional mapping and full shear domain validation remain unresolved.",
                ["Physical direction, resisting elements, Lv if applicable and one validated shear route"],
                alternatives=("G2.1 base route", "G2.2/3 tension-field route with all prerequisites")
                if family in {"W", "CHANNEL"} else ())
            if family in {"W", "CHANNEL"}:
                add(f"N28.openings.{component}", "N28", "web_openings", component, "Web openings if present",
                    "No opening declaration/assessment is available.", ["Opening geometry or justified absence"], unknown=True)
        if (loads.Pu and (loads.Mux or loads.Muy)) or (loads.Mux and loads.Muy):
            add("N29.interaction", "N29", "axial_biaxial_interaction", "Pu+Mux+Muy",
                "Axial plus bending OR biaxial bending even with Pu=0",
                "F-01/F-33: isolated checks do not satisfy interaction; available HSS route lacks full accreditation.",
                ["Eligible and validated H1 or H2 route and all dependent capacities"],
                alternatives=("H1 for eligible symmetry/restraints", "H2 permitted general alternative"))
            if family in {"W", "CHANNEL"}:
                add("N32.holes", "N32", "combined_flange_rupture", "Pu+Mux", "Axial-flexure with flange holes",
                    "H4 hole conditions are not supplied.", ["Hole/net area and load-position evidence"], unknown=True)
        if loads.Tu:
            hss = family in {"RECTANGULAR_HSS", "CIRCULAR_HSS"}
            add("H.torsion.Tu", "N30" if hss else "N31", "torsional_yielding_buckling", "Tu", "Nonzero torsion",
                "Torsional route, geometry and independent validation are not complete.", ["Validated torsional domain"])
            if hss and any((loads.Pu, loads.Mux, loads.Muy, loads.Vu, loads.Vux, loads.Vuy)):
                add("N30.interaction", "N30", "torsion_interaction", "Pu+Mux+Muy+V+Tu",
                    "Torsion with other demands; H3 threshold determines a permitted alternative",
                    "F-06: directional demand/capacity selection is unvalidated; no isolated maximum correction is made.",
                    ["Validated Tr/Tc branch, directional capacities and maximum of directional ratios"],
                    alternatives=("H1 if Tr/Tc <= 0.20 with conditions", "H3-6 if Tr/Tc > 0.20"))

    return CoverageReport(method=case.design_method.value, section_name=section.name, profile_type=family,
                          scope_evidence=scope.model_dump() if scope is not None else {},
                          demand_components=loads.model_dump(), obligations=obligations)
