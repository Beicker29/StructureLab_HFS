"""Solid custom sections (mm): area, moments of inertia, radii of gyration, elastic and plastic moduli."""
import math

from ..errors import ValidationError
from ..models import CustomSectionType, SteelCase
from .models import Section


def build_box_section(case: SteelCase) -> Section:
    """Welded box (mm): sharp corners; b and h are the clear distances, as in Design Guide 6, Example 2.5."""
    box = case.composite.box
    if 2 * box.t >= min(box.B, box.H):
        raise ValidationError("Las placas deben dejar un núcleo de concreto positivo.", details={"section": case.section_name})
    bi, hi = box.B - 2 * box.t, box.H - 2 * box.t
    return Section(name=case.section_name, type="RECTANGULAR_HSS", A=box.B * box.H - bi * hi, tdes=box.t, Ht=box.H, B=box.B,
                   b=bi, h=hi, Ix=(box.B * box.H**3 - bi * hi**3) / 12.0, Iy=(box.H * box.B**3 - hi * bi**3) / 12.0,
                   Zx=(box.B * box.H**2 - bi * hi**2) / 4.0, Zy=(box.H * box.B**2 - hi * bi**2) / 4.0,
                   **{"b/tdes": bi / box.t, "h/tdes": hi / box.t})


def build_c_wall_section(case: SteelCase) -> Section:
    """Steel of a C-shaped wall (mm); the catalog-free properties of Design Guide 38 live in codes/aisc_dg38/walls.py."""
    wall = case.composite.c_wall
    if 2 * wall.tp >= min(wall.tsc_w, wall.tsc_f) or wall.W <= wall.tsc_w + wall.tp or wall.L <= 2 * wall.tsc_f:
        raise ValidationError("Las placas y las alas deben dejar un núcleo de concreto positivo.", details={"section": case.section_name})
    return Section(name=case.section_name, type="COMPOSITE_WALL", A=wall.tp * (4 * wall.W + 2 * wall.L + 2 * wall.tsc_f - 12 * wall.tp))


def build_coupling_beam_section(case: SteelCase) -> Section:
    """Steel of a built-up box coupling beam (mm)."""
    beam = case.composite.coupling_beam
    if 2 * beam.tw >= beam.b or 2 * beam.tf >= beam.h:
        raise ValidationError("Las placas deben dejar un núcleo de concreto positivo.", details={"section": case.section_name})
    return Section(name=case.section_name, type="COMPOSITE_WALL", A=2 * beam.h * beam.tw + 2 * (beam.b - 2 * beam.tw) * beam.tf)


def build_wall_section(case: SteelCase) -> Section:
    """Steel of a planar composite plate shear wall (mm): two full-length plates and two flange plates between them."""
    wall = case.composite.wall
    if 2 * wall.t >= wall.tsc or 2 * wall.tf >= wall.length:
        raise ValidationError("Las placas deben dejar un núcleo de concreto positivo.", details={"section": case.section_name})
    between = wall.tsc - 2 * wall.t
    area = 2 * wall.t * wall.length + 2 * wall.tf * between
    ix = 2 * wall.t * wall.length**3 / 12.0 + 2 * wall.tf * between * ((wall.length - wall.tf) / 2) ** 2 + 2 * between * wall.tf**3 / 12.0
    iy = (2 * wall.length * wall.t**3 / 12.0 + 2 * wall.length * wall.t * ((wall.tsc - wall.t) / 2) ** 2
          + 2 * wall.tf * between**3 / 12.0)
    return Section(name=case.section_name, type="COMPOSITE_WALL", A=area, Ix=ix, Iy=iy)


def build_custom_section(case: SteelCase) -> Section:
    custom = case.custom_section
    if custom is None:
        raise ValidationError("custom_section is required to build a custom section.")
    if custom.type == CustomSectionType.SOLID_CIRCULAR:
        d = custom.diameter
        inertia = math.pi * d**4 / 64.0
        s, z = math.pi * d**3 / 32.0, d**3 / 6.0
        return Section(name=case.section_name, type=custom.type.value, A=math.pi * d**2 / 4.0, OD=d,
                       Ix=inertia, Iy=inertia, rx=d / 4.0, ry=d / 4.0, Sx=s, Sy=s, Zx=z, Zy=z)
    h, b = custom.H, custom.B
    area = b * h
    ix, iy = b * h**3 / 12.0, h * b**3 / 12.0
    return Section(name=case.section_name, type=custom.type.value, A=area, h=h, b=b,
                   Ix=ix, Iy=iy, rx=math.sqrt(ix / area), ry=math.sqrt(iy / area),
                   Sx=b * h**2 / 6.0, Sy=h * b**2 / 6.0, Zx=b * h**2 / 4.0, Zy=h * b**2 / 4.0)
