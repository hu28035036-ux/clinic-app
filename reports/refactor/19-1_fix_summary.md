# 19-1 core 공통 유틸 정리 — 변경 요약

> 19-1 = **첫 번째 실제 코드 리팩토링 세션**. `app/core/` 신설 + 7개 파일.
> 5회 루프 1회차에 통과 (545 passed) — 18-8 baseline 회귀 0.

## 0. 메타

- 세션 이름: **19-1 core 공통 유틸 / 응답 / 에러 / 시간 유틸 정리**
- 검증일: 2026-05-03
- 시작 HEAD: `09f49c1` (commit 2 — 19-P 준비 + 19-0 baseline)
- 직전 19-0 Codex: pass with caveat — yes 19-1 진입 가능

### 0-1. Revision 이력

| 회차 | 결과 | 변경 |
|---|---|---|
| r1 | pass with caveat (Codex 검증 — caveat 1 line count / caveat 2 수정량 표기 부정확 등 4건) | 초기 작성 |
| r2 | (본 revision) | **r1 Codex caveat 1, 2 보정 (옵션 D 사용자 결정)** — 실측 line count 재측정 + diff stat 정확 반영. 동작 영향 0, 코드 변경 0 (문서 수치만 보정). |

## 1. 변경 파일 목록

### 신규 (8개) — r2 보정: 실측 line count 정합 (bash `wc -l`)

| 파일 | 라인 수 | 종류 | 책임 |
|---|---|---|---|
| `app/core/__init__.py` | **12** | 신규 | core 패키지 facade docstring + D-4 정합 명시 |
| `app/core/config.py` | 41 | **re-export wrapper** | `app.config` 의 11개 공개 API re-export (COMPAT) |
| `app/core/database.py` | **37** | **re-export wrapper** | `app.database` 의 7개 공개 API re-export (COMPAT) |
| `app/core/security.py` | **47** | **re-export wrapper** | `app.services.auth` 의 13개 공개 API re-export (COMPAT) |
| `app/core/errors.py` | **77** | 신규 helper | reason_code 상수 21개 (인증/입력/자원/업무규칙/AI/시스템) |
| `app/core/responses.py` | **109** | 신규 helper | 응답 키 상수 (manual/search 3, ask 9, sources 3, health 9, public 4) + `assert_keys` |
| `app/core/time_utils.py` | **100** | 신규 helper | Asia/Seoul 시간 / 반차 12:00 / 점심창 / ISO 형식 |
| `app/core/feature_flags.py` | **126** | 신규 helper | ai_mode + `AI_RAG_*`/`VECTOR`/`HYBRID` env 통합 진입점 |
| **합계** | **549** | | bash `wc -l` 기준 |

### 수정 (2개) — r2 보정: 실제 diff stat 정합

| 파일 | 변경 | 이유 |
|---|---|---|
| `dosu_clinic.spec` | **+10 lines** | 19-1 core 8 모듈 hidden imports 추가 (PyInstaller 빌드 안전성) |
| `tests/test_pyinstaller_hidden_imports.py` | **+42 lines** | `EXPECTED_19_X_CORE_MODULES` + parametrized 2 tests 추가 (16 신규 검증) |
| **합계** | **+52 lines** | `git diff --stat 09f49c1` 실측 |

### 무수정 (회귀 보호)

`app/config.py`, `app/database.py`, `app/services/auth.py`, `app/routers/*.py`, `app/services/ai/**`, `app/templates/**`, `app/static/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `pyproject.toml`, `app/models/**`, `tests/conftest.py`, `tests/harness/**`, 기존 `tests/test_*.py` (test_pyinstaller_hidden_imports.py 외).

## 2. 본 세션 의도 / 이유

### 의도

19-P-2 §2-1 V2 트리의 `app/core/` 자리를 *최소 범위* 로 신설. 향후 19-x 코드 세션 (19-2 settings / 19-4 availability / ... / 19-13 AI commands) 이 채택할 수 있는 *공통 유틸 facade* 만 마련.

### 이유

1. **사용자 명시 "이동 최소화 + compatibility wrapper 유지"** — 실제 `app/config.py` / `app/database.py` / `app/services/auth.py` 의 *본체* 는 그대로 두고, `app/core/{config,database,security}.py` 는 *re-export wrapper* 만 — 기존 import 경로 0 변경.
2. **신규 helper 4개 (errors / responses / time_utils / feature_flags)** 는 기존 라우터가 *참조하지 않음* — 19-x 분리 시점에 점진적으로 채택. 19-1 에서는 *facade* 만.
3. **PyInstaller 빌드 안전성** — `dosu_clinic.spec` 의 `hiddenimports` 에 19-1 core 8 모듈 추가 + `tests/test_pyinstaller_hidden_imports.py` 에 검증 16 tests 추가 (53 → 69).

## 3. 새로 만든 core 구조

```
app/core/
├── __init__.py          (13 lines, 빈 facade + D-4 정합 docstring)
├── config.py            (re-export from app.config — 11 API)
├── database.py          (re-export from app.database — 7 API)
├── security.py          (re-export from app.services.auth — 13 API)
├── errors.py            (신규 — reason_code 21개 상수)
├── responses.py         (신규 — 응답 키 상수 + assert_keys)
├── time_utils.py        (신규 — Asia/Seoul / 반차 12:00 / 점심창)
└── feature_flags.py     (신규 — ai_mode + env helpers)
```

## 4. 실제 이동한 로직

**0 줄** — 본 19-1 시점에 *실제 본체 이동 0*. 모두 신규 helper 또는 re-export wrapper.

| 파일 | 이동? | 비고 |
|---|---|---|
| `app/config.py` | ✗ | 본체 그대로. `app/core/config.py` 가 re-export. |
| `app/database.py` | ✗ | 본체 그대로. `app/core/database.py` 가 re-export. |
| `app/services/auth.py` | ✗ | 본체 그대로. `app/core/security.py` 가 re-export. |

→ **기존 import 경로 0 변경**. `from app.config import ...`, `from app.database import ...`, `from app.services.auth import ...` 모두 그대로 동작.

## 5. 유지한 compatibility wrapper

| wrapper | 위치 | COMPAT 사유 |
|---|---|---|
| `app/core/config.py` | re-export wrapper | `app.config` 11 공개 API 그대로 — 기존 `from app.config import ...` 호환 |
| `app/core/database.py` | re-export wrapper | `app.database` 7 공개 API + SQLAlchemy engine 즉시 생성 정책 그대로 |
| `app/core/security.py` | re-export wrapper | `app.services.auth` 13 공개 API + PBKDF2 + 5회 잠금 + 세션 토큰 정책 그대로 |

각 wrapper 파일 docstring 에 `COMPAT:` + `TODO(19-x): wrapper 제거 + 본체 이동` 주석 명시.

## 6. 주석 / 문서화 적용

[docs/refactor/19_refactor_checklists.md §4](../../docs/refactor/19_refactor_checklists.md) 정합:

| 카테고리 | 적용 위치 |
|---|---|
| **파일 상단 docstring** | 8개 파일 모두 (1줄~다줄 docstring + 모듈 책임 + 의존 모듈 명시) |
| `# COMPAT:` (호환 wrapper) | core/config.py, core/database.py, core/security.py, core/feature_flags.py |
| `# SAFETY:` (운영 DB / 외부 API / API key / PII) | core/config.py (DOSU_DB_PATH 우선 / 운영 DB 미접근), core/database.py (DOSU_DB_PATH 우선), core/security.py (PBKDF2 / 비번 비노출), core/feature_flags.py (local_only 외부 호출 0) |
| `# NOTE:` (업무 규칙 / 정책) | core/__init__.py (D-4 단방향), core/errors.py (응답 dict 키 보존), core/responses.py (33+ 키 셋), core/time_utils.py (12:00 정확 / Asia/Seoul / 점심창), core/feature_flags.py (env vs DB / 환경변수 우선) |
| `# RISK:` (동시성 / 의존) | core/database.py (engine 즉시 생성), core/responses.py (main.html 의존 키), core/time_utils.py (naive vs aware datetime), core/feature_flags.py (ai_mode 도출 오류 시 외부 호출) |
| `# TODO(19-x):` | core/__init__.py, core/config.py, core/database.py, core/security.py (모두 wrapper 제거 + 본체 이동 TODO) |
| 의미 없는 모든 줄 주석 | ⊥ (파일별 docstring + section 헤더 만) |

## 7. 코드 동작 변경 0

| 검증 | 결과 |
|---|---|
| 기존 API URL | 변경 0 |
| 기존 응답 dict 키 (33+ 키 셋) | 변경 0 |
| DB schema (m001~m013) | 변경 0 |
| 마이그레이션 신규 | ⊥ (m014+ 미도입) |
| UI (main.html / app.css / vendor JS) | 변경 0 |
| 기존 SMS AI / 휴무 AI 동작 | 변경 0 |
| local_only / local_first / ai_assist 모드 | 변경 0 |
| 운영 DB 접근 | 0건 |
| 실제 외부 API 호출 | 0건 |

## 8. 5회 루프 카운트

- **1회차**: 모든 검증 통과 (ruff / check_db_path / core import / PyInstaller 69 / 전체 pytest 545 passed) ✓
- 2~5회차: 불필요 (1회차 통과)

→ **5회 루프 1회차에 통과** (땜질 ⊥, `xfail`/`skip` 으로 덮기 ⊥, per-file-ignores 풀기 ⊥).

## 9. 남은 위험

| # | 위험 | 후속 시점 |
|---|---|---|
| 1 | core/config.py / database.py / security.py wrapper 가 무한 보유 (TODO(19-x) 미해소) | 본체 이동은 19-x 후속 (예: 19-12 admin/security 분리 시) |
| 2 | core/errors.py / responses.py / time_utils.py / feature_flags.py 의 신규 helper 가 *기존 라우터에 채택되지 않음* — 19-x 분리 시점에 점진 채택 | 19-2 (settings + feature_flags) / 19-4 (availability + time_utils) / 19-9 (appointments + responses) 등 |
| 3 | core 가 modules 를 import 하지 않는다는 D-4 정합은 본 19-1 까지 안전 — 그러나 19-x 분리 시 modules 가 core 를 import 하면 사이클 발생 가능 | 매 19-x 세션 §3-3 / §3-4 체크리스트 |
| 4 | PyInstaller hidden imports 19-1 core 8 모듈 등록은 spec hiddenimports 에만 — `EXPECTED_19_X_CORE_MODULES` 와 spec 둘 중 하나가 누락되면 fail | 19-x 분리마다 spec + EXPECTED 동기화 |

## 10. 다음 세션

[docs/refactor/19_refactor_rollout_plan.md §3-2](../../docs/refactor/19_refactor_rollout_plan.md) — **19-2 settings / feature_flags / health 경계 정리**:
- `modules/settings/` 신규 (SystemSetting + SmsSetting + AiSetting 통합 read/write)
- `core/feature_flags.py` 채택 (본 19-1 신규 helper)
- `/api/health` 신설은 post-19-P 후속 (M-28)
- 기존 `/api/system-settings` / `/api/config/*` URL 그대로
