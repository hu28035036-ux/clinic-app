# 18 AI/RAG 최종 배포 전 체크리스트

> v1.4.0 배포 직전 사용자가 한 번 더 확인할 항목.
> 자동 검증 항목 (테스트/lint/빌드) 은 18-8 시점에 모두 통과.
> 본 문서는 사용자 수동 확인 + 배포 절차 가이드.

## 1. 자동 검증 결과 (18-8 시점)

| 항목 | 결과 | 출처 |
|---|---|---|
| 전체 pytest | **529 passed, 1 skipped, 7 xfailed** | `reports/ai_dev_loop/18-8_test_report.md` |
| ruff `app tests scripts` | All checks passed | 동상 |
| `scripts/check_db_path.py` | OK | 동상 |
| PyInstaller hidden import 사전 검증 | 53 passed | `tests/test_pyinstaller_hidden_imports.py` |
| PyInstaller 실제 빌드 | exit 0, 14.9MB | `reports/ai_dev_loop/18-8_build_smoke.md` |
| exe smoke (5 엔드포인트) | 모두 200 + 응답 키 정확 | 동상 |

→ 전체 통과. 코드 차원에서 추가 조치 불필요.

## 2. 회귀 보호 — 응답 키 후방호환

### 2-1. v1.3.3 응답 키 보존 단언 (자동 테스트로 입증)

| 엔드포인트 | 필수 키 수 | 검증 테스트 |
|---|---|---|
| `/api/ai/manual/search` | 3 (sources/masked_question/top_score) | `test_ai_manual_rag_contract.py`, `test_ai_contract_manual.py` |
| `/api/ai/manual/ask` | 9 (answer/sources/confidence/not_found/blocked/blocked_reason/guard_hits/top_score/masked_question) | 동상 |
| `sources[]` 항목 | 3 (title/path/snippet) | 동상 |
| `/api/ai/health` admin | 9 (enabled/ready/provider/api_key_set/model/sdk_installed/sdk_errors/knowledge_doc_count/version) | `test_ai_health_public.py`, `test_ai_contract_manual.py` |
| `/api/ai/health/public` | 4 (enabled/ready/provider/api_key_set) | 동상 |

### 2-2. 신규 18-7 엔드포인트 키 (admin 전용)

| 엔드포인트 | top-level 9키 | 검증 테스트 |
|---|---|---|
| `/api/ai/status` | ai_mode/search_mode/version/ai_settings/vector_status/external_api/knowledge/prompt_versions/recent_ai_logs | `test_ai_health_status.py`, `test_admin_ui_smoke.py` |

→ 신규 엔드포인트 추가만, 기존 엔드포인트 무수정. 후방호환 100%.

## 3. 운영 DB 보호

### 자동 검증 결과
- `scripts/check_db_path.py` 통과 (단독 실행 시 운영 경로 표시는 의도된 INFO).
- `tests/conftest.py` 4단계 격리 (APPDATA + DOSU_DB_PATH + 워커 무력화 + SDK 차단).
- 다수 `test_*_does_not_use_operational_db` 통과.
- exe smoke 도 격리 APPDATA (`/tmp/dosu_smoke_appdata`) 로 진행 — 사용자 운영 DB 미접근.

### 사용자 수동 확인
- [ ] 운영 환경에서 v1.4.0 첫 실행 시 `%APPDATA%\도수치료예약\backups\` 에 자동 백업이 생기는지 확인.
- [ ] 첫 실행 시 init_db() 가 m012/m013 자동 실행 → `knowledge_chunks` / `knowledge_vectors` 테이블 생성 확인.
- [ ] m012/m013 idempotent — 두 번째 실행 시 에러 없이 skip.

## 4. 외부 API 호출 차단

### 자동 검증 결과
- conftest `_block_sdk_modules` 가 openai/anthropic SDK 클래스를 raise stub 으로 교체.
- 모든 테스트에서 FakeProvider / FakeEmbeddingProvider 만 사용.
- `should_call_llm()` 다층 게이트 — provider_disabled / pii / local_only / no_sources / low_confidence 5개 차단 케이스.
- `local_only` 모드에서 `len(provider.calls) == 0` + `len(embedding_provider.calls) == 0` 단언.

### 사용자 수동 확인
- [ ] 운영 환경에서 v1.4.0 첫 실행 시 `AiSetting.enabled=False` (default) — 외부 LLM 호출 0.
- [ ] 사용자가 명시적으로 `enabled=True` + `api_key` + `model` 설정해야 LLM 호출 가능 (manual_ask 게이트 통과 케이스만).
- [ ] vector path 는 m014 미도입 → 항상 disabled (외부 embedding 호출 0).

## 5. API key / 개인정보 비노출

### 자동 검증 결과 (테스트 단언)
- `/api/ai/status` 응답 — `api_key` / `api_key_masked` 키 부재, `api_key_set` boolean 만 노출.
- `/api/ai/health/public` — `api_key_set` boolean 만 노출.
- `recent_ai_logs.recent[].error_detail` — `pii.scan().cleaned` 마스킹 + 200자 cap (`_safe_error_detail` 헬퍼).
- `prompt_hash` / `response_hash` — 응답 부재 (DB 저장은 sha256, UI 노출 X).
- 운영 환경에서 fixture `test-fake-key` / 평문 / 마스킹 형식 모두 응답 본문 부재 (smoke 입증).

### 사용자 수동 확인
- [ ] 운영 환경에서 실제 API key 등록 후 `/api/ai/settings` 응답이 마스킹 (`sk-X****`) 만 노출하는지 확인.
- [ ] `/api/ai/status` 응답에 api_key 평문 / 마스킹 모두 부재 확인.
- [ ] `AiUsageLog` 테이블 직접 SELECT 시 `prompt_hash` / `response_hash` 만 보이고 원문 부재 확인.

## 6. PyInstaller 빌드

### 자동 검증 결과
- spec hidden imports 17개 추가 (18-1~18-7 신규 모듈) — `test_pyinstaller_hidden_imports.py:test_18_X_module_in_spec_hidden_imports` 19개 parametrize 모두 통과.
- 빌드 exit 0, 14.9MB exe.
- `_internal/{knowledge, app/templates, app/static}` 동봉 + updater.bat 루트 배치 + m001~m013 PYZ 포함.
- 빌드 후 exe smoke 5 엔드포인트 모두 통과.

### 사용자 수동 확인 (배포 직전)
- [ ] 사용자 환경에서 `venv/Scripts/python.exe -m PyInstaller --noconfirm dosu_clinic.spec` 재실행 (선택).
- [ ] dist/도수치료예약/도수치료예약.exe 더블클릭 → 기본 화면 (http://127.0.0.1:8000) 정상 로드.
- [ ] `_internal/knowledge/manuals/` 6개 .md 동봉 확인.

## 7. 배포 절차 (CLAUDE.md 배포 규칙 준수)

### 7-1. 사전 (코드 단계 — 사용자 승인 후)
- [ ] `app/config.py` APP_VERSION = "1.4.0", APP_BUILD_DATE 갱신
- [ ] `CHANGELOG.txt` 맨 위에 v1.4.0 블록 추가 (18-0~18-8 변경사항)
- [ ] `VERSION.txt` 통째로 새 작성 (v1.4.0 기준)
- [ ] `versions/INDEX.txt` 맨 위에 v1.4.0 블록 추가

### 7-2. 빌드 (사용자 승인 후)
```bash
cd "C:/Users/user/Desktop/새 폴더/병원예약관리/병원예약관리"
rm -rf build dist/도수치료예약
venv/Scripts/python.exe -m PyInstaller --noconfirm dosu_clinic.spec
```

### 7-3. ZIP 패키징
```bash
# CHANGELOG/VERSION/도구/안내txt 등 추가 동봉 파일 복사 + ZIP
# (PowerShell 스크립트로 처리. 과거 세션 참고)
```

→ 결과: `dist/dosu_clinic_v1.4.0_20260502.zip`

### 7-4. GitHub Release
```bash
gh release create v1.4.0 \
  --title "v1.4.0 — AI/RAG v1 통합 (18-0~18-8)" \
  --notes-file <release_notes.md> \
  dist/dosu_clinic_v1.4.0_20260502.zip
```

### 7-5. clinic-updates manifest 푸시
- `manifest.json` 의 version / sha256 / notes 갱신
- `README.md` 의 버전 히스토리 섹션 갱신
- 매니페스트 URL: `https://hu28035036.github.io/clinic-updates/manifest.json`

### 7-6. 백업 폴더
- `versions/v1.4.0/` 디렉토리 생성 + 빌드 산출물 + 리포트 보존

## 8. Git 커밋 분리 (Codex 18-7 M-B + 18-8 누적 권고)

### 옵션 A: 세션별 커밋 분리 (세부 추적)
- 18-0 ~ 18-8 각 세션을 별도 커밋으로
- 시간 소요: ~1시간

### 옵션 B: 단일 release commit (속도 우선)
- 모든 18-X 변경을 `release: v1.4.0 — AI/RAG v1` 단일 커밋
- 시간 소요: 즉시

### 사용자 결정
- [ ] 옵션 A 또는 B 선택
- [ ] 커밋 후 ai-rag-v1-integration 브랜치를 main 에 머지

## 9. 운영 환경 smoke (Codex 18-8 권고)

배포 직후 운영 환경에서 실행:

- [ ] `dist/도수치료예약/도수치료예약.exe` 더블클릭 → 8000 포트 listen 확인.
- [ ] 브라우저 자동 열림 → 기본 화면 로드 OK.
- [ ] 관리자 로그인 (admin1234) → 토큰 발급.
- [ ] `/api/ai/health/public` 200 응답.
- [ ] `/api/ai/status` 200 응답 + 9 top-level 키 정확.
- [ ] `/api/ai/manual/search` 200 + 한글 검색 매칭.
- [ ] (외부 API key 등록한 경우) `/api/ai/manual/ask` 200 + LLM 1회 호출 + 응답 받음.
- [ ] 24시간 후 `/api/ai/status` 응답의 `recent_ai_logs.total` 카운트 확인 (호출 흐름 정상).

## 10. 후속 모니터링 (배포 후 1주일)

- [ ] 사용자 보고: 기능 깨짐 0
- [ ] AI 비활성 (default) 상태에서 외부 LLM 호출 0 (비용 단계)
- [ ] PII 사고 0 (admin 화면 + 로그 확인)
- [ ] 백업 자동 동작 OK
- [ ] init_db() 마이그레이션 m012/m013 idempotent 동작 OK

## 11. 종합 자체 판단

✅ **자동 검증 100% 통과 + Codex 1/2회차 모두 해결 + PyInstaller 빌드 + smoke 통과**.

⏳ **사용자 수동 확인 (운영 환경 smoke) 후 v1.4.0 정식 배포 가능**.
