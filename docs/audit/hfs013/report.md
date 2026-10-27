# HFS-013 — Ejes, demandas direccionales e interacción H3

Entrega para **revisión técnica**, 2026-10-27. Base `main`, SHA
`3af52aa9848ccb6ff040fd1f8203a4609599f341`, inicialmente sin cambios locales.
HFS-012 incorporada según el usuario. No se hace commit, push, rama ni PR.
HFS-000 sigue siendo línea base de comportamiento, no validación AISC.

## 1. Diagnóstico y decisiones

F-06 se confirma: H3 dividía la mayor demanda de cortante por la mayor capacidad,
que podían pertenecer a paredes distintas. Se corrige a máximo de **cocientes
emparejados por plano**. Además, la lectura de Specification identificó dos
errores en las fórmulas existentes: el término normal de H3-6 estaba al cuadrado
y el coeficiente elástico de H3-5 era 4,58 en vez de 0,458π². Se corrigen dentro
del alcance H3 autorizado. Las funciones/factores D/E/F/H1/I no se modifican.

Se mantienen parciales y pendientes las evaluaciones cuyas condiciones completas
no están acreditadas. Ningún check G/H3 obtiene nueva acreditación de cobertura
global por estas correcciones. PASS de un check no certifica AISC 360-22.

| Decisión | Evidencia / motivo | Comportamiento implementado |
|---|---|---|
| Conservar asociación histórica de cortante, aclarando física | Vux ya consumía alma/pared h, Vuy alas/pared b. Con z longitudinal, una fuerza y produce flexión alrededor de x y una fuerza x, alrededor de y | Sufijo Vux/Vuy = plano de Mux/Muy; fuerza local y/x respectivamente. No permutar valores por sus nombres |
| Vu es alias escalar del primer plano | HFS-011 ya había eliminado resultante/sobrescritura; G y router interpretaban Vu como cortante mayor | Fuente compartida de demandas; nunca calcular √(Vux²+Vuy²). Las representaciones activas contradictorias siguen rechazadas |
| H3-6 conserva pares por eje y término normal lineal | Specification H3.2, ecuación H3-6 | `Pr/Pc + Mrx/Mcx + Mry/Mcy + (max(Vrx/Vcx,Vry/Vcy)+Tr/Tc)^2` |
| H3-5 corrige coeficiente y dominio | Specification H3.1(b), ecuaciones H3-3/4/5 | Última rama `0.458*pi²*E/(h/t)²`, solo hasta h/t=260. h es el lado plano mayor |
| G4/G5 comparten capacidad con H3 | Las copias anteriores divergían en geometría, longitud y selección de máximo | Un evaluador bruto, sin consumir CheckResult redondeado. Cada componente activa pide su propia capacidad |
| No reconstruir C rectangular desde planos+3t | B4.1b(d) permite aproximar ancho plano desde exterior si falta radio; no demuestra la operación inversa como geometría exacta | C explícita en mm³, h/b planos y tdes obligatorios. Sin C, bloquear H3 conservando G4 ejecutable |
| No sustituir C circular por 2J/D | H3 define C; User Note proporciona aproximación conservadora con D/t explícitos | C declarada o `π(D−t)²t/2`. J no acredita C; argumento conservado por compatibilidad de llamada |
| No inventar Lv o L | G5 define Lv como distancia de cortante máximo a cero; H3.1 circular define L como longitud física del miembro | No usar Lx/Ly ni KzLz. Sin datos dedicados se bloquea la rama dependiente, salvo prueba matemática de fluencia independiente de la longitud |
| No convertir el umbral 20% en check PASS | H3.2 permite alternativa H1, no define una resistencia del tipo Tr/(0,2Tc) | Tr/Tc≤0,20 deja diagnóstico de alternativa H1/G pendiente; no se implementa otra interacción en este hito |
| Bloquear direcciones no acreditadas | G3 necesita el ala que resiste la fuerza; una b/t no acredita ambas direcciones ni reparto de doble ángulo. G6 canal no acredita distribución por ala | G3 y G6 canal bloqueados. G6 W conserva dos alas iguales y exige ausencia de torsión; datos de ala ausentes no borran G2 ejecutable |
| Conservar verificaciones independientes | Faltante de pared/C o torsión no HSS antes podía impedir todo el caso | Validación de G3/G4/G5/G6/H3 dentro de su regla; errores en `coverage.evaluation_errors`. Torsión no HSS y cortante macizo quedan pendientes sin eliminar checks independientes |

La [convención canónica](../../contracts/hfs013-axes.md) define todas las entradas,
signos, ejes, unidades y migración. Pu>0 es compresión; Pu<0 tracción. Mux/Muy/Tu
son kN·m; Vux/Vuy/Vu/Pu son kN. Se conservan signos de entrada y se usan magnitudes
positivas para G/H3; no se deduce el signo de equilibrio de una cara de corte.
Un adaptador que llame Vx a una **fuerza x** debe mapearla expresamente a Vuy.
Esta aclaración exige revisar interpretaciones históricas de usuarios externos.

## 2. Fuentes normativas y límites de la revisión

Fuente primaria local: `a360-22w.pdf`, ANSI/AISC 360-22, *Specification for
Structural Steel Buildings*, August 1, 2022. SHA-256:
`25c4bf59b4c6fd00589e32a6ddac92cc9fd6be30dd5da07fc7c5f7fd475b2361`.
Las páginas PDF siguientes son **1-based**. Se extrajo texto y se inspeccionaron
las ecuaciones renderizadas, especialmente H3-5/H3-6, cuyo orden de símbolos se
pierde en extracción textual. No se versiona otra copia del PDF ni sus PNG.

| Fuente | Página impresa / PDF | Aplicación en HFS-013 |
|---|---|---|
| Specification B4.1b(d); B4.2 | 16.1-22 y 24 / 90 y 92 | Ancho plano y espesor de diseño; no invertir la aproximación de esquinas |
| Specification G1, G2.1, G2.2 | 16.1-75–77 / 143–145 | Factores de cortante y Cv; G2 se conserva, su validación integral no se afirma |
| Specification G3/G4, G3-1/G4-1 | 16.1-80 / 148 | Ala resistente del ángulo, Aw=2ht, kv=5 para HSS rectangular |
| Specification G5, G5-1/2a/2b; G6, G6-1; G7 | 16.1-81 / 149 | Circular: Vn=FcrAg/2; Lv; cortante por ala sin torsión; aberturas pendientes |
| Specification H3.1, H3-1/2a/2b | 16.1-85 / 153 | Tn=Fcr·C; circular usa longitud real L, no longitud efectiva |
| Specification H3.1(b), H3-3/4/5 | 16.1-85–86 / 153–154 | Tres ramas de Fcr rectangular y límite 260 |
| **User Note** tras H3.1 | 16.1-86 / 154 | C circular/rectangular conservadoras. Alternativas expresas; no requisito de usar una geometría reconstruida |
| Specification H3.2, H3-6 y definiciones | 16.1-86–87 / 154–155 | Umbral 20%, cocientes por eje, capacidades de D/E/F/G, expresión lineal+cuadrática |
| **User Note** tras H3-6 | 16.1-87 / 155 | Convención positiva de términos; no autoriza mezclar ejes |

No se usa Commentary como obligación adicional. Las etiquetas de software
`H3-1`/`H3-2` identifican reglas; la interacción resistente cita ahora
explícitamente **ecuación H3-6**. H3.3 no HSS es una sección, no ecuación H3-3.

Consulta complementaria: la [errata oficial de enero de 2025](https://www.aisc.org/globalassets/aisc/publications/revisions-and-errata/errata_360-22_1st-printing_01.23.2025.pdf)
no enumera correcciones G/H3. El [índice oficial de erratas](https://www.aisc.org/aisc/publications/revisions-and-errata/)
también anuncia septiembre de 2026; **no se declara cotejada integralmente esa
revisión**. F-28 permanece abierto. La edición local y las referencias anteriores
son la fuente efectivamente contrastada, no una afirmación de cobertura de todas
las erratas ni de todos los requisitos AISC.

### Longitudes circulares desconocidas

G5 usa `max(1.60E/[sqrt(Lv/D)*(D/t)^1.25], 0.78E/(D/t)^1.5)`, limitado a 0,6Fy.
H3 circular usa coeficientes 1,23 y 0,60 y longitud L distinta. Si la segunda
rama ya alcanza el límite, `min(max(a(L),b),c)=c` para todo L>0 cuando b≥c.
Esta identidad acredita fluencia sin conocer L/Lv; no es asumir longitud cero,
infinita o el valor de otra longitud. Si no se cumple, Fcr queda no disponible
y se registra el dato requerido. No se añaden campos nuevos en este hito.

## 3. Oráculos independientes y diferencias intencionales

Los esperados están en [test_hfs013_directional_h3.py](../../../tests/test_hfs013_directional_h3.py).
Se calculan desde ecuaciones citadas y geometrías explícitas, sin llamar a la
producción para obtener el esperado. La igualdad G/H3 compartida prueba DRY,
pero no se confunde con el oráculo normativo independiente.

| Referencia | Resultado independiente / propósito |
|---|---|
| Caja 200×100×5 mm, planos h=190/b=90, E=200000/Fy=320 MPa | G4 LRFD Vcx=328,32 kN, Vcy=155,52 kN; ASD usa 1/1,67. Se ensayan Vux, Vuy, ambas, Vu y signos negativos |
| Demandas 0,4Vcx y 1,2Vcy | Primer plano PASS, segundo FAIL; emparejar segunda fuerza con Vcx daría falso PASS |
| Caja compacta 130×70×5 mm, h=120/b=60 | Diferencia de rectángulos: A=1900 mm², Zx=79750/Zy=51250 mm³; D2 gobierna Pc=547,2 kN y F7 da Mcx=22,968/Mcy=14,76 kN·m para el caso corto declarado |
| Caso completo de esa caja | Pu=−109,44 kN, Mux=3,4452/Muy=0,738 kN·m, Vux=82,944/Vuy=62,208 kN, Tu=0,5Tc. Normal=0,40; corte máximo=0,60; torsi=0,50. Correcto: 0,40+1,10²=**1,61**; previo: 0,40²+0,90²=**0,97** |
| Misma caja, solo corte+torsión | DCR H3 **0,81→1,21**, atribuible solo a F-06; capacidades G4/Tc se conservan |
| Solo expresión H3-6, normal=0,4 y corte+torsi=0,9 | 0,97→1,21, atribuible solo al término normal (F-39) |
| H3 rectangular E/Fy=625 | Límites 61,25/76,75; fluencia 192 MPa; a h/t=100: **91,6→90,40557631397853 MPa**. En 260: 13,550295857988166→13,373605963606291 MPa; >260 bloqueado |
| Tubo OD=100, tdes=5, A=475π mm² | G5 LRFD Vc=128,9309625 kN en ambos planos por simetría. C de User Note=π95²5/2; Tc≈12,2484414 kN·m; antes 2J/D daba ≈11,6682521. Pruebas independientes de Kz/Lz/J |
| Circular D/t=100, longitudes explícitas solo en funciones puras | L/Lv=500 mm: G5/H3 Fcr=192 MPa. L/Lv=5000000 mm: G5=156, H3=120 MPa; coeficientes y dominios no fusionados |
| Circular D=1000, t=2 | Sin L/Lv reales, G5 y H3 pendientes; las antiguas capacidades dependían de longitudes de pandeo no equivalentes |
| Catálogo PTE50X30X2.5MM asimétrico | h=43,025/b=23,025/tdes=2,325 mm transcritos como referencia; oráculo G4 por plano, demanda desigual. Sin C, H3 bloqueado; esto no certifica la procedencia/calidad del catálogo |

Se ensayan también 20% y valores superiores, H3 h/t=260 y superior, falta de
C/espesor/pared, W con torsión, canal, ángulos y macizo, así como la conservación
del cortante de alma si faltan datos de ala. Tolerancias de oráculos: relativas
hasta 1e−12 y absolutas 1e−9 kN / 1e−10 MPa para aritmética, según prueba;
algunos cocientes usan `pytest.approx` por defecto (rel=1e−6, abs=1e−12). No se
introducen tolerancias en clasificación/decisión productiva. Salidas redondeadas
se contrastan a su resolución; las interacciones consumen valores brutos.

Las [sondas](probes.py) ejecutan **entradas idénticas** contra el código previo y
el final; [antes](evidence/probes-before.json) y [después](evidence/probes-after.json)
conservan entradas, salidas, capacidades, DCR y errores completos. No son el
oráculo. El caso `threshold_20_percent_independent_float` ilustra una frontera:
el orden de operaciones del oráculo deja Tr un ULP por encima de 0,2Tc calculado
por producción, por lo que ejecuta H3-6; no se oculta con epsilon. El caso 10%
queda bloqueado. Las pruebas de frontera contrastan el límite representable;
la política general de precisión permanece pendiente HFS-015.

### Los 12 ejemplos existentes

Se ejecutaron realmente antes y después. El [comparador](../../../scripts/compare_hfs013.py)
conserva exactos los checks D/E/F/H1/I, estado global y contenido de obligaciones
(salvo explicación/índices de checks); registra todos los cambios G/H3. No permite
nuevo PASS. [Comparación completa](evidence/final/hfs013-comparison.json).

| Ejemplo | Diferencia |
|---|---|
| W | G2/G6 añaden trazas de ejes; capacidades y DCR sin cambio |
| HSS rectangular | G4 conserva números. Se retiran H3-1 (Tc=1,134; DCR=0,705) y H3-2 (DCR=7,013): C no está acreditada; errores explícitos y obligaciones pendientes. Un antiguo FAIL calculado con datos no acreditados no se presenta como resistencia válida |
| HSS circular | H3 combinado DCR **0,831→0,950** por término normal lineal; trazas G/H3 actualizadas. Global sigue INCOMPLETE |
| Otros nueve | Sin diferencias de resultados de ejemplo |

El JSON previo es idéntico al canónico HFS-010 (HFS-012 no lo alteró), hash de
bytes `d4ffba78e13fb18feb16b198e0f071c950ef4af4ce0102c0675cdbea643e0ea2`.
Los hashes semánticos del capturador son 584c52… antes y 8b34ce… después;
no confundirlos con hash de bytes. No se reescribe ninguna captura anterior.

## 4. Pruebas ejecutadas y reproducción

Windows, Python **3.12.10**, `.venv/hfs000/Scripts/python.exe`. Dependencias
completas y comando/cwd/exit/stdout/stderr en [entorno final](evidence/final/environment.json)
y `pytest-*.json`/XML. Principales: pytest 9.1.1, pydantic 2.14.1,
pydantic_core 2.50.1, openpyxl 3.1.5. No se instalaron dependencias.

| Suite separada | Antes | Final | Fallidas / errores / omitidas ordinarias final |
|---|---:|---:|---|
| Original | 68 métodos + 12 subpruebas | 68 métodos + 12 subpruebas | 0 / 0 / 0 |
| Caracterización HFS-000 | 9 aprobadas + 3 xfail | 9 aprobadas + 3 xfail | 0 / 0 / 0 |
| HFS-011 contratos | 665 | 665 | 0 / 0 / 0 |
| HFS-016 catálogo | 44 | 44 | 0 / 0 / 0 |
| HFS-010 cobertura | 57 | 57 | 0 / 0 / 0 |
| HFS-012 selección | 61 | 61 | 0 / 0 / 0 |
| HFS-013 nueva | No existía | 57 | 0 / 0 / 0 |

Total final: **961 aprobadas + 12 subpruebas + 3 xfail estrictos**; todas las
suites exit 0. JUnit cuenta las 12 subpruebas en los 80 registros originales y
clasifica xfail como skipped: no son 80 métodos ni 3 omisiones ordinarias.
F-05 (mínimo de dimensiones distintas), F-09 (FAIL/DCR redondeado=1) y F-29
(lote vacío PASS) conservan reproducción y `xfail(strict=True)` sin cambios.
No hay XPASS. No se implementan HFS-014/015 para eliminarlos.

Comandos de capturas, desde raíz; Git debe estar en PATH:

```powershell
$env:PATH = 'D:\Users\byomayusa\AppData\Local\GitHubDesktop\app-3.6.7\resources\app\git\cmd;' + $env:PATH
# Ejecutado antes de editar, sobre SHA base:
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs011.py --baseline docs/audit/hfs010/evidence/after/engine-results.json --out .venv/hfs013-before --work .venv/hfs013-before-work --extra-suite tests/test_hfs016_catalog_integrity.py --extra-suite tests/test_hfs010_coverage.py --extra-suite tests/test_hfs012_flexure_selection.py
# Ejecutado sobre código final, directorios nuevos:
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs013.py --baseline .venv/hfs013-before/engine-results.json --out .venv/hfs013-final --work .venv/hfs013-final-work
# Sondas, contra copia previa conservada y checkout actual:
.\.venv\hfs000\Scripts\python.exe docs/audit/hfs013/probes.py .venv/hfs013-before-work .venv/hfs013-probes-before-v2.json
.\.venv\hfs000\Scripts\python.exe docs/audit/hfs013/probes.py . .venv/hfs013-probes-after-v2.json
```

Para reproducir después, usar rutas de salida nuevas y el código base desde Git
en un checkout/copia aparte; no cambiar el main de trabajo ni sobrescribir
evidencia. El baseline puede apuntar directamente al JSON HFS-010 canónico.
El capturador aísla copia y fixtures, fija PYTHONNOUSERSITE=1,
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONUTF8=1, retira PYTHONPATH y ejecuta
`python -m pytest -q -ra --tb=short -p no:cacheprovider --basetemp=... --junitxml=...`.
La suite original excluye los seis archivos de las otras suites, que ejecuta
individualmente. Los comandos completos quedan en cada log.

El resultado literal heredado `verification.json` indica `examples_identical=false`
y `regression_accepted=false`, **esperados por las correcciones autorizadas**.
No se suprimen: el wrapper añade [hfs013-verification.json](evidence/final/hfs013-verification.json)
con tests, invariantes y comparación compatibles, y exit 0. Esta aceptación
automática es de la ejecución/comparación definida, no aprobación ingenieril.

### Incidencias y expectativas modificadas

- Primera ejecución dirigida tras cambios: **4 fallidas / 67 aprobadas**, exit 1,
  [registro](evidence/incidents/initial-targeted.json). G3 y G6 canal esperaban
  capacidad; dos tests H3 usaban C inferida o PASS de umbral. Se sustituyen por
  expectativas de bloqueo fundamentadas arriba. El test de umbral declara C
  sintética explícita para aislar esa condición; los oráculos nuevos validan
  resistencias reales por ecuación. No se altera el histórico de la base.
- Primera corrida nueva: 3 fallidas / 49 aprobadas. Se corrigió una hipótesis del
  **fixture** (la caja grande no era compacta como ala en flexión menor), usando
  caja 130×70×5 con límites comprobados; no se cambió F7. La frontera 61,25
  requería dos `nextafter` para superar el límite 61,25000000000001 calculado en
  float. La tercera falla mostró validación global de pared ausente: se movió
  la comprobación de G4/G5/H3 al evaluador para preservar la otra pared. Esta
  incidencia se conserva narrativamente del transcript; no se inventa un log.
- Primera captura completa posterior: solo HFS-010 falló (**56/1**); un test
  suponía H3 ejecutado aun sin C. Ahora exige diagnóstico `missing_fields=[c]`,
  ninguna ejecución N30 y global INCOMPLETE. [Log](evidence/incidents/initial-hfs010.json)
  y [resumen](evidence/incidents/initial-verification.json).
- Captura intermedia [after](evidence/after/hfs013-verification.json): siete
  suites verdes con 55 pruebas nuevas. Revisión posterior añadió dos regresiones
  de datos de ala ausentes y validación por regla G3/G6. Se repitieron 128 pruebas
  dirigidas (exit 0) y todas las suites en `final`; no se usa la captura intermedia
  como verificación del código final.
- Un pytest directo de las 55 pruebas pasó con advertencia WinError 5 al crear
  caché. Capturas finales deshabilitan la caché. Los intentos iniciales bajo
  sandbox encontraron restricciones de fixtures; se ejecutaron las capturas
  mediante escalación aprobada, sin cambiar ACL ni borrar carpetas históricas.
  No se marcaron errores de infraestructura como xfail. Los directorios con
  problemas de acceso ya inventariados en HFS-000 siguen sin tocarse.
  También quedó `pytest-cache-files-93oft8sd/`, temporal nuevo del pytest directo:
  `rg` informa acceso denegado. Se clasifica como caché generada no inspeccionada;
  no se elimina ni se modifica su ACL. No forma parte del código ni de la evidencia
  promovida a Git.

## 5. Cobertura, DRY, archivos y pendientes

HFS-010 conserva plan independiente, IDs y condiciones de acreditación. Solo se
actualizan dos razones explicativas G/H3. El motor agrega diagnósticos de
resistencias ausentes y reutiliza su canal existente de errores parciales; no
hay otra arquitectura de cobertura ni alcance definido a partir del router.
Los FAIL de checks válidos siguen visibles en `known_failures`. Si no se puede
ejecutar un check por datos/dominio, no se inventa una capacidad cero ni un FAIL
resistente: queda pendiente y el caso INCOMPLETE.

DRY: `domain/actions.py` es fuente de demanda/traza por plano para router/G/H3;
`domain/evaluators/hss_shear.py` es fuente de G4/G5 y sus dos consumidores, reglas
G y H3. Las fórmulas puras permanecen en `codes`. Se retiran copias de capacidades
y fallbacks, sin clasificador nuevo, clases/servicios genéricos o motor paralelo.
[Inventario DRY actualizado](../../architecture/dry-inventory.md).

Inventario completo de archivos y comprobación Git en
[changed-files.md](changed-files.md) y [final-verification.json](evidence/final-verification.json).
Los cambios de runtime se limitan a cargas descritas, G/H3, helpers compartidos y
su integración. Se preservan por Git/hash las fórmulas D/E/F/I, reglas axiales,
flexión, tensión y compuestos, catálogo, PDFs, modelos de resultados, validación,
selector HFS-012 y sus 61 pruebas. Las funciones H1/capacidades D/E/F internas de
`combined_hss_rules.py` se comprueban sin cambios. No se presenta el motor entero
como intacto: **G/H3 sí cambian intencionalmente**.

Evidencia: se conservan nuevos logs, XML, sondas y resultados revisables; no se
versionan entornos, copias de trabajo ni imágenes de lectura. El baseline previo
duplicado se resuelve en [reused-evidence.json](evidence/reused-evidence.json) a
su ruta canónica recuperable y hash; no se elimina el original. Manifiesto del
conjunto en [SHA256SUMS.json](evidence/SHA256SUMS.json). Las capturas históricas
HFS-000/010/011/012/016 permanecen intactas.

Pendientes prioritarios para revisión, sin implementar otro hito:

1. Revisar la convención declarada con los consumidores y la ingeniería de cada
   modelo. No se acredita orientación de ángulos, centro de cortante, carga fuera
   de centro, aberturas G7, sección real ni análisis/estabilidad del capítulo C.
2. F-06 se corrige en agregación; Pc/Mc heredadas D/E/F, H1, dominios circulares,
   cortante circular oblicuo sin torsión y métodos completos requieren auditoría
   posterior. Con flexión, el motor sigue limitado a LRFD; no habilitar ASD por
   invocar directamente una regla interna.
3. Revisar/representar Lv, longitud real L, geometría exterior/procedencia de C y
   espesor de diseño. No completar datos artificialmente. Casos antes calculables
   quedan bloqueados deliberadamente.
4. H3 con Tr/Tc≤20% necesita alternativa H1/G acreditada; G3 y G6 canal necesitan
   entradas y distribución justificadas. F-31 sigue **abierto P0**: aquí no se
   implementa ni valida la resistencia mayor del canal. F-03/HFS-012 conservan
   selector y regresiones; no se declaran solucionados por modificar G.
5. Revisar prioridades propuestas F-39/41/42 P0 y F-40 P1 en
   [tracking](../tracking.md). El exceso ~1,32% de la antigua rama H3-5 no se
   considera aceptable; su prioridad distingue impacto acotado de mezclas/fallbacks
   potencialmente grandes. F-28 erratas, F-05/09/29 y riesgos numéricos extremos
   permanecen abiertos.

Solo HFS-013 ejecutada. Sin HFS-014/015, web, cambios de catálogo, migración masiva,
commit ni publicación. La revisión técnica humana de decisiones y referencias
queda pendiente; los resultados de pruebas no la sustituyen.
