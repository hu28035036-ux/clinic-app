# 도수치료 앱 작업 인수인계

작성일: 2026-06-04
작업 위치: `C:\Users\master\Desktop\개발\도수치료\clinic-app`
브랜치: `ai-rag-v1-integration`

## 1. 대화/작업 로그 요약

1. 사용자가 GitHub `hu28035036-ux/clinic-updates` 링크를 제공하고, 업데이트 기록 확인 후 현재 컴퓨터에서 기능 추가/수정할 수 있게 해달라고 요청했다.
2. `clinic-updates`는 배포/업데이트용 저장소이고 실제 소스는 `hu28035036-ux/clinic-app`임을 확인했다.
3. 소스 저장소 `clinic-app`의 `ai-rag-v1-integration` 브랜치를 기준으로 개발 환경을 구성했다.
4. 사용자가 바탕화면에 `개발\도수치료` 폴더를 만들고 거기에 저장해달라고 요청했다.
5. 현재 개발 대상은 `C:\Users\master\Desktop\개발\도수치료\clinic-app`이다.
6. 사용자가 현재 프로그램의 하드코딩 부분을 알려달라고 요청했고, 인증/설정/기본진료항목/SMS/AI/백업/UI/엑셀/배포 스크립트 등 주요 하드코딩을 분류해서 전달했다.
7. 사용자가 그중 “1. 기본진료항목”을 수정/추가/삭제 가능하게 변경하라고 요청했다.
8. 기본진료항목 하드코딩 제거 및 관리자 화면 기반 관리 구조를 보강했다.

## 2. 이번 세션에서 완료한 기능

기본진료항목 관련 하드코딩을 줄이고, 다음 구조로 변경했다.

- 기본 시드 5개 항목을 Python 상수에서 제거하고 JSON 파일로 분리했다.
- 새 DB/초기 설치 시 `app/data/default_treatments.json`을 읽어 기본 진료항목을 등록한다.
- 실행 후 운영 중에는 기존 관리자 화면의 `치료항목` 카드에서 추가/수정/삭제/비활성화를 한다.
- 프론트엔드의 `injection/cartilage/eswt/manual30/manual60` 폴백 배열을 제거하고 `/api/treatment-meta` 응답 기준으로 동작하게 바꿨다.
- 새 치료항목 추가 모달에 `내부 코드` 입력칸을 추가했다.
- 기존 치료항목의 내부 코드는 예약/통계 참조 키라 수정 불가하도록 읽기 전용 표시한다.
- 서버에서 새 치료항목 내부 코드 형식을 검증한다.
- PyInstaller 배포 빌드에 `app/data`가 포함되도록 spec을 수정했다.

## 3. 변경 파일

바탕화면 프로젝트 기준 변경 파일:

- `app/data/default_treatments.json`
  - 기본 진료항목 JSON.
  - 현재 기본값: `injection`, `cartilage`, `eswt`, `manual30`, `manual60`.

- `app/modules/treatments/defaults.py`
  - 기본 진료항목 JSON 로더.
  - 우선순위:
    1. 환경변수 `DOSU_TREATMENT_DEFAULTS_PATH`
    2. `%APPDATA%\도수치료예약\default_treatments.json`
    3. 번들 파일 `app/data/default_treatments.json`
  - 사용자 APPDATA에 기본 JSON이 없으면 번들 파일을 복사한다.

- `app/models/constants.py`
  - 기존 `SEED_TREATMENTS = [...]` 하드코딩 제거.
  - 호환용 `SEED_TREATMENTS`는 JSON 로더 결과를 튜플로 반환.
  - `ESWT_CODE = "eswt"`는 아직 특수 분기 코드로 남아 있다.

- `app/services/seed.py`
  - 기본 치료항목 시드를 `load_default_treatments()` 기준으로 변경.
  - 이미 존재하는 코드는 건너뛰고 누락 항목만 등록.

- `app/routers/api.py`
  - 새 치료항목 생성 시 내부 코드 검증 추가.
  - 형식: 영문으로 시작, 영문/숫자/밑줄만, 최대 40자.
  - 중복 시 기존처럼 suffix를 붙이되 길이 제한을 고려.

- `app/templates/main.html`
  - 프론트 하드코딩 기본 치료항목 폴백 제거.
  - 기존 `TREATMENT_SHORT`, `nameToCode` 하드코딩 제거.
  - `TX_META` 기반 이름/약자/코드 매핑으로 변경.
  - `eswt`, `manual30` 직접 fallback을 줄이고 `TX_META.eswt_code`, `TX_META.manual_treatments` 기준으로 치환.
  - 치료항목 추가 모달에 내부 코드 입력칸 추가.

- `dosu_clinic.spec`
  - `app.modules.treatments.defaults` hidden import 추가.
  - `app/data`를 배포 데이터에 포함.

- `tests/test_19_6_treatments.py`
  - JSON 기본값 로딩 테스트 추가.
  - 잘못된 내부 코드 생성 거부 테스트 추가.

- `tools/build_knowledge_index.py`
  - 이전 작업 중 ruff 정리로 import 포맷이 바뀐 파일. 이번 기능과 직접 관련은 낮다.

## 4. 검증 결과

바탕화면 프로젝트 `C:\Users\master\Desktop\개발\도수치료\clinic-app` 기준:

- `ruff check app\modules\treatments\defaults.py app\models\constants.py app\services\seed.py app\routers\api.py tests\test_19_6_treatments.py`
  - 통과.

- `pytest tests\test_19_6_treatments.py -q`
  - `45 passed`.

- 전체 테스트:
  - 명령: `PYTEST_ADDOPTS=--basetemp=tests/temp/pytest python -m pytest -q`
  - 결과: `2158 passed, 1 skipped, 10 xfailed, 27 warnings`.

참고:

- Windows 기본 pytest 임시 폴더 `C:\Users\master\AppData\Local\Temp\pytest-of-master`에 권한 문제가 있어 전체 테스트는 `--basetemp=tests/temp/pytest`를 지정해서 실행했다.
- 8000 포트는 인수인계 작성 시점에 비어 있었고, 개발 서버는 실행 중이 아니다.

## 5. 현재 Git 상태

커밋되지 않은 변경이 있다.

수정:

- `app/models/constants.py`
- `app/routers/api.py`
- `app/services/seed.py`
- `app/templates/main.html`
- `dosu_clinic.spec`
- `tests/test_19_6_treatments.py`
- `tools/build_knowledge_index.py`

신규:

- `app/data/default_treatments.json`
- `app/modules/treatments/defaults.py`

## 6. 다음 세션에서 바로 할 일

사용자는 하드코딩 제거 목록을 순서대로 처리하려는 흐름이다. 이번에는 `1. 기본진료항목`만 완료했다.

다음 후보:

1. 관리자 초기 비밀번호 `admin1234`
   - `app/services/auth.py`
   - `app/templates/main.html`
   - `run.py`
   - dev/test 스크립트

2. 운영시간/점심시간/슬롯/포트 기본값
   - `app/config.py`
   - `main.html`의 UI fallback

3. 문자나라/SMS URL 및 필드명
   - `app/models/models.py`
   - `app/migrations/m003_add_api_url.py`
   - `app/templates/main.html`
   - `app/routers/api.py`

4. AI provider/model 기본 목록
   - `app/models/models.py`
   - `app/routers/ai.py`
   - `app/templates/main.html`

5. UI 색상/타이머/카카오 URL/엑셀 스타일 등 프론트 하드코딩
   - 주로 `app/templates/main.html`
   - 일부 `app/static/css/app.css`
   - 일부 `app/routers/api.py` 엑셀 export

## 7. 주의사항

- 기존 운영 DB에 이미 들어간 치료항목은 JSON 파일 수정으로 바뀌지 않는다. 관리자 화면에서 수정/삭제/비활성화해야 한다.
- JSON은 새 DB나 누락 항목 시드 기준이다.
- `ESWT_CODE = "eswt"`는 아직 특수 분기 코드로 남아 있다. 체외충격파 공용 열/통계/수동 카운트 로직과 깊게 연결돼 있어서 별도 단계로 분리하는 것이 안전하다.
- `tools/build_knowledge_index.py` 변경은 이전 ruff 정리로 생긴 관련 낮은 변경이다. 커밋 시 포함 여부를 판단해야 한다.

## 8. 실행 방법

개발 서버 실행:

```powershell
cd C:\Users\master\Desktop\개발\도수치료\clinic-app
.\venv\Scripts\python.exe run.py
```

접속:

```text
http://127.0.0.1:8000
```

개발 모드는 자동으로 격리 DB를 사용한다.

- DB: `tests/temp/dev_clinic.db`
- APPDATA: `tests/temp/dev_appdata`
- 관리자 비밀번호: `admin1234`

운영 DB로 실행하려면:

```powershell
.\venv\Scripts\python.exe run.py --prod
```
