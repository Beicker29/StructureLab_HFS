"""Shared input policy; engineering relationships remain in domain.validation."""
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


# JSON numbers only: bool and numeric strings are not engineering magnitudes.
FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]
PositiveNumber = Annotated[FiniteNumber, Field(gt=0)]
NonNegativeNumber = Annotated[FiniteNumber, Field(ge=0)]
UnitFactor = Annotated[PositiveNumber, Field(le=1)]
PositiveCount = Annotated[int, Field(strict=True, gt=0)]
NonBlankString = Annotated[str, Field(strict=True, pattern=r"\S")]


class InputModel(BaseModel):
    """One policy for cases, nested objects and normalized section records.

    Revalidation prevents model_copy/model_construct or later mutations from
    bypassing the engine boundary. These Pydantic escape hatches are not trusted
    input APIs. Output models deliberately do not inherit this policy.
    """

    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, validate_default=True,
        revalidate_instances="always",
    )
