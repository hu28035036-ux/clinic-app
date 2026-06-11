from typing import Any, List

from pydantic import BaseModel, Field


class RevenueRecordEntry(BaseModel):
    record_date: str
    category_id: str = ""
    total_medical_fee: int = 0
    nhis_burden_total: int = 0
    cash_amount: int = 0
    cash_counts: dict[str, int] | None = None
    card_amount: int = 0
    receivable_income: int = 0
    transfer_amount: int = 0
    unpaid_amount: int = 0
    health_living_fee: int = 0
    certificate_amount: int = 0
    disability_fund: int = 0
    uninsured_amount: int = 0
    meal_amount: int = 0
    other_amount: int = 0
    discount_amount: int = 0
    free_amount: int = 0
    cash_expense_amount: int = 0
    field_memos: dict[str, str] | None = None
    memo: str = ""


class RevenueGridIn(BaseModel):
    date_from: str
    date_to: str
    category_id: str = ""
    entries: List[RevenueRecordEntry] = Field(default_factory=list)


class DailyReportField(BaseModel):
    id: str = ""
    label: str = ""
    type: str = "long_text"
    value: Any = ""
    sort_order: int = 0


class DailyReportIn(BaseModel):
    report_date: str
    selected_treatment_codes: List[str] = Field(default_factory=list)
    custom_fields: List[DailyReportField] = Field(default_factory=list)
