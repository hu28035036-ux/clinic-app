# 도수치료예약 (Dosu Clinic)

도수치료 병원 현장에서 쓰는 Windows 단독 실행형 예약/환자/직원/정산 관리 프로그램입니다.
FastAPI 서버를 로컬에서 띄우고, 브라우저 UI로 SQLite 데이터를 관리합니다.

> 현재 안정화 기준: `v1.3.23`
> 검증일: `2026-06-11`
> 기본 관리자 비밀번호: `admin1234` (첫 배포 후 반드시 변경 권장)

이 저장소는 소스 코드 저장소입니다. 자동 업데이트용 ZIP, 릴리스 파일, 매니페스트는 별도 배포 저장소
`hu28035036-ux/clinic-updates`에서 관리합니다.

## 주요 기능

- 예약 보드: 일자별 예약, 치료사 배정, 시간 이동, 승인/취소/노쇼, 점심시간 차단
- 환자 관리: 대량 환자 검색, 차트번호/전화번호/생년월일 관리, 메모, 중복 등록 방지
- 직원 관리: 직원 카테고리, 치료 가능 항목, 입사일, 반차/휴무 관리
- 치료 항목: 도수/체외충격파 등 치료 코드, 가격, 인센티브, 카테고리 연결
- 통계/정산: 치료별/직원별/기간별 통계, 정산 기록, 매출 기록, 일일 현금 기입장, 일일 업무 보고
- 재고 관리: 항목/필드 추가, 셀 단위 자동 저장, 탭 이동 후 보존
- 문자 발송: 문자나라 설정, 템플릿, 예약 안내/리마인더 대상 조회
- 관리자 보안: PBKDF2 비밀번호 해시, 로그인 실패 잠금, 감사 로그, 백업/복원
- AI 보조 기능: 예약/휴무 명령 보조, RAG 기반 매뉴얼 질의 백엔드 보존

## 데이터 보관 위치

운영 데이터는 실행 파일 폴더가 아니라 사용자 AppData에 저장됩니다.

```text
%APPDATA%\도수치료예약\
  clinic.db
  config.json
  schema_version.txt
  backups\
```

배포 업데이트는 실행 파일과 `_internal` 폴더를 교체하는 방식입니다. 위 AppData 폴더의 `clinic.db`는 업데이트 대상이 아니므로, 정상 업데이트 과정에서 환자/예약/직원 기록이 지워지지 않습니다.

## 개발 실행

```powershell
venv\Scripts\python.exe run.py
```

브라우저 접속:

```text
http://127.0.0.1:8000/
```

개발 모드는 기본적으로 격리 DB를 사용합니다.

```text
tests\temp\dev_clinic.db
tests\temp\dev_appdata\
```

운영 DB를 직접 확인해야 할 때만 아래 명령을 사용합니다.

```powershell
venv\Scripts\python.exe run.py --prod
```

DB 경로와 마이그레이션만 점검하려면:

```powershell
venv\Scripts\python.exe run.py --check
```

## 검증 명령

```powershell
venv\Scripts\python.exe -m pytest
venv\Scripts\python.exe -m ruff check .
venv\Scripts\python.exe run.py --check
node --check app\static\js\ai_helper.js
```

PyInstaller 관련 사전 점검:

```powershell
venv\Scripts\python.exe -m pytest tests\test_pyinstaller_hidden_imports.py tests\test_migration_spec_discovery.py
```

## 배포 빌드

1. 전체 테스트와 ruff를 통과시킵니다.
2. 지식 인덱스가 변경된 경우 인덱스를 다시 만듭니다.

```powershell
venv\Scripts\python.exe tools\build_knowledge_index.py
```

3. PyInstaller onedir 빌드를 실행합니다.

```powershell
venv\Scripts\pyinstaller.exe --noconfirm dosu_clinic.spec
```

4. 결과물을 확인합니다.

```text
dist\도수치료예약\도수치료예약.exe
dist\도수치료예약\_internal\
dist\도수치료예약\updater.bat
```

5. 배포 ZIP을 만들고 SHA256을 계산합니다.
6. GitHub Release에 ZIP을 올립니다.
7. `clinic-updates/manifest.json`의 `version`, `download_url`, `sha256`, `notes`를 갱신합니다.

## 2026-06-11 배포 확인 항목

- 가장 최근 백업 복원이 파일 수정시각 기준으로 진짜 최신 백업을 선택하는지 확인
- 일반 자동백업과 업데이트/복원 직전 스냅샷 보관 개수 정리가 각각 적용되는지 확인
- SQLite WAL/busy_timeout 적용 후 백업/동기화/예약 저장 동시 실행 안정성 확인
- config.json 손상 시 `.broken_*` 보존 후 기본 설정으로 자동 재생성되는지 확인
- 동기화 변경 기록 180일 보존 정리와 증분 push 동작 확인
- 신규 환자 등록 직후 새 예약창 환자 검색 캐시가 즉시 갱신되는지 확인
- 미니캘린더 날짜 선택 표시와 예약표 기준일이 함께 바뀌는지 확인
- 브라우저 폭을 줄여도 예약표 영역이 사라지지 않고 가로 스크롤로 확인 가능한지 확인
- 일일 현금 기입장에서 권종별 수량 입력 시 금액과 총합이 자동 계산되는지 확인
- 매출 기록에서 현금/카드/계좌/미수납/기타/메모 저장과 음수 금액 입력이 가능한지 확인
- 일일보고 업무일지 반영 영역에 매출 기록과 정산 기준 값이 연결되어 표시되는지 확인
- 기간별 데이터 엑셀 업로드 후 일일보고에 날짜별 총진료비/공단부담총액/본인부담총액/급여총액/비급여총액이 표시되는지 확인
- 매출 기록의 미수납 입력값이 합계/통계/업무일지에서 차감 금액으로 반영되는지 확인
- 카카오톡 일별 수입현황 예시 엑셀의 추가 컬럼/합계 행이 있어도 날짜별 기간 데이터만 반영되는지 확인

## 2026-06-08 안정화 확인 항목

- 매니페스트 자동업데이트 후 새 버전 첫 실행 시 업데이트 완료 안내가 1회만 표시되는지 확인
- 업데이트 진행 화면이 안내 화면으로 전환되고 서버 재시작 후 자동 새로고침되는 흐름 확인
- `/api/about`의 `update_completed` 응답과 `update_last_seen_version` 저장값으로 중복 안내가 방지되는지 회귀 테스트
- 초기 설정 화면에서 로컬 최초 모드 저장이 관리자 로그인 없이 정상 반영됨
- 설정 파일에 UTF-8 BOM이 포함되어도 로그인/설정 로딩이 실패하지 않음
- 관리자 기본 비밀번호 `admin1234` 로그인 정상 확인
- 환자 등록 후 탭 이동/새로고침에도 기록 보존 확인
- 직원 카테고리와 직원 등록 후 탭 이동/새로고침에도 기록 보존 확인
- 첫 직원 카테고리 생성 직후에도 예약 모달의 치료 항목이 비지 않도록 fallback 적용
- 예약 생성 후 보드/오늘 목록 표시와 새로고침 보존 확인
- 재고 필드/항목/수량 입력 후 탭 이동 자동 저장 및 새로고침 보존 확인
- 다중 PC 동기화에서 서브 PC의 최신 입력 때문에 메인 PC의 이전 변경이 누락되지 않도록 검증
- 동기화 중 오래된 삭제 요청이 더 최신 로컬 기록을 지우지 않도록 검증
- 동기화 push 일부 실패 시 정상 op는 커밋되고 실패 op만 따로 보고되도록 검증
- 의사/자원 변경 로그가 peer PC에 적용 가능한 동기화 엔티티 목록에 포함되는지 검증

## 문제 해결

`ModuleNotFoundError: No module named 'uvicorn'`이 나오면 시스템 Python으로 실행한 것입니다.

```powershell
venv\Scripts\python.exe run.py
```

관리자 로그인이 500으로 실패하고 `config.json` 인코딩 문제가 의심되면 최신 빌드에서는 `utf-8-sig`로 읽어 BOM을 허용합니다. 이전 빌드에서는 `config.json`을 UTF-8 without BOM으로 저장해야 합니다.

배포본 실행 후 화면이 예전처럼 보이면 브라우저 캐시를 새로고침합니다.

```text
Ctrl + Shift + R
```

## 기술 스택

- Backend: Python 3.12, FastAPI, SQLAlchemy, SQLite, uvicorn
- Frontend: Jinja2, Alpine.js, FullCalendar, SortableJS
- Packaging: PyInstaller onedir
- Update channel: GitHub Releases + GitHub Pages manifest

## 라이선스

내부 배포 및 운영용 프로젝트입니다. 무단 재배포와 상업적 재사용을 금지합니다.
