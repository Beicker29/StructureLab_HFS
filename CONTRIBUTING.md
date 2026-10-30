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
| `tests/test_compression.py` | Perfiles reales contra cálculos independientes (todas las familias soportadas, LRFD y ASD); selección; bloqueos; propiedades de fórmulas (continuidad E3/E5, c2, E4-4 → E4-3, E6, E7-7) |
| `tests/test_tension.py` | Capítulo D: perfiles reales de las seis familias contra cálculos independientes (LRFD y ASD), modo gobernante por resistencia disponible, datos faltantes, nota D1, memoria |
| `tests/test_engine.py` | Obligaciones independientes; frontera PASS/FAIL; INCOMPLETE ante dominios bloqueados; barra maciza a mano |
| `tests/test_inputs.py` | Rechazo de entradas inválidas o incompletas |
| `tests/test_catalog.py` | Importación del Excel: familias, unidades, relaciones B4 |
| `tests/test_interfaces.py` | CLI (sin escritura por defecto, `--output`, errores), lotes y ejemplos |
| `tests/test_reporting.py` | Memoria de cálculo: contenido trazable al resultado, caso bloqueado sin resistencia, PDF y CLI |

## Oráculo independiente

`tests/oracles/chapter_e.py` y `tests/oracles/chapter_d.py` se escriben directamente desde la Specification, en
Decimal, leyendo `data/sections.xlsx` con sus propias escalas de unidades y **sin
importar `steel_design`**. Las pruebas consumen el resultado congelado
`tests/fixtures/chapter_<x>/reference.json`. Para añadir un caso:

```powershell
python tests/oracles/chapter_e.py   # regenera la referencia del capítulo E
python tests/oracles/chapter_d.py   # regenera la referencia del capítulo D
```

Revisar el diff de la referencia: un valor de referencia solo cambia por una
razón normativa documentada, nunca para que pase el software.

## Reglas

- No declarar validación normativa a partir de pruebas que comparan el motor
  consigo mismo; las expectativas numéricas vienen del oráculo o de cálculos a mano.
- Un dominio sin datos o sin decisión se bloquea (INCOMPLETE); nunca se supone un valor.
- Las salidas generadas (`results/`, temporales) no se versionan.
