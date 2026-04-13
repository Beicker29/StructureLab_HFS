from ..models import SteelCase
from ..codes.aisc_360_22.axial_calc import NORMATIVE_E_MPA
from .errors import ValidationError

def validate_case(case: SteelCase):
    if case.lengths.Lb <= 0:
        raise ValidationError("Unbraced length Lb must be > 0.")
    if case.lengths.Lx <= 0 or case.lengths.Ly <= 0 or case.lengths.Lz <= 0:
        raise ValidationError("Unbraced lengths Lx, Ly and Lz must be > 0.")
    if case.material.Fy <= 0:
        raise ValidationError("Yield strength Fy must be > 0.")
    if case.material.Fu <= 0:
        raise ValidationError("Ultimate strength Fu must be > 0.")
    if abs(case.material.E - NORMATIVE_E_MPA) > 1e-6:
        raise ValidationError(
            "Elastic modulus E must be 200000 MPa for normative Chapter E checks.",
            details={"E_received": case.material.E, "E_expected": NORMATIVE_E_MPA},
        )
    if case.factors.Kx <= 0 or case.factors.Ky <= 0 or case.factors.Kz <= 0:
        raise ValidationError("Effective length factors Kx, Ky and Kz must be > 0.")
    if case.factors.Cb <= 0:
        raise ValidationError("Cb must be > 0.")
    if case.factors.xa < 0 or case.factors.ya < 0:
        raise ValidationError("Bracing offsets xa and ya must be >= 0.")
    if case.loads.Pu < 0.0 and case.composite is None:
        if case.connection.An is None or case.connection.An <= 0.0:
            raise ValidationError(
                "connection.An is required and must be > 0 for tension cases.",
                details={"required_field": "connection.An"},
            )
        if case.connection.U is None:
            raise ValidationError(
                "connection.U is required for tension cases.",
                details={"required_field": "connection.U"},
            )
        if case.connection.U <= 0.0 or case.connection.U > 1.0:
            raise ValidationError(
                "connection.U must satisfy 0 < U <= 1 for tension cases.",
                details={"U_received": case.connection.U},
            )
    has_major_flexure = abs(case.loads.Mux) > 0.0
    has_minor_flexure = abs(case.loads.Muy) > 0.0
    if (has_major_flexure or has_minor_flexure) and case.design_method.value != "LRFD":
        raise ValidationError(
            "Chapter F flexural checks are implemented only for LRFD in the current scope.",
            details={"design_method_received": case.design_method.value, "design_method_required": "LRFD"},
        )
    if case.composite is not None:
        if case.design_method.value != "LRFD":
            raise ValidationError(
                "Chapter I composite checks are implemented only for LRFD in the current scope.",
                details={"design_method_received": case.design_method.value, "design_method_required": "LRFD"},
            )

        concrete = case.composite.concrete
        if concrete.fc <= 0.0 or concrete.wc <= 0.0:
            raise ValidationError(
                "composite.concrete.fc and composite.concrete.wc must be > 0.",
                details={"fc": concrete.fc, "wc": concrete.wc},
            )

        role = case.composite.role.value
        if role == "ENCASED_MEMBER":
            if case.composite.geometry.B is None or case.composite.geometry.B <= 0.0:
                raise ValidationError(
                    "composite.geometry.B is required for ENCASED_MEMBER.",
                    details={"required_field": "composite.geometry.B"},
                )
            if case.composite.geometry.H is None or case.composite.geometry.H <= 0.0:
                raise ValidationError(
                    "composite.geometry.H is required for ENCASED_MEMBER.",
                    details={"required_field": "composite.geometry.H"},
                )
            if case.composite.geometry.cover is None or case.composite.geometry.cover <= 0.0:
                raise ValidationError(
                    "composite.geometry.cover is required for ENCASED_MEMBER.",
                    details={"required_field": "composite.geometry.cover"},
                )
            if not case.composite.reinforcement.longitudinal_bars:
                raise ValidationError(
                    "composite.reinforcement.longitudinal_bars is required for ENCASED_MEMBER.",
                    details={"required_field": "composite.reinforcement.longitudinal_bars"},
                )
            if case.composite.reinforcement.transverse is None:
                raise ValidationError(
                    "composite.reinforcement.transverse is required for ENCASED_MEMBER.",
                    details={"required_field": "composite.reinforcement.transverse"},
                )

        if role == "COMPOSITE_BEAM":
            if case.composite.geometry.slab_effective_width is None or case.composite.geometry.slab_effective_width <= 0.0:
                raise ValidationError(
                    "composite.geometry.slab_effective_width is required for COMPOSITE_BEAM.",
                    details={"required_field": "composite.geometry.slab_effective_width"},
                )
            if case.composite.geometry.slab_thickness is None or case.composite.geometry.slab_thickness <= 0.0:
                raise ValidationError(
                    "composite.geometry.slab_thickness is required for COMPOSITE_BEAM.",
                    details={"required_field": "composite.geometry.slab_thickness"},
                )
