# Verificación con los Design Examples de AISC (v16.0)

Fuente: AISC, *Companion to the AISC Steel Construction Manual, Vol. 1: Design Examples*,
v16.0 (`v16.0_vol-1_design-examples.pdf`). Solo LRFD. Prueba:
`tests/test_design_examples.py`.

Criterio: los ejemplos usan unidades US, E = 29 000 ksi y propiedades redondeadas a tres
cifras; el programa usa el catálogo métrico (AISC v16) y E = 200 000 MPa. Se exige
coincidencia dentro de ±1,5 %. Los perfiles que no están en el catálogo (HSS, Pipe) se
construyen con las propiedades impresas en el ejemplo, convertidas a SI; A del HSS8X8X3/16
(no impresa) y S de los Pipe se obtienen de la geometría (radio exterior 2t, anillo) y se
contrastan con los valores del Manual (5,37 in² y Z = 31,0 in³).

An y U de los ejemplos del Capítulo D se toman del ejemplo (son datos del usuario, DD-1). En H.4 los
momentos ya amplificados por el ejemplo (B1 del Apéndice 8) se dan como dato (DH-3); en H.3 se pide la
amplificación de Cb de H1.2 y An = Ag, U = 1 (sin agujeros).

| Ejemplo | Caso | Ejemplo (φRn en kip o kip-ft; razón en H) | Programa | Diferencia | Gobierna |
| --- | --- | --- | --- | --- | --- |
| D.1 | W8X21, rotura en conexión | 211 | 210.7 | -0.14 % | TR |
| D.2 | L4X4X1/2, rotura | 140 | 140.2 | +0.16 % | TR |
| D.4 | HSS6X4X3/8, rotura | 248 | 247.4 | -0.23 % | TR |
| D.5 | HSS6.000X0.500, rotura | 349 | 348.8 | -0.05 % | TR |
| D.6 | 2L4X4X1/2 (s = 3/8 in), rotura | 305 | 305.1 | +0.04 % | TR |
| E.1C | W14X132, Lc = 30 ft | 892 | 892.2 | +0.02 % | FB-y |
| E.1D | W14X90, Lcx = 30 ft, Lcy = Lcz = 15 ft | 927 | 927.8 | +0.09 % | FB-x |
| E.1E-a | W16X31 alma esbelta (E7), Lc = 5 ft | 314 | 312.9 | -0.34 % | FB-y |
| E.1E-b | W16X31, Lc = 10 ft | 189 | 190.2 | +0.66 % | FB-y |
| E.1E-c | W16X31, Lc = 15 ft | 87.1 | 87.06 | -0.05 % | FB-y |
| E.5 | 2L4X3-1/2X3/8LLBB (s = 3/4 in), L = 8 ft, E6 | 157 | 157 | +0.01 % | FB-x |
| E.9 | HSS12X10X3/8, K = 0.8, L = 20 ft | 556 | 555.6 | -0.07 % | FB-y |
| E.10 | HSS12X8X3/16 paredes esbeltas (E7), Lc = 24 ft | 151 | 151.4 | +0.29 % | FB-y |
| E.10-18ft | HSS12X8X3/16, Lc = 18 ft (Tabla E.10-1) | 177 | 178 | +0.57 % | FB-y |
| E.10-40ft | HSS12X8X3/16, Lc = 40 ft (Tabla E.10-1) | 74.8 | 74.41 | -0.53 % | FB-y |
| E.11 | Pipe 10 Std, Fy = 35 ksi, Lcx = 30 ft, Lcy = 15 ft | 221 | 222 | +0.45 % | FB-x |
| E.14A | L5X3X1/2, E5(a) ala larga, L = 5 ft | 52.3 | 52.81 | +0.98 % | FB-E5 |
| F.1-1B | W18X50, arriostramiento continuo | 379 | 379.9 | +0.23 % | Y |
| F.1-2B | W18X50, Lb = 11.67 ft, Cb = 1.01 | 304 | 306.2 | +0.72 % | LTB |
| F.1-3B | W18X50, Lb = 17.5 ft, Cb = 1.30 | 288 | 288.3 | +0.11 % | LTB |
| F.2-1B | C15X33.9, arriostramiento continuo | 191 | 190.4 | -0.32 % | Y |
| F.2-2B | C15X33.9, Lb = 5 ft | 173 | 172.3 | -0.41 % | LTB |
| F.3B | W21X48 ala no compacta (F3) | 398 | 397.1 | -0.22 % | FLB |
| F.5 | W12X58, eje menor (F6) | 122 | 122 | -0.02 % | Y |
| F.7B | HSS10X6X3/16 ala no compacta, Lb = 21 ft, Cb = 1.14 | 59.7 | 59.7 | +0.01 % | FLB |
| F.8B | HSS8X8X3/16 ala esbelta (F7-3) | 45.4 | 46.27 | +1.92 % | FLB |
| F.9B | Pipe 8 XS, Fy = 35 ksi | 81.4 | 81.36 | -0.04 % | Y |
| F.11A | L4X4X1/4 eje x, sin restricción, Lb = 6 ft, Cb = 1.14 | 3.69 | 3.678 | -0.32 % | LTB |
| F.11B | L4X4X1/4 eje x, restricción en Mmáx, Lb = 3 ft, Cb = 1.30 | 3.98 | 4.919 | +23.60 % | LLB |
| F.11C-z | L4X4X1/4 eje z, punteras comprimidas | 4.13 | 4.11 | -0.48 % | LLB |
| F.11C-w | L4X4X1/4 eje w, Lb = 6 ft, Cb = 1.14 | 7.49 | 7.492 | +0.02 % | LTB |
| F.12 | Barra 5 x 3 in, Lb = 6 ft | 70.4 | 70.31 | -0.12 % | Y |
| F.13 | Barra redonda D = 1 in, Lb = 2.5 ft | 0.59 | 0.589 | -0.16 % | Y |
| G.1B | W24X62, cortante en el alma, G2.1(a) φv = 1.00 | 306 | 305.1 | -0.29 % | V |
| G.2B | C15X33.9, cortante en el alma, G2.1(b) | 162 | 162.6 | +0.39 % | V |
| G.3 | L5X3X1/4, ala larga vertical (G3) | 33.8 | 33.75 | -0.15 % | V |
| G.4 | HSS6X4X3/8, paredes anchas verticales (G4) | 93.6 | 93.4 | -0.22 % | V |
| G.5 | HSS16.000X0.375, Lv = 192 in (G5) | 232 | 232.2 | +0.09 % | V |
| G.6 | W21X48, cortante en el eje menor (G6) | 189 | 188.9 | -0.08 % | V |
| G.7 | C9X20, cortante en el eje menor (G6) | 59.1 | 59.15 | +0.08 % | V |
| H.1B | W14X99, Pu = 400 kips, Mux = 250, Muy = 80 kip-ft, L = 14 ft (H1-1a) | 0.929 | 0.9294 | +0.05 % | H1 |
| H.3 | W14X82 en tracción, Pu = 174 kips, Mux = 192, Muy = 67.6 kip-ft, Lb = 30 ft, Cb amplificado (H1.2) | 0.873 | 0.8732 | +0.02 % | H1 |
| H.4 | W10X33, Pu = 30 kips, Mux = 91.8, Muy = 13.1 kip-ft (amplificados por el ejemplo), L = 14 ft | 0.979 | 0.9808 | +0.19 % | H1 |

## Diferencias explicadas

- **F.8B (+1,9 %):** el ejemplo descuenta el ancho no efectivo en ambas alas, simplificación
  que el propio texto declara conservadora; el programa usa el eje neutro desplazado
  (Commentary F7, DF-5). La prueba exige que el programa quede por encima.
- **F.11B (+23,6 %):** el ejemplo reutiliza el pandeo local de F.11A, con Sc = 0,80·Sx, y
  dice que es conservador; con restricción en el punto de máximo momento, F10.2(2)(ii) no
  reduce My y el programa usa Sc = Sx.

## Hallazgo resuelto: DF-11 (fluencia F10-1 en ángulo sin restricción)

En F.11A el ejemplo calcula la fluencia como Mn = 1,5·Fy·Sx = 6,44 kip-ft, sin el factor
0,80, que aplica solo a My del pandeo lateral-torsional (F10.2(2)(i)) y a Sc del pandeo local.
El programa aplicaba también 0,80 a la fluencia (5,11 kip-ft). Corregido por indicación del
usuario (2026-10-30): ahora Y = 6,44 kip-ft, LTB = 4,09 y LLB = 4,37, y una prueba lo verifica
estado por estado.

## Fuera del alcance de esta verificación

WT (D.3, E.7, E.8, F.10), miembros armados (E.2, E.3, E.12, E.13, F.14, G.8), pasadores y barras
de ojo (D.7, D.8), placas con agujeros al tresbolillo (D.9: An lo da el usuario), ángulos simples
con fuerzas combinadas (F.11C completo, E.14B: H2), H.1A y H.2 (tablas del Manual y H2) y torsión
(H.5, H.6: H3).
