"""AISC Design Guide 6, 2nd ed. (2025), procedures that ANSI/AISC 360-22 does not print. Not a standard. Units N, mm, MPa.

Yield moment of a round filled section with internal bars (Example 2.7, Fig. 2-19, Table 2-8), the My of I3-5b.
"""
import math

E_STEEL = 200000.0


def _segment(r, y):
    """Area, first moment and second moment about the center of the part of a circle above y."""
    if y >= r:
        return 0.0, 0.0, 0.0
    if y <= -r:
        return math.pi * r**2, 0.0, math.pi * r**4 / 4
    alpha = math.acos(y / r)
    return (r**2 * (alpha - math.sin(alpha) * math.cos(alpha)), 2 / 3 * r**3 * math.sin(alpha) ** 3,
            r**4 / 4 * (alpha - math.sin(4 * alpha) / 4))


def _between(r, low, high):
    above_low, above_high = _segment(r, low), _segment(r, high)
    return tuple(a - b for a, b in zip(above_low, above_high))


def round_yield_moment(*, Fy, fc, Ec, D, t, Fysr=0.0, bars=()) -> dict:
    """Neutral axis at yn (compression above): steel linear from Fy at the top fiber and yielded in tension below;
    concrete linear up to 0.7f'c at the inside of the tube; bars with the strain of the concrete, up to Fysr.
    bars = [(area, v from the bending axis)]. Returns My (N*mm) and yn (mm).
    """
    ro, ri = D / 2, D / 2 - t

    def forces(yn):
        y_yield = max(2 * yn - ro, -ro)                              # tension yield of the steel below this level
        slope = Fy / (ro - yn)
        out_a, out_q, out_i = _between(ro, y_yield, ro)
        in_a, in_q, in_i = _between(ri, y_yield, ri)
        a, q, i = out_a - in_a, out_q - in_q, out_i - in_i
        axial = slope * (q - yn * a)
        moment = slope * (i - yn * q)
        tension_a = (_between(ro, -ro, y_yield)[0] - _between(ri, -ri, y_yield)[0])
        tension_q = (_between(ro, -ro, y_yield)[1] - _between(ri, -ri, y_yield)[1])
        axial -= Fy * tension_a
        moment -= Fy * tension_q
        slope_c = 0.7 * fc / (ri - yn)
        c_a, c_q, c_i = _between(ri, yn, ri)
        axial += slope_c * (c_q - yn * c_a)
        moment += slope_c * (c_i - yn * c_q)
        strain_top = 0.7 * fc / Ec
        for area, v in bars:
            stress = E_STEEL * strain_top * (v - yn) / (ri - yn)
            stress = max(min(stress, Fysr), -Fysr)
            if v > yn:                                               # the bar displaces compressed concrete
                concrete = slope_c * (v - yn)
                axial -= concrete * area
                moment -= concrete * area * v
            axial += stress * area
            moment += stress * area * v
        return axial, moment

    low, high = -ro * 0.999, ri * 0.999
    for _ in range(200):
        middle = (low + high) / 2
        if forces(middle)[0] > 0:
            low = middle
        else:
            high = middle
    yn = (low + high) / 2
    return {"My": forces(yn)[1], "yn_mm": yn}
