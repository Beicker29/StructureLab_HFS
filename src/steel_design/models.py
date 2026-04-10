from enum import Enum
from typing import Any, Dict, Optional

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
    Vu: float = Field(0.0, description="Required shear strength (kN)")

class Lengths(BaseModel):
    Lx: float = Field(..., description="Unbraced length for strong axis buckling (mm)")
    Ly: float = Field(..., description="Unbraced length for weak axis buckling (mm)")
    Lz: float = Field(..., description="Unbraced length for torsional/flexural-torsional buckling (mm)")
    Lb: float = Field(..., description="Unbraced length for lateral-torsional buckling (mm)")

class AngleCompressionMode(str, Enum):
    ONE_LEG = "one_leg"
    BOTH_LEGS = "both_legs"


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


class Connection(BaseModel):
    An: Optional[float] = Field(None, description="Net area for tension rupture (mm^2)")
    U: Optional[float] = Field(None, description="Shear lag factor for tension rupture (0 < U <= 1)")
    angle_compression_mode: Optional[AngleCompressionMode] = Field(
        None,
        description="Connection mode for single-angle compression (E5).",
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
