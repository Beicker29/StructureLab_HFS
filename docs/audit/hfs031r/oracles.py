"""Independent S22 D/E arithmetic, Decimal 60 digits; never imports the product.

Source identities are in evidence/sources.json. The normative expressions were
read from S22 pp. 16.1-42..49. This bank supplements, never rewrites HFS-031.
Run explicitly to emit JSON; tests consume the frozen output, not this script.
"""
from decimal import Decimal as D, localcontext
import json
from pathlib import Path


PI = D('3.1415926535897932384626433832795028841971693993751058209749445923')


def build():
    with localcontext() as ctx:
        ctx.prec = 60
        cases = {}
        # E4-4 exact roots constructed independently from its secular form.
        # All elastic stresses exceed the prescribed root, so the monotone
        # secular expression proves it is the lowest root, not merely a root.
        for label, x, y, r, ax, ay in [
            ('general', 200, 300, 50, '.09', '.16'),
            ('coincident', 100, 100, 50, '.25', '.25'),
            ('one-offset', 80, 300, 40, '.36', '0'),
        ]:
            x, y, r, ax, ay = map(D, map(str, (x, y, r, ax, ay)))
            z = r + r*r*ax/(x-r) + r*r*ay/(y-r)
            cases['E4-cubic-'+label] = {'Fex': x, 'Fey': y, 'Fez': z,
                'xo': ax.sqrt()*100, 'yo': ay.sqrt()*100, 'ro': D(100),
                'Fe': r, 'H': 1-ax-ay, 'equation': 'E4-4'}
        for direction, xa, ya in [('MINOR_AXIS_LATERAL', 0, 150),
                                  ('MAJOR_AXIS_LATERAL', 50, 0)]:
            # Stipulated doubly symmetric I, explicit restraint; SI units.
            E, G, J, ix, iy, area = map(D, (200000, 77200, 100000, 50000000, 10000000, 5000))
            rx, ry, ho, length = D(100), D(2000).sqrt(), D(280), D(6000)
            ro2 = rx*rx + ry*ry + xa*xa + ya*ya
            arm = ho*ho/4 + (ya*ya if xa == 0 else ix/iy*xa*xa)
            fe = (PI*PI*E*iy/(length*length)*arm + G*J)/(area*ro2)
            fn = D('.658')**(D(345)/fe)*345 if D(345)/fe <= D('2.25') else D('.877')*fe
            cases['E4-offset-'+direction] = {'Fe': fe, 'Fn': fn, 'ro2': ro2,
                'Pn_N': fn*area, 'LRFD_kN': fn*area*D('.9')/1000,
                'ASD_kN': fn*area/D('1.67')/1000}
        for label, c1 in [('STIFFENED', D('.18')), ('HSS_WALL', D('.20')),
                          ('UNSTIFFENED', D('.22'))]:
            c2 = (1-(1-4*c1).sqrt())/(2*c1)  # S22 E7-4, unrounded.
            for fn in (D(80), D(250), D(345)):
                for multiple in (D('.75'), D(1), D('1.000001'), D(2)):
                    fy, lr, t = D(345), D(30), D(6)
                    ratio = lr*(fy/fn).sqrt()*multiple
                    b = ratio*t
                    fel = (c2*lr/ratio)**2*fy
                    z = (fel/fn).sqrt()
                    be = b if multiple <= 1 else b*(1-c1*z)*z
                    cases[f'E7-width-{label}-{fn}-{multiple}'] = {
                        'b': b, 't': t, 'lambda_r': lr, 'Fn': fn, 'Fy': fy,
                        'kind': label, 'be': be, 'Fel': fel, 'c1': c1, 'c2': c2,
                        'area_loss': (b-be)*t, 'equation': 'E7-2' if multiple <= 1 else 'E7-3'}
        for family, ag, elements in [
            ('W', D(12800), [(4,200,10,'.56','UNSTIFFENED'), (1,600,8,'1.49','STIFFENED')]),
            ('CHANNEL', D(6800), [(2,100,10,'.56','UNSTIFFENED'), (1,600,8,'1.49','STIFFENED')]),
            ('RECTANGULAR_HSS', D(7800)+PI*108, [(2,400,6,'1.40','HSS_WALL'), (2,250,6,'1.40','HSS_WALL')]),
            ('SINGLE_ANGLE', D(2375), [(1,250,5,'.45','UNSTIFFENED'), (1,230,5,'.45','UNSTIFFENED')]),
        ]:
            fe, fy = D(500), D(345)
            fn = D('.658')**(fy/fe)*fy
            ae, rows = ag, []
            for count, width, thick, coefficient, kind in elements:
                c1 = {'STIFFENED': D('.18'), 'HSS_WALL': D('.20'), 'UNSTIFFENED': D('.22')}[kind]
                c2 = (1-(1-4*c1).sqrt())/(2*c1)
                b, t = D(width), D(thick)
                lr = D(coefficient)*(D(200000)/fy).sqrt()
                z = c2*lr/(b/t)*(fy/fn).sqrt()
                be = b if b/t <= lr*(fy/fn).sqrt() else b*(1-c1*z)*z
                loss = count*(b-be)*t
                ae -= loss
                rows.append({'count': count, 'b': b, 't': t, 'lambda_r': lr, 'kind': kind, 'be': be, 'loss': loss})
            cases['E7-'+family+'-500'] = {'Ag': ag, 'Fn': fn, 'Ae': ae, 'elements': rows,
                'Pn_N': fn*ae, 'LRFD_kN': fn*ae*D('.9')/1000, 'ASD_kN': fn*ae/D('1.67')/1000}
        return cases


if __name__ == '__main__':
    destination = Path(__file__).resolve().parents[3]/'tests/fixtures/hfs031r/formulas.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({'precision': 60, 'cases': build()},
                                      default=str, indent=2)+'\n', encoding='utf-8', newline='\n')
