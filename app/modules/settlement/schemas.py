from typing import List

from pydantic import BaseModel, Field


class SettlementGridEntry(BaseModel):
    performed_on: str
    employee_id: str
    treatment_id: str
    quantity: int = 0
    memo: str = ""


class SettlementGridIn(BaseModel):
    date_from: str
    date_to: str
    category_id: str = ""
    entries: List[SettlementGridEntry] = Field(default_factory=list)
