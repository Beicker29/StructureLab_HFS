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

    @model_validator(mode="after")
    def demand(self):
        if not any((self.Pu, self.Mux, self.Muy, self.Mw, self.Mz, self.Vux, self.Vuy)):
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
    id: Literal["axial", "flexure_x", "flexure_y", "flexure_w", "flexure_z", "shear_x", "shear_y", "interaction"]
    chapter: Literal["D", "E", "F", "G", "H"]
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
                  "F (flexión), G (cortante) y H (interacción H1, H2 en ángulos simples y H4). Longitudes efectivas, análisis de segundo "
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
