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
    if case.loads.Pu < 0.0:
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
