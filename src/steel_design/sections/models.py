from typing import Optional
from pydantic import ConfigDict, Field
from ..input_contracts import InputModel, NonNegativeNumber, NonBlankString, PositiveCount


class SectionSource(InputModel):
    """Location in the exact workbook read; not a certification of its data."""

    file: NonBlankString
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sheet: NonBlankString
    row: PositiveCount
    original_name: NonBlankString


class Section(InputModel):
    name: NonBlankString = Field(..., description="Section name (e.g., W14x90)")
    type: NonBlankString = Field("W", description="Shape type")
    source: Optional[SectionSource] = Field(None, description="Import provenance; None for unsourced programmatic sections")
    
    # Fundamental properties
    area: NonNegativeNumber = Field(..., alias="A", description="Cross-sectional area (mm^2)")
    d: Optional[NonNegativeNumber] = Field(None, description="Depth (mm)")
    h: Optional[NonNegativeNumber] = Field(None, description="Flat wall depth for HSS / detailed web depth (mm)")
    bf: Optional[NonNegativeNumber] = Field(None, description="Flange width (mm)")
    b: Optional[NonNegativeNumber] = Field(None, description="Flat wall width for HSS / leg width (mm)")
    od: Optional[NonNegativeNumber] = Field(None, alias="OD", description="Outside diameter for round HSS/pipe (mm)")
    tf: Optional[NonNegativeNumber] = Field(None, description="Flange thickness (mm)")
    t: Optional[NonNegativeNumber] = Field(None, description="Angle/HSS nominal thickness (mm)")
    tdes: Optional[NonNegativeNumber] = Field(None, alias="tdes", description="HSS design thickness (mm)")
    tw: Optional[NonNegativeNumber] = Field(None, description="Web thickness (mm)")
    ho: Optional[NonNegativeNumber] = Field(None, alias="ho", description="Distance between flange centroids (mm)")
    
    # Moments of inertia (geometric x/y axes)
    ix: Optional[NonNegativeNumber] = Field(None, alias="Ix", description="Moment of inertia about x-axis (mm^4)")
    iy: Optional[NonNegativeNumber] = Field(None, alias="Iy", description="Moment of inertia about y-axis (mm^4)")
    # Radius of gyration
    rx: Optional[NonNegativeNumber] = Field(None, description="Radius of gyration about x-axis (mm)")
    ry: Optional[NonNegativeNumber] = Field(None, description="Radius of gyration about y-axis (mm)")
    rz: Optional[NonNegativeNumber] = Field(None, description="Radius of gyration about z/principal axis (mm)")
    
    # Torsional properties
    j: Optional[NonNegativeNumber] = Field(None, alias="J", description="Torsional constant (mm^4)")
    cw: Optional[NonNegativeNumber] = Field(None, alias="Cw", description="Warping constant (mm^6)")
    ro: Optional[NonNegativeNumber] = Field(None, alias="ro", description="Polar radius of gyration about shear center (mm)")
    H: Optional[NonNegativeNumber] = Field(None, alias="H", description="Flexural-torsional constant (dimensionless)")

    # Slenderness metrics from AISC database
    bf_2tf_ratio: Optional[NonNegativeNumber] = Field(None, alias="bf/2tf", description="Flange slenderness bf/2tf")
    b_t_ratio: Optional[NonNegativeNumber] = Field(None, alias="b/t", description="b/t slenderness")
    b_tdes_ratio: Optional[NonNegativeNumber] = Field(None, alias="b/tdes", description="b/tdes slenderness")
    h_tw_ratio: Optional[NonNegativeNumber] = Field(None, alias="h/tw", description="h/tw slenderness")
    h_tdes_ratio: Optional[NonNegativeNumber] = Field(None, alias="h/tdes", description="h/tdes slenderness")
    d_t_ratio: Optional[NonNegativeNumber] = Field(None, alias="D/t", description="D/t slenderness")

    model_config = ConfigDict(populate_by_name=True)
