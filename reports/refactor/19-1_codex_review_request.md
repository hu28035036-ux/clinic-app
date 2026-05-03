# 19-1 Codex 검증 요청서 — core 공통 유틸 정리

> **사용자가 Codex에게 전달할 최소 문구**
>
> > "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

## 0. Revision 이력

| 회차 | 날짜 | 결과 | 변경 |
|---|---|---|---|
| r1 | 2026-05-03 | **pass with caveat — yes 19-2 진입 가능** ([reports/refactor/latest_codex_review.md](latest_codex_review.md) r1 시점) | 초기 작성 — 19-1 core 공통 유틸 정리. 5회 루프 1회차 통과. caveat 1: line count 부정확 / caveat 2: 수정량 +9/+30 vs 실제 +10/+42 / caveat 3: `python -c` 직접 import Codex 환경 재현 실패 / caveat 4: untracked dirty. |
| r2 | 2026-05-03 | (본 revision) | **r1 Codex caveat 1, 2 보정 (옵션 D 사용자 결정)** — 실측 line count 재측정 (bash `wc -l`): __init__ 12 / config 41 / database 37 / security 47 / errors 77 / responses 109 / time_utils 100 / feature_flags 126 = 합계 549. diff stat 정확: spec +10 / test +42 = 합계 +52. 본 §3 + §16 검증 명령에 PowerShell `(Get-Content).Count` 추가 (caveat 3 정합 — 환경 의존성 해소). 코드 변경 0, 문서 수치만 보정. |

## 1. 세션 이름

**19-1 core 공통 유틸 / 응답 / 에러 / 시간 유틸 정리**

- 19-P-1 ~ 19-P-10 + 19-0 baseline 의 후속 **첫 번째 실제 코드 리팩토링 세션 (실행 #2)**.
- 19-P-2 §2-1 V2 트리의 `app/core/` 자리 신설.
- [docs/refactor/19_refactor_rollout_plan.md §3-1](../../docs/refactor/19_refactor_rollout_plan.md) 정합.

## 2. 이번 세션 목표

| # | 목표 | 결과 |
|---|---|---|
| 1 | `app/core/` 폴더 신설 | ✓ 8 파일 (`__init__.py` + 7 모듈) |
| 2 | `config.py` / `database.py` / `security.py` re-export wrapper | ✓ COMPAT 주석 + 본체 이동 0 + TODO(19-x) 명시 |
| 3 | `errors.py` / `responses.py` / `time_utils.py` / `feature_flags.py` 신규 helper | ✓ reason_code 21 / 응답 키 상수 / Asia/Seoul / ai_mode env helpers |
| 4 | 기존 import 경로 호환 유지 | ✓ `from app.config` / `from app.database` / `from app.services.auth` 0 변경 |
| 5 | 기존 동작 0 변경 | ✓ 545 passed (= 529 baseline + 16 신규 PyInstaller) |
| 6 | dosu_clinic.spec hidden imports 갱신 | ✓ 9 lines 추가 (19-1 core 8 모듈) |
| 7 | PyInstaller 53 → 69 tests (신규 16) | ✓ `EXPECTED_19_X_CORE_MODULES` + parametrized 2 tests |
| 8 | 18-8 baseline 회귀 0 | ✓ 529 passed 그대로 + 16 신규만 추가 |

## 3. 변경 파일 목록

### 신규 (8개) — r2 실측 보정 (bash `wc -l`)

- `app/core/__init__.py` — **12 lines**, 빈 facade + D-4 정합 docstring
- `app/core/config.py` — 41 lines, **re-export wrapper** (`app.config` 11 API)
- `app/core/database.py` — **37 lines**, **re-export wrapper** (`app.database` 7 API)
- `app/core/security.py` — **47 lines**, **re-export wrapper** (`app.services.auth` 13 API)
- `app/core/errors.py` — **77 lines**, 신규 helper (reason_code 21개)
- `app/core/responses.py` — **109 lines**, 신규 helper (응답 키 상수 + `assert_keys`)
- `app/core/time_utils.py` — **100 lines**, 신규 helper (Asia/Seoul / 12:00 / 점심창)
- `app/core/feature_flags.py` — **126 lines**, 신규 helper (ai_mode + env helpers)
- **합계: 549 lines** (bash `wc -l app/core/*.py` 기준)

### 수정 (2개) — r2 실측 보정 (`git diff --stat 09f49c1`)

- `dosu_clinic.spec` — **+10 lines** (19-1 core 8 모듈 hidden imports)
- `tests/test_pyinstaller_hidden_imports.py` — **+42 lines** (`EXPECTED_19_X_CORE_MODULES` + 2 parametrized tests)
- **합계: +52 lines** (`git diff --stat 09f49c1 -- dosu_clinic.spec tests/test_pyinstaller_hidden_imports.py` 기준)

### 무수정 (회귀 보호)

`app/config.py`, `app/database.py`, `app/services/auth.py`, `app/routers/*.py`, `app/services/ai/**`, `app/templates/**`, `app/static/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `pyproject.toml`, `app/models/**`, `tests/conftest.py`, `tests/harness/**`, 기존 `tests/test_*.py` (test_pyinstaller_hidden_imports.py 외).

## 4. 실제 이동한 코드

**0 줄** — 본 19-1 시점에 *실제 본체 이동 0*. 모두 신규 helper 또는 re-export wrapper.

```python
# app/core/config.py — re-export pattern
from app.config import (
    APP_NAME, APP_VERSION, APP_BUILD_DATE, DEFAULT_CONFIG,
    get_appdata_dir, get_db_path, get_config_path, get_backup_dir,
    load_config, save_config, resource_path,
)
```

기존 `app/config.py` / `app/database.py` / `app/services/auth.py` 는 *본체 그대로*. 기존 import 경로는 모두 그대로 동작.

## 5. compatibility wrapper 유지 여부

| wrapper | 위치 | COMPAT 주석 | 기존 import 호환 | 본체 이동 |
|---|---|---|---|---|
| `app/core/config.py` | re-export | ✓ | ✓ | ⊥ (TODO(19-x)) |
| `app/core/database.py` | re-export | ✓ | ✓ | ⊥ (TODO(19-x)) |
| `app/core/security.py` | re-export | ✓ | ✓ | ⊥ (TODO(19-x)) |

→ **3 wrapper 모두 유지** — 기존 `from app.config` / `from app.database` / `from app.services.auth` 경로 그대로 동작 + 신규 `from app.core.config` / `from app.core.database` / `from app.core.security` 동시 지원.

## 6. 수정 금지 범위 준수 여부

11개 금지 항목 (사용자 명시) 모두 준수:
1. ✓ 예약/휴무/문자/통계/AI 기능 로직 변경 0
2. ✓ app 전체 대규모 이동 ⊥ (신규 폴더만)
3. ✓ DB schema 변경 0 (m001~m013 diff 0)
4. ✓ migration 신규 ⊥
5. ✓ UI 변경 0
6. ✓ 기존 API 응답 key 변경 0 (33+ 키 셋 보존)
7. ✓ 하네스/테스트 약화 ⊥ (`xfail`/`skip` 으로 덮기 ⊥)
8. ✓ 운영 DB 접근 0
9. ✓ 실제 외부 API 호출 0
10. ✓ requirements.txt 수정 0
11. ✓ PyInstaller spec *불필요 수정* 0 (hidden imports 갱신은 *필요* 변경)

추가:
- ✓ 기존 SMS AI / 휴무 AI 동작 변경 0 (각 27 / 44 passed 통과)
- ✓ 18-8 baseline 회귀 0 (529 passed 그대로 + 16 신규만)

## 7. 기존 API 응답 key 유지 여부

✓ **33+ 키 셋 100% 보존**:
- `/api/ai/manual/search` (3키): sources / masked_question / top_score
- `/api/ai/manual/ask` (9키): answer / sources / confidence / not_found / blocked / blocked_reason / guard_hits / top_score / masked_question
- `sources[]` (3키): title / path / snippet
- `/api/ai/health` admin 9키 / public 4키
- `/api/ai/status` 18-7 9 top-level
- 비-AI alias: `therapist_id` 이중 키 등

`app/core/responses.py` 에 응답 키 상수 (`MANUAL_SEARCH_KEYS` / `MANUAL_ASK_KEYS` / `SOURCE_ITEM_KEYS` / `HEALTH_ADMIN_KEYS` / `HEALTH_PUBLIC_KEYS`) 정의 — *신규* 만, 기존 응답 dict 빌드 위치는 변경 0.

## 8. 운영 DB 보호 여부

✓ S-1 ~ S-5 모두 통과 ([19-1_test_report.md §7](19-1_test_report.md)):
- `check_db_path.py` exit 0
- `tests/conftest.py` 4단계 격리 활성
- `db_guard.assert_safe_db_path()` import-time + session-scope
- `_block_sdk_modules` 활성
- `test_*_does_not_use_operational_db` 다수 통과

`app/core/config.py` SAFETY 주석 명시 — `DOSU_DB_PATH` 환경변수 우선 정책 보존 (테스트/하네스 운영 DB 미접근).

## 9. 외부 API 호출 여부

✓ **0건**:
- `_block_sdk_modules` 자동 활성 (openai/anthropic SDK RuntimeError 교체)
- FakeProvider / FakeEmbeddingProvider 만 사용
- `local_only` 모드 LLM/Embedding 호출 0 (AI-Mode 19 passed)
- API key 원문 응답/로그 부재 (Safety 36 passed)
- 실제 OpenAI / Anthropic / 문자나라 호출 0

`app/core/feature_flags.py` SAFETY 주석 명시 — local_only 외부 호출 0 (DEC-N 절대 원칙).

## 10. 순환참조 위험 여부

✓ **순환참조 0**:

| 의존 | 방향 | 결과 |
|---|---|---|
| `app/core/config.py` → `app/config.py` | core → app (root) | ✓ (re-export) |
| `app/core/database.py` → `app/database.py` → `app/config.py` | core → app | ✓ (re-export) |
| `app/core/security.py` → `app/services/auth.py` → `app/config.py` | core → services → app | ✓ (re-export) |
| `app/core/{errors,responses,time_utils,feature_flags}.py` | 외부 의존 ⊥ (typing / os / datetime 만) | ✓ 신규 helper |
| `app/core/__init__.py` | 빈 facade | ✓ |

**core 가 modules 를 import 하지 않음** (D-4 정합 — 19-P-4 §1):
- `from app.modules.*` 참조 0건 (현재 modules 폴더 부재 — 19-2 부터 신설)

`python -c "import app.main"` / `from app.core import ...` 모두 정상 import 확인.

## 11. 주석 / 문서화 기준 적용 여부

[docs/refactor/19_refactor_checklists.md §4](../../docs/refactor/19_refactor_checklists.md) + [19_refactor_decision_record.md DEC-S](../../docs/refactor/19_refactor_decision_record.md) 정합:

| 카테고리 | 적용 |
|---|---|
| 새 파일 상단 docstring | ✓ 8 파일 모두 |
| 주요 helper 함수 docstring | ✓ `assert_keys` / `today` / `tomorrow` / `is_morning` / `is_afternoon` / `is_within_lunch` / `isoformat_minute` / `env_*` 등 |
| `# COMPAT:` (호환 wrapper) | ✓ core/{config,database,security,feature_flags}.py |
| `# SAFETY:` (운영 DB / 외부 API / API key) | ✓ core/{config,database,security,feature_flags}.py |
| `# NOTE:` (업무 규칙 / 정책) | ✓ core/{__init__,errors,responses,time_utils,feature_flags}.py |
| `# RISK:` (동시성 / 의존) | ✓ core/{database,responses,time_utils,feature_flags}.py |
| `# TODO(19-x):` | ✓ core/{__init__,config,database,security}.py (wrapper 제거 + 본체 이동) |
| 의미 없는 모든 줄 주석 ⊥ | ✓ |
| 주석 작성으로 동작 변경 ⊥ | ✓ |

## 12. 실행한 테스트와 결과

| 명령 | 결과 | 시간 |
|---|---|---|
| `pytest tests -q` | **545 passed, 1 skipped, 7 xfailed, 27 warnings** | 10.68초 |
| `ruff check app tests scripts` | **All checks passed!** | 즉시 |
| `check_db_path.py` | exit 0 | 즉시 |
| PyInstaller hidden imports | **69 passed** (= 53 + 16 신규) | 0.47초 |
| core import sanity | OK | 즉시 |

→ **18-8 baseline (529 passed) 회귀 0 + 19-1 신규 16 tests 추가 = 545 passed** ✓

## 13. 실패 / 수정 루프 횟수

| 회차 | 결과 |
|---|---|
| **1** | **모두 통과** ✓ |

→ **5회 루프 1회차에 통과** (땜질 ⊥, `xfail`/`skip` 으로 덮기 ⊥, per-file-ignores 풀기 ⊥, 추가 수정 ⊥).

## 14. 19-2 settings / feature_flags / health 경계 정리 진입 판단 기준

| 게이트 | 통과 조건 | 본 19-1 결과 |
|---|---|---|
| 19-1-G1 코드 변경 범위 최소 | 신규 8 파일 + spec 갱신 + 1 test 파일 갱신 만 | ✓ pass |
| 19-1-G2 18-8 baseline 회귀 0 | 529 passed 그대로 + 19-1 신규만 추가 | ✓ pass (545 passed) |
| 19-1-G3 ruff lint | All checks passed | ✓ pass |
| 19-1-G4 운영 DB 보호 | S-1 ~ S-5 모두 통과 | ✓ pass |
| 19-1-G5 외부 API 차단 | _block_sdk_modules + FakeProvider | ✓ pass |
| 19-1-G6 PyInstaller 53 → 69 | 69 passed | ✓ pass |
| 19-1-G7 응답 키 33+ 보존 | 변경 0 | ✓ pass |
| 19-1-G8 부재 항목 단정 ⊥ | grep 0건 | ✓ pass |
| 19-1-G9 D-1~D-13 정합 | core → modules ⊥ (D-4) / 순환참조 0 | ✓ pass |
| 19-1-G10 compatibility wrapper 유지 | 3 wrapper + COMPAT 주석 + TODO(19-x) | ✓ pass |
| 19-1-G11 5회 루프 1회차 통과 | 1회차 통과 | ✓ pass |
| 19-1-G12 주석 카테고리 6종 | COMPAT/SAFETY/NOTE/RISK/TODO 적용 | ✓ pass |

→ **12 게이트 모두 통과** = **yes — 19-2 settings / feature_flags / health 경계 정리 진입 가능**.

## 15. Codex 가 검증해야 할 문서

### 1차 (필수)

- [reports/refactor/19-1_test_report.md](19-1_test_report.md)
- [reports/refactor/19-1_fix_summary.md](19-1_fix_summary.md)
- 신규 8 파일 (`app/core/*.py`)
- 수정 2 파일 (`dosu_clinic.spec`, `tests/test_pyinstaller_hidden_imports.py`)

### 2차 (대조 기준)

- [docs/refactor/19_refactor_target_architecture.md §2-1](../../docs/refactor/19_refactor_target_architecture.md) (V2 트리 core 자리)
- [docs/refactor/19_refactor_dependency_map.md §1 D-4](../../docs/refactor/19_refactor_dependency_map.md) (core → modules ⊥)
- [docs/refactor/19_refactor_checklists.md §3 + §4](../../docs/refactor/19_refactor_checklists.md) (코드 이동 + 주석)
- [docs/refactor/19_refactor_decision_record.md DEC-A + DEC-E + DEC-S](../../docs/refactor/19_refactor_decision_record.md)
- [reports/refactor/19-0_codex_review.md](19-0_codex_review.md) (직전 baseline)

### Codex 가 직접 검증할 명령

```bash
# 코드 변경 범위
git status --short | grep -v "^.test-tmp"
git diff --stat 09f49c1 -- app dosu_clinic.spec tests/test_pyinstaller_hidden_imports.py

# core 신설 검증
ls app/core/ | wc -l   # 8 (8 파일 + __pycache__ 가능 — 본체는 8)
venv/Scripts/python.exe -c "from app.core import config, database, security, errors, responses, time_utils, feature_flags; print('OK')"

# 18-8 baseline 회귀 검증
venv/Scripts/python.exe -m pytest tests -q   # 545 passed, 1 skipped, 7 xfailed 기대

# PyInstaller 신규 검증
venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q   # 69 passed 기대

# 기존 import 경로 그대로 동작
venv/Scripts/python.exe -c "from app.config import APP_VERSION, get_db_path; from app.database import init_db, engine; from app.services.auth import login, verify_password; print('legacy imports OK')"

# 신규 core import 경로 동작
venv/Scripts/python.exe -c "from app.core.config import APP_VERSION, get_db_path; from app.core.database import init_db, engine; from app.core.security import login, verify_password; print('core imports OK')"

# 주석 카테고리 grep
grep -rE "# (COMPAT|SAFETY|NOTE|RISK|TODO):" app/core/   # 다수 기대

# r2 실측 line count 검증 (bash 환경)
wc -l app/core/*.py   # __init__ 12 / config 41 / database 37 / security 47 / errors 77 / responses 109 / time_utils 100 / feature_flags 126 = 549 합계
git diff --stat 09f49c1 -- dosu_clinic.spec tests/test_pyinstaller_hidden_imports.py   # spec +10 / test +42 = +52
```

```powershell
# r2 PowerShell 환경 (caveat 3 정합 — bash 미존재 환경 대안)
Get-ChildItem app/core/*.py | ForEach-Object { "$($_.Name): $((Get-Content $_.FullName).Count) lines" }
# (Get-Content).Count 는 PowerShell 환경 의존 — bash wc -l 과 ±1 줄 차이 가능

# 또는 .NET 다중 측정
[System.IO.File]::ReadAllText("app/core/__init__.py").Split("`n").Count - 1   # 12 기대
[System.IO.File]::ReadAllText("app/core/config.py").Split("`n").Count - 1   # 41 기대
[System.IO.File]::ReadAllText("app/core/feature_flags.py").Split("`n").Count - 1   # 126 기대

# import 가능성 검증 (PyInstaller actually_importable 8/8 통과로 간접 확인 — 직접 명령 재현 ⊥)
venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -k "19_X_core" -q   # 16 passed 기대
```

## 16. Codex 검증 결과 기록 위치

- [reports/refactor/19-1_codex_review.md](19-1_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

응답 형식 권장:

```markdown
# 19-1 Codex 검증 결과

## 1. 종합 판정
{pass | pass with caveat | fail}

## 2. 게이트별 결과
- 19-1-G1 ~ G12: {결과 + 근거}

## 3. 추가 발견 / 누락 / 부정확 항목
{있으면 bullet}

## 4. 19-2 진입 권고
{yes / no + 근거}
```

## 17. Claude Code 자체 판단

**yes (19-2 settings / feature_flags / health 경계 정리 진입 권고)**.

근거:
1. 19-1 = 신규 폴더 / 파일만 추가 + spec/test 갱신. 기존 코드 / API URL / 응답 키 / DB schema / migration / UI / requirements 0 변경.
2. 545 passed (18-8 baseline 529 + 19-1 신규 16) — 18-8 회귀 0.
3. 5회 루프 1회차에 통과 — 땜질 ⊥, 추가 수정 ⊥.
4. core 가 modules 를 import 하지 않음 (D-4 정합) + 순환참조 0.
5. compatibility wrapper 3개 + COMPAT 주석 + TODO(19-x) 명시 — 본체 이동 19-x 후속 시점에.
6. 신규 helper 4개 (errors / responses / time_utils / feature_flags) — 19-x 분리 시 점진 채택 가능.
7. 응답 키 33+ 셋 보존 / 운영 DB 미접근 / 외부 API 호출 0 / local-first 보존 / 부재 항목 단정 ⊥ 100% 정합.
8. PyInstaller hidden imports 53 → 69 (+16 신규 19-1 core 검증) 모두 통과.
9. 주석 카테고리 6종 (COMPAT/SAFETY/NOTE/RISK/TODO) 적용.
10. 19-1 진입 게이트 19-1-G1 ~ G12 = 12 pass.

남은 위험 / 후속:
- core wrapper 본체 이동 — 19-x 후속 (19-12 admin/security 분리 시 등)
- core 신규 helper 채택 — 19-x 분리 시 점진 (19-2 settings + feature_flags / 19-4 availability + time_utils / 19-9 appointments + responses 등)

다음 세션:
- **19-2 settings / feature_flags / health 경계 정리** ([docs/refactor/19_refactor_rollout_plan.md §3-2](../../docs/refactor/19_refactor_rollout_plan.md)).
