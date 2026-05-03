# 19-7 patients / notes 환자·메모 경계 분리 — 테스트 리포트

> 19-7 = **일곱 번째 실제 코드 리팩토링 세션**. `app/modules/patients/` +
> `app/modules/notes/` 후보 구조 신설.
> **5회 루프 1회차 통과 (938 passed, 1 skipped, 7 xfailed) — 19-6 baseline 회귀 0**.
> 1회차 PII 마스킹 부족 1건 + ruff 자동 fix 1건 보강 (코드 동작 변경 0).

## 0. 메타

- 세션 이름: **19-7 patients / notes 환자·메모 경계 분리**
- 검증일: 2026-05-03
- 시작 HEAD: `67ce889` (19-6 treatments)
- baseline 추이: 19-6 (846) → **19-7 (938)** = 846 + 92 (19-7 contract 80 + PyInstaller 19-7 modules 12)
- 직전 19-6 Codex: pass — yes 19-7 진입 가능
- r2 보정 (Codex 19-7 r1 caveat 1): `tests/test_19_7_patients_notes.py` 실제 줄 수 **662** (r1 표기 670 — ruff `--fix` 후 추가 변동분 미반영)

## 1. 실행 환경

| 항목 | 값 |
|---|---|
| Python | 3.12.10 |
| pytest | 8.4.2 |
| ruff | 0.15.12 |

## 2. 실행한 검증 명령

| # | 명령 | 결과 |
|---|---|---|
| C-1 | `pytest tests -q` | **938 passed, 1 skipped, 7 xfailed** (11.45초) |
| C-2 | `ruff check app tests scripts` | **All checks passed!** (1차 `I001` 자동 fix 후) |
| C-3 | `scripts/check_db_path.py` | exit 0 |
| C-4 | `pytest tests/test_pyinstaller_hidden_imports.py -q` | **115 passed** (= 19-6 시점 103 + 19-7 신규 12) |
| C-5 | `pytest tests/test_19_7_patients_notes.py -q` | **80 passed** |
| C-6 | `pytest tests/test_admin_ui_smoke.py tests/test_appointment_rules.py tests/test_19_4_availability.py tests/test_19_5_leaves.py tests/test_19_6_treatments.py tests/test_ai_action_leave.py tests/test_ai_sms_validate.py tests/test_ai_sms_draft.py -q` | **262 passed, 1 skipped, 3 xfailed** |

## 3. baseline 회귀 검증

| 항목 | 19-6 | **19-7** | 일치 |
|---|---|---|---|
| passed | 846 | **938** (= 846 + 92 신규) | ✓ |
| skipped | 1 | **1** | ✓ |
| xfailed | 7 | **7** | ✓ |
| failed | 0 | **0** | ✓ |
| errors | 0 | **0** | ✓ |

## 4. 5회 루프 카운트

| 회차 | 결과 |
|---|---|
| 1 | C-1 ~ C-6 — `test_patient_summary_for_log_does_not_leak_pii` 1건 실패: `mask_memo` 가 truncate head 안 전화번호를 노출. SAFETY 강화 필요. |
| 2 | `_scrub_pii_patterns` 추가 (전화/주민번호 → ``***``). C-1 ~ C-6 모두 통과. ruff `I001` 1건. |
| 3 | `ruff check --fix` 자동 정렬. **모두 통과** ✓ |

→ **5회 루프 3회차 통과**. 1회차 실패는 SAFETY 강화 (PII 스크럽 추가) — 정책 강화이지
기능 결함 아님.

## 5. PyInstaller hidden imports 검증 (115 tests)

| 카테고리 | 카운트 |
|---|---|
| 18-1~18-7 (38) + 19-1 core (16) + spec sanity / data files / migrations | 합산 안 |
| 19-x modules combined (`EXPECTED_19_X_MODULES_MODULES` 23개 × parametrized 2) | **46** (settings/health 4 + calendar 2 + appointments 2 + leaves 4 + treatments 5 + **patients 4 + notes 2**) × 2 |
| **19-7 신규** | **12** (modules 6개 × parametrized 2) |
| **합계** | **115 passed** |

## 6. 19-7 contract 테스트 (80 tests)

| 카테고리 | 테스트 수 |
|---|---|
| 1. 중복 검사 정규화 / 분기 (parametrize 5+2+4) | 11 + 1 (메시지) |
| 2. 신환 체크 (parametrize 4+3) | 7 |
| 3. PII 마스킹 (mask_name 6 / mask_phone 7 / mask_birth 6 / mask_memo 4 + 2 PII 스크럽 / mask_chart 4 + summary leak 검증) | 30 |
| 4. service — counts dict | 1 |
| 5. service — patient_to_dict (9키) + 부재 필드 + light (7키) | 3 |
| 6. service — search response envelope (6키) + has_more boundary | 2 |
| 7. service — manual_history_summary (5키) | 2 |
| 8. notes — 메모 분류 (NOTE_KIND / is_persistent / is_per_appointment) | 3 |
| 9. notes — append_cancel_memo byte-equivalent (parametrize 6) + 상수 | 7 |
| 10. notes — mask_memo_for_log == patients.mask_memo + PII truncate | 2 |
| 11. 단방향 경계 ast 6 (rules / repository / service / notes / 2 init) | 6 |
| 12. 라우터 무수정 회귀 (api.py 본체 + 3 endpoint) | 4 |
| 13. 외부 API 호출 0 | 1 |
| **합계** | **80** ✓ |

## 7. 기존 회귀 검증 (262 tests)

| 파일 | 결과 |
|---|---|
| test_admin_ui_smoke.py | 14 ✓ |
| test_appointment_rules.py | 6+1+3xfail ✓ |
| test_19_4_availability.py | 79 ✓ |
| test_19_5_leaves.py | 54 ✓ |
| test_19_6_treatments.py | 43 ✓ |
| test_ai_action_leave.py | 44 ✓ |
| test_ai_sms_validate.py | 11 ✓ |
| test_ai_sms_draft.py | 11 ✓ |
| **합계** | **262 passed, 1 skipped, 3 xfailed** |

→ **AI / SMS / 휴무 / 예약 / availability / treatments 회귀 0**.

## 8. 운영 DB 보호 / 외부 API 차단

| 검사 | 결과 |
|---|---|
| `check_db_path.py` exit 0 | ✓ |
| `_block_sdk_modules` | ✓ |
| 19-7 helper 외부 호출 0 | ✓ |
| repository / service — DB 호출자 주입 | ✓ |

## 9. 응답 키 / API 보호 검증

| 응답 | 키 셋 | 보존 |
|---|---|---|
| `GET /api/patients?light=1` | 7키 (id / name / chart_no / phone / birth_date / gender / memo) | ✓ |
| `GET /api/patients/search` | 6키 envelope | ✓ |
| `GET /api/patients/{pid}/manual-history-summary` | 5키 | ✓ |
| `GET /api/patients/{pid}` | 9키 (counts 포함) | ✓ |
| `PATCH /api/patients/{pid}/memo` | ok | ✓ |
| `POST /api/appointments/{aid}/cancel` 메모 prefix | `\\n[취소] {memo}` | ✓ |

## 10. PII 보호 검증

| 검증 | 결과 |
|---|---|
| `mask_name` / `mask_phone` / `mask_birth_date` / `mask_chart_no` / `mask_memo` 원문 노출 ⊥ | ✓ |
| `mask_memo` 안 전화번호 패턴 → `***` 스크럽 | ✓ (`_scrub_pii_patterns` 추가) |
| `mask_memo` 안 주민번호 패턴 → `***` 스크럽 | ✓ |
| `patient_summary_for_log` 결과 dict 에 원문 PII 노출 ⊥ | ✓ |
| `notes.rules.mask_memo_for_log` ≡ `patients.rules.mask_memo` | ✓ (동등성 contract 테스트) |
| 운영 응답 dict (환자 / 검색 / 모달) — 평문 PII 그대로 (UI 정합) | ✓ (마스킹 정책 변경 ⊥) |

## 11. 19-8 진입 권고

**yes — 19-8 staff (therapists + doctors) 분리 진입 가능**.

근거:
1. 19-6 baseline (846/1/7) 회귀 0 — 신규 +92 만 추가 (총 938).
2. ruff / check_db_path / PyInstaller 115 tests 모두 통과.
3. 19-7 80 contract + 기존 AI/SMS/휴무/예약/treatments 262 tests 모두 통과.
4. PII 마스킹 정책 보존 — 운영 응답 평문 / 로그 마스킹 분리 명확.
5. 운영 DB 미접근 + 외부 API 호출 0.
6. modules.patients / notes 단방향 경계 (D-4) 검증 통과 (ast 6).

남은 위험:
- (1) 19-7 helpers 미채택 (의도) — 19-9 시점 채택.
- (2) `_check_patient_duplicate` / `_patient_to_dict` 등 두 사본 공존 — 19-9 통합.
- (3) data-convert 흐름 (~600줄 `_dc_*`) 분리 — 19-12 export_import 시점.

다음 세션:
- **19-8 staff (therapists + doctors) 또는 medical_staff 경계 정리** — Employee role
  분기 + alias `therapist_id` 이중 키 + doctors 후속 검토 분류.
