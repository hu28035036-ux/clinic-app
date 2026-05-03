# 19-0 baseline 재고정 — 변경 요약

> 19-0 = read-only 검증 세션 — 코드 / 테스트 / migration / spec / UI / requirements 무수정.
> 본 세션 = 환경 진단 + baseline 재확인 + caveat 해소 검증.

## 0. 메타

- 세션 이름: **19-0 baseline 재고정**
- 검증일: 2026-05-03
- 기준 커밋: `bcd74a7` (release v1.3.3)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed** — 100% 일치
- 직전 세션: 19-P-10 r1 Codex `pass with caveat (yes — 19-0 진입 가능)` ([reports/refactor/19-P-10_codex_review.md](../refactor/19-P-10_codex_review.md))

## 1. 변경 파일 목록

### 신규 (2)

- `reports/ai_dev_loop/19-0_test_report.md` (영구 보존본 — 테스트 리포트)
- `reports/ai_dev_loop/latest_test_report.md` (덮어쓰기 — 진입점)

### 신규 (Codex 검증 요청서 — §3 작성 예정)

- `reports/refactor/19-0_codex_review_request.md` (영구 보존본)
- `reports/refactor/latest_codex_review_request.md` (덮어쓰기 — 19-P-10 진입점에서 19-0 으로)
- `reports/ai_dev_loop/19-0_fix_summary.md` (본 문서, 영구)
- `reports/ai_dev_loop/latest_fix_summary.md` (덮어쓰기)

### 무수정 (회귀 보호)

`app/**`, `tests/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`, `CLAUDE.md`, `app/services/**`, 19-P-1 ~ 19-P-10 산출물.

> `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` = 18-0~18-8 변경분 **5 tracked** (`app/models/models.py`, `app/routers/ai.py`, `app/services/ai/manual_qa.py`, `dosu_clinic.spec`, `tests/conftest.py`) + 본 19-0 추가 0.
>
> **r2 보정 (19-0 caveat 3 — 5 vs 6 tracked 기준 차이)**: `git status --short` 기준 modified tracked 는 **6 개** (`.gitignore` 포함). 본 diff stat 명령 범위 (`app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml`) 는 `.gitignore` 를 *제외* 하므로 **5 tracked** 로 표시. 두 기준은 *서로 다른 명령의 결과* 이며 실제 변경 파일은 일관 (`.gitignore` 는 명령 범위 밖이라 본 G-1 에 포함되지 않음). 19-P-1 ~ 19-P-10 모두 동일 범위 사용.

## 2. 본 세션 의도 / 이유

### 의도

19-x 실제 코드 리팩토링 세션 (19-1 core 분리 ~ 19-14 종료 게이트) 진입 직전 **baseline 재고정**.

### 이유

1. **19-P-10 §5-1 사용자 결정 항목 답변 준비** — 본 19-0 baseline 검증 결과 = 사용자 결정의 근거.
2. **19-P-10 §5-2 환경 복구 4 항목 검증** — `.venv` Python 런처 / pytest / ruff / check_db_path 모두 정상 동작 확인.
3. **19-P-8 caveat 3 / 19-P-9 caveat 2 / 19-P-10 caveat 4 해소** — PyInstaller "53 tests" 산출 공식 (15 + 19×2 = 53) 실제 collection / 실행 검증.
4. **18-8 baseline (529/1/7) 회귀 0 확인** — 19-1 진입 시 회귀 비교 기준 확보.

## 3. 검증 결과 요약

| 검증 항목 | 결과 |
|---|---|
| `.venv` Python 3.12.10 / pytest 8.4.2 / ruff 0.15.12 정상 동작 | ✓ pass |
| `check_db_path.py` exit 0 | ✓ pass |
| `ruff check app tests scripts` All checks passed! | ✓ pass |
| `pytest tests -q` 529 passed, 1 skipped, 7 xfailed (12.45초) | ✓ pass — 18-8 baseline 100% 일치 |
| `pytest tests/test_pyinstaller_hidden_imports.py --collect-only` 53 tests | ✓ pass — 산출 공식 정확 |
| `pytest tests/test_pyinstaller_hidden_imports.py` 53 passed (0.36초) | ✓ pass |
| baseline 측정값 (api.py 5127 / 86 endpoint / ai.py 929 / 13 / main.html 7331 / app.css 3626 / tests 40 / ORM 19 / m001~m013 13 / PyInstaller 53) | ✓ 19-P-10 §4-1 100% 일치 |
| 부재 항목 grep (Doctor / doctor_id / no_show 등) 0건 | ✓ 단정 ⊥ 정책 정합 |
| 운영 DB 보호 S-1 ~ S-5 | ✓ 자동 통과 |
| 외부 API 차단 (`_block_sdk_modules`) | ✓ 자동 활성 |

## 4. 19-P 시리즈 caveat 본 19-0 시점 해소 현황

### 4-1. 본 19-0 시점에 해소 (6건)

- 19-P-8 caveat 3 / 19-P-9 caveat 2 / 19-P-10 caveat 4 — PyInstaller 53 tests collection 미실행 → **53 collected + 53 passed** ✓
- 19-P-10 §5-2 환경 복구 1 ~ 4번 — `.venv` Python / pytest / ruff / check_db_path → 모두 정상 ✓

### 4-2. 본 19-0 시점에 보정 가능 (5건 — 사용자 결정 후)

[reports/ai_dev_loop/19-0_test_report.md §9-2](19-0_test_report.md) 표 정합. 모두 read-only 문서 보정 — 코드 영향 0.

### 4-3. 사용자 결정 필요 (3건)

[reports/ai_dev_loop/19-0_test_report.md §9-3](19-0_test_report.md) 표 정합.

## 5. 5회 루프 카운트

- 본 19-0 = read-only 검증 — **루프 0회** (수정 ⊥).
- baseline 일치 100% — 추가 수정 불필요.

## 6. 남은 위험

- 사용자 결정 3건 답변 전까지 19-1 진입 보류.
- caveat 보정 5건 (read-only 문서 — 코드 영향 0) — 사용자 결정 후 본 19-0 안 또는 19-1 직전 진행.
- `docs/ai_rag_current_state.md` stale 보정 — 사용자 결정 (시점 / 범위) 필요.
- 18-0 ~ 18-8 dirty 변경분 처리 — 사용자 결정 (머지 / commit / 유지) 필요.

## 7. 다음 단계

[reports/ai_dev_loop/19-0_test_report.md §11](19-0_test_report.md) 정합:

1. 사용자 결정 3건 답변 대기.
2. 결정 답변 후 옵션 1/2/3 진행:
   - **옵션 1**: caveat 보정 (read-only) → Codex 검증 → 19-1 진입.
   - **옵션 2**: caveat 보정 + dirty 변경분 처리 → Codex 검증 → 19-1 진입.
   - **옵션 3**: 19-1 직진 (비권장 — caveat 누적).
3. 19-1 진입 직전 [19_refactor_checklists.md §1 ~ §2](../../docs/refactor/19_refactor_checklists.md) 적용.
