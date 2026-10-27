from enum import Enum
import math
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, StrictBool, computed_field, field_serializer, model_serializer, model_validator

from .input_contracts import (InputModel, FiniteNumber, PositiveNumber,
                              NonNegativeNumber, UnitFactor, PositiveCount, NonBlankString)

from .design_methods import DesignMethod

class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"

class Material(InputModel):
    Fy: PositiveNumber = Field(..., description="Yield strength (MPa)")
    Fu: PositiveNumber = Field(..., description="Ultimate tensile strength (MPa)")
    E: PositiveNumber = Field(200000.0, description="Elastic modulus (MPa)")

    @model_validator(mode="after")
    def validate_strength_order(self):
        if self.Fu < self.Fy:
            raise ValueError("material.Fu must be >= material.Fy (MPa).")
        return self

class Loads(InputModel):
    Pu: FiniteNumber = Field(0.0, description="Required axial strength (kN). Positive is compression.")
    Mux: FiniteNumber = Field(0.0, description="Required flexural strength, major-axis (kN-m)")
    Muy: FiniteNumber = Field(0.0, description="Required flexural strength, minor-axis (kN-m)")
    Tu: FiniteNumber = Field(0.0, description="Required torsional strength (kN-m)")
    Vux: FiniteNumber = Field(0.0, description="Shear associated with major-axis Mux, force along local y (kN); suffix names bending plane")
    Vuy: FiniteNumber = Field(0.0, description="Shear associated with minor-axis Muy, force along local x (kN); suffix names bending plane")
    Vu: FiniteNumber = Field(0.0, description="Legacy scalar alias of Vux (local-y force, kN), never a vector resultant")

    @model_validator(mode="after")
    def validate_load_representation(self):
        if not self.model_fields_set:
            raise ValueError("loads must declare at least one component; use an explicit zero for a zero-demand case.")
        if self.Vu != 0.0 and (self.Vux != 0.0 or self.Vuy != 0.0):
            raise ValueError("loads.Vu cannot be nonzero with loads.Vux/Vuy nonzero; choose legacy Vu or directional components. No resultant or axis transformation is inferred.")
        return self

class Lengths(InputModel):
    Lx: PositiveNumber = Field(..., description="Unbraced length for strong axis buckling (mm)")
    Ly: PositiveNumber = Field(..., description="Unbraced length for weak axis buckling (mm)")
    Lz: PositiveNumber = Field(..., description="Unbraced length for torsional/flexural-torsional buckling (mm)")
    Lb: PositiveNumber = Field(..., description="Unbraced length for lateral-torsional buckling (mm)")

class AngleCompressionMode(str, Enum):
    ONE_LEG = "one_leg"
    BOTH_LEGS = "both_legs"


class AngleFlexureAxis(str, Enum):
    MAJOR_PRINCIPAL = "major_principal"
    GEOMETRIC_AXIS = "geometric_axis"


class AngleLtbRestraint(str, Enum):
    CONTINUOUS = "continuous"
    DISCRETE_UNBRACED = "discrete_unbraced"
    MAX_MOMENT_ONLY = "max_moment_only"


class AngleMaxTensionLocation(str, Enum):
    TOE = "toe"
    HEEL = "heel"


class CustomSectionType(str, Enum):
    SOLID_CIRCULAR = "SOLID_CIRCULAR"
    SOLID_RECTANGULAR = "SOLID_RECTANGULAR"


class CustomSection(InputModel):
    type: CustomSectionType
    diameter: Optional[PositiveNumber] = Field(None, description="Diameter for solid circular section (mm)")
    H: Optional[PositiveNumber] = Field(None, description="Height for solid rectangular section (mm)")
    B: Optional[PositiveNumber] = Field(None, description="Width for solid rectangular section (mm)")

    @model_validator(mode="after")
    def validate_dimensions(self):
        if self.type == CustomSectionType.SOLID_CIRCULAR:
            if self.diameter is None:
                raise ValueError("custom_section.diameter must be > 0 for SOLID_CIRCULAR.")
            if self.H is not None or self.B is not None:
                raise ValueError("custom_section.H and custom_section.B are only valid for SOLID_RECTANGULAR.")
            return self

        if self.H is None or self.B is None:
            raise ValueError("custom_section.H and custom_section.B must be > 0 for SOLID_RECTANGULAR.")
        if self.diameter is not None:
            raise ValueError("custom_section.diameter is only valid for SOLID_CIRCULAR.")
        return self


class CompositeRole(str, Enum):
    ENCASED_MEMBER = "ENCASED_MEMBER"
    FILLED_MEMBER = "FILLED_MEMBER"
    COMPOSITE_BEAM = "COMPOSITE_BEAM"


class CompositeNominalStrengthMethod(str, Enum):
    PLASTIC = "PLASTIC"
    STRAIN_COMPAT = "STRAIN_COMPAT"
    ELASTIC = "ELASTIC"
    EFFECTIVE_STRAIN = "EFFECTIVE_STRAIN"


class CompositeI5Method(str, Enum):
    METHOD_1_H1_1 = "METHOD_1_H1_1"
    METHOD_2_PLASTIC_INTERACTION = "METHOD_2_PLASTIC_INTERACTION"
    METHOD_4_DIRECT_INTERACTION = "METHOD_4_DIRECT_INTERACTION"


class CompositeConcrete(InputModel):
    fc: PositiveNumber = Field(..., description="Specified compressive strength of concrete (MPa)")
    wc: PositiveNumber = Field(..., description="Concrete unit weight (kg/m3)")

class CompositeLongitudinalBar(InputModel):
    count: PositiveCount = Field(..., description="Number of bars at this coordinate")
    db: PositiveNumber = Field(..., description="Bar diameter (mm)")
    fy: PositiveNumber = Field(..., description="Bar yield stress (MPa)")
    x: FiniteNumber = Field(..., description="Bar x coordinate from composite centroid (mm)")
    y: FiniteNumber = Field(..., description="Bar y coordinate from composite centroid (mm)")

class CompositeTransverseReinforcement(InputModel):
    db: PositiveNumber = Field(..., description="Transverse bar diameter (mm)")
    spacing: PositiveNumber = Field(..., description="Spacing (mm)")
    fy: PositiveNumber = Field(..., description="Yield stress (MPa)")
    type: Literal["ties", "hoops", "spirals", "stirrups"] = Field(..., description="Transverse reinforcement type (ties/hoops/spirals/stirrups)")

class CompositeReinforcement(InputModel):
    longitudinal_bars: List[CompositeLongitudinalBar] = Field(
        default_factory=list,
        description="Longitudinal reinforcement layout.",
    )
    transverse: Optional[CompositeTransverseReinforcement] = Field(
        None,
        description="Minimum transverse reinforcement definition.",
    )


class CompositeGeometry(InputModel):
    B: Optional[PositiveNumber] = Field(None, description="Overall composite width for encased members (mm)")
    H: Optional[PositiveNumber] = Field(None, description="Overall composite depth for encased members (mm)")
    cover: Optional[PositiveNumber] = Field(None, description="Concrete cover to reinforcement (mm)")
    slab_effective_width: Optional[PositiveNumber] = Field(None, description="Effective slab width for composite beam (mm)")
    slab_thickness: Optional[PositiveNumber] = Field(None, description="Slab thickness for composite beam (mm)")
    deck_present: Optional[StrictBool] = Field(None, description="Whether formed steel deck is present.")


class CompositeAnchorType(str, Enum):
    STUD = "STUD"
    CHANNEL = "CHANNEL"


class CompositeAnchorSegment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class CompositeAnchorGroup(InputModel):
    type: CompositeAnchorType
    count: PositiveCount = Field(..., description="Number of anchors in this group")
    segment: CompositeAnchorSegment = Field(
        CompositeAnchorSegment.POSITIVE,
        description="Span segment associated with this anchor group.",
    )
    d: Optional[PositiveNumber] = Field(None, description="Stud shank diameter (mm)")
    Fu: Optional[PositiveNumber] = Field(None, description="Stud ultimate tensile strength (MPa)")
    Rg: Optional[UnitFactor] = Field(None, description="Deck geometry reduction factor for stud anchors")
    Rp: Optional[UnitFactor] = Field(None, description="Deck position reduction factor for stud anchors")
    la: Optional[PositiveNumber] = Field(None, description="Channel anchor length (mm)")
    tf: Optional[PositiveNumber] = Field(None, description="Channel flange thickness (mm)")
    tw: Optional[PositiveNumber] = Field(None, description="Channel web thickness (mm)")

    @model_validator(mode="after")
    def validate_anchor_group(self):
        required = ("d", "Fu", "Rg", "Rp") if self.type == CompositeAnchorType.STUD else ("la", "tf", "tw")
        forbidden = ("la", "tf", "tw") if self.type == CompositeAnchorType.STUD else ("d", "Fu", "Rg", "Rp")
        for name in required:
            if getattr(self, name) is None:
                raise ValueError(f"composite.anchors.groups.{name} is required for {self.type.value}; no material/factor is inferred.")
        for name in forbidden:
            if getattr(self, name) is not None:
                raise ValueError(f"composite.anchors.groups.{name} is not applicable to {self.type.value}.")
        return self


class CompositeAnchors(InputModel):
    groups: List[CompositeAnchorGroup] = Field(default_factory=list)


class CompositeI5Config(InputModel):
    method: CompositeI5Method = Field(
        CompositeI5Method.METHOD_1_H1_1,
        description="Commentary I5 method selector.",
    )
    method2_pc_ratio: Optional[PositiveNumber] = Field(
        None, lt=1,
        description="Optional P_C/P_A ratio for Method 2 when not inferred (0 < ratio < 1).",
    )
    method2_mc_ratio: Optional[PositiveNumber] = Field(
        None,
        description="Optional M_C/M_B ratio for Method 2 when not inferred (0 < ratio).",
    )

    @model_validator(mode="after")
    def validate_i5_config(self):
        if self.method != CompositeI5Method.METHOD_2_PLASTIC_INTERACTION and (
            self.method2_pc_ratio is not None or self.method2_mc_ratio is not None
        ):
            raise ValueError("composite.i5.method2_pc_ratio/method2_mc_ratio require METHOD_2_PLASTIC_INTERACTION.")
        return self


class CompositeConfig(InputModel):
    role: CompositeRole
    nominal_strength_method: CompositeNominalStrengthMethod
    concrete: CompositeConcrete
    reinforcement: CompositeReinforcement = Field(default_factory=CompositeReinforcement)
    geometry: CompositeGeometry = Field(default_factory=CompositeGeometry)
    anchors: CompositeAnchors = Field(default_factory=CompositeAnchors)
    i5: CompositeI5Config = Field(default_factory=CompositeI5Config)


class Connection(InputModel):
    An: Optional[PositiveNumber] = Field(None, description="Net area for tension rupture (mm^2)")
    U: Optional[UnitFactor] = Field(None, description="Shear lag factor for tension rupture (0 < U <= 1)")
    angle_compression_mode: Optional[AngleCompressionMode] = Field(
        None,
        description="Connection mode for single-angle compression (E5).",
    )
    angle_flexure_axis: Optional[AngleFlexureAxis] = Field(
        None,
        description="Single-angle flexure axis definition for F10.",
    )
    angle_ltb_restraint: Optional[AngleLtbRestraint] = Field(
        None,
        description="Lateral-torsional restraint condition for F10.",
    )
    angle_max_tension_location: Optional[AngleMaxTensionLocation] = Field(
        None,
        description="Location of maximum tension for geometric-axis bending in F10.",
    )

class Factors(InputModel):
    Kx: PositiveNumber = Field(1.0, description="Effective length factor for strong axis")
    Ky: PositiveNumber = Field(1.0, description="Effective length factor for weak axis")
    Kz: PositiveNumber = Field(1.0, description="Effective length factor for torsional/flexural-torsional buckling axis")
    Cb: PositiveNumber = Field(1.0, description="Lateral-torsional buckling modification factor")
    xa: NonNegativeNumber = Field(0.0, description="Bracing offset distance along x-axis (mm)")
    ya: NonNegativeNumber = Field(0.0, description="Bracing offset distance along y-axis (mm)")

class TensionScope(InputModel):
    """External basis for the narrow ordinary solid-tie scope (HFS-010).

    None is unknown. References are supplied evidence, not authenticated here.
    """
    ordinary_prismatic_member: Optional[StrictBool] = None
    concentric_axial_force: Optional[StrictBool] = None
    no_special_conditions: Optional[StrictBool] = None
    material_reference: Optional[NonBlankString] = None
    demand_reference: Optional[NonBlankString] = None
    net_area_reference: Optional[NonBlankString] = None
    connection_reference: Optional[NonBlankString] = None
    external_checks_reference: Optional[NonBlankString] = None


class SlendernessAdviceBasis(InputModel):
    """Optional external facts for User Notes, never resistance/coverage inputs."""
    fabricated_length: Optional[PositiveNumber] = Field(None, description="Fabricated member length (mm), not unbraced length")
    least_radius: Optional[PositiveNumber] = Field(None, description="Least section radius of gyration (mm), including principal axes")
    is_rod: Optional[StrictBool] = Field(None, description="Whether the D1 rod exception applies; absent means unknown")


class SteelCase(InputModel):
    section_name: NonBlankString
    material: Material
    loads: Loads
    lengths: Lengths
    factors: Factors = Field(default_factory=Factors)
    connection: Connection = Field(default_factory=Connection)
    custom_section: Optional[CustomSection] = Field(
        None,
        description="Optional custom solid section defined directly in input.",
    )
    composite: Optional[CompositeConfig] = Field(
        None,
        description="Optional Chapter I composite member configuration.",
    )
    design_method: DesignMethod = DesignMethod.LRFD
    slenderness_advice_basis: Optional[SlendernessAdviceBasis] = None
    tension_scope: Optional[TensionScope] = Field(
        None, description="Applicability evidence for ordinary custom solid axial tension; absence means unknown.")

def finite_json_payload(payload: dict) -> dict:
    """JSON-safe projection, preserving the location and kind of every nonfinite.

    Does not mutate calculation values or replace missing resistance by zero.
    Used by CheckResult serialization and by the CLI's complete memory payload.
    """
    diagnostics = []

    def project(value, path):
        if isinstance(value, float) and not math.isfinite(value):
            diagnostics.append({"path": path, "kind": "NaN" if math.isnan(value) else
                                "Infinity" if value > 0 else "-Infinity"})
            return None
        if isinstance(value, dict):
            return {k: project(v, f"{path}/{k}") for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [project(v, f"{path}/{i}") for i, v in enumerate(value)]
        return value

    result = project(payload, "")
    if diagnostics:
        result["nonfinite_values"] = result.get("nonfinite_values", []) + diagnostics
    return result


class CheckResult(BaseModel):
    name: str = Field(..., description="Name of the check (e.g., Flexure Major F2)")
    code: str = Field("AISC 360-22", description="Reference code")
    clause: str = Field(..., description="Code clause (e.g., F2-1)")
    demand: float = Field(..., description="Original unrounded required strength")
    capacity: float = Field(..., description="Original unrounded available strength (phi*Rn or Rn/Omega)")
    dcr: float = Field(..., description="Original unrounded ratio used for the decision; not a display value")
    unit: Optional[Literal["kN", "kN-m", "ratio"]] = None
    numeric_issue: Optional[str] = None
    status: CheckStatus = Field(..., description="PASS or FAIL status")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured rule details (e.g., element classification).",
    )

    @classmethod
    def from_values(cls, *, name, clause, demand, capacity, unit, details=None):
        """Canonical result decision; capacities/equations remain in their rules."""
        usable = math.isfinite(demand) and math.isfinite(capacity) and demand >= 0 and capacity > 0
        dcr = demand / capacity if usable else math.inf
        return cls(name=name, clause=clause, demand=demand, capacity=capacity, dcr=dcr,
                   unit=unit, details=details,
                   status=CheckStatus.PASS if math.isfinite(dcr) and dcr <= 1.0 else CheckStatus.FAIL,
                   numeric_issue=None if usable and math.isfinite(dcr) else "UNDEFINED_OR_NONFINITE_RATIO")

    @model_validator(mode="after")
    def reject_undefined_pass(self):
        if (not all(math.isfinite(v) for v in (self.demand, self.capacity, self.dcr))
                or (self.demand != 0 and self.capacity <= 0)):
            self.status = CheckStatus.FAIL
            self.numeric_issue = self.numeric_issue or "UNDEFINED_OR_NONFINITE_RATIO"
        return self

    @computed_field
    @property
    def display(self) -> dict:
        def formatted(value):
            return f"{value:.3f}" if math.isfinite(value) else "undefined"
        return {"demand": formatted(self.demand), "capacity": formatted(self.capacity),
                "dcr": formatted(self.dcr),
                "dcr_label": f"{formatted(self.dcr)} ({self.status.value}; raw={self.dcr!r})"}

    @model_serializer(mode="wrap")
    def serialize_numbers(self, handler):
        return finite_json_payload(handler(self))

    @field_serializer("details")
    def serialize_details(self, value):
        # Project before Pydantic's Any serializer can turn infinity into null
        # without its path/type diagnostic in JSON mode.
        return finite_json_payload(value) if value is not None else None
