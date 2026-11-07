# Capítulo F — alcance implementado (etapas 1 y 2)

Fuente: ANSI/AISC 360-22, `a360-22w.pdf` (Tabla B4.1b pp. 16.1-22/23; F1–F13
pp. 16.1-50 a 16.1-73) y errata E25-02 (enero de 2025), que renumera las
ecuaciones de pandeo lateral-torsional de F7 a F7-8, F7-9, F7-10 y F7-11. Solo
LRFD: φb = 0,90 (F1(a)). Momentos en kN·m.

## Matriz de familias y secciones

| Familia | Eje x | Eje y | Estados límite (Tabla de Nota F1.1) |
| --- | --- | --- | --- |
| W / IPE / HEA / HEB | F2 (ala compacta) o F3 (ala no compacta/esbelta); F4 (alma no compacta) o F5 (alma esbelta); F13.1 | F6 | Y, LTB, FLB, TFR o CFY, LTB, FLB, TFY, TFR / Y, FLB |
| I armada soldada (`custom_section` `I_BUILT_UP`) | Doble simetría y alma compacta: F2 o F3 (ala caso 11). Alma no compacta, o simetría simple con alma compacta o no compacta: F4. Alma esbelta: F5. F13.1 y F13.2 | F6 (ala más esbelta, DF-19) | CFY, LTB, FLB, TFY, TFR / Y, FLB |
| Canal | F2 (solo compacto); F13.1 | F6 | Y, LTB, FLB, TFR / Y, FLB |
| PTE rectangular | F7 | F7 | Y, FLB, WLB, LTB (LTB no aplica en eje menor ni en sección cuadrada, Nota de F7.4) |
| PTE redondo | F8 (D/t < 0,45E/Fy) | F8 | Y, LB |
| Barra rectangular / redonda | F11 | F11 | Y, LTB (solo barra rectangular en su eje mayor) |
| Ángulo doble (F9) | F9 (plano de simetría) | — (no cubierto, INCOMPLETO) | Y, LTB, FLB, WLB |
| Ángulo simple (F10) | F10.2(2) ejes geométricos (x_3, y_2), un solo momento | — | Y, LTB, LLB |
| Ángulo simple (F10), ejes principales (giro de `Mx_3`, `My_2`) | w: F10-4 | z: Y y LLB | Y, LTB, LLB / Y, LLB |

Bloqueos con motivo (INCOMPLETO): canal con ala o alma no compacta (sin sección aplicable
en F), alma esbelta en PTE (F7-7), D/t ≥ 0,45E/Fy en PTE redondo y ángulos con flexión sin `heel`.

Ejes y signos de ETABS ([axes.md](axes.md)): `Mx_3` (eje mayor de un I) y `My_2`, con el signo que define la parte
comprimida. Las ecuaciones conservan los símbolos de AISC (Sx, Zx, Iy, ...), con x = eje 3 e y = eje 2.

Cada estado límite de la sección elegida figura en el resultado: calculado o con el
motivo por el que no aplica (p. ej. Lb ≤ Lp, ala compacta). Gobierna el menor Mn.

## Perfiles I con F4 y F5

**Secciones.** F4 y F5 se aplican a los W del catálogo con alma no compacta o esbelta (hoy
ninguno a Fy ≤ 450 MPa: h/tw máx. 57,5) y a las I armadas soldadas de `custom_section`
(`type: "I_BUILT_UP"`, `d`, `tw`, `flange_plus2: {b, t}`, `flange_minus2: {b, t}` (alas de las caras +2 y −2), mm). De las placas, sin
radios de soldadura, salen A, Ix, Iy, Sx (el menor), Sy, Zx (eje neutro plástico de áreas iguales), Zy, r,
h = d − tf,sup − tf,inf (distancia libre, B4.1b(b)), ho, J, Cw, r̄o y H (DF-17).

**Clasificación (B4.1b).** Alas de I armada: caso 11, λp = 0,38√(E/Fy), λr = 0,95√(kc·E/FL), con kc de
la nota [a] y FL de la nota [b] (0,7Fy con alma esbelta; si no, F4-6a/F4-6b); λ = bfc/2tfc del ala
comprimida. Laminados: caso 10. Alma de doble simetría: caso 15 con h/tw; de simetría simple: caso 16
con hc/tw, λp = (hc/hp)√(E/Fy)/(0,54·Mp/My − 0,09)² ≤ λr (My en la fibra que fluye primero, Mp = Fy·Zx); si el
eje neutro plástico cae en el ala comprimida, hp ≤ 0 y el alma es compacta (Commentary F4). La clasificación
se hace a temperatura ambiente, como en todo el capítulo.

**F4.** CFY (F4-1) con Rpc (F4-9a, F4-9b o F4-10, Mp ≤ 1,6·Fy·Sxc, DF-16b); LTB con rt (F4-11, aw de
F4-12), Lp (F4-7), Lr (F4-8) y Fcr (F4-5), J = 0 si Iyc/Iy ≤ 0,23 (DF-16); FLB F4-13/F4-14; TFY F4-15 con
Rpt (F4-16a, F4-16b o F4-17, Mp ≤ 1,6·Fy·Sxt) solo si Sxt < Sxc. Iyc = tfc·bfc³/12.

**F5.** Rpg (F5-6, aw ≤ 10); CFY F5-1; LTB F5-2 con F5-3/F5-4, Lp (F4-7) y Lr (F5-5); FLB F5-7 con F5-8/F5-9;
TFY F5-10 si Sxt < Sxc.

**Ala comprimida.** `Mx_3 > 0` comprime el ala de la cara +2 (`flange_plus2`) y `Mx_3 < 0` la de la cara −2
(`flange_minus2`) (DF-18). En F13.1, Afg es el ala traccionada y Sx el menor módulo elástico.

**F13.2 (requisitos técnicos, obligatorios).** I de simetría simple con `Mx_3`: 0,1 ≤ Iyc/Iy ≤ 0,9 con
cualquiera de las dos alas (F13-2). Alma esbelta sin rigidizadores: h/tw ≤ 0,40E/Fy (F13-4), h/tw ≤ 260 y
aw ≤ 10. Uno incumplido da FAIL aunque las resistencias alcancen.

**Otros capítulos.** E: alas caso 2 de B4.1a (0,64√(kc·E/Fy)), alma caso 5 u 8; doble simetría E4-2,
simetría simple E4(b) con Fey y Fez ([chapter-e.md](chapter-e.md)). G: G2.1(b) siempre (G2.1(a) es solo para
laminados) y G6 ala por ala ([chapter-g.md](chapter-g.md)). H1.2 amplifica Cb solo con doble simetría. En
incendio, A-4-13 queda para los W laminados compactos; la I armada usa el Capítulo F con E(T) y Fy(T)
(DA4-3) y con elementos esbeltos queda bloqueada (4.2.4d).

## Ángulos (etapa 2)

**Ángulo doble (F9), flexión respecto de x (eje 3).** `heel.axis_2` indica de qué lado del eje 2 queda el dorso; las
alas verticales (en el plano de simetría) apuntan al otro lado y están comprimidas en su punta cuando `Mx_3` comprime esa
cara (DF-9). Las alas verticales se identifican por el rótulo:
LLBB → alas largas verticales, SLBB → alas cortas; en ángulos iguales, indistinto
(DF-10). J = 2·J del ángulo componente, leído del catálogo. Y: F9-2 (alas
verticales en tracción) o F9-5 (en compresión); LTB: F9-6/F9-7 con Lp F9-8 y Lr F9-9,
o F9.2(b)(2) con F10-2/F10-3; Mcr F9-10 con B de F9-11/F9-12. FLB (F9.3) con
Sc = Ix/ȳ al dorso de las alas horizontales; WLB (F9.4) con Sx; ambos mediante
F10-6/F10-7.

**Ángulo simple (F10), ejes geométricos.** Se aplica con un solo momento (`Mx_3` o `My_2`), sin fuerza axial y con
`flexure.lateral_torsional_restraint` declarado: `continuous`, o `none`/`at_max_moment` con alas iguales (F10.2(2) remite a
ejes principales en los demás casos). El ala larga es paralela al eje 2: respecto de x (eje 3) el ala perpendicular es la
larga y respecto de y (eje 2) la corta. La punta comprimida sale del signo del momento y de `heel` (DF-9). Sin restricción: My y Sc multiplicados por 0,80
solo en LTB y LLB (F10.2(2)(i), DF-11); restricción en el punto de máximo momento: Mcr × 1,25
(F10.2(2)(ii)). Mcr con F10-5a/F10-5b según la punta comprimida o traccionada.

**Ángulo simple, ejes principales.** En los demás casos `Mx_3` y `My_2` se llevan a los ejes principales w y z con tan α
del catálogo y el talón (DF-20, [axes.md](axes.md)). Eje w (mayor): My = Fy·min(SwA, SwB, SwC);
Mcr F10-4 con Cb ≤ 1,5 y |βw| de la columna `βw` de la hoja L del catálogo (mm, DF-12) con signo
positivo cuando el ala corta está comprimida; el ala comprimida sale del signo de Mw y define Sc (SwC punta del ala
larga, SwA punta del ala corta). En ángulos iguales βw = 0 y el ala es indistinta.
Eje z (menor): Y y LLB, sin LTB (Nota de F10); con las punteras comprimidas se toma el
menor LLB de ambas alas (SzC y SzA).

Puntos del catálogo: A = punta del ala corta, B = talón, C = punta del ala larga.

## Entrada

- `Mx_3`, `My_2` por combinación (kN·m), con signo. Una combinación con más de una demanda
  (P, Mx_3, My_2) se calcula por componente y se combina en el chequeo de interacción
  del Capítulo H ([chapter-h.md](chapter-h.md)); un FAIL conocido se informa siempre (DF-4).
- `custom_section` `I_BUILT_UP` para las I armadas soldadas (`flange_plus2`, `flange_minus2`).
- `lengths` del miembro, de las que sale Lb (DF-13; obligatorias cuando aplica el pandeo
  lateral-torsional), y `flexure`: `Cb` (1,0 si no se indica: límite inferior de F1-1, DF-2) y
  `tension_flange_holes` (obligatorio en I y canales sobre el eje x_3, F13.1) con
  `Afn` (mm²) cuando hay agujeros; F13.1 requiere además `material.Fu` (DF-3).
- Ángulos: `heel` (`axis_2`, `axis_3`; en ángulos dobles solo `axis_2`) y, en ángulos simples,
  `flexure.lateral_torsional_restraint`. Sin el dato necesario: INCOMPLETO con el campo que falta.

## Verificación con cálculos independientes

`tests/oracles/chapter_f.py` recalcula en Decimal desde el texto de la norma, leyendo
el Excel con sus propias escalas, sin importar el paquete. El programa coincide en todos
los estados límite con tolerancia relativa 1e-9. Mn en kN·m:

| Caso | Perfil y datos | Fy | Mn por estado límite | Gobierna | φb·Mn |
| --- | --- | --- | --- | --- | --- |
| W-F2-yielding | W18X50, eje x_3, Lb=1500 | 345 | Y 572.70 | Y | 515.430 |
| W-F2-inelastic-LTB | W18X50, eje x_3, Lb=4000 | 345 | Y 572.70, LTB 428.07 | LTB | 385.264 |
| W-F2-elastic-LTB-Cb | W18X50, eje x_3, Lb=12000, Cb=1.3 | 345 | Y 572.70, LTB 140.35 | LTB | 126.317 |
| W-F3-FLB | W14X90, eje x_3, Lb=3000 | 345 | FLB 864.02 | FLB | 777.617 |
| W-F3-LTB | W14X90, eje x_3, Lb=8000, Cb=1.14 | 345 | FLB 864.02, LTB 847.16 | LTB | 762.447 |
| W-F13-holes | W14X90, eje x_3, Lb=3000, Afn=4500 | 345 | FLB 864.02, TFR 715.35 | TFR | 643.818 |
| W-F6-minor | W14X90, eje y_2 | 345 | Y 427.80, FLB 411.59 | FLB | 370.435 |
| C-F2-inelastic-LTB | C15X50, eje x_3, Lb=2000 | 345 | Y 386.40, LTB 333.35 | LTB | 300.012 |
| C-F2-elastic-LTB | C15X50, eje x_3, Lb=6000 | 345 | Y 386.40, LTB 151.93 | LTB | 136.739 |
| C-F6-minor | C15X50, eje y_2 | 345 | Y 34.11 | Y | 30.702 |
| RHSS-F7-LTB | PTE100X50X3MM, eje x_3, Lb=3000 | 345 | Y 8.63, LTB 8.50 | LTB | 7.651 |
| RHSS-F7-noncompact | PTE120X60X2MM, eje x_3, Lb=500 | 345 | Y 8.70, FLB 8.16, WLB 8.64 | FLB | 7.342 |
| RHSS-F7-minor | PTE120X60X2MM, eje y_2 | 345 | Y 5.40, FLB 3.57 | FLB | 3.216 |
| RHSS-F7-3-slender-flange | PTE100X40X1.5MM, eje y_2 | 345 | Y 2.16, FLB 1.33 | FLB | 1.193 |
| CHSS-F8-noncompact | PTER4"X3.00MM, eje x_3 | 345 | Y 11.97, LB 11.90 | LB | 10.713 |
| CHSS-F8-compact | PTER2"X4.00MM, eje x_3 | 345 | Y 4.10 | Y | 3.690 |
| BAR-F11-LTB | barra 100x20, eje x_3, Lb=1500 | 250 | Y 12.50, LTB 11.60 | LTB | 10.437 |
| BAR-F11-minor | barra 100x20, eje y_2, Lb=1500 | 250 | Y 2.50 | Y | 2.250 |
| ROUND-F11 | redondo D=50, eje x_3 | 250 | Y 4.91 | Y | 4.418 |
| 2L-F9-web-tension | 2L4X4X1/4, eje x_3, Lb=2000, alas verticales en tracción | 345 | Y 18.66, LTB 18.54, FLB 40.37 | LTB | 16.690 |
| 2L-F9-web-compression | 2L4X4X1/4, eje x_3, Lb=2000, alas verticales en compresión | 345 | Y 17.49, LTB 13.37, WLB 14.96 | LTB | 12.034 |
| 2L-F9-LLBB-tension | 2L6X4X3/8LLBB, eje x_3, Lb=3000, alas verticales en tracción | 345 | Y 59.62, LTB 56.75 | LTB | 51.074 |
| 2L-F9-SLBB-compression | 2L6X4X3/8SLBB, eje x_3, Lb=3000, alas verticales en compresión | 345 | Y 26.86, LTB 25.53 | LTB | 22.978 |
| 2L-F9-elastic-LTB | 2L4X4X1/4, eje x_3, Lb=9000, alas verticales en tracción | 345 | Y 18.66, LTB 15.03, FLB 40.37 | LTB | 13.525 |
| L-F10-geom-none-toe-comp | L4X4X1/4, eje x_3, Lb=2000, sin restricción, punta comprimida | 345 | Y 8.67, LTB 5.27, LLB 5.93 | LTB | 4.739 |
| L-F10-geom-none-toe-tens | L4X4X1/4, eje x_3, Lb=2000, sin restricción, punta traccionada | 345 | Y 8.67, LTB 6.94, LLB 16.15 | LTB | 6.243 |
| L-F10-geom-at-max | L4X4X1/4, eje y_2, Lb=2000, Cb=1.2, restricción en Mmáx, punta comprimida | 345 | Y 8.67, LTB 6.98, LLB 7.41 | LTB | 6.279 |
| L-F10-geom-continuous-unequal | L6X4X3/8, eje x_3, restricción continua, punta comprimida | 345 | Y 28.04, LLB 24.12 | LLB | 21.710 |
| L-F10-w-short-comp | L6X4X3/8, eje w, Lb=2000, ala corta comprimida | 345 | Y 32.76, LTB 28.76 | LTB | 25.881 |
| L-F10-w-long-comp | L6X4X3/8, eje w, Lb=2000, ala larga comprimida | 345 | Y 32.76, LTB 22.33, LLB 28.18 | LTB | 20.093 |
| L-F10-w-equal-Cb-capped | L4X4X1/4, eje w, Lb=3000, Cb=1.8 (se usa 1.5) | 345 | Y 14.90, LTB 10.38, LLB 12.74 | LTB | 9.346 |
| L-F10-z-toes-comp | L6X4X3/8, eje z, punteras comprimidas | 345 | Y 11.13, LLB 20.35 | Y | 10.014 |
| BUI-F2-compact | I 600, tw 10, alas 250x20, Lb=4000 | 345 | Y 1270.98, LTB 1107.02 | LTB | 996.317 |
| BUI-F3-noncompact-flange | I 600, tw 10, alas 300x14, Lb=3000 | 345 | FLB 1069.32, LTB 1116.61 | FLB | 962.387 |
| BUI-F4-wide-flange-compressed | I 900, tw 8, 350x22 / 250x16, Mx_3 > 0 (ala +2 comprimida), Lb=3000 | 345 | CFY 2145.10, LTB 2109.89, TFY 2145.10 | LTB | 1898.898 |
| BUI-F4-narrow-flange-compressed-J0 | la misma, Mx_3 < 0 (ala −2 comprimida) (Iyc/Iy ≤ 0,23), Lb=9000 | 345 | CFY 1646.86, LTB 450.00 | LTB | 404.998 |
| BUI-F4-noncompact-web-and-flange | I 1000, tw 9, alas 300x16, Lb=4000 | 345 | CFY 2253.39, LTB 1937.45, FLB 2230.26 | LTB | 1743.707 |
| BUI-F4-14-slender-flange | I 1000, tw 9, 500x12 / 300x25, Mx_3 > 0 (ala +2 comprimida), Lb=2500, Cb=1.2 | 345 | CFY 2702.09, FLB 1182.71 | FLB | 1064.441 |
| BUI-F4-9b-16b-noncompact-web | I 1100, tw 7, 350x22 / 250x18, Mx_3 > 0 (ala +2 comprimida), Lb=3000 | 345 | CFY 2826.17, LTB 2773.34, TFY 1998.54 | TFY | 1798.682 |
| BUI-F5-noncompact-flange | I 1200, tw 8, alas 400x20, Lb=6000 | 345 | CFY 3779.07, LTB 3242.07, FLB 3641.77 | LTB | 2917.861 |
| BUI-F5-elastic-LTB | la misma, Lb=16000 | 345 | CFY 3779.07, LTB 943.70, FLB 3641.77 | LTB | 849.326 |
| BUI-F5-tension-flange-yielding | I 1400, tw 8, 450x25 / 300x16, Mx_3 > 0 (ala +2 comprimida), Lb=2000 | 345 | CFY 4650.15, TFY 2043.87 | TFY | 1839.483 |
| BUI-F6-unequal-flanges | I 900, tw 8, 350x22 / 300x10, eje y_2 | 345 | Y 314.86, FLB 246.16 | FLB | 221.544 |

## Decisiones

- **DF-1** Etapa 1 sin ángulos (indicación del usuario); F9 y F10 implementados en la etapa 2.
- **DF-2** Cb es dato del usuario; si no se indica, 1,0, límite inferior de F1-1 en
  miembros doblemente simétricos (indicación del usuario). La memoria lo señala.
- **DF-3** La presencia de agujeros en el ala traccionada (F13.1) debe declararse en I
  y canales sobre el eje x_3; sin declaración, INCOMPLETO (indicación del usuario). Afg = bf·tf.
- **DF-4** Combinaciones con más de una demanda: cada componente se calcula por separado;
  desde la incorporación del Capítulo H se combinan con H1/H4, y los ángulos simples con H2.
- **DF-5** F7-3: Se referido al ala comprimida con el eje neutro desplazado
  (Commentary F7): se descuenta (b − be)·t del ala comprimida a (H − t)/2 del
  centroide, incluida la inercia propia de la franja; c = H/2 + desplazamiento.
- **DF-6** PTE rectangular: el pandeo lateral-torsional se evalúa solo en el eje mayor
  de secciones no cuadradas (Nota de F7.4 y forma de F7-8 a F7-11 con ry y Sx).
- **DF-7** Catálogo: la hoja PTE_RED almacena Sx y Sy en mm³ (las demás hojas en
  10³ mm³); el cargador lo trata explícitamente y una prueba exige S = I/c.
- **DF-8** Ángulo simple: se calculan ambos ejes geométricos y principales
  (indicación del usuario). Desde 2026-11-06 la entrada es solo `Mx_3`, `My_2`: F10.2(2) donde se admite y, si no, los
  ejes principales (DF-20).
- **DF-9** La parte comprimida se deduce del signo del momento con la convención de ETABS y de la orientación declarada
  (`heel`) (indicación del usuario, 2026-11-06). Sustituye a los campos `web_legs`, `toe` y `leg_in_compression`, que
  se retiraron.
- **DF-10** Ángulo doble: alas verticales según el rótulo LLBB/SLBB, no según las
  columnas d/b del catálogo; desigual sin sufijo → INCOMPLETO. J = 2·J del componente.
  La flexión respecto del eje y (de simetría) no está en F9 → INCOMPLETO.
- **DF-11** F10.2(2)(i) sin restricción: el factor 0,80 reduce solo My del pandeo
  lateral-torsional (F10-2/F10-3) y Sc del pandeo local del ala (F10.3); la fluencia F10-1
  usa My sin reducir (indicación del usuario, 2026-10-30). Coincide con el ejemplo F.11A de
  los AISC Design Examples v16.0 (Mn = 1,5·Fy·Sx = 6,44 kip-ft).
- **DF-14** F7.4 se revisa respecto del eje mayor de la sección, sea x o y: en un cajón con B > H ese eje es y, con Sy, Zy y rx. El pandeo lateral-torsional no se revisaba respecto de y; ningún resultado de perfiles del catálogo cambió.
- **DF-13** Lb no es un dato (indicación del usuario, 2026-10-31): flexión respecto de x, Lb = min(Ly_2, Lz_1); respecto de y, Lb = min(Lx_3, Lz_1), con las
  longitudes de la condición del case. En ángulos simples, el eje principal w sigue la regla de x y z la de y.
- **DF-15** F4.4 (indicación del usuario, 2026-11-03): en F4-16b, λ = h/tw como imprime la Specification, aunque
  el Commentary y la edición 2016 usan hc/tw; la rama (F4-16a o F4-16b) sigue hc/tw, también como está impreso.
  Solo cambia algo en I de alas distintas.
- **DF-16** J = 0 cuando Iyc/Iy ≤ 0,23 (indicación del usuario, 2026-11-03): la Specification lo escribe junto a F4-5;
  se aplica también a Lr (F4-8), que el Commentary deriva de F4-5 con Fcr = FL, para que Mn sea continuo en Lb = Lr.
  **DF-16b** El tope «Mp = FyZx ≤ 1,6FySx» de F4-9 y F4-16 usa Sxc en Rpc y Sxt en Rpt (Mp/Myc ≤ 1,6 y
  Mp/Myt ≤ 1,6, Commentary F4).
- **DF-17** I armada (indicación del usuario, 2026-11-03): se ingresa por placas; las propiedades salen de ellas sin
  radios de soldadura. J = Σb·t³/3 (alas con su ancho, alma con h); Cw = ho²·Iy,+2·Iy,−2/(Iy,+2 + Iy,−2) y centro
  de corte a ho·Iy,−2/(Iy,+2 + Iy,−2) del centroide del ala de la cara +2, con las inercias de las alas (pared delgada,
  Commentary F4 y Design Guide 9). No es norma; la memoria lo indica.
- **DF-18** Ala comprimida (indicación del usuario, 2026-11-06): `Mx_3 > 0` comprime el ala de la cara +2. Sustituye al
  campo `flexure.compression_flange` (2026-11-03), que se retiró.
- **DF-20** Ángulo simple en ejes principales (indicación del usuario, 2026-11-06): `Mw` y `Mz` dejan de ser datos. El
  vector momento m = (−M2, M3) se proyecta en w = (−s2·sin α, −s3·cos α) y z = (−s2·cos α, s3·sin α) (componentes 2, 3;
  talón en (s2, s3)) con tan α del catálogo; los sentidos en A, B y C salen de (m·u)·p·(e1 × u). Un componente menor que
  10⁻¹² de la suma de los momentos es redondeo y no genera chequeo. El oráculo determina el cuadrante de w y z con el producto
  de inercia de las alas; los Ejemplos E.14B y F.11C se reproducen con esta entrada.
- **DF-19** F6 con alas distintas (indicación del usuario, 2026-11-03): se clasifican las dos alas y FLB usa el mayor
  b/tf con Sy y Zy de la sección; F6 no dice qué ala usar.
- **DF-12** |βw| (F10-4) se lee de la columna `βw` de la hoja L del catálogo, en mm (indicación del usuario,
  2026-10-31): sustituye al dato `flexure.beta_w`, que se retiró. Positivo con el ala corta comprimida y negativo con la
  larga (Commentary F10); 0 en alas iguales. Se contrastó con la Tabla C-F10.1 (promedios, diferencia máxima 1,8 %) y con
  la integral de la definición del Commentary sin filetes (máxima 3,1 %). El catálogo varía con el espesor; la tabla no.

## Incidencias del catálogo detectadas

- **IPE 80:** Iy = 0,8489·10⁶ mm⁴ contradice ry = 10,5 mm y Sy (valor ≈ 10 veces
  mayor). El programa marca el perfil como incoherente y sus comprobaciones quedan
  INCOMPLETO hasta que se corrija la fila del Excel.
- **IPE 100–600, HEA/HEB 100–200:** sin Sx, Zx, Sy, Zy, J, Cw ni ho en el catálogo;
  su flexión (y el pandeo torsional en compresión) queda INCOMPLETO por falta de datos.

## Limitaciones

- Ángulos dobles respecto de y (eje 2): no cubiertos.

- Lb y Cb son datos del usuario; se supone que los apoyos restringen la rotación
  respecto del eje longitudinal (F1(b)). F1(d) (miembros con un eje de simetría en
  curvatura doble) no se evalúa: Cb es dato del usuario también para ángulos dobles.
- Cada chequeo de flexión es respecto de un eje; la flexión biaxial y la carga axial se
  combinan en el chequeo de interacción (Capítulo H). El cortante es el Capítulo G.
- F13.2 se revisa sin rigidizadores transversales (F13-4); F13-3 (a/h ≤ 1,5), F13.3 (cubreplacas) y F13.4 no
  se cubren. rt para alas con canal o cubreplaca (F4-11(ii)) tampoco: la entrada no admite esas secciones.
- F1(d): en I de simetría simple con doble curvatura, el pandeo lateral-torsional se revisa con cada ala dando
  una combinación con cada signo de `Mx_3`; el programa no las genera.
