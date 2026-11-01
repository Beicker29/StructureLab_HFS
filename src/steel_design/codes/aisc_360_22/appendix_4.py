"""ANSI/AISC 360-22 Appendix 4, Sections 4.2.3b and 4.2.4d: retention factors and simple method. LRFD.

Pure functions; units N, mm, MPa; moments in N*mm; temperatures in deg C. Selection lives in domain/fire.py and in each chapter.
"""
import math

SIMPLE_METHOD_MIN = 200.0   # 4.2.4d: at or below this steel temperature the strengths ignore temperature
FY_MAX = 450.0              # 4.2.3b: Fy of structural and reinforcing steel
FC_MAX = 55.0               # 4.2.3b: f'c
FU_REDUCED_ABOVE = 400.0    # 4.2.3b(a): Fu(T) = Fy(T) above this temperature
# T, kE, kp, ky (Table A-4.2.1)
STEEL = ((20, 1.00, 1.00, 1.00), (93, 1.00, 1.00, 1.00), (200, 0.90, 0.80, 1.00), (320, 0.78, 0.58, 1.00), (400, 0.70, 0.42, 1.00),
         (430, 0.67, 0.40, 0.94), (540, 0.49, 0.29, 0.66), (650, 0.22, 0.13, 0.35), (760, 0.11, 0.06, 0.16), (870, 0.07, 0.04, 0.07),
         (980, 0.05, 0.03, 0.04), (1100, 0.02, 0.01, 0.02), (1200, 0.00, 0.00, 0.00))
# T, kc normal weight, kc lightweight, kEc (Table A-4.2.2)
CONCRETE = ((20, 1.00, 1.00, 1.00), (93, 0.95, 1.00, 0.93), (200, 0.90, 1.00, 0.75), (290, 0.86, 1.00, 0.61),
            (320, 0.83, 0.98, 0.57), (430, 0.71, 0.85, 0.38), (540, 0.54, 0.71, 0.20), (650, 0.38, 0.58, 0.092),
            (760, 0.21, 0.45, 0.073), (870, 0.10, 0.31, 0.055), (980, 0.05, 0.18, 0.036), (1100, 0.01, 0.05, 0.018),
            (1200, 0.00, 0.00, 0.000))
# T, kcb (Table A-4.2.4)
COMPOSITE_BEAM = ((20, 1.00), (150, 0.98), (320, 0.95), (430, 0.89), (540, 0.71), (650, 0.49), (760, 0.26), (870, 0.12), (980, 0.05), (1100, 0.00))


def _interpolate(table, T, column) -> float:
    if T <= table[0][0]:
        return float(table[0][column])
    for low, high in zip(table, table[1:]):
        if T <= high[0]:
            return low[column] + (high[column] - low[column]) * (T - low[0]) / (high[0] - low[0])
    return float(table[-1][column])


def steel_factors(T) -> dict:
    return {"kE": _interpolate(STEEL, T, 1), "kp": _interpolate(STEEL, T, 2), "ky": _interpolate(STEEL, T, 3)}


def concrete_factors(T, *, lightweight) -> dict:
    return {"kc": _interpolate(CONCRETE, T, 2 if lightweight else 1), "kEc": _interpolate(CONCRETE, T, 3)}


def composite_beam_factor(T) -> float:
    """kcb of Table A-4.2.4, by the bottom flange temperature."""
    return _interpolate(COMPOSITE_BEAM, T, 1)


def tensile_strength(*, Fu, Fy_T, T) -> float:
    """4.2.3b(a): Fu(T) = Fy(T) above 400 deg C; at or below it, Fu may be used."""
    return Fy_T if T > FU_REDUCED_ABOVE else Fu


def compression_stress(*, Fy_T, Fe_T) -> dict:
    """A-4-9, in lieu of E3-2 and E3-3."""
    ratio = Fy_T / Fe_T
    return {"Fn_mpa": 0.42 ** math.sqrt(ratio) * Fy_T, "equation": "A-4-9", "Fy_over_Fe": ratio}


def filled_compression(*, Pno_T, Pe_T) -> dict:
    """A-4-11, in lieu of I2-2 and I2-3."""
    return {"Pn": 0.54 ** ((Pno_T / Pe_T) ** 0.3) * Pno_T, "equation": "A-4-11", "Pno_over_Pe": Pno_T / Pe_T}


def wall_compression(*, Pno_T, Pe_T) -> dict:
    """A-4-12, in lieu of I2-2 and I2-3."""
    return {"Pn": 0.32 ** ((Pno_T / Pe_T) ** 0.3) * Pno_T, "equation": "A-4-12", "Pno_over_Pe": Pno_T / Pe_T}


def composite_beam_strength(*, Mn, kcb) -> dict:
    """A-4-20."""
    return {"Mn": kcb * Mn, "equation": "A-4-20"}


def plastic_moment(*, Fy_T, Zx) -> dict:
    """A-4-18."""
    return {"Mn": Fy_T * Zx, "equation": "A-4-18"}


def ltb(*, E_T, Fy, kp, ky, T, Sx, Zx, rts, J, c, ho, Lb, Cb) -> dict:
    """A-4-13 to A-4-19M: lateral-torsional buckling of doubly symmetric compact rolled wide-flange shapes, major axis."""
    Fy_T = ky * Fy
    FL = Fy * (kp - 0.3 * ky)                                                    # A-4-17
    Mp = Fy_T * Zx                                                               # A-4-18
    cx = min(0.6 + T / 250, 3.0)                                                 # A-4-19M
    jc = J * c / (Sx * ho)
    Lr = 1.95 * rts * E_T / FL * math.sqrt(jc + math.sqrt(jc**2 + 6.76 * (FL / E_T) ** 2))   # A-4-16
    out = {"Lr_T_mm": Lr, "FL_T_mpa": FL, "cx": cx, "rts_mm": rts, "c": c, "Lb_mm": Lb, "Cb": Cb}
    if Lb <= Lr:
        mn = Cb * (FL * Sx + (Mp - FL * Sx) * (1 - Lb / Lr) ** cx)               # A-4-13
        return {**out, "Mn": min(mn, Mp), "equation": "A-4-13"}
    fcr = Cb * math.pi**2 * E_T / (Lb / rts) ** 2 * math.sqrt(1 + 0.078 * jc * (Lb / rts) ** 2)   # A-4-15
    return {**out, "Fcr_T_mpa": fcr, "Mn": min(fcr * Sx, Mp), "equation": "A-4-14"}
