"""AISC Design Guide 38 (2023), Appendix A: plastic strength of C-shaped SpeedCore walls and composite coupling beams.

Not a standard: ANSI/AISC 360-22 I3.5 and I5(c) refer to the plastic stress distribution of I1.2a, and the guide writes it
out for these shapes. Units N, mm. C is measured from the outer face of the web (A.2.1 to A.2.5), from the end of the web
(A.2.6) or from the compression face (A.3). Each function reports whether C lies in the zone its equations assume.
"""


def c_wall_properties(*, L, W, tsc_w, tsc_f, tp, n) -> dict:
    """Areas, elastic centroid (from the web outer face) and inertias; n = Ec/Es, as in Example 2.3."""
    tc_w, tc_f = tsc_w - 2 * tp, tsc_f - 2 * tp
    web = L - 4 * tp
    steel = [(tp * W, W / 2)] * 4 + [(web * tp, tsc_w - tp / 2), (web * tp, tp / 2), (tc_f * tp, W - tp / 2), (tc_f * tp, W - tp / 2)]
    core = W - tsc_w - tp
    concrete = [(core * tc_f, tsc_w + core / 2)] * 2 + [(web * tc_w, tsc_w / 2)]
    As, Ac = sum(a for a, _ in steel), sum(a for a, _ in concrete)
    y = (sum(a * v for a, v in steel) + n * sum(a * v for a, v in concrete)) / (As + n * Ac)
    # Minor axis (through y): depth along W. Major axis (mid-length): depth along L.
    Is_y = (4 * tp * W**3 / 12 + 4 * tp * W * (W / 2 - y) ** 2
            + web * tp**3 / 12 * 2 + web * tp * ((tsc_w - tp / 2 - y) ** 2 + (tp / 2 - y) ** 2)
            + 2 * (tc_f * tp**3 / 12 + tc_f * tp * (W - tp / 2 - y) ** 2))
    Ic_y = (2 * (tc_f * core**3 / 12 + tc_f * core * (tsc_w + core / 2 - y) ** 2)
            + web * tc_w**3 / 12 + web * tc_w * (tsc_w / 2 - y) ** 2)
    edge = L / 2 - tp / 2
    inner = L / 2 - tsc_f + tp / 2
    mid = L / 2 - tsc_f / 2
    Is_x = (2 * (W * tp**3 / 12) * 2 + 2 * W * tp * (edge**2 + inner**2)
            + 2 * tp * web**3 / 12 + 2 * (tp * tc_f**3 / 12 + tp * tc_f * mid**2))
    Ic_x = 2 * (core * tc_f**3 / 12 + core * tc_f * mid**2) + tc_w * web**3 / 12
    return {"As": As, "Ac": Ac, "Ag": As + Ac, "y": y, "Is_x": Is_x, "Is_y": Is_y, "Ic_x": Ic_x, "Ic_y": Ic_y,
            "Asw": 4 * W * tp, "Acw": 2 * (W - 3 * tp) * tc_f}


def _geometry(L, tp, tsc_w, tsc_f):
    return L - 4 * tp, tsc_w - 2 * tp, tsc_f - 2 * tp


def flange_tips_in_compression(*, L, W, tsc_w, tsc_f, tp, Fy, fc, T=0.0, y=0.0) -> dict:
    """A.2.1 (T = 0) and A.2.3 (axial tension T > 0 at the centroid y): plastic neutral axis in the flanges."""
    web, _, tc_f = _geometry(L, tp, tsc_w, tsc_f)
    c = 0.85 * fc
    C = (T + 4 * tp * W * Fy + 2 * tp * tc_f * Fy + c * 2 * tc_f * (W - tp) - 2 * tp * web * Fy) / (8 * tp * Fy + c * 2 * tc_f)
    C1, C2, C3 = 4 * (W - C) * tp * Fy, 2 * tc_f * tp * Fy, c * 2 * tc_f * (W - C - tp)
    T1, T2, T3 = 4 * C * tp * Fy, web * tp * Fy, web * tp * Fy
    Mp = (C1 * (W - C) / 2 + C2 * (W - C - tp / 2) + C3 * (W - C - tp) / 2 + T1 * C / 2 + T2 * (C - tsc_w + tp / 2)
          + T3 * (C - tp / 2) + T * (y - C))
    return {"C": C, "Mp": Mp, "equation": "DG38 A.2.3" if T else "DG38 A.2.1", "valid": tsc_w <= C <= W - tp}


def web_in_compression(*, L, W, tsc_w, tsc_f, tp, Fy, fc) -> dict:
    """A.2.2: no axial force, plastic neutral axis in the web."""
    web, _, tc_f = _geometry(L, tp, tsc_w, tsc_f)
    c = 0.85 * fc
    C = (web * tp * c + 4 * W * tp * Fy + 2 * tp * tc_f * Fy) / (8 * tp * Fy + web * c)
    C1, C2, C3 = 4 * tp * C * Fy, tp * web * Fy, web * (C - tp) * c
    T1, T2, T3 = 4 * (W - C) * tp * Fy, tp * web * Fy, 2 * tp * tc_f * Fy
    Mp = (C1 * C / 2 + C2 * (C - tp / 2) + C3 * (C - tp) / 2 + T1 * (W - C) / 2 + T2 * (tsc_w - C - tp / 2)
          + T3 * (W - C - tp / 2))
    return {"C": C, "Mp": Mp, "equation": "DG38 A.2.2", "valid": tp <= C <= tsc_w - tp}


def web_in_compression_with_axial(*, L, W, tsc_w, tsc_f, tp, Fy, fc, P, y) -> dict:
    """A.2.4 (neutral axis in the flange concrete) or, when its C falls short of the web, A.2.5 (in the interior web plate)."""
    web, tc_w, tc_f = _geometry(L, tp, tsc_w, tsc_f)
    c = 0.85 * fc
    C = ((P - 2 * tp * web * Fy - tc_w * web * c + 2 * tc_f * tsc_w * c + 4 * tp * W * Fy + 2 * tp * tc_f * Fy)
         / (8 * tp * Fy + 2 * tc_f * c))
    if C >= tsc_w:
        C1, C2, C3 = 4 * C * tp * Fy, tp * web * Fy, tp * web * Fy
        C4, C5 = c * tc_w * web, c * 2 * tc_f * (C - tsc_w)
        T1, T2 = 4 * (W - C) * tp * Fy, 2 * tp * tc_f * Fy
        Mp = (C1 * C / 2 + C2 * (C - tp / 2) + C3 * (C - tsc_w + tp / 2) + C4 * (C - tsc_w / 2) + C5 * (C - tsc_w) / 2
              + T1 * (W - C) / 2 + T2 * (W - C - tp / 2) + P * (y - C))
        return {"C": C, "Mp": Mp, "equation": "DG38 A.2.4", "valid": C <= W - tp}
    C = ((P - tp * web * Fy + (tc_w + tp) * web * Fy - tc_w * web * c + 4 * tp * W * Fy + 2 * tp * tc_f * Fy + tsc_w * web * Fy)
         / (8 * tp * Fy + 2 * web * Fy))
    C1, C2, C3 = 4 * C * tp * Fy, tp * web * Fy, (C - tc_w - tp) * web * Fy
    C4 = c * tc_w * web
    T1, T2, T3 = 4 * (W - C) * tp * Fy, (tsc_w - C) * web * Fy, 2 * tp * tc_f * Fy
    Mp = (C1 * C / 2 + C2 * (C - tp / 2) + C3 * (C - tc_w - tp) / 2 + C4 * (C - tp - tc_w / 2) + T1 * (W - C) / 2
          + T2 * (tsc_w - C) / 2 + T3 * (W - C - tp / 2) + P * (y - C))
    return {"C": C, "Mp": Mp, "equation": "DG38 A.2.5", "valid": tsc_w - tp <= C <= tsc_w}


def major_axis(*, L, W, tsc_w, tsc_f, tp, Fy, fc) -> dict:
    """A.2.6: no axial force, plastic neutral axis in the web. The flange-wall length without perpendicular plates is Wc."""
    _, tc_w, tc_f = _geometry(L, tp, tsc_w, tsc_f)
    Wc = W - 3 * tp
    c = 0.85 * fc
    C = (2 * L * tp * Fy + c * (tc_w * tsc_f - tc_f * Wc)) / (4 * tp * Fy + c * tc_w)
    flange, end = Wc * tp * Fy, tsc_f * tp * Fy
    C4, C5, C6 = 2 * C * tp * Fy, c * Wc * tc_f, c * (C - tsc_f) * tc_w
    T4 = 2 * (L - C) * tp * Fy
    Mp = (flange * (C - tp / 2) + flange * (C - tsc_f + tp / 2) + end * (C - tsc_f / 2) + C4 * C / 2 + C5 * (C - tsc_f / 2)
          + C6 * (C - tsc_f) / 2 + flange * (L - C - tp / 2) + flange * (L - C - tsc_f + tp / 2) + end * (L - C - tsc_f / 2)
          + T4 * (L - C) / 2)
    return {"C": C, "Mp": Mp, "equation": "DG38 A.2.6", "valid": tsc_f <= C <= L - tsc_f}


def coupling_beam_moment(*, b, h, tf, tw, Fy, fc) -> dict:
    """A.3: composite coupling beam, compact box of flange plates tf and web plates tw."""
    tc = b - 2 * tw
    c = 0.85 * fc
    C = (2 * tw * h * Fy + c * tc * tf) / (4 * tw * Fy + c * tc)
    C1, C2, C3 = tc * tf * Fy, 2 * tw * C * Fy, c * tc * (C - tf)
    T1, T2 = tf * tc * Fy, 2 * tw * (h - C) * Fy
    Mp = C1 * (C - tf / 2) + C2 * C / 2 + C3 * (C - tf) / 2 + T1 * (h - C - tf / 2) + T2 * (h - C) / 2
    return {"C": C, "Mp": Mp, "equation": "DG38 A.3", "valid": tf <= C <= h - tf}
