# Capítulo G — alcance implementado

Fuente: ANSI/AISC 360-22, `a360-22w.pdf` (G1–G7, pp. 16.1-75 a 16.1-81); las erratas de
enero 2025 y septiembre 2026 no modifican el Capítulo G. Solo LRFD: φv = 0,90 (G1(a)),
salvo G2.1(a). Fuerzas en kN.

## Entrada

- `Vy_2`: cortante requerido a lo largo de y (eje 2), que acompaña a `Mx_3` (alma de perfiles I y
  canales, paredes de altura H de los PTE, alas paralelas al eje 2 de los ángulos).
- `Vx_3`: cortante requerido a lo largo de x (eje 3), que acompaña a `My_2` (alas de I y canales,
  paredes de ancho B de los PTE, alas paralelas al eje 3 de los ángulos).
- El signo del cortante no interviene ([axes.md](axes.md)); el chequeo se llama `shear_y_2` o `shear_x_3`.
- `stiffeners` (rigidizadores transversales del alma, separación uniforme): `a` (separación libre), `b`, `t` (cada placa),
  `arrangement` (`pair` o `single`), `material` (nombre de `Materiales.xlsx`, obligatorio) y, para el panel extremo con campo
  de tensión, `end` (`b`, `t`, `arrangement`, `e`: de la cara interior del rigidizador extremo al extremo de la viga).
- `shear.panel` (`interior` o `end`) por combinación, obligatorio con rigidizadores y a/h ≤ 3: el panel que revisa ese Vy_2.
- `shear.Lv` (mm, opcional): distancia del cortante máximo al cortante nulo en PTE redondos (G5).

El cortante no interviene en la interacción de H1; un caso con flexión y cortante se
verifica por separado (la interacción con torsión, H3, queda fuera del alcance).

## Matriz de familias

| Familia | `Vy_2` | `Vx_3` |
| --- | --- | --- |
| W / IPE / HEA / HEB (laminados) | G2.1(a) si h/tw ≤ 2,24√(E/Fy): φv = 1,00, Cv1 = 1; si no G2.1(b) con kv = 5,34 | G6: 2 alas, bf/2tf, kv = 1,2 |
| Canal | G2.1(b), kv = 5,34 (G2.1(a) no se aplica a canales) | G6: 2 alas, bf/tf, kv = 1,2 |
| I armada soldada (`I_BUILT_UP`) | G2.1(b), kv = 5,34, Aw = d·tw, h libre entre alas (G2.1(a) es solo para laminados) | G6: cada ala con su bf/2tf y su Cv2, sumadas |
| I o canal con `stiffeners` | G2.1(b) con kv de G2-5 (5,34 con a/h > 3); con a/h ≤ 3, además el campo de tensión: panel interior G2.2 (G2-6, G2-7 o G2-8), panel extremo G2.3 (G2-12, βv de G2-13 con Mpf y Mpst); gobierna el mayor (DG-6). Requisitos G2-16 y G2-17 con Ist ≥ Ist1 (DG-7); en panel extremo, αMr/Sxt ≤ 0,35Fy | — |
| PTE rectangular | G4: Aw = 2ht, kv = 5, h = ancho plano de las paredes de altura H | G4 con las paredes de ancho B |
| PTE redondo | G5: Vn = Fcr·Ag/2 | igual |
| Ángulo simple | G3 con el ala larga (paralela a y en el catálogo) | G3 con el ala corta |
| Ángulo doble | G3 con las 2 alas verticales (LLBB: largas; SLBB: cortas) | G3 con las 2 alas horizontales |
| Barra o platina rectangular | G4: Aw = H·B, h/t = H/B, kv = 5 | G4: Aw = H·B, h/t = B/H, kv = 5 |
| Barra redonda | G4-1 con Aw = 0,5·Ag, Cv2 = 1 (DG-4) | igual |

h de los PTE: el catálogo da h = Ht − 3·tdes, que coincide con la distancia libre menos el
radio interior de esquina de G4 (hi − 2·ri, con ri = 0,5·tdes en la hoja PTE_RECT); el
oráculo lo recalcula de las columnas hi y ri_1.

## Verificación con cálculos independientes

`tests/oracles/chapter_g.py` (Decimal, sin importar el paquete). Coincidencia con
tolerancia relativa 1e-9. Vn y φv·Vn en kN:

| Caso | Perfil y eje del cortante | Fy | Vn | φv | φv·Vn |
| --- | --- | --- | --- | --- | --- |
| W-G2.1a | W24X62, y_2 | 345 | 1358.29 | 1.00 | 1358.29 |
| W-G2.1b | W24X55, y_2 (h/tw > 2,24√(E/Fy)) | 345 | 1239.93 | 0.90 | 1115.94 |
| W-G2.1b-Cv1 | W16X26, y_2 (G2-4) | 450 | 645.41 | 0.90 | 580.87 |
| C-G2.1b | C15X33.9, y_2 | 345 | 804.44 | 0.90 | 724.00 |
| W-G6 | W21X48, x_3 | 345 | 934.11 | 0.90 | 840.70 |
| C-G6 | C9X20, x_3 | 345 | 292.55 | 0.90 | 263.30 |
| RHSS-G4-y_2 | PTE100X50X3MM, y_2 | 345 | 105.84 | 0.90 | 95.25 |
| RHSS-G4-x_3 | PTE100X50X3MM, x_3 | 345 | 48.09 | 0.90 | 43.28 |
| RHSS-G4-slender | PTE100X40X1.5MM, y_2 (G2-10) | 345 | 47.71 | 0.90 | 42.94 |
| CHSS-G5-no-Lv | PTER4"X3.00MM | 345 | 101.16 | 0.90 | 91.04 |
| CHSS-G5-Lv | PTER4"X3.00MM, Lv = 1000 | 345 | 101.16 | 0.90 | 91.04 |
| L-G3-long | L5X3X1/4, y_2 | 345 | 166.94 | 0.90 | 150.24 |
| L-G3-short | L5X3X1/4, x_3 | 345 | 100.16 | 0.90 | 90.14 |
| 2L-G3-LLBB-y_2 | 2L4X3-1/2X3/8LLBB, y_2 | 345 | 402.43 | 0.90 | 362.19 |
| 2L-G3-SLBB-y_2 | 2L4X3-1/2X3/8SLBB, y_2 | 345 | 350.75 | 0.90 | 315.67 |
| 2L-G3-LLBB-x_3 | 2L4X3-1/2X3/8LLBB, x_3 | 345 | 350.75 | 0.90 | 315.67 |
| BAR-G4-y_2 | Barra 100 x 20 mm, y_2 | 345 | 414.00 | 0.90 | 372.60 |
| BAR-G4-x_3 | Barra 100 x 20 mm, x_3 | 345 | 414.00 | 0.90 | 372.60 |
| BAR-G4-G2-10 | Platina 650 x 10 mm, y_2 (G2-10) | 345 | 1225.90 | 0.90 | 1103.31 |
| BAR-G4-G2-11 | Platina 10 x 750 mm, x_3 (G2-11) | 345 | 1208.00 | 0.90 | 1087.20 |
| ROUND-G4 | Barra redonda D = 50 mm | 250 | 147.26 | 0.90 | 132.54 |
| BUI-G2.1b-stocky-web | I armada 400, tw 12, 250x20 / 200x16, y_2 | 345 | 993.60 | 0.90 | 894.24 |
| BUI-G2.1b-Cv1 | I armada 1200, tw 8, alas 400x20, y_2 (G2-4) | 345 | 838.77 | 0.90 | 754.89 |
| BUI-G6-unequal | I armada 900, tw 8, 350x22 / 600x10, x_3 | 345 | 2795.03 | 0.90 | 2515.52 |
| ST-G2.2-G2-7 | I armada 1200, tw 8, alas 400x20, a = 1500, panel interior (G2-7) | 345 | 1366.51 | 0.90 | 1229.86 |
| ST-G2.2-G2-8 | I armada 1200, tw 10, alas 200x12, a = 1000, interior (G2-8 > G2.1), Fyst = 250 | 345 | 2118.83 | 0.90 | 1906.95 |
| ST-G2.2-G2-6 | I armada 600, tw 10, alas 250x20, a = 600, interior (G2-6), rigidizador simple | 345 | 1242.00 | 0.90 | 1117.80 |
| ST-G2.3-end | I armada 1200, tw 8, alas 400x20, a = 1500, panel extremo, rigidizador extremo 2x150x20, e = 100 | 345 | 1193.76 | 0.90 | 1074.38 |
| ST-G2.3-end-e-capped | igual, a = 1000, rigidizador extremo simple, e = 400 (tope 0,84tw√(E/Fy)), Fyst = 250 | 345 | 1521.70 | 0.90 | 1369.53 |
| ST-G2.1-a-over-h-3 | igual, a = 4000 (a/h > 3: kv = 5,34, sin campo de tensión) | 345 | 838.77 | 0.90 | 754.89 |
| ST-W-G2.2 | W24X55, a = 900, interior (Cv1 = 1 con kv de G2-5) | 345 | 1239.93 | 0.90 | 1115.94 |

En los casos con rigidizadores el oráculo también reproduce kv, Vn de G2.1 y del campo de tensión, βv, Mpf, Mpst y los límites de
G2-16 y G2-18. Mpf se calcula en forma cerrada (T de ala y alma de altura de) y Mpst con el eje neutro plástico por bisección.

En los PTE redondos del catálogo (D/t ≤ 41) gobierna siempre 0,6Fy; las ramas G5-2a y
G5-2b se prueban con las fórmulas. Contraste con los AISC Design Examples G.1B–G.7 en
[design-examples.md](design-examples.md).

## Decisiones

- **DG-1** Sin `stiffeners`, el alma no tiene rigidizadores transversales: kv = 5,34 (indicación del usuario, 2026-10-30). Con
  `stiffeners`, ver DG-6 a DG-8 (2026-11-07).
- **DG-2** G5: `Lv` es opcional. Con Lv, Fcr = máx(G5-2a, G5-2b) ≤ 0,6Fy; sin Lv, solo
  G5-2b, límite inferior conservador (indicación del usuario). La memoria lo indica.
- **DG-3** Ángulos dobles: G3 se aplica a cada ángulo y se suman las dos alas
  paralelas al cortante; las alas verticales se identifican por LLBB/SLBB, igual que en
  F9 (DF-10).
- **DG-4** Barras y platinas macizas: se diseñan con G4, apartado «other singly or doubly
  symmetric shapes» (indicación del usuario, 2026-10-30), con φv = 0,90 de G1(a).
  Rectangulares: Aw = d·t = área bruta, h = d (dimensión paralela al cortante), t = la
  dimensión perpendicular, Cv2 de G2.2 con kv = 5. Redondas: G4 define Aw = d·tw y la sección
  no tiene espesor de alma; se usa la mitad del área bruta, Aw = 0,5·Ag (indicación del
  usuario, 2026-10-30), y Cv2 = 1 (lectura de la implementación: sin alma, no hay h/t con
  el que evaluar G2.2). La memoria lo indica.
- **DG-5** Convención de ETABS (indicación del usuario, 2026-11-06): el cortante se nombra por la dirección de la fuerza,
  `Vy_2` a lo largo de y (eje 2), que acompaña a `Mx_3`, y `Vx_3` a lo largo de x (eje 3). Antes se nombraba por el momento al
  que acompaña (`Vux`, `Vuy`).

- **DG-6** Rigidizadores (indicación del usuario, 2026-11-07): `shear.panel` indica por combinación si el Vy_2 es de un panel
  interior (G2.2) o extremo (G2.3). G2 presenta G2.2 y G2.3 como alternativas a G2.1, y G2.2 permite tomar el mayor: se toma el mayor
  de G2.1 y del campo de tensión en ambos paneles. G2.3 se aplica a perfiles I con alas de igual área; con alas distintas o en canales
  queda INCOMPLETE (G2.3(b): por análisis). Mpf y Mpst siguen la Fig. C-G2.3; el tope 0,84tw√(E/Fy) se aplica a e. Mr del límite
  αMr/Sxt ≤ 0,35Fy es el |Mx_3| de la combinación.
- **DG-7** G2-17 (indicación del usuario, 2026-11-07): Ist ≥ Ist1 siempre, como permite la User Note de G2.4, sin la interpolación con
  ρw, porque solo se conoce el Vr de la combinación.
- **DG-8** Ist son las placas del rigidizador: un par respecto del centro del alma, tst·((2b + tw)³ − tw³)/12; una placa respecto de la
  cara en contacto con el alma, tst·b³/3. El acero del rigidizador es dato obligatorio (`stiffeners.material`). G2.4(b) y (c) y los
  rigidizadores de apoyo (J10.8) no se verifican; G2.4(a) se informa como nota.

## Limitaciones

- Sin torsión (H3) ni aberturas en el alma (G7).
- Los perfiles I del catálogo se tratan como laminados (G2.1(a) admisible).
