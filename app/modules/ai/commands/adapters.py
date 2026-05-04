"""AI commands → appointments / leaves / sms 모듈 경계 호출 helper (19-13 신규).

본 19-13 본 세션 *비-목표* — 19-x 후속 검토용 *문서화 + 경계 표기*. 현재 AI 흐름
(action_leave / sms_draft / manual_qa) 은 ``app/services/ai/`` 가 직접 ORM /
helper 를 호출. 본 모듈은 *어떤 모듈 경계로 채택할지* 만 명시.

# COMPAT: 본 모듈은 *문서화* 만 — 라우터 / 서비스 본체 채택 ⊥. 19-x 채택 시점에
#         실제 adapter 본격 분리.

# SAFETY: 본 모듈은 *상수 셋 / 분류* 만 — DB 변경 ⊥, LLM 호출 ⊥.

# RISK: AI 가 사용자 승인 없이 예약 / 휴무 / 문자 실행 ⊥ 정책 — 본 adapter 모듈은
#       *Preview / Approval / Execute 경계* 를 통해서만 호출 가능 정책 가드.

# NOTE: 19-x 채택 시 본 adapter 가 ``app/modules/{appointments,leaves,sms}/``
#       service 를 호출하도록 분리. 현재는 ``app/services/ai/action_leave.py``
#       가 ORM 직접 호출 (services/ai/leaves 헬퍼 부재 — 19-5 leaves 모듈 합류
#       시점에 채택 검토).
"""
from __future__ import annotations


# ──────────────── AI 흐름 → 모듈 매핑 (19-x 채택 후보) ────────────────

# AI 휴무 흐름 (action_leave) 가 호출해야 할 모듈 셋.
# COMPAT: 현재는 services/ai/action_leave.py 가 ORM 직접 호출 (Employee / EmployeeLeave /
#         Appointment). 19-x 에서 modules/leaves / modules/therapists 경계로 분리 검토.
AI_LEAVE_FLOW_MODULES: frozenset[str] = frozenset({
    "app.modules.leaves",       # EmployeeLeave upsert / overwrite
    "app.modules.therapists",   # Employee 매칭 (이름 → id)
    "app.modules.appointments", # 같은 날짜 예약 충돌 검사
})

# AI 문자 흐름 (sms_draft) 가 호출해야 할 모듈 셋.
# COMPAT: 현재는 services/ai/sms_draft.py 가 ORM 직접 호출 (Appointment / Patient /
#         Employee / Treatment / SystemSetting). 19-x 에서 modules/sms / modules/
#         appointments / modules/patients / modules/therapists / modules/treatments
#         경계로 분리 검토.
AI_SMS_DRAFT_FLOW_MODULES: frozenset[str] = frozenset({
    "app.modules.sms",          # 템플릿 / provider 경계 (FakeSmsProvider 만 — 19-10)
    "app.modules.appointments", # 예약 정보 read-only
    "app.modules.patients",     # 환자명 / token
    "app.modules.therapists",   # 치료사명 read-only
    "app.modules.treatments",   # 치료항목명 read-only
})

# AI 매뉴얼 흐름 (manual_qa) 가 호출해야 할 모듈 셋.
# COMPAT: 현재는 services/ai/manual_qa.py 가 services/rag/search 와 services/ai/rag/
#         pipeline 호출. 19-x 에서 modules/ai/rag 경계로 분리 검토.
AI_MANUAL_QA_FLOW_MODULES: frozenset[str] = frozenset({
    # AI / RAG 본체는 services/ai/{rag,knowledge,vector}/ 단일 원천 — 19-x 채택 시점에
    # modules/ai/rag 으로 이동 검토. 현재는 미분리.
    "app.services.ai.rag",
    "app.services.ai.knowledge",
    "app.services.ai.vector",
    "app.services.rag",
})


# ──────────────── AI 흐름 → 직접 호출 금지 정책 ────────────────

# RISK: AI 가 다음 모듈 / 서비스를 *직접 호출 ⊥* 정책 — 사용자 승인 / Approval
#       단계를 거쳐야 함.
AI_DIRECT_CALL_FORBIDDEN: frozenset[str] = frozenset({
    # 외부 SMS 발송 — sms_draft 는 초안만 생성, 발송은 별도 /api/sms/send (관리자).
    "external_sms_send",
    # DB 직접 commit — Preview 단계는 read-only.
    "db_commit_in_preview",
    # 운영 DB 파일 직접 read/write — modules/backup 정책 단일 원천.
    "operational_db_file_io",
    # 외부 LLM/Embedding API 직접 호출 — local_only / no_sources / low_confidence /
    # PII 분기에서 호출 ⊥.
    "llm_call_in_local_only",
    "llm_call_with_pii",
    "llm_call_without_sources",
    "llm_call_with_low_confidence",
})


# ──────────────── AI 흐름 → 후속 검토 (현재 미구현) ────────────────

# TODO(19-x): AI 예약 흐름 채택 — 자연어 → 예약 생성 / 수정 / 취소.
#             modules/appointments / modules/availability / modules/patients /
#             modules/therapists / modules/treatments / modules/leaves 경계.
AI_RESERVATION_FLOW_MODULES_TODO: frozenset[str] = frozenset({
    "app.modules.appointments",
    "app.modules.appointments.availability",
    "app.modules.patients",
    "app.modules.therapists",
    "app.modules.treatments",
    "app.modules.leaves",  # 휴무 충돌 검사
})

# TODO(19-x): AI SMS 일괄 발송 흐름 채택 — 환자 그룹 → 발송 대상 추출 + 초안
#             일괄 생성 + 사용자 승인 후 발송.
AI_SMS_BATCH_FLOW_MODULES_TODO: frozenset[str] = frozenset({
    "app.modules.sms",
    "app.modules.appointments",
    "app.modules.patients",
})
