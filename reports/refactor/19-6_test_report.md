# 19-6 treatments / completion_rules 분리 — 테스트 리포트

> 19-6 = **여섯 번째 실제 코드 리팩토링 세션**. `app/modules/treatments/` 신설 —
> 치료항목 분류 / 직렬화 / read-only 조회 + completion_rules (`bump_patient_count`).
> **5회 루프 1회차 통과 (846 passed, 1 skipped, 7 xfailed) — 19-5 baseline 회귀 0**.
> ruff 자동 fix 1회 (`I001` import 정렬, 코드 동작 변경 0).

## 0. 메타

- 세션 이름: **19-6 treatments / completion_rules 치료항목·완료체크 분리**
- 검증일: 2026-05-03
- 시작 HEAD: `ba19cda` (19-5 leaves)
- baseline 추이: 18-8 (529) → 19-5 (793) → **19-6 (846)** = 793 + 53 (19-6 contract 43 + PyInstaller 19-6 modules 10)
- 직전 19-5 Codex: pass — yes 19-6 진입 가능

## 1. 실행 환경

| 항목 | 값 |
|---|---|
| Python | 3.12.10 |
| pytest | 8.4.2 |
| ruff | 0.15.12 |

## 2. 실행한 검증 명령

| # | 명령 | 결과 |
|---|---|---|
| C-1 | `pytest tests -q` | **846 passed, 1 skipped, 7 xfailed** (11.05초) |
| C-2 | `ruff check app tests scripts` | **All checks passed!** (1차 `I001` 자동 fix 후) |
| C-3 | `scripts/check_db_path.py` | exit 0 |
| C-4 | `pytest tests/test_pyinstaller_hidden_imports.py -q` | **103 passed** (= 19-5 시점 93 + 19-6 신규 10 = modules 5개 × parametrized 2) |
| C-5 | `pytest tests/test_19_6_treatments.py -q` | **43 passed** |
| C-6 | `pytest tests/test_appointment_rules.py tests/test_employee_can_manual_contract.py tests/test_stats_counts.py tests/test_admin_ui_smoke.py tests/test_19_4_availability.py tests/test_19_5_leaves.py -q` | **160 passed, 1 skipped, 3 xfailed** |

## 3. baseline 회귀 검증

| 항목 | 19-5 | **19-6** | 일치 |
|---|---|---|---|
| passed | 793 | **846** (= 793 + 53 신규) | ✓ |
| skipped | 1 | **1** | ✓ |
| xfailed | 7 | **7** | ✓ |
| failed | 0 | **0** | ✓ |
| errors | 0 | **0** | ✓ |

## 4. 5회 루프 카운트

| 회차 | 결과 |
|---|---|
| 1 | C-1 ~ C-6 통과. ruff `I001` (import 정렬) 1건 — 자동 fix |

→ **5회 루프 1회차에 통과**. ruff 자동 fix 는 *코드 동작 변경 0*.

## 5. PyInstaller hidden imports 검증 (103 tests)

| 카테고리 | 카운트 |
|---|---|
| 18-1~18-7 신규 (38) + 19-1 core (16) + spec sanity / data files / migrations | 합산 안에 포함 |
| 19-x modules combined (`EXPECTED_19_X_MODULES_MODULES` 17개 × parametrized 2) | **34** (settings/health 4 + calendar 2 + appointments 2 + leaves 4 + **treatments 5**) × 2 |
| **19-6 신규** | **10** (modules 5개 × parametrized 2) |
| **합계** | **103 passed** |

## 6. 19-6 contract 테스트 (43 tests)

| 카테고리 | 테스트 수 |
|---|---|
| 1. role / ESWT / manual 분류 helper (parametrize 5+6+is_active) | 13 |
| 2. set comprehensions byte-equivalent (api.py 인라인 패턴) | 4 |
| 3. serialize_treatment byte-equivalent (12키) | 2 |
| 4. normalize_incentive (XOR / 0~100 / 8 parametrize) | 10 |
| 5. build_treatment_meta 응답 dict 15키 | 1 |
| 6. completion_rules.bump_patient_count byte-equivalent + Lazy create | 2 |
| 7. **manual60 = 1 정책** (CLAUDE.md 정합) + 항목별 개별 체크 원칙 | 2 |
| 8. 단방향 경계 (D-4 ast 기반: rules / repository / service / completion_rules) | 4 |
| 9. 라우터 무수정 회귀 (api.py 본체 + endpoint) | 3 |
| 10. 외부 API 호출 0 | 1 |
| **합계** | **43** ✓ |

## 7. 기존 회귀 검증 (160 tests)

| 파일 | 카운트 | 결과 |
|---|---|---|
| `test_appointment_rules.py` | 6 + 1 skipped + 3 xfailed | ✓ |
| `test_employee_can_manual_contract.py` | 2 | ✓ |
| `test_stats_counts.py` | 6 | ✓ |
| `test_admin_ui_smoke.py` | 14 | ✓ |
| `test_19_4_availability.py` | 79 | ✓ |
| `test_19_5_leaves.py` | 54 | ✓ |
| **합계** | **160 passed, 1 skipped, 3 xfailed** | ✓ |

→ **통계 (test_stats_counts.py) / 예약 / 휴무 / 완료체크 회귀 0**.

## 8. 핵심 정책 검증 (사용자 명시)

| 정책 | 검증 | 결과 |
|---|---|---|
| `manual60`.count_increment = 1 | DB 시드 + 19-6 helper 일관성 | ✓ |
| 시간 가중치 (count_increment 합산) ⊥ | 19-6 helper 의 정책 상수 + completion_rules.bump_patient_count delta=±1 | ✓ |
| 항목별 개별 체크 | `DEFAULT_COMPLETION_DELTA_PER_CODE == 1` + 도수30/60/90/ESWT 모두 독립 카운트 | ✓ |
| 통계 집계 기준 무수정 | api.py:_get_manual_treatment_rows / _get_manual_therapy_codes 본체 그대로 | ✓ |

## 9. 운영 DB 보호 / 외부 API 차단

| 검사 | 결과 |
|---|---|
| `check_db_path.py` exit 0 | ✓ |
| `_block_sdk_modules` | ✓ |
| 19-6 helper 외부 호출 0 | ✓ — `test_helpers_do_not_invoke_provider_or_db` 통과 |
| repository / completion_rules — DB 호출자 주입 | ✓ |

## 10. 응답 키 / API 보호 검증

| 응답 | 키 셋 | 보존 |
|---|---|---|
| `GET /api/treatment-meta` | 15키 (treatment_codes / names / short / minutes / role / show / doctor / therapist / manual / count_increment / eswt_code / price / incentive_pct/amount / all_treatments) | ✓ |
| `GET /api/treatments` | 12키 per row | ✓ |
| `POST /api/appointments/{aid}/approve` | (전체 그대로) | ✓ |
| `POST /api/appointments/{aid}/revert-approve` | (전체 그대로) | ✓ |
| 통계 endpoint (8개 GET + manual-counts) | (전체 그대로) | ✓ |

## 11. 19-7 진입 권고

**yes — 19-7 patients / notes / data-convert 분리 진입 가능**.

근거:
1. 19-5 baseline (793/1/7) 회귀 0 — 신규 +53 만 추가 (총 846).
2. ruff / check_db_path / PyInstaller 103 tests 모두 통과.
3. 19-6 43 contract + 기존 통계/예약/휴무/availability 160 tests 모두 통과.
4. **manual60=1 정책 보존** (CLAUDE.md 정합) — 시간 가중치 합산 ⊥.
5. **항목별 개별 체크 원칙 유지** — count_increment 곱셈 ⊥.
6. 라우터 / 통계 / SMS / AI 본체 무수정.
7. 운영 DB 미접근 + 외부 API 호출 0.
8. modules.treatments 단방향 경계 (D-4) 검증 통과 (ast 기반).

남은 위험:
- (1) 19-6 helpers 미채택 (의도) — 19-9 / 19-11 시점 채택.
- (2) `_bump_patient_count` 두 사본 (api.py + treatments.completion_rules) 공존 — 19-9 통합.

다음 세션:
- **19-7 patients / notes / data-convert 분리** — `app/modules/patients/` 신설 + PII 보호 +
  검색 / 메모 / counts dict / data-convert 흐름 분리.
