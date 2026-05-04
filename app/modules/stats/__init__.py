"""modules.stats — 통계 도메인 후보 구조 (19-11 신규).

19-11 본 세션 범위:
  - **rules.py** : 매칭 / mode 분류 / 카운트 증분 정책 상수 (시간 가중치 회귀 방지) +
    weekday 라벨. ORM / DB / 외부 API 미참조 — primitives 만 받음.
  - **repository.py** : 통계용 read-only 조회 helper (예약 / ManualCount /
    Treatment / Employee). DB 세션 호출자 주입, lazy import.
  - **aggregators.py** : 순수 집계 함수 (summary / by-hour / by-weekday /
    by-treatment / daily / aggregate). caller 가 row 리스트 + manual code 셋 주입.
  - **service.py** : 응답 dict 빌더 + 기간 해석기 (``_resolve_stats_range`` /
    ``_date_list`` byte-equivalent).
  - **schemas.py** : 통계 API 응답 키 contract 상수 (frozenset).

19-11 본 세션 범위 *외* (라우터 본체 / 통계 흐름 무수정):
  - ``app/routers/api.py`` 의 모든 통계 핸들러 *완전 무수정* — 본 패키지는
    *byte-equivalent helper* 만 제공. 라우터 채택은 19-12+ 시점 점진적.
  - 예약 / 환자 / 치료사 / 휴무 / 치료항목 / 문자 / AI / RAG 흐름 *완전 무수정*.
  - DB schema / migration *완전 무수정*.
  - UI / API URL / 응답 key *완전 무수정*.

# COMPAT: 기존 ``app/routers/api.py`` 의 모든 통계 핸들러 (`/stats/by-therapist` /
#         `/stats/manual-by-therapist` / `/stats/aggregate` / `/stats/daily-by-therapist` /
#         `/stats/summary` / `/stats/by-hour` / `/stats/by-weekday` /
#         `/stats/by-treatment` / `/stats/daily`) 그대로 동작. 본 패키지는 *helper 만*
#         제공 — 라우터에서 채택 ⊥. 19-11 contract 테스트가 인라인 동작과 본 helper
#         결과의 byte-equivalent 검증.

# SAFETY: 본 모듈은 *읽기 / 집계 / 응답 조립* 만 — DB 변경 ⊥. 환자 PII 응답 dict
#         빌드는 *기존 응답 그대로* (UI 가 평문 PII 필요한 흐름은 부재 — 통계는
#         counts 만 노출). 본 19-11 가 마스킹 정책 변경 ⊥.

# RISK: 시간 가중치 방식 (``manual30=1, manual60=2`` 같은 ``count_increment`` 합산)
#       으로 *되돌아가지 ⊥*. ``rules.py`` 의 ``MANUAL_COUNT_INCREMENT_PER_APPT = 1``
#       정책 상수가 명시적 가드 — UI / 예약 1건 = count 1 정책 보존. RISK 주석으로
#       모든 aggregator 에 명시.

# RISK: 응답 dict 키 변경 ⊥ — UI / 차트 / 표 모두 의존. ``schemas.py`` contract
#       상수 + 19-11 contract 테스트가 회귀 검출.

# NOTE: 현재 *취소 / 노쇼 / 의사별 통계* 는 부분 구현 (``canceled`` 카운트 +
#       ``stats_by_therapist`` 의 doctor 필터) — 본 19-11 가 *추가 구현 ⊥*.
#       향후 검토 후보는 ``rules.py`` / ``__init__`` 의 ``TODO`` 마커로 명시.
"""
