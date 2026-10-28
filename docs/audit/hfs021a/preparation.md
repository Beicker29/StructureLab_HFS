# Preparación y mapa HFS-021A

2026-10-28: `main`, HEAD `39a7614a413a06eef78f597e142f7ba0e889c123`,
sin cambios locales antes de iniciar. Se preservan las advertencias de acceso
a temporales históricos, sin limpieza ni cambios de permisos.
Leídos AGENTS, CONTRIBUTING, ROADMAP, ADR-001/002/003, contrato HFS-021 y
política de evidencia. Usuario aprueba HFS-021; GitHub confirma Windows y
Ubuntu SUCCESS en run 40687160912 (jobs 122812372184 y 122812371832).

## Consumidores y plan previo a editar runtime

[Inventario por archivo/línea](consumer-inventory.json): 208 referencias en
36 archivos operativos; incluye rutas físicas que **no** deben migrarse.
Los documentos históricos de audit/contracts/ADR/normative se preservan.

| Consumidor | Decisión |
|---|---|
| Productivo `src/steel_design/**/*.py` | Conservar ubicación física e imports relativos. Añadir inicializadores a los 8 paquetes reales; ninguna implementación ingenieril cambia |
| `tests/test_*.py` | Cambiar exclusivamente prefijos de imports y comandos modulares/dinámicos. Oráculos, escenarios, aserciones y conteos históricos intactos |
| `audit_baseline`, `audit_hfs011`, `audit_hfs014_cli`, sondas y debug | Import convencional. Capturas explícitas de fuentes añaden su `root/src` al path; capturas de instalación no contienen fuentes y resuelven site-packages. Nunca fallback a import legado |
| `verify_hfs020` | Sigue siendo el verificador CI común. Inspeccionar wheel sin src, sdist con src-layout, metadata sin versión fija, instalaciones normal/wheel/editable, API/imports e identidades |
| `hfs020_comparison` | Conservar íntegro: autoridad de comparación JSON exacta y procedencia de entradas |
| `compare_hfs021` | Verificador de extracción histórica anclado a f3a5198; mantener esa verificación reproducible contra Git, sin exigir bytes actuales a tests cuyo único cambio es imports |
| README/CONTRIBUTING | Instalar editable para desarrollo; comandos convencionales y retirada explícita del comando legado |
| pyproject/MANIFEST/CI | Versión 0.2.0, setuptools where=src, namespaces=false, entry point convencional. MANIFEST conserva rutas físicas; CI conserva matriz y ejecuta el verificador ampliado |

Decisiones: API explícita por módulos (sin reexports masivos ni ciclos),
`__init__` raíz sin imports ni efectos salvo rechazo `__name__ != steel_design`.
Así el namespace implícito `src` del checkout no puede inicializar un segundo
motor. No aliases sys.modules, segundo paquete, nueva capa ni dependencia.

Línea base iniciada con fuentes aprobados mediante
`scripts/verify_hfs020.py --out .venv/21abefore`, antes de cambios productivos.
Se conservarán logs, instalaciones, wheel/sdist, 1762 pruebas +12 subpruebas,
12 ejemplos, 24 consumidores y SVG. El contraste posterior comprobará igualdad
exacta y AST con transformación limitada al prefijo de imports/ejecución.
Los snapshots no se actualizan. HFS-022/023/024 y web fuera de alcance.
