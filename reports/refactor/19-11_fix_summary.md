# 19-11 stats 분리 — 변경 요약

## 세션 이름

`19-11_stats_aggregation_boundary` — 통계 도메인 후보 helper (rules / repository /
aggregators / service / schemas) 분리. 라우터 본체 *완전 무수정*. **시간 가중치
회귀 방지 가드** 명시.

## 작업 목표 (한 문장)

`api.py` 의 9개 통계 핸들러 (`/stats/summary` / `/by-hour` / `/by-weekday` /
`/by-treatment` / `/daily` / `/aggregate` / `/by-therapist` /
`/manual-by-therapist` / `/daily-by-therapist`) 에 인라인 분산된 *집계 loop /
응답 빌더 / 매칭 lambda / 기간 해석기* 를 `app/modules/stats/` 후보 구조에
byte-equivalent 로 분리. **예약 1건 = count 1 정책 보존** (시간 가중치 회귀 가드).
*라우터 본체 / 통계 결과 / API 응답 key 완전 무수정*.

## 변경 파일 목록

| 파일 | 변경 종류 | 줄 수 |
|---|---|---:|
| `app/modules/stats/__init__.py` | 신규 | 43 |
| `app/modules/stats/rules.py` | 신규 | 182 |
| `app/modules/stats/repository.py` | 신규 | 201 |
| `app/modules/stats/aggregators.py` | 신규 | 271 |
| `app/modules/stats/service.py` | 신규 | 272 |
| `app/modules/stats/schemas.py` | 신규 | 170 |
| `tests/test_19_11_stats.py` | 신규 (90 cases) | 776 |
| `dosu_clinic.spec` | 수정 (+9) | — |
| `tests/test_pyinstaller_hidden_imports.py` | 수정 (+6) | — |

## 파일별 변경 요약

### `app/modules/stats/__init__.py` (신규, 43줄)

패키지 docstring — 19-11 본 세션 범위 / 범위 외 / COMPAT / SAFETY / NOTE / RISK.
**RISK 마커 — 시간 가중치 회귀 방지** 명시.

### `app/modules/stats/rules.py` (신규, 182줄)

순수 도메인 규칙 (DB / ORM / FastAPI 미참조).

- **카운트 정책 상수** : `MANUAL_COUNT_INCREMENT_PER_APPT = 1` /
  `TIME_WEIGHTED_COUNT_DENIED = True` (RISK 가드).
- **mode 상수** : `MODE_RESERVED` / `MODE_APPROVED` / `MODE_ALL` / `MODE_VALUES`.
- **treatment_code 매칭** : `treatment_code_matches` — `api.py` 의 `_matches`
  lambda byte-equivalent.
- **mode 분기** : `is_counted_for_mode` (by_hour/by_weekday) /
  `is_counted_for_treatment_mode` (by_treatment).
- **weekday 라벨** : `WEEKDAY_LABELS` / `weekday_label`.
- **미배정 sentinel** : `UNASSIGNED_SENTINEL` / `UNASSIGNED_LABEL`.
- **ESWT_CODE** : `app.models.constants` re-export.

### `app/modules/stats/repository.py` (신규, 201줄)

read-only 조회 helper (`app.models` lazy import).

- `list_appointments_in_range` — 기간 범위 예약.
- `list_approved_appointments_in_range` — approved 필터.
- `list_manual_count_rows_in_date_range` — ManualCount 기간 + 코드 필터.
- `list_manual_treatment_rows` / `list_manual_treatment_codes` —
  `_get_manual_treatment_rows` byte-equivalent (role 기반 판정).
- `get_active_eswt_treatment` — 활성 ESWT row.
- `list_all_treatments` / `list_therapist_employees` / `list_all_employees`.

### `app/modules/stats/aggregators.py` (신규, 271줄)

순수 집계 함수 (DB 미참조 — caller 가 row + manual_codes_set + parse_codes 주입).

- `aggregate_summary` — 5 카운트 (total/manual/approved/manual_approved/canceled).
- `aggregate_by_hour` — 24 시간대.
- `aggregate_by_weekday` — 7 요일.
- `aggregate_by_treatment` — 코드별 (한 예약 N코드 → 각 +1).
- `aggregate_daily` — 날짜별 8키 + manual_by_code / manual_approved_by_code.

**RISK 가드** : 모든 함수가 `MANUAL_COUNT_INCREMENT_PER_APPT` (= 1) 만 사용 —
시간 가중치 (`+= 2` / `*= 2`) 패턴 부재.

### `app/modules/stats/service.py` (신규, 272줄)

응답 dict 빌더 + 공용 helper.

- `StatsRangeError` — 기간 입력 오류 (라우터가 HTTPException 변환).
- `resolve_stats_range` — `_resolve_stats_range` byte-equivalent (date_from/to >
  year/month > 현재 월).
- `date_list` — `_date_list` byte-equivalent.
- `build_summary_response` — 12키.
- `build_by_hour_response` — 3키 + 24항목.
- `build_by_weekday_response` — 3키 + 7요일.
- `build_by_treatment_response` — 3키 + 내림차순 정렬.
- `build_daily_response` — 10키 envelope + 10키 항목.

### `app/modules/stats/schemas.py` (신규, 170줄)

응답 키 contract 상수 (frozenset).

- `SUMMARY_RESPONSE_KEYS` (12키), `BY_HOUR_*` / `BY_WEEKDAY_*` / `BY_TREATMENT_*`
  envelope + item, `DAILY_*` envelope + item, `AGGREGATE_*` + `BY_THERAPIST_*`.

### `tests/test_19_11_stats.py` (신규, 776줄)

90 cases — contract 검증.

1. 카운트 정책 상수 + 시간 가중치 회귀 방지.
2. mode / treatment_code 매칭 byte-equivalent.
3. weekday / 미배정 / ESWT.
4. resolve_stats_range / date_list byte-equivalent.
5-8. aggregators (summary / by_hour / by_weekday / by_treatment / daily).
9. service 응답 빌더.
10. repository DB 격리 fixture.
11. schemas contract.
12. 단방향 경계 D-4.
13. 라우터 9개 시그니처 무수정.
14. 기존 흐름 contract 검증 (6 endpoint).
15. stats 모듈 read-only + 외부 호출 ⊥.

### `dosu_clinic.spec` (수정, +9줄)

`hidden` 리스트에 19-11 신규 6개 모듈 등록.

### `tests/test_pyinstaller_hidden_imports.py` (수정, +6줄)

`EXPECTED_19_X_MODULES_MODULES` 에 6개 모듈 추가.

## 의도 / 이유

- **byte-equivalent 분리** : 통계 핸들러 응답 dict / 매칭 lambda / mode 분기 / 집계
  loop 가 `api.py` 안에 인라인으로 분산. 19-12+ 라우터 채택 시점에 본 helper 채택.
- **시간 가중치 회귀 방지** : `MANUAL_COUNT_INCREMENT_PER_APPT = 1` 정책 상수 +
  코드 패턴 검증 + 집계 결과 검증 (manual30 + manual60 = 2). CLAUDE.md "manual60
  = 1카운트 정책" 정합.
- **계약 회귀 보호** : `schemas.py` 의 contract 상수가 응답 키 셋 *임의 변경* 검출.
  UI / 차트 / 표 / SMS / AI 의존 키 보호.
- **stats 모듈 read-only 보장** : 모든 파일에 `db.commit` / `db.add` / `db.delete` /
  `db.flush` 부재 단위 테스트.
- **D-4 경계 보존** : `rules.py` / `aggregators.py` 는 ORM / DB / FastAPI 미참조.
  `repository.py` 만 `app.models` 함수 안 lazy import.

## compatibility wrapper / 라우터 무수정

- `app/routers/api.py` 본체 *완전 무수정* — 9개 통계 핸들러 그대로 동작.
- `tests/test_19_11_stats.py` 의 9개 시그니처 테스트가 라우터 함수 서명 무수정 검증.
- 응답 dict 키 / 타입 *완전 보존*.

## 수정 금지 범위 준수

| 금지 항목 | 준수 |
|---|---|
| 통계 집계 기준 변경 | ✅ aggregator byte-equivalent + 응답 키 contract |
| 시간 가중치 방식 회귀 | ✅ 정책 상수 + 패턴 검사 + 합계 검증 |
| count_increment 합산 방식 회귀 | ✅ aggregator 모두 += 1 만 사용 |
| stats 가 예약/환자/치료사/휴무/문자 상태 변경 | ✅ db.commit/add/delete 부재 검증 |
| 예약 API 응답 key 변경 | ✅ 19-9 무수정 |
| 통계 API 응답 key 변경 | ✅ schemas contract + endpoint test |
| 예약 생성/수정/삭제 변경 | ✅ 라우터 무수정 |
| 문자/SMS 변경 | ✅ 19-10 무수정 |
| AI/RAG 변경 | ✅ 무수정 |
| DB schema / migration | ✅ 무수정 |
| UI 디자인 | ✅ 무수정 |
| 운영 DB 접근 | ✅ 미접근 |
| 실제 외부 API 호출 | ✅ urllib/requests/httpx import 부재 |
| 기존 SMS AI / 휴무 AI | ✅ 무수정 |

## 자동 수정 루프 횟수

**0회 코드 수정** — 90 / 90 contract 1회차 통과. ruff I001 1건만 자동 보정 (테스트
파일 import 정렬).

## 5회 실패 여부

**미해당** — 1회차 통과.

## 위반 / 우회 없음

- `pyproject.toml` per-file-ignores 무수정.
- 운영 DB 직접 open 없음.
- 외부 API 호출 없음.
- `app.routers` 본체 무수정.
- DB schema / migration 무수정.
- 시간 가중치 방식 회귀 없음.
