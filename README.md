# 🏥 도수치료예약 (Dosu Clinic)

> 도수치료 전문 병원을 위한 **환자·예약·직원·통계** 통합 관리 시스템
> Windows 단독 실행형 · 로컬 SQLite · 멀티-PC 동기화 지원
> **현재 버전: v1.3.5** (2026-05-05)

이 저장소는 **소스 코드** 저장소입니다. 배포본(ZIP)과 자동 업데이트 매니페스트는 별도 리포(`hu28035036-ux/clinic-updates`)에 있습니다.

---

## ✨ v1.3.5 주요 변경 (2026-05-05)

- 🎨 **전체 UI/UX 모더화** (CompteExpress CRM 톤, Phase A~M) — 디자인 토큰 / 폰트 / 헤더·탭 카드형 / 가독성 보강 / 헤더 흰글씨 충돌 fix
- 🛡️ **AI 안전 게이트 강화** — `approve` endpoint stored-state 게이트 (executed/rejected/failed → 409), create_leave Gate 1
- 🤖 **AI 인증 정책 변경** — 일반 사용자도 AI 예약/휴무 도우미 사용 가능 (anonymous), 관리자 로그만 엄격
- 🗑️ **AI 도우미 탭 (RAG Q&A) UI 제거** — 백엔드 보존
- 🍱 **예약표 엑셀 점심시간 반영** — 옵션 ② (보고서 가독성 우선, 점심 슬롯 = 점심 라벨 우선)
- 💻 **dev 서버 통합** — `venv\Scripts\python.exe run.py` 한 줄로 자동 더미 시드 + 격리 DB
- 🔔 **비밀번호 변경 권장 알림 fix** — 탭 변경 시마다 ❌ → 관리자 로그인 시점 1회만
- 🤝 **Codex 외부 검증 워크플로우** — `codex.cmd exec --sandbox read-only --ephemeral` + Claude 독립 재검토
- 🧹 **프로젝트 정리** — 580 MB 회수 (broken venv / build / dist / 과거 버전 / .claude worktrees / Drive sync)
- 🛠️ **회귀 / 안정성** — 단위 + 통합 2156 passed / ruff clean / DB 안전검사 강화

상세는 `CHANGELOG.txt` / `docs/ui/UI_DESIGN_TOKENS.md` / `docs/codex_reviews/` 참조.

---

## 📋 주요 기능

### 예약 관리
- 일자별 **치료사 × 시간대** 보드 (드래그로 시간·담당자 변경)
- 체외충격파·주사·연골주사 공용 예약 · 도수치료 개인 담당 예약
- 원무과 승인(완료 처리) + 낙관적 락(다중 PC 동시 수정 안전)
- 운영 시간(08:30 ~ 18:30) 종료 시각 라인 포함 (v1.2.6+)
- **점심시간 시스템 설정** (v1.2.17+) — 관리자 탭에서 시작/종료 지정 시
  그 시간대 셀이 가로 병합되고 신규 예약·드래그 이동 차단
- **도수치료 예약현황 엑셀 다운로드** (v1.2.17+) — 보드 헤더에서
  현재 날짜 도수치료 예약을 A4 가로 1페이지 .xlsx 로 인쇄용 출력

### 집계 & 통계 (v1.2.9+ 기간 조회)
- 시작일~종료일 지정 · 프리셋 5종 (오늘/최근7일/이번달/지난달/최근30일)
- 치료사별 도수 시간항목 집계 + **인센티브 자동 계산**
- 체외충격파 **수동 입력** (집계 탭 더블클릭, v1.2.7+)
- 매출 중심 분석 (치료항목별·치료사별)
- **통계 엑셀 다운로드** (v1.2.18+) — 조회 기간 보고서를 A4 가로 .xlsx 로
  출력 (요약/일별통계/치료사별집계 3 시트, 화면 매출과 동일한 산식)

### 환자 관리
- 8만 명+ 대용량 대응 (서버 검색 + 페이지네이션)
- 엑셀 **데이터변환** (성별·주민번호·차트번호 자동 인식)
- 치료항목별 처방/완료 횟수 자동 카운트
- **신규 환자 중복 등록 차단** (v1.2.17+) — 차트번호 중복 또는
  이름+생년월일 중복 시 등록 차단 (이름만 같음 = 동명이인 허용)

### 문자 발송 (문자나라)
- 한글 인코딩 자동 (v1.2.4+: POST + charset 자동 감지)
- 예약 안내/리마인더 템플릿 · 변수 치환

### 시스템
- 관리자 비밀번호 보호 (PBKDF2-SHA256 200,000회 + 16바이트 salt)
- 감사 로그 (모든 보호 작업 기록)
- 5회 실패 시 5분 잠금 · 8시간 세션
- 자동 백업 + 복원 도구

---

## 🔄 자동 업데이트 파이프라인

**v1.2.4+** 부터 3클릭 업데이트 지원:
1. `config.json` 의 `update_manifest_url` 로 GitHub Pages 매니페스트 조회
2. 새 버전이면 ZIP 자동 다운로드 + SHA256 검증
3. `updater.bat` (detached) 가 exe/_internal 교체 + 재시작

**안전장치:**
- 설치 직전 **DB 자동 스냅샷** (`clinic_before_update_v*.db`)
- SHA256 검증 실패 시 중단
- 업데이트 실패 시 자동 롤백 (`_internal.old` / `.exe.old` 복원)

배포 리포: https://github.com/hu28035036-ux/clinic-updates

---

## 📂 데이터 저장 위치 (프로그램 폴더와 분리)

```
%APPDATA%\도수치료예약\
├── clinic.db               환자·예약·직원·치료항목 DB
├── config.json             관리자 설정 · 매니페스트 URL
├── schema_version.txt      마이그레이션 버전 기록
└── backups\                자동 백업 · 업데이트 직전 스냅샷
```

프로그램 폴더(exe + _internal)만 업데이트되고 **데이터는 절대 영향받지 않습니다**.

---

## 🗄️ 마이그레이션 시스템

`app/migrations/` 하에서 순차 실행 (`schema_migrations` 테이블로 추적):

| # | 설명 |
|---|------|
| 001 | 베이스라인 (v1.0~v1.2.1 호환) |
| 002 | `patients.gender` 추가 |
| 003 | `sms_settings.api_url` 추가 |
| 004 | 대량 데이터 대응 인덱스 |
| 005 | 치료항목 수가/인센티브 (price, incentive_pct, incentive_amount) |
| 006 | 집계 수동 카운트 테이블 (`manual_counts` — 체외충격파 당일 환자 등) |

`_reset_database()` 자동 호출 제거됨 (v1.2.2+) → **버전 업데이트해도 환자 데이터 손실 없음**.

---

## 🛠️ 개발 / 빌드

### 개발 환경
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### dev 서버 실행 (한 명령)
```powershell
venv\Scripts\python.exe run.py            # 개발 모드 자동 — 격리 DB + 더미 자동 시드
venv\Scripts\python.exe run.py --prod     # 운영 DB 사용 (개발 PC 에서 실제 데이터 작업할 때만)
venv\Scripts\python.exe run.py --check    # DB 점검만 (서버 안 띄움)
```

- **소스에서 실행**: 자동 개발 모드 — 격리 DB (`tests\temp\dev_clinic.db`) + 더미 (환자 50 / 치료사 8 / 의사 2 / 치료항목 alias)
- **PyInstaller 빌드본**: 자동 운영 모드 — `%APPDATA%\도수치료예약\clinic.db` (실제 운영 DB)
- 시드는 **1회 멱등** — 격리 DB 가 비어있을 때만 시드, 두 번째부터 재사용
- 격리 DB 초기화: `tests\temp\dev_clinic.db` 와 `tests\temp\dev_appdata\` 삭제 후 다음 실행 시 자동 재시드
- 관리자 비번: `admin1234`
- 브라우저: http://127.0.0.1:8000/

> ⚠ `python run.py` (시스템 Python) 호출 시 `ModuleNotFoundError: No module named 'uvicorn'`
> → 의존성은 `venv` 안에만 설치되어 있음. 반드시 `venv\Scripts\python.exe run.py` 사용.
> 또는 PowerShell 에서 venv 활성화: `.\venv\Scripts\Activate.ps1` 후 `python run.py`.

### 보조 진입점 (선택)
```powershell
.\dev_run.bat              # run.py 와 같지만 .bat 호출 (cmd 호환)
.\dev_run.ps1              # PowerShell 진입점
```
> `run.py` 통합 이후 보조 — 사용 안 해도 무방.

### 배포 빌드
```bash
pyinstaller --noconfirm dosu_clinic.spec
# → dist/도수치료예약/ 폴더 (onedir)
```

`dosu_clinic.spec` 이 `hiddenimports` 로 동적 로드 모듈(openpyxl, 마이그레이션 등) 포함.

### 배포 프로세스
1. `app/config.py` 에서 `APP_VERSION` / `APP_BUILD_DATE` 업데이트
2. `CHANGELOG.txt` / `VERSION.txt` / `versions/INDEX.txt` 갱신
3. PyInstaller 빌드 → ZIP 생성 → SHA256 계산
4. GitHub Release 생성 + ZIP 업로드
5. `clinic-updates` 레포의 `manifest.json` 갱신 (version + download_url + sha256)
6. GitHub Pages 반영 (30초~2분)

---

## 🧪 기술 스택

- **백엔드**: Python 3.12 · FastAPI · SQLAlchemy · SQLite · uvicorn
- **프론트엔드**: Jinja2 + Alpine.js + FullCalendar + SortableJS (모두 로컬 번들)
- **배포**: PyInstaller onedir · exclude_binaries=True + COLLECT
- **업데이트 채널**: GitHub Releases (ZIP) + GitHub Pages (manifest.json)
- **CSS 캐시 무효화**: `?v={{ app_version }}` 자동 주입 (v1.2.8+)

---

## 📜 최근 버전 (요약)

| 버전 | 날짜 | 핵심 변경 |
|------|------|----------|
| **v1.3.5** | **2026-05-05** | **UI/UX 모더화 (Phase A~M) + AI 안전 게이트** — CompteExpress 톤 + 가독성 보강 + approve stored-state 게이트 + AI 인증 정책 + AI 도우미 탭 UI 제거 + Codex 외부 검증 |
| v1.3.4 | 2026-05-05 | AI 명령 도우미 (Phase 1~12) — AI 예약 / 휴무 도우미 + commands API + 안전 정책 |
| v1.3.3 | 2026-05-01 | AI/RAG v1 후속 보강 — 휴무 UNIQUE 제약 (m011) + outcome 50자 + /api/ai/health/public |
| v1.3.2 | 2026-04-30 | 직원 관리 강화 — 휴무 연차/월차 (m009) + 치료사 입사일 (m010) |
| v1.3.1 | 2026-04-30 | 보안 + 안정성 패치 — 자동업데이트 hang fix + 인증 누수 + DB 복원 + SMS 비밀 |
| v1.3.0 | 2026-04-30 | **AI/RAG 1차 통합** — AI 도우미 탭 + SMS 초안/점검 + PII 보호 |
| v1.2.18 | 2026-04-28 | 문자나라 발송 결과 오판정 fix + 통계탭 엑셀 다운로드 (3시트) |
| v1.2.17 | 2026-04-28 | 점심시간 설정 + 도수치료 엑셀 다운로드 + 신규 환자 중복 차단 |
| v1.2.16 | 2026-04-25 | 문자나라 설정 저장 시 비밀번호 초기화 버그 수정 |
| v1.2.15 | 2026-04-25 | 문자나라 SMS 한글 인코딩 UTF-8 → CP949 |
| v1.2.14 | 2026-04-25 | 예약 탭 우측 빈 공간 근본 해결 |
| v1.2.10~13 | 2026-04-24 | 예약 표 반응형 레이아웃 시도 |
| v1.2.9 | 2026-04-24 | 집계·통계 **기간 조회** 도입 (date_from/date_to + 프리셋) |
| v1.2.8 | 2026-04-24 | 체외충격파 집계 **수동입력 전용** · **CSS 캐시 자동 무효화** |
| v1.2.7 | 2026-04-23 | 체외충격파 **수동 입력** 기능 (집계 더블클릭) |
| v1.2.6 | 2026-04-23 | 운영 종료 시각 라인 수정 · 상단 접속주소 복사 |
| v1.2.5 | 2026-04-23 | **네이비 헤더 디자인 리뉴얼** |
| v1.2.4 | 2026-04-21 | **자동 업데이트 완성** · DB 자동 백업 · 문자 한글 수정 |
| v1.2.3 | 2026-04-20 | 치료항목 수가/인센티브 · 매출 분석 |
| v1.2.2 | 2026-04-19 | **증분 마이그레이션** · CDN 번들 (오프라인 지원) |
| v1.2.1 | 2026-04-19 | openpyxl 핫픽스 |
| v1.2.0 | 2026-04-18 | 환자 성별 필드 |
| v1.1.0 | 2026-04-18 | 데이터변환 · 문자나라 연동 · 드래그 이동 |

전체 이력은 [`CHANGELOG.txt`](CHANGELOG.txt) 참고.

---

## 🔐 보안 정책

### 비보호 (일상 업무)
캘린더 조회, 예약 등록/수정/취소, 1·2단계 승인, 환자 등록·조회

### 보호 (관리자 비밀번호 필요)
환자 수정/삭제, 치료사 추가/수정/삭제, 시스템 설정, DB 복원, 비밀번호 변경, 감사 로그

### 관리자 인증
- 기본 비밀번호: `admin1234` (최초 변경 권장)
- 세션 8시간 · `localStorage` 보관
- 5회 실패 시 5분 잠금
- 비번 변경 시 모든 세션 즉시 무효화

---

## 📄 라이선스

내부 배포용 · 상업적 재사용 금지
