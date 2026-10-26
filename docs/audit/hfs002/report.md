# HFS-002 — Entrega para revisión técnica

Fecha: 2026-10-26, America/Bogota. Base: `main`, `2b96da7cfa160932f78f9501de80d573a6704786`; inicio sin cambios versionados, con avisos de acceso a temporales históricos. HFS-000 fue aceptada como comportamiento reproducible y HFS-001 como arquitectura. Se incorporan los tres ajustes documentales acordados. **No se modifican fórmulas, motor, router, contratos, resultados productivos ni datos. No se implementan HFS-010/016 ni tareas posteriores.**

## Entregables y decisiones

| Entregable | Contenido y uso |
|---|---|
| [Fuentes](../../normative/hfs002-sources.md) | PDF local por hash/edición; páginas impresas y físicas; Specification, Commentary y User Notes diferenciados; erratas pendientes |
| [Matriz de aplicabilidad](../../normative/hfs002-applicability.md) | 45 IDs N, familias × demandas × condiciones, entradas, métodos, alternativas y límites. Derivada de S22, no de las reglas del motor |
| [Comparación y riesgos](../../normative/hfs002-implementation.md) | Las 45 filas contrastadas con código, inventario de familias/configuraciones, implementación frente a validación, revisión F-01/03/06/31 y F-33–38 |
| [Cobertura futura](../../normative/hfs002-coverage-proposal.md) | Conjunto requerido independiente frente al ejecutado; claves por componente/etapa/posición, razones y alternativas; comportamiento futuro ante falta de datos/soporte/validación |
| [Seguimiento maestro](../tracking.md) | Todos los hallazgos abiertos; F-13 vinculado a HFS-016 antes de G1; prioridades/evidencia nuevas |
| [Inventario DRY](../../architecture/dry-inventory.md) | Fuentes independientes de requisitos y soporte; DRY-17–20, vínculos normativos y condiciones de consolidación futura |

Los ADR aprobados precisan que PASS acredita solo el **alcance verificable declarado**, no certificación global automática de AISC. El alcance no se puede reducir retrospectivamente a lo que el código ejecutó. La independencia normativa no exige un motor paralelo: exige derivar requisitos y esperados desde fuentes distintas del selector bajo prueba. Se conserva arquitectura simple, registro ejecutable actual y motor único.

Discrepancias/acotaciones al roadmap: «todos los huecos» no puede significar cobertura exhaustiva de AISC con solo esta lectura; se identifican ramas pendientes, referencias externas y erratas no cotejadas. No se habilitan familias/métodos por tener una ecuación parecida. El nombre `I3-3` no prueba cobertura de la sección I3.3; tampoco una etiqueta E7-1 valida su método. La mitigación de falsos PASS debe bloquear dominios incompletos en HFS-010 sin esperar la reparación profunda de HFS-031–038. HFS-016 queda **planificada**, no ejecutada.

## Hallazgos prioritarios

- **F-01/03/31 permanecen P0:** interacción fuera de HSS, selección F2 sin prueba de compactación y omisión mayor oculta por F6. Las caracterizaciones se reprodujeron. Se precisaron dominios H1/H2 y F2/F6; F-31 sigue siendo sonda sintética, sin validación física de un canal real.
- **F-06 P0:** H3.2 exige máximo de cocientes por eje. El cociente de máximos independientes no es equivalente: ejemplo aritmético 0,5 frente a 0,25. Se confirma discrepancia de selección, no una capacidad física independiente ni todas sus consecuencias.
- **F-33 P0 propuesto:** biaxialidad con Pu=0 puede ejecutar solo checks uniaxiales; sonda W nueva conserva PASS sin H.
- **F-34 P0 propuesto:** los tres roles compuestos ejecutados con flexión pura Mx=1 y 1 000 000 kNm conservan PASS sin check resistente de momento. Cuantías/transferencia no satisfacen I3.2/3/4. Se conservaron entradas y resultados completos en [probes.json](probes.json).
- **F-35/36 P0 propuestos:** E7 QFy/Ag frente a área efectiva de S22; E5 rama única y condiciones incompletas. Son contrastes estáticos confirmados en alcance de método/dominio; conservadurismo y error numérico por perfil siguen pendientes de oráculos. No se cambian ecuaciones.
- **F-37/38 P1:** referencias de ecuación confundidas con IDs internos y verificaciones/precondiciones complementarias ausentes. Cada falta que afecte el alcance solicitado deberá bloquear cobertura; no se declara segura por estar asignada P1.

F-19 se precisa sin prejuzgar reparación: la User Note F4 sí menciona diseño conservador con F5; eso no acredita que esta implementación y sus hipótesis reproduzcan la alternativa correctamente. F-07 distingue recomendaciones D1/E2 de la condición obligatoria de elegibilidad E5. Ningún hallazgo se cierra.

## Pruebas realmente ejecutadas

Entorno de pruebas: `.venv/hfs000/Scripts/python.exe`, **Python 3.12.10**, pytest **9.1.1**, pydantic **2.14.1**, pydantic_core **2.50.1**, openpyxl **3.1.5**. Freeze completo, comando con rutas absolutas, cwd, stdout/stderr, exit y resumen JUnit en cada captura enlazada. Sin instalaciones ni cambios de dependencias. Se copió la superficie versionada de fuentes/tests/ejemplos/catálogo a `.venv/hfs002-review/work`, comprobando hashes antes de ejecutar. Overrides: `PYTHONNOUSERSITE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONUTF8=1`; PYTHONPATH heredado retirado.

| Ejecución | Aprobadas | Fallidas | Omitidas ordinarias | xfail / XPASS | Errores | Exit / evidencia |
|---|---:|---:|---:|---:|---:|---|
| Original, independiente de caracterización | 68 métodos + 12 subpruebas (80 JUnit) | 0 | 0 | 0 / 0 | 0 | 0; [original-tests.json](original-tests.json); 31,96 s consola |
| Caracterización, intento con temporal global | 0 | 0 | 0 | 10 / 0 | 1 de setup | 1; [characterization-tests.json](characterization-tests.json); WinError 5 |
| Caracterización, temporal local nuevo en sandbox | 0 | 0 | 0 | 10 / 0 | 1 de setup, más excepción al finalizar limpieza de temporales | 1; [characterization-local-tests.json](characterization-local-tests.json) |
| Caracterización, repetición autorizada fuera del sandbox, otro temporal nuevo | 0 | 0 | 0 | **11 / 0** | **0** | **0**; [characterization-authorized-tests.json](characterization-authorized-tests.json); 3,26 s |
| Sondas HFS-002 | 7 ejecuciones del motor + 1 contraste algebraico; no son pytest ni pruebas de capacidad normativa | — | — | — | 0 | 0; [probes.py](probes.py), [probes.json](probes.json) |

Los 11 xfail mantienen `strict=True, raises=AssertionError`; JUnit los representa como `skipped`, pero no se cuentan como omisiones ordinarias. Los errores de infraestructura no se convierten en xfail. Cada ejecución pytest emitió la advertencia conocida `Section.Config` obsoleta en Pydantic. No se modificaron expectativas ni archivos de tests.

Comandos efectivos (rutas exactas en JSON; `python` designa el intérprete fijado):

```powershell
# cwd: .venv/hfs002-review/work
python -m pytest -q -ra --tb=short -p no:cacheprovider --ignore=tests/test_hfs000_characterization.py --junitxml=<temporal>/original.xml
python -m pytest -q -ra --tb=short -p no:cacheprovider tests/test_hfs000_characterization.py --junitxml=<temporal>/characterization.xml
# Segundo/tercer intento añaden --basetemp con destinos NUEVOS distintos:
# .venv/hfs002-review/pytest-fresh y .venv/hfs002-review/pytest-authorized
# y JUnit characterization-local.xml / characterization-authorized.xml.
# Sondas, cwd raíz:
python -m docs.audit.hfs002.probes
```

La suite original ejecutó los **12 ejemplos existentes** mediante `test_examples_smoke.py`: 11 producen JSON con exit 0 y 2L produce el error estructurado esperado. Eso verifica ejecución, no que todos sean PASS de diseño. No se regeneraron capturas HFS-000 ni se hizo una nueva comparación numérica exhaustiva contra sus fixtures. Las sondas nuevas usan copias de entradas en memoria y no sobrescriben ejemplos. No se ejecutaron lint/tipos ni un banco nuevo de oráculos de capacidad; no sería correcto presentarlos como realizados.

## Integridad, accesos y evidencia

[verification.json](verification.json) registra SHA base, hashes antes/después, `git diff --check`, estado Git y `git diff --exit-code HEAD -- src tests scripts data examples requirements.txt`. Este último produjo **diff vacío y exit 0**: incluye motor, router, modelos y ecuaciones. Se comprobaron 196 archivos versionados al inicio: únicamente cambiaron los siete documentos indicados abajo. Los 90 hashes de los dos manifiestos HFS-000 coinciden. También se comprobaron 69 enlaces locales sin roturas y correspondencia exacta de los 45 N-ID entre matrices. `git diff --check` terminó sin errores; conserva avisos de normalización LF/CRLF. La igualdad de archivos no equivale a validación normativa.

Persisten 30 directorios históricos no versionados inaccesibles ya clasificados en HFS-000: 10 bajo `.tmp_test/` y 20 bajo `tests/.tmp_tests/`. Los avisos Git se conservan; no se cambian ACL ni se borra contenido. Nuevos accesos fallidos: temporal global `D:/Users/byomayusa/AppData/Local/Temp/pytest-of-byomayusa` y temporal local regenerable `.venv/hfs002-review/pytest-fresh` creado por pytest en sandbox; se preservan sin reintentar su limpieza. El último ensayo usó un destino nuevo y autorización para ejecución fuera del sandbox. No hubo rechazo de auto-review.

Capturas de HFS-002 son evidencia de esta revisión. Extracciones de PDF, imágenes de lectura, copia de ejecución, JUnit y auxiliares de captura en `.venv/hfs002-reading/`, `.venv/hfs002-review/`, `.venv/hfs002_verify.py` quedan ignorados y regenerables. Ninguna exclusión/borrado nuevo ni limpieza de evidencia histórica. Los únicos programas añadidos al entregable son sondas de auditoría de lectura, sin conexión al runtime productivo.

## Inventario completo de archivos entregables

| Archivo | Estado / finalidad |
|---|---|
| `AGENTS.md` | Modificado: alcance de PASS e independencia normativa |
| `docs/ROADMAP.md` | Modificado: acuerdos, HFS-016 antes de G1, estado y seguimiento nuevo |
| `docs/adr/001-engine-architecture.md` | Modificado: aprobación y separación requisito/implementación |
| `docs/adr/002-contracts-errors.md` | Modificado: PASS acotado y propietarios de requisitos/soporte |
| `docs/adr/003-traceability-testing.md` | Modificado: matriz independiente, sin generación circular |
| `docs/architecture/dry-inventory.md` | Modificado: propiedad normativa y DRY-17–20 |
| `docs/audit/tracking.md` | Modificado: revisión de hallazgos y seis IDs nuevos |
| `docs/normative/hfs002-sources.md` | Nuevo: registro documental/localizadores/incertidumbres |
| `docs/normative/hfs002-applicability.md` | Nuevo: matriz normativa canónica |
| `docs/normative/hfs002-implementation.md` | Nuevo: familias, contraste, riesgos y evidencia |
| `docs/normative/hfs002-coverage-proposal.md` | Nuevo: mecanismo futuro, sin implementación |
| `docs/audit/hfs002/probes.py` | Nuevo: sondas reproducibles de solo lectura |
| `docs/audit/hfs002/probes.json` | Nuevo: entradas/salidas y contraejemplo algebraico |
| `docs/audit/hfs002/original-tests.json` | Nuevo: suite original real |
| `docs/audit/hfs002/characterization-tests.json` | Nuevo: primer intento/error preservado |
| `docs/audit/hfs002/characterization-local-tests.json` | Nuevo: segundo intento/error preservado |
| `docs/audit/hfs002/characterization-authorized-tests.json` | Nuevo: caracterización completa |
| `docs/audit/hfs002/verification.json` | Nuevo: prueba Git/integridad y control documental |
| `docs/audit/hfs002/report.md` | Nuevo: este informe |

Total: **7 preexistentes modificados, 12 nuevos**; sin commits ni cambios del índice. HFS-000 y el informe/capturas históricos HFS-001 se conservan intactos; las nuevas decisiones se registran en documentos vivos.

## Pendientes para revisión

1. Revisar la matriz y prioridades F-33–38; aceptar/corregir dominios y exclusiones. No se solicita aprobación para una reparación implícita.
2. Cotejar erratas oficiales en HFS-030: el índice oficial enumera entregas posteriores al PDF local, pero la apertura directa devolvió 403 y no se examinó su contenido. No afirmar vigencia completa de la edición corregida.
3. Resolver canal mayor fuera de F2, macizos a cortante, 2L por eje/ensamble, ejes físicos HSS/ángulos, biaxialidad compuesta y precondiciones externas. Caso desconocido debe seguir incompleto, no completarse con una hipótesis silenciosa.
4. Preparar oráculos independientes por capacidades/dominios en las tareas autorizadas; F-31 aún requiere canal real. F-06 solo dispone aquí de contraejemplo algebraico, no capacidad validada.
5. HFS-010 y HFS-016 quedan pendientes de autorización posterior; no se abre web, no se migra código y no se corrige ninguna ecuación en esta entrega.

HFS-002 queda presentada como matriz y diagnóstico **para revisión técnica**, con incertidumbres explícitas. No se afirma cobertura normativa exhaustiva ni aprobación ingenieril automática.
