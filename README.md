# StructureLab HFS: Steel Design Engine

Este repositorio contiene un motor de diseño estructural en acero estricto y de nivel de producción, fundamentado en la especificación AISC 360-22. Está construido en Python siguiendo un esquema riguroso de arquitectura en capas (Layered / Domain-Driven Architecture).

## Estructura del Repositorio

La arquitectura asegura que las reglas del negocio y cálculos matemáticos puros estén separados completamente de los casos de uso, repositorios de datos y mecanismos de entrada/salida de la aplicación:

```text
├── a360-22w.pdf                 # Especificación original AISC 360-22.
├── data/
│   └── sections.xlsx            # Base de datos de perfiles en acero (W, HSS, etc.)
├── examples/
│   └── case_001.json            # Ejemplo de payload (cargas, material, dimensiones)
├── src/
│   └── steel_design/
│       ├── codes/               # Fórmulas de ingeniería puras agnósticas a negocio (AISC 360-22)
│       ├── domain/              # Reglas de validación, evaluación de DCRs y excepciones
│       ├── sections/            # Lógica de persistencia, lectura del Excel y Modelos Geométricos
│       ├── engine.py            # Orquestador del pipeline (no hace cálculos directos)
│       ├── models.py            # Modelos Pydantic (SteelCase, CheckResult)
│       └── run.py               # Ejecutable CLI
└── requirements.txt             # Dependencias del proyecto (Pydantic, Openpyxl)
```

## Flujo de Trabajo (Pipeline)

El orquestador central (`engine.py`) asegura que cualquier caso de diseño fluya direccionalmente sin saltarse pasos:
1. **Validation**: Revisa la integridad física de las variables de entrada usando `domain/validation.py`.
2. **Repository Fetch**: Extrae el perfil mediante el `sections/repository.py` el cual usa en el backend la lectura del Excel estructurado.
3. **Execution**: Lanza una lista de reglas registradas (`FlexureRule`, `AxialRule`, etc.) que internamente invocan a `evaluators` correspondientes y luego a los cálculos base provistos en `codes/`.
4. **Aggregation**: Convierte los resultados en respuestas formateadas indicando Capacidad, Demanda, DCR y Estado (PASS/FAIL).

## Instalación y Ejecución

Primero, instala las dependencias usando el entorno virtual:
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Para ejecutar el motor desde la consola a modo de prueba:
```bash
python -m src.steel_design.run examples/case_001.json
```

---

*Nota: Los modelos subyacentes se encuentran en pleno desarrollo. El motor ha sido diseñado para mapear fielmente los lineamientos del `a360-22w.pdf` incluido en los entregables base.*
