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
| Ángulo simple con Pu y Mw o Mz, o con Mw y Mz | H2-1 en los puntos A, B y C (F10) |
| Ángulo simple con Mux o Muy combinado con otra demanda | INCOMPLETO: H2 exige ejes principales (DH-7) |
| Torsión (H3) y alternativa H1.3 | no implementadas |

El chequeo `interaction` aparece cuando la combinación tiene dos o más de Pu, Mux, Muy,
Mw, Mz. Usa las resistencias de diseño de los chequeos de los Capítulos D, E y F sin
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

El sentido se declara con `angle_flexure.leg_in_compression` (Mw) y `angle_flexure.toe` (Mz),
igual que en F10 (DF-9); el signo de `Mw` y `Mz` no se usa. En alas iguales `leg_in_compression`
es opcional: A y C son simétricos y solo cambia el rótulo del punto gobernante.

## Entrada

- Las demandas `Pu`, `Mux`, `Muy` de la combinación.
- `flexure.tension_cb_amplification` (por defecto `false`): H1.2 permite multiplicar Cb
  por √(1 + Pr/Pey), Pey = π²EIy/Lb² (H1-2), en miembros doblemente simétricos (W,
  PTE, barras). Si se pide en un perfil que no lo es, se informa y se usa Cb sin amplificar.

## Verificación con cálculos independientes

`tests/oracles/chapter_h.py` escribe H1-1a/H1-1b, H1-2, H4-1 y H2-1 y toma Pc y Mc de
los oráculos D, E y F. Coincidencia con tolerancia relativa 1e-9:

| Caso | Perfil y demandas (kN, kN·m) | Pc | Mcx | Mcy | H1 | Valor |
| --- | --- | --- | --- | --- | --- | --- |
| W-H1-1a | W14X90, Pu = 1500, Mux = 200, Muy = 50 | 4650.81 | 777.62 | 370.43 | H1-1a 0.6711 | 0.6711 |
| W-H1-1b | W14X90, Pu = 300, Mux = 200, Muy = 50 | 4650.81 | 777.62 | 370.43 | H1-1b 0.4244 | 0.4244 |
| W-biaxial-no-axial | W14X90, Mux = 300, Muy = 100 | – | 777.62 | 370.43 | H1-1b 0.6557 | 0.6557 |
| W-H1.2-tension | W14X90, Pu = −800, Mux = 400, Muy = 50, Lb = 8000, Cb = 1.14 | 4556.25 | 762.45 | 370.43 | H1-1b 0.7474 | 0.7474 |
| W-H1.2-Cb-amplified | igual, Cb × 1.0825 (H1-2) | 4556.25 | 777.62 | 370.43 | H1-1b 0.7372 | 0.7372 |
| W-H4-holes | W14X90, Pu = −1500, Mux = 300, Afn = 4500 | 4556.25 | 643.82 | – | H1-1a 0.7434; H4 0.7952 | 0.7952 |
| C-H1-1a | C15X50, Pu = 800, Mux = 100 | 794.30 | 300.01 | – | H1-1a 1.3035 | 1.3035 (FAIL) |
| RHSS-H1-1a | PTE100X100X4MM, Pu = 200, Mux = 5, Muy = 3 | 281.67 | 15.52 | 15.52 | H1-1a 1.1681 | 1.1681 (FAIL) |
| 2L-H1-1b | 2L4X4X1/4, Pu = 40, Mux = 5 | 483.03 | 16.69 | – | H1-1b 0.3410 | 0.3410 |

H2 en ángulos simples. El oráculo obtiene el signo en cada punto de sus coordenadas en ejes
principales (x, y, tan α del catálogo), no de la tabla anterior. Fy = 345 MPa salvo indicación:

| Caso | Perfil y demandas (kN, kN·m) | Pc | Mcw | Mcz | A | B | C | Valor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L-H2-comp-long-toe | L6X4X3/8, Pu = 100, Mw = 5 (ala larga), Mz = 2 (punteras en tracción), L = Lb = 2000 | 385.95 | 20.10 | 10.01 | 0.1894 | 0.2101 | 0.3081 | 0.3081 (C) |
| L-H2-comp-short-toe | igual, ala corta y punteras comprimidas | 385.95 | 25.88 | 10.01 | 0.6521 | 0.2526 | 0.2656 | 0.6521 (A) |
| L-H2-comp-axial-Mw | L8X4X1/2, Pu = 300, Mw = 20 (ala larga), L = Lb = 1524 | 749.78 | 42.42 | – | 0.0714 | 0.0714 | 0.8716 | 0.8716 (C) |
| L-H2-comp-heel-governs | L8X4X1/2, Pu = 150, Mz = 5 (punteras en tracción), L = 1524 | 749.78 | – | 13.88 | 0.1602 | 0.5603 | 0.1602 | 0.5603 (B) |
| L-H2-comp-FAIL | L4X4X1/4, Fy = 450, Pu = 120, Mz = 4 (punteras comprimidas), L = 2000 | 188.21 | – | 6.35 | 1.2678 | 0.0074 | 1.2678 | 1.2678 (FAIL) |
| L-H2-tension | L6X4X3/8, Pu = −300, Mw = 8 (ala corta), Mz = 3 (punteras en tracción), Lb = 2000 | 545.06 | 25.88 | 10.01 | 0.5408 | 0.0584 | 1.1592 | 1.1592 (FAIL) |
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
- **DH-7** Mux y Muy de un ángulo simple no se convierten a ejes principales: combinados con otra
  demanda, el resultado es INCOMPLETO y se pide Mw y Mz (F.11C muestra la conversión). Convertirlos
  exigiría declarar el sentido en los ejes principales, que no se deduce de `toe` en ejes geométricos.
- **DH-8** Compresión de un ángulo simple con Mw o Mz: Pc sale de E3/E7 respecto de z y de E4 si
  b/t > 0,71√(E/Fy) (primer párrafo de E5), como en E.14B, y la excentricidad entra como momentos.
  `single_angle_e5` junto con Mw o Mz queda INCOMPLETO, porque E5 evalúa el miembro como cargado
  axialmente. Sin E5 y sin momentos también: no se supone carga concéntrica.

## Limitaciones

- H2 solo para ángulos simples; no se ofrece como alternativa a H1 en otras secciones.
- Mw y Mz, con sus efectos de segundo orden (DH-3), los aporta el usuario; el programa no calcula
  la excentricidad de la conexión ni B1.
- Sin H1.3 (alternativa para perfiles compactos con flexión en un eje), que puede ser
  menos conservadora; H1.1 siempre es válida.
