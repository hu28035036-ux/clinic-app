"""DB 모델 (단계 A: 치료항목 동적화)

변경:
- Treatment 테이블 부활 (DB 기반 관리)
- PatientTreatmentCount 신설 (Lazy 생성, 환자별 항목별 처방/완료 카운트)
- Patient: rx_*, done_* 필드 모두 제거
- Appointment.treatment_codes 는 그대로 유지 (코드 문자열 배열)
- TreatmentAssignment 그대로 (체외충격파/주사/연골주사 담당 추적)
"""
import uuid
from datetime import datetime
from sqlalchemy import (Column, String, Integer, Float, DateTime, ForeignKey, Text,
                        Boolean, UniqueConstraint)
from sqlalchemy.orm import relationship
from ..database import Base

def uid() -> str: return uuid.uuid4().hex

APPT_STATUSES = ("reserved", "approved", "canceled")


class Employee(Base):
    """의사 / 치료사 통합 직원."""
    __tablename__ = "employees"
    id = Column(String(32), primary_key=True, default=uid)
    name = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False, default="therapist")
    color = Column(String(20), nullable=False, default="#9CA3AF")
    active = Column(Boolean, default=True)
    birth_date = Column(String(10))
    phone = Column(String(30))
    can_eswt = Column(Boolean, default=True)
    can_manual = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="therapist",
                                foreign_keys="Appointment.therapist_id")


class EmployeeLeave(Base):
    __tablename__ = "employee_leaves"
    id = Column(String(32), primary_key=True, default=uid)
    employee_id = Column(String(32), ForeignKey("employees.id"), nullable=False, index=True)
    leave_date = Column(String(10), nullable=False, index=True)
    leave_type = Column(String(10), default="full")
    memo = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    employee = relationship("Employee")


class Treatment(Base):
    """치료항목 — DB 기반 동적 관리.

    code: 불변 식별자 (영문/숫자, 시드는 'injection' 등 하드코딩, 신규는 'tx_xxxx' 자동)
    name/short: 표시용 (변경 가능, short 는 약자 중복 거부)
    role: doctor | therapist (배타)
    count_increment: 완료 시 누적 +N (도수60=2, 나머지 1)
    show_in_patient: 환자 관리 표/편집 모달에 노출 여부
    """
    __tablename__ = "treatments"
    id = Column(String(32), primary_key=True, default=uid)
    code = Column(String(40), nullable=False, unique=True, index=True)
    name = Column(String(50), nullable=False)
    short = Column(String(10), nullable=False)
    default_minutes = Column(Integer, default=30)
    role = Column(String(20), nullable=False, default="therapist")  # doctor | therapist
    count_increment = Column(Integer, default=1)
    show_in_patient = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    # ── 수가/인센티브 (v1.2.3+) ──
    # price: 수가(원). 기본 0.
    # incentive_pct  : 치료사 인센티브 % (예: 10.0). NULL 이면 '입력 안 함'.
    # incentive_amount: 치료사 인센티브 고정 금액(원). NULL 이면 '입력 안 함'.
    # ⚠ pct 와 amount 는 **둘 중 하나만** 사용 (앱 레벨에서 강제).
    price = Column(Integer, nullable=False, default=0)
    incentive_pct = Column(Float, nullable=True)
    incentive_amount = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Patient(Base):
    """환자 — 카운트 필드는 PatientTreatmentCount 별도 테이블로 분리."""
    __tablename__ = "patients"
    id = Column(String(32), primary_key=True, default=uid)
    # 대량(수만 건) 검색 대응 — 이름/연락처에도 인덱스
    name = Column(String(50), nullable=False, index=True)
    birth_date = Column(String(10), index=True)
    phone = Column(String(30), index=True)
    chart_no = Column(String(30), index=True)
    # 성별: 'M' / 'F' / '' (빈값 = 미지정). 라디오로만 선택하므로 값 엄격히 제한.
    gender = Column(String(2), default="")
    memo = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="patient")
    counts = relationship("PatientTreatmentCount", back_populates="patient",
                          cascade="all, delete-orphan")


class PatientTreatmentCount(Base):
    """환자별·치료항목별 처방/완료 카운트 (Lazy 생성).

    - 처방 입력 또는 완료 누적이 발생할 때만 row 생성
    - 환자 편집 모달에서는 COALESCE(0) 으로 표시
    """
    __tablename__ = "patient_treatment_counts"
    id = Column(String(32), primary_key=True, default=uid)
    patient_id = Column(String(32), ForeignKey("patients.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    treatment_id = Column(String(32), ForeignKey("treatments.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    rx_count = Column(Integer, default=0)
    done_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="counts")
    treatment = relationship("Treatment")

    __table_args__ = (
        UniqueConstraint("patient_id", "treatment_id", name="uq_patient_treatment"),
    )


class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(String(32), primary_key=True, default=uid)
    # 환자 이력/예약 조회 성능 — 인덱스 필수
    patient_id = Column(String(32), ForeignKey("patients.id"), nullable=False, index=True)
    therapist_id = Column(String(32), ForeignKey("employees.id"), nullable=True, index=True)

    start_at = Column(DateTime, nullable=False, index=True)
    end_at = Column(DateTime, nullable=False)
    duration_min = Column(Integer, nullable=False, default=30)
    # JSON 배열 문자열: '["injection","eswt","manual30"]' (코드 문자열)
    treatment_codes = Column(Text, nullable=False, default="[]")

    status = Column(String(20), default="reserved", index=True)
    approved_at = Column(DateTime)
    approved_by = Column(String(50))

    memo = Column(Text, default="")
    is_new_patient = Column(Boolean, default=False)
    # 낙관적 락: 저장 시마다 +1. 클라이언트가 받은 값과 DB 값이 다르면 409
    version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    therapist = relationship("Employee", back_populates="appointments",
                             foreign_keys=[therapist_id])
    assignments = relationship("TreatmentAssignment", back_populates="appointment",
                               cascade="all, delete-orphan")


class TreatmentAssignment(Base):
    __tablename__ = "treatment_assignments"
    id = Column(String(32), primary_key=True, default=uid)
    appointment_id = Column(String(32),
                            ForeignKey("appointments.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    treatment_code = Column(String(40), nullable=False)
    handler_id = Column(String(32), ForeignKey("employees.id"), nullable=True)

    appointment = relationship("Appointment", back_populates="assignments")
    handler = relationship("Employee")

    __table_args__ = (
        UniqueConstraint("appointment_id", "treatment_code", name="uq_appt_tx"),
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, default=1)
    manual_slot_limit = Column(Integer, nullable=True)
    sms_template = Column(Text, default="")  # legacy: 단일 템플릿. 단계 F에서 SmsTemplate 테이블로 이동 예정
    # 자동 백업 설정 (단계 G에서 추가)
    auto_backup_enabled = Column(Boolean, default=True)
    auto_backup_interval_min = Column(Integer, default=60)
    auto_backup_keep_count = Column(Integer, default=30)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(32), primary_key=True, default=uid)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    node_id = Column(String(32))
    actor = Column(String(50))
    action = Column(String(50))
    entity_id = Column(String(32))
    detail = Column(Text, default="")


class SyncOp(Base):
    __tablename__ = "sync_ops"
    id = Column(String(64), primary_key=True)
    node_id = Column(String(32), nullable=False, index=True)
    entity = Column(String(30), nullable=False)
    entity_id = Column(String(32), nullable=False, index=True)
    op = Column(String(10), nullable=False)
    payload = Column(Text, default="{}")
    ts = Column(DateTime, default=datetime.utcnow, index=True)


class ManualCount(Base):
    """집계 수동 카운트 (v1.2.7+).
    체외충격파 등 당일 내방 환자처럼 예약 등록 없이 바로 진행한 경우,
    집계/통계 표에서 직원이 숫자만 입력하면 저장됨.
    (count_date, therapist_id, treatment_code) 당 1행. count 덮어쓰기.
    """
    __tablename__ = "manual_counts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    count_date = Column(String(10), nullable=False, index=True)   # 'YYYY-MM-DD'
    therapist_id = Column(String(32), nullable=True)              # NULL = 미배정
    treatment_code = Column(String(40), nullable=False)
    count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("count_date", "therapist_id", "treatment_code",
                         name="uq_manual_count_key"),
    )


class SmsSetting(Base):
    __tablename__ = "sms_settings"
    id = Column(Integer, primary_key=True, default=1)
    munjanara_id = Column(String(50), default="")
    munjanara_key = Column(String(100), default="")
    munjanara_pw = Column(String(100), default="")
    sender_phone = Column(String(30), default="")
    clinic_phone = Column(String(30), default="02-000-0000")
    clinic_name = Column(String(100), default="서울튼튼정형외과의원")
    # 문자나라 발송 API URL — 사용자 전체 공용 엔드포인트.
    # 2026-04-18 확인: https://munjanara.co.kr/send.sys (200 OK, 응답 형식 "코드|메시지")
    # 병원별로 다른 건 ID/비번/2차비번/발신번호뿐 — URL 은 동일.
    api_url = Column(String(500), default="https://munjanara.co.kr/send.sys")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SmsLog(Base):
    __tablename__ = "sms_logs"
    id = Column(String(32), primary_key=True, default=uid)
    patient_id = Column(String(32), ForeignKey("patients.id"), nullable=True)
    phone = Column(String(30))
    body = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    result = Column(String(30))
    detail = Column(Text, default="")


class SmsTemplate(Base):
    """문자 템플릿 (단계 F #15) — 예약 문자 탭에서 CRUD 관리.

    - sort_order 가 가장 낮은 활성 템플릿이 "1번 템플릿"
    - 신규 추가 시 1번 템플릿 본문이 기본값
    - 시드: 기본 템플릿 1개 자동 생성
    """
    __tablename__ = "sms_templates"
    id = Column(String(32), primary_key=True, default=uid)
    name = Column(String(50), nullable=False)
    body = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AiSetting(Base):
    """AI 기능 관리자 설정 (v1.3 단계 1).

    Provider 선택형 — openai / anthropic / local(v2 보류).
    기본값은 enabled=False — AI 가 켜질 때까지 기능 동작 X.

    api_key 는 DB 평문 저장 (Windows 단독 실행형, %APPDATA% 보호 영역).
    응답 직렬화 시에는 반드시 마스킹 — SmsSetting.munjanara_key 패턴 참조.
    """
    __tablename__ = "ai_settings"
    id = Column(Integer, primary_key=True, default=1)
    enabled = Column(Boolean, default=False)
    provider = Column(String(20), default="openai")  # openai | anthropic | local
    model = Column(String(100), default="")          # 예: gpt-4o-mini, claude-haiku-4-5
    api_key = Column(String(500), default="")
    base_url = Column(String(500), default="")       # 사설 엔드포인트(옵션)
    max_tokens = Column(Integer, default=512)
    temperature = Column(Float, default=0.3)
    # 외부 LLM 으로 PII (전화번호/생년월일/차트번호/메모) 전송 차단 스위치.
    # 기본 True — 끄려면 명시적으로 False 로 설정해야 함 (관리자 책임).
    pii_guard_enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AiUsageLog(Base):
    """AI 호출 사용량/감사 로그.

    의도: 비용 추적 + PII 누출 사고 시 추적 가능하도록 어떤 feature 가 어떤
    프롬프트 길이로 호출됐는지 기록. 프롬프트/응답 본문 자체는 저장하지
    않음 (저장하면 그 자체가 PII 저장소가 되어버림).
    """
    __tablename__ = "ai_usage_logs"
    id = Column(String(32), primary_key=True, default=uid)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    provider = Column(String(20))
    model = Column(String(100))
    feature = Column(String(50))                 # 예: sms_suggest, chat
    prompt_chars = Column(Integer, default=0)
    completion_chars = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)   # provider 가 알려주면 기록
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    status = Column(String(20))                  # ok | error | blocked
    error_kind = Column(String(50), default="")  # 차단/실패 이유 분류
    actor = Column(String(50), default="")
