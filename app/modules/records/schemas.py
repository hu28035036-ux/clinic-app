from pydantic import BaseModel, Field


class RecordTabSettingIn(BaseModel):
    label: str = ""
    category_id: str = ""


class RecordEntryIn(BaseModel):
    tab_key: str = Field(pattern="^(manual|carm)$")
    chart_no: str = ""
    patient_name: str = ""
    employee_id: str
