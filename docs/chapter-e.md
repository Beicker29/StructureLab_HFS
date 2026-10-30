# Capítulo E — alcance implementado

Fuente: ANSI/AISC 360-22, `a360-22w.pdf` (B4.1a p. 16.1-21; E1–E7 pp. 16.1-38 a
16.1-49). Las erratas locales (2025-01-23 y 2026-09-23) no modifican el capítulo E
ni la tabla B4.1a. Unidades internas: N, mm, MPa; resultados en kN.

## Matriz de familias

Selección organizada según la Tabla de Nota E1.1 y contrastada con el texto
obligatorio de E3–E7.

| Familia (`data/sections.xlsx`) | Elementos B4.1a | Modos globales | Con elementos esbeltos | Estado |
| --- | --- | --- | --- | --- |
| W / IPE / HEA / HEB (`W`) | ala caso 1 (bf/2tf), alma caso 5 (h/tw) | E3 (x, y); E4(a) TB (E4-2); E4(d)/(e) con `ya` o `xa` | E7 con Fn de cada modo | Verificado |
| Canal (`C`) | ala caso 1 (bf completo), alma caso 5 | E3 (x, y); E4(b) FTB (E4-3 con Fex, Nota de E4) | E7 con Fn de cada modo | Verificado |
| PTE rectangular (`PTE_RECT`) | paredes caso 6 (b/tdes, h/tdes) | E3; E4-2 si Lz > min(Lx, Ly) (D-7) | E7 (c1 = 0,20) | Verificado |
| PTE redondo (`PTE_RED`) | caso 9 (D/tdes) | E3; E4-2 (Cw = 0 del catálogo) si Lz > min(Lx, Ly) | E7.2 (E7-6/E7-7) | Verificado |
| Ángulo simple (`L`) | ambas alas caso 3 | E5(a)/(b) con E3; E4 si b/t > 0,71√(E/Fy): E4-3 (alas iguales) o E4-4 (desiguales) | FB: E7 con Fn de E3; FTB: E4-1 con Ag | Verificado (solo ruta E5) |
| Ángulo doble (`2L`) | alas caso 1(3) en contacto o 3(2) con separadores (D-11) | E3 (x); E3 + E6 (y); E4(b) FTB con E6 (E4-3) | E7 con Fn de cada modo | Verificado |
| Barra maciza (entrada) | ninguno | E3 | — | Verificado |

“Verificado” significa contrastado con cálculos independientes en los casos de
la tabla siguiente, sin condiciones obligatorias abiertas dentro del dominio
declarado. No es una validación por terceros.

## Verificación con cálculos independientes

`tests/oracles/chapter_e.py` recalcula en Decimal (50 dígitos), leyendo el Excel
directamente y sin importar el paquete. Resultados (kN); L = 3000 mm y K = 1 salvo
indicación:

| Caso | Perfil y datos | Fy | Esbelto | Gobierna | Pn | φPn | Pn/Ω |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RHSS-nonslender | PTE100X100X4MM | 345 | no | FB-x | 312.96 | 281.67 | 187.40 |
| RHSS-slender | PTE120X60X2MM, L=1500 | 345 | sí | FB-y | 140.66 | 126.59 | 84.23 |
| RHSS-torsional-length-E4-2 | PTE150X50X3MM, L=1000, Lz=6000 | 345 | sí | FB-y | 266.31 | 239.68 | 159.47 |
| C-flexural | C15X50 | 345 | no | FB-y | 882.55 | 794.30 | 528.47 |
| C-flexural-torsional | C15X50, L=1000 | 345 | no | FB-y | 2811.81 | 2530.63 | 1683.72 |
| C-FTB-governs | C15X50, L=4000, Ly=1000 | 345 | no | FTB | 2504.79 | 2254.31 | 1499.87 |
| C-slender | C12X20.7, L=1500 | 450 | sí | FB-y | 1042.30 | 938.07 | 624.13 |
| W-torsional | W14X90 | 345 | no | TB | 5466.31 | 4919.68 | 3273.24 |
| W-slender-web | W8X10 | 345 | sí | FB-y | 168.25 | 151.42 | 100.75 |
| W-bracing-offset-E4-10 | W14X90, L=6000, ya=200 | 345 | no | FB-y | 4379.00 | 3941.10 | 2622.16 |
| CHSS-nonslender | PTER4"X3.00MM, L=2500 | 345 | no | FB-x | 251.31 | 226.18 | 150.49 |
| CHSS-torsional-length | PTER4"X3.00MM, L=2500, Lz=5000 | 345 | no | FB-x | 251.31 | 226.18 | 150.49 |
| CHSS-slender-E7-7 | PTER24"X12.70MM, L=8000 | 450 | sí | FB-x | 8653.36 | 7788.03 | 5181.66 |
| L-E5a-equal | L4X4X1/4, L=2000, E5(a), ala larga | 250 | sí | FB-E5 | 147.20 | 132.48 | 88.14 |
| L-E5b-short-leg | L6X4X3/8, L=2500, E5(b), ala corta | 250 | sí | FB-E5 | 313.38 | 282.04 | 187.65 |
| L-E5a-slender-leg | L4X4X1/4, L=600, E5(a), ala larga | 345 | sí | FB-E5 | 233.52 | 210.17 | 139.83 |
| L-E4-3-equal-legs | L4X4X1/4, L=2000, E5(a), ala larga | 450 | sí | FB-E5 | 152.37 | 137.14 | 91.24 |
| L-E4-3-governs | L6X6X5/16, L=600, Lz=3000, E5(b), ala larga | 450 | sí | FTB | 489.10 | 440.19 | 292.88 |
| L-E4-4-unequal-legs | L6X4X3/8, L=2000, E5(a), ala corta | 450 | sí | FB-E5 | 349.07 | 314.16 | 209.02 |
| 2L-contact-welded | 2L4X4X1/4, L=2000, soldado, a=500 | 345 | sí | FTB | 536.70 | 483.03 | 321.38 |
| 2L-separated-snug | 2L4X4X1/4X3/4, L=2000, snug-tight, a=800 | 345 | sí | FTB | 458.05 | 412.24 | 274.28 |
| 2L-LLBB-pretensioned | 2L8X4X1/2LLBB, pretensado, a=1500 | 345 | sí | FTB | 1151.19 | 1036.07 | 689.33 |

El software coincide con todos los modos (Fe, Fn, área, Pn) en LRFD y ASD con
tolerancia relativa 1e-9.

## Decisiones ingenieriles vigentes

- **D-1** c2 de E7-4 sin redondear (la Tabla E7.1 imprime 1,31/1,38/1,49). Confirmado por el usuario.
- **D-2** E7-7: Ae ≤ Ag. La ecuación literal da Ae > Ag para 0,11E/Fy < D/t < 0,114E/Fy. Confirmado por el usuario; se informan ambos valores.
- **D-3** W: el modo TB (E4) se calcula siempre (Tabla E1.1); la cobertura lo exige solo cuando Lz > min(Lx, Ly) o hay desplazamiento del arriostramiento (texto de E4).
- **D-4** Ancho de paredes de PTE rectangular: columna `b`/`h` del catálogo = dimensión exterior − 3·tdes (B4.1b(d), radio interior no conocido).
- **D-5** Ángulos (E5): `ra` es ry si se conecta el ala larga y rx si se conecta la corta (convención del catálogo: rx > ry, ala larga paralela a y). En alas iguales se usa el ala larga.
- **D-6** E = 200000 MPa obligatorio; otro valor se rechaza.
- **D-7** PTE rectangular con Lz > min(Lx, Ly): E4-2 con el término de Cw omitido, porque el catálogo no trae Cw (indicación del usuario; es el Fe más bajo de E4-2).
- **D-8** Ángulo simple, E4: se usa r̄o del catálogo. Alas iguales: E4-3 con el eje w como eje de simetría (Few) y H del catálogo. Alas desiguales: E4-4 con las coordenadas del centro de corte en ejes principales (wo, zo), obtenidas de x, y, t y tan α (intersección de las líneas medias de las alas); se verifica que reproducen el r̄o del catálogo (E4-9) con tolerancia del 2 % (máximo observado 0,65 %).
- **D-9** Ángulo simple, E4: longitud efectiva sobre los ejes principales = Kx·Lx, que exige Lx = Ly y Kx = Ky (si no, se bloquea); Lcz = Kz·Lz. Pn = Fn·Ag (E4-1), porque E4 se aplica a ángulos con b/t > 0,71√(E/Fy) y E7 limita su Fn a E3.
- **D-10** Ángulo doble: J = 2·J del ángulo simple de la hoja `L` (la hoja `2L` no trae J); término de Cw omitido según la Nota de E4; ri = rz del ángulo simple; Ki = 0,50.
- **D-11** Ángulo doble: la nomenclatura AISC_Manual_Label indica la separación. Sin sufijo de separación = contacto continuo (caso 1(3), 0,56√(E/Fy)); con sufijo (`X3/8`, `X3/4`, `X1-1/2`) = separadores (caso 3(2), 0,45√(E/Fy)). Indicación del usuario.
- **D-12** E6: la esbeltez modificada se aplica al pandeo con cortante en conectores (eje y, de simetría) y a Fey en E4-3; el eje x no se modifica (Commentary E6). E6.1 (conexión de extremo soldada o pretensada) es condición de aplicación; si no se cumple, se bloquea. E6.2(a) (a/ri ≤ ¾ de la esbeltez gobernante) se verifica: si no se cumple, el estado es FAIL.

## Limitaciones

- Lc = K·L es dato del usuario; no se verifica E2/capítulo C/Apéndice 7.
- Arriostramiento (Apéndice 6), conexiones y los demás requisitos de E6.2 (b)–(e) no se comprueban.
- E4(f) (desplazamientos en ambas direcciones, o en canales/PTE) requiere análisis: bloqueado.
- Ángulos simples fuera de E5 (o con Lc/r de E5 > 200) remiten al capítulo H: bloqueado.
- Nota E2 (Lc/r ≤ 200) solo se informa como recomendación.
- 2L: a los dos lados de cada ángulo se aplica el mismo caso B4.1a (decisión D-11).
