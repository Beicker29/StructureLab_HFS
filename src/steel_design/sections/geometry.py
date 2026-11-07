"""Custom sections (mm): solid bars and welded built-up I-shapes, and the steel of composite members.

Area, moments of inertia, radii of gyration, elastic and plastic moduli. A welded built-up I has no weld or corner radii:
h is the clear distance between flanges (B4.1b(b)). Its J, Cw and shear center are thin-walled values (decision DF-17).
"""
import math

from ..codes.aisc_dg06.members import box_torsional_constant
from ..errors import ValidationError
from ..models import CustomSectionType, SteelCase
from .models import Section


def build_box_section(case: SteelCase) -> Section:
    """Welded box (mm): sharp corners; b and h are the clear distances, as in Design Guide 6, Example 2.5."""
    box = case.composite.box
    if 2 * box.t >= min(box.B, box.H):
        raise ValidationError("Las placas deben dejar un núcleo de concreto positivo.", details={"section": case.section_name})
    bi, hi = box.B - 2 * box.t, box.H - 2 * box.t
    area, ix, iy = box.B * box.H - bi * hi, (box.B * box.H**3 - bi * hi**3) / 12.0, (box.H * box.B**3 - hi * bi**3) / 12.0
    return Section(name=case.section_name, type="RECTANGULAR_HSS", area=area, tdes=box.t, h_out=box.H, b_out=box.B,
                   b=bi, h=hi, ix=ix, iy=iy, sx=2 * ix / box.H, sy=2 * iy / box.B, rx=math.sqrt(ix / area), ry=math.sqrt(iy / area),
                   j=box_torsional_constant(B=box.B, H=box.H, t=box.t),
                   zx=(box.B * box.H**2 - bi * hi**2) / 4.0, zy=(box.H * box.B**2 - hi * bi**2) / 4.0,
                   **{"b/tdes": bi / box.t, "h/tdes": hi / box.t})


def build_c_wall_section(case: SteelCase) -> Section:
    """Steel of a C-shaped wall (mm); the catalog-free properties of Design Guide 38 live in codes/aisc_dg38/walls.py."""
    wall = case.composite.c_wall
    if 2 * wall.tp >= min(wall.tsc_w, wall.tsc_f) or wall.W <= wall.tsc_w + wall.tp or wall.L <= 2 * wall.tsc_f:
        raise ValidationError("Las placas y las alas deben dejar un núcleo de concreto positivo.", details={"section": case.section_name})
    return Section(name=case.section_name, type="COMPOSITE_WALL", area=wall.tp * (4 * wall.W + 2 * wall.L + 2 * wall.tsc_f - 12 * wall.tp))


def build_coupling_beam_section(case: SteelCase) -> Section:
    """Steel of a built-up box coupling beam (mm)."""
    beam = case.composite.coupling_beam
    if 2 * beam.tw >= beam.b or 2 * beam.tf >= beam.h:
        raise ValidationError("Las placas deben dejar un núcleo de concreto positivo.", details={"section": case.section_name})
    return Section(name=case.section_name, type="COMPOSITE_WALL", area=2 * beam.h * beam.tw + 2 * (beam.b - 2 * beam.tw) * beam.tf)


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
    return Section(name=case.section_name, type="COMPOSITE_WALL", area=area, ix=ix, iy=iy)


def _plastic_axis(plates, area):
    """Depth from the +2 fiber of the line that halves the area: the plastic neutral axis."""
    above = 0.0
    for near, far, width in plates:
        if above + width * (far - near) >= area / 2:
            return near + (area / 2 - above) / width
        above += width * (far - near)
    raise ValueError("the plates do not add up to the area")


def _first_moments(plates, y):
    """Sum of the absolute first moments of the plates about the horizontal line at depth y."""
    total = 0.0
    for near, far, width in plates:
        if y > near:
            edge = min(far, y)
            total += width * (edge - near) * (y - (near + edge) / 2)
        if y < far:
            edge = max(near, y)
            total += width * (far - edge) * ((edge + far) / 2 - y)
    return total


def built_up_i_properties(*, d, tw, bf_plus2, tf_plus2, bf_minus2, tf_minus2) -> dict:
    """Plate properties of a welded I (mm). Depths are measured from the +2 fiber toward -2.

    J = sum of b*t^3/3 with the clear web height h; Cw = ho^2*Iyt*Iyb/(Iyt + Iyb) and the shear center at ho*Iyb/(Iyt + Iyb)
    from the centroid of the +2 flange, with the flange inertias about y (thin-walled section, Commentary F4 and AISC Design Guide 9).
    """
    h = d - tf_plus2 - tf_minus2
    plates = ((0.0, tf_plus2, bf_plus2), (tf_plus2, d - tf_minus2, tw), (d - tf_minus2, d, bf_minus2))
    area = sum(w * (b - t) for t, b, w in plates)
    y_plus2 = sum(w * (b - t) * (t + b) / 2 for t, b, w in plates) / area
    ix = sum(w * (b - t) ** 3 / 12 + w * (b - t) * ((t + b) / 2 - y_plus2) ** 2 for t, b, w in plates)
    iy_plus2, iy_minus2 = tf_plus2 * bf_plus2**3 / 12, tf_minus2 * bf_minus2**3 / 12
    iy = iy_plus2 + iy_minus2 + h * tw**3 / 12
    ho = d - tf_plus2 / 2 - tf_minus2 / 2
    y_pna = _plastic_axis(plates, area)
    y_shear_center = tf_plus2 / 2 + ho * iy_minus2 / (iy_plus2 + iy_minus2)
    yo = y_shear_center - y_plus2
    ro = math.sqrt(yo**2 + (ix + iy) / area)
    return {"area": area, "h": h, "ho": ho, "y_plus2": y_plus2, "y_pna": y_pna, "ix": ix, "iy": iy, "iy_plus2": iy_plus2,
            "iy_minus2": iy_minus2, "sx_plus2": ix / y_plus2, "sx_minus2": ix / (d - y_plus2), "zx": _first_moments(plates, y_pna),
            "sy": iy / (max(bf_plus2, bf_minus2) / 2), "zy": (tf_plus2 * bf_plus2**2 + tf_minus2 * bf_minus2**2 + h * tw**2) / 4,
            "j": (bf_plus2 * tf_plus2**3 + bf_minus2 * tf_minus2**3 + h * tw**3) / 3,
            "cw": ho**2 * iy_plus2 * iy_minus2 / (iy_plus2 + iy_minus2), "yo": yo, "ro": ro, "H": 1 - yo**2 / ro**2}


def singly_symmetric_i(section: Section) -> bool:
    """A built-up I whose flanges differ: symmetric about y only."""
    return section.bf_minus2 is not None and (section.bf_minus2, section.tf_minus2) != (section.bf, section.tf)


def i_major_properties(section: Section, compression_flange: str | None) -> dict:
    """Major-axis properties of an I-shape referred to its compression flange, "plus2" or "minus2" (B4.1b, F4, F5).

    Rolled shapes take the catalog values: h = (h/tw)*tw, hc = hp = h and Sxc = Sxt = Sx (doubly symmetric, B4.1b(a)).
    Iyc = tfc*bfc^3/12, the compression flange alone (F4.2(c)(2)).
    """
    if section.type.upper() != "I_BUILT_UP":
        h = section.h_tw_ratio * section.tw
        return {"bfc": section.bf, "tfc": section.tf, "bft": section.bf, "tft": section.tf, "tw": section.tw, "h": h, "hc": h,
                "hp": h, "Sxc": section.sx, "Sxt": section.sx, "Zx": section.zx, "Iyc": section.tf * section.bf**3 / 12,
                "Iy": section.iy, "ho": section.ho, "J": section.j}
    p = built_up_i_properties(d=section.d, tw=section.tw, bf_plus2=section.bf, tf_plus2=section.tf, bf_minus2=section.bf_minus2,
                              tf_minus2=section.tf_minus2)
    plus2 = compression_flange == "plus2"
    flanges = ((section.bf, section.tf), (section.bf_minus2, section.tf_minus2))
    (bfc, tfc), (bft, tft) = flanges if plus2 else flanges[::-1]
    c = p["y_plus2"] if plus2 else section.d - p["y_plus2"]            # centroid to the compression fiber
    plastic = p["y_pna"] if plus2 else section.d - p["y_pna"]          # plastic neutral axis to the compression fiber
    return {"bfc": bfc, "tfc": tfc, "bft": bft, "tft": tft, "tw": section.tw, "h": p["h"], "hc": 2 * (c - tfc),
            "hp": 2 * (plastic - tfc), "Sxc": p["ix"] / c, "Sxt": p["ix"] / (section.d - c), "Zx": p["zx"],
            "Iyc": tfc * bfc**3 / 12, "Iy": p["iy"], "ho": p["ho"], "J": p["j"]}


def _built_up_i(case: SteelCase) -> Section:
    custom = case.custom_section
    plus2, minus2 = custom.flange_plus2, custom.flange_minus2
    if plus2.t + minus2.t >= custom.d or custom.tw >= min(plus2.b, minus2.b):
        raise ValidationError("Las alas deben dejar una altura de alma positiva y el alma no puede ser más ancha que las alas.",
                              details={"section": case.section_name})
    p = built_up_i_properties(d=custom.d, tw=custom.tw, bf_plus2=plus2.b, tf_plus2=plus2.t, bf_minus2=minus2.b, tf_minus2=minus2.t)
    return Section(name=case.section_name, type=custom.type.value, area=p["area"], d=custom.d, h=p["h"], tw=custom.tw, ho=p["ho"],
                   bf=plus2.b, tf=plus2.t, bf_minus2=minus2.b, tf_minus2=minus2.t, ix=p["ix"], iy=p["iy"],
                   sx=min(p["sx_plus2"], p["sx_minus2"]), sy=p["sy"], zx=p["zx"], zy=p["zy"], rx=math.sqrt(p["ix"] / p["area"]),
                   ry=math.sqrt(p["iy"] / p["area"]), j=p["j"], cw=p["cw"], ro=p["ro"], H=p["H"], h_tw_ratio=p["h"] / custom.tw)


def build_custom_section(case: SteelCase) -> Section:
    custom = case.custom_section
    if custom is None:
        raise ValidationError("custom_section is required to build a custom section.")
    if custom.type == CustomSectionType.I_BUILT_UP:
        return _built_up_i(case)
    if custom.type == CustomSectionType.SOLID_CIRCULAR:
        d = custom.diameter
        inertia = math.pi * d**4 / 64.0
        s, z = math.pi * d**3 / 32.0, d**3 / 6.0
        return Section(name=case.section_name, type=custom.type.value, area=math.pi * d**2 / 4.0, od=d,
                       ix=inertia, iy=inertia, rx=d / 4.0, ry=d / 4.0, sx=s, sy=s, zx=z, zy=z)
    h, b = custom.H, custom.B
    area = b * h
    ix, iy = b * h**3 / 12.0, h * b**3 / 12.0
    return Section(name=case.section_name, type=custom.type.value, area=area, h=h, b=b,
                   ix=ix, iy=iy, rx=math.sqrt(ix / area), ry=math.sqrt(iy / area),
                   sx=b * h**2 / 6.0, sy=h * b**2 / 6.0, zx=b * h**2 / 4.0, zy=h * b**2 / 4.0)
