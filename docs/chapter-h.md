# Capítulo H — alcance implementado (etapa 1)

Fuente: ANSI/AISC 360-22, `a360-22w.pdf` (H1–H4, pp. 16.1-82 a 16.1-88) y errata de
septiembre 2026 (unidades de Lb en H1-2: in. (mm)). Solo LRFD (α = 1,0 en H1-2).

## Alcance

| Situación | Disposición |
| --- | --- |
| Compresión y flexión (x, y o ambas) | H1.1: H1-1a si Pr/Pc ≥ 0,2; si no, H1-1b |
| Tracción y flexión | H1.2: mismas ecuaciones con Pc = φt·Pn (Capítulo D) |
| Flexión biaxial sin carga axial | H1-1b con Pr = 0 |
| Tracción y flexión respecto de x en I o canal con agujeros en el ala traccionada | H4-1, además de H1 |
| Ángulos simples con fuerzas combinadas (incluido Mw con Mz) | INCOMPLETO: requieren H2 (etapa 2) |
| Torsión (H3) y alternativa H1.3 | no implementadas |

El chequeo `interaction` aparece cuando la combinación tiene dos o más de Pu, Mux, Muy,
Mw, Mz. Usa las resistencias de diseño de los chequeos de los Capítulos D, E y F sin
recalcularlas (Mcx incluye F13.1 cuando hay agujeros). Si falta alguna, queda
INCOMPLETO con el chequeo que falta; un FAIL de un componente siempre se informa.
Gobierna el mayor valor entre H1 y H4.

## Entrada

- Las demandas `Pu`, `Mux`, `Muy` de la combinación.
- `flexure.tension_cb_amplification` (por defecto `false`): H1.2 permite multiplicar Cb
  por √(1 + Pr/Pey), Pey = π²EIy/Lb² (H1-2), en miembros doblemente simétricos (W,
  PTE, barras). Si se pide en un perfil que no lo es, se informa y se usa Cb sin amplificar.

## Verificación con cálculos independientes

`tests/oracles/chapter_h.py` escribe H1-1a/H1-1b, H1-2 y H4-1 y toma Pc, Mcx y Mcy de
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

Contraste con los AISC Design Examples H.1B, H.3 y H.4 en [design-examples.md](design-examples.md).

## Decisiones

- **DH-1** Etapa 1: H1.1, H1.2 y H4; H2 (ángulos simples y secciones asimétricas) en una
  etapa 2; H3 (torsión) fuera del alcance (indicación del usuario, 2026-10-30).
- **DH-2** La amplificación de Cb de H1.2 es opcional y la pide el usuario
  (`tension_cb_amplification`); sin pedirla, Cb no se amplifica (conservador).
- **DH-3** Segundo orden: Pr y Mr se toman como datos del usuario y se supone que
  provienen de un análisis según el Capítulo C; el programa no amplifica momentos (no
  calcula B1/B2). Supuesto documentado en cada resultado con compresión (indicación del
  usuario).
- **DH-4** H4 solo se evalúa con tracción axial: con compresión, Pr/Pc es negativo y la
  ecuación queda cubierta por la comprobación de flexión con F13.1.
- **DH-5** El cortante no entra en H1; se verifica por separado (Capítulo G).

## Limitaciones

- Sin H2: ángulos simples con carga axial y flexión, o con flexión en dos ejes, quedan INCOMPLETO.
- Sin H1.3 (alternativa para perfiles compactos con flexión en un eje), que puede ser
  menos conservadora; H1.1 siempre es válida.
