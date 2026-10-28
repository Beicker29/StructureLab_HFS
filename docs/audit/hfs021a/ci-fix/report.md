# HFS-021A — Corrección de comparación SVG multiplataforma

Fecha: 2026-10-28. Base y HEAD verificados: `main`,
`ae5f54bff77288731a487f0195e82f0752cd23a7`. Árbol inicialmente limpio,
con las advertencias históricas de acceso; sin cambios de permisos ni limpiezas.
Este suplemento conserva el [informe anterior](../report.md) y sus capturas.
Entrega para revisión técnica; **cierre remoto pendiente**. Sin commit, push,
rama, PR ni HFS-022.

## Diagnóstico demostrado y límite de la evidencia

Se consultaron jobs, logs y artefactos del
[run 40694129771](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40694129771):
Ubuntu 24.04 job `122836258660` FAILURE; Windows 2022 job `122836258883` SUCCESS.
El fallo de Ubuntu ocurre en la igualdad binaria de `verify_hfs020.py`, después
de las 1790 pruebas +12 subpruebas, los 12 ejemplos y los 24 escenarios CLI.
Primer miembro: `after/composite_encased_case.json/original/case-0.svg`.
Los resultados del motor y las salidas CLI/memorias normalizadas de ambos
artefactos son exactamente iguales; se conserva el control de procedencia
existente para hashes de entradas con finales de línea distintos por checkout.

**Ningún artefacto remoto contiene SVG**: Ubuntu tiene 88 miembros, Windows 91.
Los gráficos se escribieron en el directorio temporal externo, que CI no subía.
No se inspeccionaron bytes SVG del runner original. Se conservan los dos ZIP
descargados íntegros, sus hashes publicados por GitHub y los logs decodificados.

Ante esa ausencia se ejecutó una reproducción Linux real, sin instalar WSL ni
software del sistema: QEMU portable con red deshabilitada (`-nodefaults`),
kernel Alpine `6.6.134-0-virt`, x86_64, CPython **3.12.13**. No es el runner Ubuntu
ni una nueva corrida completa del motor Linux. Se extraen, sin cambiar su texto,
las funciones `_ordered_pm_points` y `_write_i5_interaction_diagram_svg` de
`reporting.py`; se usan las cargas de los ejemplos versionados y los puntos
brutos de interacción de las memorias del artefacto Ubuntu. El objeto auxiliar
solo proporciona los tres atributos de cargas consumidos por el renderizador.
La misma reproducción en Windows coincide con los seis SVG históricos por bytes.

En Linux se recuperan los bytes originales mediante base64 por consola serial,
sin conversiones de finales de línea del host. Los seis difieren de Windows
exclusivamente en CRLF/LF. Todos son UTF-8 válido, subconjunto ASCII, sin BOM;
no hay CR aislados. Tras reemplazar únicamente `b"\r\n"` por `b"\n"`, la
igualdad es exacta. Por ello no hay diferencias de coordenadas, números,
geometría, textos, elementos o atributos en estas seis reproducciones.

| Familia; original y detailed (dos archivos por fila) | Windows, bytes / CRLF | Linux, bytes / LF | Primer offset diferente, base 0 |
|---|---:|---:|---:|
| Encased | 4696 / 56 | 4640 / 56 | 87 |
| Filled circular HSS | 4754 / 57 | 4697 / 57 | 87 |
| Filled rectangular HSS | 4750 / 57 | 4693 / 57 | 87 |

SHA-256 originales, en orden Windows / Linux (original y detailed coinciden):

- Encased: `b1891197ec6e8748f87b74e9ca1a06ec50dc2480c52b545d2592c1169ca22d6e` /
  `4416176a9013c61998a9bb837e7ccc9abd3660172962a3d18881f593b3a8d2f2`.
- Circular: `9ad1d10077b529cd331b256fe5468979662c54d6886ff38abe3e30ac01ab02ce` /
  `78862a153708b31b2d07102d0e2d91bf427e213f852158568667c6f468f11946`.
- Rectangular: `61692cf8297faf6ba77c64673623e261d549a0632c5f3b7cf34faf9a9f74de6b` /
  `099ee3388995ef2e3d73ebe0a699cd3951385c70c323ea67818694bd8b561d58`.

El [diagnóstico por archivo](evidence/diagnosis.json) conserva tamaños, hashes,
conteos y las primeras doce posiciones de diferencia. Los SVG completos,
entradas, funciones ejecutadas, comandos y consola Linux están en
[linux-reproduction.zip](evidence/linux-reproduction.zip).

La causa es la escritura de texto existente con
`Path.write_text("\n".join(svg_parts), encoding="utf-8")`, cuyo `newline=None`
usa el final de línea del sistema. La igualdad binaria introducida en CI por
HFS-021A exigía CRLF en Ubuntu. El generador permanece intacto.

## Corrección mínima

`scripts/hfs021a_svg_comparison.py::assert_svg_equal` compara bytes tras una sola
transformación explícita CRLF → LF. Mantiene hashes/tamaños de ambos originales,
conteos de finales de línea, hash normalizado e indicador `byte_identical`.
No analiza ni reserializa XML; no altera espacios, BOM, orden de atributos,
textos, números, redondeo ni tolerancias. Un CR aislado diferente se rechaza.
El identificador exacto del archivo se incluye en el error.

`verify_hfs020.py` usa esa función para los seis miembros históricos y conserva
la comprobación exacta del conjunto esperado. Archiva los bytes generados y
de referencia en `svg-originals.zip` antes de compararlos; el ZIP se cierra
también al fallar. Así el próximo fallo de CI conservará el SVG causante, sin
cambiar el workflow. El hash de cada original queda además en la comparación
cuando esta termina correctamente. Los manifiestos generales incluyen el ZIP.

Los JSON/valores numéricos siguen usando el comparador HFS-020 intacto.
`compare_hfs021.compare_results` conserva su comparación binaria antes/después
en una misma plataforma. No se cambian archivos productivos, API, ecuaciones,
factores, guardas, geometría, cobertura, catálogo ni expectativas históricas.

## Pruebas, ejecución y diferencias

Las 29 pruebas nuevas son independientes de `steel_design`: igualdad idéntica
LF/CRLF, diferencia de plataforma en ambos sentidos, doce mutaciones probadas
con y sin CRLF (24 rechazos) y conservación de bytes/mtime de ambos archivos.
Incluyen coordenadas, texto numérico, representación numérica equivalente,
elementos añadidos/eliminados, atributos, color, texto, orden de atributos,
espacios, CR aislado y BOM. El comparador nuevo acepta los seis SVG Linux;
la comparación binaria anterior rechaza los seis.

Los resultados y conteos finales, separados por suite, están en
[validation.json](evidence/validation.json). Cada captura completa conserva
comando, cwd, código de salida, stdout/stderr, JUnit, entorno, freeze,
distribuciones e inspección de archivos:
[antes local](evidence/before-local.zip), [después local](evidence/after-local.zip).
La suite original mantiene 68 métodos +12 subpruebas; caracterización HFS-000
se ejecuta separadamente con 12 pruebas. La nueva suite no se suma a la original.

| Suite | Antes local | Después local |
|---|---:|---:|
| Original | 68 +12 subpruebas | 68 +12 subpruebas |
| Caracterización HFS-000 | 12 | 12 |
| HFS-011 | 665 | 665 |
| HFS-016 | 44 | 44 |
| HFS-010 | 57 | 57 |
| HFS-012 | 61 | 61 |
| HFS-013 direccional | 57 | 57 |
| HFS-013 método | 73 | 73 |
| HFS-014 | 72 | 72 |
| HFS-015 | 84 | 84 |
| HFS-017 | 468 | 468 |
| HFS-020 comparación | 50 | 50 |
| HFS-021 ejecución | 51 | 51 |
| HFS-021A API | 28 | 28 |
| HFS-021A SVG nueva | No existía | 29 |
| **Métodos, sin sumar subpruebas** | **1790** | **1819** |

Ambos verificadores completos terminaron con **exit 0, accepted=true**.
Cero fallidas, errores, omitidas, xfail o XPASS en las corridas finales.
Adicionalmente, las 29 nuevas pasan en Linux Alpine (exit 0 de pytest en la
consola del guest), y las 28 de API pasan de nuevo en editable en cada captura.
Estas repeticiones no se suman al total principal. Un primer intento dirigido
en Windows encontró WinError 5 al usar un temporal; se repitió en otro
directorio con el permiso de ejecución disponible y pasó 29/29. No se cambió
ningún ACL ni se ocultó como xfail. Los incidentes auxiliares del montaje
Linux están identificados en `incidents.json` dentro del ZIP de reproducción.

**Diferencias numéricas o de resultado: ninguna** en los 12 ejemplos y los
24 escenarios antes/después. Los seis SVG Windows siguen idénticos por bytes.
Los seis SVG Linux conservados son equivalentes solo por CRLF/LF. El
[comparador HFS-021A existente](evidence/comparison.json) también pasó sin cambios;
los 44 fuentes Python del checkout y de ambos wheels son idénticos. Los
checks Git, Ruff, builds, tres `pip check` y twine estricto terminaron con exit 0.
Las advertencias conocidas de acceso se conservan en los registros; no se
tratan como una inspección exitosa de esos temporales históricos.

```powershell
# Python/herramientas fijados; Git debe estar en PATH. Usar salidas nuevas.
.\.venv\21dev\Scripts\python.exe -X utf8 scripts/verify_hfs020.py --out .venv/21a-ci-fix/before-local
# Después de aplicar la corrección:
.\.venv\21dev\Scripts\python.exe -X utf8 scripts/verify_hfs020.py --out .venv/21a-ci-fix/after-local
.\.venv\21dev\Scripts\python.exe -X utf8 -m ruff check .
git diff --check
```

El primer comando se ejecutó sobre el verificador anterior y sus 1790 pruebas;
para repetirlo después hay que recuperar esa versión desde el SHA base en una
copia aislada, sin sobrescribir evidencia ni revertir el árbol de trabajo.
La construcción produce sdist y wheel reconstruido desde sdist. El verificador
prueba instalaciones normal, editable y wheel, `pip check` en las tres,
`twine check --strict`, Ruff, orígenes/identidad de imports, ambas entradas CLI,
12 ejemplos, 24 escenarios y los seis SVG. La repetición editable de 28 pruebas
de API es adicional al total principal. Entorno completo en las capturas;
Windows usa Python 3.12.10 y las constraints existentes, sin nuevas dependencias.

Reproducción Linux: extraer `linux-reproduction.zip` en la raíz indicada por su
README, recuperar los cuatro recursos portables listados con URL/hash en
`toolchain.json` y ejecutar sus comandos. No se versionan el emulador de 1,2 GB
ni el sistema regenerable; quedan en `.venv/21a-ci-fix`, sin eliminación.
Los logs de intentos auxiliares y sus limitaciones se conservan en el archivo.

## Inventario y pendientes

Archivos de código cambiados: `scripts/verify_hfs020.py`.
Nuevos: `scripts/hfs021a_svg_comparison.py`,
`tests/test_hfs021a_svg_comparison.py`. Documentación modificada:
`CONTRIBUTING.md`, `docs/ROADMAP.md`, `docs/architecture/dry-inventory.md`.
Se añade este informe y su directorio `evidence/`; el inventario completo,
incluidos los miembros archivados, está en
[file-inventory.json](evidence/file-inventory.json). No se sustituye evidencia
de HFS-000/021/021A ni se modifican los seis SVG de referencia.

La comparación Git y los hashes de las fuentes verifican identidad de motor,
reglas, ecuaciones, factores, contratos y generador frente a HEAD, así como de
tests previos, catálogo, ejemplos, comparador JSON y evidencia histórica.
No se interpretan estas comprobaciones como validación normativa AISC.

**Pendiente obligatorio:** después de que el usuario publique, ejecutar CI sobre
el nuevo commit y obtener Windows 2022 **SUCCESS** y Ubuntu 24.04 **SUCCESS**.
La reproducción Alpine del renderizador y las pruebas locales no sustituyen
esa puerta. Los bytes remotos de los SVG del fallo original no son recuperables
de los artefactos recibidos; la conclusión se limita a la reproducción demostrada
y a los resultados remotos conservados. PNG/matplotlib no se ejercita ni se
incorpora en este alcance. Los defectos normativos abiertos siguen pendientes.
