# 19-11 stats 분리 — Codex 검증 요청

## 1. 세션 이름

`19-11_stats_aggregation_boundary` — 통계 도메인 후보 helper 분리 (rules /
repository / aggregators / service / schemas).

## 2. 작업 목표

`api.py` 의 9개 통계 핸들러에 인라인 분산된 *집계 loop / 응답 빌더 / 매칭
lambda / 기간 해석기* 를 `app/modules/stats/` 후보 구조에 byte-equivalent 로 분리.
**예약 1건 = count 1 정책 보존** (시간 가중치 회귀 방지 가드 명시). *라우터 본체 /
통계 결과 / API 응답 key 완전 무수정*.

## 3. 변경 파일 목록

신규:
- `app/modules/stats/__init__.py` (43줄)
- `app/modules/stats/rules.py` (182줄)
- `app/modules/stats/repository.py` (201줄)
- `app/modules/stats/aggregators.py` (271줄)
- `app/modules/stats/service.py` (272줄)
- `app/modules/stats/schemas.py` (170줄)
- `tests/test_19_11_stats.py` (776줄, 90 cases)

수정:
- `dosu_clinic.spec` (+9, hidden imports 6개 모듈 등록)
- `tests/test_pyinstaller_hidden_imports.py` (+6, EXPECTED tuple 6개 추가)

라우터 / DB schema / migration / `app/routers/` 본체 — *무수정*.

## 4. 실제 이동 / 분리한 통계 집계 로직

| api.py 위치 | 본 19-11 helper | byte-equivalent 검증 |
|---|---|---|
| 모든 통계 핸들러의 `_matches` lambda | `rules.treatment_code_matches` | `test_treatment_code_matches_byte_equivalent[*]` (9 parametrize) |
| `stats_by_hour` mode 분기 (4093~4098) | `rules.is_counted_for_mode` | `test_is_counted_for_mode[*]` (13 parametrize) |
| `stats_by_treatment` mode 분기 (4192~4195) | `rules.is_counted_for_treatment_mode` | `test_is_counted_for_treatment_mode[*]` (7 parametrize) |
| `_resolve_stats_range` (3944~3968) | `service.resolve_stats_range` | `test_resolve_stats_range_byte_equivalent_with_api` |
| `_date_list` (3971~3978) | `service.date_list` | `test_date_list_byte_equivalent_with_api` |
| `stats_summary` loop (4013~4033) | `aggregators.aggregate_summary` | `test_aggregate_summary_*` (3 cases) |
| `stats_by_hour` loop (4087~4098) | `aggregators.aggregate_by_hour` | `test_aggregate_by_hour_*` (2 cases) |
| `stats_by_weekday` loop (4136~4147) | `aggregators.aggregate_by_weekday` | `test_aggregate_by_weekday_basic` |
| `stats_by_treatment` loop (4190~4200) | `aggregators.aggregate_by_treatment` | `test_aggregate_by_treatment_basic` |
| `stats_daily` loop (4256~4282) | `aggregators.aggregate_daily` | `test_aggregate_daily_basic` |
| `stats_summary` 응답 (4038~4053) | `service.build_summary_response` | `test_build_summary_response_keys_and_values` |
| `stats_by_hour` 응답 (4100~4102) | `service.build_by_hour_response` | `test_build_by_hour_response_keys` |
| `stats_by_weekday` 응답 (4150~4155) | `service.build_by_weekday_response` | `test_build_by_weekday_response_keys` |
| `stats_by_treatment` 응답 (4202~4210) | `service.build_by_treatment_response` | `test_build_by_treatment_response_sorted_desc` |
| `stats_daily` 응답 (4286~4310) | `service.build_daily_response` | `test_build_daily_response_keys` |
| `_get_manual_treatment_rows` (3732~3749) | `repository.list_manual_treatment_rows` | `test_list_manual_treatment_rows` |
| `_get_manual_therapy_codes` (3752~3754) | `repository.list_manual_treatment_codes` | `test_list_manual_treatment_codes` |
| 모든 통계 query 패턴 | `repository.list_*` | DB 격리 fixture 검증 |

## 5. service / repository / aggregators 책임 분리 방식

- **rules** : 순수 도메인 규칙 (DB / ORM 미참조). 매칭 lambda + mode 분기 +
  카운트 정책 상수 + weekday / 미배정 sentinel.
- **repository** : `Appointment` / `ManualCount` / `Treatment` / `Employee` 의
  read-only query (`app.models` lazy import).
- **aggregators** : 순수 집계 함수 (DB 미참조 — caller 가 row 주입).
- **service** : 응답 dict 빌더 + 공용 helper (`resolve_stats_range` / `date_list`).
- **schemas** : 응답 키 contract 상수 (frozenset).

## 6. compatibility wrapper 유지 여부

- `app/routers/api.py` 본체 *완전 무수정* — 9개 통계 핸들러 그대로 동작.
- 9개 시그니처 테스트 (parametrize) 가 라우터 함수 서명 무수정 검증.
- 응답 dict 키 / 타입 *완전 보존* — 6개 endpoint contract 검증 통과.

## 7. 수정 금지 범위 준수 여부

| 금지 항목 | 준수 |
|---|---|
| 통계 집계 기준 변경 | ✅ aggregator byte-equivalent + endpoint contract |
| 시간 가중치 방식 회귀 | ✅ 정책 상수 + 패턴 검사 + 합계 검증 |
| count_increment 합산 방식 회귀 | ✅ aggregator 모두 += 1 만 |
| stats 가 상태 변경 | ✅ db.commit/add/delete 부재 검증 |
| 예약 / 통계 API 응답 key 변경 | ✅ schemas contract |
| 예약 / 문자 / 휴무 / 치료항목 / AI 변경 | ✅ 19-3~19-10 모듈 무수정 |
| DB schema / migration | ✅ 무수정 |
| UI 디자인 | ✅ 무수정 |
| 운영 DB 접근 | ✅ 미접근 |
| 실제 외부 API 호출 | ✅ urllib/requests/httpx import 부재 |

## 8. 기존 통계 API 응답 key 유지 여부

| 응답 | contract | 검증 |
|---|---|---|
| `/stats/summary` | `SUMMARY_RESPONSE_KEYS` (12키) | ✅ |
| `/stats/by-hour` | `BY_HOUR_RESPONSE_KEYS` + item (3+3키) | ✅ |
| `/stats/by-weekday` | `BY_WEEKDAY_RESPONSE_KEYS` + item (3+3키) | ✅ |
| `/stats/by-treatment` | `BY_TREATMENT_RESPONSE_KEYS` + item (3+3키) | ✅ |
| `/stats/daily` | `DAILY_RESPONSE_KEYS` + item (10+10키) | ✅ |
| `/stats/aggregate` | `AGGREGATE_RESPONSE_KEYS` + item (6+5키) | ✅ |

## 9. 기존 통계 결과 유지 여부

라우터 본체 *완전 무수정* — 통계 결과는 라우터 인라인 loop 가 직접 계산. 본 19-11
의 aggregator 는 *byte-equivalent helper* 로 contract 테스트가 동등성 검증. 라우터
미채택 — 결과 유지.

## 10. 예약 기준 / 완료 기준 분리 유지 여부

- `MODE_RESERVED` / `MODE_APPROVED` / `MODE_ALL` 상수.
- `is_counted_for_mode` (by_hour/by_weekday) / `is_counted_for_treatment_mode`
  (by_treatment) — 분기 차이 정합.
- 라우터 인라인 분기와 byte-equivalent 검증 (20 parametrize cases).

## 11. 치료항목별 개별 체크 원칙 유지 여부

- `_serialize_treatment` (19-6) / `aggregate_by_treatment` 가 한 예약에 여러
  코드면 *각 코드마다* +1 — 합산 가중치 ⊥ (api.py 정합).
- `aggregate_daily` 의 `manual_by_code` / `manual_approved_by_code` 도 코드별
  개별 카운트.

## 12. 시간 가중치 방식으로 되돌아가지 않았는지 여부

**확정 가드**:
1. `rules.MANUAL_COUNT_INCREMENT_PER_APPT = 1` 상수.
2. `rules.TIME_WEIGHTED_COUNT_DENIED = True` 상수 (의도 명시).
3. `aggregators.py` 본체에 `+= 2` / `* 2` / `*= 2` 패턴 부재 — 단위 테스트 검증.
4. `test_aggregate_summary_unit_increment_only` — manual30 + manual60 = total 2
   (시간 가중치라면 1+2=3 이지만 1+1=2 가 정답).
5. CLAUDE.md "manual60 = 1카운트 정책" 정합.

## 13. stats 모듈의 상태 변경 여부

**없음**. 검증:
- `test_stats_module_does_not_use_session_commit_or_add` : 6개 stats 파일 어디에도
  `db.commit` / `db.add(` / `db.delete(` / `db.flush` 부재.
- `repository.py` 는 `db.query(...).all() / .first()` 만 사용.
- `aggregators.py` 는 DB 세션 자체 미사용 (caller 주입 row 만 처리).

## 14. 기존 예약 / 문자 / 휴무 / 치료항목 영향 여부

영향 없음:
- `app/routers/api.py` 본체 *완전 무수정*.
- 19-3 ~ 19-10 모듈 *완전 무수정*.
- AI / RAG / SMS draft 흐름 *완전 무수정*.
- 142 AI 회귀 테스트 통과 + 1335 전체 회귀 통과.

## 15. 운영 DB 보호 여부

`scripts/check_db_path.py` exit 0. 테스트 fixture 격리 강제.

## 16. 외부 API 호출 여부

**없음**. 검증:
- `test_stats_module_no_external_calls` : 6개 stats 파일에 `urllib.request` /
  `requests` / `httpx` import 라인 부재.

## 17. 순환참조 위험 여부

- `rules.py` ORM / DB / FastAPI 미참조.
- `aggregators.py` ORM / DB / FastAPI 미참조 (caller 가 row + parse_codes 주입).
- `repository.py` `app.models` 함수 안 lazy import.
- `service.py` `app.modules.stats.rules` 만 lazy import.
- `schemas.py` 외부 의존 ⊥.
- `app.routers` 미참조 (6개 모듈 모두).

## 18. 주석/문서화 기준 적용 여부

- 6개 신규 파일 모두 docstring (COMPAT / SAFETY / NOTE / RISK 섹션).
- 시간 가중치 회귀 방지에 RISK 주석.
- read-only 보장 / 외부 호출 부재에 SAFETY 주석.
- 예약 기준 / 완료 기준 분기 차이에 NOTE 주석.
- 미배정 sentinel / ESWT 코드 / weekday 라벨에 COMPAT 주석.

## 19. 실행한 테스트와 결과

| 명령 | 결과 |
|---|---|
| 19-11 contract | **90 passed** |
| 전체 회귀 | **1335 passed, 1 skipped, 7 xfailed** |
| PyInstaller 스펙 | **155 passed** |
| AI 회귀 | **142 passed** |
| ruff | **All checks passed!** |
| check_db_path | exit 0 |

## 20. 자동 수정 루프 횟수

**0회 코드 수정** — 90 / 90 contract 1회차 통과. ruff I001 1건 자동 보정 (테스트
import 정렬).

## 21. 다음 세션으로 넘어가도 되는지에 대한 Claude Code 의 자체 판단

**yes**. 근거:

1. 19-11 신규 contract 90 cases 모두 1회차 통과 (수정 루프 0회).
2. 전체 회귀 1335 passed (19-10 통과 1233 + 19-11 신규 90 + spec 12 = 1335).
3. ruff / DB 경로 / SMS AI / 휴무 AI / RAG / 계약 회귀 모두 통과.
4. **시간 가중치 방식 회귀 방지** 다중 가드 (정책 상수 + 패턴 검사 + 합계 검증).
5. **stats 모듈 read-only 보장** (DB 변경 메서드 부재 단위 테스트).
6. **외부 API 호출 부재** (외부 호출 라이브러리 import 부재 단위 테스트).
7. 라우터 / DB schema / migration / API 응답 key *완전 무수정* (9개 시그니처 +
   6개 endpoint contract 검증).
8. 19-3 ~ 19-10 모듈 *완전 무수정*.
9. 단방향 경계 (D-4) 보존.
10. 19-12 (admin / backup / audit / export_import) 진입 후보.

다만 **Codex 독립 검증 통과** 가 19-12 진입의 필수 게이트.
