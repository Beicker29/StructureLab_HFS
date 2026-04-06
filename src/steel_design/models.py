from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

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
    Lb: float = Field(..., description="Unbraced length for lateral-torsional buckling (mm)")

class Connection(BaseModel):
    Ae: Optional[float] = Field(None, description="Effective net area (mm^2). If None, defaults to Ag.")

class Factors(BaseModel):
    Kx: float = Field(1.0, description="Effective length factor for strong axis")
    Ky: float = Field(1.0, description="Effective length factor for weak axis")
    Cb: float = Field(1.0, description="Lateral-torsional buckling modification factor")

class SteelCase(BaseModel):
    section_name: str
    material: Material
    loads: Loads
    lengths: Lengths
    factors: Factors = Field(default_factory=Factors)
    connection: Connection = Field(default_factory=Connection)
    design_method: DesignMethod = DesignMethod.LRFD

class CheckResult(BaseModel):
    name: str = Field(..., description="Name of the check (e.g., Flexure Major F2)")
    code: str = Field("AISC 360-22", description="Reference code")
    clause: str = Field(..., description="Code clause (e.g., F2-1)")
    demand: float = Field(..., description="Required strength")
    capacity: float = Field(..., description="Available strength (phi*Rn or Rn/Omega)")
    dcr: float = Field(..., description="Demand to capacity ratio")
    status: CheckStatus = Field(..., description="PASS or FAIL status")
