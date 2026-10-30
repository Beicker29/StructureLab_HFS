"""HFS-031R normative corrections; independent references, not accreditation.

Arithmetic tests do not discharge applicability/data/coverage obligations.
Historical HFS-031 oracles remain unchanged, including rounded table-c2 values.
"""
import json
import math
from decimal import Decimal as D, localcontext
from pathlib import Path

import pytest

from steel_design.codes.aisc_360_22 import axial_calc as calc


BANK = json.loads((Path(__file__).parent/'fixtures/hfs031r/formulas.json').read_text(encoding='utf-8'))['cases']


def close(value):
    # 60-digit Decimal to IEEE-754: tighter than 1e-10 engineering bank tolerance.
    return pytest.approx(float(value), rel=2e-13, abs=2e-10)


@pytest.mark.parametrize('key', [k for k in BANK if k.startswith('E4-cubic-')])
def test_e4_cubic_smallest_root_independent(key):
    o = BANK[key]
    actual = calc.calculate_Fe_unsymmetric(*(float(o[k]) for k in ('Fex', 'Fey', 'Fez', 'xo', 'yo', 'ro')))
    assert actual['Fe_mpa'] == close(o['Fe'])
    assert actual['H'] == close(o['H'])
    assert abs(actual['normalized_residual']) < 1e-14
    assert actual['bracket_mpa'][1]-actual['bracket_mpa'][0] <= 2e-13*float(o['Fe'])


@pytest.mark.parametrize('stresses', [(100, 100, 100), (100, 100, 200), (200, 300, 50),
                                     (1e-12, 1000, 1e8), (100, 1e-12, 1e8)])
def test_e4_cubic_uncoupled_repeated_and_dissimilar_roots(stresses):
    result = calc.calculate_Fe_unsymmetric(*stresses, 0, 0, 100)
    assert result['Fe_mpa'] == pytest.approx(min(stresses), rel=2e-14, abs=0)


@pytest.mark.parametrize('h', [1, .9, .01, 1e-12])
@pytest.mark.parametrize('a,b', [(100, 100), (80, 2000), (1e-12, 1e8)])
def test_e4_quadratic_stable_against_independent_high_precision(h, a, b):
    with localcontext() as ctx:
        ctx.prec = 80
        da, db, dh = map(lambda x: D(str(x)), (a, b, h))
        expected = (da+db)/(2*dh)*(1-(1-4*da*db*dh/(da+db)**2).sqrt())
    assert calc.calculate_Fe_flexural_torsional(a, b, h) == pytest.approx(float(expected), rel=2e-14, abs=0)


@pytest.mark.parametrize('direction', ['MINOR_AXIS_LATERAL', 'MAJOR_AXIS_LATERAL'])
@pytest.mark.parametrize('method', ['LRFD', 'ASD'])
def test_e4_offset_independent_stress_nominal_and_available(direction, method):
    o = BANK['E4-offset-'+direction]
    xa, ya = (0, 150) if direction == 'MINOR_AXIS_LATERAL' else (50, 0)
    result = calc.calculate_Fe_offset(E=200000, G=77200, J=100000, Ix=50000000,
        Iy=10000000, Ag=5000, rx=100, ry=math.sqrt(2000), ho=280,
        Lcz=6000, xa=xa, ya=ya, bracing=direction)
    assert result['Fe_mpa'] == close(o['Fe'])
    assert result['ro2_mm2'] == close(o['ro2'])
    fn = calc.calculate_Fcr(345, result['Fe_mpa'])
    assert fn == close(o['Fn'])
    pn = calc.calculate_Pn(fn, 5000)
    assert pn == close(o['Pn_N'])
    assert calc.calculate_available_compressive_strength(pn, method) == close(o[method+'_kN'])


@pytest.mark.parametrize('config,s,leg,ratio,principal,value,equation', [
    ('A', 40, 'EQUAL', 1, None, 102, 'E5-1'),
    ('A', 80, 'LONG', 1.5, None, 132, 'E5-1'),
    ('A', 100, 'LONG', 1.5, None, 157, 'E5-2'),
    ('A', 40, 'SHORT', 1.5, 100, 107, 'E5-1'),
    ('A', 40, 'SHORT', 1.5, 200, 190, 'E5-1'),
    ('B', 50, 'EQUAL', 1, None, 100, 'E5-3'),
    ('B', 75, 'LONG', 1.5, None, 120, 'E5-3'),
    ('B', 100, 'LONG', 1.5, None, 145, 'E5-4'),
    ('B', 50, 'SHORT', 1.5, 100, 107.5, 'E5-3'),
    ('B', 50, 'SHORT', 1.5, 200, 164, 'E5-3'),
    ('A', 134.4, 'EQUAL', 1, None, 200, 'E5-2'),
    ('B', 155, 'EQUAL', 1, None, 200, 'E5-4'),
    ('A', 180, 'EQUAL', 1, None, 257, 'E5-2'),
])
def test_e5_all_branches_short_leg_floors_and_eligibility(config,s,leg,ratio,principal,value,equation):
    actual = calc.calculate_e5_slenderness(s=s, configuration=config, connected_leg=leg,
                                          leg_ratio=ratio, principal_slenderness=principal)
    assert actual['effective_slenderness'] == close(value)
    assert actual['equation'] == equation
    assert actual['eligible_slenderness'] == (value <= 200)


@pytest.mark.parametrize('connector', ['SNUG_TIGHT', 'WELDED', 'PRETENSIONED_CLASS_A', 'PRETENSIONED_CLASS_B'])
@pytest.mark.parametrize('arrangement,ki', [('ANGLES_BACK_TO_BACK', '.5'), ('CHANNELS_BACK_TO_BACK', '.75'), ('OTHER', '.86')])
@pytest.mark.parametrize('spacing', [20, 40, 60])
def test_e6_modified_slenderness_all_detail_branches(connector, arrangement, ki, spacing):
    with localcontext() as ctx:
        ctx.prec = 50
        if connector == 'SNUG_TIGHT':
            value, eq = (D(10000)+D(spacing)**2).sqrt(), 'E6-1'
        elif spacing <= 40:
            value, eq = D(100), 'E6-2a'
        else:
            value, eq = (D(10000)+(D(ki)*spacing)**2).sqrt(), 'E6-2b'
    result = calc.calculate_e6_slenderness(s0=100, a_over_ri=spacing, connector=connector, arrangement=arrangement)
    assert result['modified_slenderness'] == close(value)
    assert result['equation'] == eq


@pytest.mark.parametrize('key', [k for k in BANK if k.startswith('E7-width-')])
def test_e7_widths_unrounded_equation_c2(key):
    o = BANK[key]
    result = calc.calculate_e7_effective_width(**{k: float(o[k]) for k in ('b','t','lambda_r','Fn','Fy')}, element_kind=o['kind'])
    for field, expected in [('be_mm','be'), ('Fel_mpa','Fel'), ('area_loss_mm2','area_loss'), ('c1','c1'), ('c2','c2')]:
        assert result[field] == close(o[expected]), (key, field)
    # At an exactly constructed mathematical threshold, decimal->binary can
    # choose either identical limiting expression. No tolerance changes design.
    if not key.endswith('-1'):
        assert result['equation'] == o['equation']
    assert result['be_mm'] <= float(o['b'])*(1+3e-16)


@pytest.mark.parametrize('ratio', [20, 50, 100, 200])
def test_e7_round_independent_areas_outside_pending_transition_interval(ratio):
    with localcontext() as ctx:
        ctx.prec = 50
        area = D(5000) if ratio <= D('.11')*200000/345 else (D('.038')*200000/(345*D(ratio))+D(2)/3)*5000
    assert calc.calculate_e7_round_area(Ag=5000, D_over_t=ratio, E=200000, Fy=345)['Ae_mm2'] == close(area)


@pytest.mark.parametrize('ratio', [.45*200000/345, 300])
def test_e7_round_strict_upper_limit(ratio):
    with pytest.raises(ValueError, match='strictly below'):
        calc.calculate_e7_round_area(Ag=5000, D_over_t=ratio, E=200000, Fy=345)


@pytest.mark.parametrize('normalized', [.11000001, .111, .113, .114, .115])
def test_e7_round_user_confirmed_bound_preserves_literal_area(normalized):
    ratio = normalized*200000/345
    literal = (.038/normalized+2/3)*5000
    actual = calc.calculate_e7_round_area(Ag=5000, D_over_t=ratio, E=200000, Fy=345)
    assert actual['Ae_equation_mm2'] == close(literal)
    assert actual['Ae_mm2'] == close(min(literal, 5000))
    assert actual['Ae_mm2'] <= 5000
    if normalized != .114:  # No rounded threshold is used in production.
        assert actual['gross_area_bound_applied'] == (normalized < .114)


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -1, 0, True, None])
def test_new_formula_boundaries_reject_invalid_required_input(bad):
    with pytest.raises(ValueError, match='finite and positive'):
        calc.calculate_e7_effective_width(b=bad, t=6, lambda_r=30, Fn=250, Fy=345, element_kind='STIFFENED')
    with pytest.raises(ValueError, match='finite and positive'):
        calc.calculate_Fe_unsymmetric(bad, 100, 200, 30, 40, 100)


@pytest.mark.parametrize('od,inside,tdes,nominal,given,expected', [
    (100, 90, 5, 6, None, 20),
    (100, None, 5, None, None, 20),
    (None, 90, 5, None, None, None),
    (100, 90, None, 5, None, None),
    (100, 90, 5, 6, 20.01, 20.01),  # Explicit source ratio is not rewritten.
])
def test_f12_loader_requires_outside_diameter_and_design_thickness(tmp_path,od,inside,tdes,nominal,given,expected):
    from openpyxl import Workbook
    from steel_design.sections.loader import load_sections_from_excel
    book = Workbook()
    sheet = book.active
    sheet.title = 'PTE_RED'
    sheet.append(['shape', 'A', 'OD', 'ID', 'tdes', 't', 'D/t'])
    sheet.append(['HSS_TEST', 1000, od, inside, tdes, nominal, given])
    path = tmp_path/'round.xlsx'
    book.save(path)
    section, = load_sections_from_excel(str(path))
    assert section.d_t_ratio == expected
    assert section.od == od
    assert section.id == inside
