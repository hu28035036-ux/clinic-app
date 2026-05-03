# 19-1 core 공통 유틸 정리 — 테스트 리포트

> 19-1 = **첫 번째 실제 코드 리팩토링 세션**. `app/core/` 신설 + 7개 파일 (re-export 3 + 신규 4) + spec 갱신.
> **5회 루프 1회차에 통과 (545 passed, 1 skipped, 7 xfailed) — 18-8 baseline 회귀 0**.

## 0. 메타

- 세션 이름: **19-1 core 공통 유틸 / 응답 / 에러 / 시간 유틸 정리**
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 commit (시작 HEAD): `09f49c1` (commit 2: 19-P 단위화 리팩토링 준비 + 19-0 baseline 재고정)
- 18-8 baseline: 529 passed, 1 skipped, 7 xfailed
- **19-1 baseline (신규)**: **545 passed, 1 skipped, 7 xfailed** = 529 + 16 (PyInstaller 19-1 core 검증 16 tests 추가)
- 직전 세션 19-0 Codex: **pass with caveat — yes 19-1 진입 가능**

## 1. 실행 환경

| 항목 | 값 |
|---|---|
| Python | 3.12.10 |
| pytest | 8.4.2 |
| ruff | 0.15.12 |

## 2. 실행한 검증 명령

| # | 명령 | 결과 | 시간 |
|---|---|---|---|
| C-1 | `venv/Scripts/python.exe -m pytest tests -q` | **545 passed, 1 skipped, 7 xfailed, 27 warnings** | 10.68초 |
| C-2 | `venv/Scripts/python.exe -m ruff check app tests scripts` | **All checks passed!** | 즉시 |
| C-3 | `venv/Scripts/python.exe scripts/check_db_path.py` | exit 0 | 즉시 |
| C-4 | `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **69 passed** (= 53 + 16 신규) | 0.47초 |
| C-5 | `venv/Scripts/python.exe -c "from app.core import ..."` | all core imports OK | 즉시 |

## 3. baseline 회귀 검증

| 항목 | 18-8 baseline | 19-0 시점 | 19-1 시점 | 일치 |
|---|---|---|---|---|
| passed | 529 | 529 | **545** (= 529 + 16 신규 PyInstaller) | ✓ (신규만 +16) |
| skipped | 1 | 1 | **1** | ✓ |
| xfailed | 7 | 7 | **7** | ✓ |
| failed | 0 | 0 | **0** | ✓ |
| errors | 0 | 0 | **0** | ✓ |

> **18-8 baseline 회귀 0** — 추가된 16 tests = 19-1 core 8 모듈 × 2 parametrized (in_spec_hidden_imports + actually_importable). 기존 529 tests 모두 그대로 통과.

## 4. 5회 루프 카운트

| 회차 | 실행 명령 | 결과 |
|---|---|---|
| 1 | ruff + check_db_path + core import + PyInstaller + 전체 pytest | **모두 통과** ✓ |

→ **5회 루프 1회차에 통과** (땜질 ⊥, 추가 수정 ⊥).

## 5. PyInstaller hidden imports 검증 (69 tests)

| 카테고리 | 카운트 | 결과 |
|---|---|---|
| 18-1~18-7 신규 모듈 in_spec | 19 (`EXPECTED_18_X_MODULES` × 1) | ✓ 19 passed |
| 18-1~18-7 신규 모듈 importable | 19 | ✓ 19 passed |
| **19-1 core 신규 모듈 in_spec** | **8** (`EXPECTED_19_X_CORE_MODULES` × 1) | ✓ **8 passed** |
| **19-1 core 신규 모듈 importable** | **8** | ✓ **8 passed** |
| non-parametrized (spec 검증 + 데이터 번들) | 15 | ✓ 15 passed |
| **합계** | **69** | ✓ **69 passed** |

> 19-1 core 8 모듈 모두 spec hidden imports 등록 + 실제 import 가능 확인 ✓.

## 6. 응답 키 / API 보존 검증

| 검사 | 결과 |
|---|---|
| 33+ 응답 키 셋 (manual/search 3 + manual/ask 9 + sources 3 + health 9 + health/public 4 + status 9 + 비-AI alias) | ✓ 545 passed 통과 시 자동 검증 |
| `/api/ai/manual/search` (3키) | ✓ |
| `/api/ai/manual/ask` (9키) | ✓ |
| `/api/ai/health` admin 9키 / public 4키 | ✓ |
| API URL 변경 0 | ✓ |
| `app.core.responses.MANUAL_SEARCH_KEYS` / `MANUAL_ASK_KEYS` / `HEALTH_ADMIN_KEYS` / `HEALTH_PUBLIC_KEYS` 상수 정의 (신규) | ✓ |

## 7. 운영 DB 보호 + 외부 API 차단

| # | 검사 | 결과 |
|---|---|---|
| S-1 | `check_db_path.py` exit 0 | ✓ |
| S-2 | `tests/conftest.py` 4단계 격리 | ✓ (545 passed) |
| S-3 | `db_guard.assert_safe_db_path()` | ✓ |
| S-4 | `_block_sdk_modules` (openai/anthropic SDK 차단) | ✓ |
| S-5 | `test_*_does_not_use_operational_db` 다수 | ✓ |
| FakeProvider / FakeEmbeddingProvider 만 사용 | ✓ |
| local_only LLM/Embedding 호출 0 | ✓ (AI-Mode 19 passed) |
| API key 원문 응답/로그 부재 | ✓ (Safety 36 passed) |
| 실제 OpenAI/Anthropic/문자나라 호출 | ✓ 0건 |

> **운영 DB 미접근 100% + 외부 API 호출 0건 100% 정합**.

## 8. 카테고리별 회귀 (변경 없음)

| 카테고리 | 결과 |
|---|---|
| AI/RAG 9 카테고리 (RAG/Safety/Chunker/Reindex/Vector/Hybrid/Health/ManualQA/AI-Mode) | ✓ 모두 19-0 와 동일 |
| 기존 기능 8 카테고리 (예약/휴무/SMS/통계/환자/관리자/SMS AI/휴무 AI) | ✓ 모두 19-0 와 동일 |
| PyInstaller (53 → 69, +16 신규 19-1 core) | ✓ |

## 9. 코드 변경 범위

```
git diff --stat 09f49c1 -- app dosu_clinic.spec tests/test_pyinstaller_hidden_imports.py
 app/core/__init__.py                       |   N (신규)
 app/core/config.py                         |   N (신규 — re-export wrapper)
 app/core/database.py                       |   N (신규 — re-export wrapper)
 app/core/security.py                       |   N (신규 — re-export wrapper)
 app/core/errors.py                         |   N (신규 — reason_code 상수)
 app/core/responses.py                      |   N (신규 — 응답 키 상수 + assert_keys helper)
 app/core/time_utils.py                     |   N (신규 — Asia/Seoul / 반차 12:00 / 점심창)
 app/core/feature_flags.py                  |   N (신규 — ai_mode + AI_RAG_*/VECTOR/HYBRID env helper)
 dosu_clinic.spec                           |   +9 (19-1 core 8 모듈 hidden imports 추가)
 tests/test_pyinstaller_hidden_imports.py   |   +N (EXPECTED_19_X_CORE_MODULES + parametrized 2 tests)
```

→ **신규 파일만 + spec 갱신 + 테스트 갱신**. 기존 코드 / API URL / 응답 키 / DB schema / migration / UI / requirements 0 변경.

## 10. 19-2 settings / feature_flags / health 경계 정리 진입 권고

**yes — 19-2 진입 가능** (Codex 검증 후).

근거:
1. 본 19-1 = 신규 폴더 / 파일만 추가. 기존 동작 0 변경 (회귀 0).
2. 545 passed (18-8 + 19-1 신규 16) — 18-8 baseline 100% 회귀 0.
3. ruff All checks passed / check_db_path exit 0 / PyInstaller 69 passed.
4. core 가 modules 를 import 하지 않음 (D-4 정합) — re-export wrapper 만 (`app.config` / `app.database` / `app.services.auth` 정참조).
5. compatibility wrapper 유지 — 기존 import 경로 0 변경.
6. 응답 키 33+ 셋 보존 / 운영 DB 미접근 / 외부 API 호출 0 / local-first 보존.
7. 5회 루프 1회차 통과 — 땜질 ⊥.

다음 세션:
- **19-2 settings / feature_flags / health 경계 정리** ([docs/refactor/19_refactor_rollout_plan.md §3-2](../../docs/refactor/19_refactor_rollout_plan.md)) — `modules/settings/` 신규 + `core/feature_flags.py` 채택 + `/api/health` 후속 검토 분류 명시.
