# HFS-013 — Corrección final F-43: método de diseño en Mc de H3/H1

2026-10-27. Base `main`, commit `abafdbbf0305ab489728d0eea5b81cdaf2e7e90c`,
sin cambios locales al comenzar. **Defecto corregido; cierre funcional demostrado
para revisión técnica.** Sin commit, push, ramas, PR ni otro hito.

Este suplemento actualiza el [informe HFS-013](../report.md) sin reemplazar sus
capturas ni afirmar validación normativa integral. La revisión independiente
del usuario identificó que `_available_flexural_strength` siempre aplicaba LRFD,
incluso en evaluaciones internas H3/H1 cuyo método declarado era ASD.

## Diagnóstico, norma y alcance del cierre

**F-43 confirmado:** para igual Mn, el código devolvía 0,90Mn en ASD, cuando
corresponde Mn/1,67. La capacidad anterior era **1,503 veces** la correcta
(exceso del 50,3% respecto a Mc ASD). Consecuentemente infravaloraba los cocientes
Mrx/Mcx y Mry/Mcy. La selección axial, de cortante y de torsión ya recibía el
método del caso; mezclarla con flexión LRFD producía interacciones inconsistentes.

Fuente primaria: **Specification** ANSI/AISC 360-22, August 1, 2022, **F1(a)**,
página impresa **16.1-52**, PDF **120** (1-based). Es la disposición de factores,
no la ecuación F1-1 de Cb. Documento local `a360-22w.pdf`, SHA-256
`25c4bf59b4c6fd00589e32a6ddac92cc9fd6be30dd5da07fc7c5f7fd475b2361`:

- LRFD: Mc = φb Mn, φb = 0,90.
- ASD: Mc = Mn / Ωb, Ωb = 1,67.
- Mn en N·mm se convierte a Mc en kN·m dividiendo entre 10⁶ tras aplicar el factor.

No se modifica Mn, clasificación, selección de estados límite, H3-6 ni ninguna
expresión H1. H3.2/H3-6, páginas 16.1-86–87/PDF154–155, remite las capacidades
Mcx/Mcy al capítulo F por método. H1.1, páginas 16.1-82–83/PDF150–151, también
utiliza las capacidades disponibles por método. No se convierte Commentary o
User Note en una obligación para esta decisión. Los valores de C de las sondas
siguen la User Note H3 identificada en la entrega anterior; aquí no se cambia C.
La limitación de cotejo integral de erratas F-28 sigue como en el informe previo.

### Recorrido completo comprobado

| Etapa / consumidor | Hallazgo y decisión |
|---|---|
| JSON/modelo `SteelCase.design_method` | Enum LRFD/ASD, default LRFD; parser y modelos se conservan |
| `SteelDesignEngine.run → validate_case` | **Rechaza Mux o Muy no nulos con ASD** antes del router. Este bloqueo existente se conserva; no se habilita Chapter F ASD completo |
| Router → H3/H1 | Las reglas internas pueden invocarse directamente sin pasar por `validate_case`; el router no transforma el método |
| H3.2 → `_available_flexural_strength` por x/y | Mantiene F7 rectangular/F8 circular y el Mn de cada eje; ahora transmite `case.design_method.value` al conversor canónico |
| H1 → `_compute_h1_interaction` → mismo helper | Recibe la misma corrección por ambos ejes, incluidas las ramas heredadas de compresión alta/baja y tracción |
| Capacidad axial D/E, cortante G y torsión H3 | Ya reciben método del caso; se preservan íntegros. Las sondas comprueban que no cambian |
| `flexure_rule._build_flexure_result` y `FlexureEvaluator` | Conservan el punto de entrada LRFD compatible. La habilitación pública ASD de Chapter F está fuera de esta corrección |
| HFS-010 | Plan, acreditaciones y agregación no cambian. En LRFD las sondas públicas siguen INCOMPLETE; en ASD con flexión siguen dando el mismo error de alcance |

Por tanto, la corrección cierra el factor incorrecto en el **evaluador compartido
interno**, no un error de cálculo ejecutado por el CLI actual para flexión ASD:
esa entrada pública ya estaba bloqueada. Se prueban ambos recorridos, sin
presentar una invocación directa de regla como cobertura del motor público.

## Implementación canónica y preservación

Solo dos archivos de runtime cambian:

1. `codes/aisc_360_22/flexure_calc.py`: función pura
   `available_flexural_strength(Mn_Nmm, design_method)`, reutilizando φb existente
   y declarando Ωb una sola vez. Rechaza métodos desconocidos, sin asumir ASD.
   `available_flexural_strength_lrfd` conserva su firma y delega al mismo código.
2. `domain/rules/combined_hss_rules.py`: sustituye una llamada LRFD fija por el
   conversor con el método del caso. No duplica factores en H3/H1 ni capacidades.

El orden aritmético LRFD sigue siendo exactamente `0.90 * Mn / 1e6` para evitar
variaciones de redondeo. ASD usa `Mn / 1.67 / 1e6`. No hay tolerancias nuevas en
producción, redondeo de capacidades antes de combinar, nuevas clases ni cambios
de contrato/traza. Los valores de Mc y los cocientes consecuentes cambian solo
cuando la evaluación interna es ASD y hay demanda en ese eje.

El [inventario DRY](../../../architecture/dry-inventory.md) registra propietario,
consumidores y alcance. F7 y F8 siguen separados: compartir F1(a) está justificado
por su aplicación a las disposiciones del capítulo F, no por parecido entre
sus ecuaciones nominales. Los factores numéricamente iguales de D/E/G/H3 no se
consolidan con F1.

## Oráculos independientes y diferencias antes/después

[73 pruebas nuevas](../../../../tests/test_hfs013_design_method.py), separadas de
las anteriores. Los esperados usan la norma y geometrías explícitas, no constantes
ni resultados del conversor productivo para construir el esperado.

| Geometría compacta y nominal independiente | Mcx LRFD conservado | Mcy LRFD conservado | Mcx ASD corregido | Mcy ASD corregido |
|---|---:|---:|---:|---:|
| Caja exterior 130×70×5 mm, A=1900 mm², Zx=79750/Zy=51250 mm³; F7-1 Mn=Fy·Z, Fy=320 MPa → 25,52/16,40 kN·m | 22,968 | 14,760 | 15,2814371257 | 9,8203592814 |
| Tubo OD=100/ID=90 mm, Zx=Zy=(100³−90³)/6 mm³; F8-1 Mn=14,4533333333 kN·m | 13,008 | 13,008 | 8,6546906188 | 8,6546906188 |

Las propiedades se obtienen por diferencia de rectángulos/círculos e integración
del módulo plástico. Caja: razones de pared 12/24 por debajo del límite de ala
compacta 1,12√(E/Fy)=28 y alma compacta; Lb=100 mm no reduce Mn. Circular:
D/t=20<0,07E/Fy=43,75 y dentro del dominio F8. F7-1 se identifica en
16.1-62–63/PDF130–131, F8-1 en 16.1-65/PDF133. Estas referencias acreditan los
nominales de las sondas compactas, no todas las ramas F7/F8.

Para reproducir las demandas se toman fracciones de capacidades **LRFD de
referencia**, iguales antes/después y entre métodos: Mux=0,4Mcx_LRFD,
Muy=−0,2Mcy_LRFD, Tr=0,35Tc_LRFD. Al añadir cortante:
Vux=0,10Vcx_LRFD y Vuy=−0,15Vcy_LRFD. En ASD, los cocientes correctos se
multiplican por r=0,90·1,67=1,503. Solo el cociente de flexión omitía ese cambio.
Usar las mismas demandas en ambos métodos aísla el defecto en estas sondas; no
constituye una conversión de combinaciones de carga LRFD a ASD. Su procedencia
normativa y los efectos del análisis siguen siendo responsabilidad externa.

H3 se contrasta para Mux solo, Muy solo, ambos, torsión, cortante+torsión y también
axial+ambos momentos+cortante+torsión, en ambas familias y ambos métodos.
Por ejemplo, biaxial con torsión sin cortante:

- LRFD: 0,6 + 0,35² = **0,7225**, sin cambio.
- ASD previo: 0,6 + (0,35·1,503)² = **0,8767286025** → PASS parcial incorrecto.
- ASD corregido: 0,6·1,503 + (0,35·1,503)² = **1,1785286025** → FAIL parcial.

H1 tiene regresiones de ambas ramas de compresión y de su expresión de tracción
heredada. Se usan Pc independientes: D2 para tracción con An=Ag/U=1; para las
sondas de compresión E3 gobierna, con Fe=π²E·ry²/Ly² y
Pn=0,658^(Fy/Fe)FyAg. Se verifica el efecto de F1 sobre Mc sin modificar Pc.
**La regresión de la expresión de tracción H1 no valida su fórmula/etiqueta H1-2:
F-37 permanece abierto.**

Resumen de las sondas ASD, igual patrón en ambas familias (DCR presentado a 3
decimales; los JSON conservan la memoria bruta):

| Sonda | DCR antes | DCR después | Estado de check |
|---|---:|---:|---|
| H3 Mux+Tu | 0,677 | 0,878 | PASS→PASS |
| H3 Muy+Tu | 0,477 | 0,577 | PASS→PASS |
| H3 Mux+Muy+Tu | 0,877 | 1,179 | PASS→FAIL |
| H3 Mux+Vux+Vuy+Tu | 0,965 | 1,166 | PASS→FAIL |
| H3 Muy+Vux+Vuy+Tu | 0,765 | 0,865 | PASS→PASS |
| H3 Mux+Muy+Vux+Vuy+Tu | 1,165 | 1,467 | FAIL→FAIL |
| H1 tracción+biaxial, Pr/Pc_LRFD=0,15 | 0,825 | 1,127 | PASS→FAIL |
| H1 compresión baja+biaxial, Pr/Pc_LRFD=0,10 | 0,675 | 0,977 | PASS→PASS |
| H1 compresión alta+biaxial, Pr/Pc_LRFD=0,25 | 0,909 | 1,177 | PASS→FAIL |

Evidencia: [antes](evidence/probes-before.json), [después](evidence/probes-after.json)
y [comparación completa](evidence/comparison.json). **36 sondas: 18 LRFD idénticas,
18 ASD internas con cambios, 8 PASS→FAIL parciales.** Todas conservan entradas,
nominales, capacidades ajenas a Mc y resultado público del motor. El
[comparador reproducible](compare.py) solo permite cambios de Mc, cocientes y
DCR/estado derivados en ASD; no es un oráculo numérico.

Tolerancias: Mc rel=1e−12/abs=1e−10 kN·m; Mn rel=1e−12/abs=1e−7 N·mm; razones
rel=abs=1e−12. Presentación a tres decimales: error absoluto máximo 0,0005 más
1e−12 por representación, separado del oráculo bruto estricto. Esto no altera
decisiones productivas ni aborda HFS-015. Compatibilidad LRFD se comprueba
también con igualdad exacta, sin tolerancia.

## Pruebas realmente ejecutadas

Windows, Python **3.12.10**, entorno `.venv/hfs000`. Dependencias/versión completa,
Git y comandos en [antes](evidence/before/environment.json) y
[después](evidence/after/environment.json): pytest 9.1.1, pydantic 2.14.1,
pydantic_core 2.50.1, openpyxl 3.1.5. No hubo instalación de dependencias.

| Suite | Base ejecutada | Final ejecutada | Fallidas / errores / omitidas ordinarias final |
|---|---:|---:|---|
| Original | 68 + 12 subpruebas | 68 + 12 subpruebas | 0 / 0 / 0 |
| Caracterización | 9 + 3 xfail | 9 + 3 xfail | 0 / 0 / 0 |
| HFS-011 | 665 | 665 | 0 / 0 / 0 |
| HFS-016 | 44 | 44 | 0 / 0 / 0 |
| HFS-010 | 57 | 57 | 0 / 0 / 0 |
| HFS-012 | 61 | 61 | 0 / 0 / 0 |
| HFS-013 direccional | 57 | 57 | 0 / 0 / 0 |
| HFS-013 método F1, nueva | No existía | 73 | 0 / 0 / 0 |

Final: **1034 aprobadas + 12 subpruebas + 3 xfail estrictos**, ocho suites con
exit 0. Los xfail siguen siendo F-05/F-09/F-29, sin cambios ni XPASS. JUnit
representa las subpruebas como registros y los xfail como skipped; no se cuentan
como métodos originales u omisiones ordinarias. [Verificación final](evidence/after/verification.json).

Los 12 ejemplos existentes se ejecutaron antes/después y son **idénticos
completos**, no solo en capacidad. Hash semántico:
`8b34cead811434c03119e0c456e9c70cd49ca555a8c17589013911a51d77f3d2`.
No se utiliza una tolerancia del comparador HFS-013 anterior para permitir cambios
LRFD/H1. En esta captura se exige igualdad literal de ejemplos.

### Reproducción y registro de incidencias

Desde la raíz, con Git en PATH y directorios nuevos (nunca sobre capturas):

```powershell
$env:PATH = 'D:\Users\byomayusa\AppData\Local\GitHubDesktop\app-3.6.7\resources\app\git\cmd;' + $env:PATH
# Base, ejecutado antes de editar runtime:
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs011.py --baseline docs/audit/hfs013/evidence/final/engine-results.json --out .venv/hfs013-f1-before --work .venv/hfs013-f1-before-work --extra-suite tests/test_hfs016_catalog_integrity.py --extra-suite tests/test_hfs010_coverage.py --extra-suite tests/test_hfs012_flexure_selection.py --extra-suite tests/test_hfs013_directional_h3.py
# Final, ocho suites separadas:
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs011.py --baseline docs/audit/hfs013/evidence/final/engine-results.json --out .venv/hfs013-f1-after --work .venv/hfs013-f1-after-work --extra-suite tests/test_hfs016_catalog_integrity.py --extra-suite tests/test_hfs010_coverage.py --extra-suite tests/test_hfs012_flexure_selection.py --extra-suite tests/test_hfs013_directional_h3.py --extra-suite tests/test_hfs013_design_method.py
# Sondas: el test nuevo se ejecuta como programa de captura; importa producción desde SOURCE_ROOT:
.\.venv\hfs000\Scripts\python.exe tests/test_hfs013_design_method.py .venv/hfs013-f1-before-work .venv/hfs013-f1-probes-before.json
.\.venv\hfs000\Scripts\python.exe tests/test_hfs013_design_method.py . .venv/hfs013-f1-probes-after.json
.\.venv\hfs000\Scripts\python.exe docs/audit/hfs013/f1-correction/compare.py .venv/hfs013-f1-probes-before.json .venv/hfs013-f1-probes-after.json .venv/hfs013-f1-comparison.json
```

El capturador fija PYTHONNOUSERSITE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1,
PYTHONUTF8=1 y retira PYTHONPATH; usa copia verificada por hash, `--basetemp`
nuevo y `-p no:cacheprovider`. Los logs `pytest-*.json` conservan comando/cwd,
exit, stdout y stderr; los XML identifican los casos. Se usó la escalación
aprobada para fixtures de Windows, sin cambiar permisos. Siguen registrados
los 31 directorios inaccesibles conocidos; no se limpian ni modifican.

Antes de corregir producción, los oráculos H3/H1 ejecutados con
`-k "h3_f1_oracle or h1_f1_regression"` reprodujeron **18 fallos ASD / 18 aprobadas
LRFD / 37 deseleccionadas**, exit 1 ([log](evidence/reproduced-red.json)). No se
añadió xfail al defecto. Una primera corrida había dado 19 fallos: el adicional
era una expectativa de redondeo en 0,5225 (0,522 frente a 0,523 por orden float).
Se ajustó exclusivamente la prueba de presentación a su resolución, conservando
el oráculo bruto estricto; [log inicial](evidence/initial-red.json). No se modificó
redondeo productivo ni F-09. Tras corregir F1, las 73 nuevas pasaron y se ejecutó
la captura completa anterior. No se modificaron expectativas de tests previos.

`scripts/audit_hfs013.py` se actualiza para separar también la octava suite en
futuras capturas. La ejecución final registrada aquí usó el comando explícito
`audit_hfs011.py` mostrado, con igualdad estricta; no se atribuye al wrapper una
ejecución que no se realizó.

## Git, archivos, evidencia y cierre

[Inventario completo de esta corrección](changed-files.md) y
[verificación de alcance](evidence/scope-verification.json). Git confirma solo
dos archivos de runtime modificados. Se preservan todos los cuerpos de
evaluación nominal F2–F11 y los demás módulos normativos; H1/H3 conservan sus
ecuaciones y consumidores excepto la llamada compartida F1. Catálogo, validación
pública, router HFS-012, cobertura HFS-010, resultados, CLI y tests anteriores
permanecen sin cambios. Runtime probado coincide con los hashes de la captura.

Las evidencias previas permanecen intactas. El informe principal recibe un enlace
al suplemento; su hash antiguo, incluido en el manifiesto previo HFS-013, se
recupera desde el commit `abafdbb` restaurando los finales de línea CRLF de la
captura Windows (Git guarda ese blob con LF). Se verifican ambos hashes y la
restauración exacta. **No se reescribe ese manifiesto histórico**.
El manifiesto nuevo [SHA256SUMS.json](evidence/SHA256SUMS.json) identifica este
suplemento y los archivos revisables actuales. Los resultados de ejemplos
idénticos se reutilizan en su ruta canónica, indicada con hash en
[reused.json](evidence/reused.json), sin duplicarlos ni borrar capturas locales.

F-43 queda corregido y con cierre funcional demostrado: factor por método,
oráculos independientes y efecto compartido en H3/H1. Su prioridad histórica
propuesta P0 permanece trazable: el bloqueo público mitiga exposición, pero las
reglas internas podían dar capacidades excesivas y checks PASS incorrectos.
La revisión ingenieril del cierre sigue pendiente del usuario. No implica
acreditar íntegramente H1, F7/F8, dominios H3 o nuevas obligaciones HFS-010.
F-31, F-37 y demás pendientes conservan su estado. No se implementan HFS-014/015
ni se amplía el catálogo o la habilitación pública ASD.
