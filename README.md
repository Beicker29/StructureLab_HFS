# StructureLab HFS

Motor de diseno estructural en acero basado en AISC 360-22 (`a360-22w.pdf`).

## Estado actual

- Arquitectura por capas (`codes`, `domain`, `sections`, `engine`).
- Capitulo D (tension) y F2 (flexion mayor) implementados.
- Capitulo E (compresion) implementado para E3, E4, E5 y E7.
- Politica estricta: si una regla aplicable no puede evaluarse por datos faltantes, el caso falla con error estructurado.
- Los checks axiales reportan clasificacion de elementos (`non_slender`/`slender`) en `checks[].details.element_classification`.

## Estructura

```text
data/sections.xlsx               Catalogo de perfiles
examples/*.json                  Casos CLI de referencia
src/steel_design/codes           Formulas normativas puras
src/steel_design/domain          Reglas, validaciones, enrutamiento, errores
src/steel_design/sections        Carga y modelos de secciones
src/steel_design/engine.py       Pipeline principal
src/steel_design/run.py          CLI
tests/                           Suite unitaria e integracion
docs/aisc_360_22_traceability.md Matriz de trazabilidad normativa
```

## Instalacion

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Uso CLI

```bash
python -m src.steel_design.run examples/w_shape_case.json
```

Salida por consola: resumen de checks (sin `details`).

Salida detallada por ejecucion: se genera automaticamente un JSON en `results/<TIPO_PERFIL>/`.
Incluye `input`, `output` completo y `memory` tipo memoria de calculo:
- `memory.global_summary`: capacidad global gobernante (minima entre clausulas) y clausulas criticas.
- `memory.clause_results`: desarrollo por clausula con variables intermedias, factores de diseno y capacidad.

## Ejemplos

Casos actualmente ejecutables (exit code 0):

- `examples/w_shape_case.json`
- `examples/channel_case.json`
- `examples/single_angle_case.json`
- `examples/rectangular_hss_case.json`
- `examples/circular_hss_case.json`

Casos de error esperado (exit code != 0):

- `examples/double_angle_case.json` (faltan `J` y `Cw` en hoja `2L` para E4)

## Nota de entrada para E4

En `factors` se pueden incluir offsets de arriostramiento:

- `xa` (mm): bracing offset distance along x-axis
- `ya` (mm): bracing offset distance along y-axis
