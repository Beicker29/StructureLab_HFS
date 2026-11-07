"""ANSI/AISC 360-22 Chapter G formulations (shear). Pure functions; units N, mm, MPa. LRFD only.

G2.1 with or without transverse stiffeners (kv of G2-5), tension field action in interior (G2.2) and end (G2.3)
web panels, and the transverse stiffener limits of G2.4. Selection lives in domain/shear.py.
"""
import math

from ._checks import positive as _positive

PHI_V = 0.90          # G1(a)
PHI_V_ROLLED = 1.00   # G2.1(a): webs of rolled I-shapes with h/tw <= 2.24*sqrt(E/Fy)
KV_UNSTIFFENED = 5.34  # G2.1(b)(2)(i)
KV_HSS = 5.0           # G4
KV_LEG = 1.2           # G3, G6


def rolled_web_limit(*, E, Fy) -> float:
    """G2.1(a): 2.24*sqrt(E/Fy)."""
    _positive(E=E, Fy=Fy)
    return 2.24 * math.sqrt(E / Fy)


def cv1(*, h_tw, kv, E, Fy) -> dict:
    """G2.1(b)(1): web shear strength coefficient Cv1 (G2-3, G2-4)."""
    _positive(h_tw=h_tw, kv=kv, E=E, Fy=Fy)
    limit = 1.10 * math.sqrt(kv * E / Fy)
    if h_tw <= limit:
        return {"Cv": 1.0, "equation": "G2-3", "limit": limit}
    return {"Cv": limit / h_tw, "equation": "G2-4", "limit": limit}


def cv2(*, h_tw, kv, E, Fy) -> dict:
    """G2.2: web shear buckling strength coefficient Cv2 (G2-9, G2-10, G2-11)."""
    _positive(h_tw=h_tw, kv=kv, E=E, Fy=Fy)
    root = math.sqrt(kv * E / Fy)
    if h_tw <= 1.10 * root:
        return {"Cv": 1.0, "equation": "G2-9", "limit": 1.10 * root}
    if h_tw <= 1.37 * root:
        return {"Cv": 1.10 * root / h_tw, "equation": "G2-10", "limit": 1.37 * root}
    return {"Cv": 1.51 * kv * E / (h_tw**2 * Fy), "equation": "G2-11", "limit": 1.37 * root}


def kv_stiffened(*, a_h) -> dict:
    """G2-5: web plate shear buckling coefficient with transverse stiffeners; 5.34 when a/h > 3.0."""
    _positive(a_h=a_h)
    if a_h > 3.0:
        return {"kv": KV_UNSTIFFENED, "kv_equation": "G2.1(b)(2)(ii), a/h > 3"}
    return {"kv": 5 + 5 / a_h**2, "kv_equation": "G2-5"}


def tension_field_interior(*, Fy, E, Aw, h_tw, kv, a_h, Afc, Aft, h_bfc, h_bft) -> dict:
    """G2.2, interior web panel with a/h <= 3: G2-6, or G2-7 / G2-8 with Cv2 of G2-9 to G2-11."""
    _positive(Fy=Fy, E=E, Aw=Aw, h_tw=h_tw, kv=kv, a_h=a_h, Afc=Afc, Aft=Aft, h_bfc=h_bfc, h_bft=h_bft)
    if a_h > 3.0:
        raise ValueError("G2.2 requires a/h <= 3")
    cv = cv2(h_tw=h_tw, kv=kv, E=E, Fy=Fy)
    out = {"Cv2": cv["Cv"], "Cv_equation": cv["equation"], "Aw_Af": 2 * Aw / (Afc + Aft)}
    if h_tw <= 1.10 * math.sqrt(kv * E / Fy):
        return {**out, "Vn": 0.6 * Fy * Aw, "equation": "G2-6"}
    if out["Aw_Af"] <= 2.5 and h_bfc <= 6.0 and h_bft <= 6.0:
        field = (1 - cv["Cv"]) / (1.15 * math.sqrt(1 + a_h**2))
        return {**out, "Vn": 0.6 * Fy * Aw * (cv["Cv"] + field), "equation": "G2-7"}
    field = (1 - cv["Cv"]) / (1.15 * (a_h + math.sqrt(1 + a_h**2)))
    return {**out, "Vn": 0.6 * Fy * Aw * (cv["Cv"] + field), "equation": "G2-8"}


def plastic_moment(pieces) -> float:
    """Plastic moment of rectangles (start, end, width, Fy) along one line, about the axis that balances the forces."""
    total = sum(fy * w * (s1 - s0) for s0, s1, w, fy in pieces)
    events = sorted({s for s0, s1, _, _ in pieces for s in (s0, s1)})
    below = 0.0
    axis = events[-1]
    for lo, hi in zip(events, events[1:]):
        rate = sum(fy * w for s0, s1, w, fy in pieces if s0 <= lo and hi <= s1)
        if rate and below + rate * (hi - lo) >= total / 2:
            axis = lo + (total / 2 - below) / rate
            break
        below += rate * (hi - lo)
    moment = 0.0
    for s0, s1, w, fy in pieces:
        if axis > s0:
            edge = min(s1, axis)
            moment += fy * w * (edge - s0) * (axis - (s0 + edge) / 2)
        if axis < s1:
            edge = max(s0, axis)
            moment += fy * w * (s1 - edge) * ((edge + s1) / 2 - axis)
    return moment


def end_panel_de(*, tw, Cv2) -> dict:
    """G2-14 (Cv2 <= 0.8) or G2-15: depth of the web segment included in Mpf and Mpst."""
    _positive(tw=tw, Cv2=Cv2)
    if Cv2 <= 0.8:
        return {"de_mm": 35 * tw * (0.8 - Cv2) ** 2, "de_equation": "G2-14"}
    return {"de_mm": 0.0, "de_equation": "G2-15"}


def tension_field_end(*, Fyw, E, Fy, Aw, h, tw, h_tw, kv, a_h, bf, tf, Fyf, stiffener_width, tst, Fyst, e) -> dict:
    """G2.3(a), end web panel with a/h <= 3 and equal flange areas: G2-12 with beta_v of G2-13.

    Mpf: the flange and a web segment of depth de, bending in the plane of the web. Mpst: the end stiffener (total width
    across the web, stiffener_width, of thickness tst) and the web from the end of the beam to de past the inside face of
    the stiffener, with that end distance not taken greater than 0.84*tw*sqrt(E/Fy) (Commentary, Fig. C-G2.3).
    """
    _positive(Fyw=Fyw, E=E, Fy=Fy, Aw=Aw, h=h, tw=tw, h_tw=h_tw, kv=kv, a_h=a_h, bf=bf, tf=tf, Fyf=Fyf,
              stiffener_width=stiffener_width, tst=tst, Fyst=Fyst, e=e)
    if a_h > 3.0:
        raise ValueError("G2.3 requires a/h <= 3")
    if e < tst:
        raise ValueError("the end distance e reaches the inside face of the stiffener: e >= tst")
    cv = cv2(h_tw=h_tw, kv=kv, E=E, Fy=Fy)
    de = end_panel_de(tw=tw, Cv2=cv["Cv"])
    d_e = de["de_mm"]
    e_used = min(e, 0.84 * tw * math.sqrt(E / Fy))
    mpf = plastic_moment([(0.0, tf, bf, Fyf), (tf, tf + d_e, tw, Fyw)] if d_e else [(0.0, tf, bf, Fyf)])
    web = [(0.0, e_used + d_e, tw, Fyw)]
    stiffener = [(e_used - tst, e_used, stiffener_width, Fyst)] if e_used > tst else [(0.0, e_used, stiffener_width, Fyst)]
    mpst = plastic_moment(web + stiffener)
    mpm = min(mpf, mpst)
    out = {"Cv2": cv["Cv"], "Cv_equation": cv["equation"], **de, "e_used_mm": e_used, "Mpf_Nmm": mpf, "Mpst_Nmm": mpst,
           "Mpm_Nmm": mpm}
    if cv["Cv"] >= 1.0:
        return {**out, "beta_v": 1.0, "Vn": 0.6 * Fyw * Aw, "equation": "G2-12"}
    beta = min(2.8 * (math.sqrt(mpf + mpm) + math.sqrt(mpst + mpm)) / (h * math.sqrt(Fyw * tw * (1 - cv["Cv"]))), 1.0)  # G2-13
    field = beta * (1 - cv["Cv"]) / (1.15 * math.sqrt(1 + a_h**2))
    return {**out, "beta_v": beta, "Vn": 0.6 * Fyw * Aw * (cv["Cv"] + field), "equation": "G2-12"}


def stiffener_limits(*, E, Fyst, Fyw, b, t, h, tw, pair: bool) -> dict:
    """G2.4(d), G2-16: (b/t)st <= 0.56*sqrt(E/Fyst); G2.4(e) with Ist >= Ist1 of G2-18 (User Note of G2.4).

    Ist of the stiffener plates: a pair about the web center, tst*((2b + tw)^3 - tw^3)/12; one plate about the face in contact
    with the web, tst*b^3/3.
    """
    _positive(E=E, Fyst=Fyst, Fyw=Fyw, b=b, t=t, h=h, tw=tw)
    rho = max(Fyw / Fyst, 1.0)
    ist = t * ((2 * b + tw) ** 3 - tw**3) / 12 if pair else t * b**3 / 3
    ist1 = h**4 * rho**1.3 / 40 * (Fyw / E) ** 1.5                            # G2-18
    return {"b_t": b / t, "b_t_max": 0.56 * math.sqrt(E / Fyst), "rho_st": rho, "Ist_mm4": ist, "Ist1_mm4": ist1}


def web_strength(*, Fy, Aw, Cv, equation) -> dict:
    """0.6*Fy*Aw*Cv: G2-1 (I-shapes, channels) and G4-1 (HSS, box)."""
    _positive(Fy=Fy, Aw=Aw, Cv=Cv)
    return {"Vn": 0.6 * Fy * Aw * Cv, "equation": equation}


def leg_strength(*, Fy, b, t, Cv) -> dict:
    """G3-1: Vn = 0.6*Fy*b*t*Cv2 of one angle leg."""
    _positive(Fy=Fy, b=b, t=t, Cv=Cv)
    return {"Vn": 0.6 * Fy * b * t * Cv, "equation": "G3-1"}


def flange_strength(*, Fy, bf, tf, Cv) -> dict:
    """G6-1: Vn = 0.6*Fy*bf*tf*Cv2 of one flange."""
    _positive(Fy=Fy, bf=bf, tf=tf, Cv=Cv)
    return {"Vn": 0.6 * Fy * bf * tf * Cv, "equation": "G6-1"}


def round_hss_strength(*, E, Fy, Ag, D, t, Lv=None) -> dict:
    """G5: Vn = Fcr*Ag/2; Fcr = max(G5-2a, G5-2b) <= 0.6Fy. Without Lv only G5-2b (a lower bound)."""
    _positive(E=E, Fy=Fy, Ag=Ag, D=D, t=t)
    d_t = D / t
    fcr_b = 0.78 * E / d_t**1.5                                   # G5-2b
    fcr_a = None
    if Lv is not None:
        _positive(Lv=Lv)
        fcr_a = 1.60 * E / (math.sqrt(Lv / D) * d_t**1.25)         # G5-2a
    buckling = max(fcr_b, fcr_a) if fcr_a is not None else fcr_b
    fcr = min(buckling, 0.6 * Fy)
    equation = "0.6Fy" if fcr == 0.6 * Fy else ("G5-2a" if fcr_a is not None and fcr_a >= fcr_b else "G5-2b")
    return {"Vn": fcr * Ag / 2, "equation": "G5-1", "Fcr": fcr, "Fcr_equation": equation,
            "Fcr_G5_2a": fcr_a, "Fcr_G5_2b": fcr_b, "D_t": d_t}


def design_strength(Vn_N: float, phi: float) -> float:
    """phi_v*Vn (LRFD) in kN."""
    return phi * Vn_N / 1000.0
