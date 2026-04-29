# 도수치료예약 — 작업 규칙 (CLAUDE.md)

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
- `app/templates/main.html` — 메인 페이지 + 모든 탭 JS (~5000줄)
- `app/static/css/app.css` — 디자인 + 레이아웃 (~3000줄)
- `app/config.py` — 버전·기본설정·APP_NAME

## 📝 버전업 시 문서 업데이트 체크리스트

1. `app/config.py` — APP_VERSION, APP_BUILD_DATE
2. `CHANGELOG.txt` — 맨 위에 새 버전 블록 추가
3. `VERSION.txt` — 통째로 새로 작성
4. `versions/INDEX.txt` — 맨 위에 새 버전 블록 추가
5. (배포 시) `clinic-updates/README.md` — 버전 히스토리 섹션 갱신
6. (배포 시) `clinic-updates/manifest.json` — version/sha256/notes 갱신
