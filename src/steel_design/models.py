"""Input and result models (ANSI/AISC 360-22 Chapters D, E and F, LRFD). Units: N, mm, MPa, kN, kN*m."""
from enum import Enum
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, computed_field, model_validator


# JSON numbers only: bool and numeric strings are not engineering magnitudes.
FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]
PositiveNumber = Annotated[FiniteNumber, Field(gt=0)]
NonNegativeNumber = Annotated[FiniteNumber, Field(ge=0)]
PositiveCount = Annotated[int, Field(strict=True, gt=0)]
NonBlankString = Annotated[str, Field(strict=True, pattern=r"\S")]


class InputModel(BaseModel):
    """One policy for cases, nested objects and normalized section records.

    Revalidation prevents model_copy/model_construct or later mutations from
    bypassing the engine boundary. These Pydantic escape hatches are not trusted
    input APIs. Output models deliberately do not inherit this policy.
    """

    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, validate_default=True,
        revalidate_instances="always",
    )


def unique_json_object(pairs):
    """Reject duplicate keys before a JSON decoder loses the first value.

    Used by the CLI when reading JSON input.
    """
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Campo JSON duplicado {key!r}; indique un único valor por campo.")
        result[key] = value
    return result


class Material(InputModel):
    Fy: PositiveNumber = Field(..., description="Specified minimum yield stress (MPa)")
    Fu: Optional[PositiveNumber] = Field(None, description="Specified minimum tensile strength (MPa); required for tension (D2-2)")
    E: PositiveNumber = Field(200000.0, description="Modulus of elasticity (MPa); Chapter E defines 200000")

    @model_validator(mode="after")
    def fu_not_below_fy(self):
        if self.Fu is not None and self.Fu < self.Fy:
            raise ValueError("Fu no puede ser menor que Fy.")
        return self


class Lengths(InputModel):
    Lx: PositiveNumber = Field(..., description="Laterally unbraced length for buckling about x (mm)")
    Ly: PositiveNumber = Field(..., description="Laterally unbraced length for buckling about y (mm)")
    Lz: PositiveNumber = Field(..., description="Unbraced length for torsional buckling (mm)")


class Factors(InputModel):
    Kx: PositiveNumber = Field(1.0, description="Effective length factor, x axis (E2)")
    Ky: PositiveNumber = Field(1.0, description="Effective length factor, y axis (E2)")
    Kz: PositiveNumber = Field(1.0, description="Effective length factor, torsion (E4)")
    xa: NonNegativeNumber = Field(0.0, description="Lateral bracing offset from the shear center along x (mm), E4(e)")
    ya: NonNegativeNumber = Field(0.0, description="Lateral bracing offset from the shear center along y (mm), E4(d)")


class SingleAngleE5Basis(InputModel):
    """Facts required by S22 E5; the program cannot infer them from the section."""
    configuration: Literal["a", "b"] = Field(..., description="E5(a) individual/planar-truss member; E5(b) box/space-truss web member")
    connected_leg: Literal["long", "short"] = Field(..., description="Leg through which the load is applied (equal legs: either)")
    L: PositiveNumber = Field(..., description="Member length between work points at truss chord centerlines (mm)")
    loaded_at_ends_through_same_leg: StrictBool = Field(..., description="E5(1)")
    welded_or_two_bolts_min: StrictBool = Field(..., description="E5(2)")
    no_intermediate_transverse_loads: StrictBool = Field(..., description="E5(3)")


class DoubleAngleE6Basis(InputModel):
    """Built-up double angle data required by S22 E6 (supplied by the user)."""
    connectors: Literal["snug_tight", "welded", "pretensioned"] = Field(
        ..., description="Intermediate connectors: snug-tight bolts (E6-1), welded or pretensioned Class A/B bolts (E6-2)")
    a: PositiveNumber = Field(..., description="Distance between intermediate connectors (mm)")
    end_connection_welded_or_pretensioned: StrictBool = Field(
        ..., description="E6.1: end connection welded or with pretensioned bolts, Class A or B faying surfaces")


class TensionBasis(InputModel):
    """Net section data for Chapter D, supplied by the user (not computed by the program)."""
    An: PositiveNumber = Field(..., description="Net area per B4.3b (mm2); An = Ag for members without holes")
    U: PositiveNumber = Field(..., le=1, description="Shear lag factor per Table D3.1 (0 < U <= 1)")
    fabricated_length: Optional[PositiveNumber] = Field(
        None, description="Fabricated member length (mm), only for the D1 User Note L/r <= 300")


class FlexureBasis(InputModel):
    """Member data for Chapter F (supplied by the user)."""
    Lb: Optional[PositiveNumber] = Field(None, description="Unbraced length for lateral-torsional buckling (mm)")
    Cb: PositiveNumber = Field(1.0, description="LTB modification factor (F1); 1.0 when not given (lower bound of F1-1)")
    tension_flange_holes: Optional[StrictBool] = Field(
        None, description="F13.1: bolt holes in the tension flange (I-shapes and channels, major axis); must be declared")
    Afn: Optional[PositiveNumber] = Field(None, description="Net area of the tension flange (mm2), when it has holes")
    lateral_torsional_restraint: Optional[Literal["none", "at_max_moment", "continuous"]] = Field(
        None, description="Single angles (F10): lateral-torsional restraint along the length")
    beta_w: Optional[NonNegativeNumber] = Field(
        None, description="Single angles (F10-4): |beta_w| (mm) of unequal-leg angles; sign from the leg in compression")
    tension_cb_amplification: StrictBool = Field(
        False, description="H1.2: multiply Cb by sqrt(1 + Pr/Pey) when axial tension acts with flexure "
                           "(doubly symmetric members only)")

    @model_validator(mode="after")
    def holes_need_net_area(self):
        if self.tension_flange_holes and self.Afn is None:
            raise ValueError("tension_flange_holes = true requiere Afn.")
        if self.tension_flange_holes is False and self.Afn is not None:
            raise ValueError("Afn solo corresponde a un ala traccionada con agujeros.")
        return self


class ShearBasis(InputModel):
    """Member data for Chapter G (supplied by the user)."""
    Lv: Optional[PositiveNumber] = Field(
        None, description="Round HSS (G5-2a): distance from maximum to zero shear force (mm); "
                          "without it only G5-2b is used (lower bound)")


class AngleFlexure(InputModel):
    """Which part of an angle is in flexural compression (explicit, per load combination)."""
    web_legs: Optional[Literal["tension", "compression"]] = Field(
        None, description="Double angles (F9): legs in the plane of symmetry; 'compression' if compressed anywhere along Lb")
    toe: Optional[Literal["compression", "tension"]] = Field(
        None, description="Single angle, geometric axis: toe of the leg perpendicular to the bending axis; "
                          "principal minor axis (Mz): both toes")
    leg_in_compression: Optional[Literal["long", "short"]] = Field(
        None, description="Single angle, major principal axis (Mw): leg whose toe is in compression")


class Concrete(InputModel):
    fc: PositiveNumber = Field(..., description="Specified compressive strength f'c (MPa)")
    wc: PositiveNumber = Field(..., ge=1500, le=2500, description="Weight of concrete per unit volume (kg/m3), I2.1b")
    lightweight: StrictBool = Field(..., description="Lightweight concrete: f'c limit of I1.3(a); must be declared")


class ReinforcingBar(InputModel):
    area: PositiveNumber = Field(..., description="Bar area (mm2)")
    db: PositiveNumber = Field(..., description="Nominal bar diameter (mm)")
    x: FiniteNumber = Field(..., description="Bar center from the section centroid, along x (mm)")
    y: FiniteNumber = Field(..., description="Bar center from the section centroid, along y (mm)")


class TransverseReinforcement(InputModel):
    db: PositiveNumber = Field(..., description="Tie or hoop bar diameter (mm)")
    spacing: PositiveNumber = Field(..., description="Center-to-center spacing (mm)")


class EncasedBasis(InputModel):
    """Encased W-shape (I2.1, I3.3): concrete outline, bars and the flexural method of I3.3a."""
    H: PositiveNumber = Field(..., description="Concrete depth, parallel to the web of the steel shape (mm)")
    B: PositiveNumber = Field(..., description="Concrete width, parallel to the flanges of the steel shape (mm)")
    Fysr: PositiveNumber = Field(..., description="Specified minimum yield stress of the reinforcing bars (MPa)")
    bars: list[ReinforcingBar] = Field(..., min_length=1, description="Continuous longitudinal bars")
    transverse: TransverseReinforcement
    flexure_method: Literal["steel", "composite"] = Field(
        "steel", description="I3.3a(2) plastic on the steel section, or I3.3a(3) plastic on the composite section")
    anchors_provided: StrictBool = Field(False, description="I3.3a(3): steel anchors provided along the member")


class StudAnchors(InputModel):
    count: PositiveCount = Field(..., description="Studs between the point of maximum moment and the point of zero moment")
    d: PositiveNumber = Field(..., description="Shank diameter dsa (mm)")
    Fu: PositiveNumber = Field(..., description="Specified minimum tensile strength of the stud (MPa)")
    length: PositiveNumber = Field(..., description="Length after installation, base to top of the head (mm)")
    per_rib: PositiveCount = Field(1, description="Studs in one deck rib (deck perpendicular to the beam)")
    over_web: StrictBool = Field(..., description="I8.1: welded to the flange directly over the web")


class ChannelAnchors(InputModel):
    count: PositiveCount = Field(..., description="Channels between the point of maximum moment and the point of zero moment")
    la: PositiveNumber = Field(..., description="Channel length (mm)")
    tf: PositiveNumber = Field(..., description="Channel flange thickness (mm)")
    tw: PositiveNumber = Field(..., description="Channel web thickness (mm)")


class FormedDeck(InputModel):
    orientation: Literal["perpendicular", "parallel"] = Field(..., description="Deck ribs relative to the steel beam")
    hr: PositiveNumber = Field(..., description="Nominal rib height (mm)")
    wr: PositiveNumber = Field(..., description="Average width of the concrete rib or haunch (mm)")
    emid_ht_at_least_50: Optional[StrictBool] = Field(
        None, description="I8.2a: emid-ht >= 50 mm; required with the deck perpendicular to the beam")


class CompositeBeamBasis(InputModel):
    """Composite beam with steel anchors (I3.2, I8.2); the moment sense is explicit, as in Chapter F (DF-9)."""
    moment: Literal["positive", "negative"] = Field(..., description="Sense of Mux in this load combination")
    span: PositiveNumber = Field(..., description="Beam span, center-to-center of supports (mm)")
    left_beam_spacing: Optional[PositiveNumber] = Field(None, description="Distance to the adjacent beam on the left (mm)")
    left_edge_distance: Optional[PositiveNumber] = Field(None, description="Distance to the slab edge on the left (mm)")
    right_beam_spacing: Optional[PositiveNumber] = Field(None, description="Distance to the adjacent beam on the right (mm)")
    right_edge_distance: Optional[PositiveNumber] = Field(None, description="Distance to the slab edge on the right (mm)")
    tc: PositiveNumber = Field(..., description="Concrete thickness above the deck, or of the solid slab (mm)")
    deck: Optional[FormedDeck] = None
    studs: Optional[StudAnchors] = None
    channels: Optional[ChannelAnchors] = None
    shored: StrictBool = Field(..., description="I3.1b: temporary shores used during construction")
    Mu_construction: Optional[PositiveNumber] = Field(
        None, description="I3.1b: required strength before the concrete reaches 75% of f'c (kN*m), when unshored")

    @model_validator(mode="after")
    def one_limit_per_side(self):
        for side in ("left", "right"):
            given = [getattr(self, f"{side}_beam_spacing"), getattr(self, f"{side}_edge_distance")]
            if sum(v is not None for v in given) != 1:
                raise ValueError(f"Indique {side}_beam_spacing o {side}_edge_distance (solo uno).")
        return self


class PlateShearWall(InputModel):
    """Filled composite plate shear wall, planar and rectangular, with flange (closure) plates (I1.6, Fig. C-I1.4(a))."""
    length: PositiveNumber = Field(..., description="Wall length, in the direction of in-plane bending and shear (mm)")
    tsc: PositiveNumber = Field(..., description="Wall thickness tsc (mm)")
    t: PositiveNumber = Field(..., description="Thickness of each steel plate (mm)")
    tf: PositiveNumber = Field(..., description="Thickness of each flange (closure) plate (mm); I1.6 requires them")
    b: PositiveNumber = Field(..., description="I1-4: largest clear distance between rows of steel anchors or ties (mm)")
    st: PositiveNumber = Field(..., description="I1-5: largest clear spacing of the ties (mm)")
    dtie: PositiveNumber = Field(..., description="I1-6: effective diameter of the tie bar (mm)")


class ComponentAnchor(InputModel):
    """One anchor of a composite component (I8.3), with its required strengths for this load combination."""
    type: Literal["stud", "channel"]
    Qrv: NonNegativeNumber = Field(0.0, description="Required shear strength of one anchor (kN)")
    Qrt: NonNegativeNumber = Field(0.0, description="Required tensile strength of one anchor (kN)")
    spacing: PositiveNumber = Field(..., description="Center-to-center spacing of the anchors (mm)")
    d: Optional[PositiveNumber] = Field(None, description="Stud: shank diameter (mm)")
    Fu: Optional[PositiveNumber] = Field(None, description="Stud: specified minimum tensile strength (MPa)")
    height: Optional[PositiveNumber] = Field(None, description="Stud: installed height, base to top of the head (mm)")
    head_diameter: Optional[PositiveNumber] = Field(None, description="Stud: head diameter (mm); required with tension")
    edge_distance: Optional[PositiveNumber] = Field(
        None, description="Stud: anchor center to the free edge, perpendicular to the height (mm); omit if there is no free edge")
    breakout_in_shear: Optional[StrictBool] = Field(None, description="Stud: concrete breakout in shear is an applicable limit state")
    reinforcement_shear: Optional[PositiveNumber] = Field(
        None, description="Stud: nominal strength of the anchor reinforcement in shear, per ACI 318 (kN)")
    reinforcement_tension: Optional[PositiveNumber] = Field(
        None, description="Stud: nominal strength of the anchor reinforcement in tension, per ACI 318 (kN)")
    base_thickness: Optional[PositiveNumber] = Field(None, description="Stud, I8.1: thickness of the base metal (mm)")
    over_web: StrictBool = Field(False, description="Stud, I8.1: welded to a flange directly over a web")
    solid_slab: StrictBool = Field(False, description="Stud, I8.1: used solely for shear transfer in a solid slab")
    la: Optional[PositiveNumber] = Field(None, description="Channel: length (mm)")
    tf: Optional[PositiveNumber] = Field(None, description="Channel: flange thickness (mm)")
    tw: Optional[PositiveNumber] = Field(None, description="Channel: web thickness (mm)")

    @model_validator(mode="after")
    def data_of_the_declared_type(self):
        if not (self.Qrv or self.Qrt):
            raise ValueError("El anclaje requiere Qrv o Qrt.")
        needed = (("d", "Fu", "height", "breakout_in_shear", "base_thickness") if self.type == "stud" else ("la", "tf", "tw"))
        missing = [name for name in needed if getattr(self, name) is None]
        if missing:
            raise ValueError(f"Anclaje {self.type}: faltan {', '.join(missing)}.")
        return self


class CompositeBasis(InputModel):
    """Chapter I: the member type is declared, never deduced from the section."""
    kind: Literal["filled", "encased", "beam", "wall"]
    concrete: Concrete
    interaction: Literal["H1", "I5", "M2", "M2S"] = Field(
        "H1", description="H1.1; Equations I5-1a/b (filled noncompact or slender); Commentary I5 Method 2 (M2) or "
                          "Method 2 simplified (M2S), for encased and compact filled members. Walls use I5(c)")
    encased: Optional[EncasedBasis] = None
    beam: Optional[CompositeBeamBasis] = None
    wall: Optional[PlateShearWall] = None
    anchor: Optional[ComponentAnchor] = None

    @model_validator(mode="after")
    def data_of_the_declared_kind(self):
        if (self.kind == "encased") != (self.encased is not None):
            raise ValueError("composite.encased corresponde solo a kind = encased, y es obligatorio en ese caso.")
        if (self.kind == "beam") != (self.beam is not None):
            raise ValueError("composite.beam corresponde solo a kind = beam, y es obligatorio en ese caso.")
        if (self.kind == "wall") != (self.wall is not None):
            raise ValueError("composite.wall corresponde solo a kind = wall, y es obligatorio en ese caso.")
        if self.kind == "wall" and self.interaction != "H1":
            raise ValueError("Los muros usan la distribución plástica de I5(c); no indique composite.interaction.")
        return self


class CustomSectionType(str, Enum):
    SOLID_CIRCULAR = "SOLID_CIRCULAR"
    SOLID_RECTANGULAR = "SOLID_RECTANGULAR"


class CustomSection(InputModel):
    type: CustomSectionType
    diameter: Optional[PositiveNumber] = Field(None, description="Diameter of a solid circular section (mm)")
    H: Optional[PositiveNumber] = Field(None, description="Height of a solid rectangular section (mm)")
    B: Optional[PositiveNumber] = Field(None, description="Width of a solid rectangular section (mm)")

    @model_validator(mode="after")
    def validate_dimensions(self):
        circular = self.type == CustomSectionType.SOLID_CIRCULAR
        if circular and (self.diameter is None or self.H is not None or self.B is not None):
            raise ValueError("SOLID_CIRCULAR requires diameter only.")
        if not circular and (self.H is None or self.B is None or self.diameter is not None):
            raise ValueError("SOLID_RECTANGULAR requires H and B only.")
        return self


class SteelCase(InputModel):
    section_name: NonBlankString
    material: Material
    Pu: FiniteNumber = Field(0.0, description="Required axial strength (kN): > 0 compression (Chapter E), "
                                               "< 0 tension (Chapter D); LRFD load combination")
    Mux: FiniteNumber = Field(0.0, description="Required flexural strength about x (kN*m), Chapter F")
    Muy: FiniteNumber = Field(0.0, description="Required flexural strength about y (kN*m), Chapter F")
    Mw: FiniteNumber = Field(0.0, description="Single angles: required flexural strength about the major principal axis w (kN*m)")
    Mz: FiniteNumber = Field(0.0, description="Single angles: required flexural strength about the minor principal axis z (kN*m)")
    Vux: FiniteNumber = Field(0.0, description="Required shear strength that accompanies Mux, parallel to y "
                                                "(web of I-shapes, H walls of HSS) (kN), Chapter G")
    Vuy: FiniteNumber = Field(0.0, description="Required shear strength that accompanies Muy, parallel to x (kN), Chapter G")
    angle_flexure: Optional[AngleFlexure] = None
    lengths: Optional[Lengths] = Field(None, description="Unbraced lengths; required for compression")
    factors: Factors = Field(default_factory=Factors)
    single_angle_e5: Optional[SingleAngleE5Basis] = None
    double_angle_e6: Optional[DoubleAngleE6Basis] = None
    tension: Optional[TensionBasis] = None
    flexure: Optional[FlexureBasis] = None
    shear: Optional[ShearBasis] = None
    custom_section: Optional[CustomSection] = None
    composite: Optional[CompositeBasis] = None

    @model_validator(mode="after")
    def demand(self):
        if self.composite is not None and self.custom_section is not None:
            raise ValueError("Un miembro compuesto usa un perfil del catálogo, no custom_section.")
        if not any((self.Pu, self.Mux, self.Muy, self.Mw, self.Mz, self.Vux, self.Vuy,
                    self.composite and self.composite.anchor)):
            raise ValueError("La combinación debe tener al menos una demanda distinta de cero "
                             "(Pu, Mux, Muy, Mw, Mz, Vux, Vuy).")
        if self.Pu > 0 and self.lengths is None:
            raise ValueError("La compresión requiere lengths (Lx, Ly, Lz).")
        return self


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"


class Obligation(BaseModel):
    """A limit state required by the applicable chapter, derived independently of the selection."""
    id: str
    provision: str
    reason: str
    satisfied_by: Optional[str] = None


class Check(BaseModel):
    """One required strength of a load combination (axial, flexure or shear) or their interaction (H)."""
    id: Literal["axial", "flexure_x", "flexure_y", "flexure_w", "flexure_z", "shear_x", "shear_y", "interaction", "anchor"]
    chapter: Literal["D", "E", "F", "G", "H", "I"]
    demand: float = Field(..., description="|Pu| or |Vu| (kN), |Mu| (kN*m); interaction value for Chapter H")
    unit: Literal["kN", "kN·m", "–"]
    status: Status
    capacity: Optional[float] = Field(None, description="Design strength phi*Rn (LRFD); 1.0 for Chapter H")
    ratio: Optional[float] = None
    result: Optional[dict] = Field(None, description="Full chapter result (modes, equations, intermediates)")
    obligations: list[Obligation] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)


class DesignResult(BaseModel):
    section: str
    family: str
    status: Status
    section_data: dict = Field(default_factory=dict, description="Section properties used (mm units) and catalog provenance")
    checks: list[Check] = Field(default_factory=list)
    scope: str = ("Resistencia del miembro según ANSI/AISC 360-22 (LRFD): Capítulos D (tracción), E (compresión), "
                  "F (flexión), G (cortante), H (interacción H1, H2 en ángulos simples y H4) e I (miembros compuestos: I2, I3, I4, "
                  "I5, I8.2 e I8.3). Longitudes efectivas, análisis de segundo "
                  "orden, combinaciones de carga, conexiones, torsión y demás capítulos quedan fuera de este resultado.")

    @computed_field
    @property
    def ratio(self) -> Optional[float]:
        """Largest demand/capacity ratio among the evaluated checks."""
        ratios = [c.ratio for c in self.checks if c.ratio is not None]
        return max(ratios) if ratios else None

    @computed_field
    @property
    def errors(self) -> list[dict]:
        return [{**e, "check": c.id} for c in self.checks for e in c.errors]

    # Convenience accessors for the axial check (Python API; not serialized).
    def check(self, check_id: str) -> Optional[Check]:
        return next((c for c in self.checks if c.id == check_id), None)

    @property
    def chapter(self) -> Optional[str]:
        axial = self.check("axial")
        return axial.chapter if axial else None

    @property
    def compression(self) -> Optional[dict]:
        axial = self.check("axial")
        return axial.result if axial and axial.chapter == "E" else None

    @property
    def tension(self) -> Optional[dict]:
        axial = self.check("axial")
        return axial.result if axial and axial.chapter == "D" else None

    @property
    def capacity_kN(self) -> Optional[float]:
        axial = self.check("axial")
        return axial.capacity if axial else None

    @property
    def demand_kN(self) -> Optional[float]:
        axial = self.check("axial")
        return axial.demand if axial else None

    @property
    def obligations(self) -> list[Obligation]:
        return [o for c in self.checks for o in c.obligations]
