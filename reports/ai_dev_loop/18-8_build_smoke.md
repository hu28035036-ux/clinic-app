# 18-8 PyInstaller 빌드 + Smoke 검증

> 사용자 승인 (옵션 A) 후 실행. 빌드 결과 + smoke 결과 기록.

## 빌드 명령

```bash
cd "C:/Users/user/Desktop/새 폴더/병원예약관리/병원예약관리"
rm -rf build dist/도수치료예약
venv/Scripts/python.exe -m PyInstaller --noconfirm dosu_clinic.spec
```

(Codex 18-8 권고 우회 방식 — `python -m PyInstaller`. Claude Code 환경에서는
`venv/Scripts/pyinstaller.exe` 도 정상 작동하지만 호환성 우선.)

## 빌드 전 정리

- `build/` — PyInstaller 캐시 제거
- `dist/도수치료예약/` — 18-8 이전 빌드 산출물 (2026-05-01) 제거
- 보존: `dist/dosu_clinic_ai_rag_v1.3.0_20260430.zip`, `dist/dosu_clinic_v1.3.3_20260501.zip`,
  `dist/도수치료예약_v1.2.18.zip` (이전 release ZIP, 사용자가 별도 결정)

## 검증 체크리스트

### 1. 빌드 산출물 존재 + 타임스탬프 ✅

- [x] `dist/도수치료예약/도수치료예약.exe` 존재
- [x] Modify 시각: **2026-05-02 18:01:35** (빌드 직후, 18-8 변경 반영본 — Codex 지적 해결)
- [x] Size: **14,915,945 bytes ≈ 14.9MB** (이전 14.8MB 와 비슷, 18-1~18-7 신규 모듈 추가 반영)
- [x] PyInstaller 빌드 로그: `Building COLLECT COLLECT-00.toc completed successfully` + exit 0
- [x] `[spec] migration auto-register: 13 modules - [m001~m013 모두 13개 등록]`
- [x] `[spec post-build] updater.bat -> dist\도수치료예약\updater.bat`

### 2. `_internal/` 동봉 (Codex 권고 4) ✅

- [x] `_internal/knowledge/manuals/` — 6개 모두 동봉:
      `ai_settings.md / backup.md / munjanara_error.md / no_therapist.md / sms_compose.md / therapist_leave.md`
- [x] `_internal/knowledge/sms_guides/` — 4개 모두 동봉:
      `tone_confirm.md / tone_noshow.md / tone_reminder.md / tone_reschedule.md`
- [x] `_internal/app/templates/` — `main.html / base.html / setup.html / server_info.html`
- [x] `_internal/app/static/css/app.css`
- [x] `dist/도수치료예약/updater.bat` (spec post-build 가 _internal → 루트로 복사)
- [x] `_internal/app/migrations/m001~m013` — Python 모듈은 PYZ archive 에 포함 (file system 미노출이 정상).
      빌드 로그의 `migration auto-register: 13 modules` + 런타임 smoke 의 init_db() 정상 동작으로 입증.
- [x] `_internal/anthropic/` + `_internal/certifi/` 등 SDK 데이터 파일 정상 동봉

### 3. exe 실행 smoke (Codex 권고 3) ✅

격리 환경: `APPDATA=/tmp/dosu_smoke_appdata` (운영 DB 보호)

- [x] exe 실행 → 8000 포트 listen (READY after 2s)
- [x] **`/api/ai/health/public`** (no auth) → 200
      `{"enabled":false,"ready":false,"provider":"openai","api_key_set":false}` — v1.3.3 응답 4키 정확
- [x] **`/api/admin/login`** (admin1234) → 200, 토큰 발급 (예: `sdW38FcanmsPdlYi...`)
- [x] **`/api/ai/health`** (admin) → 200, 응답 9키 정확:
      `enabled / ready / provider / api_key_set / model / sdk_installed / sdk_errors / knowledge_doc_count=10 / version`
- [x] **`/api/ai/status`** (18-7 신규 admin) → 200, top-level 9키 정확:
      `ai_mode=local_only / search_mode=keyword / version / ai_settings / vector_status / external_api / knowledge / prompt_versions / recent_ai_logs`
- [x] **`/api/ai/manual/search`** (LLM 미사용, no auth, AI disabled 에서도 동작) → 200
      한글 query "백업" + 영어 "backup" 모두 `manuals/backup.md` 매칭 정확
- [x] exe 정상 종료 (`taskkill //F //IM 도수치료예약.exe` PID 14012 종료)

### 4. 18-1~18-7 신규 모듈 런타임 import 가능 ✅

`/api/ai/status` 응답이 정상이면 다음이 모두 import 입증:

- [x] `app.services.ai.health` (18-7) — `build_admin_status` 호출 성공
- [x] `app.services.ai.rag.prompts` — `prompt_versions["manual_qa.system"]="v1"` 응답
- [x] `app.services.ai.rag.{schemas,pipeline,retriever,...}` — manual_qa wrapper 가 정상 동작
- [x] `app.services.ai.knowledge.{loader,keyword_index}` — `knowledge_doc_count=10` 응답
- [x] `app.services.ai.vector.*` — vector_status 응답 (m014 미도입 → disabled 정상 파생)
- [x] `app.services.ai.rag.{reranker,confidence}` — import 됨 (status 응답 200 이면 사용 가능)

### 5. API key / PII 보호 검증 (런타임) ✅

- [x] `/api/ai/status` 응답 `ai_settings` dict 에 `api_key`/`api_key_masked` 키 부재
- [x] `api_key_set: False` boolean 만 노출
- [x] `/api/ai/health` admin 응답에도 api_key 평문 부재

### 6. 운영 DB 보호 검증 ✅

- [x] APPDATA 격리 (`/tmp/dosu_smoke_appdata`) — 사용자의 운영 DB
      (`C:\Users\user\AppData\Roaming\도수치료예약\clinic.db`) 미접근
- [x] exe 가 임시 APPDATA 에 새 clinic.db 생성 + init_db() m001~m013 실행
- [x] smoke 후 임시 APPDATA 폴더 정리 가능 (사용자 결정)

## 결과

✅ **PyInstaller 빌드 100% 성공 + smoke 100% 통과**.

| 항목 | 결과 |
|---|---|
| 빌드 exit code | 0 |
| exe 크기 | 14.9MB |
| 빌드 시각 | 2026-05-02 18:01:35 |
| listen ready | 2초 |
| /api/ai/health/public | 200, 4키 정확 |
| /api/admin/login | 200, 토큰 발급 |
| /api/ai/health admin | 200, 9키 + knowledge_doc_count=10 |
| /api/ai/status (18-7) | 200, 9 top-level 키 + api_key 부재 + ai_mode/search_mode/vector_status/prompt_versions 정확 |
| /api/ai/manual/search | 200, 한글/영어 검색 정확 |
| 운영 DB 보호 | OK (APPDATA 격리) |

**Codex 18-8 1/2회차 지적 (사용자 요청 15/16번 미충족) 모두 해결**:
- ✅ 15번 "PyInstaller 빌드 성공" — 빌드 exit 0, 14.9MB exe 생성
- ✅ 16번 "빌드 산출물 실행 가능" — 8000 포트 listen + 5개 엔드포인트 smoke 통과
