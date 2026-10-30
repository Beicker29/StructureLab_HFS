"""Input and result models for member compression (ANSI/AISC 360-22 Chapter E). Units: N, mm, MPa, kN."""
from enum import Enum
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator


class DesignMethod(str, Enum):
    LRFD = "LRFD"
    ASD = "ASD"


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
            raise ValueError(f"Duplicate JSON field {key!r}; supply exactly one value per field.")
        result[key] = value
    return result


class Material(InputModel):
    Fy: PositiveNumber = Field(..., description="Specified minimum yield stress (MPa)")
    E: PositiveNumber = Field(200000.0, description="Modulus of elasticity (MPa); Chapter E defines 200000")


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
    Pu: PositiveNumber = Field(..., description="Required axial compressive strength (kN), LRFD or ASD combination")
    lengths: Lengths
    factors: Factors = Field(default_factory=Factors)
    design_method: DesignMethod = DesignMethod.LRFD
    single_angle_e5: Optional[SingleAngleE5Basis] = None
    double_angle_e6: Optional[DoubleAngleE6Basis] = None
    custom_section: Optional[CustomSection] = None


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"


class Obligation(BaseModel):
    """A limit state required by Chapter E, derived independently of the selection."""
    id: str
    provision: str
    reason: str
    satisfied_by: Optional[str] = None


class DesignResult(BaseModel):
    section: str
    family: str
    design_method: str
    status: Status
    demand_kN: float
    section_data: dict = Field(default_factory=dict, description="Section properties used (mm units) and catalog provenance")
    capacity_kN: Optional[float] = None
    ratio: Optional[float] = None
    compression: Optional[dict] = Field(None, description="Full Chapter E result (modes, equations, intermediates)")
    obligations: list[Obligation] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
    scope: str = ("Member compressive strength per ANSI/AISC 360-22 Chapter E only. Effective lengths, "
                  "load combinations, connections and other chapters are outside this result.")
