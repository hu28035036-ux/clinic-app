"""modules.ai — AI / RAG 도메인 후보 구조 (19-13 신규).

19-13 본 세션 범위:
  - **commands/** : AI commands (자연어 명령) Preview / Approval / Execute 경계
    helper. 응답 키 contract / reason_code 셋 / safety 게이트 helper / preview /
    executor adapter.

19-13 본 세션 범위 *외* (라우터 / 서비스 본체 무수정):
  - ``app/routers/ai.py`` 의 13 endpoint *완전 무수정*.
  - ``app/services/ai/action_leave.py`` (917줄, parse / preview / execute / HMAC
    토큰) *완전 무수정*.
  - ``app/services/ai/sms_draft.py`` (469줄, make_draft / DraftContext / PII /
    환각 검증) *완전 무수정*.
  - ``app/services/ai/manual_qa.py`` (78줄, manual_search / ask_manual_question /
    validate_answer) *완전 무수정*.
  - ``app/services/ai/{provider,pii,prompts,validators,ai_logging,health,
    date_resolver,openai_client,anthropic_client}.py`` *완전 무수정*.
  - ``app/services/ai/{rag,knowledge,vector}/`` 패키지 *완전 무수정*.
  - DB schema / migration *완전 무수정*.
  - UI / API URL / 응답 key *완전 무수정*.

19-13 본 세션 *비-목표*:
  - AI 예약 (자연어 → 예약 생성) 흐름 — *현재 미구현*. commands.schemas 의
    INTENT_NAMES / reason_codes 에 후보 키만 표기, 실제 helper / preview /
    executor 는 19-x 후속.
  - 외부 LLM/Embedding 실제 호출 — 본 19-13 는 *추가 ⊥*.
  - 실제 SMS 발송 — 본 19-13 는 *추가 ⊥* (별도 ``/api/sms/send`` 관리자 흐름).

# COMPAT: 기존 ``app/routers/ai.py`` 의 13 endpoint (action/parse/preview/execute,
#         sms/{validate,draft}, manual/{search,ask}, health/status/providers/settings)
#         그대로 동작. 본 패키지는 *helper 만* 제공 — 라우터에서 채택 ⊥.

# COMPAT: 기존 ``app/services/ai/action_leave.py`` 의 ``parse`` / ``preview`` /
#         ``execute`` 시그니처 + HMAC 토큰 (TTL 120s, prefix v1) 정책 그대로 동작.
#         본 19-13 가 변경 ⊥.

# SAFETY: 본 패키지는 *Preview / Approval / Execute 경계 helper* 만 — 실제 LLM 호출 ⊥,
#         실제 DB 변경 ⊥, 실제 SMS 발송 ⊥. ``app/services/ai/`` 가 모든 본체 보유.

# SAFETY: 환자 / 직원 PII / 차트번호 / 전화번호 / 생년월일 / 이메일 / 메모 *원문
#         전송 / 로그 / 응답 노출 ⊥*. ``commands/safety.py`` 가 PII 차단 reason_code
#         정책 단일 원천. 실제 PII 마스킹은 ``services/ai/pii.py`` (변경 ⊥).

# SAFETY: AI api_key / 문자나라 계정 / sync_secret *원문 전송 / 로그 / 응답 ⊥*.
#         ``app/modules/admin/service.py`` 의 mask_* helper 와 정합.

# RISK: AI 가 사용자 승인 없이 DB 변경 ⊥ — ``commands/preview.py`` /
#       ``commands/executor.py`` 분리 정책으로 명확히. action_leave 흐름은
#       parse / preview = read-only + execute 만 ``confirm=True`` + HMAC 토큰
#       검증 통과 시 ``EmployeeLeave`` upsert 1행 (services/ai/action_leave.py
#       정책 단일 원천).

# RISK: AI 가 외부 SMS 직접 발송 ⊥ — sms_draft 는 ``needs_user_confirm=True`` 만
#       반환, 실제 발송은 별도 ``/api/sms/send`` (관리자 권한). 본 19-13 가 정책 변경 ⊥.

# RISK: local-first 정책 (``local_only`` 모드 → LLM/Embedding 호출 0,
#       ``no_sources`` / ``low_confidence`` / PII / unknown_feature → provider 호출 0)
#       은 ``services/ai/manual_qa.py`` / ``rag/pipeline.py`` 단일 원천. 본 19-13
#       가 정책 변경 ⊥. ``commands/safety.py`` 의 reason_code 셋이 정합.

# NOTE: 본 19-13 contract 테스트 (``tests/test_19_13_ai_commands.py``) 가
#       commands.schemas 의 응답 key / reason_code / 라우터 시그니처 무수정 검증.

# NOTE: AI 예약 흐름은 *후속 19-x* — 현재 helper 부재. ``commands.schemas`` 의
#       AI_RESERVATION_TODO 마커가 후속 검토 명시.

# TODO(19-x): AI 예약 자연어 → 예약 생성 흐름 (환자 검색 / 신환 등록 / 중복검사 /
#             치료항목 alias / 예약 충돌 검사 / preview / approval / execute) —
#             현재 미구현. commands.schemas 에 INTENT/reason_code 후보 셋만 표기.
"""
