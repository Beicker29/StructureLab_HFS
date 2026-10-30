"""Product vs AISC Design Examples v16.0 (Companion Vol. 1, v16.0_vol-1_design-examples.pdf), LRFD.

The examples use US units, E = 29000 ksi and properties rounded to three figures; the program uses
the metric catalog (AISC v16 metric) and E = 200000 MPa. Agreement is therefore checked with a
tolerance, not to the digit. Sections absent from the catalog (HSS, Pipe) are built from the
properties printed in the example, converted to SI; nothing else is assumed.
"""
import math

import pytest

from steel_design.engine import SteelDesignEngine
from steel_design.models import SteelCase
from steel_design.sections.models import Section
from steel_design.sections.repository import SectionRepository

IN, KSI, KIP, KIPFT = 25.4, 6.894757293168361, 4.4482216152605, 1.3558179483314004
FT = 12 * IN
FY50, FY35 = 50 * KSI, 35 * KSI
TOL = 0.015         # rounding of the examples, metric catalog, E = 29000 ksi vs 200000 MPa


def rect_hss(name, *, A, t, B, H, b_t, h_t, rx=None, ry=None, Sx=None, Zx=None, J=None, Iy=None, Zy=None):
    """HSS from the example's Manual Table 1-11/1-12 values (inches)."""
    data = dict(name=name, type="RECTANGULAR_HSS", A=A * IN**2, tdes=t * IN, Ht=H * IN, B=B * IN,
                b=b_t * t * IN, h=h_t * t * IN, **{"b/tdes": b_t, "h/tdes": h_t})
    data.update({k: v for k, v in dict(rx=rx and rx * IN, ry=ry and ry * IN, Sx=Sx and Sx * IN**3,
                                       Zx=Zx and Zx * IN**3, J=J and J * IN**4, Iy=Iy and Iy * IN**4,
                                       Zy=Zy and Zy * IN**3).items() if v})
    if Sx:
        data["Ix"] = Sx * H / 2 * IN**4                     # I = S·c, consistent with the printed S
    return Section(**data)


def rounded_hss_area(B, H, t):
    """Manual Part 1: outside corner radius 2t (used only where the example omits Ag)."""
    return B * H - (4 - math.pi) * (2 * t) ** 2 - ((B - 2 * t) * (H - 2 * t) - (4 - math.pi) * t**2)


def pipe(name, *, OD, t, A=None, r=None):
    """Pipe from OD and design thickness; S and Z from the annulus (Z checked against the example)."""
    d = OD - 2 * t
    data = dict(name=name, type="CIRCULAR_HSS", OD=OD * IN, tdes=t * IN, **{"D/t": OD / t},
                Sx=math.pi * (OD**4 - d**4) / (32 * OD) * IN**3, Zx=(OD**3 - d**3) / 6 * IN**3)
    data.update(Sy=data["Sx"], Zy=data["Zx"])
    if A:
        data.update(A=A * IN**2, rx=r * IN, ry=r * IN)
    else:
        data["A"] = math.pi / 4 * (OD**2 - d**2) * IN**2
    return Section(**data)


EXTRA = [
    rect_hss("HSS6X4X3/8", A=6.18, t=0.349, B=4, H=6, b_t=8.46, h_t=14.2, ry=1.55),
    rect_hss("HSS10X6X3/8", A=10.4, t=0.349, B=6, H=10, b_t=14.2, h_t=25.7, Sx=137 / 5, Zx=33.8, Iy=61.8),
    rect_hss("BOX30X30X1/2", A=59.0, t=0.5, B=30, H=30, b_t=58, h_t=58, Sx=8600 / 15, Zx=(30**3 - 29**3) / 4, Iy=8600,
             Zy=(30**3 - 29**3) / 4),
    rect_hss("BOX30X30X1/4", A=29.8, t=0.25, B=30, H=30, b_t=118, h_t=118, Sx=4400 / 15, Zx=(30**3 - 29.5**3) / 4, Iy=4400,
             Zy=(30**3 - 29.5**3) / 4),
    rect_hss("HSS12X10X3/8", A=14.6, t=0.349, B=10, H=12, b_t=25.7, h_t=31.4, rx=4.61, ry=4.01),
    rect_hss("HSS12X8X3/16", A=6.76, t=0.174, B=8, H=12, b_t=43.0, h_t=66.0, rx=4.56, ry=3.35),
    rect_hss("HSS10X6X3/16", A=5.37, t=0.174, B=6, H=10, b_t=31.5, h_t=54.5, ry=2.52, Sx=14.9, Zx=18.0, J=73.8),
    rect_hss("HSS8X8X3/16", A=rounded_hss_area(8, 8, 0.174), t=0.174, B=8, H=8, b_t=43.0, h_t=43.0,
             Sx=13.6, Zx=15.7),
    pipe("HSS6.000X0.500", OD=6.0, t=0.465, A=8.09, r=1.96),
    pipe("PIPE10STD", OD=10.75, t=0.340, A=11.5, r=3.68),
    pipe("PIPE8XS", OD=8.625, t=0.465),
    pipe("HSS16.000X0.375", OD=16.0, t=16.0 / 45.8, A=17.2, r=5.53),
]

E6_WELDED = dict(connectors="welded", a=32 * IN, end_connection_welded_or_pretensioned=True)
E5_LONG = dict(configuration="a", connected_leg="long", L=5 * FT, loaded_at_ends_through_same_leg=True,
               welded_or_two_bolts_min=True, no_intermediate_transverse_loads=True)


def tension(name, Fy, Fu, An, U):
    return dict(section_name=name, material={"Fy": Fy * KSI, "Fu": Fu * KSI}, Pu=-1.0,
                tension={"An": An * IN**2, "U": U})


def column(name, Fy, Lx, Ly, Lz, K=1.0, **extra):
    return dict(section_name=name, material={"Fy": Fy}, Pu=1.0,
                lengths={"Lx": Lx * FT, "Ly": Ly * FT, "Lz": Lz * FT}, factors={"Kx": K, "Ky": K, "Kz": K}, **extra)


def beam(name, Fy, Lb=None, Cb=1.0, axis="Mux", holes=False, **extra):
    flexure = {"Cb": Cb, **({"Lb": Lb * FT} if Lb else {}), **({"tension_flange_holes": False} if holes is False else {})}
    flexure.update(extra.pop("flexure", {}))
    return dict(section_name=name, material={"Fy": Fy}, flexure=flexure, **{axis: 1.0}, **extra)


def shear(name, Fy, axis="Vux", **extra):
    return dict(section_name=name, material={"Fy": Fy}, **{axis: 1.0}, **extra)


def combined(name, Fy, L, Pu, Mux, Muy, Cb=1.0, **extra):
    flexure = {"Lb": L * FT, "Cb": Cb, "tension_flange_holes": False, **extra.pop("flexure", {})}
    return dict(section_name=name, material={"Fy": Fy, **extra.pop("material", {})}, Pu=Pu * KIP, Mux=Mux * KIPFT,
                Muy=Muy * KIPFT, lengths={"Lx": L * FT, "Ly": L * FT, "Lz": L * FT}, flexure=flexure, **extra)


CONTINUOUS = 0.5   # ft: continuously braced (Lb below Lp)
WC = 2323.0        # 145 lb/ft3
F5 = 5 * KSI


def filled_member(name, fc_ksi, L=None, interaction="H1", **demands):
    data = dict(section_name=name, material={"Fy": FY50}, **demands,
                composite={"kind": "filled", "interaction": interaction,
                           "concrete": {"fc": fc_ksi * KSI, "wc": WC, "lightweight": False}})
    if L:
        data["lengths"] = {"Lx": L * FT, "Ly": L * FT, "Lz": L * FT}
    return data


def encased_member(L=None, method="steel", interaction="H1", anchor=None, **demands):
    """Examples I.9 to I.11: eight No. 8 bars at 9.5 in; ties No. 3 at 12 in (10 mm at 300 mm, the metric limit)."""
    e = 9.5 * IN
    positions = [(e, e), (e, 0.0), (e, -e), (0.0, e), (0.0, -e), (-e, e), (-e, 0.0), (-e, -e)]
    bars = [{"area": 0.79 * IN**2, "db": 1.0 * IN, "x": x, "y": y} for x, y in positions]
    data = dict(section_name="W10X45", material={"Fy": FY50}, **demands,
                composite={"kind": "encased", "interaction": interaction, "anchor": anchor,
                           "concrete": {"fc": F5, "wc": WC, "lightweight": False},
                           "encased": {"H": 24 * IN, "B": 24 * IN, "Fysr": 60 * KSI, "bars": bars,
                                       "transverse": {"db": 10, "spacing": 300}, "flexure_method": method,
                                       "anchors_provided": method == "composite"}})
    if L:
        data["lengths"] = {"Lx": L * FT, "Ly": L * FT, "Lz": L * FT}
    return data


def composite_beam(name):
    """Example I.1: 22 studs give ΣQn = 381 kips; the example selects PNA 5 with 386 kips (no integer stud count)."""
    beam = {"moment": "positive", "span": 45 * FT, "left_beam_spacing": 10 * FT, "right_beam_spacing": 10 * FT,
            "tc": 4.5 * IN, "shored": True,
            "deck": {"orientation": "perpendicular", "hr": 3 * IN, "wr": 6 * IN, "emid_ht_at_least_50": False},
            "studs": {"count": 22, "d": 0.75 * IN, "Fu": 65 * KSI, "length": 4.5 * IN, "over_web": True}}
    return dict(section_name=name, material={"Fy": FY50}, Mux=1.0,
                composite={"kind": "beam", "concrete": {"fc": 4 * KSI, "wc": WC, "lightweight": False}, "beam": beam})


# Example E.14B at the strength it prints, Pu = 85.9 kips: Mr = Pu*e*B1, with B1 from its Pe1w and Pe1z (kip-in).
E14B_PU = 85.9
E14B = dict(section_name="L8X4X1/2", material={"Fy": FY50}, Pu=E14B_PU * KIP,
            Mw=1.44 * E14B_PU / (1 - E14B_PU / 3260) * KIPFT / 12, Mz=0.889 * E14B_PU / (1 - E14B_PU / 343) * KIPFT / 12,
            lengths={"Lx": 5 * FT, "Ly": 5 * FT, "Lz": 5 * FT}, flexure={"Lb": 5 * FT, "beta_w": 5.48 * IN},
            angle_flexure={"leg_in_compression": "long", "toe": "tension"})

# id: (example, page, case data, check id, LRFD design strength printed in the example, unit, note)
EXAMPLES = {
    "D.1": ("W8X21, rotura en conexión", tension("W8X21", 50, 65, 4.76, 0.908), "axial", 211, "kip"),
    "D.2": ("L4X4X1/2, rotura", tension("L4X4X1/2", 50, 65, 3.31, 0.869), "axial", 140, "kip"),
    "D.4": ("HSS6X4X3/8, rotura", tension("HSS6X4X3/8", 50, 62, 5.79, 0.919), "axial", 248, "kip"),
    "D.5": ("HSS6.000X0.500, rotura", tension("HSS6.000X0.500", 50, 62, 7.57, 0.991), "axial", 349, "kip"),
    "D.6": ("2L4X4X1/2 (s = 3/8 in), rotura", tension("2L4X4X1/2X3/8", 50, 65, 6.63, 0.944), "axial", 305, "kip"),
    "E.1C": ("W14X132, Lc = 30 ft", column("W14X132", FY50, 30, 30, 30), "axial", 892, "kip"),
    "E.1D": ("W14X90, Lcx = 30 ft, Lcy = Lcz = 15 ft", column("W14X90", FY50, 30, 15, 15), "axial", 927, "kip"),
    "E.1E-a": ("W16X31 alma esbelta (E7), Lc = 5 ft", column("W16X31", FY50, 5, 5, 5), "axial", 314, "kip"),
    "E.1E-b": ("W16X31, Lc = 10 ft", column("W16X31", FY50, 10, 10, 10), "axial", 189, "kip"),
    "E.1E-c": ("W16X31, Lc = 15 ft", column("W16X31", FY50, 15, 15, 15), "axial", 87.1, "kip"),
    "E.5": ("2L4X3-1/2X3/8LLBB (s = 3/4 in), L = 8 ft, E6",
            column("2L4X3-1/2X3/8X3/4LLBB", FY50, 8, 8, 8, double_angle_e6=E6_WELDED), "axial", 157, "kip"),
    "E.9": ("HSS12X10X3/8, K = 0.8, L = 20 ft", column("HSS12X10X3/8", FY50, 20, 20, 20, K=0.8), "axial", 556, "kip"),
    "E.10": ("HSS12X8X3/16 paredes esbeltas (E7), Lc = 24 ft", column("HSS12X8X3/16", FY50, 24, 24, 24),
             "axial", 151, "kip"),
    "E.10-18ft": ("HSS12X8X3/16, Lc = 18 ft (Tabla E.10-1)", column("HSS12X8X3/16", FY50, 18, 18, 18),
                  "axial", 177, "kip"),
    "E.10-40ft": ("HSS12X8X3/16, Lc = 40 ft (Tabla E.10-1)", column("HSS12X8X3/16", FY50, 40, 40, 40),
                  "axial", 74.8, "kip"),
    "E.11": ("Pipe 10 Std, Fy = 35 ksi, Lcx = 30 ft, Lcy = 15 ft", column("PIPE10STD", FY35, 30, 15, 15),
             "axial", 221, "kip"),
    "E.14A": ("L5X3X1/2, E5(a) ala larga, L = 5 ft", column("L5X3X1/2", FY50, 5, 5, 5, single_angle_e5=E5_LONG),
              "axial", 52.3, "kip"),
    "F.1-1B": ("W18X50, arriostramiento continuo", beam("W18X50", FY50, CONTINUOUS), "flexure_x", 379, "kip-ft"),
    "F.1-2B": ("W18X50, Lb = 11.67 ft, Cb = 1.01", beam("W18X50", FY50, 35 / 3, 1.01), "flexure_x", 304, "kip-ft"),
    "F.1-3B": ("W18X50, Lb = 17.5 ft, Cb = 1.30", beam("W18X50", FY50, 17.5, 1.30), "flexure_x", 288, "kip-ft"),
    "F.2-1B": ("C15X33.9, arriostramiento continuo", beam("C15X33.9", FY50, CONTINUOUS), "flexure_x", 191, "kip-ft"),
    "F.2-2B": ("C15X33.9, Lb = 5 ft", beam("C15X33.9", FY50, 5), "flexure_x", 173, "kip-ft"),
    "F.3B": ("W21X48 ala no compacta (F3)", beam("W21X48", FY50, CONTINUOUS), "flexure_x", 398, "kip-ft"),
    "F.5": ("W12X58, eje menor (F6)", beam("W12X58", FY50, axis="Muy", holes=None), "flexure_y", 122, "kip-ft"),
    "F.7B": ("HSS10X6X3/16 ala no compacta, Lb = 21 ft, Cb = 1.14", beam("HSS10X6X3/16", FY50, 21, 1.14, holes=None),
             "flexure_x", 59.7, "kip-ft"),
    "F.8B": ("HSS8X8X3/16 ala esbelta (F7-3)", beam("HSS8X8X3/16", FY50, holes=None), "flexure_x", 45.4, "kip-ft"),
    "F.9B": ("Pipe 8 XS, Fy = 35 ksi", beam("PIPE8XS", FY35, holes=None), "flexure_x", 81.4, "kip-ft"),
    "F.11A": ("L4X4X1/4 eje x, sin restricción, Lb = 6 ft, Cb = 1.14",
              beam("L4X4X1/4", FY50, 6, 1.14, holes=None, flexure={"lateral_torsional_restraint": "none"},
                   angle_flexure={"toe": "compression"}), "flexure_x", 3.69, "kip-ft"),
    "F.11B": ("L4X4X1/4 eje x, restricción en Mmáx, Lb = 3 ft, Cb = 1.30",
              beam("L4X4X1/4", FY50, 3, 1.30, holes=None, flexure={"lateral_torsional_restraint": "at_max_moment"},
                   angle_flexure={"toe": "compression"}), "flexure_x", 3.98, "kip-ft"),
    "F.11C-z": ("L4X4X1/4 eje z, punteras comprimidas",
                beam("L4X4X1/4", FY50, 6, 1.14, axis="Mz", holes=None, angle_flexure={"toe": "compression"}),
                "flexure_z", 4.13, "kip-ft"),
    "F.11C-w": ("L4X4X1/4 eje w, Lb = 6 ft, Cb = 1.14",
                beam("L4X4X1/4", FY50, 6, 1.14, axis="Mw", holes=None), "flexure_w", 7.49, "kip-ft"),
    "F.12": ("Barra 5 x 3 in, Lb = 6 ft", beam("BAR", FY50, 6, holes=None,
             custom_section={"type": "SOLID_RECTANGULAR", "H": 5 * IN, "B": 3 * IN}), "flexure_x", 70.4, "kip-ft"),
    "F.13": ("Barra redonda D = 1 in, Lb = 2.5 ft", beam("ROUND", FY50, 2.5, holes=None,
             custom_section={"type": "SOLID_CIRCULAR", "diameter": 1 * IN}), "flexure_x", 0.590, "kip-ft"),
    "G.1B": ("W24X62, cortante en el alma, G2.1(a) φv = 1.00", shear("W24X62", FY50), "shear_x", 306, "kip"),
    "G.2B": ("C15X33.9, cortante en el alma, G2.1(b)", shear("C15X33.9", FY50), "shear_x", 162, "kip"),
    "G.3": ("L5X3X1/4, ala larga vertical (G3)", shear("L5X3X1/4", FY50), "shear_x", 33.8, "kip"),
    "G.4": ("HSS6X4X3/8, paredes anchas verticales (G4)", shear("HSS6X4X3/8", FY50), "shear_x", 93.6, "kip"),
    "G.5": ("HSS16.000X0.375, Lv = 192 in (G5)", shear("HSS16.000X0.375", FY50, shear={"Lv": 192 * IN}),
            "shear_x", 232, "kip"),
    "G.6": ("W21X48, cortante en el eje menor (G6)", shear("W21X48", FY50, "Vuy"), "shear_y", 189, "kip"),
    "G.7": ("C9X20, cortante en el eje menor (G6)", shear("C9X20", FY50, "Vuy"), "shear_y", 59.1, "kip"),
    "H.1B": ("W14X99, Pu = 400 kips, Mux = 250, Muy = 80 kip-ft, L = 14 ft (H1-1a)",
             combined("W14X99", FY50, 14, 400, 250, 80), "interaction", 0.929, "ratio"),
    "H.3": ("W14X82 en tracción, Pu = 174 kips, Mux = 192, Muy = 67.6 kip-ft, Lb = 30 ft, Cb amplificado (H1.2)",
            combined("W14X82", FY50, 30, -174, 192, 67.6, Cb=1.14, flexure={"tension_cb_amplification": True},
                     material={"Fu": 65 * KSI}, tension={"An": 24.0 * IN**2, "U": 1.0}), "interaction", 0.873, "ratio"),
    "H.4": ("W10X33, Pu = 30 kips, Mux = 91.8, Muy = 13.1 kip-ft (amplificados por el ejemplo), L = 14 ft",
            combined("W10X33", FY50, 14, 30, 91.8, 13.1, Cb=1.14), "interaction", 0.979, "ratio"),
    "I.1": ("W21X50, deck de 3 in perpendicular, 22 pernos de 3/4 in, tc = 4.5 in, f'c = 4 ksi (ejemplo: ΣQn = 386 kips)",
            composite_beam("W21X50"), "flexure_x", 769, "kip-ft"),
    "I.4": ("HSS10X6X3/8 relleno, f'c = 5 ksi, Lc = 14 ft", filled_member("HSS10X6X3/8", 5, Pu=1.0, L=14),
            "axial", 368, "kip"),
    "I.5": ("HSS10X6X3/8 relleno, tracción", filled_member("HSS10X6X3/8", 5, Pu=-1.0), "axial", 468, "kip"),
    "I.6-Mc": ("HSS10X6X3/8 relleno, flexión compacta (Tabla 4-B)", filled_member("HSS10X6X3/8", 5, Mux=1.0),
               "flexure_x", 141, "kip-ft"),
    "I.6-Vc": ("HSS10X6X3/8 relleno, cortante I4-1, Kc = 1", filled_member("HSS10X6X3/8", 5, Vux=1.0), "shear_x", 176, "kip"),
    "I.6-H1": ("HSS10X6X3/8 relleno, Pu = 129 kips, Mux = 120 kip-ft, H1-1a",
               filled_member("HSS10X6X3/8", 5, Pu=129 * KIP, Mux=120 * KIPFT, L=14), "interaction", 1.11, "ratio"),
    "I.7-noncompact": ("Cajón 30 x 30 x 1/2 in relleno, no compacto (I3-5b)", filled_member("BOX30X30X1/2", 7, Mux=1.0),
                       "flexure_x", 2910, "kip-ft"),
    "I.7-slender": ("Cajón 30 x 30 x 1/4 in relleno, esbelto (Fig. C-I3.8(c))", filled_member("BOX30X30X1/4", 7, Mux=1.0),
                    "flexure_x", 1220, "kip-ft"),
    "I.7-slender-Pc": ("Cajón 30 x 30 x 1/4 in relleno, esbelto, Lc = 30 ft (I2-9e)",
                       filled_member("BOX30X30X1/4", 7, Pu=1.0, L=30), "axial", 3300, "kip"),
    "I.9": ("W10X45 embebido en 24 x 24 in, 8 barras No. 8, Lc = 14 ft", encased_member(Pu=1.0, L=14), "axial", 2360, "kip"),
    "I.10": ("W10X45 embebido, tracción (I2-8)", encased_member(Pu=-1.0), "axial", 936, "kip"),
    "I.11-Mc": ("W10X45 embebido, plástico compuesto I3.3a(3)", encased_member(Mux=1.0, method="composite"),
                "flexure_x", 673, "kip-ft"),
    "I.11-H1": ("W10X45 embebido, Pu = 1170 kips, Mux = 670 kip-ft, H1-1a",
                encased_member(Pu=1170 * KIP, Mux=670 * KIPFT, L=14, method="composite"), "interaction", 1.38, "ratio"),
    "I.6-M2S": ("HSS10X6X3/8 relleno, Pu = 129 kips, Mux = 120 kip-ft, Método 2 simplificado (C-I5-1b)",
                filled_member("HSS10X6X3/8", 5, Pu=129 * KIP, Mux=120 * KIPFT, L=14, interaction="M2S"),
                "interaction", 0.948, "ratio"),
    "I.6-M2": ("HSS10X6X3/8 relleno, igual, Método 2 (razón obtenida con los puntos impresos en el ejemplo)",
               filled_member("HSS10X6X3/8", 5, Pu=129 * KIP, Mux=120 * KIPFT, L=14, interaction="M2"),
               "interaction", 0.963, "ratio"),
    "I.11-M2S": ("W10X45 embebido, Pu = 1170 kips, Mux = 670 kip-ft, Método 2 simplificado (C-I5-1a)",
                 encased_member(Pu=1170 * KIP, Mux=670 * KIPFT, L=14, method="composite", interaction="M2S"),
                 "interaction", 0.996, "ratio"),
    "I.11-M2": ("W10X45 embebido, igual, Método 2 (razón obtenida con los puntos impresos en el ejemplo)",
                encased_member(Pu=1170 * KIP, Mux=670 * KIPFT, L=14, method="composite", interaction="M2"),
                "interaction", 0.870, "ratio"),
    "I.12": ("Perno de 3/4 in, Quv = 10.4 kips, Qut = 15.6 kips (I8-5)",
             encased_member(anchor={"type": "stud", "Qrv": 10.4 * KIP, "Qrt": 15.6 * KIP, "spacing": 24 * IN, "d": 0.75 * IN,
                                    "Fu": 65 * KSI, "height": 6 * IN, "head_diameter": 1.25 * IN, "breakout_in_shear": False,
                                    "base_thickness": 1 * IN}),
             "anchor", 0.962, "ratio"),
    "E.14B-Pc": ("L8X4X1/2 fuera de E5, Lc = 5 ft, ala larga esbelta (E7)", E14B, "axial", 168, "kip"),
    "E.14B-Mcw": ("L8X4X1/2 eje w, punta del ala larga comprimida, βw = −5.48 in", E14B, "flexure_w", 375 / 12, "kip-ft"),
    "E.14B-Mcz": ("L8X4X1/2 eje z, punteras traccionadas, fluencia en A", E14B, "flexure_z", 123 / 12, "kip-ft"),
    "E.14B": ("L8X4X1/2, Pu = 85.9 kips con Mw y Mz amplificados: H2-1 en B ≈ 1.0", E14B, "interaction", 1.0, "ratio"),
    "F.11C": ("L4X4X1/4, Muw = 0.286, Muz = 1.05 kip-ft, Lb = 6 ft, Cb = 1.14: H2-1 en la punta comprimida",
              dict(section_name="L4X4X1/4", material={"Fy": FY50}, Mw=0.286 * KIPFT, Mz=1.05 * KIPFT,
                   flexure={"Lb": 6 * FT, "Cb": 1.14}, angle_flexure={"toe": "compression"}),
              "interaction", 0.292, "ratio"),
}

# Differences explained by the example itself (simplified, conservative hand method): program / example
EXPECTED_ABOVE = {
    "F.8B": "el ejemplo descuenta el ancho no efectivo de ambas alas (conservador, lo dice el texto); "
            "el programa usa el eje neutro desplazado (Commentary F7, DF-5)",
    "F.11B": "el ejemplo usa 0.80·Sx en el pandeo local por simplicidad y lo declara conservador; con restricción "
             "en el punto de máximo momento F10.2(2)(ii) no reduce My ni Sc",
}


@pytest.fixture(scope="module")
def examples_engine(catalog):
    repository = SectionRepository()
    repository.load([*catalog, *EXTRA])
    return SteelDesignEngine(repository)


def program_value(engine, data, check_id, unit):
    check = engine.run(SteelCase(**data)).check(check_id)
    assert check.capacity is not None, check.errors
    if unit == "ratio":
        return check.ratio, check
    return check.capacity / (KIP if unit == "kip" else KIPFT), check


@pytest.mark.parametrize("example_id", sorted(set(EXAMPLES) - set(EXPECTED_ABOVE)))
def test_program_matches_design_example(examples_engine, example_id):
    _, data, check_id, expected, unit = EXAMPLES[example_id]
    value, _ = program_value(examples_engine, data, check_id, unit)
    assert value == pytest.approx(expected, rel=TOL), example_id


@pytest.mark.parametrize("example_id", sorted(EXPECTED_ABOVE))
def test_program_is_above_a_declared_conservative_example(examples_engine, example_id):
    _, data, check_id, expected, unit = EXAMPLES[example_id]
    value, _ = program_value(examples_engine, data, check_id, unit)
    assert expected < value < 1.30 * expected, example_id


def test_extra_sections_reproduce_printed_properties():
    by_name = {s.name: s for s in EXTRA}
    assert by_name["PIPE8XS"].zx / IN**3 == pytest.approx(31.0, rel=0.005)            # F.9B: Z = 31.0 in.3
    assert by_name["HSS8X8X3/16"].area / IN**2 == pytest.approx(5.37, rel=0.005)       # Manual Table 1-12


def test_single_angle_yielding_is_not_reduced_by_080(examples_engine):
    # F.11A: Mn = 1.5·Fy·Sx = 6.44 kip-ft (F10-1); 0.80 only reduces My of LTB and Sc of LLB (DF-11)
    _, data, check_id, _, unit = EXAMPLES["F.11A"]
    _, check = program_value(examples_engine, data, check_id, unit)
    modes = check.result["modes"]
    assert modes["Y"]["Mn_kNm"] / KIPFT == pytest.approx(6.44, rel=TOL)
    assert modes["LTB"]["Mn_kNm"] / KIPFT == pytest.approx(4.10, rel=TOL)
    assert modes["LLB"]["Mn_kNm"] / KIPFT == pytest.approx(4.42, rel=TOL)
