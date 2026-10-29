# HFS-031 — Auditoría normativa D/E

Fecha: 2026-10-29. **Para revisión técnica independiente.** Base `main`,
`05198f06a63f8405bd96ffbe494be796cdb165e4`; árbol inicial limpio.
No se autoasigna calificación ni se declara aptitud global AISC.

## Dictamen

**No es posible demostrar corrección integral de D/E con la implementación
actual.** Se verifican las fórmulas elementales D2/D3-1, factores LRFD/ASD,
E3 bajo ejes principales completos y E4 de doble simetría por centro de corte.
Se demuestran errores en E5/E7 y en recorridos E4, y faltan implementaciones
de D4–D6, E6 y otras ramas. El dictamen exacto por dominio está en el
[contraste ecuación por ecuación](software-audit.md), con estados
VERIFICADO / INCORRECTO / NO IMPLEMENTADO / INDETERMINADO.

**F-35 y F-36 siguen abiertos, ahora con demostración numérica.** Los casos
analíticos muestran diferencias que pueden sobrestimar capacidades:

| Caso independiente | Disponible LRFD normativo kN | Programa kN | Diferencia relativa |
|---|---:|---:|---:|
| E7 circular, D/t100, Fe80MPa, Ag5000mm² | 280,029913043 | 315,720000000 | +12,7451% |
| E5(a), L/ra120, Ag2000mm² | 94,071715418 | 118,733100957 | +26,2155% |
| Ángulo concéntrico100×100×10, eje principal menor | 120,750491456 | 283,865206512 | +135,0841% |
| E4 canal, eje de simetría x, Fex50/Fey200/Fez100MPa | 150,742886340 | 301,485772680 | +100% del check E4 |
| E4 I doble simétrica, ya200mm | 1269,832966188 | 2015,858852803 | +58,7499% |

No son porcentajes atribuibles a todo perfil comercial; cada entrada y supuesto
están en el [banco desarrollado](calculations.md). ASD confirma el mismo
error relativo de nominales usando sus propios factores. También hay errores
de signo contrario: Q no es universalmente conservador.

Se reproducen **PASS locales falsos**, con demanda entre resistencia normativa
y capacidad del check. En los escenarios públicos ensayados el motor conserva
`INCOMPLETE`: HFS-010 mitiga el falso cumplimiento global, pero no corrige el
número ni garantiza seguridad de una llamada directa. No se amplía cobertura.

## Fuentes, independencia y alcance

Se leyeron AGENTS, roadmap, ADR-003, seguimiento, inventario DRY, contratos
vigentes de entradas/métodos/cobertura/registro/trazas y documentación HFS-030.
Se adoptan S22 + E25 + E26 por los hashes de HFS-030, comprobados nuevamente
en [start.json](evidence/start.json) y [sources.json](evidence/sources.json).
Matriz construida desde las páginas S22 de D/E completas (PDF100–117),
B4 pertinente y las tres páginas de erratas, con inspección visual de tablas,
ecuaciones y desigualdades. Las listas no corrigen directamente D/E; la
definición L de Ap.7 y la referencia HSS se consignan como dependencias externas.

La [matriz independiente](requirements.md) enumera familias, condiciones,
datos, fórmulas, factores, excepciones, detalles y remisiones externas.
No se deriva del router ni del registro. La confrontación posterior no modifica
su autoridad. 95 hojas Decimal a50 dígitos y desarrollos manuales; esperados
sin imports productivos. 78 comparaciones de capacidades, ambas metodologías,
con entradas, nominales/áreas/intermedios y resultados en
[probes.json](evidence/probes.json). Las referencias no son ejemplos publicados:
se identifica autoría del agente y falta de revisión humana.

La CI inicial fue consultada en API pública:
[run40961316786](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40961316786),
SHA inicial, Windows2022 y Ubuntu24.04 `completed/success`, jobs123754505909
y123754505596. [Captura](evidence/ci.json). Esa CI acredita la base de software,
no estos cambios locales ni fórmulas normativas.
El acceso web al editor AISC devolvió403; autenticación remota de bytes,
completitud editorial y permisos continúan pendientes F-28. No se sustituyen
PDF ni se usa un tercero como autoridad normativa.

## Hallazgos y decisión sobre correcciones

El [plan verificable](findings.md) contiene severidad, certeza, disposición,
consecuencia, responsable y condiciones de cierre para F-35/F-36 y nuevos
F-46 (eje E4 canal/H), F-47 (offsets ignorados), F-48 (clasificación/datos
incompletos). F-12 obtiene reproducción de OD/ID; F-38 conserva los dominios
ausentes, F-37 conserva referencias E5 imprecisas. **F-31 sigue P0 abierto y
reservado prioritariamente para HFS-032**; no se inicia ese hito.

La entrega es una auditoría con propuestas y pruebas de regresión de los
defectos, **no una reparación normativa del motor**. No se cambiaron cálculos
para conservar una referencia errónea ni para volver verdes los oráculos.
E5 requiere datos que JSON1.0 no expresa; E4 requiere simetría/arriostre
acreditados y E7 geometría por elemento y modos. Adoptar esos datos por defecto
sería una nueva hipótesis. El plan propone rechazo/pendiente ante insuficiencia
y correcciones por dominio con revisión explícita de contratos y consumidores.

No se han implementado todavía esas guardas adicionales ni correcciones:
las capacidades incorrectas permanecen en el runtime y sus xfail siguen abiertos.
No se presenta esta auditoría como habilitación para usar esos dominios.
La investigación de consumidores H/I se limita a localizar llamadas a Q;
no se auditan sus ecuaciones ni interacciones, ni se toca F/G/H/I.

## Pruebas, diferencias y compatibilidad

Python3.12.10, Windows, entorno editable nuevo `.venv/31dev`, instalación con
`requirements/ci-constraints.txt`. Freeze y comandos exactos capturados.
Se ejecutó `scripts/verify_hfs020.py --out .venv/31-verify` con las21 suites
separadas, instalaciones normal/wheel/editable y consumidores fuera del checkout.
Resultado `accepted=true`, exit0. La nueva suite durante esa corrida tenía
70 aprobadas/59xfail; después se añadieron tres comprobaciones (raíz E4 por
método y F-12), y se repitió **íntegra la suite final** desde wheel y editable
en otra carpeta externa: **72 aprobadas/60xfail**, exit0 ambos. No se suman
ejecuciones repetidas ni se cuentan xfail como aprobados.

| Conjunto | Aprobadas | Subpruebas | Fallos / errores / skip ordinario / XPASS |
|---|---:|---:|---|
| Original | 68 | 12 | 0 / 0 / 0 / 0 |
| Caracterización HFS-000 | 12 | 0 | 0 / 0 / 0 / 0 |
| HFS-011/016/010/012/013×2/014/015/017/020/021/021A×2/022/022R/022Q/023/024 | 2595 | 0 | 0 / 0 / 0 / 0 |
| HFS-031 final | 72 | 0 | 0 / 0 / 0 / 0; **60 xfail estrictos** |
| Total único final | **2747** | **12** | **60 defectos esperados, no acreditados** |

JUnit representa xfail como skipped: se separan aquí de omisiones ordinarias.
La suite contiene132 casos,72 aprobados+60xfail, con `raises=AssertionError`:
errores de setup, importación o validación no quedan enmascarados. Un XPASS es
fallo. La base2675+12 permanece íntegra. Resultados por suite, comandos y logs
están archivados en [verification.zip](evidence/verification.zip) y las
comprobaciones finales en [final-checks.zip](evidence/final-checks.zip), con
inventario de miembros y hashes en [archives.json](evidence/archives.json).

- **12 ejemplos:** comparación exacta de resultados contra referencia existente.
- **24 escenarios CLI/memoria:** entradas versionadas, capacidades, DCR,
  estados, cobertura, trazas, códigos de salida y contenido preservados.
- **Seis SVG:** iguales según política existente de finales LF/CRLF, sin nueva
  normalización. No hay auditoría de capacidades I por comprobar esos archivos.
- Instalación normal, wheel desde sdist y editable: build/twine/pipcheck,
  imports e identidad canónica, schemas y consumidores externos correctos.
- Diez esquemas JSON1.0 y manifiesto sin diferencias; registro93 entradas
  íntegro, sin nueva acreditación. Ruff y `git diff --check` exit0.
- `git diff --exit-code HEAD -- src examples schemas data pyproject.toml
  docs/contracts docs/audit/hfs030 docs/audit/hfs000`: exit0. Ningún cambio
  productivo, de expectativa histórica o de contrato para pasar pruebas.

El antes/después del producto es idéntico por fuentes protegidos y por regresión
estricta; las diferencias numéricas de la tabla son **norma frente a software**,
no cambios aplicados. Los tests históricos que solo exigen positividad o
reducción respecto de E3 permanecen, pero no se consideran acreditación.

### Incidentes conservados

La primera ejecución de la suite nueva falló50 casos por faltar el campo
contractual `Lb` en el constructor de pruebas; se corrigió el constructor,
no el motor ni esperados. JUnit inicial preservado. Se corrigió un borrador
del área de HSS rectangular del oráculo para explicitar radios12/6 y área
analítica exacta; ambos borradores se conservan, no eran oráculos históricos.
Los registros finales usan exclusivamente el fixture final reproducible.

El entorno histórico `.venv/21dev` no existe aquí; se creó31dev. El entorno
documental carecía de renderizador/Pillow: se instalaron solo en `.venv`,
sin añadir dependencias al paquete. El intento inicial de pip restringido dio
WinError10013; la instalación autorizada fuera del sandbox terminó correctamente.
Git puede advertir acceso denegado a un temporal preexistente
`tests/.tmp_tests/debug_cli_gb5761jq`; no se modifican permisos ni se borra.
La inspección de fuentes/tests/scripts y la regresión externa sí se completaron.

Al archivar, la lectura restringida del wheel dio PermissionError; se conservó
el ZIP parcial como `archiving-restricted-attempt.zip` y se repitió la lectura
fuera del sandbox, sin cambiar permisos ni borrar archivos. El ZIP definitivo
contiene124 miembros recuperados y verificados por hash; los15 miembros de
comprobaciones finales también se verificaron. [Incidente](evidence/archive-incident.json).

## Reproducción

Desde el checkout, con entorno dev instalado y salidas nuevas:

```powershell
.venv/31dev/Scripts/python.exe docs/audit/hfs031/oracles.py --out .venv/31-oracles-new.json
.venv/31dev/Scripts/python.exe -m pytest -q -rx -p no:cacheprovider tests/test_hfs031_de_audit.py --basetemp=.venv/31-tests-new
.venv/31dev/Scripts/python.exe docs/audit/hfs031/probe.py --out .venv/31-probes-new.json
.venv/31dev/Scripts/python.exe scripts/verify_hfs020.py --out .venv/31-verification-new
.venv/31dev/Scripts/python.exe docs/audit/hfs031/checks.py --verification .venv/31-verification-new --out .venv/31-checks-new
```

`checks.py` copia solo nueva suite/fixture a una carpeta externa nueva, usa los
intérpretes wheel/editable del verificador, comprueba hashes de entradas,
reproducción exacta del banco, Ruff, schemas, índice y ausencia de cambios
protegidos. Los logs contienen rutas absolutas del entorno observado, no rutas
portables prometidas. `oracles.py` y `probe.py` rechazan sobrescritura de salidas.

## Inventario de cambios

| Archivo / conjunto | Cambio y responsabilidad |
|---|---|
| `docs/audit/hfs031/requirements.md` | Matriz desde S22, sin código como fuente de aplicabilidad |
| `software-audit.md` | Confrontación de ecuaciones/selección/datos, dictamen por dominio |
| `calculations.md`, `oracles.py` | Desarrollo manual y evaluación independiente Decimal |
| `findings.md` | F-ID, severidad/certeza, reparación propuesta y condiciones de cierre |
| `report.md`, `evidence/` | Informe, base/CI/fuentes, capturas recuperables, hashes y pruebas |
| `probe.py`, `checks.py` | Confrontación y reproducción de auditoría, sin código runtime |
| `tests/test_hfs031_de_audit.py` | Oráculos, fronteras, fallos conocidos estrictos y cobertura pública |
| `tests/fixtures/hfs031/oracles.json` | Banco nuevo, generado independientemente del producto |
| `scripts/verify_hfs020.py` | Incorporar suite/fixture nuevos al consumidor instalado; sin relajar comparadores |
| `CONTRIBUTING.md` | Ejecución y significado de xfail de auditoría |
| `docs/ROADMAP.md`, `docs/audit/tracking.md` | Estado vivo y nuevos hallazgos, históricos preservados |
| `docs/architecture/dry-inventory.md` | Propietarios existentes, consumidores Q y separación de oráculos |

## Riesgos residuales

No hay dictamen global de aptitud: correcciones F-35/F-36/F-46–48 pendientes,
propiedades/fabricación/contacto/arriostramiento reales indeterminados y datos
externos An/U/K/cargas no autenticados. La revisión de todos los requisitos
documentales no equivale a un oráculo de toda posible sección o conexión.
Las hojas E6/E4(c)/fronteras be describen implementaciones ausentes, no pruebas
verdes de funciones existentes. F-12/14/27 y calidad integral del catálogo
requieren su tarea específica; no se corrigen datos sin fuente.

La CI del árbol local requiere publicación futura autorizada. No hubo commit,
push, rama ni PR. La revisión independiente debe decidir correcciones y
acreditaciones acotadas; esta entrega no las concede ni inicia HFS-032.
