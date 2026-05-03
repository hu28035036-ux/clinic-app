# 19-0 baseline 재고정 — 테스트 리포트

> 19-P-1 ~ 19-P-10 (준비 단계 10개 문서) 완료 후 **19-x 실제 코드 리팩토링 세션 진입 직전 baseline 확보** 세션.
> 본 19-0 = read-only 검증 세션 (코드 / 테스트 / migration / spec / UI / requirements 무수정).
>
> **검증 결과: 18-8 baseline 정확 일치 (529 passed, 1 skipped, 7 xfailed) — 회귀 0**.

## 0. 메타

- 세션 이름: **19-0 baseline 재고정**
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 기준 18-8 baseline: **529 passed, 1 skipped, 7 xfailed** ([reports/ai_dev_loop/18-8_test_report.md](18-8_test_report.md))
- 19-P-1 ~ 19-P-10 Codex 판정: 9개 모두 pass / pass with caveat (yes 진입 가능). 19-P-10 r1: **pass with caveat — yes 19-0 진입 가능** ([reports/refactor/19-P-10_codex_review.md](../refactor/19-P-10_codex_review.md))

## 1. 실행 환경 진단

| 항목 | 결과 | 명령 |
|---|---|---|
| `.venv\Scripts\python.exe` 존재 | ✓ | `ls -la venv/Scripts/python.exe` (274,424 bytes, 2026-05-02) |
| Python 버전 | **3.12.10** | `venv/Scripts/python.exe --version` |
| pytest 버전 | **8.4.2** | `venv/Scripts/python.exe -m pytest --version` |
| ruff 버전 | **0.15.12** | `venv/Scripts/python.exe -m ruff --version` |
| 마이그레이션 자동 적용 | m001 ~ m013 (13개) ✓ | conftest.py import-time 시점 |

> **19-P-10 caveat 4 / 19-P-9 caveat 2 / 19-P-8 caveat 3 — `.venv` Python 런처 부재로 PyInstaller 53 tests collection 미실행 → 본 19-0 시점 해소 ✓**.
>
> Codex 가 PowerShell 경로에서 `.venv` 를 잡지 못한 것일 뿐, bash 에서 `venv/Scripts/*.exe` 직접 실행 정상 동작.

## 2. 실행한 검증 명령 (5개)

| # | 명령 | 결과 | 시간 |
|---|---|---|---|
| C-1 | `venv/Scripts/python.exe scripts/check_db_path.py` | exit 0 — 운영 DB 경로 감지 (직접 실행 시 정상, 테스트 중 ⊥) | 즉시 |
| C-2 | `venv/Scripts/python.exe -m ruff check app tests scripts` | **All checks passed!** — exit 0 | 즉시 |
| C-3 | `venv/Scripts/python.exe -m pytest tests -q` | **529 passed, 1 skipped, 7 xfailed, 27 warnings** — exit 0 | 12.45초 |
| C-4 | `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py --collect-only -q` | **53 tests collected** — exit 0 (bash 셸 기준) | 0.04초 |
| C-5 | `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **53 passed** — exit 0 | 0.36초 |

> **r2 보정 (19-0 caveat 1 — `--collect-only` 단독 명령 PowerShell 재현성)**: C-4 명령은 본 19-0 시점 bash 셸 (`venv/Scripts/python.exe`) 직접 실행으로 53 tests collected 통과. PowerShell 셸에서는 `--collect-only` 단독 명령 재현이 환경 의존적으로 실패할 수 있음 (Codex r1 §3 caveat 1). 단, **C-5 (`pytest -q`) 의 53 passed 는 PowerShell 에서도 정상 동작 — 산출 공식 (15 + 19×2 = 53) 검증은 C-5 결과로 충분**. 19-1 이후에는 산출 공식 검증을 C-5 (실제 실행) 로 통일 권장.

## 3. 18-8 baseline 회귀 검증

| 항목 | 18-8 baseline | 19-0 시점 | 일치 |
|---|---|---|---|
| passed | 529 | **529** | ✓ |
| skipped | 1 | **1** | ✓ |
| xfailed | 7 | **7** | ✓ |
| failed | 0 | **0** | ✓ |
| errors | 0 | **0** | ✓ |
| warnings | (다수) | 27 (PytestReturnNotNoneWarning — `test_ai_sms_validate.py` 의 tuple return 패턴, 기존 알려진 warning) | ✓ (회귀 0) |

> **결과: 18-8 baseline 100% 일치 — 회귀 0**.

## 4. PyInstaller 53 tests 산출 공식 재검증

| 19-P-9 §0-2 산출 공식 | 19-0 시점 실측 | 일치 |
|---|---|---|
| def test_ 함수 17개 | 17 (collect-only 결과) | ✓ |
| non-parametrized 15 | 15 | ✓ |
| parametrized 2 (`test_18_X_module_in_spec_hidden_imports` + `test_18_X_module_actually_importable`) | 2 | ✓ |
| `EXPECTED_18_X_MODULES` 19개 | 19 (RAG 6 + chunker 5 + indexer 1 + vector 4 + hybrid 2 + admin status 1) | ✓ |
| 합계 = 15 + 19×2 = **53 tests** | **53 collected, 53 passed** | ✓ |

> **결과: PyInstaller 53 tests 산출 공식 정확 — 19-P-8 caveat 3 / 19-P-9 caveat 2 / 19-P-10 caveat 4 모두 해소 ✓**.

## 5. baseline 측정값 재실측 (19-P-10 §4-1 정합)

| 항목 | 19-P-10 §4-1 | 19-0 실측 | 일치 |
|---|---|---|---|
| `app/routers/api.py` 라인 수 (bash) | 5127 | 5127 | ✓ |
| `app/routers/api.py` endpoint | 86 | 86 | ✓ |
| `app/routers/ai.py` 라인 수 | 929 | 929 | ✓ |
| `app/routers/ai.py` endpoint | 13 | 13 | ✓ |
| `app/templates/main.html` | 7331 | 7331 | ✓ |
| `app/static/css/app.css` | 3626 | 3626 | ✓ |
| `tests/test_*.py` | 40 | 40 | ✓ |
| ORM 모델 | 19 | 19 | ✓ |
| 마이그레이션 | 13 | 13 | ✓ |
| PyInstaller tests | 53 | 53 | ✓ |

> **결과: 19-P-10 §4-1 baseline 측정값 100% 일치 — drift 0**.

## 6. 운영 DB 보호 / 외부 API 차단 재확인

| # | 검사 | 결과 |
|---|---|---|
| S-1 | `scripts/check_db_path.py` | exit 0 (감지 메시지는 직접 실행 시 정상) |
| S-2 | `tests/conftest.py` 4단계 격리 (APPDATA + DOSU_DB_PATH + 워커 no-op + SDK block) | 529 passed 통과 시 자동 검증 |
| S-3 | `tests/harness/db_guard.py:assert_safe_db_path()` | conftest import-time 1회 + session-scope fixture 1회 = 정상 동작 |
| S-4 | `_block_sdk_modules` (openai / anthropic SDK 차단) | conftest import-time 자동 활성 |
| S-5 | `test_*_does_not_use_operational_db` 다수 | 529 passed 통과 시 자동 검증 |

> **결과: S-1 ~ S-5 모두 통과 — 운영 DB 미접근 + 외부 API 호출 0**.

## 7. 부재 항목 단정 ⊥ 재확인 (19-P-10 §4-2 정합)

| 부재 항목 | grep 결과 | 일치 |
|---|---|---|
| `class Doctor\|Department\|Room\|DoctorSchedule\|Order\|Prescription\|Resource` in `app/models/models.py` | 0건 | ✓ |
| `doctor_id` in `app/models/models.py` | 0건 | ✓ |
| `no_show` in `app/models/models.py` | 0건 | ✓ |

> **결과: 부재 항목 단정 ⊥ 정책 100% 정합**.

## 8. 워크트리 dirty/untracked 상태

| 항목 | 카운트 | 비고 |
|---|---|---|
| modified tracked | **6** (`.gitignore` / `app/models/models.py` / `app/routers/ai.py` / `app/services/ai/manual_qa.py` / `dosu_clinic.spec` / `tests/conftest.py`) | 18-0 ~ 18-8 변경분 |
| untracked | 50 | 18-0 ~ 18-8 산출물 (마이그레이션 m012/m013, AI RAG/knowledge/vector, 신규 harness/test, 19-P-1~10 docs, 19-P-1~10 reports) |
| 본 19-0 추가 변경 | 0 (코드/테스트/spec/UI/migrations/requirements) + 본 리포트 2개 (19-0_test_report.md / latest_test_report.md) | read-only 검증 정책 |

> **caveat (19-P-1 G-1 부터 누적)**: 19-P 시리즈 검증 요청서에 "5 tracked" 로 표기됐으나 실제 6 tracked (`.gitignore` 포함). 19-P-10 §3-2 에 추가 caveat 로 인지 — *진행 차단 ⊥*.

## 9. 19-P 시리즈 caveat 본 19-0 시점 해소 현황

### 9-1. 본 19-0 시점에 해소된 caveat

| caveat | 해소 근거 |
|---|---|
| 19-P-8 caveat 3 / 19-P-9 caveat 2 / 19-P-10 caveat 4 — PyInstaller "53 tests" collection 미실행 | 본 §4 — 53 collected + 53 passed 모두 통과 |
| 19-P-10 §5-2 환경 복구 1번 — `.venv\Scripts\python.exe` 존재 여부 | 본 §1 — 정상 존재 (274 KB, 2026-05-02) |
| 19-P-10 §5-2 환경 복구 2번 — pytest 실행 가능 여부 | 본 §1 — pytest 8.4.2 동작 |
| 19-P-10 §5-2 환경 복구 3번 — ruff 실행 가능 여부 | 본 §1 — ruff 0.15.12 동작 |
| 19-P-10 §5-2 환경 복구 4번 — check_db_path 실행 가능 여부 | 본 §2 C-1 — exit 0 |
| 19-P-6 §3-0 baseline 일치 확인 | 본 §3 — 529/1/7 정확 일치 |

### 9-2. 본 19-0 시점에 보정 가능 (사용자 결정 후 진행)

| caveat | 보정 방법 |
|---|---|
| 19-P-9 caveat 1 — `## [0-9]+\.` grep 명령 fenced markdown 예시까지 잡음 | [reports/refactor/19-P-9_codex_review_request.md](../refactor/19-P-9_codex_review_request.md) §11 G-2 명령 보정 또는 [docs/refactor/19_refactor_checklists.md](../../docs/refactor/19_refactor_checklists.md) 명령 갱신 |
| 19-P-9 caveat 3 — 요청서에 `19-P-5 r2` 표기 (실제 r3) | [reports/refactor/19-P-9_codex_review_request.md](../refactor/19-P-9_codex_review_request.md) §7 표기 보정 |
| 19-P-10 caveat 1 — §1 산출물 총계 "29" vs §7 "30" 산술 불일치 | [docs/refactor/19_refactor_final_check.md §1](../../docs/refactor/19_refactor_final_check.md) 표기 보정 |
| 19-P-10 caveat 2 — `ls docs/refactor/ # 10개 기대` 가 실제 11개 (entry_notes 포함) | [reports/refactor/19-P-10_codex_review_request.md](../refactor/19-P-10_codex_review_request.md) §11 검증 명령 보정 |
| 19-P-10 caveat 3 — 19-P-9 caveat 추적 번호 매김 (PyInstaller collection 위치) | 보정 불필요 (인지만 — 실제로 본 19-0 에서 해소됨) |

### 9-3. 사용자 결정 필요 (19-P-10 §5-1)

| # | 결정 항목 | 제안 |
|---|---|---|
| 1 | **18-0 ~ 18-8 dirty/untracked 변경분 처리** (6 modified + 50 untracked) | (a) main 머지 (v1.3.3 → v1.4.0 release notes 후속) / (b) 별도 commit 만 남기고 main 머지 보류 / (c) 그대로 유지 (19-x 코드 세션마다 G-1 pass with caveat 누적) |
| 2 | **`docs/ai_rag_current_state.md` stale 보정 시점** | (a) 19-0 안 read-only 갱신 / (b) 별도 문서 갱신 세션 / (c) post-19-P |
| 3 | **19-P-9 / 19-P-10 caveat 5개 보정 시점** (§9-2 표) | (a) 19-0 안에서 즉시 (read-only 문서 보정 — 코드 영향 0) / (b) 19-1 진입 직전 / (c) 통합 보정 세션 |

## 10. 종합

- **18-8 baseline 100% 일치** — 529 passed, 1 skipped, 7 xfailed (회귀 0).
- **모든 baseline 측정값 19-P-10 §4-1 와 100% 일치** — drift 0.
- **PyInstaller 53 tests 산출 공식 정확 검증** — 53 collected + 53 passed.
- **운영 DB 보호 + 외부 API 차단 + 부재 항목 단정 ⊥ 100% 정합**.
- **19-P 시리즈 caveat 6개 본 19-0 시점에 해소** (PyInstaller 53 / `.venv` 4건 / baseline 일치).
- **본 19-0 시점에 보정 가능 caveat 5개** (사용자 결정 후 — read-only 문서 보정만).
- **사용자 결정 필요 3건** (dirty 변경분 처리 / stale 보정 시점 / caveat 보정 시점).
- **본 19-0 추가 코드 / 테스트 / spec / UI / migrations / requirements 변경 = 0** (read-only 검증).
- **19-1 진입 권고**: 사용자 결정 3건 답변 후 [19-P-6 §3-1 (19-1 core 분리)](../../docs/refactor/19_refactor_rollout_plan.md) 진입 가능.

## 11. 다음 단계

1. **사용자 결정 3건 답변 대기** (§9-3).
2. 결정 답변 후:
   - (옵션 1) caveat 보정만 진행 (read-only) → Codex 검증 → 19-1 진입
   - (옵션 2) caveat 보정 + dirty 변경분 처리 (머지 또는 commit) → Codex 검증 → 19-1 진입
   - (옵션 3) 19-1 직진 (caveat 보정 보류 — 19-x 코드 세션마다 누적) → 비권장
3. 19-1 진입 직전에 **19-P-9 §1 ~ §2 체크리스트** 적용.
