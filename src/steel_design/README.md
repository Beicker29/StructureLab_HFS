# Steel Design Base Engine 

Motor estructural AISC para análisis de elementos bajo AISC 360-22 (a360-22w.pdf).

## Reglas Estrictas de Modificación

Si vas a contribuir o añadir un nuevo estado límite a este motor de cálculo, es **obligatorio** cumplir esta estructura:

1. **(No mezclar capas) `codes/`**: Este directorio aloja cálculos matemáticos de la norma en crudo.
   - Las funciones aquí deben recibir datos flotantes puros (por ejemplo: `calculate_shear(Fy: float, Aw: float, ...)`).
   - No pueden conocer ni importar a `SteelCase` o `Section`. Son agnósticas al programa principal.
   
2. **(Reglas de Negocio) `domain/`**:
   - `evaluators/`: Aquí tomas el `SteelCase` y el `Section`, extraes las variables como área y base del patín, y llamas a la función que escribiste en `codes/`.
   - `rules/`: Tomas el evaluador, tomas las cargas actuantes del Payload como demanda, computas el índice de Demanda/Capacidad (DCR) y armas el diccionario `CheckResult` con el STATUS final (`PASS`/`FAIL`).

3. **(Pipeline) `engine.py`**:
   - Si creaste un nuevo Rule, repórtalo en el array `self.rules` dentro de `engine.py`. El orquestador se encargará del resto de manera automática.

## Fichas y Formato
El motor leerá la información de catálogo (Ix, Iy, Zx, variables elásticas y geométricas) directamente del cargador de Excel en la capa de datos (`sections/`). Si necesitas nuevas propiedades geométricas, modifíca el modelo Pydantic `sections/models.py`.
