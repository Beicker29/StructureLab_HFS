# Capítulo D — alcance implementado

Fuente: ANSI/AISC 360-22, `a360-22w.pdf` (B4.3 p. 16.1-24; D1–D6 pp. 16.1-32 a
16.1-37). Las erratas locales no modifican el capítulo D. Unidades internas: N, mm,
MPa; resultados en kN.

## Alcance

Se activa con `Pu < 0` (tracción). Aplica a todas las familias del catálogo y a
las barras macizas definidas en la entrada.

| Disposición | Tratamiento |
| --- | --- |
| D1 | Recomendación L/r ≤ 300 (nota, no resistencia) con la longitud fabricada (`tension.fabricated_length`) y el radio de giro mínimo (rz en ángulos simples). Sin longitud fabricada se informa como no evaluada. |
| D2(a) | Fluencia en la sección bruta: Pn = Fy·Ag (D2-1), φt = 0,90. |
| D2(b) | Rotura en la sección neta: Pn = Fu·Ae (D2-2), φt = 0,75. |
| D3 | Ae = An·U (D3-1). An (B4.3b) y U (Tabla D3.1) son **datos del usuario** (decisión DD-1). |
| D4 | Detallado de miembros armados (placas de unión, separación de conectores): no se verifica; se informa como nota en ángulos dobles. |
| D5, D6 | Miembros con pasador y barras de ojo: fuera del alcance. |
| J4.1, J4.3 | Elementos de conexión y bloque de cortante: fuera del alcance (Capítulo J). |

**Modo gobernante.** D2 toma la menor resistencia de diseño φt·Pn (solo LRFD). Como
los factores difieren entre fluencia y rotura, puede gobernar la rotura aunque su Pn
nominal sea mayor (cuando Pn rotura / Pn fluencia < 0,90/0,75 = 1,2).

**Datos obligatorios.** Sin `tension` (An, U) o sin `material.Fu`, el resultado es
INCOMPLETO. An > Ag se rechaza. U debe cumplir 0 < U ≤ 1.

## Verificación con cálculos independientes

`tests/oracles/chapter_d.py` recalcula en Decimal leyendo Ag directamente del Excel,
sin importar el paquete. El software coincide con tolerancia relativa 1e-12.

| Caso | Perfil | Fy/Fu (MPa) | An (mm²) | U | Pn fluencia (kN) | Pn rotura (kN) | φt·Pn (kN) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W-rupture-governs | W14X90 | 345/450 | 15000 | 0.9 | 5899.50 | 6075.00 | 4556.25 (TR) |
| W-yielding-governs | W14X90 | 345/450 | 17100 | 1 | 5899.50 | 7695.00 | 5309.55 (TY) |
| W-rupture-governs-larger-Pn | W14X90 | 345/450 | 15719 | 1 | 5899.50 | 7073.55 | 5305.16 (TR) |
| C-case2-U | C15X50 | 250/400 | 8600 | 0.85 | 2370.00 | 2924.00 | 2133.00 (TY) |
| L-case8-U | L4X4X1/4 | 250/400 | 1100 | 0.6 | 312.50 | 264.00 | 198.00 (TR) |
| 2L-welded | 2L4X4X1/4 | 345/450 | 2490 | 0.87 | 859.05 | 974.84 | 731.13 (TR) |
| RHSS-slotted | PTE100X100X4MM | 345/450 | 1350 | 0.80 | 481.97 | 486.00 | 364.50 (TR) |
| CHSS-slotted | PTER4"X3.00MM | 345/450 | 950 | 0.87 | 337.20 | 371.93 | 278.94 (TR) |

## Decisiones

- **DD-1** An y U son datos del usuario (indicación del usuario). El programa no
  calcula la disposición de agujeros (B4.3b) ni el caso de la Tabla D3.1; la memoria
  lo declara.
- **DD-2** La demanda se expresa con `Pu` con signo: Pu > 0 compresión (Capítulo E),
  Pu < 0 tracción (Capítulo D). Indicación del usuario.
- **DD-3** Para la nota D1 se usa el radio de giro mínimo del catálogo: min(rx, ry)
  y, en ángulos simples, también rz.
- **DD-4** Solo LRFD (indicación del usuario): φt = 0,90 en fluencia y 0,75 en rotura.
