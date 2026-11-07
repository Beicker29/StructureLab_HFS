# Capítulo I — alcance implementado (etapas 1 y 2 y contenidos de las Design Guides)

Fuente: ANSI/AISC 360-22, `a360-22w.pdf`: Specification pp. 16.1-89 a 16.1-120 y Commentary pp. 16.1-418 a
16.1-472 (Fig. C-I3.8 para los bloques de tensiones). Errata de septiembre 2026: I5-2 usa Fysr. Solo LRFD.
Las reglas salen de la Specification; el Commentary solo se usa donde se indica.

## Alcance

El tipo de miembro se declara en `composite.kind`; no se deduce de la sección.

| Tipo | Compresión | Tracción | Flexión | Cortante | Interacción |
| --- | --- | --- | --- | --- | --- |
| `filled`: PTE rectangular y redondo o cajón soldado, con barras opcionales | I2.2b, φc = 0,75 | I2-14, φt = 0,90 | I3.4b, φb = 0,90 | I4-1, φv = 0,90 | H1.1, I5-1, Método 2 (compacta) |
| `encased`: W embebido | I2.1b, φc = 0,75 | I2-8, φt = 0,90 | I3.3a(2) o (3), φb = 0,90 | I4.1(a): Capítulo G | H1.1, Método 2 con I3.3a(3) |
| `beam`: viga W con conectores | INCOMPLETO | INCOMPLETO | Positiva: I3.2a(a); negativa: I3.2b, Capítulo F | I4.3: Capítulo G | INCOMPLETO |
| `wall`: muro de placas plano con placas de cierre | I2.3a, φc = 0,90 | I2-16, φt = 0,90 | I3.5 en su plano, φb = 0,90 | I4-2 en su plano, φv = 0,90 | I5(c): plástica |
| `c_wall`: muro en C (Guía 38, no norma) | I2.3a | I2-16 | A.2.1, A.2.2, A.2.6 | I4-2 a lo largo de las alas | A.2.3 a A.2.5, eje menor |
| `coupling_beam`: viga de acoplamiento (Guía 38, no norma) | INCOMPLETO | INCOMPLETO | A.3, compacta | I4-1 | Sin axial |

`composite.anchor` añade el chequeo `anchor` (I8.3) a un miembro relleno, embebido o muro. En vigas se usa I8.2.

Fuera del alcance: diafragmas (I7), conexión ensayada (I8.4), Método 3 del Commentary de I5, muros con elementos de borde o en
I, y flexión y cortante de muros fuera de su plano.

## Barras internas y Apéndice 2

`composite.filled`: `Fysr`, `bars`, `transverse`. Pno, EIeff y Mp suman las barras. Redondo no compacto: My de
`codes/aisc_dg06/filled.py` (Guía 6, 2.7), con I3-5b. Rectangular no compacto o esbelto con barras: INCOMPLETO. Con `Fy` o `f'c` por
encima de I1.3 y dentro del Apéndice 2 (Fy ≤ 690 MPa, f'c ≤ 100 MPa), los rellenos rectangulares de concreto normal se calculan
con ese apéndice, incluida I5-1a con A-2-3 y A-2-4, sin barras.

## Segundo orden (Apéndice 8.1)

`composite.second_order`: `axis`, `Mnt`, `Mlt`, `Pnt`, `Plt`, `M1_M2` (omitir con carga transversal: Cm = 1), `Lc1`, `Pstory`, `Pmf`,
`H`, `L`, `drift`; `axis` es `x_3` o `y_2` y `Pnt`, `Plt` llevan el signo de ETABS (tracción positiva). Sustituye a `P` y `Mx_3` o
`My_2`, que no se indican. EI* = 0,8·τb·(EI)eff (I1.5(d), (f)), con τb = 0,8 en rellenos y
embebidos y 1,0 en muros; se usa Pr = Pnt + Plt en B1, como permite 8.1.2. El resultado guarda B1, B2, Pe1 y Pestory en `second_order`.

## Contenidos de las Design Guides

Muros en C, vigas de acoplamiento, incendio, cajones, factor de forma, sección controlada por tracción y rigideces de
servicio, con su origen y sus límites, en [design-guides.md](design-guides.md). `wall.allow_slender_plates` aplica C-I1-1 y C-I1-2 en
compresión; flexión y cortante siguen exigiendo I1-4.

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
- `composite.pour_height`: altura de colado del concreto fresco (mm), obligatoria en rellenos rectangulares y muros (DI-25).
- `composite.interaction`: opcional (DI-22). Sin indicarlo rige I5: H1.1 en embebidos y rellenos compactos; I5-1 en rellenos no compactos o
  esbeltos con compresión y flexión en un eje, y H1.1 si no; Apéndice 2 en alta resistencia. Se puede pedir `H1`, `I5`, `M2` o `M2S`; en rellenos con barras, `M2` y `M2S` se reemplazan por H1.1. Los muros no lo usan.
- `composite.encased`: `H`, `B`, `Fysr`, `bars` (`area`, `db`, `x`, `y` desde el centroide), `transverse` (`db`,
  `spacing`), `flexure_method` (`steel` por defecto, o `composite`) y `anchors_provided`.
- `composite.beam`: `span`, un límite por lado (`left_beam_spacing` o
  `left_edge_distance`; igual a la derecha), `tc`, `deck`, `studs`, `channels` y `shored`. La losa está en la cara +2:
  `Mx_3 > 0` es flexión positiva y `Mx_3 < 0` negativa, con el acero solo (Capítulo F; [axes.md](axes.md)). Sin apuntalar exige un case con `condition = construction` (I3.1b): si falta, INCOMPLETO.
- `composite.beam.studs.detailing` y `composite.beam.channels.detailing` (I8.2d, obligatorio con momento positivo; DI-24):
  `longitudinal_spacing`, `free_edge`, `distribution` (`uniform` o `design_documents`) y, según el caso, `transverse_spacing`
  (más de un perno por nervio), `lateral_cover` (sin deck) y `free_edge_distance` (con borde libre). Si falta un dato: INCOMPLETO.

Se comprueban como requisitos, con `FAIL` si no se cumplen: As/Ag ≥ 1 %, cuantía ≥ 0,004, refuerzo transversal,
separación entre barras y núcleo (encased); límites de deck y pernos (I3.2c, I8.1, I8.2), detallado de conectores (I8.2d) y sección de acero en
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
| i5-high-axial | PTE120X60X2MM, P=−120, Mu = 3 (I5-1a) | no compacta | cp 0.172; cm 1.063; 0.944 |
| i5-low-axial | igual, P=−10, Mu = 8 (I5-1b) | no compacta | 0.832 |
| m2s-filled-high | PTE100X50X3MM, L = 2000, P=−100, Mu = 4 (C-I5-1b) | compacta | PA 135.44; PC 42.64; 1.075 |
| m2s-filled-low | igual, P=−10, Mu = 8 (C-I5-1a) | compacta | 0.915 |
| m2-filled | igual, P=−40, Mu = 8 | compacta | MD'' 9.09; 0.922 |
| m2s-encased | W10X45 embebido, L = 4267, P=−5000, Mu = 800 | – | PA 10668.37; PC 7423.71; 0.869 |
| m2-encased | igual | – | MD'' 1296.30; 0.781 |
| wall-C | L = 3000, tsc = 300, t = 10, tf = 20, Fy = 345, f'c = 35, altura 6000 | – | Pno 49220.80; φcPn 35050.64 |
| wall-T | igual | – | φtPn 22107.60 |
| wall-M | igual | – | a 942.91; Mn 26971.36 |
| wall-V | igual | – | φvVn 16240.26 |
| wall-PM-compression | igual, P=−8000, Mu = 20000 | – | Mc 26983.87; 0.741 |
| wall-PM-tension | igual, P=3000, Mu = 15000 | – | Mc 22587.07; 0.664 |
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
- **DI-3** Bloqueado con INCOMPLETO: rectangulares no compactos o esbeltos con barras, porque Fig. C-I3.8 no las incluye. El Commentary
  solo da bloques para secciones rectangulares; los redondos no compactos usan My de AISC Design Guide 6, 2.7, que el programa declara
  fuera de la norma, y en flexión no hay redondos esbeltos, porque λr es el máximo permitido (2026-10-30).
- **DI-4** Kc = 1 en I4-1, el valor menor que permite la Specification; no se calcula Mu/(Vu·d).
- **DI-5** I4-1 se imprime una sola vez, con 0,06 válido para f'c en ksi: en el código equivale a 0,158·Ac·√f'c con
  f'c en MPa. Usar 0,06 con MPa daría una contribución del concreto 2,6 veces menor sin base dimensional.
- **DI-6** Embebidos a cortante: solo I4.1(a). I4.1(b) e I4.1(c) requieren ACI 318, que no está en el repositorio.
- **DI-7** Vigas: la losa cuenta sobre el deck en ambas orientaciones (con deck paralelo I3.2c.3 permite más; es
  conservador). Flexión negativa: acero solo; la alternativa compuesta de I3.2b no está implementada. h/tw > 3.76√(E/Fy):
  INCOMPLETO. P o My_2 en una viga: INCOMPLETO.
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
- **DI-14** Sección controlada por tracción (I3.3a(e), I3.4a(d)): se calcula εt como AISC Design Guide 6, 2.4.1, con |P| < 0,10·Pn. La
  Specification no dice qué es una viga en este contexto: es requisito solo con `composite.flexural_member = true`; sin declararlo, la
  memoria lo advierte. No aplica con `false` (confirmado por el usuario, 2026-10-30).
- **DI-15** C-I1-1 aparece impresa en el Commentary sin el exponente de (b/tp), lo que nunca reduciría Fy dentro de un rango realista.
  Se usa (b/tp)², como AISC Design Guide 38, Ec. 2-2, que deriva de la misma curva de Euler con K = 0,8. Las erratas del repositorio no
  lo mencionan (confirmado por el usuario, 2026-10-30).
- **DI-16** Rigideces de servicio: Gc = 0,4·Ec, como I1-3, porque la Guía 6 no lo define. La guía tampoco define Jc de rectangulares
  (2-14); se usa Jc ≈ a·b³·[1/3 − 0,21·(b/a)·(1 − b⁴/(12a⁴))], con a ≥ b las dimensiones del núcleo de concreto, sin descontar
  esquinas redondeadas ni barras (indicación del usuario, 2026-10-31). Cajones: Js = 2t(B−t)²(H−t)²/(B+H−2t) (pared delgada cerrada), que la guía no imprime.
- **DI-17** Cajones (Guía 6, 2.5): ri = 0 y Av = 2·H·t, frente a 2·h·t de los PTE. Es la única diferencia de cálculo por declarar
  `composite.box`.
- **DI-18** Muros en C: st y α de I1-6 con el menor de los espesores tsc,w y tsc,f, porque la Guía 38 no resuelve cuál usar en una sección
  con dos; es el lado conservador. A.2.3 a A.2.5 fijan el lado comprimido con el signo de P: en tracción, las puntas de las alas;
  en compresión, el alma; otra combinación queda bloqueada. El lado comprimido sale del signo de `My_2` (cara +3) y de
  `composite.c_wall.web_side` (decisión del usuario, 2026-11-06; sustituye a `minor_axis_compression`).
- **DI-19** Incendio: se aplica la Ec. 6-6a tal como la imprime la guía, sin la rama de I2-3, y la longitud L = Ly_2 con Lc = Ky_2·Ly_2, porque el
  ejemplo toma pandeo del espesor. La Ec. 6-5 se usa solo dentro de sus límites; fuera de ellos, la revisión de horas queda `INCOMPLETE`. La resistencia a temperatura es A-4-12 ([Apéndice 4](appendix-4.md)), con esa misma Lc.
- **DI-20** Rigideces en la memoria (indicaciones del usuario, 2026-10-31).
  - Muros: I1-1 a I1-3 solo se aplican a muros de placas. C2.3 con τb del usuario.
  - Rellenos y embebidos, efectivas: (EI)eff por I2-12 e I2-5; (EA)eff = EA elástica; (GA)eff = Gc·Ac. GJ, si hay ecuación, Guía 6, 2-12 a 2-14.
  - Sin ecuación en la Guía 6, se reporta cada componente solo, sin elegir entre ellos: GAs = Gs·As y GAc = Gc·Ac en redondos rellenos y embebidos; GJs = Gs·J y GJc = Gc·Jc en embebidos.
    La elástica y la efectiva de cada componente son la misma.
  - Método directo: EA* = 0,8·(EA)eff; EI* = 0,8·τb·(EI)eff; GA* = 0,8·(GA)eff; GJ* = 0,8·GJ; GJs* = 0,8·GJs; GJc* = 0,8·GJc. En tracción neta, acero solo con C2.3 (I1.5(c)).
  - Miembros no compuestos: τb = 1,0 siempre, por C2.3(c) (indicación del usuario, 2026-10-31), con la carga ficticia a cargo del modelo; no es un dato y otro valor se rechaza.
  - Miembros compuestos: τb es un dato obligatorio del usuario y no se calcula. El capítulo 4 lo compara con I1.5(d), (f), o con C2.3(c) en tracción neta; una diferencia solo se reporta.
    Sin dato, el estado es INCOMPLETO. B1 del Apéndice 8.1 sigue usando τb de I1.5.
  - Vigas compuestas y de acoplamiento no tienen rigideces de método directo: τb no aplica y no se exige. La Guía 6 pide P de servicio: el programa toma |P| de la combinación si es compresión.
- **DI-21** Requerimientos técnicos (indicación del usuario, 2026-10-31): memoria con materiales (I1.3, Apéndice 2, A3.1a, E3) y geometría (I1.4, I1.6, I2.1a, I2.2a, I3.4a, E5, E6.2,
  F8, B4.3b). Uno obligatorio incumplido impide PASS aunque no intervenga en la demanda de la combinación; las Notas de D1 y E2 son recomendación y no lo impiden. ACI 318
  (I1.1) y la designación ASTM (A3.1a) se reportan «Falta implementación». En rellenos y embebidos con solo cortante, las cuantías de I2 e I3 no aplican.
- **DI-22** Interacción y diagramas, I5 (indicaciones del usuario, 2026-10-31). Sin `composite.interaction`: I5(a), H1.1; I5(b), I5-1a y b en compresión con flexión en un eje, y H1.1 en flexión biaxial o tracción;
  Apéndice 2 según la Guía 6, 2.6 (A-2-3 y A-2-4), en alta resistencia; I5(c) en muros, que no tienen interacción biaxial definida. Alta resistencia en dos ejes: I5-1a o b con Mrx/Mcx + Mry/Mcy (extensión indicada por el usuario, no es del Apéndice 2), evaluada con cp y cm de cada eje; gobierna el mayor. Alta resistencia sin compresión: H1.1, con nota. Un método pedido se reemplaza por el Apéndice 2 y la memoria lo avisa. M2 y M2S siguen como opción, salvo en rellenos con barras: si se piden, se usa H1.1 y la memoria lo indica. Diagrama informativo en 10.2, que no decide el estado: Tablas 6-3 y 6-4 del Manual en
  rellenos compactos con Asr = 0, y 6-2a y 6-2b en embebidos con sus barras (siempre tienen Asr, I2.1a(c)). 6-2a exige barras extremas y a la línea central; 6-2b, como el Ejemplo 2.4 de la Guía 6, toma en Zr solo las extremas.
  Fuera de esas disposiciones, o con Asr ≠ 0 en rellenos, sin diagrama. Cada punto se transforma con λ = Pn/Pno, φc y φb (Commentary I5). La Tabla 6-4 usa pared delgada: su punto B difiere cerca de 1 % de Mp de I3.4b.
- **DI-23** Transferencia de carga (I6) retirada (indicación del usuario, 2026-10-31): corresponde al diseño de conexiones, fuera del alcance. Sigue en el historial de Git.
- **DI-24** Conectores de vigas (indicación del usuario, 2026-10-31): toda viga compuesta con momento positivo revisa I8.1 e I8.2, con I8.2d
  obligatorio y la separación declarada, no derivada de `count`. Por I8.1, I8.3 no aplica a vigas: sigue disponible en `composite.anchor` para
  rellenos, embebidos y muros, y el ejemplo `composite_anchor.json` se retiró (lo muestra `composite_encased.json`).
- **DI-27** Ejemplos (indicación del usuario, 2026-10-31): perfiles de acero, viga compuesta, rellenos, cajón y embebido llevan deflexiones y un case de construcción; la viga de
  acoplamiento, solo deflexiones; los muros y `multi_member`, ninguno. Sus valores son ilustrativos. La construcción de módulos de muro vacíos da INCOMPLETO: el Capítulo F no cubre esas secciones.
- **DI-26** Casos por condición (indicación del usuario, 2026-10-31): cada case declara `condition` (`ultimate`, `construction`, `fire`). Construcción: acero solo, con sus
  longitudes, Mu y Vu únicamente. Incendio: Apéndice 4, 4.2.4d, con `fire` ([detalle](appendix-4.md)). Deflexiones (`serviceability`): datos del
  usuario frente a L/n con la luz efectiva; exceder un límite se reporta y no cambia el estado. Una sola memoria por sección, con el case de mayor DCR en cada revisión.
- **DI-25** Colado del concreto (indicación del usuario, 2026-10-31; no es norma). Rellenos rectangulares: σmax ≤ 0,5 Fy y δmax ≤ L/2000 con
  L = min(Lx_3, Ly_2) (DG6 4.3; Commentary C-I2-1, C-I2-2). Redondos: no aplica. Muros planos: altura ≤ 9144 mm con placas que cumplen I1-4
  (DG38 2.2.1.2), porque las ecuaciones de DG6 no consideran los tirantes. La altura es obligatoria (sin ella, INCOMPLETO), pero un límite
  incumplido se reporta en 4.2 como recomendación y no cambia el estado. Los agujeros de ventilación usan la misma `composite.pour_height`.

## Limitaciones

- Pr y Mr son datos del usuario, con las rigideces de I1.5 (DH-3), salvo con `composite.second_order`.
- ACI 318 no se verifica: cuantía máxima, recubrimientos, separación entre barras ni desarrollo del refuerzo.
- Ec usa la fórmula métrica de la Specification; difiere cerca de 5 % de la fórmula en ksi de los ejemplos.
- I8.2d se comprueba con los datos declarados; el programa no los contrasta con `count` ni con la luz. Tampoco calcula conectores para
  cargas concentradas (I8.2c), la soldadura del canal (I8.2b) ni la alternativa de ACI 318, Capítulo 17, para el borde libre (I8.2d(c)).
- El sentido del momento en vigas sale del signo de `Mx_3` con la losa en la cara +2; una losa en la cara −2 no se puede
  declarar.
