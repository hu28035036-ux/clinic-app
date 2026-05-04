# 20-2 Codex 검증 결과

검증 시각: 2026-05-04, `latest_codex_review_request.md` 최신본 기준.

## 판정

**통과.** `20-2_group_b`는 F-13 `/api/health`, F-12 `modules/notes/service`, F-14 calendar 회귀 확인 범위를 실제 파일과 테스트로 검증했으며, 요청 문서의 핵심 기능/회귀/테스트 주장은 일치한다.

다음 세션 진입 가능으로 판단한다.

## 직접 검증한 근거

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/20-2_codex_review_request.md`가 동일함을 확인했다.
- Claude Code 요약 대신 실제 `git status`, `git diff --stat/numstat`, 파일 줄 수, 핵심 구현 패턴, 금지 범위 diff, pytest/ruff/check_db_path 결과를 직접 확인했다.
- pytest는 venv launcher 한글 경로 문제를 피하기 위해 Codex 번들 Python + venv site-packages `PYTHONPATH` 방식으로 실행했다.

## 요청 문서와 실제 파일 비교

| 파일 | 요청 문서 주장 | 실제 확인 |
|---|---:|---:|
| `app/modules/health/service.py` | 110 | 110 |
| `app/modules/health/router.py` | 23 | 18 |
| `app/modules/notes/service.py` | 117 | 112 |
| `tests/test_20_2_group_b.py` | 244 | 248 |
| `app/modules/health/__init__.py` | 수정 | 81 |
| `app/modules/notes/__init__.py` | 수정 | 35 |

줄 수 표기는 일부 불일치하지만 파일은 모두 존재하고 테스트가 통과한다.

tracked diff:

| 파일 | 실제 diff |
|---|---:|
| `app/main.py` | +6 / -2 |
| `app/modules/health/__init__.py` | +17 / -10 |
| `app/modules/notes/__init__.py` | +6 / -2 |
| `dosu_clinic.spec` | +7 |
| `tests/test_pyinstaller_hidden_imports.py` | +4 |

신규 `health/router.py`, `health/service.py`, `notes/service.py`, `tests/test_20_2_group_b.py`는 untracked 신규 파일이라 tracked diff stat에는 포함되지 않는다.

## 구현 검증

- `/api/health` router가 `APIRouter(prefix="/api")`와 `@router.get("/health")`로 추가됐다.
- `app/main.py`에서 `health_router`를 include하고 `set_startup_time()`을 호출한다.
- `collect_health_snapshot()`는 요청서의 6키 `db_ok`, `migration_version`, `backup_age`, `disk_free`, `version`, `uptime`을 반환한다.
- `HEALTH_SNAPSHOT_KEYS`가 6키를 명시한다.
- `notes/service.py`는 `get/update_patient_memo`, `get/update_appointment_memo`, `apply_cancel_memo_prefix`, `get_memo_by_kind`를 제공한다.
- `apply_cancel_memo_prefix`는 기존 `notes.rules.append_cancel_memo`를 사용한다.
- `dosu_clinic.spec`와 hidden import 테스트에 `app.modules.health.service`, `app.modules.health.router`, `app.modules.notes.service`가 등록됐다.
- 금지 범위 확인: `app/templates/main.html`, `app/modules/calendar/view_models.py`, 기존 routers/models/migrations/requirements에는 diff가 없다.

## 테스트 재실행 결과

| 검증 | 결과 |
|---|---|
| `pytest tests/test_20_2_group_b.py -q` | 24 passed |
| `pytest tests/test_pyinstaller_hidden_imports.py -q` | 211 passed |
| `pytest tests -q` | 1726 passed, 1 skipped, 10 xfailed, 27 warnings |
| `.\venv\Scripts\ruff.exe check app tests scripts` | All checks passed |
| `scripts/check_db_path.py` | exit 0 |

warnings는 기존 AI/SMS/manual QA 계열 `PytestReturnNotNoneWarning`이며, 20-2 실패로 보이지 않는다. targeted pytest에서는 `.pytest_cache` 접근 권한 warning이 발생했다.

## Caveat

- 요청 문서의 일부 줄 수가 실제 파일 줄 수와 맞지 않는다. 기능/테스트 판정에는 영향이 없지만 문서 동기화가 필요하다.
- `/api/health`는 public endpoint로 추가됐다. 요청서상 의도와 일치하지만 운영 노출 범위/외부 모니터링 연결은 후속 결정이 필요하다.
- PyInstaller hidden import 테스트는 통과했지만, 실제 PyInstaller 빌드와 exe smoke는 이번 직접 검증에서 수행하지 않았다.

## 종합

20-2 그룹 B는 schema 변경 없이 `/api/health` 신규 endpoint, notes helper, calendar view-model 회귀 확인을 추가했다. 기존 UI와 기존 calendar view-model은 변경하지 않았고, 기존 API 응답 key도 삭제/rename 없이 보존된다.

결론: **20-2 통과, 다음 세션 진입 가능**.
