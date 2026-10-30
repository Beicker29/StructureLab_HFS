"""Descriptive AISC metadata attached to RuleDefinition; never an applicability engine.

The canonical instances live ONLY in profile_router.RULE_DEFINITIONS. This
module constructs immutable annotations, with no case inputs, I/O or execution.
HFS-002 remains the independent requirements authority; coverage owns credit.
"""
from dataclasses import replace
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SOURCE_INDEX = "docs/normative/hfs002-sources.md"
MATRIX = "docs/normative/hfs002-applicability.md"
METHOD_POLICY = "steel_design.domain.design_methods:validate_method_scope"


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    edition: Literal["ANSI/AISC 360-22"] = "ANSI/AISC 360-22"
    source: Literal["S22", "UN22", "C22"]
    chapter: str = Field(pattern=r"^[A-N]$")
    provision: str = Field(min_length=1)
    equations: tuple[str, ...]
    pdf_pages: str = Field(min_length=1)

    @model_validator(mode="after")
    def nonblank(self):
        if any(not text.strip() for text in (self.provision, self.pdf_pages, *self.equations)):
            raise ValueError("Citation text cannot be blank")
        return self


class RuleMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    citations: tuple[Citation, ...] = Field(min_length=1)
    matrix_ids: tuple[str, ...] = Field(min_length=1)
    family_scope: str = Field(min_length=1)
    conditions: str = Field(min_length=1)
    equation_note: str = Field(min_length=1)
    implementation_state: Literal["PARTIAL", "BLOCKED", "NOT_IMPLEMENTED", "EXTERNAL", "ADVISORY"]
    software_verification: Literal["TESTS_REFERENCED", "NO_DIRECT_TEST"]
    software_tests: tuple[str, ...]
    independent_tests: tuple[str, ...]
    independent_scope: str = Field(min_length=1)
    normative_validation: Literal["NOT_ACCREDITED"] = "NOT_ACCREDITED"
    limitations: str = Field(min_length=1)
    findings: tuple[str, ...] = Field(min_length=1)
    calculation_refs: tuple[str, ...]
    selection_ref: str = Field(min_length=1)
    method_note: str = Field(min_length=1)

    @model_validator(mode="after")
    def coherent_evidence(self):
        for name in type(self).model_fields:
            value = getattr(self, name)
            if isinstance(value, str) and not value.strip():
                raise ValueError(f"{name}: blank metadata")
            if isinstance(value, tuple) and any(isinstance(v, str) and not v.strip() for v in value):
                raise ValueError(f"{name}: blank reference")
        if bool(self.software_tests) != (self.software_verification == "TESTS_REFERENCED"):
            raise ValueError("software_verification must describe actual test references, not accreditation")
        return self


def citation(provision, pages, *equations, source="S22"):
    return Citation(source=source, chapter=provision[0], provision=provision,
                    equations=equations, pdf_pages=pages)


def annotation(n, family, condition, citations, *, tests, calculations=(), findings=("F-23", "F-30"),
               independent=(), independent_scope="No independent numerical reference identified for this domain.",
               state="PARTIAL", limitations="Implementation is partial; full normative validation remains pending.",
               equation_note="Section-level reference; exhaustive branch-to-equation correspondence remains pending.",
               selection="steel_design.domain.routing.profile_router:ProfileRouter.get_rules",
               method="Existing method guard applies; no load combinations are generated or validated."):
    return RuleMetadata(citations=citations, matrix_ids=n, family_scope=family, conditions=condition,
                        equation_note=equation_note, implementation_state=state,
                        software_verification="TESTS_REFERENCED" if tests else "NO_DIRECT_TEST",
                        software_tests=tests, independent_tests=independent, independent_scope=independent_scope,
                        limitations=limitations, findings=findings, calculation_refs=calculations,
                        selection_ref=selection, method_note=method)


def metadata_groups():
    """Explicit reviewed indexing of existing sources, not generated requirements.

    A group shares descriptive context, never formulas, selection or coverage.
    Equation labels and internal IDs are intentionally separate (F-37).
    """
    calc = "steel_design.codes.aisc_360_22."
    tests = "tests/"
    rules = "steel_design.domain.rules."
    f_method = "Public Chapter F remains LRFD-only; ASD is blocked by the existing method policy."
    i_method = "Chapter I remains LRFD-only; nominal I1.2 method is separate from LRFD/ASD."
    composite_selection = "steel_design.domain.routing.profile_router:ProfileRouter._get_composite_rules"
    for rid, equation in (("D2-1", "D2-1"), ("D2-2", "D2-2")):
        yield (rid,), annotation(("N04",), "Ordinary steel members in tension",
            "Pu<0; yielding of gross area and rupture of effective net area are distinct. An/U require external connection provenance.",
            (citation("D2; D3", "100-103", equation, *(('D3-1',) if rid == 'D2-2' else ())),),
            tests=(tests+"test_normative_d2_e3_f2.py", tests+"test_hfs010_coverage.py", tests+"test_hfs017_design_method.py"),
            calculations=(calc+"tension_calc", "steel_design.domain.evaluators.tension_evaluator:TensionEvaluator.evaluate"),
            independent=(tests+"test_hfs010_coverage.py::test_d2_independent_capacities_and_global_pass_fail",),
            independent_scope="Manual D2 arithmetic LRFD/ASD for stipulated ordinary solid ties; not all connection geometries.",
            equation_note="Internal ID coincides with the cited D2 equation; D3 supplies Ae=U*An for rupture.",
            limitations="Only the pre-existing HFS-010 solid-tie gate can grant conditional credit; this metadata grants none.")
    for rid, n, provision, equations, condition, findings in (
        ("E3", "N06", "E1; E3", ("E3-1", "E3-2", "E3-3", "E3-4"), "Non-slender compression with complete principal axes; single/double angles blocked in HFS-031R0.", ("F-23", "F-30", "F-35", "F-36", "F-48")),
        ("E4", "N07", "E4", ("E4-1 to E4-12",), "HFS-031R0 permits only complete non-slender doubly symmetric W/HSS without bracing offsets; coupling is blocked.", ("F-23", "F-36", "F-46", "F-47", "F-48")),
        ("E5", "N08", "E5(a)/(b)", ("E5-1 to E5-4",), "Single angles; all five conditions and effective-slenderness branches require justification.", ("F-07", "F-36")),
        ("E7", "N10", "E7; Table E7.1", ("E7-1 to E7-7",), "Slender compression elements; normative effective-area treatment differs from current Q implementation.", ("F-35",)),
    ):
        yield (rid,), annotation((n,), "Steel compression families; see independent N-row", condition,
            (citation(provision, "106-117", *equations),), tests=(tests+"test_chapter_e_rules.py", tests+"test_hfs017_design_method.py", tests+"test_hfs031r0_containment.py"),
            calculations=(calc+"axial_calc", "steel_design.domain.evaluators.compression_domain:require_compression_domain"), findings=findings,
            state="BLOCKED" if rid in {"E5", "E7"} else "PARTIAL",
            independent=(tests+"test_hfs017_design_method.py::test_d2_e3_independent_rule_capacities_and_trace",) if rid == "E3" else (),
            independent_scope="E3 stipulated flexural-buckling arithmetic, both methods; not all modes/families." if rid == "E3" else "No complete independent oracle for this domain; method tests are not nominal-strength validation.",
            limitations="HFS-031R0 contains unverified domains; no E5/E7 active check is returned. F-35/36/46/47/48 remain open; containment is not a numerical correction or accreditation.")
    flexure = (
        (("F2-1", "F2-2"), "N12", "F2.1/2", "118-121", ("F2-1 to F2-8",), "Doubly symmetric I / compact channel, major axis", "Compact flange/web; Lb/Lp/Lr branches and Cb with provenance.", "evaluate_f2", ("F-03", "F-22", "F-31")),
        (("F3-1", "F3-2", "F3-3"), "N13", "F3.1/2; F2.2", "121-122", ("F3-1", "F3-2"), "Doubly symmetric I; not channels", "Compact web with noncompact/slender flanges; internal F3-3 is not a Specification equation.", "evaluate_f3", ("F-37",)),
        (("F4-1", "F4-2", "F4-3", "F4-4"), "N14", "F4; F5 alternative", "122-129", (), "I members with compact/noncompact webs", "Current implementation delegates to a conservative F5 alternative; its domain is not accredited.", "evaluate_f4_conservative", ("F-19", "F-37")),
        (("F5-1", "F5-2", "F5-3", "F5-4"), "N15", "F5.1-4", "127-129", ("F5-1 to F5-10",), "Doubly/singly symmetric I with slender centered web", "Compression/tension flange yielding, LTB and flange local buckling; F13 supplementary requirements remain.", "evaluate_f5", ("F-30", "F-38")),
        (("F6-1", "F6-2"), "N16", "F6.1/2", "129-130", ("F6-1 to F6-4",), "I and channel, minor axis", "Flange yielding/local buckling; full channel flange width needs independent review; no credit for major axis.", "evaluate_f6", ("F-03", "F-31")),
        (tuple(f"F7-{i}-{axis}" for i in range(1,5) for axis in ("Mx","My")), "N17", "F7.1-4", "130-133", ("F7-1 to F7-7", "F7-10 to F7-13 (local S22)"), "Rectangular HSS; arbitrary welded boxes not accredited", "Axis-specific yielding, flange/web local buckling and LTB; slender web plus slender flange remains unresolved.", "evaluate_f7", ("F-30", "F-28")),
        (tuple(f"F8-{i}-{axis}" for i in (1,2) for axis in ("Mx","My")), "N18", "F8.1/2", "132-133", ("F8-1 to F8-4",), "Circular HSS", "D/t strictly below 0.45E/Fy; yielding and local buckling by each requested axis.", "evaluate_f8", ("F-12", "F-33")),
        (tuple(f"F10-{i}-{axis}" for i in (1,2,3) for axis in ("Mx","My")), "N20", "F10.1-3", "136-139", ("F10-1 to F10-8",), "Single angles", "Principal/geometric-axis permissions, toe stress sign, lateral restraint and connection conditions; H2 still missing.", "evaluate_f10", ("F-01", "F-30", "F-33")),
        (tuple(f"F11-{i}-{axis}" for i in (1,2) for axis in ("Mx","My")), "N21", "F11", "139-140", ("F11-1 to F11-5",), "Solid rectangular/circular bars", "LTB only rectangular major-axis domain; circular/minor exceptions do not remove interaction requirements.", "evaluate_f11", ("F-30", "F-33")),
    )
    for ids, n, provision, pages, equations, family, condition, function, findings in flexure:
        citations = (citation(provision, pages, *equations), citation("F1(a)", "118-120"))
        if n == "N14":
            citations += (citation("F4 User Note", "124", source="UN22"),)
        if n == "N20":
            citations += (citation("H2", "152-153", "H2-1"),)
        yield ids, annotation((n,), family, condition, citations,
            tests=(tests+"test_chapter_f_rules.py", tests+"test_hfs012_flexure_selection.py", tests+"test_hfs017_design_method.py"),
            calculations=(calc+"flexure_calc:"+function, calc+"flexure_calc:available_flexural_strength"), findings=findings,
            independent=(tests+"test_hfs012_flexure_selection.py::test_selected_f2_yielding_preserves_independent_lrfd_reference",) if n == "N12" else (),
            independent_scope="F2 yielding LRFD arithmetic only, not LTB." if n == "N12" else "No independent nominal-strength oracle credited to this whole provision; F1 conversion evidence is separately linked in H1/H3 tests.",
            limitations="LRFD implementations remain partial; normative chapter applicability and every branch are not accredited. F-31 remains P0 open.",
            equation_note="Ranges identify the provision, not a verified one-to-one mapping from internal IDs. F3/F4 labels and F7 local numbering require review.", method=f_method)
    for ids, n, provision, pages, eqs, family, conditions, state, findings in (
        (("G2-Vx",), "N23", "G2.1-4", "143-147", ("G2-1 to G2-19",), "I/channel web", "Base shear branches; panel, stiffener and tension-field conditions are not fully checked.", "PARTIAL", ("F-30", "F-38")),
        (("G3-Vx", "G3-Vy"), "N24", "G3", "147", ("G3-1",), "Single/double angles", "Resisting leg and distribution are not established; direct rule blocks evaluation.", "BLOCKED", ("F-11", "F-42")),
        (("G4-Vx", "G4-Vy"), "N25", "G4", "148", ("G4-1",), "Rectangular HSS", "Resisting wall and direction must be explicit; shares actual capacities with H3.", "PARTIAL", ("F-06", "F-08", "F-11")),
        (("G5-Vx", "G5-Vy"), "N26", "G5", "148-149", ("G5-1", "G5-2a", "G5-2b"), "Circular HSS", "OD/design thickness; actual Lv required for length-dependent branch, never column L fallback.", "PARTIAL", ("F-12", "F-41")),
        (("G6-Vy",), "N27", "G6", "149", ("G6-1",), "I/channel transverse shear", "W without torsion only in current scope; channel distribution remains blocked.", "PARTIAL", ("F-11", "F-42")),
    ):
        independent = {
            "N23": (tests+"test_hfs017_design_method.py::test_g2_independent_exception_not_shared_with_other_chapters",),
            "N25": (tests+"test_hfs013_directional_h3.py::test_g4_independent_capacity_and_method",),
            "N26": (tests+"test_hfs013_directional_h3.py::test_round_numeric_functions_with_independently_given_lengths",),
        }.get(n, ())
        yield ids, annotation((n,), family, conditions, (citation(provision, pages, *eqs), citation("G1", "143")),
            tests=(tests+"test_chapter_g_rules.py", tests+"test_hfs013_directional_h3.py", tests+"test_hfs017_design_method.py"),
            calculations=(calc+"shear_calc",), findings=findings, independent=independent, state=state,
            independent_scope="Stipulated G2 factor exception / G4 capacities / G5 lengths only where explicitly referenced; no family-wide accreditation.",
            limitations="Physical provenance, all panel/directional branches and independent normative review remain pending.")
    yield ("H1",), annotation(("N29",), "HSS in current implementation; wider normative families remain pending",
        "Current path requires nonzero Pu and bending. H1/H2 alternatives and biaxial bending without axial force are not completed.",
        (citation("H1.1/2; H2", "150-153", "H1-1a", "H1-1b", "H2-1"),),
        tests=(tests+"test_chapter_h_rules.py", tests+"test_hfs013_design_method.py"),
        calculations=(calc+"combined_hss_calc",), findings=("F-01", "F-20", "F-33", "F-37", "F-43"),
        equation_note="Legacy tension label H1-2 is not an interaction equation: S22 H1-2 is Pey. Output labels preserved; mapping remains disputed.",
        limitations="F1 factor correction does not validate nominal capacities, tension interaction or full H1 domain.")
    for rid, provision, eqs in (("H3-1", "H3.1", ("H3-1 to H3-5",)), ("H3-2", "H3.2", ("H3-6",))):
        yield (rid,), annotation(("N30",), "Rectangular/circular HSS",
            "Explicit C and physical lengths; rectangular h/t<=260. Tr/Tc<=0.20 alternative remains blocked, never an automatic PASS.",
            (citation(provision, "153-154", *eqs),),
            tests=(tests+"test_chapter_h_rules.py", tests+"test_hfs013_directional_h3.py", tests+"test_hfs017_design_method.py"),
            calculations=(calc+"combined_hss_calc", "steel_design.domain.evaluators.hss_shear:evaluate_hss_shear"),
            independent=(tests+"test_hfs013_directional_h3.py::test_rectangular_torsion_regions_independent",) if rid == "H3-1" else (tests+"test_hfs013_directional_h3.py::test_h3_6_normal_term_is_linear",),
            independent_scope="Stipulated torsional stress branches / H3-6 algebra only; axial and flexural capacity validation remains separate.",
            findings=("F-06", "F-39", "F-40", "F-41", "F-42", "F-43"),
            equation_note="H3-1/H3-2 are internal rule IDs for sections H3.1/H3.2, not equation numbers.")
    # Chapter I already executes procedurally. Metadata never replaces that path.
    for ids, n, provision, eqs, family, conditions, findings in (
        (("I1",), "N36", "I1.1-5; Tables I1.1a/b", (), "All supported composite roles", "Eligibility/material/detail prerequisites; current positive-input check is not comprehensive eligibility.", ("F-38",)),
        (("I2.ENCASED.COMPRESSION",), "N37", "I2.1b", ("I2-2 to I2-7",), "W steel core encased in concrete", "Compression with effective stiffness and length; detailing/force introduction still separate.", ("F-18", "F-20", "F-30")),
        (("I2.ENCASED.TENSION",), "N37", "I2.1c", ("I2-8",), "W steel core encased in concrete", "Tension of steel and reinforcement; load transfer is not established by this check.", ("F-20", "F-38")),
        (("I2.FILLED.COMPRESSION",), "N38", "I2.2b", ("I2-9 to I2-13",), "Concrete-filled rectangular/circular HSS", "Compression by composite local class and buckling; bare steel floor does not accredit composite branches.", ("F-20", "F-35")),
        (("I2.FILLED.TENSION",), "N38", "I2.2c", ("I2-14",), "Concrete-filled HSS", "Steel/reinforcement tension with separate detailing and load transfer.", ("F-20", "F-38")),
        (("I3.TRANSFER.CONCRETE", "I3.TRANSFER.STEEL", "I3.TRANSFER.ANCHORS"), "N43", "I3.2d", ("I3-1a", "I3-1b", "I3-1c"), "W beam with connected slab", "Horizontal transfer candidates; these checks do NOT verify flexural moment resistance or construction stages.", ("F-34", "F-38")),
        (("I3.ENCASED.REINFORCEMENT",), "N39", "I3.3a", ("I3-3",), "Encased composite members", "Reinforcement ratio check; not I3.3b pure moment resistance.", ("F-34",)),
        (("I3.FILLED.REINFORCEMENT",), "N40", "I3.4a", ("I3-4",), "Filled composite members", "Reinforcement/detail ratio; not I3.4b moment resistance.", ("F-34",)),
        (("I4.ENCASED.STEEL", "I4.ENCASED.RC", "I4.ENCASED.COMBINED", "I4.ENCASED.GOVERNING"), "N41", "I4.1(a/b/c)", (), "Encased composite members", "Steel-only, RC-only or combined alternatives; governing wrapper is software aggregation, not another equation.", ("F-20", "F-38")),
        (("I4.FILLED",), "N41", "I4.2", ("I4-1",), "Filled composite members", "Steel/concrete shear contributions; Kc, directions and member Mu/Vu/d require review.", ("F-20", "F-38")),
        (("I4.BEAM.STEEL",), "N41", "I4.3", (), "W composite beam", "Steel-only Chapter G shear; does not validate composite moment resistance.", ("F-20", "F-38")),
        (("I5",), "N42", "I5(a/b); I1.2; Table I5.1", ("I5-1a", "I5-1b"), "Encased and filled composite members", "Class/method-specific axial-bending paths; pure biaxial demand without axial force remains pending.", ("F-18", "F-20", "F-33", "F-37")),
    ):
        yield ids, annotation((n,), family, conditions, (citation(provision, "157-178", *eqs),),
            tests=(tests+"test_chapter_i_rules.py", tests+"test_hfs010_coverage.py", tests+"test_hfs017_design_method.py"),
            calculations=(calc+"composite_calc", rules+"composite_rules"), findings=findings,
            selection=composite_selection, method=i_method,
            limitations="Partial LRFD path; no full independent composite oracle or normative accreditation. F-34/38 remain visible where applicable.")
    yield from pending_groups()


def pending_groups():
    """Known absent/externally assessed domains, explicitly not executable predicates."""
    for rid, n, provision, pages, family, reason, state, findings in (
        ("F9", "N19", "F9.1-4", "133-136", "Tees/double angles", "F9 blocked in router; no implemented flexural rule.", "NOT_IMPLEMENTED", ("F-23", "F-30")),
        ("I2", "N37", "I2", "163-168", "Legacy placeholder", "Unreferenced legacy registry slot; actual composite implementations have distinct descriptive IDs. Not a missing entire Chapter I2.", "NOT_IMPLEMENTED", ("F-26",)),
        ("scope.N01", "N01", "B1-B3.3; A3", "83-87", "All families", "External demands/combinations and material provenance; input validation is not analysis validation.", "EXTERNAL", ("F-22",)),
        ("scope.N02", "N02", "B4.1-B4.3", "87-93", "Compressed elements, net areas and HSS", "Classification exists in specific owners; manufacture/dimensions/net-area provenance and all table cases remain unaccredited.", "EXTERNAL", ("F-03", "F-12", "F-27")),
        ("scope.N03", "N03", "C1-C3; E2; F1", "94-99", "All families with stability/restraint requirements", "K/L/Cb inputs do not validate global analysis, second-order effects or bracing.", "EXTERNAL", ("F-22",)),
        ("scope.N05", "N05", "D4", "103-104", "Built-up tension members", "Connection/detailing of components not implemented by summing areas.", "NOT_IMPLEMENTED", ("F-38",)),
        ("scope.N09", "N09", "E6.1/2", "112-114", "Built-up compression members", "Modified slenderness, connectors and component slip not implemented.", "NOT_IMPLEMENTED", ("F-38",)),
        ("scope.N11", "N11", "F1(a)-(d)", "118-119", "Flexural members", "External loading plane, restraint, Cb and support conditions are not verified by a selector.", "EXTERNAL", ("F-22", "F-38")),
        ("scope.N22", "N22", "F13.1-4", "140-142", "Members with holes/proportion/built-up requirements", "Supplementary flange/web/detail checks absent; unknown conditions are not N/A.", "NOT_IMPLEMENTED", ("F-38",)),
        ("scope.N28", "N28", "G7", "149", "Steel/composite beams with web openings", "No opening geometry or independent opening-strength analysis.", "NOT_IMPLEMENTED", ("F-38",)),
        ("scope.N31", "N31", "H3.3", "154-155", "Non-HSS torsion/combined stresses", "No warping/combined-stress resistance; independent checks can survive, coverage remains pending.", "NOT_IMPLEMENTED", ("F-30",)),
        ("scope.N32", "N32", "H4; D2(b); F13.1", "155-156", "Flanges with holes under combined demand", "No H4 net-flange rupture check.", "NOT_IMPLEMENTED", ("F-38",)),
        ("scope.N33", "N33", "D1; E2", "100,106", "Ordinary steel members", "Slenderness recommendations are advisory, not resistance; E5 conditions remain separate.", "ADVISORY", ("F-07", "F-36")),
        ("scope.N34", "N34", "D5/D6; F12", "104-105,140", "Pins/eyebars/asymmetric sections", "Special domains outside supported ordinary member design.", "NOT_IMPLEMENTED", ("F-30",)),
        ("scope.N35", "N35", "B3.4-13; B5-B8 and external referrals", "84-93", "Connections, service, fatigue, fire and fabrication", "External/unstudied requirements remain explicit; no whole-building certification.", "EXTERNAL", ("F-30", "F-38")),
        ("scope.N44", "N44", "I2.1d/2d; I6; I8", "163-168,177-182", "Composite force introduction/anchors", "Beam anchor candidates exist; no complete column force-introduction I6 check.", "NOT_IMPLEMENTED", ("F-38",)),
        ("scope.N45", "N45", "I1.6; I2.3; I3.5; I4.4; I5(c); I7", "157-182", "Special composite/seismic/high-strength domains", "Outside current support; AISC 341 and full Appendix 2 are not implemented here.", "NOT_IMPLEMENTED", ("F-30", "F-38")),
        ("F.CHANNEL.MAJOR.OUTSIDE_F2", "N12", "F2 applicability boundary; F1", "118-121", "Channel major axis outside compact F2", "No justified major-axis alternative; minor F6 cannot satisfy it. F-31 remains P0 open.", "NOT_IMPLEMENTED", ("F-31",)),
        ("H.INTERACTION.REMAINDER", "N29", "H1/H2", "150-153", "Non-HSS axial-bending / biaxial bending without axial force", "HSS-only implementation does not cover other families, H2 or all zero-axial biaxial paths.", "NOT_IMPLEMENTED", ("F-01", "F-33", "F-37")),
        ("I3.MOMENT.ENCASED", "N39", "I3.3b", "173", "Encased member pure flexure", "Internal I5 steel-only capacity exists; standalone moment check is absent. Ratio check does not substitute it.", "NOT_IMPLEMENTED", ("F-34",)),
        ("I3.MOMENT.FILLED", "N40", "I3.4b", "173-174", "Filled member pure flexure", "Internal I5 flexural capacity exists; standalone moment check is absent.", "NOT_IMPLEMENTED", ("F-34",)),
        ("I3.MOMENT.BEAM", "N43", "I3.1/2", "168-173", "Composite beam pure flexure and construction stages", "Transfer checks are not a moment-resistance check.", "NOT_IMPLEMENTED", ("F-34", "F-38")),
    ):
        # A cross-chapter referral is a separate citation, not a page claim
        # under the first chapter's locator. Unlocalized A3 stays explicit.
        refs = {
            "N01": (citation("B1-B3.3", "83-87"), citation("A3", "Locator pending; see HFS-002 N01")),
            "N03": (citation("C1-C3", "94-99"), citation("E2", "106-117"), citation("F1", "118-120")),
            "N32": (citation("H4", "155-156", "H4-1"), citation("D2(b)", "100-101"), citation("F13.1", "140-142")),
            "N33": (citation("D1", "100"), citation("E2", "106-117"),
                    citation("D1 User Note", "100", source="UN22"), citation("E2 User Note", "108", source="UN22")),
            "N34": (citation("D5/D6", "104-105"), citation("F12", "140", "F12-1 to F12-4")),
        }.get(n, (citation(provision, pages),))
        regression = {
            "F.CHANNEL.MAJOR.OUTSIDE_F2": "test_hfs012_flexure_selection.py::test_channel_outside_f2_never_uses_i_shape_alternatives",
            "H.INTERACTION.REMAINDER": "test_hfs010_coverage.py::test_f01_f33_interaction_required_independently_of_router",
            "I3.MOMENT.ENCASED": "test_hfs010_coverage.py::test_f34_ratio_or_transfer_is_not_moment_resistance",
            "I3.MOMENT.FILLED": "test_hfs010_coverage.py::test_f34_ratio_or_transfer_is_not_moment_resistance",
            "I3.MOMENT.BEAM": "test_hfs010_coverage.py::test_f34_ratio_or_transfer_is_not_moment_resistance",
            "scope.N31": "test_hfs013_directional_h3.py::test_unsupported_non_hss_torsion_does_not_erase_independent_shear",
            "scope.N02": "test_hfs012_flexure_selection.py::test_unknown_ratio_never_selects_f2_and_keeps_coverage_pending",
        }.get(rid)
        helpers = {
            "scope.N02": ("steel_design.codes.aisc_360_22.axial_calc:classify_compression_elements",),
            "scope.N33": ("steel_design.domain.recommendations:slenderness_recommendations",),
            "scope.N44": ("steel_design.domain.rules.composite_rules:_sum_anchor_qn",),
            "I3.MOMENT.ENCASED": ("steel_design.domain.rules.composite_rules:_encased_steel_only_flexural_capacity_axis",),
            "I3.MOMENT.FILLED": ("steel_design.domain.rules.composite_rules:_filled_flexural_capacity_i3_axis",),
        }.get(rid, ())
        yield (rid,), annotation((n,), family, reason, refs, tests=("tests/"+regression,) if regression else (),
            calculations=helpers, findings=findings, state=state,
            limitations=reason,
            selection="steel_design.domain.recommendations:slenderness_recommendations" if n == "N33" else "steel_design.domain.coverage:build_coverage_plan",
            equation_note="No executable equation is claimed for this descriptive gap/external condition; see cited section and independent matrix.")


def attach_metadata(definitions):
    """Return the same definitions enriched; never infer a missing annotation."""
    annotations = {}
    for ids, metadata in metadata_groups():
        for rule_id in ids:
            if rule_id in annotations:
                raise ValueError(f"Duplicate metadata ID: {rule_id}")
            annotations[rule_id] = metadata
    if set(definitions) != set(annotations):
        raise ValueError(f"Incomplete registry metadata: {set(definitions) ^ set(annotations)}")
    return {key: replace(definition, metadata=annotations[key]) for key, definition in definitions.items()}


def validate_registry(definitions, profiles):
    """Pure integrity checks, no case evaluation, imports-by-name or file access."""
    seen = set()
    for definition in definitions:
        key = definition.rule_id
        if not key or not key.strip() or key != key.strip() or key in seen:
            raise ValueError(f"Duplicate/empty rule ID: {key}")
        seen.add(key)
        if definition.metadata is None:
            raise ValueError(f"{key}: missing metadata")
        RuleMetadata.model_validate(definition.metadata.model_dump())
        if definition.implemented != (definition.rule_class is not None):
            raise ValueError(f"{key}: implementation flag/class conflict")
        if definition.rule_class is not None and not callable(getattr(definition.rule_class, "check", None)):
            raise ValueError(f"{key}: implementation has no check")
        if definition.implemented and definition.metadata.implementation_state not in {"PARTIAL", "BLOCKED"}:
            raise ValueError(f"{key}: metadata conflicts with existing implementation")
        if not definition.implemented and definition.metadata.implementation_state in {"PARTIAL", "BLOCKED"}:
            raise ValueError(f"{key}: metadata claims missing implementation")
        if definition.applicability is not None and not callable(definition.applicability):
            raise ValueError(f"{key}: invalid predicate owner")
        if any(key in ids for ids in profiles.values()) and definition.applicability is None:
            raise ValueError(f"{key}: descriptive record cannot be routed")
    for family, ids in profiles.items():
        if not set(ids) <= seen:
            raise ValueError(f"{family}: unknown routed ID")
