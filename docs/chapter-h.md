# Capítulo H — alcance implementado (etapas 1 y 2)

Fuente: ANSI/AISC 360-22, `a360-22w.pdf` (H1–H4, pp. 16.1-82 a 16.1-88) y errata de
septiembre 2026 (unidades de Lb en H1-2: in. (mm)). Solo LRFD (α = 1,0 en H1-2).

## Alcance

| Situación | Disposición |
| --- | --- |
| Compresión y flexión (x, y o ambas) | H1.1: H1-1a si Pr/Pc ≥ 0,2; si no, H1-1b |
| Tracción y flexión | H1.2: mismas ecuaciones con Pc = φt·Pn (Capítulo D) |
| Flexión biaxial sin carga axial | H1-1b con Pr = 0 |
| Tracción y flexión respecto de x en I o canal con agujeros en el ala traccionada | H4-1, además de H1 |
| Ángulo simple con fuerza axial y momento, o con momentos que F10 lleva a los ejes principales | H2-1 en los puntos A, B y C con Mw y Mz del giro de `Mx_3`, `My_2` (F10, DF-20) |
| Torsión (H3) y alternativa H1.3 | no implementadas |

El chequeo `interaction` aparece cuando la combinación tiene dos o más de los chequeos axial y de flexión (`flexure_x_3`,
`flexure_y_2` o, en ángulos simples, `flexure_w` y `flexure_z`). Usa las resistencias de diseño de los chequeos de los Capítulos D, E y F sin
recalcularlas (Mcx incluye F13.1 cuando hay agujeros). Si falta alguna, queda
INCOMPLETO con el chequeo que falta; un FAIL de un componente siempre se informa.
Gobierna el mayor valor entre H1 y H4, o entre los puntos A, B y C en H2.

## H2 en ángulos simples

En cada punto: |± Pr/Pc ± Mrw/Mcw ± Mrz/Mcz| ≤ 1, con compresión positiva y tracción negativa.
A = punta del ala corta, B = talón, C = punta del ala larga. Sentido de la tensión de flexión:

| Punto | Mw, punta del ala larga comprimida | Mw, punta del ala corta comprimida | Mz, punteras comprimidas | Mz, punteras traccionadas |
| --- | --- | --- | --- | --- |
| A | tracción | compresión | compresión | tracción |
| B (alas desiguales) | tracción | compresión | tracción | compresión |
| B (alas iguales) | sin tensión | sin tensión | tracción | compresión |
| C | compresión | tracción | compresión | tracción |

El sentido en cada punto sale del signo de `Mx_3` y `My_2`, del talón (`heel`) y de tan α: el vector momento se proyecta
en w y z y cada punto toma el signo de su esfuerzo (DF-9, DF-20 de [chapter-f.md](chapter-f.md), [axes.md](axes.md)).
En alas iguales, w es el eje de simetría y el talón no tiene esfuerzo por Mw.

## Entrada

- Las demandas `P` (> 0 tracción), `Mx_3`, `My_2` de la combinación y, en ángulos, `heel`.
- `flexure.tension_cb_amplification` (por defecto `false`): H1.2 permite multiplicar Cb
  por √(1 + Pr/Pey), Pey = π²EIy/Lb² (H1-2), en miembros doblemente simétricos (W,
  PTE, barras). Si se pide en un perfil que no lo es, se informa y se usa Cb sin amplificar.

## Verificación con cálculos independientes

`tests/oracles/chapter_h.py` escribe H1-1a/H1-1b, H1-2, H4-1 y H2-1 y toma Pc y Mc de
los oráculos D, E y F. Coincidencia con tolerancia relativa 1e-9:

| Caso | Perfil y demandas (kN, kN·m) | Pc | Mcx | Mcy | H1 | Valor |
| --- | --- | --- | --- | --- | --- | --- |
| W-H1-1a | W14X90, P=−1500, Mx_3 = 200, My_2 = 50 | 4650.81 | 777.62 | 370.43 | H1-1a 0.6711 | 0.6711 |
| W-H1-1b | W14X90, P=−300, Mx_3 = 200, My_2 = 50 | 4650.81 | 777.62 | 370.43 | H1-1b 0.4244 | 0.4244 |
| W-biaxial-no-axial | W14X90, Mx_3 = 300, My_2 = 100 | – | 777.62 | 370.43 | H1-1b 0.6557 | 0.6557 |
| W-H1.2-tension | W14X90, P=800, Mx_3 = 400, My_2 = 50, Lb = 8000, Cb = 1.14 | 4556.25 | 762.45 | 370.43 | H1-1b 0.7474 | 0.7474 |
| W-H1.2-Cb-amplified | igual, Cb × 1.0825 (H1-2) | 4556.25 | 777.62 | 370.43 | H1-1b 0.7372 | 0.7372 |
| W-H4-holes | W14X90, P=1500, Mx_3 = 300, Afn = 4500 | 4556.25 | 643.82 | – | H1-1a 0.7434; H4 0.7952 | 0.7952 |
| C-H1-1a | C15X50, P=−800, Mx_3 = 100 | 794.30 | 300.01 | – | H1-1a 1.3035 | 1.3035 (FAIL) |
| RHSS-H1-1a | PTE100X100X4MM, P=−200, Mx_3 = 5, My_2 = 3 | 281.67 | 15.52 | 15.52 | H1-1a 1.1681 | 1.1681 (FAIL) |
| 2L-H1-1b | 2L4X4X1/4, P=−40, Mx_3 = 5 | 483.03 | 16.69 | – | H1-1b 0.3410 | 0.3410 |

H2 en ángulos simples. Cada caso indica Mw y Mz con su parte comprimida; el oráculo obtiene con un giro inverso la entrada
`Mx_3`, `My_2` del programa para el talón del caso (el cuadrante de w y z sale del producto de inercia de las alas) y el
signo en cada punto de sus coordenadas en ejes principales (x, y, tan α del catálogo). Fy = 345 MPa salvo indicación:

| Caso | Perfil y demandas (kN, kN·m) | Pc | Mcw | Mcz | A | B | C | Valor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L-H2-comp-long-toe | L6X4X3/8, P=−100, Mw = 5 (ala larga), Mz = 2 (punteras en tracción), L = Lb = 2000 | 385.95 | 20.09 | 10.01 | 0.1895 | 0.2100 | 0.3082 | 0.3082 (C) |
| L-H2-comp-short-toe | igual, ala corta y punteras comprimidas | 385.95 | 25.88 | 10.01 | 0.6520 | 0.2526 | 0.2656 | 0.6520 (A) |
| L-H2-comp-axial-Mw | L8X4X1/2, P=−300, Mw = 20 (ala larga), L = Lb = 1524 | 749.78 | 42.34 | – | 0.0722 | 0.0722 | 0.8724 | 0.8724 (C) |
| L-H2-comp-heel-governs | L8X4X1/2, P=−150, Mz = 5 (punteras en tracción), L = 1524 | 749.78 | – | 13.88 | 0.1602 | 0.5603 | 0.1602 | 0.5603 (B) |
| L-H2-comp-FAIL | L4X4X1/4, Fy = 450, P=−120, Mz = 4 (punteras comprimidas), L = 2000 | 188.21 | – | 6.35 | 1.2678 | 0.0074 | 1.2678 | 1.2678 (FAIL) |
| L-H2-tension | L6X4X3/8, P=300, Mw = 8 (ala corta), Mz = 3 (punteras en tracción), Lb = 2000 | 545.06 | 25.88 | 10.01 | 0.5409 | 0.0583 | 1.1591 | 1.1591 (FAIL) |
| L-H2-biaxial-equal | L4X4X1/4, Mw = 3, Mz = 3 (punteras comprimidas), Lb = 3000 | – | 7.59 | 5.58 | 0.1427 | 0.5381 | 0.9335 | 0.9335 (C) |

Contraste con los AISC Design Examples H.1B, H.3, H.4, E.14B y F.11C en [design-examples.md](design-examples.md).

## Decisiones

- **DH-1** Etapa 1: H1.1, H1.2 y H4. Etapa 2: H2 para ángulos simples (indicación del usuario,
  2026-10-30). H3 (torsión) queda fuera del alcance.
- **DH-2** La amplificación de Cb de H1.2 es opcional y la pide el usuario
  (`tension_cb_amplification`); sin pedirla, Cb no se amplifica (conservador).
- **DH-3** Segundo orden: Pr y Mr se toman como datos del usuario y se supone que
  provienen de un análisis según el Capítulo C; el programa no amplifica momentos (no
  calcula B1/B2). Supuesto documentado en cada resultado con compresión (indicación del
  usuario).
- **DH-4** H4 solo se evalúa con tracción axial: con compresión, Pr/Pc es negativo y la
  ecuación queda cubierta por la comprobación de flexión con F13.1.
- **DH-5** El cortante no entra en H1 ni en H2; se verifica por separado (Capítulo G).
- **DH-6** H2-1 se evalúa con Pr/Pc y Mr/Mc, usando en todos los puntos el Mc gobernante de cada
  eje, no un Mc por punto. Es el método de los Design Examples E.14B y F.11C, y el Commentary de
  H2 indica que la misma propiedad de sección entra en la tensión requerida y en la disponible.
- **DH-7** (sustituida el 2026-11-06 por DF-20) `Mx_3` y `My_2` de un ángulo simple se llevan a los ejes principales con
  tan α y el talón; ya no hay entrada `Mw`, `Mz` ni bloqueo por combinar momentos geométricos con otra demanda.
- **DH-8** Compresión de un ángulo simple con momentos: Pc sale de E3/E7 respecto de z y de E4 si
  b/t > 0,71√(E/Fy) (primer párrafo de E5), como en E.14B, y la excentricidad entra como momentos.
  `single_angle_e5` junto con `Mx_3` o `My_2` queda INCOMPLETO, porque E5 evalúa el miembro como cargado
  axialmente. Sin E5 y sin momentos también: no se supone carga concéntrica.

## Limitaciones

- H2 solo para ángulos simples; no se ofrece como alternativa a H1 en otras secciones.
- Los momentos, con sus efectos de segundo orden (DH-3), los aporta el usuario; el programa no calcula
  la excentricidad de la conexión ni B1.
- Sin H1.3 (alternativa para perfiles compactos con flexión en un eje), que puede ser
  menos conservadora; H1.1 siempre es válida.
