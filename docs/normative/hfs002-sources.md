# HFS-002 — Base documental identificada

Fecha: 2026-10-26. Lectura de aplicabilidad, no certificación ni auditoría numérica integral. La matriz se funda en el documento normativo y se contrasta después con el software. No se generó importando `ProfileRouter` ni copiando su lista de reglas.

## Fuentes y autoridad

| ID | Documento local / edición | Identidad y alcance de lectura |
|---|---|---|
| S22 | [a360-22w.pdf](../../a360-22w.pdf), ANSI/AISC 360-22, *Specification for Structural Steel Buildings*, 1 agosto 2022 | 780 páginas; SHA-256 `25c4bf59b4c6fd00589e32a6ddac92cc9fd6be30dd5da07fc7c5f7fd475b2361`. Portada PDF 1/3. Metadatos creación 2023-02-01, modificación 2023-02-15: no acreditan incorporación de erratas posteriores. |
| C22 | Commentary incluido en S22 | Inicio PDF 355, impresa 16.1-287: informativo. Lectura dirigida de introducción y C-H1, PDF 472 / 16.1-404; no se revisó íntegro el Commentary ni sus referencias. |
| UN22 | User Notes intercaladas en S22 | A1, PDF 69 / 16.1-1 excluye expresamente Commentary y User Notes de la Specification. Las tablas User Note E1.1 y F1.1 son orientación; las decisiones se anclan además en E/F. |
| S341 | [a341-22w.pdf](../../a341-22w.pdf), ANSI/AISC 341-22, *Seismic Provisions*, 26 septiembre 2022 | SHA-256 `34cdd4a45360b5e3cb39f9fbb55640af79ece0deb9070a112aaccb938c027e0c`. Portada PDF 1; A1 PDF 55 / 9.1-1. Solo identificación y alcance sísmico; no sustituye S22 ni se integra en la matriz de resistencia ordinaria. HFS-070 futuro. |

Todas las páginas PDF son **1-based**. En S22, para los capítulos consultados, página PDF = número arábigo impreso después de `16.1-` + 68. Esta correspondencia no se extrapola a preliminares ni a S341.

## Localizador de disposiciones consultadas

| Disposición S22 | Impresa 16.1- | PDF | Uso |
|---|---|---|---|
| A1 | 1 | 69 | Alcance y jerarquía documental |
| B1–B3 | 15–19 | 83–87 | Demandas, LRFD/ASD, estabilidad y verificaciones externas |
| B4; tablas B4.1a/b | 19–25; 21–23 | 87–93; 89–91 | Dimensiones, clasificación por elemento, espesor de diseño, área neta |
| C1–C3 | 26–31 | 94–99 | Estabilidad y procedencia de demandas |
| D1–D6; tabla D3.1 | 32–37; 34–35 | 100–105; 102–103 | Tracción, conexiones y miembros armados |
| E1–E7; tabla E7.1 | 38–49; 49 | 106–117; 117 | Compresión, condiciones E5/E6 y área efectiva |
| Introducción F; F1–F6 | 50–62 | 118–130 | Flexión simple, estabilidad, ramas I/canal |
| F7/F8 | 62–65 | 130–133 | HSS por eje y límites de aplicación |
| F9/F10/F11/F12 | 65–72 | 133–140 | 2L/tee, ángulos, macizos, otras geometrías |
| F13 | 72–74 | 140–142 | Agujeros, proporciones y construcción armada |
| G1–G7 | 75–81 | 143–149 | Cortante, paneles, elementos resistentes y aberturas |
| H1/H2/H3/H4 | 82–88 | 150–156 | Interacciones, torsión y rotura de alas |
| I1; tablas I1.1a/b | 89–95; 92 | 157–163; 160 | Métodos, materiales, clasificación compuesta |
| I2 | 95–100 | 163–168 | Axial compuesto y detallado |
| I3 | 100–106 | 168–174 | Flexión, construcción y transferencia en vigas |
| I4/I5 | 106–110 | 174–178 | Cortante e interacción compuestos |
| I6/I7/I8.1–I8.2b | 109–114 | 177–182 | Lectura dirigida: introducción de fuerzas, diafragmas y anclajes |

Se extrajo texto con `pypdf` del entorno local y se cotejaron visualmente las tablas B4.1a/b (PDF 89–91), I1.1a/b (160) y H3-6 (154), renderizadas con `pypdfium2`. No interpretar fórmulas a partir de OCR deformado: por ejemplo, H3-6 tiene el cuadrado sobre la suma de los términos de cortante y torsión. Extracciones/renderizados regenerables están en `.venv/hfs002-reading/`, ignorados; el PDF con hash y los localizadores preservan la referencia durable. No se añaden copias del PDF ni extractos íntegros a Git.

## Erratas y límites documentales

El [índice oficial de revisiones y erratas de AISC](https://www.aisc.org/aisc/publications/revisions-and-errata/) consultado mediante búsqueda el 2026-10-26 enumera entregas de enero de 2025 y septiembre de 2026 para 360-22. La apertura directa devolvió HTTP 403 en dos intentos. **No se obtuvieron ni cotejaron los documentos de erratas**; no se afirma que el PDF local esté actualizado. No se usaron transcripciones de terceros como autoridad.

Las ecuaciones se identifican como aparecen en el PDF local: por ejemplo F7.4 muestra F7-10 a F7-13. Una correspondencia con numeración corregida queda pendiente de obtener la errata oficial. Las citas estables incluyen siempre sección, página y hash, no solo número de ecuación. F-28/HFS-030 conserva la reconciliación documental; HFS-002 no adelanta esa auditoría completa. Hasta resolverla, las conclusiones son una matriz de revisión sobre **S22 local**, con vigencia de erratas pendiente, no una declaración de cobertura exhaustiva de la edición corregida.

ACI 318, ASCE 7, ASTM de fabricación/material y documentos de análisis externo son referencias requeridas por S22, no fuentes examinadas aquí. No se inventan sus verificaciones ni se considera validado un detalle por aportar un valor positivo. Se registran como dependencias externas en la matriz. J/K, L–N y apéndices se delimitan desde las remisiones B/C/D/F/G/I; no se declara estudiado su detalle completo ni todos sus casos especiales.
