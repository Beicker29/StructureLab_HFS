# Reglas de trabajo de StructureLab_HFS

## Alcance y fuentes

- Ejecutar solo la tarea autorizada del [roadmap](docs/ROADMAP.md). Leer sus criterios y los ADR pertinentes antes de editar. No avanzar de fase por iniciativa propia.
- HFS-000 es línea base de comportamiento, no validación AISC. Sus informes y capturas son históricos; el estado vivo de defectos está en [seguimiento](docs/audit/tracking.md).
- Las decisiones HFS-001 se describen en [ADR-001](docs/adr/001-engine-architecture.md), [ADR-002](docs/adr/002-contracts-errors.md) y [ADR-003](docs/adr/003-traceability-testing.md). No confundir diseño futuro con funciones implementadas.
- Antes de trabajar, registrar rama/SHA y cambios locales. Preservar trabajo del usuario y evidencia. No ejecutar limpiezas o cambios de permisos para ocultar errores de acceso.

## DRY, simplicidad y responsabilidades

- **DRY (Don't Repeat Yourself) es permanente: cada concepto técnico tiene una fuente de verdad.** El objetivo es impedir divergencias, no reducir líneas. Consultar el [inventario DRY](docs/architecture/dry-inventory.md) y actualizarlo cuando cambie la responsabilidad canónica.
- CLI, API y futura web deben llamar al mismo motor y usar los mismos contratos. Ninguna interfaz calcula capacidades, selecciona estados límite, corrige cargas o decide cumplimiento por su cuenta.
- El transporte versionado optativo tiene un único propietario: `steel_design.contracts` ([HFS-022](docs/contracts/hfs022-versioned-json.md)). Reutilizar modelos Pydantic, preparación y decisiones canónicas; no versionar modelos ingenieriles ni migrar JSON legacy implícitamente. Regenerar/verificar esquemas con `scripts/generate_hfs022_schemas.py --check` y constraints fijadas; nunca editar los JSON generados a mano ni aceptar deriva de campos calculados/cobertura. Distinguir versión de distribución, contrato, cobertura y edición AISC.
- La preparación pura tiene un solo propietario, `steel_design.preparation`; `execution` conserva sus reexports comprometidos. Contratos no deben importar ejecución, motor, router, reglas, CLI o presentación ni consultar archivos de aplicación. Conservar las guardas en sus propietarios canónicos. Comprobar esta frontera en procesos nuevos y los diez esquemas congelados con `jsonschema` Draft 2020-12, exclusivamente de desarrollo; la aceptación de un esquema no sustituye la validación Python.
- El único paquete soportado es `steel_design` (src-layout, HFS-021A). No importar `src.steel_design`, duplicar modelos ni crear aliases en `sys.modules`. Usar instalación editable para desarrollo y las rutas explícitas de la [API pública](docs/contracts/hfs021a-public-api.md); conservar referencias antiguas solo en evidencia histórica, pruebas de rechazo o identificadores JSON históricos preservados por compatibilidad (no importables).
- Conservar funciones y módulos pequeños cuando resuelvan el problema. Añadir una clase, servicio o interfaz solo si elimina duplicación semántica, separa I/O de cálculo o resuelve una dependencia concreta; documentar el beneficio y sus consumidores.
- No fusionar ecuaciones por igualdad visual, constantes coincidentes o parecido algebraico. Exigir equivalencia de norma, dominio, unidades, factores y estados límite. Si difieren, conservar funciones y trazas separadas.
- Una refactorización DRY requiere mapa de usos, pruebas antes/después y procedencia de resultados. Si afecta cálculos o aplicabilidad, requiere además referencias numéricas independientes y revisión ingenieril. Separar la corrección normativa del movimiento de código.
- Evitar microservicios, motores paralelos, contenedores obligatorios, registro genérico de plugins, base de datos y dependencias sin necesidad demostrada. No migrar carpetas por estética.

## Limpieza incremental obligatoria

- En cada sustitución, revisar consumidores antes de retirar código: llamadas/imports, accesos dinámicos, pruebas, scripts, entry points y compromisos documentados. Registrar símbolo, propietario canónico, decisión, motivo y riesgo dentro del hito autorizado.
- Eliminar en ese mismo hito el código muerto demostrado; si existe un impedimento, documentarlo y fijar la condición de retiro. Aplicar DRY conservando una sola implementación por concepto, sin mantener copias sustituidas ni código solo porque alguna vez fue necesario.
- Una fachada de compatibilidad exige un consumidor vigente o un compromiso explícito identificable. Los nombres privados no constituyen automáticamente API pública. Tampoco basta el nombre, la antigüedad o la ausencia de llamadas estáticas para autorizar una eliminación.
- Toda eliminación debe preservar el comportamiento comprometido y superar la regresión pertinente antes/después según la sección de verificación. Investigar qué protege una prueba que consume una fachada; no eliminarla ni relajarla para facilitar la limpieza.
- Conservar evidencia histórica, oráculos independientes y documentos normativos conforme a la política de evidencia. Los cambios normativos o numéricos requieren tareas y validaciones independientes; no presentarlos como limpieza interna.

## Exactitud y evidencia normativa

- Para cambiar una regla, identificar edición, artículo/ecuación, condiciones y unidades. Distinguir Specification, Commentary, User Note, ejemplo auxiliar e inferencia. No convertir una nota o una hipótesis en obligación sin justificarlo.
- No afirmar validación normativa a partir de smoke tests, positividad de capacidades, cobertura de líneas o comparación del motor consigo mismo.
- Mantener `float` salvo necesidad numérica demostrada; decisiones con valores brutos, redondeo solo para presentación. Declarar tolerancias absolutas/relativas por magnitud y justificar límites. No introducir tolerancias que cambien PASS/FAIL sin revisión.
- No comparar capacidades de dimensiones distintas. Preservar eje, signo, método LRFD/ASD, origen del dato y unidad. No asumir compacto, cero, finitud o geometría válida por ausencia de datos.
- El objetivo es que ausencia de verificaciones o cobertura incompleta nunca se presente como PASS. Los defectos actuales deben seguir visibles; no alterar el motor fuera de una tarea autorizada para corregirlos.
- PASS expresa cumplimiento únicamente del alcance verificable declarado, con hipótesis y exclusiones explícitas; nunca certificación global automática AISC 360-22. No definir ese alcance retrospectivamente como los checks que el router ejecutó.
- La [matriz normativa independiente](docs/normative/hfs002-applicability.md) define requisitos desde las fuentes; el [contraste](docs/normative/hfs002-implementation.md) registra soporte del código. No derivar la matriz ni los esperados independientes desde `ProfileRouter`, sus predicados o sus resultados. Incertidumbre de aplicabilidad no equivale a NOT_APPLICABLE.

## Verificación y cambios

- Seguir [CONTRIBUTING.md](CONTRIBUTING.md): separar suite original y caracterización; registrar entorno, comandos, exit, aprobadas, fallidas, omitidas, errores y xfail. Distinguir métodos y subpruebas.
- No editar expectativas congeladas para hacer pasar un cambio. Documentar diferencias por caso/cláusula; las correcciones deseadas sustituyen expectativas con evidencia, nunca borran el histórico.
- `known defect` debe referenciar un F-ID y tener reproducción. Mantener `xfail(strict=True)` y acotar excepciones; un XPASS exige investigar y actualizar el test/seguimiento tras confirmar la corrección. No marcar como xfail errores de infraestructura ni nuevos fallos sin diagnóstico.
- Para cambios documentales verificar enlaces, coherencia y ausencia de cambios de runtime; no añadir tests que solo reflejen la redacción. Para cambios de comportamiento ejecutar pruebas dirigidas y regresión pertinente, sin introducir herramientas de CI ajenas a la tarea.
- Preservar capturas según la [política de evidencia](docs/audit/evidence-policy.md). No sobrescribir HFS-000 ni borrar PDFs, catálogos o históricos. Documentar archivo, hash, destino recuperable y justificación antes de proponer exclusión/eliminación.
- Cerrar cada tarea con diagnóstico, decisión, archivos modificados, pruebas reales, diferencias numéricas, riesgos y pendientes. No declarar aprobada una arquitectura o validación ingenieril que aún espera revisión humana.
