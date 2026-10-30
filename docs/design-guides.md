# Verificación con las Design Guides de AISC y contenidos candidatos

Fuentes en la raíz del repositorio:

- *AISC Design Guide 6: Composite Column Design*, 2.ª ed., 2025 (en adelante DG6).
- *AISC Design Guide 38: SpeedCore Systems for Steel Structures*, 2023 (en adelante DG38).

Las guías no son norma: explican y aplican ANSI/AISC 360-22, y no la sustituyen. Prueba: `tests/test_design_guides.py`.
Tolerancia de ±1,5 %, como en [design-examples.md](design-examples.md): las guías usan unidades US y E = 29 000 ksi.

## Resultado del contraste (LRFD)

Resistencias de diseño en kip, kip-ft o kip-in según el caso; las razones no tienen unidad.

| Caso | Descripción | Guía | Programa | Diferencia |
| --- | --- | --- | --- | --- |
| DG6-2.4-Pc | W14X211 embebido, Lc = 15 ft | 9900 | 9935 | +0.36 % |
| DG6-2.4-Mcy | W14X211 embebido, eje y, I3.3a(3), 6 barras | 3330 | 3326 | -0.11 % |
| DG6-2.4-M2S | Pu = 1000 kips, Muy = 3160 kip-ft, C-I5-1a | 0.949 | 0.950 | +0.10 % |
| DG6-2.4-Vcy | Cortante del acero, eje menor (G6) | 1330 | 1329 | -0.07 % |
| DG6-2.5-Pc | Cajón 25 x 25 x 1/2 in relleno, f'c = 6 ksi, Lc = 30 ft | 3540 | 3549 | +0.26 % |
| DG6-2.5-Mc | Igual, flexión compacta | 1980 | 1985 | +0.23 % |
| DG6-2.5-M2S | Pu = 1500 kips, Mux = 1800 kip-ft, C-I5-1a | 0.909 | 0.907 | -0.22 % |
| DG6-2.5-Vc | Igual, cortante I4-1 | 751 | 724.2 | -3.57 % |
| DG6-2.7-Vc | HSS16.000X0.250 relleno, cortante I4-1 | 226 | 226.6 | +0.27 % |
| DG38-2.1-Mc | Muro L = 300, tsc = 18, t = 1/2 in, flexión | 1 590 000 | 1 594 100 | +0.26 % |
| DG38-2.1-Vc | Igual, cortante I4-2 | 12 300 | 12 371 | +0.58 % |
| DG38-2.2-T | Muro L = 150, tsc = 18, t = 1/2 in, tracción | 7520 | 7515 | -0.07 % |
| DG38-2.2-Pc | Igual, compresión, Lc = 17 ft | 17 600 | 17 580 | -0.12 % |
| DG38-2.2-Vc | Igual, cortante I4-2 | 6170 | 6182 | +0.20 % |
| DG38-2.2-MT | Igual, Tr = 1310 kips, Mr = 147 000 kip-in | 0.385 | 0.3855 | +0.12 % |
| DG38-2.2-MC | Igual, Pr = 6110 kips, Mr = 147 000 kip-in | 0.279 | 0.2792 | +0.06 % |
| DG38-3.1-Mc | Muro L = 300, tsc = 16, t = 5/16 in, flexión | 1 040 000 | 1 048 300 | +0.80 % |
| DG38-3.1-Vc | Igual, cortante I4-2 | 8190 | 8174 | -0.20 % |
| DG38-4.1-T | Muro L = 132, tsc = 24, t = 9/16 in, tracción | 7830 | 7841 | +0.13 % |
| DG38-4.1-Pc | Igual, compresión, Lc = 17 ft | 20 400 | 20 508 | +0.53 % |
| DG38-4.1-Vc | Igual, cortante I4-2 | 6310 | 6294 | -0.26 % |
| DG38-4.1-MT | Igual, Tr = 4900 kips, Mr = 166 000 kip-in | 0.779 | 0.7796 | +0.03 % |
| DG38-4.1-MC | Igual, Pr = 4900 kips, Mr = 166 000 kip-in | 0.327 | 0.3276 | +0.05 % |

En MT y MC la guía imprime φMn (382 000, 527 000, 213 000 y 507 000 kip-in); la razón esperada es Mr/φMn.

## Notas del contraste

- **DG6-2.5-Vc (-3,57 %, del lado seguro):** en el cajón la guía toma Av = 2·H·t con el ancho total; el programa usa
  2·h·t con h plano, como el ejemplo I.6 en HSS. La prueba exige que quede por debajo.
- **DG6-2.4-Mcy:** la guía desprecia las 2 barras sobre el eje y porque la Tabla 6-2b no las admite, y aclara que su
  programa sí puede incluirlas. Con las 8 barras el programa da 3382 kip-ft (+1,6 %); se contrasta con 6 barras.
- **Estado `FAIL` en DG6-2.4-Mcy y DG38-3.1-Mc, DG38-4.1-Pc:** viene de datos de la prueba, no del ejemplo: con 6 barras la
  cuantía baja de 0,4 %, y en los muros 3.1 y 4.1 no se transcribieron sus amarres. La prueba compara la resistencia. El
  muro de 2.1 sí lleva sus datos reales (b = st = 12 in, dtie = 5/8 in) y da `PASS`, con I1-4 e I1-5M como en la guía.
- **DG6-2.6 y DG6-2.7:** la flexión de 2.7 y todo 2.6 no se contrastan porque el programa los bloquea (barras internas, redondo no
  compacto, Apéndice 2); hay pruebas que lo verifican. Son los candidatos 1 y 2.

## Qué cambió en el repositorio por esta revisión

- **DI-11 corregida:** DG38 (A.1.2, A.1.3, ejemplos 2.2 y 4.1) calcula Mn del muro con la fuerza requerida Pr, no con Pr/0,90.
  Los valores de `wall-PM-*` cambiaron por esta razón.
- **Método 2 completo:** DG6 (2.3.2) excluye el punto D por posible error del lado inseguro. `M2` se conserva, con su control contra
  la curva nominal, y la memoria lo advierte. Para diseño conviene `M2S`.
- **Confirmaciones sin cambios:** 0,06 de I4-1 con f'c en ksi (DI-5); redondeo de esquinas de HSS en Mp y puntos A-B-C-D de la
  Tabla 6-3 (DI-2, DI-12); I5-1 en rellenos no compactos.
- **Pendiente menor:** DG6 toma ri = 0 en cajones. El programa no tiene familia de cajones y usa ri = t; el efecto en estos ejemplos
  es menor que 0,3 %.

## Contenidos candidatos

Ninguno está implementado. Orden sugerido por valor y por la existencia de un ejemplo de contraste.

| # | Contenido | Origen | Contraste disponible | Carpeta |
| --- | --- | --- | --- | --- |
| 1 | Rellenos con barras internas; My de redondos no compactos (levanta DI-3) | I2.2, I3.4; procedimiento DG6 2.7 | DG6 2.7: Mp 364, My 281, φMn 318 kip-ft; I5-1 0.994 | `aisc_360_22` y `aisc_dg06` |
| 2 | Materiales de alta resistencia | Apéndice 2 de 360-22; DG6 2.6 | DG6 2.6 | `aisc_360_22` |
| 3 | Efectos de segundo orden B1, B2 (hoy dato, DH-3) | Apéndice 8 de 360-22 | DG6 2.4: Muy 3160 kip-ft | `aisc_360_22` |
| 4 | Transferencia de carga | I6; DG6 3.1 | Design Examples I.3 e I.8 | `aisc_360_22` |
| 5 | Sección controlada por tracción, I3.3a(e) | ACI 318 según DG6 2.4 | DG6 2.4: εt 0.00695 ≥ 0.00507 | `aisc_dg06` |
| 6 | Familia de cajones soldados (ri = 0, Av = 2·H·t) | DG6 2.5 | DG6 2.5 | `aisc_dg06` |
| 7 | Factor de forma α en flexión biaxial (Ec. 2-2) | DG6 2.3.2 | Sin ejemplo: solo oráculo | `aisc_dg06` |
| 8 | Placa base de columna embebida | DG6 3.4 | DG6 3.4 | `aisc_dg06` |
| 9 | Rigideces para servicio (Ec. 2-7 a 2-14) | DG6 2.8 | Sin ejemplo numérico | `aisc_dg06` |
| 10 | Muros en C | DG38 A.2 | DG38 2.3, 3.2, 4.2: MnT 2 380 000, MnC 2 160 000 kip-in (2.3) | `aisc_dg38` |
| 11 | Vigas de acoplamiento compuestas | DG38 2.3.3, A.3 | DG38 2.2: Mn 25 000 kip-in, φVn 698 kips | `aisc_dg38` |
| 12 | Muros con placas esbeltas (C-I1-1, C-I1-2) | Commentary I1.6a; DG38 Ec. 2-2, 2-3 | Sin ejemplo: solo oráculo | `aisc_360_22` |
| 13 | Rigideces efectivas de muros (I1-1 a I1-3) | I1.5; DG38 Ec. 2-9 a 2-11 | DG38 2.1: EIeff 1.36e11 kip-in² | `aisc_360_22` |
| 14 | Muros a fuego | DG38 cap. 6; Apéndice 4 de 360-22 | DG38 6.1 | `aisc_dg38` |

No recomendados por ahora:

- **Diseño sísmico (DG38 caps. 3 a 5):** depende de AISC 341, que no está en el repositorio.
- **Conexiones (DG38 4.3 y 4.4; DG6 3.3):** corresponden al Capítulo J, que aún no se implementa.
- **Análisis de edificios (viento, derivas):** el programa verifica miembros, no modela estructuras.

## Organización

La regla está en [AGENTS.md](../AGENTS.md) y [architecture.md](architecture.md): una fórmula que solo aparece en una guía va en
`codes/aisc_dg06/` o `codes/aisc_dg38/`; lo que imprime ANSI/AISC 360-22 sigue en `codes/aisc_360_22/`. Las carpetas se crearán
con el primer contenido que las necesite, y por ahora no existen porque esta revisión no añadió fórmulas de las guías.
