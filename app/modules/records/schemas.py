from pydantic import BaseModel, Field


class RecordTabSettingIn(BaseModel):
    label: str = ""
    category_id: str = ""


class RecordEntryIn(BaseModel):
    tab_key: str = Field(pattern="^(manual|carm|review_event)$")
    record_date: str = Field(default="", pattern=r"^\d{4}-\d{2}-\d{2}$|^$")
    chart_no: str = ""
    patient_name: str = ""
    employee_id: str


class RecordEntryUpdateIn(BaseModel):
    record_date: str = Field(default="", pattern=r"^\d{4}-\d{2}-\d{2}$|^$")
    chart_no: str = ""
    patient_name: str = ""
    employee_id: str
