# Capítulo F — alcance implementado (etapas 1 y 2)

Fuente: ANSI/AISC 360-22, `a360-22w.pdf` (Tabla B4.1b pp. 16.1-22/23; F1–F13
pp. 16.1-50 a 16.1-73) y errata E25-02 (enero de 2025), que renumera las
ecuaciones de pandeo lateral-torsional de F7 a F7-8, F7-9, F7-10 y F7-11. Solo
LRFD: φb = 0,90 (F1(a)). Momentos en kN·m.

## Matriz de familias y secciones

| Familia | Eje x | Eje y | Estados límite (Tabla de Nota F1.1) |
| --- | --- | --- | --- |
| W / IPE / HEA / HEB | F2 (ala compacta) o F3 (ala no compacta/esbelta); F13.1 | F6 | Y, LTB, FLB, TFR / Y, FLB |
| Canal | F2 (solo compacto); F13.1 | F6 | Y, LTB, FLB, TFR / Y, FLB |
| PTE rectangular | F7 | F7 | Y, FLB, WLB, LTB (LTB no aplica en eje menor ni en sección cuadrada, Nota de F7.4) |
| PTE redondo | F8 (D/t < 0,45E/Fy) | F8 | Y, LB |
| Barra rectangular / redonda | F11 | F11 | Y, LTB (solo barra rectangular en su eje mayor) |
| Ángulo doble (F9) | F9 (plano de simetría) | — (no cubierto, INCOMPLETO) | Y, LTB, FLB, WLB |
| Ángulo simple (F10) | F10.2(2) ejes geométricos (x, y) | — | Y, LTB, LLB |
| Ángulo simple (F10), ejes principales | `Mw`: F10-4 | `Mz`: Y y LLB | Y, LTB, LLB / Y, LLB |

Bloqueos con motivo (INCOMPLETO): alma no compacta o esbelta en I (F4/F5), canal
con ala no compacta (sin sección aplicable en F), alma esbelta en PTE (F7-7) y
D/t ≥ 0,45E/Fy en PTE redondo.

Cada estado límite de la sección elegida figura en el resultado: calculado o con el
motivo por el que no aplica (p. ej. Lb ≤ Lp, ala compacta). Gobierna el menor Mn.

## Ángulos (etapa 2)

**Ángulo doble (F9), flexión respecto de x.** El dato `angle_flexure.web_legs`
(`tension` o `compression`) indica si las alas verticales (en el plano de simetría)
están traccionadas en su punta. Las alas verticales se identifican por el rótulo:
LLBB → alas largas verticales, SLBB → alas cortas; en ángulos iguales, indistinto
(DF-10). J = 2·J del ángulo componente, leído del catálogo. Y: F9-2 (alas
verticales en tracción) o F9-5 (en compresión); LTB: F9-6/F9-7 con Lp F9-8 y Lr F9-9,
o F9.2(b)(2) con F10-2/F10-3; Mcr F9-10 con B de F9-11/F9-12. FLB (F9.3) con
Sc = Ix/ȳ al dorso de las alas horizontales; WLB (F9.4) con Sx; ambos mediante
F10-6/F10-7.

**Ángulo simple (F10), ejes geométricos (`Mux`, `Muy`).** Requiere
`flexure.lateral_torsional_restraint`: `none`, `at_max_moment` o `continuous`, y
`angle_flexure.toe` (`compression`/`tension`: estado de la punta del ala
perpendicular al eje). Ángulos desiguales solo con restricción continua (F10.2(2)
remite a ejes principales en los demás casos); F10.2(2) no se usa con compresión
axial. Orientación del catálogo: ala larga paralela a y (eje x → ala perpendicular
larga; eje y → ala corta). Sin restricción: My y Sc multiplicados por 0,80
solo en LTB y LLB (F10.2(2)(i), DF-11); restricción en el punto de máximo momento: Mcr × 1,25
(F10.2(2)(ii)). Mcr con F10-5a/F10-5b según la punta comprimida o traccionada.

**Ángulo simple, ejes principales.** `Mw` (eje mayor): My = Fy·min(SwA, SwB, SwC);
Mcr F10-4 con Cb ≤ 1,5 y βw dato del usuario (`flexure.beta_w`, mm, DF-12) con signo
positivo cuando el ala corta está comprimida; el ala comprimida se declara en
`angle_flexure.leg_in_compression` (`long`/`short`) y define Sc (SwC punta del ala
larga, SwA punta del ala corta). En ángulos iguales βw = 0 y el ala es indistinta.
`Mz` (eje menor): Y y LLB, sin LTB (Nota de F10); con `toe = compression` se toma el
menor LLB de ambas alas (SzC y SzA).

Puntos del catálogo: A = punta del ala corta, B = talón, C = punta del ala larga.

## Entrada

- `Mux`, `Muy` por combinación (kN·m). Una combinación con más de una demanda
  (Pu, Mux, Muy) se calcula por componente y se combina en el chequeo de interacción
  del Capítulo H ([chapter-h.md](chapter-h.md)); un FAIL conocido se informa siempre (DF-4).
- `flexure` del miembro: `Lb` (mm, obligatorio cuando aplica el pandeo
  lateral-torsional), `Cb` (1,0 si no se indica: límite inferior de F1-1, DF-2) y
  `tension_flange_holes` (obligatorio en I y canales sobre el eje x, F13.1) con
  `Afn` (mm²) cuando hay agujeros; F13.1 requiere además `material.Fu` (DF-3).
- Ángulos: `Mw`, `Mz` (kN·m, solo ángulos simples), `flexure.lateral_torsional_restraint`,
  `flexure.beta_w` y `angle_flexure` (`web_legs`, `toe`, `leg_in_compression`), todos
  por combinación cuando dependen del signo del momento. Sin el dato necesario: INCOMPLETO
  con el campo que falta.

## Verificación con cálculos independientes

`tests/oracles/chapter_f.py` recalcula en Decimal desde el texto de la norma, leyendo
el Excel con sus propias escalas, sin importar el paquete. El programa coincide en todos
los estados límite con tolerancia relativa 1e-9. Mn en kN·m:

| Caso | Perfil y datos | Fy | Mn por estado límite | Gobierna | φb·Mn |
| --- | --- | --- | --- | --- | --- |
| W-F2-yielding | W18X50, eje x, Lb=1500 | 345 | Y 572.70 | Y | 515.430 |
| W-F2-inelastic-LTB | W18X50, eje x, Lb=4000 | 345 | Y 572.70, LTB 428.07 | LTB | 385.264 |
| W-F2-elastic-LTB-Cb | W18X50, eje x, Lb=12000, Cb=1.3 | 345 | Y 572.70, LTB 140.35 | LTB | 126.317 |
| W-F3-FLB | W14X90, eje x, Lb=3000 | 345 | FLB 864.02 | FLB | 777.617 |
| W-F3-LTB | W14X90, eje x, Lb=8000, Cb=1.14 | 345 | FLB 864.02, LTB 847.16 | LTB | 762.447 |
| W-F13-holes | W14X90, eje x, Lb=3000, Afn=4500 | 345 | FLB 864.02, TFR 715.35 | TFR | 643.818 |
| W-F6-minor | W14X90, eje y | 345 | Y 427.80, FLB 411.59 | FLB | 370.435 |
| C-F2-inelastic-LTB | C15X50, eje x, Lb=2000 | 345 | Y 386.40, LTB 333.35 | LTB | 300.012 |
| C-F2-elastic-LTB | C15X50, eje x, Lb=6000 | 345 | Y 386.40, LTB 151.93 | LTB | 136.739 |
| C-F6-minor | C15X50, eje y | 345 | Y 34.11 | Y | 30.702 |
| RHSS-F7-LTB | PTE100X50X3MM, eje x, Lb=3000 | 345 | Y 8.63, LTB 8.50 | LTB | 7.651 |
| RHSS-F7-noncompact | PTE120X60X2MM, eje x, Lb=500 | 345 | Y 8.70, FLB 8.16, WLB 8.64 | FLB | 7.342 |
| RHSS-F7-minor | PTE120X60X2MM, eje y | 345 | Y 5.40, FLB 3.57 | FLB | 3.216 |
| RHSS-F7-3-slender-flange | PTE100X40X1.5MM, eje y | 345 | Y 2.16, FLB 1.33 | FLB | 1.193 |
| CHSS-F8-noncompact | PTER4"X3.00MM, eje x | 345 | Y 11.97, LB 11.90 | LB | 10.713 |
| CHSS-F8-compact | PTER2"X4.00MM, eje x | 345 | Y 4.10 | Y | 3.690 |
| BAR-F11-LTB | barra 100x20, eje x, Lb=1500 | 250 | Y 12.50, LTB 11.60 | LTB | 10.437 |
| BAR-F11-minor | barra 100x20, eje y, Lb=1500 | 250 | Y 2.50 | Y | 2.250 |
| ROUND-F11 | redondo D=50, eje x | 250 | Y 4.91 | Y | 4.418 |
| 2L-F9-web-tension | 2L4X4X1/4, eje x, Lb=2000, alas verticales en tracción | 345 | Y 18.66, LTB 18.54, FLB 40.37 | LTB | 16.690 |
| 2L-F9-web-compression | 2L4X4X1/4, eje x, Lb=2000, alas verticales en compresión | 345 | Y 17.49, LTB 13.37, WLB 14.96 | LTB | 12.034 |
| 2L-F9-LLBB-tension | 2L6X4X3/8LLBB, eje x, Lb=3000, alas verticales en tracción | 345 | Y 59.62, LTB 56.75 | LTB | 51.074 |
| 2L-F9-SLBB-compression | 2L6X4X3/8SLBB, eje x, Lb=3000, alas verticales en compresión | 345 | Y 26.86, LTB 25.53 | LTB | 22.978 |
| 2L-F9-elastic-LTB | 2L4X4X1/4, eje x, Lb=9000, alas verticales en tracción | 345 | Y 18.66, LTB 15.03, FLB 40.37 | LTB | 13.525 |
| L-F10-geom-none-toe-comp | L4X4X1/4, eje x, Lb=2000, sin restricción, punta comprimida | 345 | Y 8.67, LTB 5.27, LLB 5.93 | LTB | 4.739 |
| L-F10-geom-none-toe-tens | L4X4X1/4, eje x, Lb=2000, sin restricción, punta traccionada | 345 | Y 8.67, LTB 6.94, LLB 16.15 | LTB | 6.243 |
| L-F10-geom-at-max | L4X4X1/4, eje y, Lb=2000, Cb=1.2, restricción en Mmáx, punta comprimida | 345 | Y 8.67, LTB 6.98, LLB 7.41 | LTB | 6.279 |
| L-F10-geom-continuous-unequal | L6X4X3/8, eje x, restricción continua, punta comprimida | 345 | Y 28.04, LLB 24.12 | LLB | 21.710 |
| L-F10-w-short-comp | L6X4X3/8, eje w, Lb=2000, ala corta comprimida, βw=79.8 | 345 | Y 32.76, LTB 28.75 | LTB | 25.876 |
| L-F10-w-long-comp | L6X4X3/8, eje w, Lb=2000, ala larga comprimida, βw=79.8 | 345 | Y 32.76, LTB 22.33, LLB 28.18 | LTB | 20.101 |
| L-F10-w-equal-Cb-capped | L4X4X1/4, eje w, Lb=3000, Cb=1.8 (se usa 1.5) | 345 | Y 14.90, LTB 10.38, LLB 12.74 | LTB | 9.346 |
| L-F10-z-toes-comp | L6X4X3/8, eje z, punteras comprimidas | 345 | Y 11.13, LLB 20.35 | Y | 10.014 |

## Decisiones

- **DF-1** Etapa 1 sin ángulos (indicación del usuario); F9 y F10 implementados en la etapa 2.
- **DF-2** Cb es dato del usuario; si no se indica, 1,0, límite inferior de F1-1 en
  miembros doblemente simétricos (indicación del usuario). La memoria lo señala.
- **DF-3** La presencia de agujeros en el ala traccionada (F13.1) debe declararse en I
  y canales sobre el eje x; sin declaración, INCOMPLETO (indicación del usuario). Afg = bf·tf.
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
  (indicación del usuario); `Mux`/`Muy` usan F10.2(2) y `Mw`/`Mz` los ejes principales.
- **DF-9** El dato de qué parte está comprimida (`web_legs`, `toe`,
  `leg_in_compression`) es un campo explícito por combinación (indicación del
  usuario); no se deduce del signo del momento.
- **DF-10** Ángulo doble: alas verticales según el rótulo LLBB/SLBB, no según las
  columnas d/b del catálogo; desigual sin sufijo → INCOMPLETO. J = 2·J del componente.
  La flexión respecto del eje y (de simetría) no está en F9 → INCOMPLETO.
- **DF-11** F10.2(2)(i) sin restricción: el factor 0,80 reduce solo My del pandeo
  lateral-torsional (F10-2/F10-3) y Sc del pandeo local del ala (F10.3); la fluencia F10-1
  usa My sin reducir (indicación del usuario, 2026-10-30). Coincide con el ejemplo F.11A de
  los AISC Design Examples v16.0 (Mn = 1,5·Fy·Sx = 6,44 kip-ft).
- **DF-12** βw (F10-4) es dato del usuario en mm (indicación del usuario; Tabla
  C-F10.1 del Commentary da valores de referencia), positivo con el ala corta comprimida.

## Incidencias del catálogo detectadas

- **IPE 80:** Iy = 0,8489·10⁶ mm⁴ contradice ry = 10,5 mm y Sy (valor ≈ 10 veces
  mayor). El programa marca el perfil como incoherente y sus comprobaciones quedan
  INCOMPLETO hasta que se corrija la fila del Excel.
- **IPE 100–600, HEA/HEB 100–200:** sin Sx, Zx, Sy, Zy, J, Cw ni ho en el catálogo;
  su flexión (y el pandeo torsional en compresión) queda INCOMPLETO por falta de datos.

## Limitaciones

- Ángulos: no se combinan Mux y Muy en ejes geométricos con otras demandas (H2 exige ejes
  principales, DH-7); no se cubren ángulos dobles respecto de y.

- Lb y Cb son datos del usuario; se supone que los apoyos restringen la rotación
  respecto del eje longitudinal (F1(b)). F1(d) (miembros con un eje de simetría en
  curvatura doble) no se evalúa: Cb es dato del usuario también para ángulos dobles.
- Cada chequeo de flexión es respecto de un eje; la flexión biaxial y la carga axial se
  combinan en el chequeo de interacción (Capítulo H). El cortante es el Capítulo G.
- F13.2 a F13.4 (proporciones de miembros armados y cubreplacas) no aplican a los
  perfiles laminados del catálogo.
