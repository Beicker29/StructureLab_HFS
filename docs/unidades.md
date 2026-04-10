# Unidades del repositorio (Steel Design AISC 360-22)

Este documento define las unidades que usa el motor y la convencion de signos.

## 1) Sistema base interno

- Longitud: `mm`
- Area: `mm2`
- Inercia (`Ix`, `Iy`, `Iz`, `Iw`): `mm4`
- Modulo seccional (`Sx`, `Sy`, `Sz`, `Zx`, `Zy`): `mm3`
- Constante torsional `J`: `mm4`
- Constante de alabeo `Cw`: `mm6`
- Esfuerzo (`Fy`, `Fu`, `E`, `G`, `Fcr`, `Fe`): `MPa` (`N/mm2`)
- Fuerza interna nominal (`Pn`): `N`
- Momento interno nominal (`Mn`, `Mp`): `N*mm`

## 2) Convencion de signos de cargas

- `Pu > 0`: compresion
- `Pu < 0`: tension
- `Pu = 0`: sin carga axial
- `Mux`, `Muy`, `Vu`: se ingresan como magnitudes de diseno en `kN-m` y `kN`.

Nota: para chequeos de tension/flexion el motor usa magnitud absoluta de demanda.

## 3) Entradas JSON (`SteelCase`)

- `material.Fy`, `material.Fu`, `material.E`: `MPa`
- `loads.Pu`: `kN` (positivo compresion, negativo tension)
- `loads.Mux`, `loads.Muy`: `kN-m`
- `loads.Vu`: `kN`
- `lengths.Lx`, `Ly`, `Lz`, `Lb`: `mm`
- `factors.Kx`, `Ky`, `Kz`, `Cb`: adimensional
- `factors.xa`, `factors.ya`: `mm` (offset de arriostramiento para E4)
- `connection.An`: `mm2` (traccion, D3)
- `connection.U`: adimensional (traccion, D3)
- `custom_section.diameter`, `custom_section.H`, `custom_section.B`: `mm`

### 3.1) Convencion de ejes y factores de estabilidad

- `Lx` (`mm`): longitud no arriostrada para pandeo flexional respecto al eje `x` (eje fuerte).
- `Ly` (`mm`): longitud no arriostrada para pandeo flexional respecto al eje `y` (eje debil).
- `Lz` (`mm`): longitud no arriostrada para pandeo torsional o flexo-torsional.
- `Lb` (`mm`): longitud no arriostrada para pandeo lateral-torsional en flexion.
- `Kx` (adimensional): factor de longitud efectiva asociado a `Lx`.
- `Ky` (adimensional): factor de longitud efectiva asociado a `Ly`.
- `Kz` (adimensional): factor de longitud efectiva asociado a `Lz`.
- `xa` (`mm`): offset de arriostramiento en direccion del eje `x` (usado en E4).
- `ya` (`mm`): offset de arriostramiento en direccion del eje `y` (usado en E4).

Reglas de ingreso:

- `Lx`, `Ly`, `Lz`, `Lb` deben ser mayores que `0`.
- `Kx`, `Ky`, `Kz` deben ser mayores que `0`.
- `xa`, `ya` se ingresan como magnitudes no negativas (`>= 0`).

## 4) Constantes normativas usadas por el codigo

- `E = 200000 MPa` (validado de forma estricta en entrada)
- `G = 77200 MPa` (constante interna del motor para Capitulo E)

## 5) Salida del engine (`checks`)

- Chequeos axiales (`D2`, `E3`, `E4`, `E5`, `E7`):
  - `demand`: `kN`
  - `capacity`: `kN`
- Chequeo de flexion `F2`:
  - `demand`: `kN-m`
  - `capacity`: `kN-m`
- `dcr`: adimensional
- `status`: `PASS` o `FAIL`

## 6) Catalogo Excel (`data/sections.xlsx`) y normalizacion

El loader lee todas las hojas de perfiles (excepto `README`) y normaliza valores al sistema base interno.  
Segun la convencion del catalogo (hoja `README`), se aplican estos factores:

- `Ix, Iy, Iz, Iw, Sw1, Sw2, Sw3`: `x1e6`
- `Zx, Zy, Sx, Sy, Sz, SwA, SwB, SwC, SzA, SzB, SzC, Qf, Qw, C`: `x1e3`
- `J`: `x1e3`
- `Cw`: `x1e9`

Esto permite que las formulas trabajen consistentemente en `mm`, `mm2`, `mm3`, `mm4`, `mm6`, `MPa`, `N`.

## 7) Conversiones rapidas

- `1 MPa = 1 N/mm2`
- `N -> kN`: dividir entre `1000`
- `N*mm -> kN-m`: dividir entre `1,000,000`
