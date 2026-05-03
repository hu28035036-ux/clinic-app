# 18-8 Test Report — 전체 회귀 + PyInstaller 빌드 + Smoke 검증 ✅ 완료

> **상태**: 테스트/lint/빌드/smoke 100% 통과. **사용자 옵션 A 승인 후 빌드 + smoke 완료**.
> 사용자 요청 15번 "PyInstaller 빌드 성공" + 16번 "빌드 산출물 실행 가능" 모두 충족.

## 1. 세션 이름

**18-8_final_release** — 18-0~18-7 전체 회귀 테스트 + PyInstaller 빌드 사전 검증
(`tests/test_pyinstaller_hidden_imports.py`) + spec hidden imports 누락 보강.

## 2. 환경

- 작업 디렉토리: `C:\Users\user\Desktop\새 폴더\병원예약관리\병원예약관리`
- 브랜치: `ai-rag-v1-integration`
- Python: 3.12.10 (`venv\Scripts\python.exe`)
- pytest: 8.4.2
- ruff: latest
- PyInstaller: 빌드 미실행 (사용자 승인 대기)
- 격리 DB: `tests/temp/test_clinic_<uuid>.db` (운영 DB 미사용)

## 3. 실행 명령

```
venv\Scripts\python.exe -m pytest tests --tb=short -q
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -v
venv\Scripts\python.exe -m pytest tests/<개별 하네스 묶음> -q  (4 묶음)
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts/check_db_path.py
```

## 4. 결과 요약

| 항목 | 결과 |
|---|---|
| **전체 pytest** | **529 passed, 1 skipped, 7 xfailed, 27 warnings** |
| ruff (`app tests scripts`) | **All checks passed!** |
| check_db_path | OK (테스트 격리 + 단독 실행 INFO 의도) |
| **신규 18-8 테스트 (`test_pyinstaller_hidden_imports.py`)** | **53 passed** |

baseline 비교:
- 18-7: 476 passed, 1 skipped, 7 xfailed
- 18-8: **529 passed (+53), 1 skipped, 7 xfailed (회귀 0)**

## 5. AI/RAG 하네스별 결과 (개별 실행)

| 하네스 | 묶음 | 결과 |
|---|---|---|
| 18-0 RAG/Safety/Full + 18-1~18-7 통합 | `test_rag_pipeline.py` + `test_rag_safety.py` + `test_ai_safety_harness.py` + `test_ai_full_harness.py` + `test_ai_manual_rag_harness.py` + `test_ai_manual_rag_contract.py` + `test_ai_chunker_harness.py` + `test_ai_reindex_harness.py` + `test_ai_vector_harness.py` + `test_hybrid_retriever.py` + `test_ai_assist_mode.py` + `test_ai_health_status.py` + `test_ai_contract_manual.py` + `test_admin_ui_smoke.py` + `test_full_harness.py` + `test_local_only_mode.py` | **293 passed** |
| SMS AI / 휴무 AI / 기존 AI | `test_ai_action_leave.py` + `test_ai_sms_draft.py` + `test_ai_sms_validate.py` + `test_ai_sms_draft_hallucination.py` + `test_ai_logging.py` + `test_ai_hallucination.py` + `test_ai_manual_qa.py` + `test_ai_health_public.py` | **98 passed** |
| 비-AI 기능 회귀 | `test_appointment_rules.py` + `test_employee_*.py` + `test_stats_counts.py` + `test_therapist_leave.py` + `test_admin_auth_required.py` + `test_db_restore_safety.py` + `test_graceful_shutdown.py` + `test_migration_spec_discovery.py` + `test_smoke.py` + `test_sms_secret_masking.py` + `test_update_log.py` + `test_updater_invocation.py` | **85 passed, 1 skipped, 7 xfailed** |
| **PyInstaller hidden imports (신규 18-8)** | `test_pyinstaller_hidden_imports.py` | **53 passed** |

세부 카운트:
- 18-0 RAG/Safety/Full: rag_pipeline 5 + rag_safety 6 + ai_safety_harness 12 + ai_full_harness 8 + full_harness 9 + local_only_mode 4 = 44
- 18-1 manual RAG harness: 18
- 18-2 manual RAG contract: 9
- 18-3 chunker harness: 35
- 18-4 reindex harness: 24
- 18-5 vector harness: 36
- 18-6 hybrid retriever: 46 + ai_assist_mode 15 = 61
- 18-7 health_status 43 + contract_manual 9 + admin_ui_smoke 14 = 66
- 18-8 pyinstaller_hidden_imports: 53

## 6. 핵심 단언 결과

| 항목 | 결과 |
|---|---|
| 운영 DB 미사용 | ✅ check_db_path + `test_*_does_not_use_operational_db` 다수 |
| 외부 LLM/Embedding 호출 0 | ✅ FakeProvider/FakeEmbeddingProvider + conftest `_block_sdk_modules` |
| local_only 모드 호출 0 | ✅ `test_local_only_*` + `test_hybrid_local_only_blocks_vector_path` |
| sources 없음 / low_confidence / PII / unknown_feature → provider 호출 0 | ✅ confidence harness + safety harness |
| API key 원문/마스킹 화면/로그 노출 0 | ✅ `test_status_endpoint_no_api_key_in_response` (정확한 키 검사) |
| 개인정보 (전화/생년월일/RRN) 화면/로그 노출 0 | ✅ `test_status_endpoint_masks_pii_in_recent_logs` + `_safe_error_detail` 단위 |
| /api/ai/manual/{search,ask} 응답 9키/3키 보존 | ✅ `test_18_7_manual_*_keys_preserved` |
| /api/ai/health public 4키 / admin 9키 보존 | ✅ `test_18_7_health_*_keys_unchanged` |
| /api/ai/status 신규 9 top-level 키 | ✅ `test_status_response_top_level_keys_sane` |
| 마이그레이션 m001~m013 모두 import 가능 | ✅ `test_all_migration_modules_importable` |
| spec hidden imports 모두 import 가능 (18-8 신규) | ✅ `test_all_app_modules_importable` + 19개 18-X 모듈 parametrize |
| spec collect_submodules 실패 가드 | ✅ `test_spec_does_not_have_silent_collect_failure` |
| knowledge/ 디렉토리 동봉 가능 | ✅ `test_knowledge_directory_exists_for_data_bundle` |
| app/templates / app/static / updater.bat 동봉 가능 | ✅ `test_app_templates/static_exists` + `test_updater_bat_exists` |

## 7. 자동 수정 루프 횟수

**1/5 회차** — 1회차에 모든 테스트 통과.

1회차 사이클:
1. 전체 pytest baseline 확인 → 476 passed (18-7 그대로)
2. spec 분석 → 18-1~18-7 신규 모듈 17개 누락 발견 (rag/, knowledge/, vector/, health)
3. spec hidden imports 에 17개 추가 (체크리스트 §16 "오타/누락만 허용" 정합)
4. test_pyinstaller_hidden_imports.py 작성 (53 tests) — 1차 1 fail (정규식이 datas 의 파일 경로 오인) → 정규식 필터 추가 → 53/53 통과
5. 전체 pytest 재실행 → 529 passed (회귀 0)
6. ruff 1 import-order 경고 → `--fix` → 통과

## 8. 5회 실패 여부

**아니오.** 1회차 통과.

## 9. 운영 DB 보호 검사 결과

```
$ venv/Scripts/python.exe scripts/check_db_path.py
DOSU_DB_PATH 환경변수 : (없음)
APPDATA 환경변수      : C:\Users\user\AppData\Roaming
결정된 DB 경로        : C:\Users\user\AppData\Roaming\도수치료예약\clinic.db

[INFO] 운영 DB 경로가 감지되었습니다.
       (테스트 중에는 이 경로가 보이면 안 됩니다 — conftest.py 를 확인하세요.)
```

- 단독 실행 시 운영 경로 표시 (의도된 INFO).
- 테스트 중 격리는 conftest 4단계 격리 + 다수 테스트 (`test_*_does_not_use_operational_db`) 통과.

## 10. spec hidden imports 변경 (18-8)

### 추가된 17개 모듈 (체크리스트 §16 "오타/누락만 허용" 정합)

| 카테고리 | 추가된 모듈 |
|---|---|
| 18-7 admin status | `app.services.ai.health` |
| 18-1 RAG 골격 | `app.services.ai.rag`, `app.services.ai.rag.schemas`, `app.services.ai.rag.prompts`, `app.services.ai.rag.safety`, `app.services.ai.rag.retriever`, `app.services.ai.rag.pipeline` |
| 18-3/18-4 knowledge | `app.services.ai.knowledge`, `app.services.ai.knowledge.loader`, `app.services.ai.knowledge.normalizer`, `app.services.ai.knowledge.chunker`, `app.services.ai.knowledge.keyword_index`, `app.services.ai.knowledge.indexer` |
| 18-5 vector | `app.services.ai.vector`, `app.services.ai.vector.embeddings`, `app.services.ai.vector.store`, `app.services.ai.vector.similarity` |
| 18-6 hybrid | `app.services.ai.rag.reranker`, `app.services.ai.rag.confidence` |

**근거**: 일부 모듈 (vector, reranker, confidence 등) 이 lazy import 라 PyInstaller
자동 발견에서 누락 위험. 기존 패턴 (line 31~50) 과 동일한 형식으로 명시 등록.
구조 변경 0 — 항목 추가만.

## 11. PyInstaller 빌드 + Smoke 결과 ✅

✅ **사용자 옵션 A 승인 후 빌드 + smoke 완료** (2026-05-02 18:01)

### 빌드 실행 명령 (Codex 권고 우회 방식)
```bash
rm -rf build dist/도수치료예약  # 기존 ZIP 보존
venv/Scripts/python.exe -m PyInstaller --noconfirm dosu_clinic.spec
```

### 빌드 결과
- exit code: **0**
- exe 산출물: `dist/도수치료예약/도수치료예약.exe`
- Modify 시각: **2026-05-02 18:01:35** (18-8 변경 반영본)
- Size: **14,915,945 bytes ≈ 14.9MB**
- spec post-build: `[spec] migration auto-register: 13 modules` + `updater.bat → dist/도수치료예약/`

### `_internal/` 동봉 검증 ✅
- knowledge/manuals/ 6개 .md (sms_compose/no_therapist/munjanara_error/backup/therapist_leave/ai_settings)
- knowledge/sms_guides/ 4개 .md (tone_confirm/noshow/reminder/reschedule)
- app/templates/ (main/base/setup/server_info.html)
- app/static/css/app.css
- updater.bat (루트 배치)
- m001~m013 마이그레이션 — PYZ archive 에 포함 (file system 미노출이 정상)

### exe smoke 검증 ✅ (격리 APPDATA `/tmp/dosu_smoke_appdata`)
| 엔드포인트 | 결과 |
|---|---|
| `/api/ai/health/public` (no auth) | 200, 4키 정확 (enabled/ready/provider/api_key_set) |
| `/api/admin/login` (admin1234) | 200, 토큰 발급 |
| `/api/ai/health` (admin) | 200, 9키 + `knowledge_doc_count=10` |
| `/api/ai/status` (18-7 신규 admin) | 200, 9 top-level 키 + `ai_mode=local_only` + `search_mode=keyword` + `vector_status.reason=vector_disabled` + `prompt_versions={"manual_qa.system":"v1"}` + api_key/api_key_masked 키 부재 |
| `/api/ai/manual/search` (한글 "백업" + 영어 "backup") | 200, `manuals/backup.md` 매칭 |

→ 8000 포트 listen 까지 2초, 모든 엔드포인트 정상 응답.

### 18-1~18-7 신규 모듈 런타임 import 입증 ✅
`/api/ai/status` 정상 응답 = 다음 import 모두 성공:
- `app.services.ai.health` (18-7)
- `app.services.ai.rag.{prompts, schemas, retriever, pipeline, reranker, confidence}` (18-1~18-6)
- `app.services.ai.knowledge.{loader, keyword_index, ...}` (18-3/18-4)
- `app.services.ai.vector.*` (18-5)

### 운영 DB 보호 ✅
- APPDATA 격리 (`/tmp/dosu_smoke_appdata`) — 사용자 운영 DB 미접근
- exe 가 임시 APPDATA 에 새 clinic.db 생성 + init_db() m001~m013 실행

→ 상세는 `reports/ai_dev_loop/18-8_build_smoke.md` 참조.

## 12. 남은 위험 요소 (빌드 + smoke 완료 후)

| 항목 | 시점 | 비고 |
|---|---|---|
| ~~PyInstaller 실제 빌드~~ | ✅ 완료 (2026-05-02 18:01) | exit 0, 14.9MB |
| ~~빌드 산출물 실행 smoke~~ | ✅ 완료 | 5개 엔드포인트 모두 통과 |
| **운영 환경 smoke** | 사용자 환경 | 실제 외부 API 키 등록 후 manual_ask 1회 (외부 LLM 호출) |
| **APP_VERSION 갱신** | 사용자 결정 | 1.3.3 → 1.4.0 (minor) 권장 — `app/config.py` |
| **CHANGELOG.txt / VERSION.txt / versions/INDEX.txt 갱신** | 사용자 결정 | 18-0~18-8 변경사항 정리 |
| **ZIP 패키징** | 사용자 결정 | `dosu_clinic_v1.4.0_<date>.zip` |
| **gh release create / manifest 푸시** | 사용자 결정 | clinic-updates repo |
| **Git 커밋 분리** | 사용자 결정 | 18-7 Codex 2회차 M-B + 18-8 누적 — 옵션 A (세션별) vs 옵션 B (단일 release) |
| **외부 OpenAIEmbeddingProvider 실제 구현** | 별도 세션 | 18-5/18-7 모두 slot 만 |
| **m014 (AiSetting hybrid_enabled / ai_mode 컬럼)** | 별도 세션 | 18-7 자동 파생으로 갈음 |
| **main.html UI 통합** | 별도 UI 세션 | 18-7 정책 (API 만) |
| **Reindex 버튼** | 별도 세션 | 18-7 정책 |
| **Codex 환경 tmp_path 권한 이슈** | Codex 환경 | 코드 무관 — Claude Code 환경에서는 100% 통과 |

## 13. 다음 단계 — 배포 절차 (사용자 결정)

본 18-8 세션의 코드/테스트/빌드/smoke 단계는 **모두 완료**. 이후는 배포 절차로 사용자 결정:

**옵션 1**: 즉시 v1.4.0 배포
1. `app/config.py` APP_VERSION 갱신 (1.3.3 → 1.4.0)
2. CHANGELOG.txt / VERSION.txt / versions/INDEX.txt 갱신
3. ZIP 패키징 (`dist/dosu_clinic_v1.4.0_20260502.zip`)
4. `gh release create` + `clinic-updates` repo 에 manifest.json/README.md 푸시
5. `versions/v1.4.0/` 백업 폴더 생성

**옵션 2**: Git 커밋 정리 후 배포
- Codex 18-7 M-B + 18-8 누적 권고 — 18-0~18-8 변경 세션별 커밋 분리
- 그 후 v1.4.0 배포

**옵션 3**: 운영 환경 smoke 후 배포
- 사용자 환경에서 실제 외부 API 키로 manual_ask 1회 (외부 LLM 응답 정상 확인)
- 그 후 배포
