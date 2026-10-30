"""ANSI/AISC 360-22 Chapter E formulations (and Table B4.1a limits).

Pure functions: no section families, no selection, no case objects. Each
function implements one equation group and returns the equation identifier
actually applied. Units: N, mm, MPa. Selection lives in domain/compression.py.
"""
import math

from ...design_methods import require_design_method


E_STEEL = 200000.0   # MPa, S22 E3 (definition of E)
G_STEEL = 77200.0    # MPa, S22 E4 (definition of G)
PHI_C = 0.90         # S22 E1, LRFD
OMEGA_C = 1.67       # S22 E1, ASD

# Table B4.1a, members subjected to axial compression: case -> (coefficient, form)
_B41A = {
    1: (0.56, "sqrt"),   # flanges of rolled I, channels; legs of 2L in continuous contact
    3: (0.45, "sqrt"),   # legs of single angles, 2L with separators, other unstiffened
    5: (1.49, "sqrt"),   # webs of doubly symmetric I and channels
    6: (1.40, "sqrt"),   # walls of rectangular HSS
    9: (0.11, "linear"), # round HSS, D/t
}

# Table E7.1, effective width imperfection adjustment factor c1
E7_C1 = {"STIFFENED": 0.18, "HSS_WALL": 0.20, "UNSTIFFENED": 0.22}


def _positive(**values):
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive, got {value!r}")


def lambda_r(case: int, E: float, Fy: float) -> float:
    """Table B4.1a limiting width-to-thickness ratio (nonslender/slender)."""
    _positive(E=E, Fy=Fy)
    coefficient, form = _B41A[case]
    return coefficient * (E / Fy if form == "linear" else math.sqrt(E / Fy))


def elastic_flexural_stress(E: float, Lc: float, r: float) -> float:
    """E3-4 (same expression as E4-5/E4-6 for each principal axis): pi^2 E / (Lc/r)^2."""
    _positive(E=E, Lc=Lc, r=r)
    return math.pi**2 * E / (Lc / r) ** 2


def nominal_stress(Fy: float, Fe: float) -> dict:
    """E3-2 (Fy/Fe <= 2.25) or E3-3. Shared by E3, E4 and E7 (Fn)."""
    _positive(Fy=Fy, Fe=Fe)
    ratio = Fy / Fe
    if ratio <= 2.25:
        return {"Fn_mpa": 0.658**ratio * Fy, "equation": "E3-2", "Fy_over_Fe": ratio}
    return {"Fn_mpa": 0.877 * Fe, "equation": "E3-3", "Fy_over_Fe": ratio}


def torsional_stress_doubly_symmetric(*, E, G, Cw, J, Lcz, Ix, Iy) -> float:
    """E4-2: doubly symmetric members twisting about the shear center. Cw >= 0."""
    _positive(E=E, G=G, J=J, Lcz=Lcz, Ix=Ix, Iy=Iy)
    if not math.isfinite(Cw) or Cw < 0:
        raise ValueError("Cw must be finite and non-negative")
    return (math.pi**2 * E * Cw / Lcz**2 + G * J) / (Ix + Iy)


def torsional_stress(*, E, G, Cw, J, Lcz, Ag, ro) -> float:
    """E4-7 (Fez), ro = polar radius of gyration about the shear center (E4-9)."""
    _positive(E=E, G=G, J=J, Lcz=Lcz, Ag=Ag, ro=ro)
    if not math.isfinite(Cw) or Cw < 0:
        raise ValueError("Cw must be finite and non-negative")
    return (math.pi**2 * E * Cw / Lcz**2 + G * J) / (Ag * ro**2)


def flexural_torsional_stress_singly_symmetric(Fe_symmetry: float, Fez: float, H: float) -> float:
    """E4-3 with Fe_symmetry = flexural stress about the axis of symmetry.

    Fey when y is the symmetry axis; Fex for channels (E4 User Note). The
    rationalized form avoids cancellation of nearly equal terms for small H.
    """
    _positive(Fe_symmetry=Fe_symmetry, Fez=Fez)
    if not math.isfinite(H) or not 0.0 < H <= 1.0:
        raise ValueError("E4-3 requires 0 < H <= 1")
    scale = max(Fe_symmetry, Fez)
    a, b = Fe_symmetry / scale, Fez / scale
    return scale * 2 * a * b / (a + b + math.sqrt((a - b) ** 2 + 4 * a * b * (1 - H)))


def flexural_torsional_stress_unsymmetric(*, Fex, Fey, Fez, xo, yo, ro) -> dict:
    """E4-4: lowest root of the cubic, principal axes, shear-center coordinates (mm).

    In 0 < z < min(Fex, Fey, Fez) the secular form of the cubic is strictly
    decreasing, so the bisection bracket contains the lowest root only.
    """
    _positive(Fex=Fex, Fey=Fey, Fez=Fez, ro=ro)
    alpha, beta = (xo / ro) ** 2, (yo / ro) ** 2
    if alpha + beta >= 1:
        raise ValueError("E4-8 requires H = 1 - (xo^2 + yo^2)/ro^2 > 0")
    scale = max(Fex, Fey, Fez)
    a, b, c = Fex / scale, Fey / scale, Fez / scale

    def cubic(z):
        return (a - z) * (b - z) * (c - z) - z * z * (b - z) * alpha - z * z * (a - z) * beta

    lo, hi = 0.0, min(a, b, c)
    for _ in range(200):
        mid = (lo + hi) / 2
        if mid in (lo, hi):
            break
        lo, hi = (mid, hi) if cubic(mid) > 0 else (lo, mid)
    return {"Fe_mpa": (lo + hi) / 2 * scale, "H": 1 - alpha - beta, "equation": "E4-4"}


def torsional_stress_bracing_offset(*, E, G, J, Iy, Ix, Ag, rx, ry, ho, Lcz, xa, ya) -> dict:
    """E4-10 (minor-axis bracing offset ya, xa=0) or E4-12 (major-axis offset xa, ya=0).

    Doubly symmetric I-shaped members only; ro^2 from E4-11. Offsets in both
    directions are E4(f) (analysis required) and are rejected.
    """
    _positive(E=E, G=G, J=J, Iy=Iy, Ix=Ix, Ag=Ag, rx=rx, ry=ry, ho=ho, Lcz=Lcz)
    if xa == 0 and ya > 0:
        arm, equation = ho**2 / 4 + ya**2, "E4-10"
    elif ya == 0 and xa > 0:
        arm, equation = ho**2 / 4 + (Ix / Iy) * xa**2, "E4-12"
    else:
        raise ValueError("E4(f): offsets in both directions require an elastic buckling analysis")
    ro2 = rx**2 + ry**2 + xa**2 + ya**2
    return {"Fe_mpa": (math.pi**2 * E * Iy / Lcz**2 * arm + G * J) / (Ag * ro2),
            "ro2_mm2": ro2, "equation": equation}


def e5_effective_slenderness(*, L_over_ra: float, configuration: str, connected_leg: str,
                             leg_ratio: float, L_over_rz: float) -> dict:
    """E5(a) E5-1/E5-2 or E5(b) E5-3/E5-4, with the shorter-leg increase and floor.

    configuration "a": individual members / planar trusses; "b": box or space
    trusses. connected_leg: "long" or "short" (equal legs use "long").
    Eligibility conditions (1)-(5) belong to the caller; (4) is returned.
    """
    _positive(L_over_ra=L_over_ra, leg_ratio=leg_ratio, L_over_rz=L_over_rz)
    s = L_over_ra
    if configuration == "a":
        base, equation = (72 + 0.75 * s, "E5-1") if s <= 80 else (32 + 1.25 * s, "E5-2")
        coefficient, floor_factor = 4, 0.95
    elif configuration == "b":
        base, equation = (60 + 0.8 * s, "E5-3") if s <= 75 else (45 + s, "E5-4")
        coefficient, floor_factor = 6, 0.82
    else:
        raise ValueError("E5 configuration must be 'a' or 'b'")
    if connected_leg == "short" and leg_ratio > 1:
        value = max(base + coefficient * (leg_ratio**2 - 1), floor_factor * L_over_rz)
    elif connected_leg in {"long", "short"}:
        value = base
    else:
        raise ValueError("connected_leg must be 'long' or 'short'")
    return {"Lc_over_r": value, "equation": equation, "within_200": value <= 200}


def e6_modified_slenderness(*, Lc_over_r_o: float, a_over_ri: float, connector: str, Ki: float) -> dict:
    """E6-1 (snug-tight) or E6-2a/E6-2b (welded / pretensioned Class A or B)."""
    _positive(Lc_over_r_o=Lc_over_r_o, a_over_ri=a_over_ri, Ki=Ki)
    if connector == "snug_tight":
        return {"Lc_over_r_m": math.hypot(Lc_over_r_o, a_over_ri), "equation": "E6-1"}
    if connector in {"welded", "pretensioned"}:
        if a_over_ri <= 40:
            return {"Lc_over_r_m": Lc_over_r_o, "equation": "E6-2a"}
        return {"Lc_over_r_m": math.hypot(Lc_over_r_o, Ki * a_over_ri), "equation": "E6-2b"}
    raise ValueError("connector must be 'snug_tight', 'welded' or 'pretensioned'")


def e7_effective_width(*, b: float, t: float, lambda_r: float, Fn: float, Fy: float, kind: str) -> dict:
    """E7-2/E7-3 with c1 from Table E7.1 and c2 from E7-4 (unrounded), Fel E7-5."""
    _positive(b=b, t=t, lambda_r=lambda_r, Fn=Fn, Fy=Fy)
    c1 = E7_C1[kind]
    c2 = 2 / (1 + math.sqrt(1 - 4 * c1))  # E7-4, rationalized; not the rounded table value
    ratio = b / t
    fel = (c2 * lambda_r / ratio) ** 2 * Fy
    if ratio <= lambda_r * math.sqrt(Fy / Fn):
        be, equation = b, "E7-2"
    else:
        z = math.sqrt(fel / Fn)
        be, equation = b * (1 - c1 * z) * z, "E7-3"
    return {"b_mm": b, "t_mm": t, "lambda": ratio, "lambda_r": lambda_r, "c1": c1, "c2": c2,
            "Fel_mpa": fel, "be_mm": be, "area_loss_mm2": (b - be) * t, "equation": equation}


def e7_round_hss_area(*, Ag: float, D_over_t: float, E: float, Fy: float) -> dict:
    """E7-6/E7-7 for round HSS (D outside diameter, t design thickness).

    Engineering criterion confirmed by the user (docs/chapter-e.md, decision D-2): Ae <= Ag,
    because literal E7-7 exceeds Ag for 0.11E/Fy < D/t < 0.114E/Fy.
    """
    _positive(Ag=Ag, D_over_t=D_over_t, E=E, Fy=Fy)
    if D_over_t <= 0.11 * E / Fy:
        return {"Ae_mm2": Ag, "Ae_equation_mm2": Ag, "equation": "E7-6", "bounded_to_Ag": False}
    if D_over_t >= 0.45 * E / Fy:
        raise ValueError("E7.2 requires D/t < 0.45E/Fy")
    ae = (0.038 * E / (Fy * D_over_t) + 2 / 3) * Ag
    return {"Ae_mm2": min(ae, Ag), "Ae_equation_mm2": ae, "equation": "E7-7", "bounded_to_Ag": ae > Ag}


def available_strength(Pn_N: float) -> dict:
    """E1: phi_c*Pn (LRFD) and Pn/Omega_c (ASD), in kN."""
    return {"LRFD": PHI_C * Pn_N / 1000.0, "ASD": Pn_N / OMEGA_C / 1000.0}


def design_factor(method) -> dict:
    method = require_design_method(method).value
    if method == "LRFD":
        return {"design_method": method, "phi": PHI_C, "omega": None, "capacity_expression": "phi*Pn"}
    return {"design_method": method, "phi": None, "omega": OMEGA_C, "capacity_expression": "Pn/omega"}
