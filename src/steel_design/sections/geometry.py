"""Canonical solid geometry, mm-based; expressions preserved from the engine."""
import math

from ..models import CustomSectionType, SteelCase
from ..domain.errors import ValidationError
from .models import Section


def build_custom_section(case: SteelCase) -> Section:
    custom = case.custom_section
    if custom is None:
        raise ValidationError("custom_section is required to build a custom section.")

    if custom.type == CustomSectionType.SOLID_CIRCULAR:
        diameter = custom.diameter or 0.0
        area = math.pi * (diameter**2) / 4.0
        inertia = math.pi * (diameter**4) / 64.0
        radius_of_gyration = diameter / 4.0
        elastic_modulus = math.pi * (diameter**3) / 32.0
        plastic_modulus = (diameter**3) / 6.0
        return Section(
            name=case.section_name,
            type=custom.type.value,
            A=area,
            OD=diameter,
            Ix=inertia,
            Iy=inertia,
            Sx=elastic_modulus,
            Sy=elastic_modulus,
            Zx=plastic_modulus,
            Zy=plastic_modulus,
            rx=radius_of_gyration,
            ry=radius_of_gyration,
        )

    height = custom.H or 0.0
    width = custom.B or 0.0
    area = width * height
    inertia_x = width * (height**3) / 12.0
    inertia_y = height * (width**3) / 12.0
    radius_of_gyration_x = math.sqrt(inertia_x / area) if area > 0.0 else 0.0
    radius_of_gyration_y = math.sqrt(inertia_y / area) if area > 0.0 else 0.0
    section_modulus_x = width * (height**2) / 6.0
    section_modulus_y = height * (width**2) / 6.0
    plastic_modulus_x = width * (height**2) / 4.0
    plastic_modulus_y = height * (width**2) / 4.0
    return Section(
        name=case.section_name,
        type=custom.type.value,
        A=area,
        h=height,
        b=width,
        Ix=inertia_x,
        Iy=inertia_y,
        Sx=section_modulus_x,
        Sy=section_modulus_y,
        Zx=plastic_modulus_x,
        Zy=plastic_modulus_y,
        rx=radius_of_gyration_x,
        ry=radius_of_gyration_y,
    )

