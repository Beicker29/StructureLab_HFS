"""Input and result models for axial members (ANSI/AISC 360-22 Chapters D and E). Units: N, mm, MPa, kN."""
from enum import Enum
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator


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
    Pu: FiniteNumber = Field(..., description="Required axial strength (kN): > 0 compression (Chapter E), "
                                               "< 0 tension (Chapter D); LRFD load combination")
    lengths: Optional[Lengths] = Field(None, description="Unbraced lengths; required for compression")
    factors: Factors = Field(default_factory=Factors)
    single_angle_e5: Optional[SingleAngleE5Basis] = None
    double_angle_e6: Optional[DoubleAngleE6Basis] = None
    tension: Optional[TensionBasis] = None
    custom_section: Optional[CustomSection] = None

    @model_validator(mode="after")
    def axial_demand(self):
        if self.Pu == 0:
            raise ValueError("Pu debe ser distinto de cero: > 0 compresión, < 0 tracción.")
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


class DesignResult(BaseModel):
    section: str
    family: str
    status: Status
    chapter: Literal["D", "E"]
    demand_kN: float = Field(..., description="|Pu| (kN)")
    section_data: dict = Field(default_factory=dict, description="Section properties used (mm units) and catalog provenance")
    capacity_kN: Optional[float] = Field(None, description="Design strength phi*Pn (LRFD), kN")
    ratio: Optional[float] = None
    compression: Optional[dict] = Field(None, description="Full Chapter E result (modes, equations, intermediates)")
    tension: Optional[dict] = Field(None, description="Full Chapter D result (limit states, equations, intermediates)")
    obligations: list[Obligation] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
    scope: str = ("Resistencia axial del miembro según ANSI/AISC 360-22, Capítulos D (tracción) y E (compresión). "
                  "Las longitudes efectivas, combinaciones de carga, conexiones y demás capítulos quedan fuera de este resultado.")
