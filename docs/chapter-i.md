# Capítulo I — alcance implementado (etapas 1 y 2)

Fuente: ANSI/AISC 360-22, `a360-22w.pdf`: Specification pp. 16.1-89 a 16.1-120 y Commentary pp. 16.1-418 a
16.1-472 (Fig. C-I3.8 para los bloques de tensiones). Errata de septiembre 2026: I5-2 usa Fysr. Solo LRFD.
Las reglas salen de la Specification; el Commentary solo se usa donde se indica.

## Alcance

El tipo de miembro se declara en `composite.kind`; no se deduce de la sección.

| Tipo | Compresión | Tracción | Flexión | Cortante | Interacción |
| --- | --- | --- | --- | --- | --- |
| `filled`: PTE rectangular y redondo, sin barras | I2.2b, φc = 0,75 | I2-14, φt = 0,90 | I3.4b, φb = 0,90 | I4-1, φv = 0,90 | H1.1, I5-1, Método 2 (compacta) |
| `encased`: W embebido | I2.1b, φc = 0,75 | I2-8, φt = 0,90 | I3.3a(2) o (3), φb = 0,90 | I4.1(a): Capítulo G | H1.1, Método 2 con I3.3a(3) |
| `beam`: viga W con conectores | INCOMPLETO | INCOMPLETO | Positiva: I3.2a(a); negativa: I3.2b, Capítulo F | I4.3: Capítulo G | INCOMPLETO |
| `wall`: muro de placas plano con placas de cierre | I2.3a, φc = 0,90 | I2-16, φt = 0,90 | I3.5 en su plano, φb = 0,90 | I4-2 en su plano, φv = 0,90 | I5(c): plástica |

`composite.anchor` añade el chequeo `anchor` (I8.3) a un miembro relleno, embebido o muro. En vigas se usa I8.2.

Fuera del alcance: transferencia de carga (I6), diafragmas (I7), conexión ensayada (I8.4), Apéndice 2, Método 3 del
Commentary de I5, muros con elementos de borde o en C e I, y flexión y cortante de muros fuera de su plano.

## Método 2 de I5 (Commentary)

- `M2S` (Método 2 simplificado): C-I5-1a y C-I5-1b con los puntos A'', B'' y C''; admite flexión en dos ejes.
- `M2`: curva A''-C''-D''-B'' en un eje, con λ = Pn/Pno en A, C y D. El valor es demanda/curva a lo largo del rayo desde
  el origen.

Solo con compresión, en rellenos compactos o embebidos con `flexure_method = composite`. PC = C2·f'c·Ac; PD = PC/2;
MD con el eje neutro plástico en el centroide; MC = MB = Mn de I3. Las ecuaciones de los puntos están en el Manual AISC
Parte 6, que no está en el repositorio: se dedujeron de la distribución plástica y se contrastan con I.6 e I.11 (DI-12).

## Muros de placas

`composite.wall`: `length`, `tsc`, `t`, `tf` (placas de cierre, obligatorias según I1.6), `b`, `st` y `dtie`. El nombre
`section_name` es libre, porque la sección se construye con estos datos.

Requisitos, con `FAIL` si no se cumplen: placas entre 1 % y 10 % de la sección (I1.6), I1-4, st ≤ tsc y I1-5M.
Rigidez I1-1, Pno I2-15, Mn con Fig. C-I3.8(a) y Commentary I3.5; cortante I4-2 con Asw = 2·t·L. I5(c) exige los métodos de
I1.2, así que H1.1 no se ofrece: Mn se calcula a la fuerza axial requerida (DI-11).

## Anclajes de componentes (I8.3)

`composite.anchor`: `type` (`stud`, `channel`), `Qrv`, `Qrt` (kN por anclaje), `spacing`; pernos: `d`, `Fu`, `height`,
`head_diameter` (con tracción), `edge_distance` (omitir si no hay borde libre), `breakout_in_shear`, `base_thickness`,
`over_web`, `solid_slab`, `reinforcement_shear`, `reinforcement_tension`; canales: `la`, `tf`, `tw`.

I8-3 con φ = 0,65, I8-4 con φ = 0,75, I8-5 si actúan juntos, y I8-2 con φ = 0,75 en canales. Requisitos: h/d mínimo, separación
4d a 32d, d ≤ 19 mm (25 mm solo a cortante en losa maciza) y d ≤ 2,5 veces el metal base. Se bloquea lo que I8.3 remite a
ACI 318, Capítulo 17: rotura a cortante o borde y separación cortos sin refuerzo declarado, cabeza menor que 1,6d, y
cortante con tracción en concreto liviano.

## Entrada

- `composite.concrete`: `fc` (MPa), `wc` (kg/m³) y `lightweight`, obligatorio porque define el límite de I1.3(a).
- `composite.interaction`: `H1` (por defecto); `I5`, solo en rellenos no compactos o esbeltos con flexión en un eje;
  `M2` o `M2S` (Commentary I5). Los muros no lo usan.
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
| m2s-filled-high | PTE100X50X3MM, L = 2000, Pu = 100, Mu = 4 (C-I5-1b) | compacta | PA 135.44; PC 42.64; 1.075 |
| m2s-filled-low | igual, Pu = 10, Mu = 8 (C-I5-1a) | compacta | 0.915 |
| m2-filled | igual, Pu = 40, Mu = 8 | compacta | MD'' 9.09; 0.922 |
| m2s-encased | W10X45 embebido, L = 4267, Pu = 5000, Mu = 800 | – | PA 10668.37; PC 7423.71; 0.869 |
| m2-encased | igual | – | MD'' 1296.30; 0.781 |
| wall-C | L = 3000, tsc = 300, t = 10, tf = 20, Fy = 345, f'c = 35, altura 6000 | – | Pno 49220.80; φcPn 35050.64 |
| wall-T | igual | – | φtPn 22107.60 |
| wall-M | igual | – | a 942.91; Mn 26971.36 |
| wall-V | igual | – | φvVn 16240.26 |
| wall-PM-compression | igual, Pu = 8000, Mu = 20000 | – | Mc 26983.87; 0.741 |
| wall-PM-tension | igual, Pu = −3000, Mu = 15000 | – | Mc 22587.07; 0.664 |
| stud-shear | d = 19, Fu = 450, Qrv = 50 | – | Qcv 82.93; 0.603 |
| stud-tension | igual, Qrt = 60 | – | Qct 95.69; 0.627 |
| stud-interaction | igual, Qrv = 40, Qrt = 60 (I8-5) | – | 0.756 |
| channel-shear | la = 100, tf = 8, tw = 6, f'c = 35, Qrv = 100 | – | Qc 246.88; 0.405 |

Contraste con los AISC Design Examples I.1, I.4 a I.7, I.9 a I.11 e I.12 en [design-examples.md](design-examples.md), y con los
ejemplos de AISC Design Guide 6 y 38, incluidos los muros, en [design-guides.md](design-guides.md).

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
- **DI-11** Muros, I5(c): I1.2 no da una fórmula de interacción. Se toma Mn de la distribución plástica a P = Pr, como AISC Design
  Guide 38 (A.1.2, A.1.3 y ejemplos 2.2 y 4.1), y el valor es Mr/(0,90·Mn); si Pr excede la sección, el valor es P/Pmáx. La
  estabilidad se comprueba en el chequeo axial. Esquinas rectas, como Fig. C-I3.8. Antes se usaba P = Pr/0,90; se corrigió
  con la guía (2026-10-30).
- **DI-12** Método 2: se implementan `M2` y `M2S` (indicación del usuario, 2026-10-30, sin distinguirlos). `M2` también compara la
  demanda con la curva nominal sin φ ni λ y gobierna el mayor valor, porque el Commentary y los ejemplos I.6 e I.11 advierten
  que D'' puede salir de esa curva y lo declaran inseguro. No se usa el punto E: el tramo recto A''-C'' queda del lado seguro.
  AISC Design Guide 6 (2.3.2) excluye el punto D en su método; `M2` lo conserva con ese control y la memoria lo advierte: para
  diseño conviene `M2S`.
- **DI-13** I8.1 limita d a 19 mm salvo solo cortante en losa maciza, aunque la Tabla I.12-1 del ejemplo lista 1 in a tracción. Se
  sigue la Specification.

## Limitaciones

- Pr y Mr son datos del usuario, con las rigideces de I1.5 (DH-3). El programa no calcula B1 ni (EI)eff para el análisis.
- ACI 318 no se verifica: cuantía máxima, recubrimientos, separación entre barras, sección controlada por tracción
  (I3.3a(e), I3.4a(d)) ni desarrollo del refuerzo.
- Ec usa la fórmula métrica de la Specification; difiere cerca de 5 % de la fórmula en ksi de los ejemplos.
- Longitud de los pernos, recubrimiento y separación se comprueban solo con los datos que se declaran; la separación entre
  conectores (I8.2d) y su distribución no se comprueban.
- `Mux`, `Muy` y sus signos no definen el sentido del momento en vigas: se declara en `composite.beam.moment`.
