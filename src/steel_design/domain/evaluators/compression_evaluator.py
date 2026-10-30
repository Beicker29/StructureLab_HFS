"""Canonical Chapter E elastic modes and capacities, shared with H/I consumers.

No routing registry, transport, or presentation dependencies. Local capacity
is not a member coverage decision. Source/domain constraints precede arithmetic.
"""
import math

from ...codes.aisc_360_22 import axial_calc
from ...models import SteelCase
from ...sections.models import Section
from ..errors import RuleNotImplementedError, IncompleteSectionDataError
from ..design_methods import require_case_method
from .compression_domain import compression_classification, require_compression_domain, requires_torsional_mode

def _safe_klr(K: float, L: float, r: float | None) -> float | None:
    if r is None or r <= 0.0 or K <= 0.0 or L <= 0.0:
        return None
    return (K * L) / r


def flexural_components(case: SteelCase, section: Section) -> dict:
    klr_x = _safe_klr(case.factors.Kx, case.lengths.Lx, section.rx)
    klr_y = _safe_klr(case.factors.Ky, case.lengths.Ly, section.ry)
    fe_x = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Kx, case.lengths.Lx, section.rx or 0.0)
    fe_y = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Ky, case.lengths.Ly, section.ry or 0.0)
    axis = "x"
    fe = fe_x
    if (fe_y > 0.0 and fe_x <= 0.0) or (fe_y > 0.0 and fe_y <= fe_x):
        axis = "y"
        fe = fe_y
    if fe <= 0.0:
        axis = "none"
    return {
        "klr_x": klr_x,
        "klr_y": klr_y,
        "fe_x_mpa": fe_x,
        "fe_y_mpa": fe_y,
        "fe_governing_mpa": fe,
        "governing_axis": axis,
    }


def torsional_components(case: SteelCase, section: Section) -> dict:
    ro_raw = section.ro
    ro_source = "catalog"
    ro_value = ro_raw
    if ro_value is None or ro_value <= 0.0:
        ro_value = axial_calc.calculate_ro_for_double_symmetric(section.area, section.ix or 0.0, section.iy or 0.0)
        ro_source = "derived_from_ix_iy_ag"

    fe_z = axial_calc.calculate_Fe_torsional(
        case.material.E,
        axial_calc.NORMATIVE_G_MPA,
        section.j or 0.0,
        section.cw or 0.0,
        case.factors.Kz,
        case.lengths.Lz,
        section.area,
        ro_value,
    )
    fe_x = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Kx, case.lengths.Lx, section.rx or 0.0)
    fe_y = axial_calc.calculate_Fe_flexural(case.material.E, case.factors.Ky, case.lengths.Ly, section.ry or 0.0)
    klr_x = _safe_klr(case.factors.Kx, case.lengths.Lx, section.rx)
    klr_y = _safe_klr(case.factors.Ky, case.lengths.Ly, section.ry)
    klr_z = _safe_klr(case.factors.Kz, case.lengths.Lz, ro_value)

    kz_lz = case.factors.Kz * case.lengths.Lz
    warping_term = None
    stvenant_term = None
    torsional_stiffness = None
    torsional_denominator = None
    if kz_lz > 0.0 and section.cw and section.cw > 0.0:
        warping_term = ((math.pi**2 * case.material.E * section.cw) / (kz_lz**2))
    if section.j and section.j > 0.0:
        stvenant_term = axial_calc.NORMATIVE_G_MPA * section.j
    if warping_term is not None and stvenant_term is not None:
        torsional_stiffness = warping_term + stvenant_term
    if section.area > 0.0 and ro_value and ro_value > 0.0:
        torsional_denominator = section.area * (ro_value**2)

    flexural_torsional_terms = None
    fe_governing = fe_z if fe_z > 0.0 else 0.0
    mode = "torsional"
    if section.type.upper() == "CHANNEL":
        # S22 E4(b), User Note p.16.1-42: x is the channel symmetry axis.
        # Do not replace Fey globally: other singly symmetric families differ.
        fe_governing = axial_calc.calculate_Fe_flexural_torsional(fe_x, fe_z, section.H)
        mode = "flexural_torsional"
        flexural_torsional_terms = {"symmetry_axis": "x", "H": section.H,
                                   "Fe_symmetry_mpa": fe_x, "Fez_mpa": fe_z,
                                   "equation": "E4-3 with Fex (channel symmetry)"}

    return {
        "ro_mm": ro_value,
        "ro_source": ro_source,
        "klr_x": klr_x,
        "klr_y": klr_y,
        "klr_z": klr_z,
        "fe_x_mpa": fe_x,
        "fe_y_mpa": fe_y,
        "fe_z_mpa": fe_z,
        "fe_governing_mpa": fe_governing,
        "e4_mode": mode,
        "warping_term_n": warping_term,
        "stvenant_term_n": stvenant_term,
        "torsional_stiffness_n": torsional_stiffness,
        "torsional_denominator_mm4": torsional_denominator,
        "flexural_torsional_terms": flexural_torsional_terms,
    }


def effective_compression_area(case: SteelCase, section: Section, fn: float) -> dict:
    """E7 physical plate inventory from declared B4 ratios and thicknesses.

    The ratios already denote B4 widths (not outside PTE dimensions). This
    conversion does not infer corner radii, nominal/design thickness or contact.
    """
    family = section.type.upper()
    if family == 'CIRCULAR_HSS':
        # E7.2 requires outside diameter and design thickness. Derive the
        # resistance ratio from those physical values, never from inside D.
        return axial_calc.calculate_e7_round_area(Ag=section.area, D_over_t=section.od/section.tdes,
                                                  E=case.material.E, Fy=case.material.Fy)
    classification = compression_classification(case, section)['elements']
    if family == 'W':
        plates = [('flange', 4, section.tf, 'UNSTIFFENED'), ('web', 1, section.tw, 'STIFFENED')]
    elif family == 'CHANNEL':
        plates = [('flange', 2, section.tf, 'UNSTIFFENED'), ('web', 1, section.tw, 'STIFFENED')]
    elif family == 'RECTANGULAR_HSS':
        plates = [('wall_b', 2, section.tdes, 'HSS_WALL'), ('wall_h', 2, section.tdes, 'HSS_WALL')]
    else:
        raise RuleNotImplementedError('E7 plate inventory is not implemented.', details={'family': family})
    return axial_calc.calculate_e7_plate_area(Ag=section.area, Fn=fn, Fy=case.material.Fy,
        elements=[{'count': count, 't': thickness, 'b': classification[key]['ratio']*thickness,
                   'lambda_r': classification[key]['lambda_r'], 'kind': kind}
                  for key, count, thickness, kind in plates])


def evaluate_compression(case: SteelCase, section: Section) -> dict:
    """All currently supported E modes, without a favorable coverage claim.

    E7 evaluates Fn*Ae separately for every applicable global mode. No QFy
    substitution and no comparison of a slender-member demand against Fn*Ag.
    H/I call this same owner for their bare-steel compression component.
    """
    require_case_method(case)
    classification = compression_classification(case, section)
    slender = classification['is_slender']
    require_compression_domain(case, section, reference='E7' if slender else 'E3')
    components = {'E3': flexural_components(case, section)}
    if requires_torsional_mode(case, section):
        require_compression_domain(case, section, reference='E7' if slender else 'E4')
        components['E4'] = torsional_components(case, section)
    modes = {}
    for name, elastic in components.items():
        fn = axial_calc.calculate_Fcr(case.material.Fy, elastic['fe_governing_mpa'])
        try:
            area = effective_compression_area(case, section, fn) if slender else {'Ae_mm2': section.area, 'Ag_mm2': section.area}
        except ValueError as exc:
            raise IncompleteSectionDataError(str(exc), code='COMPRESSION_DATA_INCOMPLETE', details={
                'reference': 'E7', 'section': section.name, 'findings': ['F-35', 'F-48']}) from exc
        pn = axial_calc.calculate_Pn(fn, area['Ae_mm2'])
        modes[name] = {'elastic': elastic, 'Fn_mpa': fn, 'area': area, 'Pn_N': pn,
                       'available_kN': axial_calc.calculate_available_compressive_strength(pn, case.design_method)}
    governing = min(modes, key=lambda key: modes[key]['available_kN'])
    return {'available_kN': modes[governing]['available_kN'], 'governing_mode': governing,
            'provision': 'E7' if slender else governing, 'modes': modes,
            'classification': classification, 'design_method': case.design_method.value,
            'design_factor': axial_calc.compression_design_factor(case.design_method)}

