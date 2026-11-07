# Ejes y signos (convención de ETABS)

La entrada, la salida y la memoria usan los ejes locales de una sección de ETABS (decisión del usuario, 2026-11-06).
Las ecuaciones de `codes/` y las propiedades del catálogo conservan los símbolos de AISC (Ix, Sx, Zx, Fex, x, y); la
memoria los muestra con su eje, por ejemplo «Momento de inercia respecto de x (eje 3) (Ix)».

## Ejes

| Eje | AISC | Dirección |
| --- | --- | --- |
| 1 | z | A lo largo del miembro; su sentido positivo sale de la regla de la mano derecha girando del eje 2 al eje 3 |
| 2 | y | Vertical de la sección (en un perfil I, paralelo al alma) |
| 3 | x | Horizontal de la sección (en un perfil I, paralelo a las alas) |

El eje 3 es el eje mayor de un perfil I: `Mx_3` es el momento respecto de x (eje 3) y `My_2` respecto de y (eje 2).

## Signos

| Dato | Signo positivo |
| --- | --- |
| `P` | Tracción (Capítulo D); `P < 0` es compresión (Capítulo E) |
| `Mx_3` | Comprime la cara +2 |
| `My_2` | Comprime la cara +3 (comprobado por el usuario en ETABS) |
| `Vy_2`, `Vx_3` | El signo no interviene: se usa el valor absoluto |
| `composite.second_order.Pnt`, `Plt` | Tracción, como `P` |

`Vy_2` es el cortante a lo largo de y (eje 2), que acompaña a `Mx_3`; `Vx_3`, a lo largo de x (eje 3), acompaña a `My_2`.

## Nombres

Cada dato lleva el símbolo de AISC y el eje: `Lx_3`, `Ly_2`, `Lz_1` (longitudes no arriostradas para pandeo respecto de x,
y y torsional), `Kx_3`, `Ky_2`, `Kz_1`, `xa_3`, `ya_2` (desplazamiento del arriostramiento) y los chequeos `flexure_x_3`,
`flexure_y_2`, `shear_y_2`, `shear_x_3`. Los ejes principales w y z de los ángulos simples (AISC) conservan su nombre:
`flexure_w`, `flexure_z`.

## La parte comprimida sale del signo

No hay datos para declarar qué parte está comprimida: se deduce del signo del momento.

- **Perfil I de alas distintas (F4, F5):** `Mx_3 > 0` comprime el ala de la cara +2 (`custom_section.flange_plus2`) y
  `Mx_3 < 0` la de la cara −2 (`flange_minus2`).
- **Viga compuesta:** la losa está siempre en la cara +2. `Mx_3 > 0` es flexión positiva (I3.2a) y `Mx_3 < 0` negativa,
  con el acero solo (I3.2b, Capítulo F).
- **Muro en C:** `composite.c_wall.web_side` (`+3` o `−3`) indica de qué lado del eje 3 está el alma. Las puntas de las
  alas apuntan al otro lado; `My_2` comprime la cara +3.
- **Ángulo doble (F9):** `heel.axis_2` indica de qué lado del eje 2 queda el dorso (las alas paralelas al eje 3). Las alas
  verticales apuntan al lado contrario; están comprimidas cuando `Mx_3` comprime su punta.
- **Ángulo simple (F10):** el ala larga es paralela al eje 2 y la corta al eje 3. `heel.axis_2` y `heel.axis_3` indican
  el lado de cada eje donde queda el talón.
  - Con un solo momento geométrico, sin fuerza axial y con `flexure.lateral_torsional_restraint` declarado
    (continuo, o con alas iguales), F10.2(2) se aplica en ese eje geométrico. La punta comprimida es la del ala
    perpendicular al eje, si el momento comprime su cara.
  - En los demás casos el vector momento m = (−M2, M3) se lleva a los ejes principales w, z con tan α del catálogo.
    Con el talón en (s2, s3), z = (−s2·cos α, s3·sin α) y w = (−s2·sin α, −s3·cos α) en componentes (2, 3). El esfuerzo de
    la componente según u en el punto p es (m·u)/Iu · p·(e1 × u), con e1 × u = (−u3, u2). De ahí salen el ala comprimida
    bajo Mw, el estado de las punteras bajo Mz y los sentidos en A, B y C para H2 (decisión DF-20 de
    [chapter-f.md](chapter-f.md)).
  - El M2 de ETABS es menos el momento vectorial respecto del eje 2, porque comprime la cara +3. Un componente menor
    que 10⁻¹² de la suma de los momentos se toma como redondeo del giro y no genera chequeo.

## Ejemplo

Una columna W14X90 con compresión, flexión biaxial y cortante; sus resultados están en `checks` como `axial`,
`flexure_x_3`, `flexure_y_2`, `shear_y_2` e `interaction`:

```json
{
  "section_name": "W14X90",
  "material": "ASTM A572 Gr 50",
  "flexure": {"tension_flange_holes": false},
  "lengths": {"ultimate": {"Lx_3": 4000, "Ly_2": 4000, "Lz_1": 4000}},
  "cases": [
    {"name": "Combinación 1", "P": -1500, "Mx_3": 200, "My_2": -50, "Vy_2": 120}
  ]
}
```

Un ángulo simple con el talón abajo a la izquierda (`"heel": {"axis_2": "-", "axis_3": "-"}`) y `Mx_3 > 0` tiene
comprimida la punta del ala larga, que apunta a +2.
