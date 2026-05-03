"""modules.appointments — 예약 도메인 후보 구조 (19-4 ~ 19-9 점진적 신설).

19-4 본 세션 범위:
  - **availability** (예약 가능 여부 / 충돌 / 휴무 / 반차 / 점심창 / 낙관적 락) 만 신설.
  - 본체 (router / service / repository) 분리는 **19-9** 마지막 세션.
  - 도수 중복 / 휴무 차단 *백엔드 차단 코드 신설은 본 19-4 범위 외* — 사용자 지시문이
    "기존 규칙을 보존" 으로 명시. 본 모듈은 *순수 판정 helper* 만 정의 (실제 차단
    raise 는 호출자 책임).

19-9 본 세션 범위 (보수적 1차):
  - **rules.py** : 예약 상태 (reserved / approved / canceled) 전이 판정 + 취소 메모
    포맷 helper. ORM / DB 미참조 — primitives 인자만 받음.
  - **repository.py** : 예약 row read-only 조회 helper (단건 / 날짜 범위 / 환자별
    이력 / 마지막 예약 등) — DB 세션 호출자 주입, lazy import.
  - **service.py** : 라우터 응답 dict 빌더 (create / update / approve / cancel /
    revert / delete / split / assign / list / last / history / manual-history-summary).
  - **schemas.py** : 응답 키 contract 상수 (계약 회귀 보호 — UI 의존 키 절대 보호).

19-9 본 세션 범위 *외* (라우터 본체 / CRUD 수정 흐름 무수정):
  - ``app/routers/api.py`` 의 모든 예약 핸들러 *완전 무수정* — 본 패키지는
    *byte-equivalent helper* 만 제공. 라우터 채택은 19-10+ 시점 점진적.
  - 예약 생성 / 수정 / 삭제 / 취소 / 승인 / split / assign 본체 흐름 무수정.
  - availability / leaves / treatments / patients / therapists / 통계 / SMS / AI
    흐름 *완전 무수정* — 19-3 ~ 19-8 경계 그대로.
  - DB schema / migration *완전 무수정*.
  - UI / API URL / 응답 key *완전 무수정*.

NOTE: appointments 도메인은 *마지막에 분리* (19-P-2 §9 우선순위 14, DEC-F 정합).
core / availability / leaves / treatments / patients / staff 가 모두 안정화된 후
본 19-9 부터 본체 helper 도입 — *대규모 본체 이동은 19-10+ 시점*.

# COMPAT: 기존 ``app/routers/api.py`` 의 모든 appointment CRUD 핸들러 그대로 동작.
#         본 패키지는 *helper 만* 제공 — 라우터에서 채택 ⊥. 19-9 contract 테스트가
#         라우터 인라인 동작과 본 helper 결과의 byte-equivalent 검증.

# SAFETY: 본 모듈은 *읽기 / 판정 / 응답 조립* 만 — 실제 DB 변경 ⊥. 환자 PII 응답
#         dict 빌드는 *기존 응답 그대로* (UI / SMS 발송 / 통계 흐름이 평문 PII 필요).
#         본 19-9 가 마스킹 정책 변경 ⊥.

# RISK: 응답 key 변경 ⊥ — UI / SMS / 통계 / AI 모두 의존. ``schemas.py`` 의 contract
#       상수가 회귀 검출. 라우터 채택 시점 (19-10+) 에 점진 wire.
"""
