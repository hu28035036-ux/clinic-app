"""modules.calendar — 캘린더 / 일정표 표시용 view-model facade (19-3 후보 구조).

본 패키지는 19-3 시점에 *신설* 되며, ``app/routers/api.py`` 의 캘린더 / 미니캘린더 /
금일예약환자 / 치료사 색상 / 휴무자 표시 데이터 조립 책임을 담당하는 *순수 helper*
를 제공한다. 19-3 본 세션 범위:

  - **신규 저장소 / 신규 router 추가 ⊥** — 기존 ``api.py`` 핸들러 무수정.
  - **예약 저장 / 수정 / 삭제 로직 변경 ⊥** — 본 모듈은 *읽기 / 표시* 만 담당.
  - **휴무 차단 규칙 변경 ⊥** — 19-5 leaves 분리 시점.
  - **availability 판단 ⊥** — 19-4 availability 분리 시점.
  - 표시용 view-model helper (``view_models.py``) 만 신설 — 향후 라우터가 채택할
    *순수 함수*. ``_serialize_appointment`` (api.py:186) / ``_serialize_employee``
    (api.py:169) / ``_lighten_hex`` (api.py:4316) 의 표시 로직을 동등 helper 로 추출.

19-3 분리 대상 (사용자 명시 8개 후보):
  1. 월/주/일 캘린더 표시용 예약 데이터 (FullCalendar event)
  2. 미니캘린더 표시용 데이터
  3. 금일예약환자 표시용 데이터 (today-items)
  4. 치료사별 색상 표시 데이터 (UNASSIGNED 색 fallback 포함)
  5. 휴무자 표시 데이터 (leave_type / leave_kind 표시 라벨)
  6. 지나간 일정 표시 여부 후보 (start < now)
  7. 예약 상태별 표시용 label / class 후보 (reserved / approved / canceled)
  8. 프론트에서 쓰는 view model 조립 (extendedProps 키 셋)

NOTE: modules.calendar 는 *서버 사이드 view-model* 만 — UI / FullCalendar / Alpine
JS 무수정. main.html 의 인라인 JS 로직은 본 19-3 범위 외 (post-19-P UI 분리 후속).

# COMPAT: ``_serialize_appointment`` 의 9키 (id / start / end / color / textColor /
#         extendedProps + extendedProps 16키) 100% 보존. 새 helper 는 *동등 출력*
#         보장 — 19-3 contract 테스트가 회귀 검증.

# SAFETY: ``extendedProps`` 안에 환자 PII (patient_name / patient_phone /
#         patient_birth_date / patient_memo) 가 포함되는 것은 *기존 동작* — 본 19-3
#         이 PII 추가/제거 ⊥. 카드 모달 표시용으로 필요한 최소 PII 만 노출.
#         로그 / audit_log 에는 PII 원문 부재 (기존 정책).

# RISK: FullCalendar event ID / start / end / status / version / treatment_codes /
#       extendedProps 키 변경 ⊥ — main.html 7331줄 + 인라인 JS 의존.
"""
