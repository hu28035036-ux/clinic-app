# 도수치료 예약 — 개발 안정성 하네스

## 1. 하네스의 목적

이 프로젝트는 Windows 단독 실행형 FastAPI 프로그램으로, `%APPDATA%\도수치료예약\clinic.db` 라는 단 하나의 SQLite 파일에 모든 환자·예약·직원 데이터가 들어 있다.
Claude Code 같은 자동화 도구가 코드를 수정할 때 다음을 보장하기 위해 본 하네스가 도입되었다.

1. **실제 운영 DB 보호** — 테스트 코드가 실수로라도 운영 DB 를 건드리지 않게 3중 안전망을 둔다.
2. **핵심 비즈니스 규칙 문서화** — 예약 / 휴무 / 완료 카운트 규칙을 `docs/specs/` 에 명시.
3. **자동 회귀 검증** — pytest 로 핵심 동작이 깨지지 않았는지 검사.
4. **신규 코드 품질 유지** — ruff 로 새로 추가되는 코드의 일관성 보장 (기존 `app/` 코드는 일부러 면제).
5. **단일 검증 명령** — `run_check.bat` 한 방에 위 모두 검사.

이번 하네스는 **기능 추가가 아니라 안전망 추가**다. 기존 화면·API·DB 스키마는 그대로 유지된다.

---

## 2. 실제 운영 DB 보호 방식 (3중 안전망)

운영 DB 경로: `%APPDATA%\도수치료예약\clinic.db` (보통 `C:\Users\<유저>\AppData\Roaming\도수치료예약\clinic.db`)

테스트는 위 경로를 절대 건드리면 안 된다. 다음 3중으로 막는다.

### 1차 — `tests/conftest.py` 의 import-time 코드

`pytest` 가 시작되어 어떤 테스트 파일이든 import 되기 전에 가장 먼저 실행되는 코드.
`os.environ["APPDATA"]` 를 임시 폴더(`tests/temp/appdata_<uuid>/`) 로 강제로 바꾼다.
이 시점에 `app.config.get_db_path()` 가 결정되므로 그 이후 어떤 import 도 임시 DB 경로를 사용한다.

> Phase C 적용 후에는 `DOSU_DB_PATH` 환경변수를 사용 → 임시 DB 파일명이 `test_clinic_<uuid>.db` 가 되어 `clinic.db` 라는 이름조차 사용하지 않게 된다.

### 2차 — `tests/harness/db_guard.py` 의 `assert_safe_db_path()`

conftest 의 import-time 에서 한 번, 그리고 session-scoped autouse fixture 에서 또 한 번 호출.
다음 조건을 검사:
- DB 경로 문자열에 `temp` 또는 `test` 가 포함되어야 한다 — 없으면 `RuntimeError`.
- 경로에 `appdata/roaming/도수치료예약/clinic.db` 패턴이 보이는데 `/tests/` 가 없으면 운영 경로로 간주 — `RuntimeError`.

### 3차 — `scripts/check_db_path.py`

`run_check.bat` 의 마지막 단계에서 별도 프로세스로 실행.
현재 환경에서 결정되는 DB 경로를 출력하고, 위험 패턴 감지 시 경고를 띄운다.
사람이 한 번 더 눈으로 확인하기 위한 정보성 도구.

---

## 3. 테스트용 DB 사용 방식

- 테스트 DB 는 `tests/temp/` 아래에 생성된다 (실행마다 새로운 UUID 폴더).
- pytest 가 `app.main` 을 import 할 때 `init_db()` 가 자동으로 임시 DB 에 마이그레이션 + 시드를 적용한다.
- 추가 테스트 시드 (테스트 직원 3명, 환자 3명, 휴무 3건 등) 는 `tests/harness/seed_data.py` 가 멱등으로 주입한다.
- 모든 테스트 직원·환자 이름에 "테스트" 접미사가 붙어 있어 실수로 운영 DB 에 들어가도 즉시 식별 가능.

---

## 4. 테스트 실행 방법

### 전체 검증 (권장)

```bat
run_check.bat
```

순서: pytest → ruff → DB 경로 안전 검사. 어느 단계에서든 실패 시 즉시 중단하고 원인 출력.

### 개별 실행

```bat
run_tests.bat       :: pytest 만
run_lint.bat        :: ruff 만
```

또는 venv 직접:

```bat
venv\Scripts\python.exe -m pytest tests -v
venv\Scripts\python.exe -m ruff check app tests
venv\Scripts\python.exe scripts\check_db_path.py
```

---

## 5. 실패 시 확인 순서

### pytest 실패

1. 출력 첫 머리에 `[하네스] 테스트 DB 경로:` 라인이 보이는가?
   - 안 보이면 conftest.py 의 import-time 코드가 실행 안 됨 → pytest 호출 위치 확인.
2. `RuntimeError: 테스트 DB 경로에 'temp'/'test' 가 없음` 이 떴다면 → DB 격리 깨짐. `conftest.py` 의 APPDATA 또는 DOSU_DB_PATH 라인 확인.
3. `XFAIL` 은 실패가 아니다 — 백엔드 차단 미구현으로 의도적으로 RED. 이 라인은 무시해도 된다.
4. `XPASS` 가 보이면 → 백엔드에 차단 로직이 추가된 것. 해당 테스트의 `@pytest.mark.xfail` 마커를 제거할 시점.
5. 정방향 테스트가 실패했다면 → 핵심 동작이 깨진 것. spec 문서를 다시 읽고 코드 변경을 되돌릴지 검토.

### ruff 실패

- `tests/` 또는 `scripts/` 의 새 코드에서 발생했을 가능성이 높다 (`app/**` 은 면제).
- E / F / I / B 카테고리만 체크. 자동 수정은 `ruff check tests scripts --fix`.

### DB 경로 안전 검사 실패

- `scripts/check_db_path.py` 가 운영 경로를 위험으로 감지한 경우.
- 운영 환경에서 직접 실행하면 정상적으로 운영 경로를 출력함 — 이건 정상.
- 비정상은 테스트 환경(예: pytest 중)에서 운영 경로가 잡히는 경우.

---

## 6. Claude Code 가 기능 수정 후 반드시 실행해야 하는 명령어

```bat
run_check.bat
```

이 한 줄로 충분하다. 실패 시 출력에 명시된 단계를 보고 원인을 한국어로 설명하고, 깨진 규칙을 어떻게 만족시킬지 제안할 것.

자세한 변경 절차는 [docs/CHANGE_RULES.md](CHANGE_RULES.md) 참조.

---

## 7. 트러블슈팅 — venv 가 깨진 경우

`run_check.bat` / `run_tests.bat` / `run_lint.bat` 를 실행했을 때 다음과 같은 메시지가 보이면 venv 가 깨진 상태다.

```
No Python at "C:\Users\<user>\AppData\Local\Microsoft\WindowsApps\..."
```

또는 본 하네스의 가드가 다음을 출력하는 경우:

```
[X] venv\Scripts\python.exe 가 실행되지 않습니다 (Python 경로 깨짐).
```

원인은 venv 가 예전 Python 인터프리터(예: Microsoft Store Python) 를 바라보고 있는데 그 인터프리터가 현재 시스템에 더 이상 없어서 발생한다. 하네스 자체의 문제가 아니라 venv 만 재생성하면 정상화된다.

### 복구 절차

```bat
:: 1) 기존 venv 제거
rmdir /s /q venv

:: 2) 새 Python 으로 venv 생성 (Python 3.12 권장)
python -m venv venv

:: 3) 운영 의존성 설치 (FastAPI, SQLAlchemy 등)
venv\Scripts\python.exe -m pip install -r requirements.txt

:: 4) 하네스 의존성 설치 (pytest, ruff, httpx)
venv\Scripts\python.exe -m pip install -r requirements-dev.txt

:: 5) 정상화 확인
run_check.bat
```

### 확인 사항

- `python --version` 이 실제 설치된 Python 을 가리키는지: 3.12.x 권장.
- Microsoft Store Python 이 PATH 앞에 있다면 정식 Python 설치 후 시스템 PATH 에서 Microsoft Store stub 의 우선순위를 낮출 것.
- pyinstaller 빌드 (`venv/Scripts/pyinstaller.exe`) 가 필요한 경우 `requirements.txt` 에 이미 포함되어 있어 위 4 단계로 함께 설치됨.

---

## 8. 트러블슈팅 — `'rrorlevel' is not recognized` 같은 cmd 에러

`run_check.bat` 실행 시 다음과 같은 메시지가 보이면:

```
'rrorlevel' is not recognized as an internal or external command, ...
'Scripts\python.exe' is not recognized as an internal or external command, ...
```

배치 파일이 LF-only 줄바꿈으로 저장되어 cmd.exe 가 라벨·변수를 제대로 파싱하지 못하는 상태다.
[.gitattributes](../.gitattributes) 에 `*.bat text eol=crlf` 가 들어 있어 정상적으로 git 으로부터 받았다면 자동으로 CRLF 로 보장되지만, 외부 도구(에디터·Write 도구 등)로 .bat 를 수정한 뒤 LF 로 저장된 경우 이 증상이 난다.

### 진단 (Python)

```bat
venv\Scripts\python.exe -c "from pathlib import Path; d=Path('run_check.bat').read_bytes(); print('LF-only:', d.count(b'\n') - d.count(b'\r\n'), 'CRLF:', d.count(b'\r\n'))"
```

`LF-only: 0` 이고 `CRLF: <양수>` 면 정상.

### 복구

```bat
venv\Scripts\python.exe -c "from pathlib import Path;\
 [Path(f).write_bytes(Path(f).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))\
  for f in ['run_check.bat','run_tests.bat','run_lint.bat']]"
```

또는 git 에서 다시 checkout: `git checkout -- run_check.bat run_tests.bat run_lint.bat`
