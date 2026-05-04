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
                        Boolean, LargeBinary, UniqueConstraint)
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
    hire_date = Column(String(10))  # YYYY-MM-DD, nullable
    can_eswt = Column(Boolean, default=True)
    can_manual = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    # 20-3-2 (post-19-P / F-11): 권한 등급. 'staff' / 'admin' / 'super' (3등급).
    # 기존 admin 로그인 / require_admin 흐름은 별개 — 본 컬럼은 *직원 권한 메타*.
    permission_level = Column(String(20), nullable=False, default="staff")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="therapist",
                                foreign_keys="Appointment.therapist_id")


class EmployeeLeave(Base):
    __tablename__ = "employee_leaves"
    __table_args__ = (
        UniqueConstraint("employee_id", "leave_date", name="uq_employee_leave_date"),
    )
    id = Column(String(32), primary_key=True, default=uid)
    employee_id = Column(String(32), ForeignKey("employees.id"), nullable=False, index=True)
    leave_date = Column(String(10), nullable=False, index=True)
    leave_type = Column(String(10), default="full")
    leave_kind = Column(String(10), default="annual")  # annual | monthly
    memo = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    employee = relationship("Employee")


class Treatment(Base):
    """치료항목 — DB 기반 동적 관리.

    code: 불변 식별자 (영문/숫자, 시드는 'injection' 등 하드코딩, 신규는 'tx_xxxx' 자동)
    name/short: 표시용 (변경 가능, short 는 약자 중복 거부)
    role: doctor | therapist (배타)
    count_increment: 완료 시 누적 +N (모든 항목 1카운트 — docs/specs/03 참조)
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
    # 20-3-1 (post-19-P / F-10): 노쇼 별도 필드. status="canceled" 와 동시 적용 가능.
    no_show = Column(Boolean, nullable=False, default=False)
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

    세션 09 확장 컬럼 (m008): outcome/error_detail/prompt_hash/response_hash/
    pii_filter_hits/hallucination_guard_hits/response_used/sms_sent.
    기존 status/error_kind 는 그대로 두되 신규 호출지는 outcome/error_detail
    만 채운다 (이전 호출지가 없으므로 호환 부담 없음).
    """
    __tablename__ = "ai_usage_logs"
    id = Column(String(32), primary_key=True, default=uid)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    provider = Column(String(20))
    model = Column(String(100))
    feature = Column(String(50))                 # 예: sms_validate, sms_draft, manual_search, manual_ask
    prompt_chars = Column(Integer, default=0)
    completion_chars = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)   # provider 가 알려주면 기록
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    status = Column(String(20))                  # legacy: ok | error | blocked
    error_kind = Column(String(50), default="")  # legacy: 차단/실패 이유 분류
    actor = Column(String(50), default="")
    # ── m008 확장 ──
    # outcome: m008 에서 VARCHAR(20) 으로 컬럼 생성됨. v1.3.3(m011 시점)에서
    # 'overwrite_not_acknowledged' (26자) 같은 긴 outcome 코드를 truncate 없이
    # 저장하기 위해 모델 차원만 String(50) 으로 확장. SQLite 는 VARCHAR(N)
    # 길이를 강제하지 않으므로(TEXT 로 저장) DB 마이그레이션 불필요. m008
    # 파일은 한 번 배포된 마이그레이션이므로 수정하지 않음.
    outcome = Column(String(50), default="")     # success | error | blocked | warning | overwrite_not_acknowledged 등
    error_detail = Column(String(500), default="")  # 사유 텍스트 (PII/원문 금지, 500자 컷)
    prompt_hash = Column(String(64), default="")   # sha256(마스킹 후 prompt). 원문 미저장.
    response_hash = Column(String(64), default="")  # sha256(마스킹 후 response). 원문 미저장.
    pii_filter_hits = Column(Integer, default=0)
    hallucination_guard_hits = Column(Integer, default=0)
    response_used = Column(Integer, default=0)   # 0=미정, 1=UI 채택 (v2 PATCH 로 갱신 예정)
    sms_sent = Column(Integer, default=0)        # 항상 0 (AI 직접 발송 금지 정책)


# ──────────────────────── 18-4: knowledge_chunks / knowledge_index_runs ────────────────────────
#
# 18-3 chunker 의 in-memory 산출물을 SQLite 에 영속화하기 위한 두 테이블.
# - KnowledgeChunk      : 매뉴얼 문서를 chunk 단위로 저장
# - KnowledgeIndexRun   : reindex 실행 이력 (요약/실패 path/에러 JSON)
#
# 정책 (docs/ai_rag_migration_plan.md §0/§2/§4):
#  - (doc_id, chunk_index) UNIQUE — 위치별 1 row.
#  - content_hash 동일하면 indexer 가 skip — UNIQUE 제약 아님 (서로 다른
#    문서가 동일 텍스트를 가질 수 있어 단일 컬럼 UNIQUE 부적합).
#  - reindex 실패 시 기존 row DELETE 금지 — indexer 가 어떤 분기에서도
#    db.delete() 를 호출하지 않음으로 보장.


class KnowledgeChunk(Base):
    """매뉴얼 문서의 chunk 영속화 (18-4).

    필드 매핑은 ``app.services.ai.rag.schemas.Chunk`` dataclass 와 정렬.
    프론트/응답 키와 1:1 매핑 의무는 없음 (internal-only). 검색 단계
    (18-5/18-6) 에서 retriever 가 본 row 를 source of truth 로 사용.
    """
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("doc_id", "chunk_index", name="uq_knowledge_chunks_doc_chunk"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(40), nullable=False, index=True)            # sha1(source_path) hex
    source_path = Column(String(500), nullable=False)                  # knowledge/<cat>/<file>.md
    category = Column(String(50), nullable=False, default="", index=True)  # "manuals" | "sms_guides"
    title = Column(Text, nullable=False, default="")                   # 문서 첫 heading
    heading = Column(Text, nullable=False, default="")                 # chunk 가 속한 가장 가까운 heading
    section_path = Column(Text, nullable=False, default="")            # "h1 > h2 > h3"
    chunk_index = Column(Integer, nullable=False)                      # 문서 내 0-based
    content = Column(Text, nullable=False)                             # 정규화된 본문
    content_hash = Column(String(64), nullable=False, index=True)      # sha256(content) hex 64자
    token_count = Column(Integer, nullable=False, default=0)           # len(content) 글자 수
    tags = Column(Text, nullable=False, default="")                    # csv (현재 빈 값)
    document_version = Column(String(64), nullable=False, default="")  # reindex 추적 (현재 빈 값)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeIndexRun(Base):
    """reindex 실행 이력 (18-4).

    한 reindex 호출당 1 row. ``status`` 는 다음 중 하나:
      - ``running`` : 진행 중 (정상 종료 시 다른 값으로 갱신)
      - ``success`` : 모든 문서 성공
      - ``partial`` : 일부 문서 실패, 나머지 성공 (기존 chunk 보존)
      - ``failed``  : 전체 실패 (loader 자체 실패 등)
      - ``skipped_in_progress`` : 다른 reindex 가 이미 실행 중이라 본 호출은 즉시 종료
    """
    __tablename__ = "knowledge_index_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(30), nullable=False, default="running")
    trigger = Column(String(20), nullable=False, default="manual")  # manual | startup | upgrade
    total_documents = Column(Integer, nullable=False, default=0)
    processed_documents = Column(Integer, nullable=False, default=0)
    failed_documents = Column(Integer, nullable=False, default=0)
    total_chunks = Column(Integer, nullable=False, default=0)
    inserted_chunks = Column(Integer, nullable=False, default=0)
    updated_chunks = Column(Integer, nullable=False, default=0)
    skipped_chunks = Column(Integer, nullable=False, default=0)
    failed_chunks = Column(Integer, nullable=False, default=0)
    failed_paths = Column(Text, nullable=False, default="")  # \n 구분
    errors = Column(Text, nullable=False, default="")        # JSON 배열 [{"path","error","stage"}]
    notes = Column(Text, nullable=False, default="")


# ──────────────────────── 18-5: knowledge_vectors ────────────────────────
#
# 18-5 vector store / embedding. chunk_id 기준 (provider, model) 별 1 row.
#
# 정책 (docs/ai_rag_migration_plan.md §3, docs/ai_rag_architecture_plan.md §3-18):
#  - (chunk_id, provider, model) UNIQUE — 같은 청크에 같은 provider+model 조합은 1개.
#  - content_hash 동일 (저장된 row 의 content_hash == 현재 chunk content_hash) → 재생성 skip.
#  - dimension 은 row 당 저장 — provider/model 변경 시 다른 row 로 분리되며,
#    검색 시 query dim 과 row dim 이 다르면 안전 skip.
#  - embedding 값은 ``embedding_json`` (Text) 으로 저장 — 18-5 시점은
#    FakeEmbeddingProvider dim=16 만 검증되므로 JSON 으로 충분 (< 1KB).
#    ``embedding_blob`` 은 향후 확장(외부 OpenAI 1536 dim 등) 슬롯 — 현재 NULL.
#  - chunk 가 삭제되면 ON DELETE CASCADE 로 vector 도 정리.


class KnowledgeVector(Base):
    """청크 임베딩 영속화 (18-5).

    필드 매핑은 ``docs/ai_rag_migration_plan.md`` §3 그대로. 검색 단계
    (18-6 hybrid) 에서 retriever 가 본 row 를 source of truth 로 사용.

    저장 형식:
      - 작은 dimension (~16) : ``embedding_json`` (JSON list[float] 문자열)
      - 큰 dimension (확장)  : ``embedding_blob`` (struct 패킹) — 18-5 시점 미사용
      두 컬럼 중 하나만 채움.
    """
    __tablename__ = "knowledge_vectors"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id", "provider", "model",
            name="uq_knowledge_vectors_chunk_provider_model",
        ),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(
        Integer,
        ForeignKey("knowledge_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(40), nullable=False)              # "fake" | "openai" | ...
    model = Column(String(100), nullable=False)                # "fake-embed-1" | "text-embedding-3-small" | ...
    dimension = Column(Integer, nullable=False)                # vector 길이
    embedding_json = Column(Text, nullable=True)               # JSON list[float] (작은 dim)
    embedding_blob = Column(LargeBinary, nullable=True)        # 확장 슬롯 (큰 dim)
    content_hash = Column(String(64), nullable=False, index=True)  # 임베딩 시점의 chunk content_hash
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
