# Documentos manuales HFS-022Q

`manual.json` contiene veinte documentos y expectativas redactados antes de
ejecutar la API bajo prueba. No regenerar desde dump_json, migrate_legacy,
get_schema, modelos serializados, fixtures anteriores ni resultados del motor.
El hash previo a la primera ejecución está en
[preparation.json](../../../docs/audit/hfs022/final-quality-review/evidence/preparation.json).

Cada caso declara aceptación estructural para ambos esquemas congelados,
aceptación Python y, para rechazos, código, JSON Pointer y presencia de causa.
`reason` explica el esperado. El bundle incluye resultados efectivos manuales
de merge, sin usar un segundo algoritmo de preparación en las pruebas.

Los checks son aritmética sintética: 50/100 = 0,5 y 150/100 = 1,5. Los valores
no son resistencias normativas ni acreditan un estado límite AISC. INCOMPLETE
conserva el fallo conocido y la cobertura pendiente no es completa. Los textos
de procedencia dejan esa ausencia de acreditación explícita.

La clave duplicada se conserva en `json_text`: una decodificación genérica
pierde el primer valor y el esquema ve un objeto estructuralmente válido.
`load_json` recibe el texto original y debe rechazarlo. Las otras expectativas
se comprueban mediante load_json y validate_document, sin mutar el original.
Los roundtrips comparan valores JSON y presencia de campos; no exigen conservar
espaciado ni la grafía `50` frente a `50.0` de los documentos manuales.

El consumidor independiente está en `scripts/probe_hfs022q_consumer.py` y usa
el archivo como entrada externa, sin imports de módulos de pruebas. La suite
pytest añade el contraste Draft 2020-12 para ambos modos.
