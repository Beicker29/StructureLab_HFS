# Capítulo E — alcance implementado

Fuente: ANSI/AISC 360-22, `a360-22w.pdf` (B4.1a p. 16.1-21; E1–E7 pp. 16.1-38 a
16.1-49). Las erratas locales (2025-01-23 y 2026-09-23) no modifican el capítulo E
ni la tabla B4.1a. Unidades internas: N, mm, MPa; resultados en kN.

## Matriz de familias

Selección organizada según la Tabla de Nota E1.1 y contrastada con el texto
obligatorio de E3–E7.

| Familia (`data/sections.xlsx`) | Elementos B4.1a | Sin elementos esbeltos | Con elementos esbeltos | Estado |
| --- | --- | --- | --- | --- |
| W / IPE / HEA / HEB (`W`) | ala caso 1 (bf/2tf), alma caso 5 (h/tw) | E3 (x, y) + E4(a) TB (E4-2); E4(d)/(e) con `ya` o `xa` | E7 con Fn de cada modo | Verificado |
| Canal (`C`) | ala caso 1 (bf completo), alma caso 5 | E3 (x, y) + E4(b) FTB (E4-3 con Fex, Nota de E4) | E7 con Fn de cada modo | Verificado |
| PTE rectangular (`PTE_RECT`) | paredes caso 6 (b/tdes, h/tdes) | E3; E4-2 solo si Lz > min(Lx, Ly) | E7 (c1 = 0,20) | Verificado salvo E4 (ver C-3) |
| PTE redondo (`PTE_RED`) | caso 9 (D/tdes) | E3; E4-2 (Cw = 0 del catálogo) si Lz > min(Lx, Ly) | E7.2 (E7-6/E7-7) | Verificado |
| Ángulo simple (`L`) | ambas alas caso 3 | E5(a)/(b) con E3 | E5 + E7 (Fn de E3) | Parcial: E4 si b/t > 0,71√(E/Fy) bloqueado (C-2) |
| Ángulo doble (`2L`) | caso 1 o 3 según contacto | — | — | No implementado (C-1) |
| Barra maciza (entrada) | ninguno | E3 | — | Verificado |

“Verificado” significa contrastado con cálculos independientes en los casos de
la tabla siguiente, sin condiciones obligatorias abiertas dentro del dominio
declarado. No es una validación por terceros.

## Verificación con cálculos independientes

`tests/oracles/chapter_e.py` recalcula en Decimal (50 dígitos), leyendo el Excel
directamente y sin importar el paquete. Resultados (kN):

| Caso | Perfil | Fy | Esbelto | Gobierna | Pn | φPn | Pn/Ω |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RHSS-nonslender | PTE100X100X4MM | 345 | no | FB-x | 312.96 | 281.67 | 187.40 |
| RHSS-slender | PTE120X60X2MM | 345 | sí | FB-y | 140.66 | 126.59 | 84.23 |
| C-flexural | C15X50 | 345 | no | FB-y | 882.55 | 794.30 | 528.47 |
| C-flexural-torsional | C15X50, L=1000 | 345 | no | FB-y | 2811.81 | 2530.63 | 1683.72 |
| C-FTB-governs | C15X50, Ly=1000 | 345 | no | FTB | 2504.79 | 2254.31 | 1499.87 |
| C-slender | C12X20.7 | 450 | sí | FB-y | 1042.30 | 938.07 | 624.13 |
| W-torsional | W14X90 | 345 | no | TB | 5466.31 | 4919.68 | 3273.24 |
| W-slender-web | W8X10 | 345 | sí | FB-y | 168.25 | 151.42 | 100.75 |
| W-bracing-offset-E4-10 | W14X90, ya=200 | 345 | no | FB-y | 4379.00 | 3941.10 | 2622.16 |
| CHSS-nonslender | PTER4"X3.00MM | 345 | no | FB-x | 251.31 | 226.18 | 150.49 |
| CHSS-torsional-length | PTER4"X3.00MM, Lz=5000 | 345 | no | FB-x | 251.31 | 226.18 | 150.49 |
| CHSS-slender-E7-7 | PTER24"X12.70MM | 450 | sí | FB-x | 8653.36 | 7788.03 | 5181.66 |
| L-E5a-equal | L4X4X1/4 | 250 | sí | FB-E5 | 147.20 | 132.48 | 88.14 |
| L-E5b-short-leg | L6X4X3/8 | 250 | sí | FB-E5 | 313.38 | 282.04 | 187.65 |
| L-E5a-slender-leg | L4X4X1/4, L=600 | 345 | sí | FB-E5 | 233.52 | 210.17 | 139.83 |

L = 3000 mm y K = 1 salvo indicación. El software coincide con todos los modos
(Fe, Fn, área, Pn) en LRFD y ASD con tolerancia relativa 1e-9.

## Decisiones ingenieriles vigentes

- **D-1** c2 de E7-4 sin redondear (la Tabla E7.1 imprime 1,31/1,38/1,49). Confirmado por el usuario.
- **D-2** E7-7: Ae ≤ Ag. La ecuación literal da Ae > Ag para 0,11E/Fy < D/t < 0,114E/Fy. Confirmado por el usuario; se informan ambos valores.
- **D-3** W: el modo TB (E4) se calcula siempre (Tabla E1.1); la cobertura lo exige solo cuando Lz > min(Lx, Ly) o hay desplazamiento del arriostramiento (texto de E4).
- **D-4** Ancho de paredes de PTE rectangular: columna `b`/`h` del catálogo = dimensión exterior − 3·tdes (B4.1b(d), radio interior no conocido).
- **D-5** Ángulos: `ra` es ry si se conecta el ala larga y rx si se conecta la corta (convención del catálogo: rx > ry, ala larga paralela a y). En alas iguales se usa el ala larga.
- **D-6** E = 200000 MPa obligatorio; otro valor se rechaza.

## Limitaciones

- Lc = K·L es dato del usuario; no se verifica E2/capítulo C/Apéndice 7.
- Arriostramiento (Apéndice 6), conexiones y requisitos de E6.2 no se comprueban.
- E4(f) (desplazamientos en ambas direcciones, o en canales/PTE) requiere análisis: bloqueado.
- Ángulos simples fuera de E5 (o Lc/r de E5 > 200) remiten al capítulo H: bloqueado.
- Nota E2 (Lc/r ≤ 200) solo se informa como recomendación.

## Consultas técnicas pendientes

- **C-1 Ángulos dobles.** (a) ¿Los perfiles `2L…` sin sufijo de separación son
  “en contacto continuo” (B4.1a caso 1(3), λr = 0,56√(E/Fy)) y los de sufijo
  `X3/4`, `X1-1/2` “con separadores” (caso 3(2), 0,45√(E/Fy))? (b) El catálogo
  no trae J ni Cw para 2L; E4-7 necesita J (la Nota de E4 permite omitir Cw).
  ¿Usar J = 2·J del ángulo simple de la hoja `L`? (c) E6 requiere tipo de
  conectores, separación `a` y ri como datos de entrada.
- **C-2 Ángulo simple con b/t > 0,71√(E/Fy).** E5 exige además FTB según E4. La
  entrada no define longitudes efectivas en ejes principales; los ángulos
  desiguales requieren E4-4 con coordenadas del centro de corte (el catálogo no
  las trae; H solo existe para alas iguales).
- **C-3 PTE rectangular con Lz > min(Lx, Ly).** E4-2 necesita Cw, ausente en el
  catálogo. Alternativas: bloquear (actual), Cw = 0 (conservador) o Cw calculado
  desde la geometría.
