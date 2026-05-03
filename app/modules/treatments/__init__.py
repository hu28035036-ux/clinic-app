"""modules.treatments — 치료항목 / 완료체크 도메인 후보 구조 (19-6 신규).

19-6 본 세션 범위:
  - **rules.py** : 치료항목 분류 도메인 규칙 (role / ESWT 분리 / manual 정의 /
    완료체크 대상 판정 — *시간 가중치 ⊥*, 항목별 개별 체크 원칙).
  - **repository.py** : 치료항목 row read-only 조회 (DB 세션 호출자 주입).
  - **service.py** : ``_serialize_treatment`` / ``_normalize_incentive`` /
    ``_build_treatment_meta`` 동등 helper.
  - **completion_rules.py** : ``_bump_patient_count`` 의 *동등 service helper* +
    카운트 ±N 정책 (0 미만 방지 / `manual60`=1 정책 보존 — 시간 가중치 합산 ⊥).

19-6 본 세션 범위 *외* (라우터 / 서비스 본체 무수정):
  - ``app/routers/api.py`` 의 모든 치료항목 / 예약 / 통계 핸들러 무수정.
  - ``_bump_patient_count`` (api.py:1934) 본체 무수정 — 19-9 시점 채택.
  - 통계 집계 기준 무수정 — 19-11 stats 분리 시점.
  - SMS / AI / 휴무 / availability 흐름 무수정.

# COMPAT: 기존 ``app/routers/api.py`` 의 모든 치료항목 / 완료체크 / 통계 흐름 그대로
#         동작. 본 패키지는 *helper 만* — 라우터에서 채택 ⊥.

# SAFETY: 본 모듈은 *판정 / 조회 / 직렬화* 만 — 실제 DB 변경 ⊥. 환자 PII 미참조.
#         ``_bump_patient_count`` 동등 helper 는 *호출자가 commit 책임* (현재 라우터
#         패턴 정합).

# NOTE: 도수30 / 도수60 / 도수90 / ESWT 등은 *각각 독립 치료항목* 이며 각각 독립
#       체크 대상 (``count_increment`` 합산 ⊥). 현재 ``manual60`` 의 ``count_increment``
#       는 1 (시간 가중치 ⊥, 항목별 개별 체크 — CLAUDE.md 정합).

# RISK: 시간 가중치 (``count_increment=2`` 등) 도입 ⊥ — 사용자 명시 "시간 가중치 방식
#       으로 되돌리는 것 금지". 통계 집계와 완료 카운트 정합도 시간 가중치 도입 시
#       깨짐. 본 19-6 helper 는 ``count_increment`` 를 *그대로 노출* — 정책 결정은
#       관리자 UI / 시드 정합 (CLAUDE.md `manual60`=1).
"""
