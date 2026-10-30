"""Solid custom sections (mm): area, moments of inertia and radii of gyration."""
import math

from ..domain.errors import ValidationError
from ..models import CustomSectionType, SteelCase
from .models import Section


def build_custom_section(case: SteelCase) -> Section:
    custom = case.custom_section
    if custom is None:
        raise ValidationError("custom_section is required to build a custom section.")
    if custom.type == CustomSectionType.SOLID_CIRCULAR:
        d = custom.diameter
        inertia = math.pi * d**4 / 64.0
        return Section(name=case.section_name, type=custom.type.value, A=math.pi * d**2 / 4.0, OD=d,
                       Ix=inertia, Iy=inertia, rx=d / 4.0, ry=d / 4.0)
    h, b = custom.H, custom.B
    area = b * h
    ix, iy = b * h**3 / 12.0, h * b**3 / 12.0
    return Section(name=case.section_name, type=custom.type.value, A=area, h=h, b=b,
                   Ix=ix, Iy=iy, rx=math.sqrt(ix / area), ry=math.sqrt(iy / area))
