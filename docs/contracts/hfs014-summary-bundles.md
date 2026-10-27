# HFS-014 — Resumen observado y lotes no vacíos

Contrato de transporte CLI/memoria, `HFS-014-v1`. Las resistencias, checks,
estado de caso y obligaciones HFS-010 no cambian. [Informe y evidencia](../audit/hfs014/report.md).

## Resumen único por caso

`run.py::_build_global_summary(result)` es la única fuente del resumen. Se publica
en el CLI (`global_summary` de cada caso, también dentro de lotes), en
`output.global_summary` de la memoria y en `memory.global_summary`. Esta última
conserva además su campo previo `admissibility`; ese campo no decide el gobernante.
No se agrega un supuesto gobernante entre miembros/casos de un lote.

Campos del resumen:

| Campo | Significado |
|---|---|
| `version` | `HFS-014-v1` |
| `overall_status` | Estado de EngineResult sin reinterpretar: PASS/FAIL/INCOMPLETE |
| `scope` | `executed_checks_only`, siempre. Nunca envolvente definitiva de la estructura |
| `description` | Explica que son gobernantes observados entre checks ejecutados |
| `ranking_basis` | DCR publicado, con todos los empates exactos a la precisión disponible; sin reconstruir DCR bruto |
| `eligibility_basis` | `executed_resistance_obligations` cuando hay coverage; `provisional_numeric_checks_without_coverage` para invocaciones directas/legacy sin ella |
| `max_dcr_published` | Máximo de DCR publicados elegibles, o `null` sin candidato |
| `observed_governing_checks` | Lista de todos los checks empatados en el máximo, en orden de ejecución; vacía sin candidato |
| `failed_checks` | **Todos** los checks FAIL, aunque no sean gobernantes/elegibles y aunque el estado global sea INCOMPLETE |
| `excluded_checks` | Índice y motivo de exclusión del ranking; no elimina el check ni cambia estado/cobertura |

Cada elemento de `observed_governing_checks` o `failed_checks` contiene:
`check_index` (base cero respecto a `checks` y `clause_results`), `clause`, `name`,
`dcr_published`, `status`. No incorpora una capacidad mezclada ni infiere unidades
por nombres/cláusulas. El DCR es adimensional; las capacidades permanecen en sus
checks originales, sin agregarlas entre unidades. Un DCR no finito de un FAIL se
representa aquí como `null` y se excluye del ranking; el check/fallo se conserva.

### Elegibilidad y límites

Con cobertura, un candidato debe estar vinculado mediante `executed_checks` a
alguna obligación con `resistance=True`. No requiere `accepted_checks`, porque
es una observación de ejecución parcial, **no acreditación**. El resumen no
modifica ni crea obligaciones. Así, un check I1 de elegibilidad o una recomendación
sin vínculo resistente no gobierna por tener un número grande.

Además, se requiere demanda publicada finita no nula, capacidad publicada finita
positiva y DCR publicado finito no negativo. Un check 0/0 o inactivo no es
resistencia gobernante. Si un valor positivo muy pequeño aparece redondeado a
cero, no se reconstruye desde la memoria: queda excluido con motivo y, si falló,
sigue en `failed_checks`. Es una limitación explícita de datos publicados hasta
HFS-015, no prueba de inexistencia de resistencia real.

Sin cobertura, las comprobaciones numéricas anteriores solo identifican
candidatos **provisionales**: no hay metadata suficiente para asegurar su papel
normativo. No se inventa mediante cláusulas ni se cambia el INCOMPLETE que el
motor asigna a esos resultados. Es el modo del contraejemplo aislado F-05.

`max` usa únicamente `check.dcr`, sin división de demanda/capacidad, sin consumir
`check_trace` y sin tolerancia nueva. Si dos DCR publicados son 1,000 y sus estados
son PASS y FAIL, ambos gobiernan observadamente; se conserva el FAIL. No se
recalcula estado a partir del DCR redondeado. F-09/HFS-015 siguen pendientes.
La traza detallada legacy que reconstruye razones/unidades no se usa para este
resumen ni se corrige en HFS-014; sigue bajo sus tareas de precisión/contratos.

### Migración JSON

Se eliminan del resumen anterior:

- `governing_capacity_kn_or_knm` (dimensionalmente ambiguo).
- `governing_clauses` y `governing_check_names` (listas paralelas sin índice).

Consumidores: leer `observed_governing_checks`, conservar cada `check_index`,
mostrar su DCR **publicado** y estado, y leer `overall_status`/coverage por
separado. La etiqueta de UI debe decir «gobernante observado de checks
ejecutados», especialmente cuando el caso sea INCOMPLETE. Una lista vacía se
presenta como «sin verificación resistente elegible», no PASS ni capacidad cero.
No depender de que haya exactamente un gobernante.

El nuevo `global_summary` del CLI y `output` es aditivo; el cambio dentro de
`memory.global_summary` es incompatible para quien leía los tres campos retirados.
Los tests ejercitan consumidores reales de CLI y memoria con y sin escritura.
No se modifica CheckResult ni EngineResult JSON del API interno `engine.run`.

## Lotes y errores

`aggregate_case_statuses` sigue siendo el único agregador de estados del lote.
`[]` lanza `ValidationError` de dominio con código `EMPTY_CASE_BUNDLE`:

```json
{
  "error": {
    "type": "ValidationError",
    "code": "EMPTY_CASE_BUNDLE",
    "stage": "run_engine",
    "message": "A case bundle must contain at least one case.",
    "details": {"field": "cases", "minimum_items": 1, "received_items": 0}
  }
}
```

CLI: stderr estructurado, exit 1, stdout vacío, sin `status` de cumplimiento y
sin crear directorio/memorias de resultados. Ocurre antes de ejecutar casos. La
carga previa de catálogo sigue igual; un error de catálogo puede preceder al de
entrada, sin ejecutar casos ni publicar memorias.

La mera presencia de `cases` activa el contrato de lote. `null`, objeto, cadena,
número o booleano no son lista: `INVALID_CASE_BUNDLE`, detalles con campo y tipo.
Se comprueba que **todos los elementos sean objetos** antes de ejecutar el primer
caso, también si el elemento inválido aparece después de uno válido. No se
convierte un `cases` mal tipado en un caso individual.

Este control no es una transacción completa de ejecución: un objeto de caso que
falle después por sus valores ingenieriles puede conservar memorias de casos
anteriores, como antes. Ese cambio general pertenece a otra tarea; no se oculta
el error de ejecución bajo FAIL resistente.

| Estados de un lote no vacío | Estado agregado |
|---|---|
| Todos PASS | PASS |
| Algún FAIL, ninguno INCOMPLETE | FAIL |
| Algún INCOMPLETE, incluso con FAIL | INCOMPLETE |

Los casos individuales, checks y `known_failures` permanecen en `cases`. Un
agregado INCOMPLETE no borra incumplimientos. La política F-32 se conserva:
lotes no vacíos ejecutados correctamente devuelven exit 0 incluso con FAIL o
INCOMPLETE. Leer el JSON; exit no es decisión resistente. HFS-014 no lo cambia.
