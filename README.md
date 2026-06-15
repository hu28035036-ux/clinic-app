# 도수치료예약 (Dosu Clinic) — 제품 요구사항 문서 (PRD)

> **문서 성격**: 이 README는 `clinic-app` 소스 저장소의 제품 요구사항 문서(PRD)입니다.
> 제품의 목적·사용자·기능/비기능 요구사항·아키텍처·릴리스 기준을 정의합니다.
>
> | 항목 | 값 |
> |------|-----|
> | 현재 버전 | **v1.3.31** |
> | 빌드일 | **2026-06-16** |
> | 저장소 역할 | **소스 코드 (제품 본체)** |
> | 배포 채널 | [`hu28035036-ux/clinic-updates`](https://github.com/hu28035036-ux/clinic-updates) (별도 저장소) |
> | 기본 관리자 비밀번호 | `admin1234` (첫 운영 시 변경 필수) |

---

## 1. 제품 개요

도수치료 전문 병원 현장에서 사용하는 **Windows 단독 실행형(on-premise) 예약·환자·직원·정산 관리 프로그램**이다.
별도 서버/클라우드 없이 메인 PC에서 로컬 FastAPI 서버를 띄우고, 같은 네트워크의 다른 PC·태블릿은 브라우저로 접속하는 **씬 클라이언트** 구조다.

- **한 줄 정의**: 인터넷이 끊겨도 동작하는, 병원 원무과용 단일 실행형 예약관리 데스크톱 앱.
- **배포 형태**: PyInstaller onedir(`도수치료예약.exe` + `_internal/`) → ZIP → GitHub Release 자산.
- **업데이트**: 프로그램 폴더만 교체, 운영 데이터(`clinic.db`)는 절대 건드리지 않음.

## 2. 해결하는 문제 / 목표

| 문제 | 제품 목표 |
|------|-----------|
| 외부 예약 SaaS는 인터넷 의존·구독료·환자정보 외부 전송 부담 | 인터넷 없이 동작하는 로컬 실행형, 데이터는 병원 PC에만 보관 |
| 도수치료 특유의 치료사 배정·횟수권·인센티브 정산 미지원 | 도수/체외충격파 코드·치료사 배정·신환·노쇼·정산을 1급 기능으로 |
| 원무·간호·치료사가 같은 화면을 동시에 봐야 함 | 메인 PC 1대 + 다중 브라우저 접속 + 변경 즉시 반영(폴링) |
| 데이터 유실·업데이트 사고에 대한 공포 | AppData 분리 보관 + 자동 백업 + 업데이트 직전 스냅샷 + 무중단 자가 업데이트 |

## 3. 대상 사용자 / 운영 환경

- **사용자**: 병원 원무과(예약·수납), 간호과, 도수치료사, 관리자(원장/실장).
- **운영 토폴로지**: 메인 PC 1대만 exe 실행(원무과). 서브 PC·휴대폰은 브라우저로 `메인IP:8000` 접속.
  - sub 모드 P2P 동기화 코드는 존재하나 실배포에서는 미사용(메인 단일 구동이 기본).
- **플랫폼**: Windows 10/11 (x64). 별도 런타임 설치 불필요(PyInstaller 동봉).

## 4. 기능 요구사항 (Functional Requirements)

### F-1. 예약 보드 (예약 탭)
- 일자별 예약 보드: 시간대 × 치료사/의사(공용)/체외충격파 열 그리드.
- 예약 생성·수정·시간 이동(드래그), 승인 / 취소 / 노쇼 처리, 점심시간 차단.
- 반복 예약(N회·미래만·충돌 skip), 치료실(자원) 배정·충돌 검사.
- **미니달력**: 월별 예약 수·휴무자 표시, 날짜 선택 시 보드 기준일 동기화. 내용에 맞춰 높이 자동 확장.
- **금일 예약 환자 / 금일 예약 취소** 목록: 치료사별 그룹화, 신규 환자 등록 직후에도 이름 정상 표시(서버 임베드 폴백).

### F-2. 환자 관리 (환자 탭)
- 대량 환자 검색(이름·차트번호·생년월일·연락처), 차트/전화/생년월일 자동 포맷.
- 환자 누적 메모, 중복 등록 방지, 도수치료 이력·신환 자동 판정.
- 엑셀 가져오기(휴대폰 컬럼 우선 인식).

### F-3. 직원 관리 (직원 탭)
- 직원 과(category)·치료 가능 항목·입사일 관리, 권한 등급(staff/admin/super).
- 휴무 관리: 종일/오전반차/오후반차 + 연차/월차, 직원 1명 다중 날짜 동시 등록(bulk-add, 기존 휴무 보존).

### F-4. 치료 항목 / 기록
- 도수·체외충격파 등 치료 코드, 가격, 인센티브, 과 카테고리 연결, 별칭.
- 기록 탭: 주간 요일별 입력(메뉴얼/C-Arm/리뷰이벤트 등 하위탭), 차트·성함·직원 기록.

### F-5. 통계 / 정산 / 매출
- 치료별·직원별·기간별 통계, 정산 grid/report·스냅샷·XLSX export.
- 매출 일계표(16개 항목 + 항목별 메모), 일일 현금 기입장(권종별 자동 합계), 일일 업무 보고.

### F-6. 재고 관리
- 카테고리별 재고 항목·동적 필드·셀 단위 자동 저장.

### F-7. 문자 발송
- 문자나라 연동 설정·템플릿, 예약 안내/리마인더 대상 조회.

### F-8. 관리자 / AI 보조
- PBKDF2 비밀번호 해시, 로그인 실패 잠금, 감사 로그(5년 보존), 백업/복원.
- AI 예약/휴무 명령 보조(안전 게이트), RAG 기반 매뉴얼 질의 백엔드.

## 5. 비기능 요구사항 (Non-Functional Requirements)

- **데이터 안전**: 운영 데이터는 `%APPDATA%\도수치료예약\`에만 저장. 업데이트는 exe+`_internal`만 교체.
  자동 백업 + 업데이트/복원 직전 스냅샷(분리 보관), SQLite 공식 backup API 사용.
- **동시성/안정성**: SQLite WAL + `busy_timeout`으로 백업·동기화·예약 저장 동시 실행 안정화.
- **다중 PC 정합성**: 변경 로그(SyncOp) 기반 증분 동기화, 자연키 병합, 오래된 삭제가 최신 기록을 덮지 않도록 충돌 처리.
- **무중단 업데이트**: 매니페스트 비교 → ZIP 다운로드(sha256 검증) → `updater.bat` 자가 교체 → 재시작·자동 새로고침, 완료 안내 1회.
- **캐시 무효화**: 정적 자원은 `?v={{ app_version }}`으로 버전 변경 시 자동 갱신(서브 PC 브라우저 캐시 포함).
- **회복력**: `config.json` 원자적 저장·손상 시 `.broken_*` 보존 후 재생성, UTF-8 BOM 허용.

## 6. 시스템 아키텍처

```
[메인 PC]  도수치료예약.exe (PyInstaller onedir)
   └─ uvicorn → FastAPI (app.main:app)  :8000
        ├─ Jinja2 SSR (templates/) + 정적자원 (static/)
        ├─ SQLAlchemy → SQLite (%APPDATA%\도수치료예약\clinic.db)
        └─ 마이그레이션 러너 (app/migrations/m001~m036)
[서브 PC/휴대폰]  브라우저 → http://메인IP:8000  (Alpine.js + FullCalendar + SortableJS)
[업데이트]  GitHub Release(ZIP 자산) ← manifest.json(GitHub Pages, clinic-updates)
```

- **Backend**: Python 3.12 · FastAPI · SQLAlchemy · SQLite · uvicorn
- **Frontend**: Jinja2(SSR) · Alpine.js · FullCalendar 6 · SortableJS (모두 로컬 vendor, 오프라인 동작)
- **Packaging**: PyInstaller onedir · `dosu_clinic.spec`(마이그레이션 자동 discover)
- **주요 파일**: `app/routers/api.py`(API ~3,800줄), `app/templates/main.html`, `app/static/js/main.js`(탭 JS ~9,100줄), `app/static/css/app.css`, `app/config.py`

## 7. 데이터 모델 / 마이그레이션

- `app/migrations/m00X_*.py`가 `schema_migrations` 테이블 기준으로 순차 실행.
- 현재 **m001 ~ m036** (베이스라인·gender·인덱스·치료 수가/인센티브·manual_counts·AI·휴무·의사·반복예약·자원·과 카테고리·정산·재고·매출·기록탭·매출 UI 설정 등).
- `dosu_clinic.spec`가 마이그레이션 모듈을 자동 등록하므로 신규 m0XX 추가 시 hiddenimports 수동 등록 불필요.

## 8. 빌드 / 배포 / 업데이트

> ⚠ **빌드/배포는 사용자 승인 후 진행** (코드·문서 수정은 자유).

1. 테스트 + ruff 통과, (지식 인덱스 변경 시) `tools\build_knowledge_index.py` 재생성.
2. 버전 문서 갱신: `app/config.py`(APP_VERSION/BUILD_DATE), `CHANGELOG.txt`, `VERSION.txt`, `versions/INDEX.txt`.
3. PyInstaller 빌드:
   ```powershell
   venv\Scripts\pyinstaller.exe --noconfirm dosu_clinic.spec
   # → dist\도수치료예약\(도수치료예약.exe + _internal\ + updater.bat)
   ```
4. ZIP 패키징(파일명 ASCII, 내부 최상위 폴더 `도수치료예약`):
   ```powershell
   Compress-Archive -Path dist\도수치료예약 -DestinationPath dist\dosu_clinic_vX_YYYYMMDD.zip
   ```
5. 격리 환경 exe 스모크(`APPDATA`/`DOSU_DB_PATH`를 `tests\temp`로, 별도 포트).
6. 배포 → GitHub Release 자산 업로드 + manifest만 커밋:
   ```powershell
   scripts\publish_release.ps1 -Version X -ZipPath ... -NotesPath ..\clinic-updates\release-vX.md -ManifestNotesPath ...   # 먼저 -DryRun
   ```
7. 검증: Pages 매니페스트(version/sha256) 폴링, Release 자산 다운로드 확인.

## 9. 개발 / 검증

```powershell
# 개발 실행 (기본 격리 DB: tests\temp\dev_clinic.db)
venv\Scripts\python.exe run.py            # http://127.0.0.1:8000/
venv\Scripts\python.exe run.py --prod     # 운영 DB 직접 확인 시에만
venv\Scripts\python.exe run.py --check    # DB 경로·마이그레이션 점검

# 검증 (작업 후 필수)
venv\Scripts\python.exe -m pytest tests --basetemp=tests\temp\pytmp
venv\Scripts\python.exe -m ruff check app tests
venv\Scripts\python.exe scripts\check_db_path.py
node --check app\static\js\main.js
```

- 안정성 하네스: `tests/`(2,241건), `docs/specs/`, `run_check.bat`. 작업 규칙은 `CLAUDE.md` 참조.
- 절대 금지: 운영 DB를 테스트에 사용, DB 컬럼/API 경로 임의 변경, 요청 없는 대규모 리팩토링.

## 10. 현재 릴리스 상태

### v1.3.31 · 2026-06-16
- **관리자 비밀번호 간헐적 "틀렸다" 수정**: 동시 `save_config` 가 고정 임시파일을 공유해 `config.json` 이 깨지고 → 다음 `load_config` 가 기본값(`admin1234`)으로 재생성하던 문제.
  - `save_config`: 호출별 고유 임시파일 + `_CONFIG_WRITE_LOCK` 직렬화(손상 방지), `os.replace` WinError 5 재시도.
  - `load_config`: 손상 시 `_salvage_secrets()` 로 비번 해시·node_id·sync_secret 복구 보존.
- **검증**: 동시저장/손상 비번보존 회귀 3건 추가, 전체 회귀 **2,244 passed**, ruff 통과.

### v1.3.30 · 2026-06-15
- 미니달력 깨짐 수정(`height: auto` + 휴무명 3개 축약), 금일 목록/상세창 "?" 수정(서버 임베드 폴백).

## 라이선스

내부 배포 및 운영용 프로젝트입니다. 무단 재배포와 상업적 재사용을 금지합니다.
