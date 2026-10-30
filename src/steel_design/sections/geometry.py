"""Solid custom sections (mm): area, moments of inertia, radii of gyration, elastic and plastic moduli."""
import math

from ..errors import ValidationError
from ..models import CustomSectionType, SteelCase
from .models import Section


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
