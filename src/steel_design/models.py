from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

class DesignMethod(str, Enum):
    LRFD = "LRFD"
    ASD = "ASD"

class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"

class Material(BaseModel):
    Fy: float = Field(..., description="Yield strength (MPa)")
    Fu: float = Field(..., description="Ultimate tensile strength (MPa)")
    E: float = Field(200000.0, description="Elastic modulus (MPa)")

class Loads(BaseModel):
    Pu: float = Field(0.0, description="Required axial strength (kN). Positive is compression.")
    Mux: float = Field(0.0, description="Required flexural strength, major-axis (kN-m)")
    Muy: float = Field(0.0, description="Required flexural strength, minor-axis (kN-m)")
    Tu: float = Field(0.0, description="Required torsional strength (kN-m)")
    Vux: float = Field(0.0, description="Required shear strength about x direction (kN)")
    Vuy: float = Field(0.0, description="Required shear strength about y direction (kN)")
    Vu: float = Field(0.0, description="Legacy resultant shear strength (kN)")

    @model_validator(mode="after")
    def normalize_shear(self):
        if abs(self.Vux) > 0.0 or abs(self.Vuy) > 0.0:
            self.Vu = (self.Vux**2 + self.Vuy**2) ** 0.5
        return self

class Lengths(BaseModel):
    Lx: float = Field(..., description="Unbraced length for strong axis buckling (mm)")
    Ly: float = Field(..., description="Unbraced length for weak axis buckling (mm)")
    Lz: float = Field(..., description="Unbraced length for torsional/flexural-torsional buckling (mm)")
    Lb: float = Field(..., description="Unbraced length for lateral-torsional buckling (mm)")

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


class CustomSection(BaseModel):
    type: CustomSectionType
    diameter: Optional[float] = Field(None, description="Diameter for solid circular section (mm)")
    H: Optional[float] = Field(None, description="Height for solid rectangular section (mm)")
    B: Optional[float] = Field(None, description="Width for solid rectangular section (mm)")

    @model_validator(mode="after")
    def validate_dimensions(self):
        if self.type == CustomSectionType.SOLID_CIRCULAR:
            if self.diameter is None or self.diameter <= 0.0:
                raise ValueError("custom_section.diameter must be > 0 for SOLID_CIRCULAR.")
            if self.H is not None or self.B is not None:
                raise ValueError("custom_section.H and custom_section.B are only valid for SOLID_RECTANGULAR.")
            return self

        if self.H is None or self.H <= 0.0 or self.B is None or self.B <= 0.0:
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


class CompositeConcrete(BaseModel):
    fc: float = Field(..., description="Specified compressive strength of concrete (MPa)")
    wc: float = Field(..., description="Concrete unit weight (kg/m3)")

    @model_validator(mode="after")
    def validate_concrete_values(self):
        if self.fc <= 0.0:
            raise ValueError("composite.concrete.fc must be > 0.")
        if self.wc <= 0.0:
            raise ValueError("composite.concrete.wc must be > 0.")
        return self


class CompositeLongitudinalBar(BaseModel):
    count: int = Field(..., description="Number of bars at this coordinate")
    db: float = Field(..., description="Bar diameter (mm)")
    fy: float = Field(..., description="Bar yield stress (MPa)")
    x: float = Field(..., description="Bar x coordinate from composite centroid (mm)")
    y: float = Field(..., description="Bar y coordinate from composite centroid (mm)")

    @model_validator(mode="after")
    def validate_longitudinal_bar(self):
        if self.count <= 0:
            raise ValueError("composite.reinforcement.longitudinal_bars.count must be >= 1.")
        if self.db <= 0.0:
            raise ValueError("composite.reinforcement.longitudinal_bars.db must be > 0.")
        if self.fy <= 0.0:
            raise ValueError("composite.reinforcement.longitudinal_bars.fy must be > 0.")
        return self


class CompositeTransverseReinforcement(BaseModel):
    db: float = Field(..., description="Transverse bar diameter (mm)")
    spacing: float = Field(..., description="Spacing (mm)")
    fy: float = Field(..., description="Yield stress (MPa)")
    type: str = Field(..., description="Transverse reinforcement type (ties/hoops/spirals/stirrups)")

    @model_validator(mode="after")
    def validate_transverse(self):
        if self.db <= 0.0:
            raise ValueError("composite.reinforcement.transverse.db must be > 0.")
        if self.spacing <= 0.0:
            raise ValueError("composite.reinforcement.transverse.spacing must be > 0.")
        if self.fy <= 0.0:
            raise ValueError("composite.reinforcement.transverse.fy must be > 0.")
        if not self.type or not self.type.strip():
            raise ValueError("composite.reinforcement.transverse.type is required.")
        return self


class CompositeReinforcement(BaseModel):
    longitudinal_bars: List[CompositeLongitudinalBar] = Field(
        default_factory=list,
        description="Longitudinal reinforcement layout.",
    )
    transverse: Optional[CompositeTransverseReinforcement] = Field(
        None,
        description="Minimum transverse reinforcement definition.",
    )


class CompositeGeometry(BaseModel):
    B: Optional[float] = Field(None, description="Overall composite width for encased members (mm)")
    H: Optional[float] = Field(None, description="Overall composite depth for encased members (mm)")
    cover: Optional[float] = Field(None, description="Concrete cover to reinforcement (mm)")
    slab_effective_width: Optional[float] = Field(None, description="Effective slab width for composite beam (mm)")
    slab_thickness: Optional[float] = Field(None, description="Slab thickness for composite beam (mm)")
    deck_present: Optional[bool] = Field(None, description="Whether formed steel deck is present.")


class CompositeAnchorType(str, Enum):
    STUD = "STUD"
    CHANNEL = "CHANNEL"


class CompositeAnchorSegment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class CompositeAnchorGroup(BaseModel):
    type: CompositeAnchorType
    count: int = Field(..., description="Number of anchors in this group")
    segment: CompositeAnchorSegment = Field(
        CompositeAnchorSegment.POSITIVE,
        description="Span segment associated with this anchor group.",
    )
    d: Optional[float] = Field(None, description="Stud shank diameter (mm)")
    Fu: Optional[float] = Field(None, description="Stud ultimate tensile strength (MPa)")
    Rg: Optional[float] = Field(1.0, description="Deck geometry reduction factor for stud anchors")
    Rp: Optional[float] = Field(0.75, description="Deck position reduction factor for stud anchors")
    la: Optional[float] = Field(None, description="Channel anchor length (mm)")
    tf: Optional[float] = Field(None, description="Channel flange thickness (mm)")
    tw: Optional[float] = Field(None, description="Channel web thickness (mm)")

    @model_validator(mode="after")
    def validate_anchor_group(self):
        if self.count <= 0:
            raise ValueError("composite.anchors.groups.count must be >= 1.")
        if self.type == CompositeAnchorType.STUD:
            if self.d is None or self.d <= 0.0:
                raise ValueError("composite.anchors.groups.d must be > 0 for STUD anchors.")
            if self.Fu is not None and self.Fu <= 0.0:
                raise ValueError("composite.anchors.groups.Fu must be > 0 when provided.")
            if self.Rg is not None and self.Rg <= 0.0:
                raise ValueError("composite.anchors.groups.Rg must be > 0 when provided.")
            if self.Rp is not None and self.Rp <= 0.0:
                raise ValueError("composite.anchors.groups.Rp must be > 0 when provided.")
            return self

        if self.la is None or self.la <= 0.0:
            raise ValueError("composite.anchors.groups.la must be > 0 for CHANNEL anchors.")
        if self.tf is None or self.tf <= 0.0:
            raise ValueError("composite.anchors.groups.tf must be > 0 for CHANNEL anchors.")
        if self.tw is None or self.tw <= 0.0:
            raise ValueError("composite.anchors.groups.tw must be > 0 for CHANNEL anchors.")
        return self


class CompositeAnchors(BaseModel):
    groups: List[CompositeAnchorGroup] = Field(default_factory=list)


class CompositeConfig(BaseModel):
    role: CompositeRole
    nominal_strength_method: CompositeNominalStrengthMethod
    concrete: CompositeConcrete
    reinforcement: CompositeReinforcement = Field(default_factory=CompositeReinforcement)
    geometry: CompositeGeometry = Field(default_factory=CompositeGeometry)
    anchors: CompositeAnchors = Field(default_factory=CompositeAnchors)


class Connection(BaseModel):
    An: Optional[float] = Field(None, description="Net area for tension rupture (mm^2)")
    U: Optional[float] = Field(None, description="Shear lag factor for tension rupture (0 < U <= 1)")
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

class Factors(BaseModel):
    Kx: float = Field(1.0, description="Effective length factor for strong axis")
    Ky: float = Field(1.0, description="Effective length factor for weak axis")
    Kz: float = Field(1.0, description="Effective length factor for torsional/flexural-torsional buckling axis")
    Cb: float = Field(1.0, description="Lateral-torsional buckling modification factor")
    xa: float = Field(0.0, description="Bracing offset distance along x-axis (mm)")
    ya: float = Field(0.0, description="Bracing offset distance along y-axis (mm)")

class SteelCase(BaseModel):
    section_name: str
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

class CheckResult(BaseModel):
    name: str = Field(..., description="Name of the check (e.g., Flexure Major F2)")
    code: str = Field("AISC 360-22", description="Reference code")
    clause: str = Field(..., description="Code clause (e.g., F2-1)")
    demand: float = Field(..., description="Required strength")
    capacity: float = Field(..., description="Available strength (phi*Rn or Rn/Omega)")
    dcr: float = Field(..., description="Demand to capacity ratio")
    status: CheckStatus = Field(..., description="PASS or FAIL status")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured rule details (e.g., element classification).",
    )
