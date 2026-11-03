import math

from pydantic import ConfigDict, Field

from ..models import InputModel, NonBlankString, NonNegativeNumber, PositiveCount


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
    source: SectionSource | None = Field(None, description="Import provenance; None for unsourced programmatic sections")
    
    # Fundamental properties
    area: NonNegativeNumber = Field(..., alias="A", description="Cross-sectional area (mm^2)")
    d: NonNegativeNumber | None = Field(None, description="Depth (mm)")
    h: NonNegativeNumber | None = Field(None, description="Flat wall depth for HSS / detailed web depth (mm)")
    bf: NonNegativeNumber | None = Field(None, description="Flange width (mm); top flange of a built-up I")
    b: NonNegativeNumber | None = Field(None, description="Flat wall width for HSS / leg width (mm)")
    od: NonNegativeNumber | None = Field(None, alias="OD", description="Outside diameter for round HSS/pipe (mm)")
    tf: NonNegativeNumber | None = Field(None, description="Flange thickness (mm); top flange of a built-up I")
    bf_bottom: NonNegativeNumber | None = Field(None, description="Built-up I: bottom flange width (mm)")
    tf_bottom: NonNegativeNumber | None = Field(None, description="Built-up I: bottom flange thickness (mm)")
    t: NonNegativeNumber | None = Field(None, description="Angle/HSS nominal thickness (mm)")
    tdes: NonNegativeNumber | None = Field(None, alias="tdes", description="HSS design thickness (mm)")
    tw: NonNegativeNumber | None = Field(None, description="Web thickness (mm)")
    ho: NonNegativeNumber | None = Field(None, alias="ho", description="Distance between flange centroids (mm)")
    h_out: NonNegativeNumber | None = Field(None, alias="Ht", description="Rectangular HSS outside depth (mm)")
    b_out: NonNegativeNumber | None = Field(None, alias="B", description="Rectangular HSS outside width (mm)")
    
    # Moments of inertia (geometric x/y axes)
    ix: NonNegativeNumber | None = Field(None, alias="Ix", description="Moment of inertia about x-axis (mm^4)")
    iy: NonNegativeNumber | None = Field(None, alias="Iy", description="Moment of inertia about y-axis (mm^4)")
    iw: NonNegativeNumber | None = Field(None, alias="Iw", description="Angle: moment of inertia about the major principal axis w (mm^4)")
    iz: NonNegativeNumber | None = Field(None, alias="Iz", description="Angle: moment of inertia about the minor principal axis z (mm^4)")
    sx: NonNegativeNumber | None = Field(None, alias="Sx", description="Elastic section modulus about x (mm^3)")
    sy: NonNegativeNumber | None = Field(None, alias="Sy", description="Elastic section modulus about y (mm^3)")
    zx: NonNegativeNumber | None = Field(None, alias="Zx", description="Plastic section modulus about x (mm^3)")
    zy: NonNegativeNumber | None = Field(None, alias="Zy", description="Plastic section modulus about y (mm^3)")
    # Single angles: elastic moduli at point A (short-leg toe), B (heel), C (long-leg toe), principal axes w, z
    sw_a: NonNegativeNumber | None = Field(None, alias="SwA", description="Angle: S about w at point A (mm^3)")
    sw_b: NonNegativeNumber | None = Field(None, alias="SwB", description="Angle: S about w at point B (mm^3)")
    sw_c: NonNegativeNumber | None = Field(None, alias="SwC", description="Angle: S about w at point C (mm^3)")
    sz_a: NonNegativeNumber | None = Field(None, alias="SzA", description="Angle: S about z at point A (mm^3)")
    sz_b: NonNegativeNumber | None = Field(None, alias="SzB", description="Angle: S about z at point B (mm^3)")
    sz_c: NonNegativeNumber | None = Field(None, alias="SzC", description="Angle: S about z at point C (mm^3)")
    # Radius of gyration
    rx: NonNegativeNumber | None = Field(None, description="Radius of gyration about x-axis (mm)")
    ry: NonNegativeNumber | None = Field(None, description="Radius of gyration about y-axis (mm)")
    rz: NonNegativeNumber | None = Field(None, description="Radius of gyration about z/principal axis (mm)")
    
    # Torsional properties
    j: NonNegativeNumber | None = Field(None, alias="J", description="Torsional constant (mm^4)")
    cw: NonNegativeNumber | None = Field(None, alias="Cw", description="Warping constant (mm^6)")
    ro: NonNegativeNumber | None = Field(None, alias="ro", description="Polar radius of gyration about shear center (mm)")
    H: NonNegativeNumber | None = Field(None, alias="H", description="Flexural-torsional constant (dimensionless)")
    x: NonNegativeNumber | None = Field(None, alias="x", description="Angle: centroid distance from the heel along x (mm)")
    y: NonNegativeNumber | None = Field(None, alias="y", description="Angle: centroid distance from the heel along y (mm)")
    tan_alpha: NonNegativeNumber | None = Field(None, alias="tan_alpha", description="Angle: tangent of the angle between the y and z axes")
    beta_w: NonNegativeNumber | None = Field(
        None, description="Angle: |beta_w| of F10-4 (mm), 0 for equal legs; the sign depends on the leg in compression"
    )

    # Slenderness metrics from AISC database
    bf_2tf_ratio: NonNegativeNumber | None = Field(None, alias="bf/2tf", description="Flange slenderness bf/2tf")
    b_t_ratio: NonNegativeNumber | None = Field(None, alias="b/t", description="b/t slenderness")
    b_tdes_ratio: NonNegativeNumber | None = Field(None, alias="b/tdes", description="b/tdes slenderness")
    h_tw_ratio: NonNegativeNumber | None = Field(None, alias="h/tw", description="h/tw slenderness")
    h_tdes_ratio: NonNegativeNumber | None = Field(None, alias="h/tdes", description="h/tdes slenderness")
    d_t_ratio: NonNegativeNumber | None = Field(None, alias="D/t", description="D/t slenderness")

    model_config = ConfigDict(populate_by_name=True)


def missing_properties(section: Section, names) -> list[str]:
    """The names of the properties that the catalog does not give as finite positive numbers."""
    def given(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0
    return [name for name in names if not given(getattr(section, name))]
