# 19-6 treatments / completion_rules 분리 — Codex 검증 요청서

> 사용자 양식 18개 항목 정합. Codex 가 본 문서를 시작점으로 쓰되 **실제 diff /
> 변경 파일 / 결과 / 로그를 독립적으로 확인** 한다.

---

## 1. 세션 이름

**19-6 treatments / completion_rules 치료항목·완료체크 분리**.

## 2. 이번 세션 목표

`app/modules/treatments/` 후보 구조 신설 — 치료항목 분류 (role/ESWT/manual) +
직렬화 + read-only 조회 + 인센티브 정규화 + completion_rules (`bump_patient_count`).
라우터 / 통계 / AI / SMS 본체 무수정. 시간 가중치 ⊥, 항목별 개별 체크 원칙 + manual60=1
정책 보존.

## 3. 변경 파일 목록

### 신규 (6개)

| 파일 | 라인 수 (실측) | 종류 |
|---|---|---|
| `app/modules/treatments/__init__.py` | 33 | 신규 facade docstring |
| `app/modules/treatments/rules.py` | 198 | 신규 helper (12 + 상수 다수) |
| `app/modules/treatments/repository.py` | 92 | 신규 helper (5 — DB 호출자 주입) |
| `app/modules/treatments/service.py` | 173 | 신규 helper (3 + IncentiveValidationError) |
| `app/modules/treatments/completion_rules.py` | 114 | 신규 helper (2 + 정책 상수) |
| `tests/test_19_6_treatments.py` | 575 | 신규 contract (43 테스트) |

합계 — helper **22** + 정책 상수 다수.

### 수정 (2개)

| 파일 | 변경 |
|---|---|
| `dosu_clinic.spec` | +8 lines (19-6 modules 5개 hidden imports) |
| `tests/test_pyinstaller_hidden_imports.py` | +6 lines (`EXPECTED_19_X_MODULES_MODULES` 12 → 17) |

### 무수정

`app/routers/api.py` (모든 치료항목 / 예약 / 통계 핸들러 + 본체 함수 무수정),
`app/routers/ai.py`, `app/services/**`, `app/models/**`, `app/migrations/**`,
`app/templates/**`, `app/static/**`, `tests/conftest.py`, `tests/harness/**`,
`app/modules/{appointments,leaves,calendar,settings,health}/`.

## 4. 실제 이동 / 분리한 치료항목 로직

**0 줄 이동** — 모두 facade / 동등 helper.

| api.py | 19-6 helper |
|---|---|
| `_serialize_treatment` (line 767) | `service.serialize_treatment` (12키) |
| `_normalize_incentive` (line 786) | `service.normalize_incentive` (ValueError raise — D-4) |
| `_build_treatment_meta` (line 816) | `service.build_treatment_meta` (15키) |
| `_doctor_codes_set` / `_therapist_only_codes_set` / `_existing_codes_set` 등 | `rules.doctor_codes` / `therapist_only_codes` / `existing_codes` |
| `_get_manual_treatment_rows` (line 3732) | `repository.list_active_manual_treatments` |
| `_get_manual_therapy_codes` | `rules.active_manual_codes` |

## 5. 실제 이동 / 분리한 완료체크 규칙

**0 줄 이동** — `_bump_patient_count` 본체 무수정.

| api.py | 19-6 helper |
|---|---|
| `_bump_patient_count` (line 1934) | `completion_rules.bump_patient_count` (byte-equivalent) |
| 정책 상수 — manual60=1 / 항목별 ±1 | `EXPECTED_MANUAL60_COUNT_INCREMENT = 1` / `DEFAULT_COMPLETION_DELTA_PER_CODE = 1` |

## 6. Compatibility wrapper 유지 여부

✓ **유지**. 22 helper 모두 *byte-equivalent / 동등 helper* — 라우터 / 통계 / 예약 미채택
(19-9 / 19-11 시점).

## 7. 수정 금지 범위 준수 여부

✓ **모두 준수**:

| 금지 항목 | 결과 |
|---|---|
| 완료체크를 시간 가중치 방식으로 되돌리는 것 | ✗ — `count_increment` 합산 ⊥, 항목별 ±1 |
| 도수 30분=1, 60분=2 같은 합산 | ✗ — `manual60.count_increment == 1` 시드 검증 |
| 예약 API 응답 key 변경 | ✗ — 라우터 무수정 |
| 예약 생성/수정/삭제 전체 흐름 대규모 변경 | ✗ |
| 휴무/availability 로직 변경 | ✗ — 19-4/19-5 modules 무수정 |
| 통계 집계 기준 변경 | ✗ — `_get_manual_treatment_rows` 본체 무수정 |
| 문자/SMS / AI/RAG / DB schema / migration / UI / 하네스 약화 | ✗ |
| 운영 DB 접근 / 외부 API 호출 | ✗ |
| `requirements.txt` / spec 불필요 수정 | ✗ — spec 은 5개 hidden imports 만 |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✗ |

## 8. 기존 API 응답 key 유지 여부

✓ **100% 보존**. `app/routers/api.py` 무수정.

| URL | 응답 키 | 보존 |
|---|---|---|
| `GET /api/treatment-meta` | 15키 | ✓ |
| `GET /api/treatments` | 12키 per row | ✓ |
| `POST /api/appointments/{aid}/approve` | (전체 그대로) | ✓ |
| `POST /api/appointments/{aid}/revert-approve` | (전체 그대로) | ✓ |

## 9. 치료항목별 개별 체크 원칙 유지 여부

✓ **유지**:
- `DEFAULT_COMPLETION_DELTA_PER_CODE = 1` (시간 가중치 합산 ⊥)
- 도수30 / 도수60 / 도수90 / ESWT 모두 *독립* 카운트
- 라우터의 approve / revert 흐름이 *코드별 +1 N회 호출* 패턴 그대로 (count_increment 곱셈 ⊥)

## 10. 시간 가중치 방식으로 되돌아가지 않았는지 여부

✗ **되돌아가지 않음**:
- `manual60.count_increment == 1` (DB 시드 검증 — `test_manual60_count_increment_is_one`)
- `EXPECTED_MANUAL60_COUNT_INCREMENT = 1` (19-6 정책 상수)
- `bump_patient_count` 의 `delta` 인자가 ±1 (caller 가 코드마다 별도 호출 — 곱셈 ⊥)
- RISK 주석으로 시간 가중치 도입 금지 명시 (4 위치)

## 11. 기존 통계 / 예약 / 문자 영향 여부

✗ **영향 없음**. 라우터 / `_get_manual_treatment_rows` / 통계 핸들러 모두 그대로.
`test_stats_counts.py` 6 tests 회귀 0.

## 12. 운영 DB 보호 여부

✓ **100% 보호** — `scripts/check_db_path.py` exit 0. repository / completion_rules 의 DB
세션은 호출자 주입.

## 13. 외부 API 호출 여부

✓ **0건** — `test_helpers_do_not_invoke_provider_or_db` 통과. `_block_sdk_modules` 자동
활성.

## 14. 순환참조 위험 여부

✓ **0건** — D-4 단방향 경계 검증 통과 (ast 기반):
- `rules.py`: 외부 표준 라이브러리 (`typing`) 만
- `repository.py` / `completion_rules.py`: top-level import 부재 (`app.models` lazy)
- `service.py`: `app.modules.treatments.rules` 만 (단방향) — `app.routers` / `fastapi` ⊥

## 15. 주석 / 문서화 기준 적용 여부

✓ **모두 적용**:

| # | 기준 | 적용 |
|---|---|---|
| 1 | 새 파일 상단 docstring | 6 신규 파일 모두 |
| 2 | 주요 helper 함수 docstring | 22 helper 모두 (COMPAT 명시) |
| 3 | API/UI 호환 wrapper `COMPAT` 주석 | 다수 |
| 4 | 운영 DB / 외부 API 보호 부분 `SAFETY` 주석 | 4+ |
| 5 | **시간 가중치 / 항목별 카운트 / manual60=1 정책 `RISK` 주석** | 4 위치 |
| 6 | 통계 기준 영향 부분 `NOTE` 주석 | 다수 |
| 7 | TODO(19-x) 형식 | 0 (모든 후속이 19-9/19-11 명시) |
| 8 | 의미 없는 모든 줄 주석 금지 | ✓ |
| 9 | 주석 작성 때문에 기능 동작 변경 금지 | ✓ |

## 16. 실행한 테스트와 결과

| # | 명령 | 결과 |
|---|---|---|
| C-1 | `pytest tests -q` | **846 passed, 1 skipped, 7 xfailed** (11.05초) |
| C-2 | `ruff check app tests scripts` | **All checks passed!** (1차 `I001` 자동 fix) |
| C-3 | `scripts/check_db_path.py` | exit 0 |
| C-4 | PyInstaller hidden imports | **103 passed** |
| C-5 | 19-6 contract | **43 passed** |
| C-6 | 통계/예약/휴무/availability 회귀 | **160 passed, 1 skipped, 3 xfailed** |

## 17. 실패 / 수정 루프 횟수

| 회차 | 결과 |
|---|---|
| 1 | C-1 ~ C-6 통과. ruff `I001` 1건 — 자동 fix |

→ **5회 루프 1회차 통과**. 코드 동작 변경 0.

## 18. 19-7 patients / notes 분리로 넘어가도 되는지 판단 기준

**yes — 19-7 진입 가능**.

근거:
1. **5회 루프 1회차 통과**.
2. **19-5 baseline (793/1/7) 회귀 0** — 신규 +53 (총 846).
3. **ruff / check_db_path / PyInstaller 103 tests 모두 통과**.
4. **19-6 43 contract + 통계/예약/휴무 160 tests 모두 통과**.
5. **manual60=1 정책 보존** + **항목별 개별 체크** + **시간 가중치 ⊥**.
6. **라우터 / 통계 / SMS / AI 본체 무수정**.
7. **운영 DB 미접근 + 외부 API 호출 0**.
8. **modules.treatments 단방향 경계 (D-4) 검증 통과**.
9. **사용자 명시 15 금지 항목 모두 준수**.

남은 위험:
- (1) 19-6 helpers 미채택 (의도) — 19-9 / 19-11 시점 채택.
- (2) `_bump_patient_count` 두 사본 공존 — 19-9 통합.

다음 세션:
- **19-7 patients / notes / data-convert 분리** — `app/modules/patients/` 신설 + PII 보호 +
  검색 / 메모 / counts dict / data-convert 흐름 분리.

---

## Codex 가 집중 검토할 파일

1. `app/modules/treatments/__init__.py` — 패키지 facade.
2. `app/modules/treatments/rules.py` — 분류 helper. api.py 인라인 set comprehension byte-equivalent 검증.
3. `app/modules/treatments/service.py` — `_serialize_treatment` / `_normalize_incentive` /
   `_build_treatment_meta` 동등 검증.
4. `app/modules/treatments/completion_rules.py` — `_bump_patient_count` byte-equivalent +
   정책 상수 (manual60=1 / DEFAULT_COMPLETION_DELTA_PER_CODE=1).
5. `app/modules/treatments/repository.py` — lazy import.
6. `tests/test_19_6_treatments.py` — 43 contract 테스트.
7. `dosu_clinic.spec` 19-6 추가 8줄 + `tests/test_pyinstaller_hidden_imports.py` 6줄.

## Codex 가 반드시 확인할 체크리스트

1. **응답 키 100% 보존** — `app/routers/api.py` 무수정.
2. **byte-equivalent** — serialize_treatment 12키 / build_treatment_meta 15키 /
   normalize_incentive XOR / 분류 set comprehensions / bump_patient_count Lazy 동작.
3. **시간 가중치 ⊥** — manual60.count_increment == 1 (DB 시드 검증) +
   `EXPECTED_MANUAL60_COUNT_INCREMENT = 1` + `DEFAULT_COMPLETION_DELTA_PER_CODE = 1`.
4. **항목별 개별 체크** — bump_patient_count delta=±1, count_increment 곱셈 ⊥.
5. **단방향 경계 (D-4)** — rules 가 ORM/DB/services/routers 미참조 (ast 검증).
6. **운영 DB 미접근** + **외부 API 호출 0**.
7. **PyInstaller 빌드 안전성** — 19-6 modules 5개 spec 등록 + 10 신규 tests.
8. **5회 루프 1회차 통과**.

## 자체 판단

**yes — 19-7 진입 가능 (Codex 검증 통과 후)**.
