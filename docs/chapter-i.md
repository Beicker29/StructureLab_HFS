# Capítulo I — alcance implementado (etapa 1)

Fuente: ANSI/AISC 360-22, `a360-22w.pdf`: Specification pp. 16.1-89 a 16.1-120 y Commentary pp. 16.1-418 a
16.1-472 (Fig. C-I3.8 para los bloques de tensiones). Errata de septiembre 2026: I5-2 usa Fysr. Solo LRFD.
Las reglas salen de la Specification; el Commentary solo se usa donde se indica.

## Alcance

El tipo de miembro se declara en `composite.kind`; no se deduce de la sección.

| Tipo | Compresión | Tracción | Flexión | Cortante | Interacción |
| --- | --- | --- | --- | --- | --- |
| `filled`: PTE rectangular y redondo, sin barras | I2.2b, φc = 0,75 | I2-14, φt = 0,90 | I3.4b, φb = 0,90 | I4-1, φv = 0,90 | H1.1 o I5-1 |
| `encased`: W embebido | I2.1b, φc = 0,75 | I2-8, φt = 0,90 | I3.3a(2) o (3), φb = 0,90 | I4.1(a): Capítulo G | H1.1 |
| `beam`: viga W con conectores | INCOMPLETO | INCOMPLETO | Positiva: I3.2a(a); negativa: I3.2b, Capítulo F | I4.3: Capítulo G | INCOMPLETO |

Fuera de esta etapa: muros de placas (I1.6, I2.3, I3.5, I4.4), transferencia de carga (I6), diafragmas (I7),
anclajes de componentes (I8.3, I8.4), Apéndice 2 y Métodos 2 y 3 del Commentary de I5.

## Entrada

- `composite.concrete`: `fc` (MPa), `wc` (kg/m³) y `lightweight`, obligatorio porque define el límite de I1.3(a).
- `composite.interaction`: `H1` (por defecto) o `I5`, solo en rellenos no compactos o esbeltos con flexión en un eje.
- `composite.encased`: `H`, `B`, `Fysr`, `bars` (`area`, `db`, `x`, `y` desde el centroide), `transverse` (`db`,
  `spacing`), `flexure_method` (`steel` por defecto, o `composite`) y `anchors_provided`.
- `composite.beam`: `moment` (`positive`, `negative`), `span`, un límite por lado (`left_beam_spacing` o
  `left_edge_distance`; igual a la derecha), `tc`, `deck`, `studs`, `channels`, `shored` y `Mu_construction`.

Se comprueban como requisitos, con `FAIL` si no se cumplen: As/Ag ≥ 1 %, cuantía ≥ 0,004, refuerzo transversal,
separación entre barras y núcleo (encased); límites de deck y pernos (I3.2c, I8.1, I8.2), y sección de acero en
construcción cuando la viga no está apuntalada (I3.1b). Materiales fuera de I1.3: INCOMPLETO.

## Flexión de rellenos rectangulares

`flange` es la pared perpendicular a la dirección de flexión y `web` la paralela (Tabla I1.1b).

- Compacta: Mp con los bloques de Fig. C-I3.8(a), Z del catálogo y concreto con esquinas redondeadas (DI-2).
- No compacta: I3-5b con My de Fig. C-I3.8(b); si ambas paredes son no compactas, gobierna el menor Mn.
- Esbelta: Mcr de Fig. C-I3.8(c), con Fn de I2-10 en el ala comprimida.

## Verificación con cálculos independientes

`tests/oracles/chapter_i.py` (Decimal, sin importar el paquete) escribe las ecuaciones desde la Specification y
halla los ejes neutros por bisección. Coincidencia con tolerancia relativa 1e-9. Fuerzas en kN y momentos en kN·m:

| Caso | Perfil y datos | Clase | Resultado |
| --- | --- | --- | --- |
| filled-rect-compact-C | PTE100X50X3MM, Fy = 345, f'c = 35, L = 2000 | compacta | Pno 395.68; φcPn 135.44 |
| filled-rect-noncompact-C | PTE120X60X2MM, Fy = 345, f'c = 35, L = 2000 | no compacta | Pno 412.31; φcPn 172.87 |
| filled-rect-slender-C | PTE100X40X1.5MM, Fy = 500, f'c = 35, L = 1500 | esbelta | Pno 232.73; φcPn 86.25 |
| filled-round-C | PTER6"X6.00MM, Fy = 345, f'c = 35, L = 4000 | compacta | Pno 1628.67; φcPn 798.50 |
| filled-rect-M-x | PTE100X50X3MM, eje x | compacta | Mn 9.72 |
| filled-rect-M-y | PTE100X50X3MM, eje y | compacta | Mn 5.72 |
| filled-rect-M-noncompact | PTE300X100X5MM, eje y | no compacta | Mp 55.33; My 54.13; Mn 54.85 |
| filled-rect-M-slender | PTE100X40X1.5MM, Fy = 500, eje y | esbelta | Mn 2.90 |
| filled-round-M | PTER6"X6.00MM | compacta | Mn 57.71 |
| filled-rect-V | PTE100X50X3MM | – | φvVn 98.77 |
| filled-round-V | PTER6"X6.00MM | – | φvVn 354.54 |
| encased-C | W10X45 en 610 x 610, 8 barras de 510 mm², Fysr = 420, L = 4267 | – | Pno 15367.04; φcPn 10668.37 |
| encased-T | igual | – | φtPn 4206.33 |
| encased-M-x-composite | igual, I3.3a(3), eje x | – | hn 126.99; Mn 1022.90 |
| encased-M-y-composite | igual, I3.3a(3), eje y | – | hn 115.77; Mn 1021.60 |
| encased-M-x-steel | igual, I3.3a(2) | – | Mn 310.50 |
| beam-partial-flange | W21X50, f'c = 28, deck 76 mm, 30 pernos de 19 mm, PNA en el ala | – | C 2296.58; φbMn 1133.37 |
| beam-full-steel | W14X30, losa maciza de 120 mm, 60 pernos, PNA en la losa | – | C 1969.95; φbMn 491.30 |
| beam-partial-web | W21X50, deck 76 mm, 8 pernos, PNA en el alma | – | C 612.42; φbMn 774.65 |
| i5-high-axial | PTE120X60X2MM, Pu = 120, Mu = 3 (I5-1a) | no compacta | cp 0.172; cm 1.063; 0.944 |
| i5-low-axial | igual, Pu = 10, Mu = 8 (I5-1b) | no compacta | 0.832 |

Contraste con los AISC Design Examples I.1, I.4 a I.7 e I.9 a I.11 en [design-examples.md](design-examples.md).

## Decisiones

- **DI-1** Alcance de la etapa 1 (indicación del usuario, 2026-10-30): rellenos, embebidos y vigas compuestas;
  interacción con H1.1 e I5-1; Mn embebido con I3.3a(2) por defecto o I3.3a(3) si se declaran conectores.
- **DI-2** Rellenos rectangulares: As, I y Z del catálogo; concreto con radio interior t, como en los ejemplos I.3,
  I.4 e I.6. Mp usa esa geometría y no las esquinas rectas de Fig. C-I3.8(a), que en I.6 darían unos 162 kip-ft frente a
  los 156 kip-ft del ejemplo. My y Mcr siguen Fig. C-I3.8(b) y (c), con esquinas rectas como en I.7.
- **DI-3** Bloqueado con INCOMPLETO: rellenos redondos no compactos o esbeltos en flexión, porque el Commentary solo da
  bloques para secciones rectangulares. Los rellenos no admiten barras en esta etapa (entrada no disponible).
- **DI-4** Kc = 1 en I4-1, el valor menor que permite la Specification; no se calcula Mu/(Vu·d).
- **DI-5** I4-1 se imprime una sola vez, con 0,06 válido para f'c en ksi: en el código equivale a 0,158·Ac·√f'c con
  f'c en MPa. Usar 0,06 con MPa daría una contribución del concreto 2,6 veces menor sin base dimensional.
- **DI-6** Embebidos a cortante: solo I4.1(a). I4.1(b) e I4.1(c) requieren ACI 318, que no está en el repositorio.
- **DI-7** Vigas: la losa cuenta sobre el deck en ambas orientaciones (con deck paralelo I3.2c.3 permite más; es
  conservador). Flexión negativa: acero solo; la alternativa compuesta de I3.2b no está implementada. h/tw > 3.76√(E/Fy):
  INCOMPLETO. Pu o Muy en una viga: INCOMPLETO.
- **DI-8** Ductilidad de la conexión (I3.2d): si no se cumple ninguna condición del Commentary (luz ≤ 9,1 m, acción
  compuesta ≥ 50 %, conectores ≥ 230 kN/m), la memoria lo advierte; no bloquea porque la Specification no da un límite.
- **DI-9** Compresión: se toma el mayor entre I2 y el acero solo del Capítulo E, como permiten I2.1b e I2.2b.
- **DI-10** Los límites usan los valores métricos impresos (75 mm, 19 mm). Por eso, un deck de 3 in (76,2 mm) o un perno
  de 3/4 in (19,05 mm) dan `FAIL` por conversión estricta; use 75 mm y 19 mm al declarar esos productos.

## Limitaciones

- Pr y Mr son datos del usuario, con las rigideces de I1.5 (DH-3). El programa no calcula B1 ni (EI)eff para el análisis.
- ACI 318 no se verifica: cuantía máxima, recubrimientos, separación entre barras, sección controlada por tracción
  (I3.3a(e), I3.4a(d)) ni desarrollo del refuerzo.
- Ec usa la fórmula métrica de la Specification; difiere cerca de 5 % de la fórmula en ksi de los ejemplos.
- Longitud de los pernos, recubrimiento y separación se comprueban solo con los datos que se declaran; la separación entre
  conectores (I8.2d) y su distribución no se comprueban.
- `Mux`, `Muy` y sus signos no definen el sentido del momento en vigas: se declara en `composite.beam.moment`.
