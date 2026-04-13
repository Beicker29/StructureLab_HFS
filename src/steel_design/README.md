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
- `section_name` es obligatorio incluso para secciones custom.
- `custom_section` es opcional para definir secciones macizas sin catalogo:
  - `type`: `SOLID_CIRCULAR` con `diameter`
  - `type`: `SOLID_RECTANGULAR` con `H` y `B`
- Para compresion capitulo E:
  - `lengths` requiere `Lx`, `Ly`, `Lz`, `Lb`.
  - `factors` requiere `Kx`, `Ky`, `Kz` (`Cb` para flexion) y admite `xa`, `ya` para E4.
  - Angulo simple en compresion requiere `connection.angle_compression_mode`.
- Para traccion (`Pu < 0`) se exige D3 estricto:
  - `connection.An > 0`
  - `0 < connection.U <= 1`
  - `Ae = U*An` (sin fallback a `Ae`).
- Para flexion (Capitulo F):
  - solo se admite `LRFD`.
  - se reportan checks por eje cuando existen `Mux` y `Muy` (sin interaccion biaxial H1).
  - para angulo simple en flexion (`F10`) se requiere:
    - `connection.angle_flexure_axis`
    - `connection.angle_ltb_restraint`
    - `connection.angle_max_tension_location` cuando `angle_flexure_axis = geometric_axis`.
- Para cortante (Capitulo G):
  - `Vux` y `Vuy` activan checks por eje.
  - `Vu` legacy se interpreta como demanda en eje mayor.
  - en `RECTANGULAR_HSS`, el espesor de diseno es `tdes` (mm).
- Para torsion/combinaciones (Capitulo H):
  - `Tu` activa `H3` solo en `RECTANGULAR_HSS` y `CIRCULAR_HSS`.
  - `H1` se evalua para combinacion axial + flexion en HSS.
  - `H3-3` (no-HSS con torsion) permanece fuera de alcance y falla de forma explicita.

## Politica de seguridad

- Fail-hard ante datos insuficientes de una regla aplicable.
- Errores estructurados en CLI (`type`, `code`, `message`, `details`, `stage`).
