"""modules.ai.commands — AI 자연어 명령 (Preview / Approval / Execute) 후보 구조 (19-13 신규).

19-13 본 세션 범위:
  - **schemas.py** : AI commands 응답 키 contract (action/parse/preview/execute,
    sms/draft, manual/search/ask 응답) + INTENT_NAMES + reason_code 셋.
  - **safety.py** : Safety 게이트 helper (PII / no_sources / low_confidence /
    unknown_feature / multi_command — services/ai/action_leave 의 ``_pre_gate``
    + sms_draft 의 ``assert_safe_for_external`` + manual_qa 의 hallucination
    guard 와 byte-equivalent reason_code 셋).
  - **preview.py** : Preview 결과 dict 빌더 + ``_serialize_parse_result`` /
    ``_serialize_preview_result`` (router 의 byte-equivalent helper).
  - **executor.py** : Execute 결과 dict 빌더 + HTTP 상태 코드 매핑 (router 의
    byte-equivalent helper). 실제 ``EmployeeLeave`` upsert 는 services/ai/
    action_leave.py 가 단일 원천 — 본 helper 는 응답 형식만.
  - **service.py** : Approval 토큰 정책 상수 (TTL 120s / version 1 / prefix v1)
    재노출 + 알려진 outcome 셋.
  - **adapters.py** : appointments / leaves / sms 모듈 경계 호출 helper —
    현재는 *문서화 + 후속 검토 표기* (19-x 에서 실제 adapter 본격 채택).

19-13 본 세션 범위 *외*:
  - ``app/services/ai/action_leave.py`` (917줄) — 본체 무수정.
  - ``app/services/ai/sms_draft.py`` (469줄) — 본체 무수정.
  - ``app/services/ai/manual_qa.py`` (78줄) — 본체 무수정.
  - ``app/routers/ai.py`` (929줄) — 13 endpoint 본체 무수정.

# COMPAT: 본 패키지의 모든 helper / contract 는 ``app/routers/ai.py`` /
#         ``app/services/ai/{action_leave,sms_draft,manual_qa}.py`` 의 인라인
#         dict / 시그니처 / 응답 key 와 *byte-equivalent*. 라우터 / 서비스 본체
#         채택 ⊥.

# SAFETY: ``safety.py`` 의 ``REASON_CODES_PROVIDER_BLOCKED`` 셋 (pii_detected /
#         no_sources / low_confidence / unknown_feature / llm_skipped_*) 는
#         **provider 호출 0회 정책** 단일 원천. ``len(provider.calls) == 0``
#         단언 정합.

# SAFETY: ``safety.py`` 의 ``REASON_CODES_APPROVAL_REQUIRED`` 셋 (approval_required /
#         execution_blocked / not_confirmed / overwrite_not_acknowledged /
#         token_*) 는 **승인 없는 DB 변경 차단 정책** 단일 원천.

# RISK: ``preview.py`` / ``executor.py`` 분리 — Preview 는 read-only, Execute 는
#       ``confirm=True`` + HMAC 토큰 검증 통과 시에만. 본 19-13 가 정책 변경 ⊥.

# NOTE: AI 예약 흐름 (``ai_reservation_create`` / ``ai_reservation_preview`` /
#       ``ai_reservation_execute``) 은 *현재 미구현* — schemas.py 의 INTENT_NAMES
#       / reason_codes 에 후보 키만 표기 (TODO(19-x) 마커).
"""
