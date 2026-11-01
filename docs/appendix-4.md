# Apéndice 4: incendio por el método simple (4.2.4d)

Fuente: `a360-22w.pdf`, Apéndice 4, 4.2.3b y 4.2.4d, Commentary 4.2.4d y errata de 2025 (Pe(T) con I2-4 en 4.2.4d(c) y (d)). Solo LRFD, con
los factores de resistencia de temperatura ambiente (4.1.2).

## Entrada

Un case con `"condition": "fire"` lleva `fire`, con las temperaturas en °C del análisis térmico del usuario (4.2.2):

| Campo | Uso |
| --- | --- |
| `steel_temperature` | Temperatura máxima del acero, uniforme en la sección; ala inferior en vigas. Obligatorio; de 20 a menos de 1200 °C |
| `concrete_temperature` | Concreto uniforme, en rellenos y muros |
| `concrete_elements` | Relleno por elementos: `A`, `Ix`, `Iy`, `T`; deben sumar Ac, Icx e Icy, sin las barras, con ±1 % |
| `concrete_layers` | Muro por capas, de la placa al centro: `thickness`, `T`; deben sumar tsc/2 − t, con ±1 mm |
| `bar_temperature` | Barras de un relleno; obligatorio si las tiene |

Los cases de incendio van en el mismo JSON del miembro, junto con los de otras condiciones, y salen en su única memoria. Las solicitaciones son del usuario, con la combinación A-4-1 (4.1.4). `composite.fire` queda solo para las revisiones opcionales de la Guía 38
en muros: `required_rating_hours` (Ec. 6-5) y `vent` (6.3.5). No son norma y no dan la resistencia.

## Alcance

| Literal | Miembro | Cálculo |
| --- | --- | --- |
| 4.2.4d(a) | Tracción en acero | D2 con Fy(T); Fu(T) = Fy(T) sobre 400 °C, Fu hasta 400 °C |
| 4.2.4d(b) | Compresión en acero sin elementos esbeltos | A-4-9, con Fe(T) de E3 y E4 |
| 4.2.4d(c) | Compresión en rellenos | I2-9 e I2-12 a temperatura, A-4-11, I2-4 |
| 4.2.4d(d) | Compresión en muros planos | I2-15 e I1-1 a temperatura, A-4-12, I2-4, sobre la columna unitaria |
| 4.2.4d(e) | Flexión en acero | A-4-13 a A-4-19M en W compactos, eje mayor; el resto, Capítulo F con E(T) y Fy(T) |
| 4.2.4d(f) | Viga compuesta, flexión positiva | A-4-20 |
| 4.2.4d(g) | Cortante | Fluencia del Capítulo G con Fy(T) |
| 4.2.4d(h) | Interacción en acero | Capítulo H con las resistencias anteriores |

Con T del acero ≤ 200 °C, las resistencias son las de temperatura ambiente, en todo miembro (4.2.4d y su User Note). Hay un salto en 200 °C: es
el de la norma. La compacidad y la esbeltez se evalúan a temperatura ambiente (Commentary 4.2.4d). Se interpola linealmente en las tablas.

Quedan `INCOMPLETE`: secciones esbeltas en compresión o flexión; Fy o Fysr > 450 MPa y f'c > 55 MPa (4.2.3b); cortante con Cv < 1 o Fcr por debajo
de 0.6Fy (User Note de 4.2.4d(g)); vigas compuestas desde 1100 °C (kcb = 0). Las conexiones y los agujeros de ventilación de rellenos (4.2.4a) no se revisan.

## Decisiones

- **DA4-1** Miembros sin regla en 4.2.4d (indicación del usuario, 2026-11-01): flexión, cortante y tracción de rellenos y muros, embebidos, muros en C
  y vigas de acoplamiento quedan `INCOMPLETE` sobre 200 °C (`FIRE_NOT_COVERED`). En la hoja de ruta.
- **DA4-2** Compresión con modos torsionales (indicación del usuario, 2026-11-01): A-4-9 solo se da para pandeo por flexión y su User Note pide un
  método alternativo para el torsional. Se aplica A-4-9 también con el Fe de E4, calculado con E(T) y G(T). Como todo Fe de E3 y E4 es proporcional a E y G,
  y ambos llevan kE, Fe(T) = kE·Fe. Es decisión de ingeniería, no norma.
- **DA4-3** Flexión fuera de A-4-13 (indicación del usuario, 2026-11-01): Capítulo F con E(T) y Fy(T), como dice 4.2.4d(e). El Commentary advierte que esas
  ecuaciones pueden sobrestimar los modos de inestabilidad; la memoria lo anota cuando rige uno.
- **DA4-4** Viga compuesta (indicación del usuario, 2026-11-01): solo A-4-20. El método del gradiente de temperatura, en la hoja de ruta.
- **DA4-5** Barras de un relleno: I2-9 las transforma con Asr·Es/Ec; a temperatura se evalúan Es, Ec y f'c con la temperatura de las barras, porque
  representan al concreto que las rodea. La norma no lo resuelve.
- **DA4-6** H1.2 (indicación del usuario, 2026-11-01): en incendio no se amplifica Cb aunque se pida, porque el Apéndice 4 no define Pey(T).
- **DA4-7** A-4-10M (restricción de columnas frías; indicación del usuario, 2026-11-01): no se implementa por ahora; se usa Lc/r sin reducir, conservador. En la hoja de ruta.

## Verificación

`tests/oracles/chapter_a4.py` (Decimal, sin importar el paquete, con las tablas transcritas de nuevo) y `tests/test_appendix_4.py`. El muro también se
contrasta con el Ejemplo 6.1 de la Guía 38, cuya Ec. 6-1 es A-4-12 (`tests/test_design_guides.py`).
