from ..models import SteelCase
from .errors import ValidationError

def validate_case(case: SteelCase):
    if case.lengths.Lb <= 0:
        raise ValidationError("Unbraced length Lb must be > 0.")
    if case.lengths.Lx <= 0 or case.lengths.Ly <= 0:
        raise ValidationError("Unbraced lengths Lx and Ly must be > 0.")
    if case.material.Fy <= 0:
        raise ValidationError("Yield strength Fy must be > 0.")
    if case.material.Fu <= 0:
        raise ValidationError("Ultimate strength Fu must be > 0.")
    if case.material.E <= 0:
        raise ValidationError("Elastic modulus E must be > 0.")
    if case.factors.Kx <= 0 or case.factors.Ky <= 0:
        raise ValidationError("Effective length factors Kx and Ky must be > 0.")
    if case.factors.Cb <= 0:
        raise ValidationError("Cb must be > 0.")
