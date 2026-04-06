from ..models import SteelCase
from .errors import ValidationError

def validate_case(case: SteelCase):
    if case.lengths.Lb <= 0:
        raise ValidationError("Unbraced length Lb must be > 0.")
    if case.lengths.Lx <= 0 or case.lengths.Ly <= 0:
        raise ValidationError("Unbraced lengths Lx and Ly must be > 0.")
    if case.material.Fy <= 0:
        raise ValidationError("Yield strength Fy must be > 0.")
