from typing import Optional
from pydantic import BaseModel, Field

class Section(BaseModel):
    name: str = Field(..., description="Section name (e.g., W14x90)")
    type: str = Field("W", description="Shape type")
    
    # Fundamental properties
    area: float = Field(..., alias="A", description="Cross-sectional area (mm^2)")
    d: Optional[float] = Field(None, description="Depth (mm)")
    h: Optional[float] = Field(None, description="Flat wall depth for HSS / detailed web depth (mm)")
    bf: Optional[float] = Field(None, description="Flange width (mm)")
    b: Optional[float] = Field(None, description="Flat wall width for HSS / leg width (mm)")
    od: Optional[float] = Field(None, alias="OD", description="Outside diameter for round HSS/pipe (mm)")
    id: Optional[float] = Field(None, alias="ID", description="Inside diameter for round HSS/pipe (mm)")
    tf: Optional[float] = Field(None, description="Flange thickness (mm)")
    t: Optional[float] = Field(None, description="Angle/HSS nominal thickness (mm)")
    tdes: Optional[float] = Field(None, alias="tdes", description="HSS design thickness (mm)")
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
    ro: Optional[float] = Field(None, alias="ro", description="Polar radius of gyration about shear center (mm)")
    H: Optional[float] = Field(None, alias="H", description="Flexural-torsional constant (dimensionless)")

    # Shear-center / centroid variables
    x: Optional[float] = Field(None, alias="x", description="Centroid distance x (mm)")
    y: Optional[float] = Field(None, alias="y", description="Centroid distance y (mm)")
    eo: Optional[float] = Field(None, alias="eo", description="Shear-center eccentricity (mm)")

    # Slenderness metrics from AISC database
    bf_2tf_ratio: Optional[float] = Field(None, alias="bf/2tf", description="Flange slenderness bf/2tf")
    b_t_ratio: Optional[float] = Field(None, alias="b/t", description="b/t slenderness")
    b_tdes_ratio: Optional[float] = Field(None, alias="b/tdes", description="b/tdes slenderness")
    h_tw_ratio: Optional[float] = Field(None, alias="h/tw", description="h/tw slenderness")
    h_tdes_ratio: Optional[float] = Field(None, alias="h/tdes", description="h/tdes slenderness")
    d_t_ratio: Optional[float] = Field(None, alias="D/t", description="D/t slenderness")

    class Config:
        populate_by_name = True
