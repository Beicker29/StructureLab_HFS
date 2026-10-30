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
| DG6-2.5-Pc | Cajón soldado 25 x 25 x 1/2 in, f'c = 6 ksi, Lc = 30 ft | 3540 | 3547 | +0.20 % |
| DG6-2.5-Mc | Igual, flexión compacta | 1980 | 1986 | +0.28 % |
| DG6-2.5-M2S | Pu = 1500 kips, Mux = 1800 kip-ft, C-I5-1a | 0.909 | 0.907 | -0.27 % |
| DG6-2.5-Vc | Igual, cortante I4-1, Av = 2·H·t | 751 | 751.2 | +0.03 % |
| DG6-2.6-Pc | Cajón, f'c = 12 ksi, Lc = 30 ft (Apéndice 2) | 5030 | 5053 | +0.46 % |
| DG6-2.6-Mc | Igual, 90 % de la distribución | 1840 | 1837 | -0.18 % |
| DG6-2.6-A2 | Pu = 2750 kips, Mux = 740 kip-ft, I5-1a con A-2-3 y A-2-4 | 0.757 | 0.756 | -0.13 % |
| DG6-2.7-Pc | HSS16.000X0.250 con 4 barras No. 7, Lc = 20 ft | 1230 | 1235 | +0.37 % |
| DG6-2.7-Mc | Igual, no compacta, Mp y My (I3-5b) | 318 | 318.4 | +0.12 % |
| DG6-2.7-I5 | Pu = 680 kips, Mux = 264 kip-ft, I5-1a | 0.994 | 0.991 | -0.29 % |
| DG6-2.7-Vb | Igual, cortante con el concreto neto de barras | 226 | 226.3 | +0.11 % |
| DG6-2.7-Vc | HSS16.000X0.250 relleno sin barras, cortante I4-1 | 226 | 226.6 | +0.27 % |
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

Contenidos añadidos, contrastados con los mismos ejemplos:

| Caso | Magnitud | Guía | Programa | Diferencia |
| --- | --- | --- | --- | --- |
| DG6 2.4, Apéndice 8 | B2 | 1.11 | 1.109 | -0.12 % |
| | Pestory (kip), columna ASD; ver notas | 20 400 | 20 410 | +0.05 % |
| | Muy (kip-ft) | 3160 | 3160 | -0.01 % |
| | Razón C-I5-1a con esas demandas | 0.949 | 0.950 | +0.09 % |
| DG6 2.4, sección controlada por tracción | εt | 0.00695 | 0.00690 | -0.74 % |
| Design Examples I.3, I6 | V'r (kip), acero, concreto, ambos | 49.7, 123, 17.6 | dentro de ±1,5 % | prueba |
| | φRn apoyo, adherencia (kip) | 138, 7.19 | dentro de ±1,5 % | prueba |
| Design Examples I.8, I6 | V'r, φRn apoyo (kip) | 1260, 741 | dentro de ±1,5 % | prueba |
| DG38 2.1, I1-1 a I1-3 | EIeff, EAeff, GAeff | 1.36e11, 1.95e7, 1.25e7 | dentro de ±1,5 % | prueba |
| DG38 2.2, viga de acoplamiento | φMn (kip-in), φVn (kip) | 22 500, 698 | 22 464, 698.6 | -0.16 %, +0.09 % |
| DG38 2.3, viga de acoplamiento | φMn (kip-in), φVn (kip) | 27 630, 716 | 27 602, 716.5 | -0.10 %, +0.06 % |
| DG38 2.3, muro en C | CT (in), MnT (kip-in), A.2.3 | 119, 2 380 000 | 118.8, 2 375 971 | -0.14 %, -0.17 % |
| | CC (in), MnC (kip-in), A.2.5 | 13.6, 2 160 000 | 13.61, 2 163 661 | +0.04 %, +0.17 % |
| | EIeff, EAeff, φVn (kip) | 1.17e11, 4.45e7, 14 490 | 1.169e11, 4.447e7, 14 498 | -0.07 %, -0.06 %, +0.06 % |
| DG38 6.1, incendio | Pn ambiente, Pno(T) (kip) | 1970, 1220 | 1973, 1219 | +0.15 %, -0.07 % |
| | Pe(T) (kip); ver notas | 2680 | 2781 | +3.77 % |
| | Pn(T), φPn(T) del muro (kip) | 496, 4910 | 500.8, 4958 | +0.97 %, +0.98 % |
| | R (h), tope de la Ec. 6-5 | 8 | 8 | 0 % |
| | Área de ventilación (in²) | 0.539 | dentro de ±1,5 % | prueba |

Sin ejemplo en las guías, solo con oráculo independiente: factor de forma α (Ec. 2-2), rigideces de servicio (Ec. 2-1, 2-7 a
2-13), placas esbeltas (C-I1-1, C-I1-2), tracción y flexión en el eje mayor de muros en C (A.2.1, A.2.2, A.2.4, A.2.6).

## Notas del contraste

- **DG6 2.4, Pestory:** la columna LRFD imprime 21 400 kips, pero sus datos dan 0,925(190)(180)/1,55 = 20 410 kips y su propio
  B2 = 1,11 solo sale con ese valor (21 400 daría 1,10). La columna ASD imprime 20 400. Se contrasta con 20 400 y se declara la
  errata: **no se modificó el cálculo para acercarse a un valor impreso**.
- **Ec en unidades métricas:** la fórmula métrica de la Specification (0,043·wc^1,5·√f'c) da cerca de 5 % más que la de ksi que usan
  las guías. Por eso Pe(T) de DG38 6.1 sale 3,77 % mayor y Pe1 de DG6 2.4, 3,4 % mayor (B1 sigue en 1,00). La prueba compara esas
  magnitudes con una tolerancia declarada.
- **DG6-2.4-Mcy:** la guía desprecia las 2 barras sobre el eje y porque la Tabla 6-2b no las admite, y aclara que su
  programa sí puede incluirlas. Con las 8 barras el programa da 3382 kip-ft (+1,6 %); se contrasta con 6 barras.
- **Estado `FAIL` en DG6-2.4-Mcy y DG38-3.1-Mc, DG38-4.1-Pc:** viene de datos de la prueba, no del ejemplo: con 6 barras la
  cuantía baja de 0,4 %, y en los muros 3.1 y 4.1 no se transcribieron sus amarres. La prueba compara la resistencia. El
  muro de 2.1 sí lleva sus datos reales (b = st = 12 in, dtie = 5/8 in) y da `PASS`, con I1-4 e I1-5M como en la guía.

## Qué cambió en el repositorio por esta revisión

- **DI-11 corregida:** DG38 (A.1.2, A.1.3, ejemplos 2.2 y 4.1) calcula Mn del muro con la fuerza requerida Pr, no con Pr/0,90.
  Los valores de `wall-PM-*` cambiaron por esta razón.
- **Método 2 completo:** DG6 (2.3.2) excluye el punto D por posible error del lado inseguro. `M2` se conserva, con su control contra
  la curva nominal, y la memoria lo advierte. Para diseño conviene `M2S`.
- **Confirmaciones sin cambios:** 0,06 de I4-1 con f'c en ksi (DI-5); redondeo de esquinas de HSS en Mp y puntos A-B-C-D de la
  Tabla 6-3 (DI-2, DI-12); I5-1 en rellenos no compactos.

## Contenidos incorporados

| # | Contenido | Entrada | Origen | Carpeta de las fórmulas | Límite que se conserva |
| --- | --- | --- | --- | --- | --- |
| 1 | Rellenos con barras internas; My de redondos no compactos | `composite.filled` | I2.2, I3.4; DG6 2.7 | `aisc_360_22`, `aisc_dg06/filled.py` | Rectangular no compacto o esbelto con barras: bloqueado |
| 2 | Materiales de alta resistencia | automática por Fy y f'c | Apéndice 2; DG6 2.6 | `aisc_360_22/appendix_2.py` | Solo rectangulares rellenos de concreto normal |
| 3 | Segundo orden B1, B2 | `composite.second_order` | Apéndice 8.1; DG6 2.4 | `aisc_360_22/appendix_8.py` | Rellenos, embebidos y muros planos, en un eje |
| 4 | Transferencia de carga | `composite.load_transfer` | I6; DG6 3.1 | `aisc_360_22/composite.py` | No superpone mecanismos; adherencia solo con declaración de I6.3 |
| 5 | Sección controlada por tracción | `composite.flexural_member` | I3.3a(e), I3.4a(d); DG6 2.4 | `aisc_dg06/members.py` | Obliga si se declara viga; si no, se informa y se advierte |
| 6 | Cajones soldados | `composite.box` | DG6 2.5 | `sections/geometry.py` | Una sola placa de espesor t |
| 7 | Factor de forma α biaxial | `composite.biaxial_shape_factor` | DG6 2.3.2 | `aisc_dg06/members.py` | Solo `M2S`, con flexión en dos ejes |
| 8 | Rigideces de servicio | en el resultado axial | DG6 2.8 | `aisc_dg06/members.py` | GJ de rectangulares (2-14) no calculado: la guía no define Jc |
| 9 | Muros en C | `composite.kind = c_wall` | DG38 A.2 | `aisc_dg38/walls.py` | Sin Mux con axial, sin Vux; una sola combinación de lado comprimido por signo de Pu |
| 10 | Vigas de acoplamiento | `composite.kind = coupling_beam` | DG38 2.3.3, A.3 | `aisc_dg38/walls.py` | Compactas; sin fuerza axial |
| 11 | Placas esbeltas | `wall.allow_slender_plates` | Commentary I1.6a; DG38 2.2.1 | `aisc_360_22/composite.py` | Solo compresión; flexión y cortante siguen exigiendo I1-4 |
| 12 | Rigideces efectivas de muros | en el resultado axial | I1-1 a I1-3 | `aisc_360_22/composite.py` | |
| 13 | Muros a fuego | `composite.fire` | DG38 cap. 6; Apéndice 4 | `aisc_dg38/fire.py`, `aisc_360_22/appendix_4.py` | Las temperaturas son dato de un análisis térmico del usuario; muros planos |

Todo lo que sale de una guía lo declara la memoria de cálculo como fuera de la norma.

No recomendados por ahora:

- **Placa base de columna embebida (DG6 3.4):** retirada por indicación del usuario (2026-10-30).
- **Diseño sísmico (DG38 caps. 3 a 5):** depende de AISC 341, que no está en el repositorio.
- **Conexiones (DG38 4.3 y 4.4; DG6 3.3):** corresponden al Capítulo J, que aún no se implementa.
- **Análisis de edificios (viento, derivas):** el programa verifica miembros, no modela estructuras.

## Organización

La regla está en [AGENTS.md](../AGENTS.md) y [architecture.md](architecture.md): una fórmula que solo aparece en una guía va en
`codes/aisc_dg06/` o `codes/aisc_dg38/`; lo que imprime ANSI/AISC 360-22 sigue en `codes/aisc_360_22/`.
