# 19-8 Codex 검증 결과

## 판정

**통과.** `latest_codex_review_request.md`가 가리키는 19-8 therapists / doctors boundary 변경은 실제 파일 구조, tracked diff, hidden import 등록, 테스트 재실행 결과 기준으로 요청 내용과 일치한다. 19-9 appointments service / repository 분리로 진입 가능하다고 판단한다.

단, `docs/ai/`는 현재 untracked 상태의 별도 기획 문서 묶음으로 남아 있다. 19-8 기능 diff에는 포함되지 않지만, 커밋 범위에 넣을지 별도로 결정해야 한다.

## 직접 검증한 기준

- `reports/refactor/latest_codex_review_request.md`와 `reports/refactor/19-8_codex_review_request.md`가 동일함을 확인했다.
- `reports/refactor/latest_test_report.md`와 `reports/refactor/19-8_test_report.md`가 동일함을 확인했다.
- Claude Code 요약 대신 실제 `git status`, `git diff --stat`, `git diff --numstat`, 파일 목록, import 경계, PyInstaller hidden import, pytest/ruff/check_db_path 실행 결과를 직접 확인했다.

## 실제 파일 구조

파일 줄 수는 `[System.IO.File]::ReadAllLines(...).Count` 기준이다.

| 파일 | 실제 줄 수 | 요청 문서 주장 |
|---|---:|---:|
| `app/modules/therapists/__init__.py` | 41 | 41 |
| `app/modules/therapists/rules.py` | 211 | 211 |
| `app/modules/therapists/repository.py` | 173 | 173 |
| `app/modules/therapists/service.py` | 168 | 168 |
| `tests/test_19_8_therapists.py` | 619 | 619 |

요청 문서의 신규 파일 목록과 실제 파일 구조가 일치한다.

## 실제 diff

tracked diff 기준:

| 파일 | 실제 diff |
|---|---:|
| `dosu_clinic.spec` | +7 |
| `tests/test_pyinstaller_hidden_imports.py` | +5 |

`git diff --stat -- dosu_clinic.spec tests/test_pyinstaller_hidden_imports.py app/modules/therapists tests/test_19_8_therapists.py docs/ai` 결과도 위 두 파일만 tracked 변경으로 잡혔다. 신규 `app/modules/therapists/`와 `tests/test_19_8_therapists.py`는 현재 untracked 파일이다.

## 의존성 경계

- `rules.py`는 `app.routers`, `sqlalchemy`, `app.database`, `app.models.models`를 직접 import하지 않는다.
- `rules.py`의 `app.models.constants` top-level import는 순수 상수 re-export 목적이며 ORM 모델 의존성과는 다르다.
- `repository.py`는 `app.models.models`를 함수 내부 lazy import로 사용한다.
- `service.py`는 `app.modules.therapists.rules`만 가져오며 router/FastAPI 의존성이 없다.
- `app/modules/doctors`와 `app/modules/medical_staff` 디렉터리는 생성되지 않았다.
- `/api/doctors`, `/api/medical-staff` 전용 라우터 추가 흔적은 확인되지 않았다.

## PyInstaller hidden import

`dosu_clinic.spec`와 `tests/test_pyinstaller_hidden_imports.py` 모두 아래 4개 모듈을 포함한다.

- `app.modules.therapists`
- `app.modules.therapists.rules`
- `app.modules.therapists.repository`
- `app.modules.therapists.service`

## 테스트 재실행 결과

| 명령 | 결과 |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_19_8_therapists.py -q` | 78 passed |
| `.\venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | 123 passed |
| `.\venv\Scripts\python.exe -m pytest tests/test_19_5_leaves.py tests/test_19_6_treatments.py tests/test_19_7_patients_notes.py tests/test_19_8_therapists.py tests/test_pyinstaller_hidden_imports.py -q` | 378 passed |
| `.\venv\Scripts\python.exe -m pytest tests -k "ai_sms or ai_leave or rag or safety or contract" -q` | 120 passed, 912 deselected, 21 warnings |
| `.\venv\Scripts\python.exe -m pytest tests -q` | 1024 passed, 1 skipped, 7 xfailed, 27 warnings |
| `.\venv\Scripts\python.exe -m ruff check app tests scripts` | All checks passed |
| `.\venv\Scripts\python.exe scripts/check_db_path.py` | exit 0 |

warnings는 기존 AI/SMS/manual QA 테스트에서 test 함수가 tuple을 return하는 `PytestReturnNotNoneWarning` 계열이며, 이번 19-8 변경 실패로 보이지 않는다.

## 범위 밖 / 잔여 확인

- `docs/ai/`는 untracked 상태이며 19-8 therapists 기능 diff 범위 밖의 별도 계획 문서로 보인다.
- `app/modules/therapists/__pycache__/`는 pytest 실행 중 생성될 수 있으나 `.gitignore`의 `__pycache__/` 패턴으로 무시된다.
- `git status`에서 사용자 홈 `.config/git/ignore`와 일부 `.test-tmp*` 디렉터리 permission warning이 나오지만, 검증 대상 변경과 테스트 결과에는 영향을 주지 않았다.

## 종합

19-8은 치료사/직원 역할 판정, 조회 후보, serializer, name/color map, resource view helper를 `app.modules.therapists` 경계 안에 새로 정리했고, 기존 router/API/schema/migration 본체는 건드리지 않은 것으로 확인된다. doctors / medical_staff 전용 모듈과 전용 엔드포인트가 새로 생기지 않은 것도 테스트와 파일 구조로 확인했다.

따라서 **19-9 진입 가능**으로 결론낸다. 커밋 전에는 `docs/ai/`를 포함할지 제외할지만 별도 결정하면 된다.
