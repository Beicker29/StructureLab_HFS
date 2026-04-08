from typing import Optional
from pydantic import BaseModel, Field

class Section(BaseModel):
    name: str = Field(..., description="Section name (e.g., W14x90)")
    type: str = Field("W", description="Shape type")
    
    # Fundamental properties
    area: float = Field(..., alias="A", description="Cross-sectional area (mm^2)")
    d: Optional[float] = Field(None, description="Depth (mm)")
    bf: Optional[float] = Field(None, description="Flange width (mm)")
    tf: Optional[float] = Field(None, description="Flange thickness (mm)")
    tw: Optional[float] = Field(None, description="Web thickness (mm)")
    
    # Moment of inertia
    ix: Optional[float] = Field(None, alias="Ix", description="Moment of inertia about x-axis (mm^4)")
    iy: Optional[float] = Field(None, alias="Iy", description="Moment of inertia about y-axis (mm^4)")
    
    # Section modulus
    sx: Optional[float] = Field(None, alias="Sx", description="Elastic section modulus about x-axis (mm^3)")
    sy: Optional[float] = Field(None, alias="Sy", description="Elastic section modulus about y-axis (mm^3)")
    zx: Optional[float] = Field(None, alias="Zx", description="Plastic section modulus about x-axis (mm^3)")
    zy: Optional[float] = Field(None, alias="Zy", description="Plastic section modulus about y-axis (mm^3)")
    
    # Radius of gyration
    rx: Optional[float] = Field(None, description="Radius of gyration about x-axis (mm)")
    ry: Optional[float] = Field(None, description="Radius of gyration about y-axis (mm)")
    
    # Torsional properties
    j: Optional[float] = Field(None, alias="J", description="Torsional constant (mm^4)")
    cw: Optional[float] = Field(None, alias="Cw", description="Warping constant (mm^6)")

    class Config:
        populate_by_name = True
