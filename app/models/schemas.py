"""Pydantic 스키마 (단계 A)."""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict


class EmployeeCategoryIn(BaseModel):
    name: str
    color: str = "#9CA3AF"
    active: bool = True
    sort_order: int = 0
    default_can_doctor_treatment: bool = False
    default_can_manual: bool = True
    default_can_eswt: bool = True


class EmployeeCategoryOut(EmployeeCategoryIn):
    id: str
    model_config = ConfigDict(from_attributes=True)


class EmployeeIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    category_id: Optional[str] = None
    color: str = "#9CA3AF"
    active: bool = True
    birth_date: Optional[str] = None
    phone: Optional[str] = None
    hire_date: Optional[str] = None
    can_doctor_treatment_override: Optional[bool] = None
    can_manual_override: Optional[bool] = None
    can_eswt_override: Optional[bool] = None
    # Legacy inputs are accepted and converted to override values by the router.
    can_doctor_treatment: Optional[bool] = None
    can_eswt: Optional[bool] = None
    can_manual: Optional[bool] = None
    treatment_override_enabled: Optional[bool] = None
    treatment_ids: Optional[List[str]] = None


class EmployeeOut(EmployeeIn):
    id: str
    category_name: Optional[str] = None
    can_doctor_treatment: bool = False
    can_eswt: bool = True
    can_manual: bool = True
    permission_level: str = "staff"
    sort_order: int = 0
    model_config = ConfigDict(from_attributes=True)


class EmployeePermissionIn(BaseModel):
    """20-3-2 (post-19-P / F-11): 직원 권한 등급 변경 입력.

    # NOTE: 권장값 등급 = 'staff' / 'admin' / 'super' (3등급, viewer 미도입).
    # 라우터에서 EMPLOYEE_PERMISSION_LEVELS 상수로 검증.
    """
    permission_level: str


class EmployeeLeaveIn(BaseModel):
    employee_id: str
    leave_date: str
    leave_type: str = "full"
    leave_kind: str = "annual"   # annual | monthly
    memo: str = ""


class EmployeeLeaveOut(EmployeeLeaveIn):
    id: str
    class Config: from_attributes = True


class EmployeeDutyIn(BaseModel):
    employee_id: str
    duty_date: str
    memo: str = ""


class EmployeeDutyOut(EmployeeDutyIn):
    id: str
    class Config: from_attributes = True


# ─────── Treatment (치료항목) ───────

class TreatmentIn(BaseModel):
    name: str
    short: str
    category_id: Optional[str] = None
    default_minutes: int = 30
    role: str = "therapist"           # doctor | therapist, legacy compatibility
    count_increment: int = 1
    show_in_patient: bool = False
    active: bool = True
    sort_order: int = 0
    code: Optional[str] = None        # 신규 시 자동 생성
    # ── 수가/인센티브 ──
    # incentive_pct, incentive_amount 는 **둘 중 하나만** 유효 (API 에서 검증).
    price: int = 0
    incentive_pct: Optional[float] = None
    incentive_amount: Optional[int] = None
    # 기록 필요 — True 면 '기록' 탭에 노출되고 집계는 기록(record_entries) 기반.
    requires_record: bool = False


class TreatmentOut(BaseModel):
    id: str
    code: str
    name: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    short: str
    default_minutes: int
    role: str
    count_increment: int
    show_in_patient: bool
    active: bool
    sort_order: int
    price: int = 0
    incentive_pct: Optional[float] = None
    incentive_amount: Optional[int] = None
    class Config: from_attributes = True


# ─────── 환자 ───────

class PatientCountIn(BaseModel):
    """환자별 항목별 처방/완료 카운트 입력."""
    treatment_id: str
    rx_count: int = 0
    done_count: int = 0


class PatientIn(BaseModel):
    name: str
    birth_date: Optional[str] = None
    phone: Optional[str] = None
    chart_no: Optional[str] = None
    gender: Optional[str] = ""          # 'M' / 'F' / '' (빈값 = 미지정)
    memo: str = ""
    counts: List[PatientCountIn] = []   # 처방/완료 같이 업데이트


# ─────── 예약 ───────

class AssignmentIn(BaseModel):
    treatment_code: str
    handler_id: Optional[str] = None


class AppointmentIn(BaseModel):
    patient_id: str
    therapist_id: Optional[str] = None
    treatment_codes: List[str] = []
    start_at: datetime
    duration_min: int = 30
    memo: str = ""
    assignments: List[AssignmentIn] = []
    is_new_patient: bool = False
    # 20-3-5 (post-19-P / F-3): 자원 (치료실) FK. None = 자원 미지정
    resource_id: Optional[str] = None

class AppointmentUpdate(BaseModel):
    therapist_id: Optional[str] = None
    treatment_codes: Optional[List[str]] = None
    start_at: Optional[datetime] = None
    duration_min: Optional[int] = None
    memo: Optional[str] = None
    assignments: Optional[List[AssignmentIn]] = None
    is_new_patient: Optional[bool] = None
    version: Optional[int] = None  # 낙관적 락
    # 20-3-5 (post-19-P / F-3): 자원 (치료실) FK
    resource_id: Optional[str] = None

class AssignmentChange(BaseModel):
    treatment_code: str
    handler_id: Optional[str] = None
    version: Optional[int] = None  # 낙관적 락


class ApproveAction(BaseModel):
    approved_by: str = "원무과"
    version: Optional[int] = None  # 낙관적 락


class CancelAction(BaseModel):
    memo: str = ""
    version: Optional[int] = None  # 낙관적 락
    # 20-3-1 (post-19-P / F-10): 노쇼 동시 적용. True 시 obj.no_show=True 도 함께.
    no_show: bool = False


# ─────── 시스템 설정 ───────

class SystemSettingIn(BaseModel):
    manual_slot_limit: Optional[int] = None
    sms_template: Optional[str] = None
    auto_backup_enabled: Optional[bool] = None
    auto_backup_interval_min: Optional[int] = None
    auto_backup_keep_count: Optional[int] = None


# ─────── 기존 ───────

class ModeSelect(BaseModel):
    mode: str
    main_url: Optional[str] = None


class SyncBatch(BaseModel):
    ops: List[dict]
