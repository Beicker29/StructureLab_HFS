# Arquitectura

```text
src/steel_design/
├── models.py                    entrada (SteelCase) y resultado (DesignResult)
├── sections/                    catálogo: loader.py (Excel → Section, unidades),
│                                models.py, repository.py, geometry.py (macizos), identity.py
├── codes/aisc_360_22/
│   └── compression.py           fórmulas puras E1, E3–E7 y límites λr de B4.1a
├── domain/
│   ├── compression.py           clasificación, selección, ejecución y resistencia gobernante
│   ├── coverage.py              obligaciones del capítulo E derivadas del texto, independientes
│   ├── validation.py            validación de caso y sección
│   └── errors.py                errores estructurados
├── engine.py                    sección → compresión → obligaciones → estado
├── execution.py                 ejecución en memoria de un caso o un lote (para CLI y web)
└── run.py                       CLI (JSON en stdout; archivo solo con --output)
```

## Flujo

1. `engine.run(case)` valida el caso (`E = 200000 MPa`) y obtiene la sección del
   catálogo o la construye (macizos).
2. `domain/coverage.required_obligations` enumera los estados límite que el capítulo
   E exige para esa familia y esas longitudes. No importa `domain/compression`.
3. `domain/compression.compression_strength` clasifica (B4.1a), selecciona los modos
   aplicables, calcula cada uno con `codes/aisc_360_22/compression.py` y conserva
   todos; gobierna el menor Pn (E1).
4. `coverage.discharge` cruza obligaciones y modos. Si falta alguno, el estado es
   `INCOMPLETE`; si no, `PASS` o `FAIL` según `Pu / disponible`.

Un dominio sin datos o sin decisión ingenieril lanza `RuleNotImplementedError` o
`IncompleteSectionDataError`; el motor lo convierte en `INCOMPLETE` con el motivo.

## Responsabilidades (una fuente de verdad por concepto)

| Concepto | Propietario |
| --- | --- |
| Ecuaciones E3-2…E7-7, φc/Ωc, λr | `codes/aisc_360_22/compression.py` |
| Elementos B4.1a por familia, selección de modos, E7 por modo | `domain/compression.py` |
| Estados límite obligatorios (comprobación independiente) | `domain/coverage.py` |
| Unidades del catálogo y relaciones b/t derivadas | `sections/loader.py` |
| Decisión PASS/FAIL/INCOMPLETE | `engine.py` |

Ninguna interfaz (CLI, futura web) calcula capacidades: todas llaman a `engine`.

## Cómo añadir o modificar una disposición

1. Leer el artículo en `a360-22w.pdf` y las erratas; anotar edición, ecuación,
   condiciones y unidades. Distinguir Specification, User Note y Commentary.
2. Añadir la fórmula como función pura en `codes/aisc_360_22/compression.py`,
   devolviendo el identificador de ecuación. Una función por formulación.
3. Seleccionarla en `domain/compression.py` (familia, condiciones, datos requeridos).
   Si faltan datos o una decisión, bloquear con error estructurado.
4. Si cambia qué es obligatorio, actualizar `domain/coverage.py` desde el texto
   normativo, no desde la selección.
5. Añadir el caso al oráculo `tests/oracles/chapter_e.py` (cálculo independiente),
   regenerar `tests/fixtures/chapter_e/reference.json` y ejecutar las pruebas.
6. Actualizar [chapter-e.md](chapter-e.md).
