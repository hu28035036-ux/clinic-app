"""modules.therapists — 치료사 / 직원 도메인 후보 구조 (19-8 신규).

19-8 본 세션 범위:
  - **rules.py** : 직원 역할 (doctor / therapist) 도메인 규칙 + 색상 상수 +
    치료사 / 의사 분류 / 활성 판정 helper. ORM / DB 미참조.
  - **repository.py** : ``Employee`` row read-only 조회 helper (DB 호출자 주입,
    lazy import). ``list_employees`` / ``list_therapists`` / ``list_doctors`` /
    활성 필터 / 단건 조회.
  - **service.py** : ``api.py:_serialize_employee`` 의 *동등 helper* + 치료사
    alias 응답 dict + 통계용 ``id → name`` 맵 빌더.

19-8 본 세션 범위 *외* (라우터 / 서비스 본체 무수정):
  - ``app/routers/api.py`` 의 모든 직원 / 치료사 / 휴무 / 통계 핸들러 무수정.
  - 휴무 / 예약 / 통계 / 문자 / AI 흐름 무수정.
  - DB schema / migration 미수정 — ``Employee`` 모델 그대로.

# COMPAT: 기존 ``app/routers/api.py`` 의 ``_serialize_employee`` (line 169) /
#         ``list_employees`` (line 1009) / ``list_therapists_alias`` (line 1175) /
#         통계 ``id→name`` 매핑 (line 3527 / 3609 / 3702 / 3787) 그대로 동작.
#         본 패키지는 *helper 만* 제공 — 라우터에서 채택 ⊥ (19-9 시점 후보).

# SAFETY: 본 모듈은 *조회 / 직렬화 / 분류* 만 — 실제 DB 변경 (CRUD) ⊥. 운영 DB
#         직접 open ⊥ (caller dependency 의 격리 세션만 사용). 환자 PII 미참조 —
#         직원 정보 (name / role / color / phone / hire_date / can_eswt / can_manual)
#         만 다룸.

# NOTE: 치료사 색상 fallback (``UNASSIGNED_THERAPIST_COLOR = "#9CA3AF"``) 은
#       19-3 ``calendar.view_models`` 의 단일 진실원천을 *re-export* — 본 모듈이
#       독자 정의 ⊥. 캘린더 표시 ↔ 직원 직렬화 응답의 색상 fallback 정합 보장.

# RISK: ``Employee`` 는 의사 / 치료사 두 역할을 *공유 테이블* 로 관리 — role 필드로
#       분류. doctors / medical_staff 후보 경계는 *현재 기능* 인지 / *후속 검토*
#       인지 명확히 구분 (rules.py 의 NOTE / TODO 마커).
#
# TODO(19-9): 라우터 채택 + ``stats_by_therapist`` 의 doctor 분기 정합 검토.
# TODO(후속 검토): doctors 전용 진료과 / 진료실 / 오더 / 처방 / EMR 연동은
#                 *현재 기능 부재* — 향후 ``app.modules.doctors`` 또는
#                 ``app.modules.medical_staff`` 로 분리 후보. 본 19-8 시점에는
#                 *기능 부재* 만 문서화 + 본 ``therapists`` 가 양쪽 역할의 *공통*
#                 직원 도메인을 다룸.
"""
