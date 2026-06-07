from typing import List

from pydantic import BaseModel, Field


class RevenueRecordEntry(BaseModel):
    record_date: str
    category_id: str = ""
    cash_amount: int = 0
    card_amount: int = 0
    transfer_amount: int = 0
    other_amount: int = 0
    memo: str = ""


class RevenueGridIn(BaseModel):
    date_from: str
    date_to: str
    category_id: str = ""
    entries: List[RevenueRecordEntry] = Field(default_factory=list)
