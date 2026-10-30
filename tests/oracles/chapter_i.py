"""Independent Chapter I hand calculations (ANSI/AISC 360-22, a360-22w.pdf pp.16.1-89..120), LRFD.

Decimal arithmetic (50 digits); reads data/sections.xlsx through the Chapter F oracle; never imports steel_design.
Plastic moments are obtained from the sum of forces and moments of each stress block about the top of the section,
with the neutral axis found by bisection of the axial balance; they do not reuse the Z-based forms of the product,
except for the catalog Z of the steel shape, which is data.
Regenerates tests/fixtures/chapter_i/reference.json:

    python tests/oracles/chapter_i.py
"""
from decimal import Decimal as D
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chapter_f  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
E, PI = D(200000), chapter_f.PI
KSI = D("6.894757293168361")
sqrt = chapter_f.sqrt


def row(family, name):
    return chapter_f.row(family, name)


def ec(wc, fc):
    return D("0.043") * D(wc) ** D("1.5") * sqrt(D(fc))


def pn_of(pno, ei, lc):
    pe = PI**2 * ei / D(lc) ** 2                                                 # I2-4
    if pno / pe <= D("2.25"):
        return pno * D("0.658") ** (pno / pe)                                    # I2-2
    return D("0.877") * pe                                                       # I2-3


def corners(width, depth, t):
    """Second moment of a rounded inside rectangle (radius t): integrates the four corner pieces."""
    c = depth / 2 - t
    square = t * ((depth / 2) ** 3 - c**3) / 3
    quarter = c**2 * PI * t**2 / 4 + 2 * c * t**3 / 3 + PI * t**4 / 16
    return width * depth**3 / 12 - 4 * (square - quarter)


def filled_rect(name):
    p = row("RECTANGULAR_HSS", name)
    t = p["tdes"]
    bi, hi = p["B"] - 2 * t, p["Ht"] - 2 * t
    return {"p": p, "t": t, "bi": bi, "hi": hi, "Ac": bi * hi - (4 - PI) * t**2,
            "Icx": corners(bi, hi, t), "Icy": corners(hi, bi, t)}


def filled_compression(name, fy, fc, wc, L, round_=False):
    fy, fc = D(fy), D(fc)
    if round_:
        p = row("CIRCULAR_HSS", name)
        t, d = p["tdes"], p["OD"]
        ri = d / 2 - t
        ac = PI * ri**2
        icx = icy = PI * ri**4 / 4
        lam, lp, lr, lmax = d / t, D("0.15") * E / fy, D("0.19") * E / fy, D("0.31") * E / fy
        c2, fn = D("0.95"), D("0.72") * fy / (lam * fy / E) ** D("0.2")          # I2-11
    else:
        g = filled_rect(name)
        p, t, ac, icx, icy = g["p"], g["t"], g["Ac"], g["Icx"], g["Icy"]
        root = sqrt(E / fy)
        lam = max(p["b"], p["h"]) / t
        lp, lr, lmax = D("2.26") * root, 3 * root, 5 * root                      # Table I1.1a
        c2, fn = D("0.85"), 9 * E / lam**2                                       # I2-10
    assert lam <= lmax
    a_s = p["A"]
    pp = fy * a_s + c2 * fc * ac                                                 # I2-9b
    if lam <= lp:
        pno, cls = pp, "compact"
    elif lam <= lr:
        py = fy * a_s + D("0.7") * fc * ac                                       # I2-9d
        pno, cls = pp - (pp - py) / (lr - lp) ** 2 * (lam - lp) ** 2, "noncompact"
    else:
        pno, cls = fn * a_s + D("0.7") * fc * ac, "slender"                      # I2-9e
    c3 = min(D("0.45") + 3 * a_s / (a_s + ac), D("0.9"))                         # I2-13
    modulus = ec(wc, fc)
    pn = min(pn_of(pno, E * p["Ix"] + c3 * modulus * icx, L), pn_of(pno, E * p["Iy"] + c3 * modulus * icy, L))
    return {"class": cls, "Pno_kN": pno / 1000, "Pn_kN": pn / 1000, "phiPn_kN": D("0.75") * pn / 1000}


def bisect(force, low, high):
    for _ in range(170):
        mid = (low + high) / 2
        if force(mid) > 0:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def filled_rect_flexure(name, fy, fc, axis="x"):
    fy, fc = D(fy), D(fc)
    g = filled_rect(name)
    p, t = g["p"], g["t"]
    H, bi, hi, flange, web, zs = ((p["Ht"], g["bi"], g["hi"], p["b"], p["h"], p["Zx"]) if axis == "x"
                                  else (p["B"], g["hi"], g["bi"], p["h"], p["b"], p["Zy"]))
    root = sqrt(E / fy)
    limits = {"flange": (D("2.26") * root, 3 * root), "web": (3 * root, D("5.7") * root)}
    ratios = {"flange": flange / t, "web": web / t}
    def cls(k):
        return "compact" if ratios[k] <= limits[k][0] else ("noncompact" if ratios[k] <= limits[k][1] else "slender")
    classes = {cls(k) for k in ratios}
    # Mp: concrete rounded at the inside corners; balance of the concrete block against the web band (Fig. C-I3.8(a)).
    ac = g["Ac"]
    zc = bi * hi**2 / 4 - D("0.429") * t**2 * hi + D("0.192") * t**3
    hn = bisect(lambda y: D("0.85") * fc * (ac / 2 - bi * y) - 4 * fy * t * y, D(0), hi / 2)
    mp = fy * (zs - 2 * t * hn**2) + D("0.85") * fc * (zc - bi * hn**2) / 2
    if classes == {"compact"}:
        return {"class": "compact", "Mn_kNm": mp / 10**6}
    tf = tw = t
    if "slender" not in classes:
        a = bisect(lambda y: D("0.35") * fc * (y - tf) * bi - (H - 2 * y) * 2 * tw * fy, H, D(0))
        my = (bi * tf * fy * (a - tf / 2) + D("0.35") * fc * (a - tf) * bi * 2 * (a - tf) / 3
              + 2 * (a * tw * fy) * 2 * a / 3 + (H - 2 * a) * 2 * tw * fy * H / 2 + bi * tf * fy * (H - a - tf / 2))
        values = [mp - (mp - my) * (ratios[k] - limits[k][0]) / (limits[k][1] - limits[k][0])
                  for k in ratios if cls(k) == "noncompact"]
        return {"class": "noncompact", "Mp_kNm": mp / 10**6, "My_kNm": my / 10**6, "Mn_kNm": min(values) / 10**6}
    fn = min(9 * E / ratios["flange"] ** 2, fy)                                   # I2-10
    a = (fy * H * tw + (D("0.35") * fc + fy - fn) * bi * tf) / (tw * (fn + fy) + D("0.35") * fc * bi)
    mcr = (bi * tf * fn * (a - tf / 2) + D("0.35") * fc * (a - tf) * bi * 2 * (a - tf) / 3 + a * tw * fn * 2 * a / 3
           + (H - a) * tw * fy * 2 * (H - a) / 3 + bi * tf * fy * (H - a - tf / 2))
    return {"class": "slender", "Mn_kNm": mcr / 10**6}


def segment(r, y):
    """Area above y of a circle and its first moment about the center, by series-free Decimal trigonometry."""
    if y >= r:
        return D(0), D(0)
    c = y / r
    s = sqrt(1 - c**2)
    alpha = PI / 2 - asin(c)
    return r**2 * (alpha - s * c), D(2) / 3 * r**3 * s**3


def asin(x):
    """Arcsine by Newton iteration on sin, with the Taylor series of sin in Decimal."""
    def sin_cos(a):
        sin, cos, term_s, term_c, n = a, D(1), a, D(1), 1
        for _ in range(60):
            term_c = -term_c * a**2 / ((2 * n - 1) * (2 * n))
            term_s = -term_s * a**2 / ((2 * n) * (2 * n + 1))
            cos, sin, n = cos + term_c, sin + term_s, n + 1
        return sin, cos
    a = x
    for _ in range(60):
        sin, cos = sin_cos(a)
        a -= (sin - x) / cos
    return a


def filled_round_flexure(name, fy, fc):
    fy, fc = D(fy), D(fc)
    p = row("CIRCULAR_HSS", name)
    ro, ri = p["OD"] / 2, p["OD"] / 2 - p["tdes"]
    total = PI * (ro**2 - ri**2)
    def axial(y):
        steel = segment(ro, y)[0] - segment(ri, y)[0]
        return D("0.95") * fc * segment(ri, y)[0] + fy * steel - fy * (total - steel)
    hn = bisect(axial, D(0), ro)
    mp = D("0.95") * fc * segment(ri, hn)[1] + 2 * fy * (segment(ro, hn)[1] - segment(ri, hn)[1])
    return {"class": "compact", "Mn_kNm": mp / 10**6}


def encased_data(name, H, B, bars):
    p = row("W", name)
    H, B = D(H), D(B)
    bars = [(D(a), D(db), D(x), D(y)) for a, db, x, y in bars]
    asr = sum(b[0] for b in bars)
    return p, H, B, bars, asr, B * H - p["A"] - asr


def encased_compression(name, fy, fc, wc, L, H, B, Fysr, bars):
    fy, fc, Fysr = D(fy), D(fc), D(Fysr)
    p, H, B, bars, asr, ac = encased_data(name, H, B, bars)
    pno = fy * p["A"] + Fysr * asr + D("0.85") * fc * ac                         # I2-7
    c1 = min(D("0.25") + 3 * (p["A"] + asr) / (B * H), D("0.7"))                 # I2-6
    modulus, pns = ec(wc, fc), []
    for axis, gross, is_ in (("y", B * H**3 / 12, p["Ix"]), ("x", H * B**3 / 12, p["Iy"])):
        isr = sum(PI * db**4 / 64 + a * (y if axis == "y" else x) ** 2 for a, db, x, y in bars)
        pns.append(pn_of(pno, E * is_ + E * isr + c1 * modulus * (gross - is_ - isr), L))
    pn = min(pns)
    return {"Pno_kN": pno / 1000, "Pn_kN": pn / 1000, "phiPn_kN": D("0.75") * pn / 1000}


def encased_tension(name, fy, Fysr, bars):
    p = row("W", name)
    pn = D(fy) * p["A"] + D(Fysr) * sum(D(b[0]) for b in bars)                   # I2-8
    return {"Pn_kN": pn / 1000, "phiPn_kN": D("0.90") * pn / 1000}


def encased_flexure(name, fy, fc, H, B, Fysr, bars, axis="x", method="composite"):
    fy, fc, Fysr = D(fy), D(fc), D(Fysr)
    p, H, B, bars, _, _ = encased_data(name, H, B, bars)
    zs = p["Zx"] if axis == "x" else p["Zy"]
    if method == "steel":
        return {"Mn_kNm": fy * zs / 10**6}                                       # I3.3a(2)
    h, b = (H, B) if axis == "x" else (B, H)
    arms = [(a, y if axis == "x" else x) for a, _, x, y in bars]
    d, bf, tf, tw, a_s = p["d"], p["bf"], p["tf"], p["tw"], p["A"]

    def band(y):
        if axis == "x":
            if y <= d / 2 - tf:
                return 2 * y * tw, tw * y**2
            if y < d / 2:
                return a_s - 2 * bf * (d / 2 - y), zs - bf * (d / 2 - y) * (d / 2 + y)
            return a_s, zs
        if y <= tw / 2:
            return 2 * y * d, d * y**2
        if y < bf / 2:
            return a_s - 4 * tf * (bf / 2 - y), zs - 2 * tf * (bf / 2 - y) * (bf / 2 + y)
        return a_s, zs

    def forces(y):
        area, zsn = band(y)
        above = sum(a for a, v in arms if v > y)
        steel_above = (a_s - area) / 2
        conc = b * (h / 2 - y) - steel_above - above
        total = sum(a for a, _ in arms)
        return D("0.85") * fc * conc + fy * steel_above + Fysr * above - fy * (a_s - steel_above) - Fysr * (total - above)

    hn = bisect(forces, D(0), h / 2)
    area, zsn = band(hn)
    above = [(a, v) for a, v in arms if v > hn]
    below = [(a, v) for a, v in arms if v <= hn]
    first = b * (h**2 / 4 - hn**2) / 2 - (zs - zsn) / 2 - sum(a * v for a, v in above)
    mp = (D("0.85") * fc * first + fy * (zs - zsn) + Fysr * sum(a * v for a, v in above)
          - Fysr * sum(a * v for a, v in below))
    return {"hn_mm": hn, "Mn_kNm": mp / 10**6}


def beam_flexure(name, fy, fc, wc, span, spacing, tc, hr, n, d, Fu, Rg, Rp):
    fy, fc = D(fy), D(fc)
    p = row("W", name)
    b = 2 * min(D(span) / 8, D(spacing) / 2)                                     # I3.1a
    tc, hr, d_ = D(tc), D(hr), D(d)
    asa = PI * d_**2 / 4
    qn = min(D("0.5") * asa * sqrt(fc * ec(wc, fc)), D(Rg) * D(Rp) * asa * D(Fu))  # I8-1
    crushing, steel, sum_qn = D("0.85") * fc * b * tc, fy * p["A"], n * qn       # I3-1a, b, c
    c = min(crushing, steel, sum_qn)
    a = c / (D("0.85") * fc * b)
    arm = tc + hr - a / 2
    if c >= steel:
        mn = steel * (p["d"] / 2 + arm)
    else:
        cs = (steel - c) / 2
        if cs <= fy * p["bf"] * p["tf"]:
            x = cs / (fy * p["bf"])
            mt = cs * x / 2
        else:
            web = cs - fy * p["bf"] * p["tf"]
            x = p["tf"] + web / (fy * p["tw"])
            mt = fy * p["bf"] * p["tf"] ** 2 / 2 + web * (p["tf"] + x) / 2
        mn = c * arm + steel * p["d"] / 2 - 2 * mt
    return {"Qn_kN": qn / 1000, "C_kN": c / 1000, "Mn_kNm": mn / 10**6, "phiMn_kNm": D("0.90") * mn / 10**6}


def filled_shear(name, fy, fc, axis="x", round_=False):
    fy, fc = D(fy), D(fc)
    if round_:
        p = row("CIRCULAR_HSS", name)
        av = 2 * p["A"] / PI
        ac = PI * (p["OD"] / 2 - p["tdes"]) ** 2
    else:
        g = filled_rect(name)
        av, ac = 2 * (g["p"]["h"] if axis == "x" else g["p"]["b"]) * g["t"], g["Ac"]
    vn = D("0.6") * av * fy + D("0.06") * ac * sqrt(fc * KSI)                    # I4-1, Kc = 1, f'c in ksi as printed
    return {"Vn_kN": vn / 1000, "phiVn_kN": D("0.90") * vn / 1000}


def i5(name, fy, fc, wc, L, Pu, Mu):
    fy, fc, pu, mu = D(fy), D(fc), D(Pu), D(Mu)
    g = filled_rect(name)
    pc = filled_compression(name, fy, fc, wc, L)["phiPn_kN"]
    mc = D("0.90") * filled_rect_flexure(name, fy, fc)["Mn_kNm"]
    csr = g["p"]["A"] * fy / (g["Ac"] * fc)                                      # I5-2
    cp = D("0.17") / csr ** D("0.4")
    cm = max(D("1.06") / csr ** D("0.11"), D(1)) if csr >= D("0.5") else min(D("0.90") / csr ** D("0.36"), D("1.67"))
    if pu / pc >= cp:
        ratio = pu / pc + (1 - cp) / cm * mu / mc                                # I5-1a
    else:
        ratio = (1 - cm) / cp * pu / pc + mu / mc                                # I5-1b
    return {"csr": csr, "cp": cp, "cm": cm, "Pc_kN": pc, "Mc_kNm": mc, "ratio": ratio}


def curve_moment(points, p):
    """Moment of a piecewise-linear interaction curve at the axial force p."""
    for (p1, m1), (p2, m2) in zip(points, points[1:]):
        if p1 <= p <= p2:
            return m1 + (m2 - m1) * (p - p1) / (p2 - p1)
    return D(0)


def scale_to_curve(pr, mr, points):
    """Demand ratio by bisection of the scale that places (Pr, Mr) on the curve (the product intersects segments)."""
    return bisect(lambda s: mr / s - curve_moment(points, pr / s), D("0.001"), D(100))


def method2(kind, Pu, Mu, simplified, **member):
    """Commentary I5, Method 2: anchor points A, B, C, D with the same slenderness factor on A, C and D."""
    pr, mr = D(Pu), D(Mu)
    fy, fc = D(member["fy"]), D(member["fc"])
    if kind == "filled":
        name, wc, L = member["name"], member["wc"], member["L"]
        g = filled_rect(name)
        axial = filled_compression(name, fy, fc, wc, L)
        mb = filled_rect_flexure(name, fy, fc)["Mn_kNm"]
        zc = g["bi"] * g["hi"] ** 2 / 4 - D("0.429") * g["t"] ** 2 * g["hi"] + D("0.192") * g["t"] ** 3
        md = (fy * g["p"]["Zx"] + D("0.85") * fc * zc / 2) / 10**6
        pc = D("0.85") * fc * g["Ac"] / 1000
    else:
        args = {k: member[k] for k in ("name", "H", "B", "Fysr", "bars")}
        p, H, B, bars, _, ac = encased_data(args["name"], args["H"], args["B"], args["bars"])
        axial = encased_compression(fy=fy, fc=fc, wc=member["wc"], L=member["L"], **args)
        mb = encased_flexure(fy=fy, fc=fc, **args)["Mn_kNm"]
        zr = sum(a * abs(y) for a, _, _, y in bars)
        zc = B * H**2 / 4 - p["Zx"] - zr
        md = (fy * p["Zx"] + D(args["Fysr"]) * zr + D("0.85") * fc * zc / 2) / 10**6
        pc = D("0.85") * fc * ac / 1000
    lam = axial["Pn_kN"] / axial["Pno_kN"]
    pa_d, pc_d = D("0.75") * axial["Pn_kN"], D("0.75") * lam * pc
    mc = D("0.90") * mb
    if simplified:
        ratio = mr / mc if pr < pc_d else (pr - pc_d) / (pa_d - pc_d) + mr / mc      # C-I5-1a, C-I5-1b
        return {"PA_kN": pa_d, "PC_kN": pc_d, "Mc_kNm": mc, "ratio": ratio}
    design = [(D(0), mc), (pc_d / 2, D("0.90") * md), (pc_d, mc), (pa_d, D(0))]
    nominal = [(D(0), mb), (pc / 2, md), (pc, mb), (axial["Pno_kN"], D(0))]
    ratios = scale_to_curve(pr, mr, design), scale_to_curve(pr, mr, nominal)
    return {"PA_kN": pa_d, "PC_kN": pc_d, "MD_kNm": D("0.90") * md, "ratio": max(ratios)}


def wall_data(L, tsc, t, tf):
    L, tsc, t, tf = D(L), D(tsc), D(t), D(tf)
    bi, hi = tsc - 2 * t, L - 2 * tf
    return {"L": L, "tsc": tsc, "t": t, "tf": tf, "bi": bi, "hi": hi, "Ac": bi * hi, "As": L * tsc - bi * hi}


def wall_compression(fy, fc, wc, height, L, tsc, t, tf):
    fy, fc = D(fy), D(fc)
    w = wall_data(L, tsc, t, tf)
    pno = fy * w["As"] + D("0.85") * fc * w["Ac"]                                # I2-15
    ec_ = ec(wc, fc)
    # Steel inertias as the gross outline less the concrete core.
    isx = (w["tsc"] * w["L"] ** 3 - w["bi"] * w["hi"] ** 3) / 12
    isy = (w["L"] * w["tsc"] ** 3 - w["hi"] * w["bi"] ** 3) / 12
    pns = [pn_of(pno, E * i + D("0.35") * ec_ * ic, height)                      # I1-1
           for i, ic in ((isx, w["bi"] * w["hi"] ** 3 / 12), (isy, w["hi"] * w["bi"] ** 3 / 12))]
    return {"Pno_kN": pno / 1000, "Pn_kN": min(pns) / 1000, "phiPn_kN": D("0.90") * min(pns) / 1000}


def wall_tension(fy, L, tsc, t, tf):
    pn = D(fy) * wall_data(L, tsc, t, tf)["As"]                                  # I2-16
    return {"Pn_kN": pn / 1000, "phiPn_kN": D("0.90") * pn / 1000}


def wall_moment(fy, fc, L, tsc, t, tf, P=0):
    """Closed form of Fig. C-I3.8(a) with the axial force in the balance; the block ends in the long plates."""
    fy, fc, P = D(fy), D(fc), D(P) * 1000
    w = wall_data(L, tsc, t, tf)
    H, t_, tf_, bi = w["L"], w["t"], w["tf"], w["bi"]
    a = (2 * fy * H * t_ + D("0.85") * fc * bi * tf_ + P) / (4 * t_ * fy + D("0.85") * fc * bi)
    assert tf_ <= a <= H - tf_
    forces = [(bi * tf_ * fy, a - tf_ / 2), (D("0.85") * fc * (a - tf_) * bi, (a - tf_) / 2), (a * 2 * t_ * fy, a / 2),
              ((H - a) * 2 * t_ * fy, (H - a) / 2), (bi * tf_ * fy, H - a - tf_ / 2)]
    # Moments about the neutral axis; the axial force acts at mid-length.
    mn = sum(f * y for f, y in forces) - P * (a - H / 2)
    return {"a_mm": a, "Mn_kNm": mn / 10**6}


def wall_shear_oracle(fy, fc, wc, L, tsc, t, tf):
    w = wall_data(L, tsc, t, tf)
    asw, ec_a = 2 * w["t"] * w["L"], ec(wc, fc) * w["Ac"]
    ks = D(77200) * asw                                                          # I4-3
    ksc = D("0.7") * ec_a * (E * asw) / (4 * E * asw + ec_a)                     # I4-4
    vn = (ks + ksc) / sqrt(3 * ks**2 + ksc**2) * asw * D(fy)                     # I4-2
    return {"Vn_kN": vn / 1000, "phiVn_kN": D("0.90") * vn / 1000}


def wall_interaction(fy, fc, L, tsc, t, tf, Pu, Mu):
    mn = wall_moment(fy, fc, L, tsc, t, tf, D(Pu) / D("0.90"))["Mn_kNm"]
    return {"Mc_kNm": D("0.90") * mn, "ratio": D(Mu) / (D("0.90") * mn)}


def anchor_oracle(type_, Qrv=0, Qrt=0, d=None, Fu=None, la=None, tf=None, tw=None, fc=None, wc=None):
    qrv, qrt = D(Qrv), D(Qrt)
    if type_ == "channel":
        qn = D("0.3") * (D(tf) + D(tw) / 2) * D(la) * sqrt(D(fc) * ec(wc, fc)) / 1000       # I8-2
        return {"Qc_kN": D("0.75") * qn, "ratio": qrv / (D("0.75") * qn)}
    qn = PI * D(d) ** 2 / 4 * D(Fu) / 1000                                       # I8-3, I8-4
    qcv, qct = D("0.65") * qn, D("0.75") * qn
    if qrv and qrt:
        ratio = (qrt / qct) ** (D(5) / 3) + (qrv / qcv) ** (D(5) / 3)            # I8-5
    else:
        ratio = qrv / qcv if qrv else qrt / qct
    return {"Qcv_kN": qcv, "Qct_kN": qct, "ratio": ratio}


BARS_8 = [(510, "25.4", x, y) for x, y in ((241.3, 241.3), (241.3, 0), (241.3, -241.3), (0, 241.3), (0, -241.3),
                                          (-241.3, 241.3), (-241.3, 0), (-241.3, -241.3))]
CASES = {
    "filled-rect-compact-C": dict(kind="filled_compression", name="PTE100X50X3MM", fy=345, fc=35, wc=2320, L=2000),
    "filled-rect-noncompact-C": dict(kind="filled_compression", name="PTE120X60X2MM", fy=345, fc=35, wc=2320, L=2000),
    "filled-rect-slender-C": dict(kind="filled_compression", name="PTE100X40X1.5MM", fy=500, fc=35, wc=2320, L=1500),
    "filled-round-C": dict(kind="filled_compression", name='PTER6"X6.00MM', fy=345, fc=35, wc=2320, L=4000, round_=True),
    "filled-rect-M-x": dict(kind="filled_rect_flexure", name="PTE100X50X3MM", fy=345, fc=35),
    "filled-rect-M-y": dict(kind="filled_rect_flexure", name="PTE100X50X3MM", fy=345, fc=35, axis="y"),
    "filled-rect-M-noncompact": dict(kind="filled_rect_flexure", name="PTE300X100X5MM", fy=345, fc=35, axis="y"),
    "filled-rect-M-slender": dict(kind="filled_rect_flexure", name="PTE100X40X1.5MM", fy=500, fc=35, axis="y"),
    "filled-round-M": dict(kind="filled_round_flexure", name='PTER6"X6.00MM', fy=345, fc=35),
    "filled-rect-V": dict(kind="filled_shear", name="PTE100X50X3MM", fy=345, fc=35),
    "filled-round-V": dict(kind="filled_shear", name='PTER6"X6.00MM', fy=345, fc=35, round_=True),
    "encased-C": dict(kind="encased_compression", name="W10X45", fy=345, fc=35, wc=2320, L=4267, H=610, B=610,
                      Fysr=420, bars=BARS_8),
    "encased-T": dict(kind="encased_tension", name="W10X45", fy=345, Fysr=420, bars=BARS_8),
    "encased-M-x-composite": dict(kind="encased_flexure", name="W10X45", fy=345, fc=35, H=610, B=610, Fysr=420, bars=BARS_8),
    "encased-M-y-composite": dict(kind="encased_flexure", name="W10X45", fy=345, fc=35, H=610, B=610, Fysr=420, bars=BARS_8,
                                  axis="y"),
    "encased-M-x-steel": dict(kind="encased_flexure", name="W10X45", fy=345, fc=35, H=610, B=610, Fysr=420, bars=BARS_8,
                              method="steel"),
    "beam-partial-flange": dict(kind="beam_flexure", name="W21X50", fy=345, fc=28, wc=2320, span=13716, spacing=3048,
                                tc=114, hr=76, n=30, d=19, Fu=450, Rg=1, Rp="0.6"),
    "beam-full-steel": dict(kind="beam_flexure", name="W14X30", fy=345, fc=28, wc=2320, span=9000, spacing=3000, tc=120,
                            hr=0, n=60, d=19, Fu=450, Rg=1, Rp="0.75"),
    "beam-partial-web": dict(kind="beam_flexure", name="W21X50", fy=345, fc=28, wc=2320, span=13716, spacing=3048,
                             tc=114, hr=76, n=8, d=19, Fu=450, Rg=1, Rp="0.6"),
    "i5-high-axial": dict(kind="i5", name="PTE120X60X2MM", fy=345, fc=35, wc=2320, L=2000, Pu=120, Mu=3),
    "i5-low-axial": dict(kind="i5", name="PTE120X60X2MM", fy=345, fc=35, wc=2320, L=2000, Pu=10, Mu=8),
    "m2s-filled-high": dict(kind="method2", member="filled", name="PTE100X50X3MM", fy=345, fc=35, wc=2320, L=2000,
                            Pu=100, Mu=4, simplified=True),
    "m2s-filled-low": dict(kind="method2", member="filled", name="PTE100X50X3MM", fy=345, fc=35, wc=2320, L=2000,
                           Pu=10, Mu=8, simplified=True),
    "m2-filled": dict(kind="method2", member="filled", name="PTE100X50X3MM", fy=345, fc=35, wc=2320, L=2000,
                      Pu=40, Mu=8, simplified=False),
    "m2s-encased": dict(kind="method2", member="encased", name="W10X45", fy=345, fc=35, wc=2320, L=4267, H=610, B=610,
                        Fysr=420, bars=BARS_8, Pu=5000, Mu=800, simplified=True),
    "m2-encased": dict(kind="method2", member="encased", name="W10X45", fy=345, fc=35, wc=2320, L=4267, H=610, B=610,
                       Fysr=420, bars=BARS_8, Pu=5000, Mu=800, simplified=False),
    "wall-C": dict(kind="wall_compression", fy=345, fc=35, wc=2320, height=6000, L=3000, tsc=300, t=10, tf=20),
    "wall-T": dict(kind="wall_tension", fy=345, L=3000, tsc=300, t=10, tf=20),
    "wall-M": dict(kind="wall_moment", fy=345, fc=35, L=3000, tsc=300, t=10, tf=20),
    "wall-V": dict(kind="wall_shear", fy=345, fc=35, wc=2320, L=3000, tsc=300, t=10, tf=20),
    "wall-PM-compression": dict(kind="wall_interaction", fy=345, fc=35, L=3000, tsc=300, t=10, tf=20, Pu=8000, Mu=20000),
    "wall-PM-tension": dict(kind="wall_interaction", fy=345, fc=35, L=3000, tsc=300, t=10, tf=20, Pu=-3000, Mu=15000),
    "stud-shear": dict(kind="anchor", type_="stud", Qrv=50, d=19, Fu=450),
    "stud-tension": dict(kind="anchor", type_="stud", Qrt=60, d=19, Fu=450),
    "stud-interaction": dict(kind="anchor", type_="stud", Qrv=40, Qrt=60, d=19, Fu=450),
    "channel-shear": dict(kind="anchor", type_="channel", Qrv=100, la=100, tf=8, tw=6, fc=35, wc=2320),
}
FUNCTIONS = {"filled_compression": filled_compression, "filled_rect_flexure": filled_rect_flexure,
             "filled_round_flexure": filled_round_flexure, "filled_shear": filled_shear,
             "encased_compression": encased_compression, "encased_tension": encased_tension,
             "encased_flexure": encased_flexure, "beam_flexure": beam_flexure, "i5": i5,
             "wall_compression": wall_compression, "wall_tension": wall_tension, "wall_moment": wall_moment,
             "wall_shear": wall_shear_oracle, "wall_interaction": wall_interaction, "anchor": anchor_oracle}


def run_case(spec):
    if spec["kind"] == "method2":
        args = {k: v for k, v in spec.items() if k not in {"kind", "member"}}
        return method2(spec["member"], **args)
    return FUNCTIONS[spec["kind"]](**{k: v for k, v in spec.items() if k != "kind"})


def _plain(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


if __name__ == "__main__":
    target = ROOT / "tests/fixtures/chapter_i/reference.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    cases = {cid: {"spec": spec, **run_case(spec)} for cid, spec in CASES.items()}
    payload = {"source": "ANSI/AISC 360-22 (a360-22w.pdf) I1-I5, I8.2, I8.3, Commentary Fig. C-I3.8 and I5; "
                         "catalog data/sections.xlsx",
               "generator": "tests/oracles/chapter_i.py (Decimal; independent of steel_design)",
               "cases": _plain(cases)}
    target.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(target)
