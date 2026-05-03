"""modules.leaves — 휴무 도메인 후보 구조 (19-5 신규).

19-5 본 세션 범위:
  - **rules.py** : 휴무 도메인 규칙 (LEAVE_TYPE 상수 / 종일·반차 차단 판정 / 차단 사유 메시지).
    19-4 ``app.modules.appointments.availability`` 의 휴무 helper 와 byte-equivalent —
    19-5 contract 테스트가 두 경로의 동등성을 검증.
  - **repository.py** : 휴무 row 조회 read-only helper (DB 세션 받음).
  - **service.py** : ``_upsert_employee_leave_core`` 의 *동등 service helper* +
    응답 dict 빌더 (employee / therapist alias).

19-5 본 세션 범위 *외* (라우터 / 서비스 본체 무수정):
  - ``app/routers/api.py`` 의 휴무 핸들러 + ``_upsert_employee_leave_core`` 본체 무수정.
  - ``app/services/ai/action_leave.py`` 의 import 경로 (``from ...routers.api import
    _upsert_employee_leave_core``) 무수정 — AI 휴무 등록 흐름 보존 (사용자 명시 "기존
    휴무 AI 동작 변경 금지").
  - ``app/modules/appointments/availability.py`` 무수정 (사용자 명시 "availability 로직
    대규모 재작성 ⊥") — leaves.rules 와 byte-equivalent 함을 contract 테스트로 검증.

# COMPAT: 기존 ``app/routers/api.py`` 의 모든 휴무 핸들러 + AI action_leave 흐름 그대로
#         동작. 본 패키지는 *helper 만* 제공 — 라우터에서 채택 ⊥. 19-9 appointments
#         본체 분리 시점에 점진적 채택.

# SAFETY: 본 모듈은 *판정 / 조회 / 직렬화* 만 — 실제 DB 변경은 ``service.upsert_*`` 가
#         담당하지만 라우터 미채택 (라우터의 ``create_employee_leave`` / ``bulk-set`` 본체
#         가 그대로 변경 책임). 환자 PII 미참조 (employee_id / 날짜 / leave_type 만).

# NOTE: 휴무 표시 (19-3 calendar/view_models.py:LEAVE_TYPE_LABELS) ↔ 예약 차단 (19-4
#       availability.py:is_leave_blocking) ↔ 도메인 규칙 (19-5 leaves/rules.py) 의 LEAVE_TYPE
#       기준이 일치해야 함. 19-5 contract 테스트가 LEAVE_TYPE_FULL/AM/PM 동일성 검증.

# RISK: ``_upsert_employee_leave_core`` 는 휴무 등록의 *단일 진실원천* — leaves API +
#       AI action_leave 두 경로가 같이 호출. 19-5 시점에는 본체 무수정 (라우터에서 import
#       경로 갱신은 19-9). 본 모듈의 ``service.upsert_employee_leave`` 는 *동등 helper*
#       이며, 19-9 시점에 라우터 + AI action_leave 가 채택할 *후보* 다.
"""
