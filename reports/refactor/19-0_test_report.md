# 19-0 단위화 리팩토링 전 기준 테스트/하네스 재확인 — 테스트 리포트

> 19-P-1 ~ 19-P-10 (준비 단계 10개 문서) 완료 후 **19-x 실제 코드 리팩토링 세션 진입 직전 baseline 확보** 세션의 reports/refactor 보고서.
> 본 19-0 = read-only 검증 세션. **18-8 baseline 100% 일치 — 529 passed, 1 skipped, 7 xfailed**.

## 0. 메타

- 세션 이름: **19-0 단위화 리팩토링 전 기준 테스트/하네스 재확인**
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed** ([reports/ai_dev_loop/18-8_test_report.md](../ai_dev_loop/18-8_test_report.md))
- 직전 세션 19-P-10 r5 Codex: **pass with caveat — yes 19-1 진입 가능** ([latest_codex_review.md](latest_codex_review.md) r5)

> **본 reports/refactor/19-0_test_report.md** 는 사용자 명시 `19_refactor_baseline_test_result.md` 의 *reports 영역 사본 / 보고서 형식*. 본문 권위는 [docs/refactor/19_refactor_baseline_test_result.md](../../docs/refactor/19_refactor_baseline_test_result.md) 정합.

## 1. 실행 환경

| 항목 | 값 |
|---|---|
| Python | 3.12.10 (`venv/Scripts/python.exe`) |
| pytest | 8.4.2 |
| ruff | 0.15.12 |
| OS | Windows (bash 셸 = Git Bash) |
| 마이그레이션 자동 적용 | m001 ~ m013 (13개) |

## 2. 실행한 테스트 명령 (5개)

| # | 명령 | 결과 | 시간 |
|---|---|---|---|
| C-1 | `venv/Scripts/python.exe -m pytest tests -v --tb=short` | **529 passed, 1 skipped, 7 xfailed, 27 warnings** | 11.74초 |
| C-2 | `venv/Scripts/python.exe -m ruff check app tests scripts` | **All checks passed!** (exit 0) | 즉시 |
| C-3 | `venv/Scripts/python.exe scripts/check_db_path.py` | exit 0 | 즉시 |
| C-4 | `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **53 passed** | 0.39초 |
| C-5 | (카테고리별) `pytest tests/test_<cat>*.py --tb=no -q` | 각 카테고리 모두 통과 | (개별) |

## 3. 18-8 baseline 회귀 검증

| 항목 | 18-8 baseline | 19-0 시점 | 일치 |
|---|---|---|---|
| passed | 529 | **529** | ✓ |
| skipped | 1 | **1** | ✓ |
| xfailed | 7 | **7** | ✓ |
| failed | 0 | **0** | ✓ |
| errors | 0 | **0** | ✓ |
| warnings | (다수 PytestReturnNotNoneWarning) | 27 (기존 알려진 패턴) | ✓ |

> **결과: 18-8 baseline 100% 일치 — 회귀 0**.

## 4. 카테고리별 테스트 결과

> [docs/refactor/19_refactor_baseline_test_result.md §3](../../docs/refactor/19_refactor_baseline_test_result.md) 정합.

### 4-1. AI/RAG 하네스 (9 카테고리)

| 카테고리 | 결과 |
|---|---|
| RAG (18-1) | 49 passed |
| Safety (18-1, PII / 할루시네이션) | 36 passed |
| Chunker (18-3) | 35 passed |
| Reindex (18-4) | 24 passed |
| Vector (18-5) | 36 passed |
| Hybrid (18-6) | 46 passed |
| Health/Admin (18-7) | 82 passed |
| ManualQA / Contract | 19 passed |
| AI-Mode (local-first) | 19 passed |

### 4-2. 기존 기능 회귀 (8 카테고리)

| 카테고리 | 결과 |
|---|---|
| Appointment (예약) | 6 passed, 1 skipped, 3 xfailed |
| Leaves (휴무) | 10 passed, 4 xfailed |
| SMS validation | 6 passed (test_sms_secret_masking) |
| Stats (통계) | 6 passed |
| Employee (직원) | 4 passed (can_manual_contract + hire_date) |
| AI-SMS (기존 SMS AI) | 27 passed (warnings 21) |
| AI-ActionLeave (기존 휴무 AI) | 44 passed |
| AI-Logging | 6 passed |

### 4-3. PyInstaller / 마이그레이션

| 카테고리 | 결과 |
|---|---|
| PyInstaller hidden imports | 53 passed (산출 공식 = 15 non-parametrized + 19×2 parametrized = 53) |
| Migration spec discovery | (PyInstaller 묶음 57 passed 안에 포함) |

## 5. 실패한 테스트

**failed = 0 / errors = 0**.

### 5-1. xfail 7건 + skip 1건 (백엔드 차단 미구현 명시 — 19-4/19-5 정방향 전환 예정)

[docs/refactor/19_refactor_baseline_test_result.md §4-1](../../docs/refactor/19_refactor_baseline_test_result.md) 정합. 19-P-7 §2-A R-APPT-02 / R-APPT-03 / R-APPT-04 위험 등록 정합.

## 6. 운영 DB 보호 + 외부 API 차단 결과

| # | 검사 | 결과 |
|---|---|---|
| S-1 | check_db_path.py | ✓ exit 0 |
| S-2 | conftest.py 4단계 격리 | ✓ pass |
| S-3 | db_guard.assert_safe_db_path() | ✓ pass |
| S-4 | _block_sdk_modules (openai/anthropic SDK 차단) | ✓ pass |
| S-5 | test_*_does_not_use_operational_db | ✓ pass |
| FakeProvider / FakeEmbeddingProvider 만 사용 | ✓ pass |
| local_only LLM/Embedding 호출 0 | ✓ pass (AI-Mode 19 passed) |
| API key 원문 응답/로그/audit 부재 | ✓ pass (Safety 36 passed) |
| 실제 OpenAI/Anthropic/문자나라 호출 | **0건** ✓ |

## 7. 19-P 시리즈 caveat 본 19-0 시점 해소 현황

### 7-1. 본 19-0 시점 해소 (직전 19-0 baseline 검증 + 본 세션 검증)

- 19-P-8 caveat 3 / 19-P-9 caveat 2 / 19-P-10 caveat 4 (PyInstaller 53 tests collection 미실행) — **53 collected + 53 passed 검증 완료** ✓
- 19-P-10 §5-2 환경 복구 4 항목 (.venv / pytest / ruff / check_db_path) — 모두 정상 ✓
- 19-P-9 caveat 1 (`## [0-9]+\.` grep 명령 fenced markdown 예시 포함) — 19-P-9 r2 보정 완료 ✓
- 19-P-9 caveat 3 (요청서 r2 → r3 표기) — 19-P-9 r2 보정 완료 ✓
- 19-P-10 r4 caveat 1 (baseline line count 70 줄 차이 — Codex `Get-Content` 측정 오류) — 19-P-10 r5 다중 측정 검증 (raw newline / .NET ReadLines / git show) 모두 5127 일치 확인 ✓

### 7-2. 19-x 분리 직전 보강 필수 (9개 항목)

[docs/refactor/19_refactor_baseline_test_result.md §6-1](../../docs/refactor/19_refactor_baseline_test_result.md) 정합. 비-AI 86 endpoint contract / 점심창 / PUT/DELETE/409 / xfail 7+1건 정방향 / approve-revert / stats 8 GET / tomorrow-targets / 환자 검색-메모-counts.

### 7-3. 사용자 결정 필요 (1건)

- 18-0 ~ 18-8 dirty/untracked 변경분 (6 modified + 50 untracked) 처리 결정 (머지 / commit / 유지) — 19-1 진입 직전 결정.

## 8. 코드 영역 무수정 검증

```
git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements*.txt app/templates app/static pyproject.toml
 app/models/models.py         | 123 +++++++++++++++++-
 app/routers/ai.py            |  42 ++++++
 app/services/ai/manual_qa.py | 298 +++++++------------------------------------
 dosu_clinic.spec             |  30 ++++-
 tests/conftest.py            | 132 +++++++++++++++++++
 5 files changed, 373 insertions(+), 252 deletions(-)
```

→ 18-0 ~ 18-8 변경분 5 tracked 만, **본 19-0 추가 코드 변경 0** ✓.

## 9. 19-1 진입 권고

**yes — 19-1 core 공통 유틸 정리 진입 가능** (사용자 dirty worktree 결정 답변 후).

[docs/refactor/19_refactor_baseline_test_result.md §12](../../docs/refactor/19_refactor_baseline_test_result.md) 진입 게이트 BG-1 ~ BG-10 정합. BG-10 (사용자 결정) 외 9 항목 모두 pass.

다음 세션: **19-1 core 공통 유틸 정리** — [docs/refactor/19_refactor_rollout_plan.md §3-1](../../docs/refactor/19_refactor_rollout_plan.md).
