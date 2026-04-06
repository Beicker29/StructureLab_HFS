from typing import List
from pydantic import BaseModel
from .models import CheckResult, CheckStatus

class EngineResult(BaseModel):
    checks: List[CheckResult]
    status: CheckStatus
