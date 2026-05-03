# 18 AI/RAG 백업 / 복구 / Rollback 노트

> v1.4.0 배포 직전 백업 권장 + 문제 발생 시 v1.3.3 으로 되돌리는 절차.

## 1. 배포 전 백업 권장

### 1-1. 사용자 운영 DB 백업

**필수**:
- 위치: `%APPDATA%\도수치료예약\clinic.db`
- 자동 백업: `%APPDATA%\도수치료예약\backups\` 폴더에 매일 자동 (기존 동작 그대로)
- v1.4.0 첫 실행 시 init_db() 가 m012/m013 자동 실행 — `knowledge_chunks` / `knowledge_vectors` 테이블 신규 생성

**수동 백업 권장 절차**:
```powershell
# 운영 DB 수동 복사 (배포 직전)
$src = "$env:APPDATA\도수치료예약\clinic.db"
$dst = "$env:APPDATA\도수치료예약\backups\clinic_pre_v1.4.0_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
Copy-Item $src $dst
```

**검증**:
- [ ] 백업 파일 size 가 원본과 동일 (보통 수십 MB)
- [ ] SQLite browser 로 열어서 `appointments` 카운트 확인

### 1-2. 운영 환경 config.json 백업

```powershell
$src = "$env:APPDATA\도수치료예약\config.json"
$dst = "$env:APPDATA\도수치료예약\backups\config_pre_v1.4.0.json"
Copy-Item $src $dst
```

내용에 다음이 포함되어 있어야:
- `node_id` — 동기화 식별자
- `manifest_url` — 자동 업데이트 URL
- AI 관련 설정 (provider/model/api_key 는 DB 의 `ai_settings` 에 있음)

### 1-3. 현재 docs/ + reports/ 보존

본 v1.4.0 릴리즈와 함께 다음을 보존 권장:

```
docs/
├── AI_WORKING_RULES.md
├── ai_rag_*.md (8 파일)
├── ai_harness_overview.md
├── ai_codex_review_protocol.md
├── ai_code_session_protocol.md
├── ai_docs_index.md
├── checklists/18-0_*.md ~ 18-8_*.md
├── harnesses/{full,rag,safety,chunk,vector,hybrid,component}_harness_*.md
├── migrations_rollback/m012_rollback.sql, m013_rollback.sql
└── releases/18_ai_rag_*.md (본 문서 묶음)

reports/ai_dev_loop/
├── 18-0_*.md ~ 18-8_*.md (~30 파일)
├── latest_*.md (5 파일)
└── 18-8_build_smoke.md
```

→ Git 커밋 + GitHub repo 에 보존되므로 별도 백업 불필요.
→ 단, GitHub 외부 보관 필요 시 `versions/v1.4.0/docs_snapshot.zip` 형태로 동봉 권장.

## 2. v1.4.0 빌드 산출물 백업

### 2-1. 권장 백업 디렉토리 구조

```
versions/
└── v1.4.0/
    ├── 도수치료예약_v1.4.0.exe    (또는 폴더 통째)
    ├── dosu_clinic_v1.4.0_20260502.zip  (배포용 ZIP)
    ├── CHANGELOG.txt              (빌드 시점 스냅샷)
    ├── VERSION.txt                (빌드 시점 스냅샷)
    ├── manifest.json              (clinic-updates 푸시 시점 스냅샷)
    ├── sha256.txt                 (ZIP/exe sha256 해시)
    └── README.txt                 (빌드 환경 + Python 버전 + PyInstaller 버전)
```

### 2-2. sha256 해시 저장

```bash
cd "C:/Users/user/Desktop/새 폴더/병원예약관리/병원예약관리"
sha256sum dist/dosu_clinic_v1.4.0_20260502.zip > versions/v1.4.0/sha256.txt
sha256sum dist/도수치료예약/도수치료예약.exe >> versions/v1.4.0/sha256.txt
```

→ 이후 manifest.json 의 sha256 필드와 비교해 ZIP 무결성 보증.

## 3. 문제 발생 시 Rollback 기준

### 3-1. 즉시 Rollback 트리거 (사고)

다음 중 하나라도 발생 시 즉시 v1.3.3 으로 되돌림:
- v1.4.0 첫 실행 시 init_db() 실패 (m012 또는 m013 RuntimeError)
- 기존 예약/환자/통계 데이터 유실
- AI 호출 비용 24시간 1만 토큰 초과
- PII 노출 사고 (admin 화면 또는 로그에서 환자 정보 평문 발견)
- exe 실행 직후 크래시

### 3-2. 점진 Rollback 트리거 (퇴행)

다음은 즉시는 아니지만 다음 패치 (v1.4.1) 까지 회피:
- AI 응답 품질 저하 (사용자 보고)
- /api/ai/status 응답 지연 5초 초과
- 신규 reason_code 가 프론트 분기와 불일치

→ 일시 회피: `AiSetting.enabled=False` (전체 AI OFF)

## 4. v1.3.3 복구 절차

### 4-1. exe 복구

**옵션 A**: 자동 업데이트 manifest 되돌리기
1. `clinic-updates` repo 의 `manifest.json` 에서 version 을 `1.3.3` 으로 변경
2. 사용자 환경에서 자동 업데이트 트리거 → v1.3.3 다운로드 + 교체
3. updater.bat 가 `_internal/` + exe 교체

**옵션 B**: 수동 교체
1. `versions/v1.3.3/dosu_clinic_v1.3.3_20260501.zip` 다운로드
2. 사용자에게 압축 해제 후 기존 폴더 덮어쓰기 안내

### 4-2. DB 마이그레이션 rollback

⚠️ **주의**: m012/m013 은 **테이블 추가만 함**. 기존 데이터 영향 0.
- `knowledge_chunks` / `knowledge_vectors` 테이블이 생성된 채로 v1.3.3 으로 되돌리면:
  - v1.3.3 코드는 두 테이블을 모르므로 그냥 무시 (read 안 함)
  - 데이터 무결성 영향 0

**완전 제거 (선택, 디스크 공간 회수 목적)**:
```sql
-- docs/migrations_rollback/m013_rollback.sql 실행
DROP TABLE IF EXISTS knowledge_vectors;

-- docs/migrations_rollback/m012_rollback.sql 실행
DROP TABLE IF EXISTS knowledge_index_runs;
DROP TABLE IF EXISTS knowledge_chunks;
```

→ rollback SQL 은 idempotent + IF EXISTS 가드. 데이터 손실 없음 (knowledge 데이터는 운영 DB 가 아닌 source markdown 에서 재생성 가능).

### 4-3. config.json 복구

```powershell
$bak = "$env:APPDATA\도수치료예약\backups\config_pre_v1.4.0.json"
$dst = "$env:APPDATA\도수치료예약\config.json"
Copy-Item $bak $dst -Force
```

→ AI 설정 (provider/model/api_key) 은 DB 의 `ai_settings` 에 있으므로 config.json 복구 만으로는 영향 0. 필요 시 `/api/ai/settings` PUT 으로 재설정.

### 4-4. AiSetting / AiUsageLog 데이터

- 두 테이블 모두 m007/m008 (v1.3 stage1 시점) — v1.3.3 도 동일 스키마.
- 18-0~18-8 에서 두 테이블 컬럼 변경 0.
- v1.3.3 으로 rollback 시 데이터 그대로 사용 가능.

## 5. 이전 안정 버전으로 되돌릴 때 확인 항목

### 5-1. v1.3.3 으로 되돌릴 경우

- [ ] `app/config.py` APP_VERSION = "1.3.3" 확인
- [ ] `dist/도수치료예약/도수치료예약.exe` 가 v1.3.3 빌드 (2026-05-01) 확인
- [ ] `_internal/knowledge/manuals/` 6개 .md 동봉 확인 (v1.3.3 시점은 6개 동일)
- [ ] `_internal/knowledge/sms_guides/` 4개 .md 동봉 확인
- [ ] `_internal/app/migrations/` 에 m001~m011 만 있어도 OK (m012/m013 부재 정상)
- [ ] 운영 DB 의 `knowledge_chunks` / `knowledge_vectors` 테이블 — 있으면 v1.3.3 가 무시 (제거 선택)
- [ ] `/api/ai/health` admin 응답이 v1.3.3 9키 정확
- [ ] `/api/ai/manual/{search,ask}` 응답 9키/3키 정확
- [ ] `/api/ai/status` — v1.3.3 에는 부재 (404 정상)

### 5-2. v1.2.18 으로 더 되돌릴 경우 (비상)

- AiSetting / AiUsageLog 테이블이 없는 v1.2.x 로 가는 건 비추천.
- 데이터 손실 없이는 어렵 (m007/m008 이 컬럼 추가만, 제거는 SQLite 제약).
- 부득이한 경우: 운영 DB 백업 → v1.2.18 deploy → ai_* 테이블은 그대로 남음 (영향 0).

## 6. 운영 백업 자동화 (기존)

v1.3.3 부터 다음 자동 백업이 동작 (v1.4.0 도 동일):

| 트리거 | 위치 | 보관 |
|---|---|---|
| 매일 자동 (24시간) | `%APPDATA%\도수치료예약\backups\clinic_<date>.db` | 30일 (롤링) |
| 업데이트 직전 (자동) | `%APPDATA%\도수치료예약\backups\clinic_pre_update_<version>.db` | 영구 |
| 사용자 수동 (관리자 화면) | `%APPDATA%\도수치료예약\backups\clinic_manual_<datetime>.db` | 영구 |

→ v1.4.0 첫 실행 시 자동 백업 + init_db() 가 안전하게 동작.

## 7. 검증 — 백업 + 복구 동작 확인 (선택)

### 7-1. 백업 동작 확인 (v1.4.0 첫 실행 직후)

```powershell
# 자동 백업 폴더 확인
Get-ChildItem "$env:APPDATA\도수치료예약\backups\" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 5
```

→ `clinic_<오늘날짜>.db` 가 보이면 자동 백업 정상.

### 7-2. 복구 시뮬레이션 (선택, 별도 테스트 환경)

1. v1.4.0 배포 후 임시 폴더에 v1.3.3 추출
2. 운영 DB 복사본을 v1.3.3 환경으로 옮김
3. v1.3.3 정상 동작 확인 (manual/search 200, /api/ai/health 9키)
4. 데이터 무결성 검증 (`appointments` / `patients` 카운트 동일)

## 8. 비상 연락 / 문의 채널

- 사용자 직접 보고: `https://github.com/anthropics/claude-code/issues` (Claude Code CLI 기준)
- 본 프로젝트 owner: `hu28035036-ux`
- clinic-updates manifest URL: `https://hu28035036-ux.github.io/clinic-updates/manifest.json`

## 9. 종합 권장

✅ **배포 직전 (v1.4.0)**:
1. 사용자 운영 DB 수동 백업 (1회)
2. config.json 백업 (1회)
3. v1.3.3 빌드 산출물 보존 (`versions/v1.3.3/` 디렉토리 생성)
4. `versions/v1.4.0/` 디렉토리 생성 + sha256.txt 보존

✅ **배포 후 (1주일)**:
1. 자동 백업 정상 동작 확인 (매일 1개)
2. AI 호출 비용 모니터링
3. 사용자 보고 추적

⚠️ **사고 시**: §3 의 트리거 기준으로 즉시/점진 Rollback 결정.
