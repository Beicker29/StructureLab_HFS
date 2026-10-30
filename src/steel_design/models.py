"""Input and result models for member compression (ANSI/AISC 360-22 Chapter E). Units: N, mm, MPa, kN."""
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, StrictBool, model_validator

from .design_methods import DesignMethod
from .input_contracts import InputModel, NonBlankString, NonNegativeNumber, PositiveNumber


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
    capacity_kN: Optional[float] = None
    ratio: Optional[float] = None
    compression: Optional[dict] = Field(None, description="Full Chapter E result (modes, equations, intermediates)")
    obligations: list[Obligation] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
    scope: str = ("Member compressive strength per ANSI/AISC 360-22 Chapter E only. Effective lengths, "
                  "load combinations, connections and other chapters are outside this result.")
