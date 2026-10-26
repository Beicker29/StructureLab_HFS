# ADR-001 — Un motor, fronteras simples y DRY

Fecha: 2026-10-26. Tarea: HFS-001. Estado: decisión propuesta para revisión técnica; implementación posterior, sin cambios de runtime en esta tarea.

## Problema

El motor ya separa funciones en `codes/aisc_360_22`, reglas y routing en `domain`, y catálogo en `sections`. HFS-000 demuestra puntos de aislamiento útiles, pero también geometría duplicada, capacidades recalculadas para interacciones y un CLI que reconstruye parte del cálculo. Mover todos los componentes al árbol del roadmap no elimina esos problemas; añadir `services`, `adapters` y una capa de servicios web puede producir más delegaciones sin responsabilidad propia.

Evidencia y propietarios por concepto: [inventario DRY](../architecture/dry-inventory.md). Diagnóstico original: [inventario HFS-000](../audit/inventory.md). La corrección física de las capacidades sigue pendiente.

## Alternativas

1. Mantener todo: menor costo inmediato, conserva las duplicaciones y facilita otro motor en la web.
2. Adoptar íntegro el árbol objetivo y trasladar reglas a `codes`: organización uniforme, pero gran superficie de cambio, imports rotos y separación ambigua entre funciones y selección.
3. Evolucionar el monolito Python por responsabilidades demostradas, conservando ubicaciones útiles y una entrada común. **Elegida.**

Se descartan microservicios y un framework de plugins: no hay necesidad de despliegues independientes ni extensiones externas acreditada. Tampoco se crea una interfaz abstracta para un único proveedor solo por anticipar otro.

## Decisión

**DRY permanente:** cada concepto técnico tiene un propietario canónico; no cada expresión corta una abstracción. Mantener las ecuaciones puras por capítulo en `codes/aisc_360_22`, las reglas que construyen verificaciones en `domain/rules`, el registro/aplicabilidad en `domain/routing` y las propiedades/importación en `sections`. No trasladar masivamente reglas a `codes` ni renombrar `sections` a `catalog`.

`SteelDesignEngine.run` es la entrada canónica actual de cálculo. El objetivo futuro es que la ejecución normalizada (incluido el lote, sin fórmulas) y la agregación se invoquen igual desde CLI y API. Extraer de `run.py` solo las funciones de aplicación reutilizadas cuando corresponda HFS-021; no añadir un servicio encima de otro que solo reenvíe llamadas. La web futura será un adaptador HTTP y presentación, sin `steel_design_web/services.py` obligatorio.

Dirección de dependencias objetivo:

```text
CLI / API / web -> ejecución común -> validación + selección + reglas
                                           reglas -> funciones AISC
importador -> Section normalizada -> motor -> resultado y traza -> presentación
```

Los modelos compartidos no importan interfaces. `codes` no importa CLI, HTTP, archivos o renderizadores. La selección decide qué evaluar; la regla usa una evaluación de capacidad con eje, método, aplicabilidad y traza; el reporte consume esos datos sin recalcularlos. Las capacidades compartidas entre checks e interacciones se consolidarán por concepto validado, no leyendo resultados ya redondeados ni disparando recursivamente todo el motor.

Separar geometría custom en una función pura dentro de `sections` cuando se autorice su extracción; CLI debe consumir la misma sección que el cálculo. Una función simple basta, sin fábrica genérica. La forma definitiva de un módulo de capacidades se elegirá por los consumidores reales, dentro de las responsabilidades actuales; no se crea una capa adicional en HFS-001.

Se conservan Pydantic y excepciones de dominio. No duplicar modelos para cada interfaz ni imponer una segunda jerarquía de entidades por purismo. Los modelos futuros ampliados requieren la transición del [ADR-002](002-contracts-errors.md).

## Justificación

Conservar estas fronteras permite mejorar cobertura sin reescribir los seis módulos normativos. Extraer geometría elimina divergencia entre cálculo y reporte; compartir evaluaciones evita recalcular resistencias con distintos fallbacks; separar presentación evita reconstruir estados y unidades. Cada extracción tiene consumidores y un defecto/riesgo concreto, no solo menos líneas.

DRY tiene una excepción deliberada: un cálculo independiente de referencia no debe reutilizar las funciones productivas. Tampoco se unifican E3/I2, factores de capítulos distintos o F4/F5 por parecido: la equivalencia normativa no está demostrada.

## Consecuencias

El árbol del roadmap pasa a ser ilustrativo, no una lista de carpetas obligatorias. No habrá nuevas carpetas de producción vacías, repositorios abstractos, DI, caches globales o servicios HTTP todavía. Se podrá extraer `reporting` cuando tenga funciones reales; FastAPI queda como candidato del hito web, sin dependencia instalada ahora.

Conservar un nombre o módulo no implica conservar sus defectos: routing, contratos y resultados se corregirán por tareas propias. La política DRY no autoriza sustituir resultados ni cambiar una ecuación durante una extracción.

## Riesgos y verificación futura

Una evaluación común puede propagar un error a más consumidores; exigir pruebas por consumidor, dominio, eje y estado límite, además de oráculos independientes cuando afecte cálculo. La extracción gradual deja duplicación temporal: mantenerla visible en el inventario y no añadir nuevas copias. Cuidado con ciclos entre modelos/reglas y con reutilizar capacidades válidas para otro método o condición. Cada refactorización debe mostrar comparación antes/después y rollback local.

En HFS-001 se verifica únicamente coherencia documental, integridad de runtime y reproducibilidad de la suite. No se construye el plan normativo de HFS-002 ni se cambia el routing de HFS-010.
