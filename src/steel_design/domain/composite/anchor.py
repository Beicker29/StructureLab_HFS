"""Anchors of composite components (I8.3)."""
import math

from ...codes.aisc_360_22 import composite as eq
from ...models import SteelCase
from ...sections.models import Section
from .common import blocked, check_family, composite_result, requirement_row


def composite_anchor(case: SteelCase, section: Section) -> dict:
    """I8.3: one steel headed stud or channel anchor of a composite component."""
    check_family(case, section)
    if case.composite.kind == "beam":
        blocked("Los anclajes de vigas compuestas se calculan con I8.2 (composite.beam), no con I8.3.", section)
    anchor, concrete = case.composite.anchor, case.composite.concrete
    Qrv, Qrt = anchor.Qrv, anchor.Qrt
    if anchor.type == "channel":
        if Qrt:
            blocked("I8.3d cubre conectores de canal a cortante; la tracción no está cubierta.", section)
        Ec = eq.concrete_modulus(wc=concrete.wc, fc=concrete.fc)
        qn = eq.channel_strength(tf=anchor.tf, tw=anchor.tw, la=anchor.la, fc=concrete.fc, Ec=Ec) / 1000.0
        qcv: float | None = eq.PHI_CHANNEL * qn
        mode = {"limit_state": "anchor_shear", "provision": "I8.3d", "applies": True, "equation": "I8-2", "Qnv_kN": qn,
                "phi_v": eq.PHI_CHANNEL, "Qcv_kN": qcv, "Qrv_kN": Qrv, "ratio": Qrv / qcv}
        requirements = [requirement_row("spacing", "I8.3e(d)", anchor.spacing <= 600.0, "Separación de canales ≤ 600 mm.")]
        return composite_result(case, section, modes={"V": mode}, governing="V", provisions=["I8.3d"], requirements=requirements,
                       ratio=mode["ratio"])
    d, h = anchor.d, anchor.height
    Asa = math.pi * d**2 / 4
    lightweight = concrete.lightweight
    if Qrt and Qrv and lightweight:
        blocked("Perno a cortante y tracción en concreto liviano: I8.3 remite a ACI 318, Capítulo 17.", section)
    if Qrt and (anchor.head_diameter is None or anchor.head_diameter < 1.6 * d):
        blocked("Perno a tracción: el diámetro de la cabeza debe declararse y ser ≥ 1.6·d; si no, I8.3 remite a ACI 318.",
                 section, fields=["composite.anchor.head_diameter"])
    near_edge = anchor.edge_distance is not None and anchor.edge_distance < 1.5 * h
    close = anchor.spacing < 3 * h
    qcv = None
    qct: float | None = None
    terms: dict = {}
    if Qrv:
        qnv = eq.stud_shear_strength(Fu=anchor.Fu, Asa=Asa) / 1000.0
        if anchor.breakout_in_shear:
            if anchor.reinforcement_shear is None:
                blocked("Rotura del concreto a cortante aplicable: indique composite.anchor.reinforcement_shear (I8.3a(a)); "
                         "la alternativa de ACI 318, Capítulo 17, no está implementada.", section)
            qnv = min(qnv, anchor.reinforcement_shear)
        qcv = eq.PHI_STUD_V * qnv
        terms.update(Qnv_kN=qnv, Qcv_kN=qcv, Qrv_kN=Qrv)
    if Qrt:
        qnt = eq.stud_tension_strength(Fu=anchor.Fu, Asa=Asa) / 1000.0
        if near_edge or close:
            if anchor.reinforcement_tension is None:
                blocked("Borde o separación por debajo de 1.5h o 3h: indique composite.anchor.reinforcement_tension (I8.3b(a)); "
                         "la alternativa de ACI 318, Capítulo 17, no está implementada.", section)
            qnt = min(qnt, anchor.reinforcement_tension)
        qct = eq.PHI_STUD_T * qnt
        terms.update(Qnt_kN=qnt, Qct_kN=qct, Qrt_kN=Qrt)
    if Qrv and Qrt:
        ratio, equation, provision = eq.stud_interaction(Qrv=Qrv, Qcv=qcv, Qrt=Qrt, Qct=qct), "I8-5", "I8.3c"
    elif Qrv:
        ratio, equation, provision = Qrv / qcv, "I8-3", "I8.3a"
    else:
        ratio, equation, provision = Qrt / qct, "I8-4", "I8.3b"
    minimum = ((10 if lightweight else 8) if Qrt else (7 if lightweight else 5))
    d_limit = 25.0 if anchor.solid_slab and not Qrt else 19.0
    requirements = [
        requirement_row("h/d", "I8.3", h / d >= minimum, f"Altura del perno ≥ {minimum} diámetros."),
        requirement_row("spacing_min", "I8.3e(b)", anchor.spacing >= 4 * d, "Separación de pernos ≥ 4 diámetros."),
        requirement_row("spacing_max", "I8.3e(c)", anchor.spacing <= 32 * d, "Separación de pernos ≤ 32 diámetros."),
        requirement_row("dsa_max", "I8.1", d <= d_limit, f"Diámetro de perno ≤ {d_limit:g} mm."),
        requirement_row("dsa_t", "I8.1", anchor.over_web or d <= 2.5 * anchor.base_thickness,
                     "Diámetro ≤ 2.5 veces el espesor del metal base, salvo sobre un alma."),
    ]
    mode = {"limit_state": "anchor_strength", "provision": provision, "applies": True, "equation": equation, "Asa_mm2": Asa,
            **terms, "ratio": ratio}
    return composite_result(case, section, modes={"Q": mode}, governing="Q", provisions=[provision], requirements=requirements,
                   ratio=ratio)
