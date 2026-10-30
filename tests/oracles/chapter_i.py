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


def segment_full(r, y):
    """Area, first and second moment about the center of the part of a circle above y (r^4/4*(a - sin(4a)/4))."""
    if y >= r:
        return D(0), D(0), D(0)
    if y <= -r:
        return PI * r**2, D(0), PI * r**4 / 4
    c = y / r
    s = sqrt(1 - c**2)
    alpha = PI / 2 - asin(c)
    sin_4a = 2 * (2 * s * c) * (1 - 2 * s**2)
    return r**2 * (alpha - s * c), D(2) / 3 * r**3 * s**3, r**4 / 4 * (alpha - sin_4a / 4)


def band(r, low, high):
    return tuple(a - b for a, b in zip(segment_full(r, low), segment_full(r, high)))


def round_with_bars_compression(name, fy, fc, wc, L, Fysr, bars):
    """I2-9a/b, I2-12, I2-13 with Ac net of the bars (Design Guide 6, Example 2.7)."""
    fy, fc, Fysr = D(fy), D(fc), D(Fysr)
    p = row("CIRCULAR_HSS", name)
    ri = p["OD"] / 2 - p["tdes"]
    bars = [(D(a), D(db), D(x), D(y)) for a, db, x, y in bars]
    asr = sum(b[0] for b in bars)
    afill, ac = PI * ri**2, PI * ri**2 - asr
    ec_ = ec(wc, fc)
    pno = fy * p["A"] + D("0.95") * fc * (ac + asr * E / ec_)
    c3 = min(D("0.45") + 3 * (p["A"] + asr) / (p["A"] + afill), D("0.9"))
    pns = []
    for key, inertia in (("y", p["Ix"]), ("x", p["Iy"])):
        isr = sum(PI * db**4 / 64 + a * (y if key == "y" else x) ** 2 for a, db, x, y in bars)
        pns.append(pn_of(pno, E * inertia + E * isr + c3 * ec_ * (PI * ri**4 / 4 - isr), L))
    return {"Pno_kN": pno / 1000, "Pn_kN": min(pns) / 1000, "phiPn_kN": D("0.75") * min(pns) / 1000}


def round_with_bars_flexure(name, fy, fc, wc, Fysr, bars):
    """Mp by the plastic stress blocks; My by Design Guide 6, Fig. 2-19; Mn by I3-5b."""
    fy, fc, Fysr = D(fy), D(fc), D(Fysr)
    p = row("CIRCULAR_HSS", name)
    ro, ri = p["OD"] / 2, p["OD"] / 2 - p["tdes"]
    arms = [(D(a), D(y)) for a, _, _, y in bars]

    def plastic(y):
        steel, stq = band(ro, y, ro), band(ri, y, ri)
        total = PI * (ro**2 - ri**2)
        steel_up = steel[0] - stq[0]
        above = [(a, v) for a, v in arms if v > y]
        below = [(a, v) for a, v in arms if v <= y]
        ax = (D("0.95") * fc * (stq[0] - sum(a for a, _ in above)) + fy * steel_up - fy * (total - steel_up)
              + Fysr * sum(a for a, _ in above) - Fysr * sum(a for a, _ in below))
        mo = (D("0.95") * fc * (stq[1] - sum(a * v for a, v in above)) + 2 * fy * (steel[1] - stq[1])
              + Fysr * sum(a * v for a, v in above) - Fysr * sum(a * v for a, v in below))
        return ax, mo

    mp = plastic(bisect(lambda y: plastic(y)[0], D(0), ro))[1]
    ec_ = ec(wc, fc)
    strain = D("0.7") * fc / ec_

    def elastic(yn):
        ye = max(2 * yn - ro, -ro)
        slope, slope_c = fy / (ro - yn), D("0.7") * fc / (ri - yn)
        o, i = band(ro, ye, ro), band(ri, ye, ri)
        ot, it = band(ro, -ro, ye), band(ri, -ri, ye)
        c = band(ri, yn, ri)
        ax = slope * ((o[1] - i[1]) - yn * (o[0] - i[0])) - fy * (ot[0] - it[0]) + slope_c * (c[1] - yn * c[0])
        mo = slope * ((o[2] - i[2]) - yn * (o[1] - i[1])) - fy * (ot[1] - it[1]) + slope_c * (c[2] - yn * c[1])
        for a, v in arms:
            stress = max(min(E * strain * (v - yn) / (ri - yn), Fysr), -Fysr)
            if v > yn:
                ax -= slope_c * (v - yn) * a
                mo -= slope_c * (v - yn) * a * v
            ax += stress * a
            mo += stress * a * v
        return ax, mo

    low, high = -ro * D("0.999"), ri * D("0.999")
    for _ in range(90):                                                          # 1e-27 of the depth is enough for 1e-9
        mid = (low + high) / 2
        if elastic(mid)[0] > 0:
            low = mid
        else:
            high = mid
    my = elastic((low + high) / 2)[1]
    lam, lp, lr = p["OD"] / p["tdes"], D("0.09") * E / fy, D("0.31") * E / fy
    mn = mp - (mp - my) * (lam - lp) / (lr - lp) if lam > lp else mp
    return {"Mp_kNm": mp / 10**6, "My_kNm": my / 10**6, "Mn_kNm": mn / 10**6}


def rect_with_bars_flexure(name, fy, fc, Fysr, bars, axis="x"):
    fy, fc, Fysr = D(fy), D(fc), D(Fysr)
    g = filled_rect(name)
    p, t = g["p"], g["t"]
    bi, hi, zs = (g["bi"], g["hi"], p["Zx"]) if axis == "x" else (g["hi"], g["bi"], p["Zy"])
    arms = [(D(a), D(y if axis == "x" else x)) for a, _, x, y in bars]
    zc = bi * hi**2 / 4 - D("0.429") * t**2 * hi + D("0.192") * t**3

    def state(y):
        up = [(a, v) for a, v in arms if v > y]
        down = [(a, v) for a, v in arms if v <= y]
        ua, uq = sum(a for a, _ in up), sum(a * v for a, v in up)
        ax = D("0.85") * fc * (g["Ac"] / 2 - bi * y - ua) - 4 * fy * t * y + Fysr * ua - Fysr * sum(a for a, _ in down)
        mo = (fy * (zs - 2 * t * y**2) + D("0.85") * fc * (zc - bi * y**2) / 2 - D("0.85") * fc * uq + Fysr * uq
              - Fysr * sum(a * v for a, v in down))
        return ax, mo

    return {"Mn_kNm": state(bisect(lambda y: state(y)[0], D(0), hi / 2))[1] / 10**6}


def a2_data(name, fy):
    g = filled_rect(name)
    lam = max(g["p"]["b"], g["p"]["h"]) / g["t"] * sqrt(D(fy) / E)
    return g, lam, (1 - D("0.075") * lam) * D(fy)                                # A-2-2


def appendix_2_compression(name, fy, fc, wc, L):
    fy, fc = D(fy), D(fc)
    g, lam, fn = a2_data(name, fy)
    a_s = g["p"]["A"]
    pno = fn * a_s + D("0.85") * fc * g["Ac"]                                    # A-2-1
    c3 = min(D("0.45") + 3 * a_s / (a_s + g["Ac"]), D("0.9"))
    ec_ = ec(wc, fc)
    pns = [pn_of(pno, E * g["p"]["Ix"] + c3 * ec_ * g["Icx"], L), pn_of(pno, E * g["p"]["Iy"] + c3 * ec_ * g["Icy"], L)]
    return {"Pno_kN": pno / 1000, "Pn_kN": min(pns) / 1000, "phiPn_kN": D("0.75") * min(pns) / 1000}


def appendix_2_flexure(name, fy, fc):
    """Moments of the blocks about the top of the section, axis x; the axial force of the blocks is zero."""
    fy, fc = D(fy), D(fc)
    g, _, fn = a2_data(name, fy)
    H, t, bi = g["p"]["Ht"], g["t"], g["bi"]
    a = (2 * fy * H * t + (fy - fn) * bi * t + D("0.85") * fc * bi * t) / (2 * t * fy + 2 * t * fn + D("0.85") * fc * bi)
    compression = [(fn * bi * t, t / 2), (fn * 2 * t * a, a / 2), (D("0.85") * fc * bi * (a - t), (a + t) / 2)]
    tension = [(fy * 2 * t * (H - a), (H + a) / 2), (fy * bi * t, H - t / 2)]
    msd = sum(f * y for f, y in tension) - sum(f * y for f, y in compression)
    return {"Mn_kNm": D("0.9") * msd / 10**6}


def appendix_2_interaction(name, fy, fc, wc, L, Pu, Mu):
    pu, mu, fy_, fc_ = D(Pu), D(Mu), D(fy), D(fc)
    g, lam, _ = a2_data(name, fy)
    axial = appendix_2_compression(name, fy, fc, wc, L)
    mc = D("0.90") * appendix_2_flexure(name, fy, fc)["Mn_kNm"]
    ratio_p = axial["Pn_kN"] / axial["Pno_kN"]
    bh = g["p"]["B"] / g["p"]["Ht"]
    cp = D("0.175") - D("0.075") / bh + lam * (D("0.3") / ratio_p) * (fc_ / fy_)
    cm = D("0.6") + D("0.3") * ratio_p**2 + D("0.6") * lam * bh * (D(690) / fy_) * (fc_ / fy_)
    x = pu / axial["phiPn_kN"]
    ratio = x + (1 - cp) / cm * mu / mc if x >= cp else (1 - cm) / cp * x + mu / mc
    return {"cp": cp, "cm": cm, "ratio": ratio}


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
    mn = wall_moment(fy, fc, L, tsc, t, tf, Pu)["Mn_kNm"]                        # Design Guide 38, A.1.2 and A.1.3
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


def second_order(name, fy, fc, wc, L, Pnt, Plt, Mnt, Mlt, M1_M2, Pstory, Pmf, H, story, drift):
    """Appendix 8.1 on a filled rectangular member bent about x: EI* = 0.8*0.8*(EI)eff (I1.5)."""
    g = filled_rect(name)
    p = g["p"]
    c3 = min(D("0.45") + 3 * p["A"] / (p["A"] + g["Ac"]), D("0.9"))
    ei_star = D("0.64") * (E * p["Ix"] + c3 * ec(wc, fc) * g["Icx"])
    pe1 = PI**2 * ei_star / D(L) ** 2
    cm = D(1) if M1_M2 is None else D("0.6") - D("0.4") * D(str(M1_M2))
    b1 = max(cm / (1 - D(Pnt + Plt) * 1000 / pe1), D(1))
    pe_story = (1 - D("0.15") * D(Pmf) / D(Pstory)) * D(H) * D(story) / D(drift)
    b2 = max(1 / (1 - D(Pstory) / pe_story), D(1))
    return {"B1": b1, "B2": b2, "Pr_kN": D(Pnt) + b2 * D(Plt), "Mr_kNm": b1 * D(Mnt) + b2 * D(Mlt)}


def _transfer_force(pr, share, applied_to, fraction):
    if applied_to == "steel":
        return pr * (1 - share)
    if applied_to == "concrete":
        return pr * share
    return pr * abs(D(str(fraction)) - share)


def load_transfer_filled(name, fy, fc, wc, L, applied_to, Pr, A1=None, Lin=None, steel_fraction=None, round_=False):
    """I6-1 to I6-5 for filled members; I6-2b with Fn on slender sections."""
    fy, fc = D(fy), D(fc)
    axial = filled_compression(name, fy, fc, wc, L, round_=round_)
    p = row("CIRCULAR_HSS" if round_ else "RECTANGULAR_HSS", name)
    fs = fy
    if axial["class"] == "slender":
        lam = max(p["b"], p["h"]) / p["tdes"]
        fs = 9 * E / lam**2                                                      # I2-10
    out = {"Vr_kN": _transfer_force(D(Pr), fs * p["A"] / (axial["Pno_kN"] * 1000), applied_to, steel_fraction)}
    if A1:
        out["bearing_kN"] = D("0.65") * D("1.7") * fc * D(A1) / 1000             # I6-3
    if Lin:
        t = p["tdes"]
        if round_:
            ri = p["OD"] / 2 - t
            pb, fin = 2 * PI * ri, min(5300 * t / p["OD"] ** 2, D("1.4"))
        else:
            bi, hi = p["B"] - 2 * t, p["Ht"] - 2 * t
            pb = 2 * (bi + hi) - 8 * t + 2 * PI * t
            fin = min(2100 * t / max(p["Ht"], p["B"]) ** 2, D("0.72"))
        out["bond_kN"] = D("0.50") * pb * D(Lin) * fin / 1000                    # I6-5
    return out


def load_transfer_encased(name, fy, fc, H, B, Fysr, bars, applied_to, Pr, A1):
    fy, fc = D(fy), D(fc)
    p, _, _, _, asr, ac = encased_data(name, H, B, bars)
    pno = fy * p["A"] + D(Fysr) * asr + D("0.85") * fc * ac
    return {"Vr_kN": _transfer_force(D(Pr), fy * p["A"] / pno, applied_to, None),
            "bearing_kN": D("0.65") * D("1.7") * fc * D(A1) / 1000}


def tension_control(name, fy, fc, H, B, Fysr, bars):
    """Design Guide 6, 2.4.1, on the composite flexure of an encased shape about x."""
    hn = encased_flexure(name, fy, fc, H, B, Fysr, bars)["hn_mm"]
    h = D(H)
    c = h / 2 - hn
    d = h / 2 + max(abs(D(b[3])) for b in bars)
    return {"epsilon_t": D("0.003") * (d - c) / c, "epsilon_limit": D(Fysr) / E + D("0.003")}


def box_geometry(B, H, t):
    B, H, t = D(B), D(H), D(t)
    bi, hi = B - 2 * t, H - 2 * t
    return B, H, t, bi, hi, B * H - bi * hi


def box_compression(B, H, t, fy, fc, wc, L):
    """Sharp-cornered welded box, compact: I2-9a with 0.85, stiffness I2-12."""
    B, H, t, bi, hi, a_s = box_geometry(B, H, t)
    ac = bi * hi
    pno = D(fy) * a_s + D("0.85") * D(fc) * ac
    c3 = min(D("0.45") + 3 * a_s / (a_s + ac), D("0.9"))
    modulus = ec(wc, fc)
    pns = [pn_of(pno, E * (b * h**3 - i * j**3) / 12 + c3 * modulus * i * j**3 / 12, L) for b, h, i, j in ((B, H, bi, hi), (H, B, hi, bi))]
    return {"Pno_kN": pno / 1000, "Pn_kN": min(pns) / 1000}


def box_flexure(B, H, t, fy, fc):
    """Sum of the stress blocks about the center, with the neutral axis at hn above it (web band in tension)."""
    B, H, t, bi, hi, _ = box_geometry(B, H, t)
    fy, fc = D(fy), D(fc)
    hn = D("0.85") * fc * bi * hi / 2 / (4 * fy * t + D("0.85") * fc * bi)
    steel = fy * (B * t * (H - t) + 2 * t * (hi**2 / 4 - hn**2))
    concrete = D("0.85") * fc * bi * (hi**2 / 4 - hn**2) / 2
    return {"Mn_kNm": (steel + concrete) / 10**6}


def box_shear(B, H, t, fy, fc):
    """I4-1 with Av = 2Ht, as Design Guide 6, Example 2.5, and Kc = 1 (DI-4); f'c in ksi as printed."""
    B, H, t, bi, hi, _ = box_geometry(B, H, t)
    vn = D("0.6") * 2 * H * t * D(fy) + D("0.06") * bi * hi * sqrt(D(fc) * KSI)
    return {"phiVn_kN": D("0.90") * vn / 1000}


def biaxial(member, Pu, Mux, Muy, **data):
    """Design Guide 6, Equations 2-2a and 2-2b."""
    fy, fc = D(data["fy"]), D(data["fc"])
    pr = D(Pu)
    if member == "encased":
        args = {k: data[k] for k in ("name", "H", "B", "Fysr", "bars")}
        _, _, _, _, _, ac = encased_data(args["name"], args["H"], args["B"], args["bars"])
        axial = encased_compression(fy=fy, fc=fc, wc=data["wc"], L=data["L"], **args)
        mx = encased_flexure(fy=fy, fc=fc, **args)["Mn_kNm"]
        my = encased_flexure(fy=fy, fc=fc, axis="y", **args)["Mn_kNm"]
        pc, alpha = D("0.85") * fc * ac / 1000, D("1.25")
    else:
        g = filled_rect(data["name"])
        axial = filled_compression(data["name"], fy, fc, data["wc"], data["L"])
        mx, my = (filled_rect_flexure(data["name"], fy, fc, axis=a)["Mn_kNm"] for a in "xy")
        pc, alpha = D("0.85") * fc * g["Ac"] / 1000, D("1.5")
    lam = axial["Pn_kN"] / axial["Pno_kN"]
    pa_d, pc_d = D("0.75") * axial["Pn_kN"], D("0.75") * lam * pc
    sum_ = (D(Mux) / (D("0.9") * mx)) ** alpha + (D(Muy) / (D("0.9") * my)) ** alpha
    return {"ratio": sum_ if pr <= pc_d else (pr - pc_d) / (pa_d - pc_d) + sum_ ** (1 / alpha)}


def service_filled(name, fy, fc, wc, L, Pu):
    """Design Guide 6, Equations 2-1, 2-9, 2-10 and 2-11 on a rectangular member, about x."""
    g = filled_rect(name)
    p = g["p"]
    c3 = min(D("0.45") + 3 * p["A"] / (p["A"] + g["Ac"]), D("0.9"))
    modulus = ec(wc, fc)
    pno = filled_compression(name, fy, fc, wc, L)["Pno_kN"]
    factor = D("0.4") * c3 if D(Pu) < D("0.1") * pno else D("0.6")
    return {"EI_service": E * p["Ix"] + factor * modulus * g["Icx"], "EA_service": E * p["A"] + modulus * g["Ac"],
            "GA_service": D("77200") * p["A"] / 2 + D("0.4") * modulus * g["Ac"] / D("1.2")}


def service_round(name, fy, fc, wc, L, Pu):
    """Design Guide 6, Equations 2-12 and 2-13 on a round member."""
    p = row("CIRCULAR_HSS", name)
    ri = p["OD"] / 2 - p["tdes"]
    ag = p["A"] + PI * ri**2
    beta = min(2 * p["A"] / ag + D(2) / 5, D(1))
    return {"GJ_service": D("77200") * p["J"] + beta * D("0.4") * ec(wc, fc) * PI * ri**4 / 2}


def wall_slender(fy, fc, L, tsc, t, tf, b):
    """C-I1-1 with (b/t) squared (DG38, Eq. 2-2) and C-I1-2."""
    w = wall_data(L, tsc, t, tf)
    fn = min(PI**2 * E / (12 * D("0.64") * (D(b) / w["t"]) ** 2), D(fy))
    return {"Pno_kN": (w["As"] * fn + D("0.7") * D(fc) * w["Ac"]) / 1000}


def wall_stiffnesses(fc, wc, L, tsc, t, tf):
    """I1-1 to I1-3 about the plane of the wall."""
    w = wall_data(L, tsc, t, tf)
    modulus = ec(wc, fc)
    ix = (w["tsc"] * w["L"] ** 3 - w["bi"] * w["hi"] ** 3) / 12
    return {"EI_eff": E * ix + D("0.35") * modulus * w["bi"] * w["hi"] ** 3 / 12, "EA_eff": E * w["As"] + D("0.45") * modulus * w["Ac"],
            "GA_eff": D("77200") * 2 * w["t"] * w["L"] + D("0.4") * modulus * w["Ac"]}


def blocks(pieces, compressed_above, P, y):
    """Plastic moment of rectangular pieces (kind, from, to, width) by balance of forces about the neutral axis at c."""
    def state(c):
        force, moment = D(0), D(0)
        for stress, low, high, width in pieces:
            for start, end, sign in ((max(low, c), high, 1), (low, min(high, c), -1)):
                if end <= start:
                    continue
                compresses = (sign > 0) == compressed_above
                if stress[1] and not compresses:
                    continue
                f = stress[0] * width * (end - start) * (1 if compresses else -1)
                force += f
                moment += abs(f) * abs((start + end) / 2 - c)
        return force, moment
    top = max(p[2] for p in pieces)
    sign = 1 if compressed_above else -1
    c = bisect(lambda v: sign * (state(v)[0] - P), D(0), top)
    return c, state(c)[1] + P * (y - c) * (-1 if compressed_above else 1)


def c_wall_case(fy, fc, wc, L, W, tsc_w, tsc_f, tp, mode, P=0):
    """A.2 by stress blocks (fy, tensile-capable) and (0.85f'c, compression only), from the web outer face."""
    L, W, tscw, tscf, tp = (D(str(v)) for v in (L, W, tsc_w, tsc_f, tp))
    steel, conc = (D(fy), False), (D("0.85") * D(fc), True)
    web, tcw, tcf = L - 4 * tp, tscw - 2 * tp, tscf - 2 * tp
    core = W - tscw - tp
    n = ec(wc, fc) / E
    if mode == "major":
        wc_ = W - 3 * tp
        pieces = [(steel, D(0), L, 2 * tp)]
        for low, high in ((D(0), tp), (tscf - tp, tscf), (L - tscf, L - tscf + tp), (L - tp, L)):
            pieces.append((steel, low, high, wc_))
        pieces += [(steel, D(0), tscf, tp), (steel, L - tscf, L, tp), (conc, tp, tscf - tp, wc_), (conc, L - tscf + tp, L - tp, wc_),
                   (conc, tscf, L - tscf, tcw)]
        c, m = blocks(pieces, False, D(0), D(0))
        return {"C_mm": c, "Mn_kNm": m / 10**6}
    pieces = [(steel, D(0), W, 4 * tp), (steel, D(0), tp, web), (steel, tscw - tp, tscw, web), (steel, W - tp, W, 2 * tcf),
              (conc, tscw, W - tp, 2 * tcf), (conc, tp, tscw - tp, web)]
    a_s = 4 * W * tp + 2 * web * tp + 2 * tcf * tp
    a_c = 2 * core * tcf + web * tcw
    y = ((4 * W * tp * W / 2 + web * tp * (tscw - tp / 2) + web * tp * tp / 2 + 2 * tcf * tp * (W - tp / 2)
          + n * (2 * core * tcf * (tscw + core / 2) + web * tcw * tscw / 2)) / (a_s + n * a_c))
    P_N = D(P) * 1000
    if mode == "tips":
        c, m = blocks([q for q in pieces if not (q[0][1] and q[1] == tp)] + [(conc, tp, tscw - tp, web)], True, P_N, y)
    else:
        c, m = blocks(pieces, False, P_N, y)
    return {"C_mm": c, "Mn_kNm": m / 10**6, "y": y}


def coupling_flexure(b, h, tf, tw, fy, fc):
    """A.3 by stress blocks measured from the compression face."""
    b, h, tf, tw = (D(str(v)) for v in (b, h, tf, tw))
    steel, conc = (D(fy), False), (D("0.85") * D(fc), True)
    tc = b - 2 * tw
    pieces = [(steel, D(0), h, 2 * tw), (steel, D(0), tf, tc), (steel, h - tf, h, tc), (conc, tf, h - tf, tc)]
    c, m = blocks(pieces, False, D(0), D(0))
    return {"C_mm": c, "Mn_kNm": m / 10**6}


def coupling_shear(b, h, tf, tw, fy, fc):
    b, h, tf, tw = (D(str(v)) for v in (b, h, tf, tw))
    vn = D("0.6") * 2 * h * tw * D(fy) + D("0.06") * (b - 2 * tw) * (h - 2 * tf) * sqrt(D(fc) * KSI)
    return {"phiVn_kN": D("0.90") * vn / 1000}


STEEL_RETENTION = ((20, "1", "1"), (93, "1", "1"), (200, "0.90", "1"), (320, "0.78", "1"), (400, "0.70", "1"), (430, "0.67", "0.94"),
                   (540, "0.49", "0.66"), (650, "0.22", "0.35"), (760, "0.11", "0.16"), (870, "0.07", "0.07"),
                   (980, "0.05", "0.04"), (1100, "0.02", "0.02"), (1200, "0", "0"))
CONCRETE_RETENTION = ((20, "1", "1"), (93, "0.95", "0.93"), (200, "0.90", "0.75"), (290, "0.86", "0.61"), (320, "0.83", "0.57"),
                      (430, "0.71", "0.38"), (540, "0.54", "0.20"), (650, "0.38", "0.092"), (760, "0.21", "0.073"),
                      (870, "0.10", "0.055"), (980, "0.05", "0.036"), (1100, "0.01", "0.018"), (1200, "0", "0"))


def retained(table, temperature, column):
    t = D(str(temperature))
    for low, high in zip(table, table[1:]):
        if t <= high[0]:
            return D(low[column]) + (D(high[column]) - D(low[column])) * (t - low[0]) / (high[0] - low[0])
    return D(0)


def wall_fire_oracle(fy, fc, wc, height, wall_length, tsc, t, st, Pu, plate_T, thicknesses, temperatures, required):
    """Design Guide 38, Eqs. 6-1 to 6-6, on the unit-width column, summed element by element."""
    tsc, t, st, fy, fc = D(str(tsc)), D(str(t)), D(str(st)), D(fy), D(fc)
    modulus, lc = ec(wc, fc), D(height)
    a_s, a_c = 2 * st * t, (tsc - 2 * t) * st
    ic = st * (tsc - 2 * t) ** 3 / 12
    pno = fy * a_s + D("0.85") * fc * a_c
    pe = PI**2 * (E * (st * tsc**3 / 12 - ic) + D("0.35") * modulus * ic) / lc**2
    pn = D("0.658") ** (pno / pe) * pno
    pu = D(Pu) * 1000 * st / D(wall_length)
    rating = (-D("18.5") * (pu / pn) ** (D("0.24") - lc / tsc / 230) + 15) * (D("1.9") * tsc / D("25.4") / 8 - 1)
    half_p = retained(STEEL_RETENTION, plate_T, 2) * fy * st * t
    half_ei = retained(STEEL_RETENTION, plate_T, 1) * E * (st * t**3 / 12 + st * t * (tsc / 2 - t / 2) ** 2)
    inner = tsc / 2 - t
    for thickness, temperature in zip(thicknesses, temperatures):
        h = D(str(thickness))
        mid = inner - h / 2
        inner -= h
        half_p += D("0.85") * retained(CONCRETE_RETENTION, temperature, 1) * fc * st * h
        half_ei += D("0.35") * retained(CONCRETE_RETENTION, temperature, 2) * modulus * (st * h**3 / 12 + st * h * mid**2)
    pno_t, pe_t = 2 * half_p, PI**2 * 2 * half_ei / lc**2
    pn_t = D("0.32") ** ((pno_t / pe_t) ** D("0.3")) * pno_t
    available = D("0.90") * pn_t * D(wall_length) / st
    r = min(rating, D(8))
    return {"R_hours": r, "Pn_kN": pn / 1000, "Pno_T_kN": pno_t / 1000, "Pn_T_kN": pn_t / 1000, "phi_Pn_T_wall_kN": available / 1000,
            "ratio": max(D(required) / r, D(Pu) * 1000 / available)}


BARS_8 = [(510, "25.4", x, y) for x, y in ((241.3, 241.3), (241.3, 0), (241.3, -241.3), (0, 241.3), (0, -241.3),
                                          (-241.3, 241.3), (-241.3, 0), (-241.3, -241.3))]
BARS_ROUND = [(200, 16, x, y) for x, y in ((0, 55), (0, -55), (55, 0), (-55, 0))]
BARS_RECT = [(200, 16, x, y) for x, y in ((55, 55), (55, -55), (-55, 55), (-55, -55))]
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
    "bars-round-C": dict(kind="round_with_bars_compression", name='PTER8"X5.00MM', fy=345, fc=35, wc=2320, L=4000, Fysr=420,
                         bars=BARS_ROUND),
    "bars-round-M": dict(kind="round_with_bars_flexure", name='PTER8"X5.00MM', fy=345, fc=35, wc=2320, Fysr=420, bars=BARS_ROUND),
    "bars-rect-M": dict(kind="rect_with_bars_flexure", name="PTE200X200X7MM", fy=345, fc=35, Fysr=420, bars=BARS_RECT),
    "a2-C": dict(kind="appendix_2_compression", name="PTE200X200X7MM", fy=345, fc=83, wc=2320, L=4000),
    "a2-M": dict(kind="appendix_2_flexure", name="PTE200X200X7MM", fy=345, fc=83),
    "a2-PM": dict(kind="appendix_2_interaction", name="PTE200X200X7MM", fy=345, fc=83, wc=2320, L=4000, Pu=1500, Mu=60),
    "a2-high-Fy-M": dict(kind="appendix_2_flexure", name="PTE200X200X7MM", fy=600, fc=35),
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
    "so-sway": dict(kind="second_order", name="PTE200X200X7MM", fy=345, fc=35, wc=2320, L=4000, Pnt=800, Plt=100, Mnt=40, Mlt=30,
                    M1_M2=-0.5, Pstory=20000, Pmf=8000, H=500, story=4000, drift=10),
    "so-transverse": dict(kind="second_order", name="PTE200X200X7MM", fy=345, fc=35, wc=2320, L=4000, Pnt=1200, Plt=0, Mnt=40, Mlt=0,
                          M1_M2=None, Pstory=20000, Pmf=0, H=500, story=4000, drift=4),
    "lt-steel": dict(kind="load_transfer_filled", name="PTE200X200X7MM", fy=345, fc=35, wc=2320, L=3000, applied_to="steel", Pr=800,
                     A1=9000, Lin=300),
    "lt-concrete": dict(kind="load_transfer_filled", name="PTE200X200X7MM", fy=345, fc=35, wc=2320, L=3000, applied_to="concrete", Pr=800,
                        A1=9000),
    "lt-both": dict(kind="load_transfer_filled", name="PTE200X200X7MM", fy=345, fc=35, wc=2320, L=3000, applied_to="both", Pr=800,
                    A1=9000, steel_fraction=0.4),
    "lt-round": dict(kind="load_transfer_filled", name='PTER6"X6.00MM', fy=345, fc=35, wc=2320, L=3000, applied_to="steel", Pr=300,
                     Lin=200, round_=True),
    "lt-slender": dict(kind="load_transfer_filled", name="PTE100X40X1.5MM", fy=500, fc=35, wc=2320, L=1500, applied_to="concrete", Pr=100,
                       A1=2000),
    "lt-encased": dict(kind="load_transfer_encased", name="W10X45", fy=345, fc=35, H=610, B=610, Fysr=420, bars=BARS_8, applied_to="steel",
                       Pr=5000, A1=80000),
    "tc-encased": dict(kind="tension_control", name="W10X45", fy=345, fc=35, H=610, B=610, Fysr=420, bars=BARS_8),
    "box-C": dict(kind="box_compression", B=400, H=300, t=12, fy=345, fc=35, wc=2320, L=4000),
    "box-M": dict(kind="box_flexure", B=400, H=300, t=12, fy=345, fc=35),
    "box-V": dict(kind="box_shear", B=400, H=300, t=12, fy=345, fc=35),
    "biaxial-filled-low": dict(kind="biaxial", member="filled", name="PTE200X200X7MM", fy=345, fc=35, wc=2320, L=3000, Pu=100, Mux=40,
                               Muy=30),
    "biaxial-filled-high": dict(kind="biaxial", member="filled", name="PTE200X200X7MM", fy=345, fc=35, wc=2320, L=3000, Pu=1200, Mux=20,
                                Muy=15),
    "biaxial-encased": dict(kind="biaxial", member="encased", name="W10X45", fy=345, fc=35, wc=2320, L=4267, H=610, B=610, Fysr=420,
                            bars=BARS_8, Pu=6000, Mux=500, Muy=400),
    "service-low": dict(kind="service_filled", name="PTE200X200X7MM", fy=345, fc=35, wc=2320, L=3000, Pu=50),
    "service-high": dict(kind="service_filled", name="PTE200X200X7MM", fy=345, fc=35, wc=2320, L=3000, Pu=800),
    "service-round": dict(kind="service_round", name='PTER6"X6.00MM', fy=345, fc=35, wc=2320, L=3000, Pu=100),
    "wall-slender-C": dict(kind="wall_slender", fy=345, fc=35, L=3000, tsc=300, t=10, tf=20, b=500),
    "wall-stiffness": dict(kind="wall_stiffnesses", fc=35, wc=2320, L=3000, tsc=300, t=10, tf=20),
    "cwall-major": dict(kind="c_wall_case", fy=345, fc=35, wc=2320, L=6000, W=2500, tsc_w=400, tsc_f=500, tp=16, mode="major"),
    "cwall-tips": dict(kind="c_wall_case", fy=345, fc=35, wc=2320, L=6000, W=2500, tsc_w=400, tsc_f=500, tp=16, mode="tips"),
    "cwall-web": dict(kind="c_wall_case", fy=345, fc=69, wc=2320, L=6000, W=800, tsc_w=400, tsc_f=500, tp=10, mode="web"),
    "cwall-tension": dict(kind="c_wall_case", fy=345, fc=35, wc=2320, L=6000, W=2500, tsc_w=400, tsc_f=500, tp=16, mode="tips", P=-20000),
    "cwall-comp-flange": dict(kind="c_wall_case", fy=345, fc=35, wc=2320, L=6000, W=2500, tsc_w=400, tsc_f=500, tp=16, mode="web", P=40000),
    "cwall-comp-web": dict(kind="c_wall_case", fy=345, fc=35, wc=2320, L=9144, W=4267, tsc_w=356, tsc_f=610, tp=12.7, mode="web", P=54700),
    "cb-M": dict(kind="coupling_flexure", b=450, h=600, tf=20, tw=12, fy=345, fc=40),
    "cb-V": dict(kind="coupling_shear", b=450, h=600, tf=20, tw=12, fy=345, fc=40),
    "fire-wall": dict(kind="wall_fire_oracle", fy=345, fc=40, wc=2320, height=5000, wall_length=3300, tsc=600, t=14, st=300, Pu=16000,
                      plate_T=1000, thicknesses=[40, 40, 40, 40, 42, 42, 42],temperatures=[780, 500, 370, 280, 200, 120, 60], required=3),
}
FUNCTIONS = {"filled_compression": filled_compression, "filled_rect_flexure": filled_rect_flexure,
             "filled_round_flexure": filled_round_flexure, "filled_shear": filled_shear,
             "encased_compression": encased_compression, "encased_tension": encased_tension,
             "encased_flexure": encased_flexure, "beam_flexure": beam_flexure, "i5": i5,
             "wall_compression": wall_compression, "wall_tension": wall_tension, "wall_moment": wall_moment,
             "wall_shear": wall_shear_oracle, "wall_interaction": wall_interaction, "anchor": anchor_oracle,
             "round_with_bars_compression": round_with_bars_compression, "round_with_bars_flexure": round_with_bars_flexure,
             "rect_with_bars_flexure": rect_with_bars_flexure, "appendix_2_compression": appendix_2_compression,
             "appendix_2_flexure": appendix_2_flexure, "appendix_2_interaction": appendix_2_interaction,
             "second_order": second_order, "load_transfer_filled": load_transfer_filled,
             "load_transfer_encased": load_transfer_encased, "tension_control": tension_control, "box_compression": box_compression,
             "box_flexure": box_flexure, "box_shear": box_shear, "biaxial": biaxial, "service_filled": service_filled,
             "service_round": service_round, "wall_slender": wall_slender, "wall_stiffnesses": wall_stiffnesses,
             "c_wall_case": c_wall_case, "coupling_flexure": coupling_flexure, "coupling_shear": coupling_shear,
             "wall_fire_oracle": wall_fire_oracle}


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
