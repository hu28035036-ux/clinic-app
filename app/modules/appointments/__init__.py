"""modules.appointments — 예약 도메인 후보 구조 (19-4 ~ 19-9 점진적 신설).

19-4 본 세션 범위:
  - **availability** (예약 가능 여부 / 충돌 / 휴무 / 반차 / 점심창 / 낙관적 락) 만 신설.
  - 본체 (router / service / repository) 분리는 **19-9** 마지막 세션.
  - 도수 중복 / 휴무 차단 *백엔드 차단 코드 신설은 본 19-4 범위 외* — 사용자 지시문이
    "기존 규칙을 보존" 으로 명시. 본 모듈은 *순수 판정 helper* 만 정의 (실제 차단
    raise 는 호출자 책임).

NOTE: appointments 도메인은 *마지막에 분리* (19-P-2 §9 우선순위 14, DEC-F 정합).
core / availability / leaves / treatments / patients / staff 가 모두 안정화된 후
19-9 에서 본체 이동.

# COMPAT: 기존 ``app/routers/api.py`` 의 모든 appointment CRUD 핸들러 그대로 동작.
#         본 패키지는 *helper 만* 제공 — 라우터에서 채택 ⊥.

# SAFETY: 본 모듈은 *읽기 / 판정* 만 — 실제 DB 변경 ⊥. 환자 PII 미참조 (id 만).
"""
