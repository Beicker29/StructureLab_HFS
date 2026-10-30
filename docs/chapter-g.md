# Capítulo G — alcance implementado

Fuente: ANSI/AISC 360-22, `a360-22w.pdf` (G1–G7, pp. 16.1-75 a 16.1-81); las erratas de
enero 2025 y septiembre 2026 no modifican el Capítulo G. Solo LRFD: φv = 0,90 (G1(a)),
salvo G2.1(a). Fuerzas en kN.

## Entrada

- `Vux`: cortante requerido que acompaña a `Mux`, paralelo a y (alma de perfiles I y
  canales, paredes de altura H de los PTE, alas paralelas a y de los ángulos).
- `Vuy`: cortante requerido que acompaña a `Muy`, paralelo a x (alas de I y canales,
  paredes de ancho B de los PTE, alas paralelas a x de los ángulos).
- `shear.Lv` (mm, opcional): distancia del cortante máximo al cortante nulo en PTE redondos (G5).

El cortante no interviene en la interacción de H1; un caso con flexión y cortante se
verifica por separado (la interacción con torsión, H3, queda fuera del alcance).

## Matriz de familias

| Familia | `Vux` | `Vuy` |
| --- | --- | --- |
| W / IPE / HEA / HEB (laminados) | G2.1(a) si h/tw ≤ 2,24√(E/Fy): φv = 1,00, Cv1 = 1; si no G2.1(b) con kv = 5,34 | G6: 2 alas, bf/2tf, kv = 1,2 |
| Canal | G2.1(b), kv = 5,34 (G2.1(a) no se aplica a canales) | G6: 2 alas, bf/tf, kv = 1,2 |
| PTE rectangular | G4: Aw = 2ht, kv = 5, h = ancho plano de las paredes de altura H | G4 con las paredes de ancho B |
| PTE redondo | G5: Vn = Fcr·Ag/2 | igual |
| Ángulo simple | G3 con el ala larga (paralela a y en el catálogo) | G3 con el ala corta |
| Ángulo doble | G3 con las 2 alas verticales (LLBB: largas; SLBB: cortas) | G3 con las 2 alas horizontales |
| Barras macizas | INCOMPLETO (DG-4) | INCOMPLETO |

h de los PTE: el catálogo da h = Ht − 3·tdes, que coincide con la distancia libre menos el
radio interior de esquina de G4 (hi − 2·ri, con ri = 0,5·tdes en la hoja PTE_RECT); el
oráculo lo recalcula de las columnas hi y ri_1.

## Verificación con cálculos independientes

`tests/oracles/chapter_g.py` (Decimal, sin importar el paquete). Coincidencia con
tolerancia relativa 1e-9. Vn y φv·Vn en kN:

| Caso | Perfil y eje | Fy | Vn | φv | φv·Vn |
| --- | --- | --- | --- | --- | --- |
| W-G2.1a | W24X62, x | 345 | 1358.29 | 1.00 | 1358.29 |
| W-G2.1b | W24X55, x (h/tw > 2,24√(E/Fy)) | 345 | 1239.93 | 0.90 | 1115.94 |
| W-G2.1b-Cv1 | W16X26, x (G2-4) | 450 | 645.41 | 0.90 | 580.87 |
| C-G2.1b | C15X33.9, x | 345 | 804.44 | 0.90 | 724.00 |
| W-G6 | W21X48, y | 345 | 934.11 | 0.90 | 840.70 |
| C-G6 | C9X20, y | 345 | 292.55 | 0.90 | 263.30 |
| RHSS-G4-x | PTE100X50X3MM, x | 345 | 105.84 | 0.90 | 95.25 |
| RHSS-G4-y | PTE100X50X3MM, y | 345 | 48.09 | 0.90 | 43.28 |
| RHSS-G4-slender | PTE100X40X1.5MM, x (G2-10) | 345 | 47.71 | 0.90 | 42.94 |
| CHSS-G5-no-Lv | PTER4"X3.00MM | 345 | 101.16 | 0.90 | 91.04 |
| CHSS-G5-Lv | PTER4"X3.00MM, Lv = 1000 | 345 | 101.16 | 0.90 | 91.04 |
| L-G3-long | L5X3X1/4, x | 345 | 166.94 | 0.90 | 150.24 |
| L-G3-short | L5X3X1/4, y | 345 | 100.16 | 0.90 | 90.14 |
| 2L-G3-LLBB-x | 2L4X3-1/2X3/8LLBB, x | 345 | 402.43 | 0.90 | 362.19 |
| 2L-G3-SLBB-x | 2L4X3-1/2X3/8SLBB, x | 345 | 350.75 | 0.90 | 315.67 |
| 2L-G3-LLBB-y | 2L4X3-1/2X3/8LLBB, y | 345 | 350.75 | 0.90 | 315.67 |

En los PTE redondos del catálogo (D/t ≤ 41) gobierna siempre 0,6Fy; las ramas G5-2a y
G5-2b se prueban con las fórmulas. Contraste con los AISC Design Examples G.1B–G.7 en
[design-examples.md](design-examples.md).

## Decisiones

- **DG-1** Almas sin rigidizadores transversales: kv = 5,34; el campo de tracción
  (G2.2, G2.3) y los rigidizadores (G2.4) quedan fuera (indicación del usuario,
  2026-10-30; el catálogo no tiene perfiles armados).
- **DG-2** G5: `Lv` es opcional. Con Lv, Fcr = máx(G5-2a, G5-2b) ≤ 0,6Fy; sin Lv, solo
  G5-2b, límite inferior conservador (indicación del usuario). La memoria lo indica.
- **DG-3** Ángulos dobles: G3 se aplica a cada ángulo y se suman las dos alas
  paralelas al cortante; las alas verticales se identifican por LLBB/SLBB, igual que en
  F9 (DF-10).
- **DG-4** Barras macizas: el Capítulo G no define su área de cortante sin ambigüedad
  (G4 habla de almas, G5 de PTE redondos). INCOMPLETO hasta consultar al usuario.
- **DG-5** Convención `Vux`/`Vuy`: el cortante se nombra por el momento al que acompaña,
  no por la dirección de la fuerza.

## Limitaciones

- Sin torsión (H3) ni aberturas en el alma (G7).
- Los perfiles I del catálogo se tratan como laminados (G2.1(a) admisible).
