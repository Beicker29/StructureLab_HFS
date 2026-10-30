"""Independent D/E audit, not blanket accreditation.

Expected values come from Decimal sheets authored from S22, never production.
Strict xfails assert the normative result (not the defective baseline).
Diagnostic tests separately prove numerical consequences and coverage safety.
"""
import json
import math
from pathlib import Path

import pytest

from steel_design.codes.aisc_360_22 import axial_calc, tension_calc
from steel_design.domain.evaluators.tension_evaluator import TensionEvaluator
from steel_design.domain.rules.axial_rules import AxialE3Rule, AxialE4Rule, AxialE5Rule, AxialE7Rule
from steel_design.domain.routing.profile_router import ProfileRouter
from steel_design.domain.errors import IncompleteSectionDataError, RuleNotImplementedError, ValidationError
from steel_design.engine import SteelDesignEngine
from steel_design.models import SteelCase
from steel_design.sections.models import Section
from steel_design.sections.repository import SectionRepository


BANK = json.loads((Path(__file__).parent/'fixtures/hfs031/oracles.json').read_text(encoding='utf-8'))['cases']
R_BANK = json.loads((Path(__file__).parent/'fixtures/hfs031r/formulas.json').read_text(encoding='utf-8'))['cases']
METHODS = ['LRFD', 'ASD']
# Decimal -> IEEE-754 plus exp/sqrt and printed constants: < 1e-10 relative;
# absolute 1e-8 kN (1e-5 N) is far below input/engineering precision.
REL, ABS = 1e-10, 1e-8


def expected(value):
    return pytest.approx(float(value), rel=REL, abs=ABS)


def required_capacity(rule, c, s, finding):
    # R0 contains these paths; it does NOT satisfy their numerical oracle.
    # Only the demonstrated quarantine is an expected absence of a capacity.
    # Unexpected exceptions still fail (xfail remains raises=AssertionError).
    try:
        return rule.check(c, s).capacity
    except RuleNotImplementedError as exc:
        if exc.code != "COMPRESSION_DOMAIN_BLOCKED" or finding not in exc.details.get("findings", []):
            raise
        raise AssertionError(f"{finding}: numerical implementation still unavailable under HFS-031R0 containment") from exc


def case(method='LRFD', pu=1, **extra):
    data = dict(section_name='audit', design_method=method, material=dict(Fy=345, Fu=450),
                loads=dict(Pu=pu), lengths=dict(Lx=1000, Ly=1000, Lz=1000),
                connection=dict(angle_compression_mode='one_leg'))
    data.update(extra)
    data['lengths'].setdefault('Lb', 1000)  # Required legacy field, no bending in these probes.
    return SteelCase(**data)


def run(c, s):
    repo = SectionRepository()
    repo.load([s])
    return SteelDesignEngine(repo).run(c)


@pytest.mark.parametrize('key', ['D2-800','D2-1000'])
@pytest.mark.parametrize('method', METHODS)
def test_d2_d3_declared_area_and_factors(key, method):
    o = BANK[key]
    c = case(method, -1, connection=dict(An=o['An'], U=float(o['U'])))
    s = Section(name='audit', type='SOLID_RECTANGULAR', A=1000)
    r = TensionEvaluator().evaluate(c,s)
    assert r['Ae_mm2'] == expected(o['Ae'])
    assert r['Pn_y_N'] == expected(o['Pn_y_N'])
    assert r['Pn_r_N'] == expected(o['Pn_r_N'])
    assert r['yielding_capacity'] == expected(o[method+'_kN'][0])
    assert r['rupture_capacity'] == expected(o[method+'_kN'][1])
    assert r['capacity'] == expected(min(map(float,o[method+'_kN'])))


@pytest.mark.parametrize('key', [k for k in BANK if k.startswith('E3-')])
@pytest.mark.parametrize('method', METHODS)
def test_e3_both_stress_branches_independent(key,method):
    o = BANK[key]
    fe = axial_calc.calculate_Fe_flexural(200000,1,float(o['s'])*30,30)
    assert fe == expected(o['Fe'])
    fn = axial_calc.calculate_Fcr(345,float(o['Fe']))
    assert fn == expected(o['Fn'])
    assert axial_calc.calculate_available_compressive_strength(fn*5000,method) == expected(o[method+'_kN'])


@pytest.mark.parametrize('method', METHODS)
@pytest.mark.parametrize('axis', ['x','y'])
def test_e3_rule_principal_axis_and_units(method,axis):
    o = BANK['E3-1']
    lengths = dict(Lx=float(o['s'])*50, Ly=float(o['s'])*20,Lz=1000)
    lengths['Ly' if axis=='x' else 'Lx'] /= 2
    c = case(method,lengths=lengths)
    s = Section(name='audit',type='W',A=5000,Ix=12500000,Iy=2000000,rx=50,ry=20,
                bf_2tf_ratio=5,h_tw_ratio=20)
    r = AxialE3Rule().check(c,s)
    assert r.capacity == expected(o[method+'_kN'])
    assert r.details['memory']['intermediate']['governing_axis'] == axis


def symmetric(method='LRFD', **offsets):
    o = BANK['E4-symmetric']
    s = Section(name='audit',type='W',A=float(o['A']),Ix=float(o['Ix']),Iy=float(o['Iy']),
                J=float(o['J']),Cw=float(o['Cw']),rx=100,ry=math.sqrt(2000),ho=300,
                bf_2tf_ratio=5,h_tw_ratio=20)
    c = case(method, lengths=dict(Lx=1000,Ly=1000,Lz=float(o['Lz'])), factors=offsets)
    return c,s


@pytest.mark.parametrize('method', METHODS)
def test_e4_double_symmetry_and_units(method):
    c,s = symmetric(method)
    r=AxialE4Rule().check(c,s)
    assert r.details['memory']['intermediate']['Fe_mpa'] == expected(BANK['E4-symmetric']['Fe'])
    assert r.capacity == expected(BANK['E4-symmetric'][method+'_kN'])


def channel(method='LRFD', *, omit_h=False):
    o=BANK['E4-channel']
    a,ix,iy,ro2=5000,50000000,10000000,24000
    cw=1000000
    j=(100*a*ro2-math.pi**2*200000*cw/1000**2)/77200
    s=Section(name='audit',type='CHANNEL',A=a,Ix=ix,Iy=iy,rx=100,ry=math.sqrt(2000),
              ro=math.sqrt(ro2),J=j,Cw=cw,H=None if omit_h else .5,b_t_ratio=5,h_tw_ratio=20)
    c=case(method,lengths=dict(Lx=math.pi*math.sqrt(200000/o['Fex'])*s.rx,
                              Ly=math.pi*math.sqrt(200000/o['Fey'])*s.ry,Lz=1000))
    return c,s


@pytest.mark.parametrize('method',METHODS)
def test_e4_channel_normative_symmetry_axis(method):
    c,s=channel(method)
    assert required_capacity(AxialE4Rule(),c,s,"F-46") == expected(BANK['E4-channel'][method+'_kN'])


@pytest.mark.parametrize('method',METHODS)
@pytest.mark.parametrize('axis',['x','y'])
@pytest.mark.xfail(strict=True,raises=AssertionError,reason='F-47: xa/ya are recorded but absent from E4 capacity')
def test_e4_offset_normative_capacity(method,axis):
    o=BANK[f'E4-offset-{axis}']
    c,s=symmetric(method, **{axis+'a':float(o['offset'])})
    assert required_capacity(AxialE4Rule(),c,s,"F-47") == expected(o[method+'_kN'])


def e5_params():
    for key,o in BANK.items():
        if not key.startswith(('E5-a-', 'E5-b-')):
            continue
        yield pytest.param(key,id=key)


@pytest.mark.parametrize('key',list(e5_params()))
def test_e5_all_long_leg_slenderness_branches(key):
    o=BANK[key]
    actual = axial_calc.calculate_e5_slenderness(s=float(o['s']), configuration=o['configuration'].upper(),
        connected_leg='EQUAL', leg_ratio=1, principal_slenderness=None)
    assert actual['effective_slenderness'] == expected(o['effective'])
    assert actual['eligible_slenderness'] == o['eligible_if_other_conditions_met']


@pytest.mark.parametrize('key',[k for k in BANK if k.startswith('E5-short')])
def test_e5_short_leg_and_principal_radius_floor(key):
    o=BANK[key]
    actual = axial_calc.calculate_e5_slenderness(s=float(o['s']), configuration=key.split('-')[2].upper(),
        connected_leg='SHORT', leg_ratio=float(o['leg_ratio']), principal_slenderness=float(o['L_over_rz']))
    assert actual['effective_slenderness'] == expected(o['effective'])
    assert actual['correction'] == expected(o['correction'])
    assert actual['principal_floor'] == expected(o['floor'])


@pytest.mark.parametrize('method',METHODS)
@pytest.mark.xfail(strict=True,raises=AssertionError,reason='F-36: E5-2 capacity wrong at L/ra=120')
def test_e5_rule_capacity_above_branch(method):
    c=case(method,lengths=dict(Lx=3600,Ly=3600,Lz=3600))
    s=Section(name='audit',type='SINGLE_ANGLE',A=2000,rx=30,ry=30,b_t_ratio=8)
    assert required_capacity(AxialE5Rule(),c,s,"F-36") == expected(BANK['E5-a-120'][method+'_kN'])


@pytest.mark.parametrize('key',[k for k in BANK if k.startswith('E7-round-100-') or k.startswith('E7-round-250-')])
@pytest.mark.parametrize('method',METHODS)
def test_e7_round_independent_effective_area(key,method):
    o=BANK[key]
    ae=axial_calc.calculate_e7_round_area(Ag=5000,D_over_t=float(o['D_over_t']),E=200000,Fy=345)['Ae_mm2']
    assert ae == expected(o['Ae'])
    pn=axial_calc.calculate_Fcr(345,float(o['Fe']))*ae
    assert axial_calc.calculate_available_compressive_strength(pn,method)==expected(o[method+'_kN'])


@pytest.mark.parametrize('key',[k for k in BANK if k.startswith('E7-round-50-')])
@pytest.mark.parametrize('method',METHODS)
def test_e7_round_nonslender_equivalence_is_bounded(key,method):
    o=BANK[key]
    ae=axial_calc.calculate_e7_round_area(Ag=5000,D_over_t=50,E=200000,Fy=345)['Ae_mm2']
    pn=axial_calc.calculate_Fcr(345,float(o['Fe']))*ae
    assert axial_calc.calculate_available_compressive_strength(pn,method)==expected(o[method+'_kN'])


@pytest.mark.parametrize('family',['W','CHANNEL','RECTANGULAR_HSS','SINGLE_ANGLE'])
@pytest.mark.parametrize('method',METHODS)
def test_e7_nonround_widths(family,method):
    # Explicitly superseded c2 variant, user TD-01; historical bank unchanged.
    o=R_BANK[f'E7-{family}-500']
    elements=[{**{k:float(row[k]) for k in ('b','t','lambda_r')},
               'count':row['count'],'kind':row['kind']} for row in o['elements']]
    fn=axial_calc.calculate_Fcr(345,500)
    ae=axial_calc.calculate_e7_plate_area(Ag=float(o['Ag']),Fn=fn,Fy=345,elements=elements)['Ae_mm2']
    assert ae == expected(o['Ae'])
    pn=fn*ae
    assert axial_calc.calculate_available_compressive_strength(pn,method)==expected(o[method+'_kN'])


def round_e7(method='LRFD', ratio=100):
    # Exact annulus properties, scaled Ag=5000. D/t=ratio; ro^2=2*r^2;
    # Cw=0 and J=2I give Fez=G, so Fe=80 is flexural, not invented torsion.
    t=math.sqrt(5000/(math.pi*(ratio-1)))
    diameter=ratio*t
    inertia=math.pi*(diameter**4-(diameter-2*t)**4)/64
    r=math.sqrt(inertia/5000)
    length=math.pi*math.sqrt(200000/80)*r
    s=Section(name='audit',type='CIRCULAR_HSS',A=5000,OD=diameter,tdes=t,
              Ix=inertia,Iy=inertia,rx=r,ry=r,J=2*inertia,Cw=0,d_t_ratio=ratio)
    return case(method,lengths=dict(Lx=length,Ly=length,Lz=length)),s


@pytest.mark.parametrize('method',METHODS)
def test_f35_direct_false_pass_is_contained_and_engine_incomplete(method):
    c,s=round_e7(method)
    correct=float(BANK['E7-round-100-80'][method+'_kN'])
    c.loads.Pu=correct*1.05
    local=AxialE7Rule().check(c,s)
    assert local.capacity == expected(correct)
    assert local.status.value == 'FAIL'
    result=run(c,s)
    assert result.status.value=='INCOMPLETE'
    assert any(check.clause=='E7-1' and check.status.value=='FAIL' for check in result.checks)
    obligation=next(o for o in result.coverage.obligations if o.id=='N10.effective_area')
    assert not obligation.accepted_checks


@pytest.mark.parametrize('method',METHODS)
def test_f46_channel_false_pass_is_contained(method):
    c,s=channel(method)
    correct=float(BANK['E4-channel'][method+'_kN'])
    c.loads.Pu=correct*1.05
    local = AxialE4Rule().check(c,s)
    assert local.capacity == expected(correct)
    assert local.status.value == 'FAIL'
    result=run(c,s)
    assert any(check.clause=='E4-1' and check.status.value=='FAIL' for check in result.checks)
    assert result.status.value=='INCOMPLETE'  # Existing aggregate contract; known local FAIL retained.
    assert not result.coverage.complete


@pytest.mark.parametrize('method',METHODS)
def test_f36_effective_slenderness_exceeds_200_stays_pending(method):
    c=case(method,lengths=dict(Lx=5400,Ly=5400,Lz=5400))
    s=Section(name='audit',type='SINGLE_ANGLE',A=2000,rx=30,ry=30,b_t_ratio=8)
    assert not BANK['E5-a-180']['eligible_if_other_conditions_met']
    result=run(c,s)
    assert result.status.value=='INCOMPLETE'
    assert not next(o for o in result.coverage.obligations if o.id=='N08.angle_alternative').accepted_checks


@pytest.mark.parametrize('method',METHODS)
def test_e7_round_outside_upper_bound_not_accredited(method):
    for ratio in [float(.45*200000/345),300]:
        c,s=round_e7(method,ratio)
        result=run(c,s)
        assert result.status.value=='INCOMPLETE'
        assert not any(check.clause=='E7-1' for check in result.checks)
        assert not result.coverage.complete


@pytest.mark.parametrize('family',['W','CHANNEL','DOUBLE_ANGLE','RECTANGULAR_HSS','CIRCULAR_HSS','SINGLE_ANGLE','SOLID_RECTANGULAR','SOLID_CIRCULAR'])
@pytest.mark.parametrize('method',METHODS)
def test_all_compression_families_cannot_discharge_coverage(family,method):
    s=Section(name='audit',type=family,A=5000,Ix=50000000,Iy=10000000,
              rx=100,ry=math.sqrt(2000),ro=math.sqrt(12000),H=.8,J=100000,Cw=1000000,
              bf_2tf_ratio=5,b_t_ratio=5,h_tw_ratio=10,b_tdes_ratio=10,h_tdes_ratio=10,d_t_ratio=20)
    result=run(case(method),s)
    assert result.status.value=='INCOMPLETE'
    assert not result.coverage.complete
    if family=='DOUBLE_ANGLE':
        assert any(o.id=='N09.assembly' and not o.accepted_checks for o in result.coverage.obligations)


@pytest.mark.parametrize('family',['TEE','UNSYMMETRIC','EYEBAR','PIN_CONNECTED'])
def test_unrepresented_families_explicitly_rejected(family):
    s=Section(name='audit',type=family,A=5000,rx=100,ry=50)
    with pytest.raises(RuleNotImplementedError):
        run(case(),s)


def test_missing_e4_H_is_blocked_and_coverage_pending():
    c,s=channel(omit_h=True)
    with pytest.raises(IncompleteSectionDataError) as caught:
        AxialE4Rule().check(c,s)
    assert 'section.H' in caught.value.details['fields']
    assert run(c,s).status.value=='INCOMPLETE'


# HFS-031R0: unknown classification is now contained, not a repair of B4.1a all families.
def test_partial_classification_cannot_be_nonslender():
    assert axial_calc.classify_compression_elements('W',{'h_tw_ratio':20},200000,345)['overall']=='unknown'


def test_public_router_rejects_missing_compression_classification():
    s=Section(name='audit',type='W',A=5000,rx=100,ry=50,h_tw_ratio=20)
    with pytest.raises(IncompleteSectionDataError):
        ProfileRouter.get_rules(case(),s)


@pytest.mark.parametrize('method',METHODS)
def test_d2_external_area_provenance_not_inferred(method):
    c=case(method,-1,connection=dict(An=800,U=.8),
           custom_section=dict(type='SOLID_RECTANGULAR',B=10,H=100))
    assert SteelDesignEngine(SectionRepository()).run(c).status.value=='INCOMPLETE'
    c.connection.An=1001
    with pytest.raises(ValidationError,match='Net area An'):
        SteelDesignEngine(SectionRepository()).run(c)


@pytest.mark.parametrize('limit_state,factor', [('yielding',.9),('rupture',.75)])
def test_d2_nominal_conversion_preserves_force_units(limit_state,factor):
    assert tension_calc.calculate_available_tensile_strength(1000000,'LRFD',limit_state)==factor*1000


@pytest.mark.parametrize('method',METHODS)
@pytest.mark.xfail(strict=True,raises=AssertionError,reason='F-36: concentric angle uses geometric radii instead of principal minor radius')
def test_concentric_angle_principal_minor_axis(method):
    o=BANK['E5-centric-angle']
    c=case(method,lengths=dict(Lx=float(o['L']),Ly=float(o['L']),Lz=float(o['L'])),
           connection=dict(angle_compression_mode='both_legs'))
    s=Section(name='audit',type='SINGLE_ANGLE',A=float(o['Ag']),Ix=float(o['Ix']),Iy=float(o['Iy']),
              rx=float(o['ra']),ry=float(o['ra']),rz=float(o['rz']),b_t_ratio=10)
    assert required_capacity(AxialE5Rule(),c,s,"F-36")==expected(o[method+'_kN'])


@pytest.mark.parametrize('method',METHODS)
@pytest.mark.xfail(strict=True,raises=AssertionError,reason='F-38: E6 connector-slip modified slenderness not implemented')
def test_built_up_member_requires_e6_modified_slenderness(method):
    o=BANK['E6-snug-60']
    c=case(method,lengths=dict(Lx=5000,Ly=5000,Lz=5000))
    s=Section(name='audit',type='DOUBLE_ANGLE',A=5000,rx=50,ry=50)
    assert required_capacity(AxialE3Rule(),c,s,"F-38")==expected(o[method+'_kN'])


@pytest.mark.xfail(strict=True,raises=AssertionError,reason='F-48: continuous-contact double angle classified as separated angle')
def test_double_angle_continuous_contact_table_b41_case1():
    # Stipulated continuous-contact outstanding legs: lambda=12 < .56*sqrt(E/Fy).
    assert axial_calc.classify_compression_elements('DOUBLE_ANGLE',{'b_t_ratio':12},200000,345)['overall']=='non_slender'


# HFS-031R0: direct missing-axis rejection is demonstrated.
def test_direct_e3_missing_axis_must_not_issue_favorable_check():
    s=Section(name='audit',type='W',A=5000,rx=100,ry=None)
    with pytest.raises(IncompleteSectionDataError) as caught:
        AxialE3Rule().check(case(),s)
    assert 'section.ry' in caught.value.details['fields']


@pytest.mark.parametrize('method',METHODS)
def test_e4_singly_symmetric_lower_root_with_correct_axis(method):
    o=BANK['E4-y-symmetric']
    fe=axial_calc.calculate_Fe_flexural_torsional(o['Fey'],o['Fez'],float(o['H']))
    assert fe==expected(o['Fe'])
    actual=axial_calc.calculate_available_compressive_strength(axial_calc.calculate_Fcr(345,fe)*5000,method)
    assert actual==expected(o[method+'_kN'])


# HFS-031R: OD/tdes is now used; the original normative expected 20 is unchanged.
def test_loader_compression_ratio_uses_outside_diameter(tmp_path):
    from openpyxl import Workbook
    from steel_design.sections.loader import load_sections_from_excel
    book=Workbook()
    sheet=book.active
    sheet.title='PTE_RED'
    sheet.append(['shape','A','OD','ID','tdes'])
    sheet.append(['HSS_TEST',1000,100,90,5])
    path=tmp_path/'round.xlsx'
    book.save(path)
    section,=load_sections_from_excel(str(path))
    assert section.d_t_ratio==20  # S22 B4.1a/E7.2: outer 100 / design 5, not 90/5.
