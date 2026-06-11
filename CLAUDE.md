# 도수치료예약 — 작업 규칙 (CLAUDE.md)

## 🛡️ 작업 규칙 (하네스)

이 프로젝트는 안정성 하네스(`tests/`, `docs/specs/`, `run_check.bat`)가 적용되어 있다.
Claude Code 가 이 프로젝트의 코드를 수정할 때는 아래 규칙을 반드시 지킬 것.

### 절대 금지

- 실제 운영 DB `%APPDATA%\도수치료예약\clinic.db` 를 테스트에 사용하지 않는다.
- 요청받지 않은 파일을 대규모로 리팩토링하지 않는다.
- DB 컬럼명을 임의로 변경하지 않는다.
- API 경로를 임의로 바꾸지 않는다.
- 예약 / 통계 / 권한 로직을 UI 만 수정하고 끝내지 않는다.
- 프론트에서 막는 기능은 반드시 백엔드에서도 검증한다.
- 기능 수정과 디자인 수정을 한 번에 섞지 않는다.
- 하네스 적용 작업 중 업종 변경, 용어 변경, 브랜딩 변경을 하지 않는다.
- `pyproject.toml` 의 `app/**` lint 면제(per-file-ignores)를 풀지 않는다 — 의도적으로 둔 것이며, 이를 풀면 대규모 포맷팅이 발생한다.
- `manual60` 을 다시 `count_increment=2` 로 되돌리지 않는다 (`manual60` = 1카운트 정책).

### 작업 전 필수

- 관련 `docs/specs/*.md` 문서를 먼저 읽는다.
- 수정 대상 파일을 먼저 읽고 현재 흐름을 요약한다.
- 변경 범위를 최소화한다.
- 실제 DB 를 사용하지 않는지 확인한다 (`run_check.bat` 의 DB 경로 안전 검사).

### 작업 후 필수

- `run_check.bat` 한 방으로 pytest + ruff + DB 경로 안전검사 실행.
- 또는 개별로:
  - `venv\Scripts\python.exe -m pytest tests -v`
  - `venv\Scripts\python.exe -m ruff check app tests`
  - `venv\Scripts\python.exe scripts/check_db_path.py`
- 실패 시 어떤 규칙이 깨졌는지 한국어로 설명한다.
- 자세한 절차는 `docs/CHANGE_RULES.md` 참조.

## 🚨 배포 규칙 (중요)

**GitHub 에 배포하기 전에 반드시 사용자에게 확인 받기.**

"배포" 에 해당하는 동작 (사용자 동의 없이 ❌ 절대 하지 말 것):
- PyInstaller 빌드 (시간이 걸리는 작업)
- ZIP 패키징
- `gh release create` (GitHub Release 생성)
- `clinic-updates` 레포에 manifest.json / README.md 푸시
- `versions/v1.2.X/` 백업 폴더 생성

코드/문서 수정은 자유롭게 진행 OK:
- `app/` 하위 코드 수정
- `CHANGELOG.txt` / `VERSION.txt` / `versions/INDEX.txt` 갱신
- 로컬 README.md 수정
- `app/config.py` 의 APP_VERSION 갱신

### 권장 흐름

1. 사용자 요청 분석 → 코드 수정
2. dev 서버로 검증 (필요 시)
3. **"수정 끝났습니다. 빌드 + 배포할까요?" 라고 물어보기**
4. 승인 받으면 빌드 → ZIP → Release → manifest push

여러 fix 를 모아서 한 번에 배포하는 게 좋음 — 너무 자주 업데이트하면 사용자 혼란 + GitHub Releases 가 지저분해짐.

## 📦 프로젝트 개요

- 도수치료 전문 병원 예약 관리 (Windows 단독 실행형)
- FastAPI + SQLAlchemy + SQLite
- Jinja2 + Alpine.js (서버 사이드 렌더링 + 가벼운 client-side 인터랙션)
- PyInstaller onedir 배포 → `dist/도수치료예약/`
- 자동 업데이트: GitHub Releases + GitHub Pages 매니페스트
  - 매니페스트 URL: `https://hu28035036-ux.github.io/clinic-updates/manifest.json`
  - 배포 레포: `hu28035036-ux/clinic-updates`

## 📂 데이터 폴더 (사용자 환경)

```
%APPDATA%\도수치료예약\
├── clinic.db           # 환자·예약·직원·SMS설정 등 (SQLite)
├── config.json         # 노드ID·매니페스트URL·기본설정
├── schema_version.txt
└── backups\            # 자동 백업 + 업데이트 직전 스냅샷
```

⚠️ **업데이트는 프로그램 폴더(exe + _internal)만 교체. DB는 절대 안 건드림.**

## 🗄️ 마이그레이션 시스템

`app/migrations/m00X_*.py` 파일들이 순차 실행 (`schema_migrations` 테이블 기준).
- 새 마이그레이션 추가 시 `dosu_clinic.spec` 의 `hiddenimports` 에도 등록 필요.

현재 마이그레이션:
- 001 베이스라인 / 002 patients.gender / 003 sms_settings.api_url
- 004 인덱스 / 005 치료항목 수가-인센티브 / 006 manual_counts (ESWT 수동입력)

## 🛠️ 빌드 명령

```bash
cd "C:/Users/user/Desktop/새 폴더/병원예약관리/병원예약관리"
rm -rf build dist/도수치료예약 dist/dosu_clinic_v*.zip
venv/Scripts/pyinstaller.exe --noconfirm dosu_clinic.spec
# → dist/도수치료예약/ 폴더 생성됨

# 추가 동봉 파일 (CHANGELOG, VERSION, 도구/, 안내txt 등) 복사 + ZIP 패키징
# (PowerShell 스크립트로 처리. 과거 세션 참고)
```

## 🔍 자주 보는 파일

- `app/routers/api.py` — 모든 API 엔드포인트 (긴 파일, ~3800줄)
- `app/templates/main.html` — 메인 페이지 HTML + Jinja 설정 상수 (~450줄)
- `app/static/js/main.js` — 모든 탭 JS (~9100줄, main.html 에서 분리됨. `?v={{ app_version }}` 캐시 무효화로 로드)
- `app/static/css/app.css` — 디자인 + 레이아웃 (~3300줄)
- `app/config.py` — 버전·기본설정·APP_NAME

## 📝 버전업 시 문서 업데이트 체크리스트

1. `app/config.py` — APP_VERSION, APP_BUILD_DATE
2. `CHANGELOG.txt` — 맨 위에 새 버전 블록 추가
3. `VERSION.txt` — 통째로 새로 작성
4. `versions/INDEX.txt` — 맨 위에 새 버전 블록 추가
5. (배포 시) `clinic-updates/README.md` — 버전 히스토리 섹션 갱신
6. (배포 시) `clinic-updates/manifest.json` — version/sha256/notes 갱신
