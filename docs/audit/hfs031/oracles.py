"""Independent D/E calculation sheets, S22 by hash in requirements.md.

Standard library only. Decimal(50) arithmetic; no product, router, test or
historical-result imports. These are bounded calculation sheets, not a second
design engine. See calculations.md for assumptions and manual developments.
Run --out NEW.json; never rewrites an accepted oracle.
"""
import argparse
from decimal import Decimal as D, localcontext
import json
from pathlib import Path


PI = D('3.1415926535897932384626433832795028841971693993751')
E, FY, G = D(200000), D(345), D(77200)


def stress(fe):
    ratio = FY / fe
    return FY * (D('.658').ln() * ratio).exp() if ratio <= D('2.25') else D('.877') * fe


def strengths(pn):
    return {'Pn_N': pn, 'LRFD_kN': D('.9') * pn / 1000, 'ASD_kN': pn / 1670}


def lower_root(a, b, h):
    # Rationalized quadratic root, independent of the subtractive production form.
    return 2 * a * b / (a + b + ((a + b)**2 - 4*h*a*b).sqrt())


def bank():
    rows = {}
    for an, u in [(800, '.8'), (1000, '1')]:
        ae = D(an) * D(u)
        rows[f'D2-{an}'] = {'reference': 'D2-1/2, D3-1; PDF100-101',
            'Ag': 1000, 'An': an, 'U': u, 'Fy': 345, 'Fu': 450, 'Ae': ae,
            'Pn_y_N': D(345000), 'Pn_r_N': 450*ae,
            'LRFD_kN': [D('310.5'), D('.75')*450*ae/1000],
            'ASD_kN': [D(345000)/1670, 450*ae/2000]}
    for ratio in ['.1', '1', '2.249999', '2.25', '2.250001', '4.3125']:
        fe = FY / D(ratio)
        rows[f'E3-{ratio}'] = {'reference': 'E3-1..4; PDF108-109',
            'Fy_over_Fe': ratio, 'Fe': fe, 's': PI*(E/fe).sqrt(),
            'Fn': stress(fe), **strengths(stress(fe)*5000)}
    # Consistent stipulated analytical section properties, not a catalog claim.
    a, ix, iy, j, ho, lz = map(D, [10000, 100000000, 20000000, 200000, 300, 6000])
    cw = iy * ho**2 / 4
    fe0 = (PI**2*E*cw/lz**2 + G*j)/(ix+iy)
    rows['E4-symmetric'] = {'reference': 'E4-2/7/9; PDF109-110',
        'A': a, 'Ix': ix, 'Iy': iy, 'J': j, 'Cw': cw, 'Lz': lz,
        'ro': ((ix+iy)/a).sqrt(), 'Fe': fe0, **strengths(stress(fe0)*a)}
    for axis, offset in [('x', D(100)), ('y', D(200))]:
        ro2 = (ix+iy)/a + offset**2
        term = ho**2/4 + (ix/iy if axis == 'x' else 1)*offset**2
        fe = (PI**2*E*iy/lz**2*term+G*j)/(a*ro2)
        rows[f'E4-offset-{axis}'] = {'reference': 'E4-10..12; PDF111',
            'offset': offset, 'ro2': ro2, 'Fe': fe, **strengths(stress(fe)*a)}
    for name, fex, fey, fez, h in [('channel', 50, 200, 100, '.5'),
                                  ('y-symmetric', 200, 50, 100, '.5'),
                                  ('missing-H', 50, 50, 100, '.5')]:
        fe = lower_root(D(fex if name == 'channel' else fey), D(fez), D(h))
        rows[f'E4-{name}'] = {'reference': 'E4-3/5..9 and UN axis note; PDF109-110',
            'Fex': fex, 'Fey': fey, 'Fez': fez, 'H': h, 'Fe': fe,
            **strengths(stress(fe)*5000)}
    # E4-4 symmetric offsets xo=yo, Fex=Fey=100 yields roots 100 and
    # roots of H*z^2 - (100+Fez)*z +100*Fez. H=.5, Fez=200.
    cubic_fe = lower_root(D(100), D(200), D('.5'))
    rows['E4-unsymmetric'] = {'reference': 'E4-4; PDF110', 'Fex':100, 'Fey':100,
        'Fez':200, 'xo_over_ro_squared':D('.25'), 'yo_over_ro_squared':D('.25'),
        'Fe':cubic_fe, **strengths(stress(cubic_fe)*5000)}
    # Ideal equal angle: two nonoverlapping rectangles 100x10 and 10x90.
    # Centroid/tensor from area integrals, principal minor radius, concentric load.
    ag=D(1900)
    centroid=(D(1000)*50+D(900)*5)/ag
    inertia=D(10)*D(100)**3/12+D(1000)*(50-centroid)**2
    inertia+=D(90)*D(10)**3/12+D(900)*(5-centroid)**2
    ixy=D(1000)*(50-centroid)*(5-centroid)+D(900)*(5-centroid)*(55-centroid)
    # y inertia is equal by symmetry; product integral from the two rectangles.
    rz=((inertia-abs(ixy))/ag).sqrt()
    ra=(inertia/ag).sqrt()
    length=100*ra
    fe=PI**2*E/(length/rz)**2
    rows['E5-centric-angle']={'reference':'E3 principal axes; E5 first paragraph; PDF108-111',
        'Ag':ag,'centroid':centroid,'Ix':inertia,'Iy':inertia,'Ixy':ixy,
        'ra':ra,'rz':rz,'L':length,'Fe':fe,**strengths(stress(fe)*ag)}
    for config in ['a', 'b']:
        for s in map(D, ['60', '74.999', '75', '75.001', '79.999', '80', '80.001', '120', '134.4', '155', '180']):
            effective = (72 + D('.75')*s if s <= 80 else 32 + D('1.25')*s) if config == 'a' else (60+D('.8')*s if s <=75 else 45+s)
            fe = PI**2 * E / effective**2
            rows[f'E5-{config}-{s}'] = {'reference': 'E5-1..4 and E5(4); PDF112',
                'configuration': config, 's':s, 'effective':effective,
                'eligible_if_other_conditions_met':effective <= 200,
                'Fe':fe, **strengths(stress(fe)*2000)}
        for rz_ratio in ['140', '200']:
            s, leg_ratio = D(100), D('1.5')
            base = D(157) if config == 'a' else D(145)
            correction = (4 if config=='a' else 6)*(leg_ratio**2-1)
            floor = D('.95' if config=='a' else '.82')*D(rz_ratio)
            effective = max(base+correction, floor)
            rows[f'E5-short-{config}-{rz_ratio}'] = {'reference':'E5(a/b)(2); PDF112',
                's':s,'leg_ratio':leg_ratio,'L_over_rz':D(rz_ratio),'base':base,
                'correction':correction,'floor':floor,'effective':effective,
                **strengths(stress(PI**2*E/effective**2)*2000)}
    for connection in ['snug', 'welded-angle', 'welded-channel', 'welded-other']:
        for spacing in map(D, ['39.999', '40', '40.001', '60']):
            ki = {'snug':D(1), 'welded-angle':D('.5'), 'welded-channel':D('.75'), 'welded-other':D('.86')}[connection]
            modified = (D(100)**2+(ki*spacing)**2).sqrt() if connection=='snug' or spacing>40 else D(100)
            rows[f'E6-{connection}-{spacing}'] = {'reference':'E6-1/2a/2b; PDF113-114',
                's0':100,'a_over_ri':spacing,'Ki':ki,'modified':modified,
                **strengths(stress(PI**2*E/modified**2)*5000)}
    for fe in map(D, ['80', '150', '500', '5000']):
        for ratio in map(D, ['50', '100', '250']):
            area_factor = D(1) if ratio <= D('.11')*E/FY else D('.038')*E/(FY*ratio)+D(2)/3
            rows[f'E7-round-{ratio}-{fe}'] = {'reference':'E7-1/6/7; PDF116-117',
                'D_over_t':ratio,'Fe':fe,'Fn':stress(fe),'Ag':5000,
                'Ae':5000*area_factor,'area_factor':area_factor,
                **strengths(stress(fe)*5000*area_factor)}
        # Per-element widths, expressly specified; no production classifier.
        for family, ag, elements in [
            ('W', 12800, [(4,200,10,'.56','.22','1.49'), (1,600,8,'1.49','.18','1.31')]),
            ('CHANNEL', 6800, [(2,100,10,'.56','.22','1.49'), (1,600,8,'1.49','.18','1.31')]),
            # Outside 424x274, t=6, outer corner R=12 / inner R=6:
            # four straight flats + four quarter-annuli (one full annulus).
            ('RECTANGULAR_HSS', D(7800)+PI*108, [(2,400,6,'1.40','.20','1.38'), (2,250,6,'1.40','.20','1.38')]),
            ('SINGLE_ANGLE', 2375, [(1,250,5,'.45','.22','1.49'), (1,230,5,'.45','.22','1.49')]),
        ]:
            fn = stress(fe)
            deductions, detail = D(0), []
            for count, width, thickness, coefficient, c1, c2 in elements:
                b,t=D(width),D(thickness)
                lr = D(coefficient)*(E/FY).sqrt()
                lam=b/t
                fel=(D(c2)*lr/lam)**2*FY
                z=(fel/fn).sqrt()
                be=b if lam<=lr*(FY/fn).sqrt() else b*(1-D(c1)*z)*z
                loss=count*(b-be)*t
                deductions += loss
                detail.append({'count':count,'b':b,'t':t,'lambda':lam,'lambda_r':lr,
                    'c1':c1,'c2':c2,'Fel':fel,'be':be,'loss':loss})
            ae=D(ag)-deductions
            rows[f'E7-{family}-{fe}']={'reference':'E7-1..5/Table E7.1; PDF116-117',
                'family':family,'Fe':fe,'Fn':fn,'Ag':ag,'Ae':ae,'elements':detail,
                **strengths(fn*ae)}
    # E7 width transition, no global curve copied: prescribed Fn=Fy/4.
    for c1,c2 in [('.18','1.31'),('.20','1.38'),('.22','1.49')]:
        for ratio in ['1.999999','2','2.000001']:
            x=D(ratio)
            z=D(c2)*2/x
            be_ratio=D(1) if x<=2 else (1-D(c1)*z)*z
            rows[f'E7-width-boundary-{c1}-{ratio}']={'reference':'E7-2..5; PDF116-117',
                'Fn_over_Fy':'.25','lambda_over_lambda_r':ratio,'c1':c1,'c2':c2,
                'be_over_b':be_ratio}
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args=parser.parse_args()
    with localcontext() as ctx:
        ctx.prec=50
        result={'source':'S22 + E25 + E26; requirements.md hashes',
                'author':'Codex, independent derivation from local source; no human review claimed',
                'arithmetic':'Decimal precision 50; constants as printed; tabulated c2', 'cases':bank()}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(result,indent=2,default=str)+'\n')
    print(f'{len(result["cases"])} independent calculation sheets: {args.out}')


if __name__=='__main__':
    main()
