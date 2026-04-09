# Steel Design Engine (Core)

Base del motor AISC 360-22.

## Reglas de contribucion

1. `codes/`: funciones matematicas puras, sin dependencias de modelos de aplicacion.
2. `domain/`: reglas de negocio, validaciones y evaluacion de DCR.
3. `sections/`: lectura de catalogo y modelo de propiedades geometricas.
4. `engine.py`: orquesta validacion -> seccion -> reglas -> agregacion.
5. `domain/routing/profile_router.py`: punto unico para registrar reglas por tipo de perfil.

## Contrato principal del caso (`SteelCase`)

- `material.E` debe ser `200000` MPa.
- Para compresion capitulo E:
  - `lengths` requiere `Lx`, `Ly`, `Lz`, `Lb`.
  - `factors` requiere `Kx`, `Ky`, `Kz` (`Cb` para flexion) y admite `xa`, `ya` para E4.
  - Angulo simple en compresion requiere `connection.angle_compression_mode`.

## Politica de seguridad

- Fail-hard ante datos insuficientes de una regla aplicable.
- Errores estructurados en CLI (`type`, `code`, `message`, `details`, `stage`).
