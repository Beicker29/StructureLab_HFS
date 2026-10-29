# HFS-030 — Auditoría documental de la base normativa

Fecha: 2026-10-29. **Entrega para revisión técnica**, sin autoevaluación ni nueva
acreditación normativa. Alcance final: cotejar exclusivamente los PDF locales,
incluidas las erratas AISC aportadas por el usuario durante la tarea.

## Resultado y verificación de entrada

**HECHO VERIFICADO:** `main`, SHA inicial
`76a908673259211b2d5b2407b046608ca96384ec`, sin cambios al iniciar la tarea
([captura](evidence/start.json)). Se leyeron AGENTS, ROADMAP, ADR-003,
tracking y contratos HFS-023/HFS-024. Se mantienen sus propietarios, 93 entradas
del registro y las trazas optativas, sin modificar el runtime.

La CI del SHA HFS-024 publicado se consultó antes de limitar las fuentes al
repositorio: run [40881966196](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40881966196),
jobs Ubuntu 24.04 `123475542163` y Windows 2022 `123475542580`, ambos **completed /
success** en la consulta final de jobs. La captura inicial conserva Windows en
curso; [la observación posterior](evidence/ci-observation.json) distingue ambos
momentos. Se verificó el resultado de los jobs; no se descargaron sus artefactos
ni se volvió a consultar el estado agregado final del run. La CI confirma esa
puerta de software de HFS-024, no cierre ingenieril de sus pendientes ni aprobación
humana de todas las formulaciones.

**HECHO VERIFICADO:** los dos PDF de erratas contienen 22 grupos de correcciones
y el PDF base conserva las versiones anteriores de todos ellos. Queda una base
documental reproducible: PDF original por hash **más** E25/E26 identificadas,
sin reemplazar originales ni crear un PDF consolidado aparentemente oficial.
Se contrastaron también referencias actuales del registro con disposiciones
locales relevantes para los hallazgos abiertos.

Entregables centrales:

- [Inventario de fuentes, hashes y jerarquía](sources.md).
- [Matriz completa de erratas, discrepancias y mapa de impacto](impact-matrix.md).
- [Snapshot de enlaces de las 93 entradas](evidence/registry-links.json), con
  propietarios, pruebas, referencias independientes y observaciones HFS-024.
- [Verificación real y reproducción](verification.md), con intentos fallidos
  de infraestructura preservados.

## Decisiones y hallazgos prioritarios

| Prioridad | Certeza y conclusión | Acción posterior, no ejecutada |
|---|---|---|
| **P0 abierto F-31** | HECHO: el cotejo B4/F2–F6 no proporciona resistencia mayor de canal fuera de F2. Ni las erratas ni trazar F6 cierran la omisión. | HFS-032: canal real, condiciones/anchos y oráculos de resistencia/cobertura por componente. |
| **P0 propuestos F-35/F-36** | HECHO documental: E7 exige Fn·Ae; código conserva QFy/Ag. E5 tiene condiciones y ramas que el helper de rama única no demuestra. INFERENCIA: potencial efecto de seguridad; no se calculó aquí una magnitud de error. | HFS-031 y revisión de consumidores H/I; no basta la regresión de software. |
| **P1 F-37** | HECHO: F3 y otros localizadores son incorrectos/incompletos; I3.MOMENT.ENCASED cita detalles constructivos en vez de la resistencia. H1-2 continúa siendo Pey. | Corregir metadatos con impacto explícito sobre snapshots/trazas; mantener IDs estables y no relabelar JSON legacy silenciosamente. |
| **P1 F-28/F-37** | HECHO: renumeración F7 e identificación Mn en F5; H1-2 corrige unidades Lb, I5-2 corrige Fysr. INFERENCIA: riesgo de auditorías/memorias que mezclen revisiones sin identificarlas. | Usar el par documento+errata al auditar cada ecuación, sin reemplazo global de símbolos o constantes. |
| **P1 preventivo F-28/F-38** | HECHO: K4.1A invierte un límite; I8.4d cambia sustancialmente rigidez métrica; Commentary térmico cambia unidades/expresiones. Fuera del cálculo implementado. | Conservar exclusiones. Resolver Fy/Fyb de K4.1A antes de implementar ese dominio. |
| **P2 F-28** | HECHO: hashes/procedencia local registrados. PENDIENTE: autenticación remota de bytes, historial completo de revisiones y permisos. | No declarar el repositorio sincronizado exhaustivamente con toda publicación AISC ni cerrar licencias por tener el PDF. |

No se detecta por este cotejo una necesidad demostrada de cambiar capacidades
debido únicamente a E25-01 o E26-03: el código ya denomina Mn al resultado de
fluencia de F5 y usa Fysr en csr. Esa observación **no** valida geometrías, límites,
factores ni métodos completos. El efecto numérico de las demás discrepancias
queda **PENDIENTE**, no se presume cero.

La aparente igualdad de expresiones no autoriza DRY entre capítulos: el 0,45 de
C3 no es el coeficiente de la curva corregida a 0,54; Fcr de un diagrama compuesto
no equivale a todo Fcr de E/F/H; una corrección K4 para una conexión HSS no cambia
H3 de miembros HSS. No se creó clasificador, motor, registro paralelo ni lógica
de selección. El script documental solo observa fuentes/metadatos y copia enlaces
de evidencia histórica; no modifica fuentes de verdad ni recalcula resultados.

## Incertidumbres y alcance conservado

**PENDIENTE:** E25-06 imprime Fy donde la base imprime Fyb. La inversión de la
desigualdad es inequívoca, pero no se impone una equivalencia de símbolos sin
revisión ingenieril. Las conversiones térmicas se registran tal como aparecen
en E26; no se completa silenciosamente una precisión o interpretación no dada.

**HIPÓTESIS:** atribuir un fallo del motor a una errata porque aparecen símbolos
parecidos. No se acepta esa causalidad sin un caso independiente y revisión del
recorrido real. Ninguna errata corrige automáticamente software.

Las 22 filas son exhaustivas respecto de las dos listas aportadas, no respecto
de los 780 folios, todas las publicaciones posteriores, sus implementaciones o
las 93 disposiciones registradas. Se distingue cita inventariada de pasaje
efectivamente cotejado. Los ejemplos auxiliares no se elevan a Specification;
AISC 341 conserva alcance independiente. F-19/20/22/23/28/30/33–38 y demás
pendientes no se cierran por este informe ni por pruebas verdes.

## Archivos y preservación

- Nuevos documentos: `docs/audit/hfs030/report.md`, `sources.md`,
  `impact-matrix.md`, `verification.md`.
- Nueva utilidad documental: `docs/audit/hfs030/reproduce.py`.
- Nuevas capturas: `docs/audit/hfs030/evidence/`, inventariadas con tamaños/hashes
  en [files.json](evidence/files.json). Incluyen fuentes, CI observada, registro,
  comandos, logs de cada suite e intentos de infraestructura.
- Actualizados únicamente como seguimiento vivo: `docs/ROADMAP.md` y
  `docs/audit/tracking.md`; se conservan los suplementos históricos.
- Incorporados **por el usuario**, sin edición por el agente:
  `errata_360-22_01232025.pdf`, `errata_360-22_09232026.pdf`.
- Sin modificación de `src/`, pruebas/oráculos, catálogo, schemas, contratos,
  trazas existentes, CLI, memorias, SVG históricos, PDF base o AISC 341.
  [Evidencia Git final](evidence/git-final.json).

Las salidas nuevas de pruebas bajo `results/` son artefactos de ejecución, no
cambios de producto. Se inventarían por ruta/hash y se trasladan, sin pérdida,
a `.venv/30-generated-results/` para no proponer su publicación; no se tocan
resultados históricos versionados ni directorios inaccesibles. El manifiesto
[generated-results.json](evidence/generated-results.json) permite localizar
los originales y sus destinos. No se borra evidencia ni se cambian permisos.

## Recomendación del siguiente hito

Presentar primero este cotejo y sus incertidumbres a revisión técnica. Después,
**HFS-031** es el siguiente hito recomendado por F-35/F-36 y su posible propagación
a H/I: usar la base identificada con sus erratas, construir oráculos independientes
y justificar dominios/áreas/condiciones antes de corregir fórmulas. La prioridad
P0 de F-31 exige mantener visible su auditoría HFS-032; no habilitar canales ni
cerrar cobertura mientras tanto. Si se exige una base autenticada contra el editor
o actualización exhaustiva, completar primero esa parte pendiente de F-28.

No se inicia HFS-031/032 ni interfaz web. No se realizan commits ni push. El
dictamen documental y cualquier cierre normativo permanecen sujetos a revisión
humana; no se asigna calificación.
