"""Composite beams with steel anchors: I3.2 positive flexure, I8.2 anchors and their detailing; A-4-20 under fire."""
import math

from ...codes.aisc_360_22 import appendix_4 as a4
from ...codes.aisc_360_22 import composite as eq
from ..fire import steel_at_temperature, with_fire
from .common import (
    blocked,
    flexure_output,
    incomplete,
    require_properties,
    requirement_row,
)


def _anchor_factors(beam, section):
    """Rg and Rp of I8.2a."""
    deck = beam.deck
    if deck is None:
        return 1.0, 0.75
    if deck.orientation == "parallel":
        return (1.0 if deck.wr / deck.hr >= 1.5 else 0.85), 0.75
    if deck.emid_ht_at_least_50 is None:
        incomplete("Deck perpendicular a la viga: indique composite.beam.deck.emid_ht_at_least_50 (I8.2a).", section,
                    ["composite.beam.deck.emid_ht_at_least_50"])
    per_rib = beam.studs.per_rib
    return (1.0 if per_rib == 1 else 0.85 if per_rib == 2 else 0.7), (0.75 if deck.emid_ht_at_least_50 else 0.6)



def _beam_anchors(beam):
    return [(name, anchors) for name, anchors in (("studs", beam.studs), ("channels", beam.channels)) if anchors]



def missing_anchor_detailing(beam) -> list[str]:
    """Fields that I8.2d needs and the input does not give."""
    out = []
    for name, anchors in _beam_anchors(beam):
        field, detail = f"composite.beam.{name}.detailing", anchors.detailing
        if detail is None:
            out.append(field)
            continue
        if getattr(anchors, "per_rib", 1) > 1 and detail.transverse_spacing is None:
            out.append(f"{field}.transverse_spacing")
        if beam.deck is None and detail.lateral_cover is None:
            out.append(f"{field}.lateral_cover")
        if detail.free_edge and detail.free_edge_distance is None:
            out.append(f"{field}.free_edge_distance")
    return out



def _anchor_detailing_requirements(name, anchors, beam, concrete):
    """I8.2d for one type of anchor, in the sense of the moment that uses it."""
    detail, deck = anchors.detailing, beam.deck
    s, label = detail.longitudinal_spacing, "pernos" if name == "studs" else "canales"
    out = []
    if name == "studs":
        perpendicular = deck is not None and deck.orientation == "perpendicular"
        s_min = (4.0 if perpendicular else 6.0) * anchors.d
        out.append(
            requirement_row(f"{name}_s_min", "I8.2d(d)", s >= s_min, "Separación longitudinal mínima de pernos.", s, f"≥ {s_min:g} mm")
        )
        if detail.transverse_spacing is not None:
            s_t = 4.0 * anchors.d
            out.append(requirement_row(f"{name}_s_transverse", "I8.2d(d)", detail.transverse_spacing >= s_t,
                                    "Separación transversal mínima de pernos.", detail.transverse_spacing, f"≥ {s_t:g} mm"))
    s_max = min(8.0 * (beam.tc + (deck.hr if deck else 0.0)), 900.0)
    out.append(
        requirement_row(
            f"{name}_s_max", "I8.2d(e)", s <= s_max, f"Separación máxima de {label} (8 veces la losa total o 900 mm).", s, f"≤ {s_max:g} mm"
        )
    )
    if deck is None:
        out.append(requirement_row(f"{name}_cover", "I8.2d(b)", detail.lateral_cover >= 25.0, f"Recubrimiento lateral de {label}.",
                                detail.lateral_cover, "≥ 25 mm"))
    if detail.free_edge:
        edge = 250.0 if concrete.lightweight else 200.0
        out.append(
            requirement_row(
                f"{name}_free_edge",
                "I8.2d(c)",
                detail.free_edge_distance >= edge,
                f"Distancia de {label} al borde libre en la dirección del cortante.",
                detail.free_edge_distance,
                f"≥ {edge:g} mm",
            )
        )
    out.append(
        requirement_row(
            f"{name}_distribution",
            "I8.2d(a)",
            True,
            f"Distribución de {label}.",
            "uniforme" if detail.distribution == "uniform" else "según documentos de diseño",
            "uniforme o según documentos de diseño",
        )
    )
    return out



def beam_requirements(beam, section, concrete):
    """I3.2c and I8.1 to I8.2: the geometric limits that the input declares."""
    out = []
    deck, studs = beam.deck, beam.studs
    if deck:
        out += [requirement_row("hr", "I3.2c.1(a)", deck.hr <= 75.0, "Altura nominal de nervio ≤ 75 mm."),
                requirement_row("wr", "I3.2c.1(a)", deck.wr >= 50.0, "Ancho medio de nervio ≥ 50 mm."),
                requirement_row("tc", "I3.2c.1(c)", beam.tc >= 50.0, "Espesor de losa sobre el deck ≥ 50 mm.")]
    if studs:
        out.append(requirement_row("dsa_max", "I8.1", studs.d <= (19.0 if deck else 25.0),
                                "Diámetro de perno ≤ 19 mm (hasta 25 mm solo en losa maciza)."))
        out.append(requirement_row("dsa_tf", "I8.1", studs.over_web or studs.d <= 2.5 * section.tf,
                                "Diámetro ≤ 2.5 tf si el perno no está sobre el alma."))
        out.append(requirement_row("length", "I8.2", studs.length >= 4 * studs.d, "Longitud del perno ≥ 4 diámetros."))
        if deck:
            out += [requirement_row("stud_above_deck", "I3.2c.1(b)", studs.length - deck.hr >= 38.0,
                                 "El perno debe sobresalir al menos 38 mm del deck."),
                    requirement_row("stud_cover", "I3.2c.1(b)", deck.hr + beam.tc - studs.length >= 13.0,
                                 "Recubrimiento sobre el perno ≥ 13 mm.")]
    if beam.moment == "positive" and not missing_anchor_detailing(beam):
        for name, anchors in _beam_anchors(beam):
            out += _anchor_detailing_requirements(name, anchors, beam, concrete)
    return out



def beam_flexure(case, section):
    """I3.2a(a) positive flexure; I3.2b steel section alone for negative flexure (Chapter F)."""
    beam, Fy = case.composite.beam, case.material.Fy
    if beam.moment == "negative":
        return None
    require_properties(section, "area", "d", "bf", "tf", "tw", "h_tw_ratio")
    if section.h_tw_ratio > 3.76 * math.sqrt(eq.E_STEEL / Fy):
        blocked("h/tw > 3.76·√(E/Fy): I3.2a(b) exige superposición elástica con datos de apuntalamiento, no implementada.",
                 section, h_tw=section.h_tw_ratio)
    if beam.studs is None and beam.channels is None:
        incomplete("La viga compuesta requiere conectores: indique composite.beam.studs o channels (I3.2d).", section,
                    ["composite.beam.studs", "composite.beam.channels"])
    if beam.channels is not None and beam.deck is not None:
        blocked("I8.2b cubre conectores de canal en losa maciza, no sobre deck.", section)
    missing = missing_anchor_detailing(beam)
    if missing:
        incomplete("La viga compuesta debe declarar el detallado de sus conectores (I8.2d).", section, missing)
    concrete = case.composite.concrete
    Ec = eq.concrete_modulus(wc=concrete.wc, fc=concrete.fc)
    left = beam.left_beam_spacing / 2 if beam.left_beam_spacing else beam.left_edge_distance
    right = beam.right_beam_spacing / 2 if beam.right_beam_spacing else beam.right_edge_distance
    width = eq.effective_slab_width(span=beam.span, left=left, right=right)
    b, hr = width["b_mm"], beam.deck.hr if beam.deck else 0.0
    sum_qn = 0.0
    anchors: dict = {}
    if beam.studs:
        Rg, Rp = _anchor_factors(beam, section)
        Asa = math.pi * beam.studs.d**2 / 4
        stud = eq.stud_strength(Asa=Asa, fc=concrete.fc, Ec=Ec, Rg=Rg, Rp=Rp, Fu=beam.studs.Fu)
        sum_qn += beam.studs.count * stud["Qn"]
        anchors.update(Rg=Rg, Rp=Rp, Qn_stud_kN=stud["Qn"] / 1000.0)
    if beam.channels:
        c = beam.channels
        qn = eq.channel_strength(tf=c.tf, tw=c.tw, la=c.la, fc=concrete.fc, Ec=Ec)
        sum_qn += c.count * qn
        anchors["Qn_channel_kN"] = qn / 1000.0
    crushing, steel = (
        eq.beam_slab_crushing(fc=concrete.fc, b=b, tc=beam.tc),
        eq.beam_steel_yielding(Fy=Fy, As=section.area),
    )  # ribs neglected (I3.2c)
    C = min(crushing, steel, sum_qn)                                            # I3-1c
    a = eq.beam_block_depth(C=C, fc=concrete.fc, b=b)
    out = eq.beam_plastic_moment(C=C, a=a, Ycon=beam.tc + hr, Fy=Fy, As=section.area, d=section.d, bf=section.bf,
                                 tf=section.tf, tw=section.tw)
    degree = sum_qn / min(crushing, steel)
    mode = {"provision": "I3.2a(a)", "equation": "Distribución plástica (I3.2a)", "b_mm": b, "Ycon_mm": beam.tc + hr,
            "Vp_crushing_kN": crushing / 1000.0, "Vp_steel_kN": steel / 1000.0, "SumQn_kN": sum_qn / 1000.0,
            "C_kN": C / 1000.0, "a_mm": a, "PNA": out["pna"], "x_mm": out["x_mm"], "degree_of_composite_action": degree,
            **anchors, "Mn_kNm": out["Mn"] / 1e6}
    requirements = beam_requirements(beam, section, concrete)
    notes = []
    hot = steel_at_temperature(case)
    if hot:
        kcb = a4.composite_beam_factor(hot["T_C"])
        if kcb == 0.0:
            blocked("Tabla A-4.2.4: la resistencia de la viga compuesta se anula a 1100 °C del ala inferior.", section, T_C=hot["T_C"])
        at_temperature = a4.composite_beam_strength(Mn=out["Mn"], kcb=kcb)
        mode.update(
            provision="I3.2a(a); Apéndice 4, 4.2.4d(f)",
            equation=at_temperature["equation"],
            Mn_ambient_kNm=out["Mn"] / 1e6,
            kcb=kcb,
            Mn_kNm=at_temperature["Mn"] / 1e6,
        )
    # Commentary I3.2d: conditions under which slip capacity is not a concern.
    if not (beam.span <= 9100.0 or degree >= 0.5 or sum_qn / (beam.span / 2) >= 230.0):
        notes.append("I3.2d: revise la ductilidad de la conexión; no se cumple ninguna condición del Commentary "
                     "(luz ≤ 9.1 m, acción compuesta ≥ 50 %, o conectores ≥ 230 kN/m).")
    return with_fire(flexure_output(case, section, mn_mode=mode, requirements=requirements, notes=notes, provisions=["I1", "I3.2", "I8.2"]),
                     hot, "4.2.4d(f)")
