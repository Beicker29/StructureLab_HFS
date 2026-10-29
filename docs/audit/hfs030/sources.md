# HFS-030 — Fuentes locales y procedencia

Fecha de cotejo: 2026-10-29. Alcance final indicado por el usuario: comparar
exclusivamente los PDF del repositorio, incluidas las dos erratas incorporadas
por él durante la tarea. No sustituir ni editar los originales.

## Identidad verificable

| Fuente | Archivo en la raíz | Fecha declarada en el documento | Bytes | SHA-256 |
|---|---|---|---:|---|
| S22 / UN22 / C22 | [a360-22w.pdf](../../../a360-22w.pdf) | ANSI/AISC 360-22, 1 de agosto de 2022 | 16660424 | `25c4bf59b4c6fd00589e32a6ddac92cc9fd6be30dd5da07fc7c5f7fd475b2361` |
| E25 | [errata_360-22_01232025.pdf](../../../errata_360-22_01232025.pdf) | Revision and Errata List, 23 de enero de 2025 | 301107 | `b2c8a9db622f583ebff013be1d1b4ffd3b992f7c7344d6cb815991ed400a1be6` |
| E26 | [errata_360-22_09232026.pdf](../../../errata_360-22_09232026.pdf) | Revision and Errata List, 23 de septiembre de 2026 | 122256 | `d53ff5cc753cfcf6af70fd10355895b0120074527946f997084482fb626732e6` |
| AISC 341, independiente | [a341-22w.pdf](../../../a341-22w.pdf) | ANSI/AISC 341-22, 26 de septiembre de 2022 | 28013381 | `34cdd4a45360b5e3cb39f9fbb55640af79ece0deb9070a112aaccb938c027e0c` |

**HECHO VERIFICADO:** S22 tiene 780 páginas PDF; E25 tiene dos y E26 una.
Se leyeron íntegramente ambas listas y se inspeccionaron sus tres páginas
renderizadas para distinguir tachados, sustituciones y símbolos. La
[captura reproducible](evidence/local-sources.json) conserva metadata y hashes
del texto extraído de las páginas cotejadas; no constituye una transcripción
normativa alternativa. `local-pdf.json` conserva el primer inventario, anterior
a la incorporación de E25/E26; no es la conclusión final.

**HECHO VERIFICADO:** las portadas/listas identifican AISC y esas fechas.
S22 declara creación PDF en febrero de 2023; ambas erratas tienen metadata
de creación/modificación de septiembre de 2026. La fecha de creación de un
archivo no reemplaza la fecha editorial impresa ni prueba por sí sola alteración
del contenido. El PDF base conserva las redacciones anteriores en los 22 grupos
cotejados; no incluye esas correcciones.

**PENDIENTE:** autenticación de bytes contra una descarga independiente del
editor, procedencia original de S22 y permisos de redistribución (F-28).
E25/E26 son las copias locales que el usuario identifica como oficiales; se
registra esa procedencia sin afirmar verificación criptográfica remota. La
[página AISC de revisiones y erratas](https://www.aisc.org/aisc/publications/revisions-and-errata/)
queda como referencia de procedencia declarada, no como documento descargado
en este cotejo. Los intentos anteriores al cambio de alcance devolvieron 403;
no se usa contenido de terceros ni de resultados de búsqueda como autoridad.
No se volvió a consultar la web tras la instrucción de usar solo el repositorio.

## Jerarquía y paginación

- **S22 — Specification:** A1, PDF 69 / impresa 16.1-1, distingue el cuerpo
  normativo (incluidos símbolos, glosario y apéndices) de Commentary/User Notes.
- **UN22 — User Note:** información de apoyo intercalada; por ejemplo la tabla
  de selección F1.1, PDF 119 / 16.1-51, y la alternativa F4→F5, PDF 124 / 16.1-56.
  No reemplaza las condiciones de la Specification ni valida la implementación.
- **C22 — Commentary:** comienza en PDF 355 / 16.1-287. C-I5 y sus métodos están
  en PDF 518–522 / 16.1-450–454; las ecuaciones C-I5-1a/b en PDF 521 / 16.1-453
  no son las ecuaciones I5-1a/b de la Specification.
- **E25/E26:** corrigen los pasajes identificados en la matriz. Una corrección
  de Commentary conserva su naturaleza informativa; no convierte una figura
  auxiliar en requisito autónomo. E26 declara ser adicional a listas anteriores.
- **Ejemplos, Manual y Design Guides:** referencias auxiliares que no se han
  obtenido ni auditado en este hito. Las menciones SCM de métodos compuestos
  no acreditan las tablas referidas por el solo hecho de aparecer en el código.
- **AISC 341:** inventario de identidad solamente; ningún dictamen sísmico.

Las páginas PDF son índices **1-based**. En el cuerpo estudiado, la impresa
16.1-n corresponde a PDF n+68. No aplicar esa conversión a preliminares:
16.1-lvi corresponde a PDF 58. Un encabezado heredado de la sección anterior
no determina la sección del texto; por ejemplo E7 comienza en PDF 116 aunque
el encabezado aún indique E6. Las tablas y exponentes se verificaron visualmente;
la extracción automática pierde orden, subíndices y tachados.

## Base documental adoptada para revisión

Conservar S22 por hash y leerlo junto con E25 y E26, mediante el
[mapa de correcciones](impact-matrix.md). No parchear el PDF, cambiar el catálogo,
renumerar IDs HFS-023 ni alterar trazas HFS-024 en esta tarea. La cobertura del
cotejo es exhaustiva respecto de los **22 grupos de estas dos listas**, no de
todas las erratas posibles, todas las disposiciones de AISC ni sus formulaciones
en software. Tampoco se afirma que se haya obtenido una edición consolidada.

Reproducción desde la raíz (elegir una salida nueva):

```powershell
.venv/Scripts/python.exe docs/audit/hfs030/reproduce.py --pdf --out .venv/hfs030-local-sources-new.json
.venv/21dev/Scripts/python.exe docs/audit/hfs030/reproduce.py --registry --out .venv/hfs030-registry-new.json
```

El primer entorno ya contiene `pypdf`; el segundo es la instalación editable
vigente. No se añadió dependencia al proyecto. El script rechaza hashes
distintos y salidas existentes. Los hashes de texto dependen de la versión
de `pypdf` registrada; los hashes de los PDF son independientes de la extracción.
Los renders exploratorios permanecen bajo `.venv/30-source/`; se regeneran con
`pypdfium2.PdfDocument(...)[pagina-1].render(scale=1.4).to_pil()`.
