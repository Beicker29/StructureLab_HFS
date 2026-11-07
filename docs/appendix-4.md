# Apéndice 4: incendio por el método simple (4.2.4d)

Fuente: `a360-22w.pdf`, Apéndice 4, 4.2.3b y 4.2.4d, Commentary 4.2.4d y errata de 2025 (Pe(T) con I2-4 en 4.2.4d(c) y (d)). Solo LRFD, con
los factores de resistencia de temperatura ambiente (4.1.2).

## Entrada

Un case con `"condition": "fire"` lleva `fire`, con las temperaturas en °C del análisis térmico del usuario (4.2.2). Cada material lleva la suya, siempre
(DA4-9), de 20 a menos de 1200 °C:

| Campo | Uso |
| --- | --- |
| `steel_temperature` | Acero, uniforme; ala inferior en vigas. Obligatorio en todo miembro |
| `concrete_temperature` | Concreto, uniforme. Obligatorio en rellenos, embebidos y vigas compuestas; en muros y vigas de acople, esta o su perfil |
| `concrete_layers` | Perfil de muros planos y vigas de acople, de la placa al centro: `thickness`, `T`; suma medio espesor de concreto, con ±1 mm |
| `web_layers`, `flange_layers` | Perfiles de un muro en C, uno para el alma y otro para las alas |
| `bar_temperature` | Barras longitudinales. Obligatorio en rellenos con barras y en embebidos |

En la viga compuesta por A-4-20 la temperatura del concreto se exige y se reporta, pero no entra en el cálculo.

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

Fuera de 4.2.4d y de la Guía 38, con las ecuaciones de ambiente y las propiedades de 4.2.3b (DA4-8); la memoria lo indica:

| Miembro | Cálculo |
| --- | --- |
| Rellenos | Tracción (I2-14), flexión (I3.4), cortante (I4-1) e interacción con la regla de ambiente: H1.1, I5-1, o Método 2 con su curva y λ = Pn(T)/Pno(T); diagramas con Fy(T) y f'c(T) |
| Muros planos | Tracción (I2-16), flexión (I3.5), cortante (I4-2) e interacción (I5(c)) |
| Muros en C | Tracción, flexión (Apéndice A de la guía), cortante e interacción; la compresión sí sigue la guía, con una columna unitaria por panel (DA4-10) |
| Vigas de acople | Flexión (A.3) y cortante (I4-1); la fuerza axial sigue bloqueada, como a temperatura ambiente |

Con T del acero ≤ 200 °C, las resistencias son las de temperatura ambiente, en todo miembro (4.2.4d y su User Note). Hay un salto en 200 °C: es
el de la norma. La compacidad y la esbeltez se evalúan a temperatura ambiente (Commentary 4.2.4d). Se interpola linealmente en las tablas.

Quedan `INCOMPLETE`: miembros embebidos sobre 200 °C; secciones esbeltas; Fy o Fysr > 450 MPa y f'c > 55 MPa (4.2.3b); cortante de acero con Cv < 1 o Fcr por debajo
de 0.6Fy (User Note de 4.2.4d(g)); vigas compuestas desde 1100 °C (kcb = 0). Las conexiones y los agujeros de ventilación de rellenos (4.2.4a) no se revisan.

## Decisiones

- **DA4-1** Embebidos (indicación del usuario, 2026-11-01): quedan `INCOMPLETE` sobre 200 °C (`FIRE_NOT_COVERED`), porque ni 4.2.4d ni la Guía 38 dan una ecuación para ellos. En la hoja de ruta.
- **DA4-2** Compresión con modos torsionales (indicación del usuario, 2026-11-01): A-4-9 solo se da para pandeo por flexión y su User Note pide un
  método alternativo para el torsional. Se aplica A-4-9 también con el Fe de E4, calculado con E(T) y G(T). Como todo Fe de E3 y E4 es proporcional a E y G,
  y ambos llevan kE, Fe(T) = kE·Fe. Es decisión de ingeniería, no norma.
- **DA4-3** Flexión fuera de A-4-13 (indicación del usuario, 2026-11-01): Capítulo F con E(T) y Fy(T), como dice 4.2.4d(e). El Commentary advierte que esas
  ecuaciones pueden sobrestimar los modos de inestabilidad; la memoria lo anota cuando rige uno.
- **DA4-4** Viga compuesta (indicación del usuario, 2026-11-01): solo A-4-20. El método del gradiente de temperatura, en la hoja de ruta.
- **DA4-5** Barras de un relleno: I2-9 las transforma con Asr·Es/Ec; a temperatura se usa el Es de las barras a su temperatura y el Ec del concreto a la suya. La norma no lo resuelve.
- **DA4-6** H1.2 (indicación del usuario, 2026-11-01): en incendio no se amplifica Cb aunque se pida, porque el Apéndice 4 no define Pey(T).
- **DA4-7** A-4-10M (restricción de columnas frías; indicación del usuario, 2026-11-01): no se implementa por ahora; se usa Lc/r sin reducir, conservador. En la hoja de ruta.
- **DA4-8** Miembros compuestos fuera de 4.2.4d (indicación del usuario, 2026-11-01): flexión, cortante y tracción de rellenos y muros, y todo lo de muros en C y vigas de acople salvo la
  compresión de muros, usan las ecuaciones de ambiente con Fy(T), f'c(T), Ec(T), E(T) y G(T), apoyados en el Commentary de 4.2.4d. El Capítulo 6 de la Guía 38 solo trata compresión, horas y
  ventilación, y no menciona vigas de acople en incendio: es decisión de ingeniería. Con perfil, kc y kEc son el promedio por espesor, igual que sumar por capas cuando el perfil cruza el
  espesor y el bloque avanza a lo largo; en muros en C es aproximado si el eje neutro cae dentro del alma. La viga de acople es la de menor respaldo. Si a temperatura el eje neutro sale de la zona que suponen las ecuaciones del Apéndice A de la
  guía, la revisión queda `INCOMPLETE`, igual que a temperatura ambiente.
- **DA4-9** Temperaturas (indicación del usuario, 2026-11-01): uniformes por material y siempre obligatorias: una para el acero, una para el concreto y una para las barras donde las haya, también a
  200 °C o menos, aunque entonces no intervengan. Solo muros y vigas de acople admiten perfil de concreto. La viga por gradiente, pendiente, será la excepción.
- **DA4-11** Cortante con campo de tensión (indicación del usuario, 2026-11-07): sobre 200 °C, G2.2 y G2.3 se usan con Fy(T) y los Cv de
  temperatura ambiente; todos sus términos son proporcionales a Fy, así que Vn(T) = ky·Vn. Extrapola 4.2.4d(g), que solo trata la
  fluencia; G2.1 sigue exigiendo Cv1 = 1.
- **DA4-10** Compresión de muros en C (indicación del usuario, 2026-11-01): Guía 38, 6.2.2, una columna unitaria por panel con su espesor y su perfil, y A-4-12 en cada una; el alma cuenta L y
  cada ala W − tsc_w, para no duplicar esquinas.

## Verificación

`tests/oracles/chapter_a4.py` (Decimal, sin importar el paquete, con las tablas transcritas de nuevo) y `tests/test_appendix_4.py`. El muro también se
contrasta con el Ejemplo 6.1 de la Guía 38, cuya Ec. 6-1 es A-4-12 (`tests/test_design_guides.py`).
