# 19-6 treatments / completion_rules 분리 — 변경 요약

> 19-6 = **여섯 번째 실제 코드 리팩토링 세션**. `app/modules/treatments/` 후보 구조 신설.
> 5회 루프 1회차 통과 (846 passed) — 19-5 baseline 회귀 0.

## 0. 메타

- 세션 이름: **19-6 treatments / completion_rules 치료항목·완료체크 분리**
- 검증일: 2026-05-03
- 시작 HEAD: `ba19cda` (19-5 leaves)
- 직전 19-5 Codex: pass — yes 19-6 진입 가능

## 1. 변경 파일 목록

### 신규 (6개)

| 파일 | 라인 수 | 종류 |
|---|---|---|
| `app/modules/treatments/__init__.py` | 33 | 신규 facade docstring |
| `app/modules/treatments/rules.py` | 198 | 신규 helper (12 + 상수 다수) — role / ESWT / manual / 활성 / 분류 set / 완료체크 대상 |
| `app/modules/treatments/repository.py` | 92 | 신규 helper (5 — DB 호출자 주입) |
| `app/modules/treatments/service.py` | 173 | 신규 helper (3) — `_serialize_treatment` / `_normalize_incentive` / `_build_treatment_meta` 동등 |
| `app/modules/treatments/completion_rules.py` | 114 | 신규 helper (2) — `_bump_patient_count` 동등 + 정책 상수 |
| `tests/test_19_6_treatments.py` | 575 | 신규 contract (43 테스트) |

### 수정 (2개)

| 파일 | 변경 |
|---|---|
| `dosu_clinic.spec` | +8 lines (19-6 modules 5개 hidden imports + 주석) |
| `tests/test_pyinstaller_hidden_imports.py` | +6 lines (`EXPECTED_19_X_MODULES_MODULES` 12 → 17) |

### 무수정 (절대 금지 범위 정합)

`app/routers/api.py` (모든 치료항목 / 예약 / 통계 핸들러 + `_serialize_treatment` /
`_normalize_incentive` / `_build_treatment_meta` / `_bump_patient_count` /
`_get_manual_treatment_rows` 본체 무수정), `app/routers/ai.py`, `app/services/**`,
`app/models/**`, `app/migrations/**`, `app/templates/**`, `app/static/**`,
`requirements*.txt`, `pyproject.toml`, `tests/conftest.py`, `tests/harness/**`,
`app/modules/{appointments,leaves,calendar,settings,health}/`.

## 2. 본 세션 의도 / 이유

### 의도

19-P-2 §2-1 V2 트리의 `app/modules/treatments/` 자리를 *최소 범위* 로 신설. 치료항목
분류 / 직렬화 / 완료체크 *동등 helper* (라우터 미채택). 19-9 appointments + 19-11 stats
시점 채택 후보.

### 이유

1. **사용자 명시 "치료항목별 개별 체크 원칙 유지" + "시간 가중치 ⊥"**:
   `completion_rules.bump_patient_count` 는 *항목별 ±delta* — `count_increment` 곱셈 ⊥.
   `EXPECTED_MANUAL60_COUNT_INCREMENT = 1` + `DEFAULT_COMPLETION_DELTA_PER_CODE = 1` 정책 명시.
2. **사용자 명시 "manual60=1 정책 보존" (CLAUDE.md)**:
   contract 테스트 `test_manual60_count_increment_is_one` 가 시드 row 의 `count_increment == 1` 검증.
3. **사용자 명시 "통계 집계 기준 변경 금지"**:
   `_get_manual_treatment_rows` / `_get_manual_therapy_codes` 본체 무수정 — 통계가 참조하는 분류 그대로.
4. **사용자 명시 "예약 API 응답 key 변경 금지"**:
   라우터 무수정. `serialize_treatment` 12키 / `build_treatment_meta` 15키 byte-equivalent.
5. **사용자 명시 "AI/RAG 로직 변경 금지"**:
   AI 흐름 / RAG 무수정. modules.treatments 는 `app.routers` / `fastapi` / `app.services` 미참조.

## 3. 새로 만든 modules.treatments 구조

```
app/modules/treatments/
├── __init__.py                 (33 lines, treatments 패키지 facade)
├── rules.py                    (198 lines, helper 12 + 상수 다수)
│   ├── 상수: ROLE_DOCTOR/THERAPIST/VALUES, DEFAULT_ESWT_CODE
│   ├── 단일 판정: is_doctor_role / is_therapist_role / is_manual_treatment /
│   │              is_eswt_treatment / is_active / is_completion_target /
│   │              get_count_increment
│   └── 셋 분류: doctor_codes / therapist_codes / therapist_only_codes /
│              existing_codes / active_manual_codes
├── repository.py               (92 lines, helper 5 — DB 호출자 주입)
│   └── list_all_treatments / list_treatments_sorted / list_active_manual_treatments /
│      get_treatment_by_code / get_treatment_by_id
├── service.py                  (173 lines, helper 3 + IncentiveValidationError)
│   ├── normalize_incentive (ValueError 하위 클래스 raise — D-4)
│   ├── serialize_treatment (12키)
│   └── build_treatment_meta (15키)
└── completion_rules.py         (114 lines, helper 2 + 정책 상수)
    ├── bump_patient_count (Lazy 생성 + 0 미만 방지 + delta=0 no-op)
    ├── EXPECTED_MANUAL60_COUNT_INCREMENT = 1
    └── DEFAULT_COMPLETION_DELTA_PER_CODE = 1
```

합계 — helper **22** (rules 12 + repository 5 + service 3 + completion_rules 2) + 정책 상수.

## 4. 실제 이동한 치료항목 로직

**0 줄 이동** — 모두 facade / 동등 helper.

| api.py 위치 | 19-6 helper |
|---|---|
| `_serialize_treatment` (line 767) | `service.serialize_treatment` (12키 byte-equivalent) |
| `_normalize_incentive` (line 786) | `service.normalize_incentive` (ValueError raise) |
| `_build_treatment_meta` (line 816) | `service.build_treatment_meta` (15키) |
| `_doctor_codes_set` (line 153) | `rules.doctor_codes` |
| `_therapist_codes_set` (line 158) | `rules.therapist_codes` |
| `_therapist_only_codes_set` (line 163) | `rules.therapist_only_codes` |
| `_existing_codes_set` (line 148) | `rules.existing_codes` |
| `_get_manual_treatment_rows` (line 3732) | `repository.list_active_manual_treatments` |
| `_get_manual_therapy_codes` (line 3752) | `rules.active_manual_codes` |
| `_all_treatments` (line 139) | `repository.list_all_treatments` |

## 5. 실제 이동한 완료체크 규칙

**0 줄 이동** — `_bump_patient_count` 본체 무수정.

| api.py 위치 | 19-6 helper |
|---|---|
| `_bump_patient_count` (line 1934) | `completion_rules.bump_patient_count` (byte-equivalent) |
| approve / revert / delete 흐름의 코드별 ±1 호출 | (호출 패턴 그대로 — 19-9 시점 위임) |
| `manual60`=1 정책 시드 + 카운트 산정 | `EXPECTED_MANUAL60_COUNT_INCREMENT` 상수로 명시 |

## 6. 유지한 compatibility wrapper

| wrapper | 위치 | 역할 |
|---|---|---|
| `service.serialize_treatment` | `service.py` | api.py:_serialize_treatment 12키 byte-equivalent |
| `service.normalize_incentive` | `service.py` | api.py:_normalize_incentive 동등 — ValueError raise (D-4 정합) |
| `service.build_treatment_meta` | `service.py` | api.py:_build_treatment_meta 15키 byte-equivalent |
| `rules.doctor_codes` / `therapist_only_codes` 등 | `rules.py` | api.py 인라인 set comprehension 정합 |
| `repository.list_*` | `repository.py` | api.py query 패턴 정합 (lazy import) |
| `completion_rules.bump_patient_count` | `completion_rules.py` | api.py:_bump_patient_count byte-equivalent |

## 7. 기존 API 응답 구조 유지 여부

✓ **100% 보존** — `app/routers/api.py` 무수정.

## 8. 치료항목별 개별 체크 원칙 유지 여부

✓ **유지** — `DEFAULT_COMPLETION_DELTA_PER_CODE = 1` 명시. 도수30 / 도수60 / 도수90 /
ESWT 모두 독립 카운트 — `count_increment` 합산 ⊥.

## 9. 시간 가중치 방식으로 되돌아가지 않았는지 확인

✓ **확인** — `manual60.count_increment == 1` (시드 검증) + `EXPECTED_MANUAL60_COUNT_INCREMENT = 1`
+ `DEFAULT_COMPLETION_DELTA_PER_CODE = 1` 정책 상수 명시. RISK 주석으로 시간 가중치 도입 금지
명시.

## 10. 기존 예약 / 통계 / 문자 영향 여부

✗ **무영향** — 라우터 / 통계 흐름 / SMS 본체 무수정. test_stats_counts.py 6 tests 회귀 0.

## 11. 개인정보 / 운영 DB / 외부 API 보호 결과

- PII: treatments helper 가 환자 PII 미참조 (Treatment 테이블은 환자 데이터 부재)
- 운영 DB: helper 안에서 DB 세션 호출자 주입 (직접 open ⊥)
- 외부 API: 0건 (tripwire 통과)

## 12. 순환참조 위험 여부

✓ **0건** — D-4 단방향 경계 (ast 기반):
- `rules.py`: 외부 표준 라이브러리 (`typing`) 만
- `repository.py`: top-level import 부재 (`app.models` lazy)
- `service.py`: `app.modules.treatments.rules` (단방향) — `app.routers` / `fastapi` ⊥
- `completion_rules.py`: top-level import 부재 (`app.models` lazy)

## 13. 실행한 테스트와 결과

- `pytest tests`: **846 passed, 1 skipped, 7 xfailed** (= 793 + 53 신규)
- `ruff`: All checks passed!
- `check_db_path`: exit 0
- PyInstaller: **103 passed**
- 19-6 contract: **43 passed**
- 통계/예약/휴무/availability 회귀: **160 passed, 1 skipped, 3 xfailed**

## 14. 주석 / 문서화 적용 내용

### 14-1. 카테고리별 주석 카운트

| 카테고리 | 주요 위치 |
|---|---|
| `# COMPAT:` | __init__ + 4 모듈 + 22 helper docstring |
| `# SAFETY:` | __init__ / 모듈 docstring (운영 DB 보호 / PII 미참조) |
| `# NOTE:` | rules / completion_rules (도수 정의 / 항목별 개별 체크 / Lazy 생성) |
| `# RISK:` | __init__ + rules + service + completion_rules — *시간 가중치 합산 ⊥* / `manual60`=1 |
| `TODO(19-x)` | 0 — 모든 후속 작업이 19-9 / 19-11 시점 명시 |

## 15. 생성한 리포트 파일

- `reports/refactor/19-6_test_report.md`
- `reports/refactor/19-6_fix_summary.md`
- `reports/refactor/19-6_codex_review_request.md`
- `latest_*.md` 3개 동기화

## 16. 남은 위험 요소

| # | 위험 | 분류 | 해결 시점 |
|---|---|---|---|
| 1 | 19-6 helpers 미채택 (라우터 / 통계 / 예약 모두) | 의도 | 19-9 / 19-11 |
| 2 | `_bump_patient_count` / `_serialize_treatment` 등 두 사본 공존 | 알려진 — 19-9/19-11 통합 | 19-9 / 19-11 |
| 3 | `count_increment` 합산 도입 시 본 19-6 정책 위반 — 시드 / 관리자 UI 가 보호 | RISK 주석 명시 | 운영 정책 변경 시 |

## 17. Codex 검증으로 넘겨도 되는지 자체 판단

**yes — Codex 검증 진입 가능**.

근거:
1. 5회 루프 1회차 통과 (ruff 자동 fix — 동작 변경 0).
2. 19-5 baseline (793/1/7) 회귀 0 — 신규 +53 만 추가 (총 846).
3. ruff / check_db_path / PyInstaller 103 tests 모두 통과.
4. 19-6 43 contract + 기존 통계/예약/휴무/availability 160 tests 모두 통과.
5. **manual60=1 정책 보존** + **항목별 개별 체크 원칙 유지** + **시간 가중치 ⊥**.
6. 라우터 / 통계 / SMS / AI 본체 무수정.
7. 운영 DB 미접근 + 외부 API 호출 0.
8. modules.treatments 단방향 경계 (D-4) 검증 통과 (ast 기반).
9. 사용자 명시 15 금지 항목 모두 준수.
