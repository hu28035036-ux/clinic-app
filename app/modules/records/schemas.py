from pydantic import BaseModel, Field


class RecordTabSettingIn(BaseModel):
    label: str = ""
    category_id: str = ""


class RecordEntryIn(BaseModel):
    # v1.3.37+: tab_key = 기록필요 치료항목 code. 존재/기록필요 여부는 서비스에서 검증.
    tab_key: str
    record_date: str = Field(default="", pattern=r"^\d{4}-\d{2}-\d{2}$|^$")
    chart_no: str = ""
    patient_name: str = ""
    memo: str = ""
    employee_id: str


class RecordEntryUpdateIn(BaseModel):
    record_date: str = Field(default="", pattern=r"^\d{4}-\d{2}-\d{2}$|^$")
    chart_no: str = ""
    patient_name: str = ""
    memo: str = ""
    employee_id: str
