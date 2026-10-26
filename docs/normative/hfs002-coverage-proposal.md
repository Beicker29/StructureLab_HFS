# HFS-002 — Propuesta concreta para HFS-010

Diseño documental, sin implementación de nuevos estados, routing o contratos. Fuentes: [matriz N](hfs002-applicability.md), [contraste](hfs002-implementation.md), ADR-002/003. Mantener un motor y contratos comunes para CLI/API/web.

## Dos conjuntos con autoridad diferente

1. **Requisitos normativos esperados**: nacen de la matriz revisada por ingeniería, identificada por versión/hash de norma y revisión de errata. No importar `RULE_DEFINITIONS`, `PROFILE_RULE_MAP`, predicados del router ni salidas del motor para construirlos. La independencia es de derivación y revisión, no otro motor de capacidades. En HFS-010 bastan tablas y predicados pequeños revisados; sin DSL ni framework.
2. **Evaluaciones disponibles/ejecutadas**: registro actual de implementación, ampliado con vínculos a requisitos. Describe lo que sabe hacer el motor; nunca define por sí solo lo que exige el caso. Un check interno puede cubrir parte de N y una N puede requerir varios checks.
3. El motor compara ambos conjuntos. Las interfaces consumen el mismo resultado y la misma explicación, sin otro selector ni recomputación.

No mantener dos matrices normativas editables: esta matriz es fuente documental durante revisión; una eventual representación estructurada revisada reemplazaría su contenido editable y generaría sus vistas. **Nunca** generar la norma desde los metadatos del router. El mapa N→implementación sí puede tener una vista generada, señalada como tal. Los oráculos de selección permanecen independientes de los predicados productivos.

## Identidad mínima y decisión de cobertura

Clave de obligación futura: `(N-ID, estado_límite, eje/componente, signo relevante, combinación, posición/segmento, etapa, método, alternativa)`. No basta contar checks ni comparar prefijo `F` o `I3`. Registrar cita (documento, edición, errata, cláusula/ecuación/página), condición, entradas requeridas con origen/unidad, dependencias de capacidades y resultado de la decisión de aplicabilidad.

| Estado de la condición/evaluación | Acción futura |
|---|---|
| Condición falsa con evidencia suficiente | NOT_APPLICABLE y razón técnica; un cero explícito puede excluir una demanda, no todas sus condiciones |
| Condición desconocida | NOT_EVALUATED, lista de datos/estudio faltantes; caso INCOMPLETE |
| Obligatoria pero sin implementador o fuera del método/dominio soportado | NOT_EVALUATED, `unsupported`; INCOMPLETE |
| Obligatoria con error técnico/no finito | Error estructurado y obligación no evaluada; no FAIL resistente ficticio ni PASS |
| Ejecutada pero no cubre eje/etapa/estado requerido | Mantener check como evidencia parcial; obligación pendiente |
| Implementada pero validación independiente exigida para alcance publicitado ausente | Marcar `unvalidated`; impedir afirmar cumplimiento de ese alcance. No confundir ejecución con validación |
| Exclusión externa declarada y compatible con las hipótesis internas | Enumerar fuera del alcance, con evidencia externa cuando sea precondición; no certificar ese aspecto |
| Exclusión que afecta una capacidad asumida o que el usuario solicita incluir | No quitarla del denominador para lograr PASS; INCOMPLETE |

Los límites de producto deben ser visibles antes y después de ejecutar. No crear automáticamente un «alcance verificable» igual a los checks que aparecieron. Debe ser una selección explícita, versionada y aprobada, con exclusiones que no invaliden sus capacidades. Sin definición suficiente del caso/alcance, INCOMPLETE.

Agregación objetivo: falta una obligación o validación exigida → INCOMPLETE conservando cualquier FAIL; cobertura completa y fallo resistente → FAIL; cobertura completa, no vacía y sin fallos → **PASS del alcance verificable declarado**. Un lote vacío no acredita cumplimiento. No se anuncia certificación global AISC 360-22. Una advertencia D1/E2 no es un estado límite incumplido; E5≤200 tiene otra semántica.

Las alternativas se modelan como grupos `una ruta completa requerida`, no como todos los checks obligatorios: G2.1 frente campo de tracción; H1 frente H2 cuando permitido; I4.1 acero solo/RC/acero+refuerzo; I5 según clase. Si se elige una ruta se conservan motivo, factores y dependencias. Una capacidad interna calculada para interacción puede reutilizarse sin otro motor, pero debe emitir evidencia de lo que cubre; no aceptar la cuantía I3-3 como resistencia I3.3.

## Escenarios de aceptación a desarrollar en HFS-010

| Caso | Conjunto esperado independiente | Resultado exigido si soporte actual no cambia |
|---|---|---|
| Cargas vacías/typo/NaN | Definición del caso inválida o pendiente antes del plan | Error/INCOMPLETE, jamás PASS |
| W con compresión+Mx | E aplicable, F por clase, interacción N29 y precondiciones | INCOMPLETE por interacción no cubierta |
| W/HSS con Mx+My, Pu=0 | Flexión por eje + combinación N29 | INCOMPLETE si solo hay checks aislados |
| Canal no compacto mayor + menor | Dos componentes independientes; N16 solo satisface menor | INCOMPLETE por mayor no soportado |
| Datos de compactación ausentes | N02 pendiente; rama F no decidida | No inferir F2 |
| HSS con T y dos cortantes | N25/26 y N30; elegir máximo de cocientes por eje | No usar capacidad del eje no demandado para cubrir otro |
| Compuesto con flexión pura | N39/40/43 según rol; no confundir ecuación de cuantía y sección de flexión | INCOMPLETE aun si I1 y cuantía/transferencia pasan |
| 2L sin detalle de ensamblaje | N05/N09 según signo y condiciones | INCOMPLETE cuando detalle es precondición |
| ASD con flexión o compuesto | Requisito normativo existe, implementador actual no soporta método | Bloqueo explícito, nunca N/A |
| Resultado FAIL parcial y falta otra obligación | Ambos hechos conservados | INCOMPLETE global con FAIL visible |

Pruebas futuras: conjuntos esperados escritos desde la matriz por revisión independiente; eliminar deliberadamente una regla/alterar su gating debe producir obligación faltante. Cubrir fronteras de clase, signos, ejes y alternativas. Regresión de HFS-000 por separado; correcciones deseadas documentadas, nunca cambiar snapshots para ocultarlas. Cambios de capacidad requieren oráculos numéricos externos/manuales revisados y tolerancias por magnitud. Esta propuesta no añade esos tests ni activa HFS-010.

HFS-016 queda separado: identidad ambigua de catálogo impide construir una Section confiable **antes** del plan. Rechazo/identificación acotados deben revisarse antes de G1; no implementar limpieza masiva ni resolver filas dudosas mediante renombrado automático.
