# Reglas de trabajo de StructureLab_HFS

## Alcance

- El repositorio implementa solo el capítulo E de ANSI/AISC 360-22. No añadir
  otros capítulos sin una tarea autorizada de la [hoja de ruta](docs/ROADMAP.md).
- Fuente normativa: `a360-22w.pdf` y las erratas del repositorio. Alcance,
  decisiones y consultas abiertas: [docs/chapter-e.md](docs/chapter-e.md).
- Antes de trabajar, registrar rama/SHA y cambios locales. No borrar trabajo del
  usuario ni archivos no versionados desconocidos; no cambiar permisos.
- Sin commit ni push salvo autorización.

## Arquitectura

- Una fuente de verdad por concepto ([arquitectura](docs/architecture.md)):
  fórmulas en `codes/aisc_360_22/compression.py`; clasificación y selección en
  `domain/compression.py`; obligaciones independientes en `domain/coverage.py`.
- Las interfaces (CLI, web) llaman a `engine`/`execution`; nunca calculan capacidades.
- No fusionar ecuaciones por parecido algebraico; exigir equivalencia de norma,
  dominio, unidades y estado límite.
- No añadir clases, servicios, registros o dependencias sin necesidad demostrada.
- Eliminar el código sustituido en la misma tarea; sin fachadas sin consumidores.

## Exactitud normativa

- Para cambiar una regla, identificar artículo/ecuación, condiciones y unidades;
  distinguir Specification, User Note y Commentary.
- No suponer valores (Cw, J, H, compacidad, conexiones) por ausencia de datos:
  bloquear con error estructurado (`INCOMPLETE`).
- Una decisión que AISC 360-22 no resuelve inequívocamente se consulta al usuario
  (problema, referencia, alternativas, consecuencias, recomendación) y se registra
  en `docs/chapter-e.md`.
- `PASS` solo para el alcance declarado, con todas las obligaciones cumplidas.
- `float` en el cálculo; redondeo solo para presentación.

## Verificación

- Seguir [CONTRIBUTING.md](CONTRIBUTING.md). Cambios de cálculo requieren casos en
  el oráculo independiente `tests/oracles/chapter_e.py` (no importa el paquete).
- No modificar valores de referencia para hacer pasar un cambio.
- Cerrar cada tarea con: cambios, pruebas reales (comando y resultado), diferencias
  numéricas, riesgos y pendientes.
