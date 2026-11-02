# Pruebas y validación

```powershell
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
python -m build            # opcional: comprueba el empaquetado
```

La CI (`.github/workflows/ci.yml`) ejecuta lo mismo en Windows y Ubuntu con Python 3.12.

## Suite

| Archivo | Garantía |
| --- | --- |
| `tests/test_compression.py` | Perfiles reales contra cálculos independientes (todas las familias soportadas); selección; bloqueos; propiedades de fórmulas (continuidad E3/E5, c2, E4-4 → E4-3, E6, E7-7) |
| `tests/test_tension.py` | Capítulo D: perfiles reales de las seis familias contra cálculos independientes, modo gobernante por resistencia de diseño φt·Pn, datos faltantes, nota D1, memoria |
| `tests/test_flexure.py` | Capítulo F: perfiles reales contra cálculos independientes (F2, F3, F6, F7 incl. Se, F8, F11, F13.1), estados límite reportados, datos faltantes, bloqueos, interacción pendiente, memoria |
| `tests/test_shear.py` | Capítulo G: perfiles reales contra cálculos independientes, selección y bloqueos |
| `tests/test_interaction.py` | Capítulo H: H1, H2 y H4 contra cálculos independientes |
| `tests/test_interaction_diagram.py` | Diagramas de interacción de rellenos y embebidos |
| `tests/test_requirements_direct_analysis.py` | Requerimientos técnicos y rigideces para el método directo |
| `tests/test_design_examples.py` | Contraste con los AISC Design Examples v16.0 |
| `tests/test_beta_w_catalog.py` | βw de los ángulos del catálogo |
| `tests/test_composite.py` | Capítulo I: rellenos, embebidos y vigas contra cálculos independientes; requisitos, bloqueos y memoria |
| `tests/test_appendix_4.py` | Apéndice 4, 4.2.4d: incendio contra cálculos independientes, bloqueos y memoria |
| `tests/test_design_guides.py` | Contraste con los ejemplos de AISC Design Guide 6 y Design Guide 38 y contenidos de esas guías contra cálculos independientes ([detalle](docs/design-guides.md)) |
| `tests/test_engine.py` | Obligaciones independientes; frontera PASS/FAIL; INCOMPLETE ante dominios bloqueados; barra maciza a mano |
| `tests/test_inputs.py` | Rechazo de entradas inválidas o incompletas |
| `tests/test_catalog.py` | Importación del Excel: familias, unidades, relaciones B4 |
| `tests/test_interfaces.py` | CLI (sin escritura por defecto, `--output`, errores), lotes y ejemplos |
| `tests/test_reporting.py` | Memoria de cálculo: contenido trazable al resultado, caso bloqueado sin resistencia, PDF y CLI |

## Oráculo independiente

`tests/oracles/chapter_c.py`, `chapter_d.py`, `chapter_e.py`, `chapter_f.py`, `chapter_g.py`, `chapter_h.py` (este
reutiliza los oráculos D, E y F para las resistencias), `chapter_i.py` y `chapter_a4.py` se escriben directamente desde la Specification, en
Decimal, leyendo `data/sections.xlsx` con sus propias escalas de unidades y **sin
importar `steel_design`**. Las pruebas consumen el resultado congelado
`tests/fixtures/chapter_<x>/reference.json`. Para añadir un caso:

```powershell
python tests/oracles/chapter_e.py   # regenera la referencia del capítulo E
python tests/oracles/chapter_d.py   # regenera la referencia del capítulo D
python tests/oracles/chapter_f.py   # regenera la referencia del capítulo F
python tests/oracles/chapter_c.py   # regenera la referencia de C2.3 (rigideces para método directo)
python tests/oracles/chapter_g.py   # regenera la referencia del capítulo G
python tests/oracles/chapter_h.py   # regenera la referencia del capítulo H
python tests/oracles/chapter_i.py   # regenera la referencia del capítulo I
python tests/oracles/chapter_a4.py  # regenera la referencia del Apéndice 4, 4.2.4d
```

Revisar el diff de la referencia: un valor de referencia solo cambia por una
razón normativa documentada, nunca para que pase el software.

## Reglas

- No declarar validación normativa a partir de pruebas que comparan el motor
  consigo mismo; las expectativas numéricas vienen del oráculo o de cálculos a mano.
- Un dominio sin datos o sin decisión se bloquea (INCOMPLETE); nunca se supone un valor.
- Las salidas generadas (`results/`, temporales) no se versionan.
