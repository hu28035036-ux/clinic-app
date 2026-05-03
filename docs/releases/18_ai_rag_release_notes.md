# 18 AI/RAG 릴리즈 노트

> 18-0 ~ 18-8 세션 묶음 (`ai-rag-v1-integration` 브랜치) 의 완료 기준점.
> 본 문서는 v1.4.0 (예정) 릴리즈의 주요 변경사항 요약이다. 코드 변경 0
> (18-F 문서 정리 세션). 자세한 절차/사고 이력은 `reports/ai_dev_loop/18-X_*.md` 참조.

## 메타

- 브랜치: `ai-rag-v1-integration`
- 베이스 버전: v1.3.3 (`app/config.py:APP_VERSION="1.3.3"`)
- 권장 다음 버전: **v1.4.0** (minor — RAG/Vector/Hybrid 옵션 도입, 응답 키 후방호환 보존)
- 코드 변경 누적: 18-0~18-8 (8개 세션) + 18-F 문서
- 신규 파일: ~70 (코드 + 테스트 + 하네스 + 리포트 + 문서)
- 기존 파일 diff: `app/routers/ai.py` (+42줄), `app/models/models.py` (+123줄), `app/services/ai/manual_qa.py` (-298줄 wrapper 분리), `tests/conftest.py` (+132줄), `dosu_clinic.spec` (hidden imports 17개 추가)

## 1. 세션별 요약

### 18-0 RAG/Safety 하네스 + 전체 하네스 최소 버전
- 외부 LLM/Embedding 호출 차단 layer 도입 (`tests/conftest.py:_block_sdk_modules`)
- FakeProvider / FakeEmbeddingProvider 표준화 (`len(provider.calls)` 컨벤션)
- 4단계 격리 (APPDATA / DOSU_DB_PATH / 워커 무력화 / SDK 차단)
- 기본 회귀 하네스 (`test_full_harness.py`, `test_rag_pipeline.py`, `test_rag_safety.py`, `test_local_only_mode.py`)

### 18-1 RAG/Knowledge/Vector 폴더 구조 생성
- `app/services/ai/rag/` 신규 패키지 (schemas/prompts/safety/retriever/pipeline 골격)
- `Source`/`Document`/`Chunk`/`Answer` dataclass — v1.3.3 응답 키 1:1
- 23개 reason_code 표준화 (`docs/ai_rag_error_codes.md`)
- `manual_qa._MANUAL_SYSTEM_PROMPT` → `rag.prompts.PROMPTS["manual_qa.system"]["v1"]` 단일 진실원천

### 18-2 기존 keyword RAG 구조 분리
- `app/services/rag/search.py` → `app/services/ai/rag/{retriever,pipeline}.py` + `app/services/ai/knowledge/{loader,keyword_index}.py`
- `manual_qa.py` 가 wrapper 로 축소 (~80줄). v1.3.3 import 경로/시그니처/응답 9키 100% 보존
- 신규 reason_code 6개 추가 (총 29개)

### 18-3 Chunker 구현
- `app/services/ai/knowledge/{chunker,normalizer}.py` — 마크다운 헤딩 기반 청킹
- `Chunk` dataclass (doc_id/source_path/category/title/heading/section_path/chunk_index/content/content_hash/...)
- 35 tests — heading 트리, 한국어 normalize, 결정성, content_hash 안정성

### 18-4 knowledge_chunks DB / reindex (m012)
- `app/migrations/m012_knowledge_chunks.py` — `knowledge_chunks` + `knowledge_index_runs` 테이블
- `app/services/ai/knowledge/indexer.py` — `reindex_all` (lock + per-doc commit + DELETE 금지 정책)
- 24 tests — 부분 실패 보존, content_hash skip, 동시 실행 lock

### 18-5 Vector / Embedding 도입
- `app/migrations/m013_knowledge_vectors.py` — `knowledge_vectors` 테이블 (UNIQUE chunk_id+provider+model)
- `app/services/ai/vector/{embeddings,store,similarity}.py` — `EmbeddingProvider` 추상 + `FakeEmbeddingProvider` + cosine top_k
- 차단 우선순위 factory: local_only > disabled > api_key_missing > sdk_missing
- 36 tests — content_hash skip, dimension mismatch 안전 실패, vector_disabled fallback

### 18-6 Hybrid Retriever (α/β + cache + LLM 게이트)
- `app/services/ai/rag/{reranker,confidence}.py` 신규
- `hybrid_retrieve()` — keyword + (옵션) vector 결합. 기본 OFF (`AI_RAG_HYBRID_ENABLED=false`)
- max-normalize + α/β 가중합 + chunk_id/source_path dedup
- `should_call_llm()` 단일 진실원천 — no_sources/low_confidence/local_only/pii/provider_disabled 차단
- vector 실패 → keyword fallback (검색 중단 0)
- 61 tests — reranker 단위 11 + confidence 단위 13 + integration 16 + 모드별 15 + 회귀 6

### 18-7 UI / 관리자 상태 화면 (API)
- `app/services/ai/health.py` — read-only 상태 집계 (~340줄)
- `GET /api/ai/status` (admin) — 9 top-level 키:
  `ai_mode / search_mode / version / ai_settings / vector_status / external_api / knowledge / prompt_versions / recent_ai_logs`
- API key 평문/마스킹/`api_key_masked` 키 모두 응답 부재 (`api_key_set` boolean 만)
- `recent_ai_logs.recent[].error_detail` PII 마스킹 (`pii.scan` + 200자 cap, Codex M-1 후속)
- 66 tests — health unit 37 + contract regression 9 + admin smoke 14 + 6 PII tests
- main.html UI 미수정 (사용자 정책 — API 만)

### 18-8 전체 회귀 + PyInstaller 빌드 + Smoke
- `dosu_clinic.spec` — 18-1~18-7 신규 모듈 17개 hidden imports 추가 (체크리스트 §16 "오타/누락만 허용")
- `tests/test_pyinstaller_hidden_imports.py` — 53 tests (spec 파싱 + 모듈 import + data files + migrations)
- PyInstaller 빌드: exit 0, **14.9MB exe (2026-05-02 18:01:35)**
- 격리 APPDATA exe smoke — 5개 엔드포인트 (health/public, admin login, health admin, status, manual/search) 모두 통과
- 한글/영어 manual/search 정확 매칭

## 2. 누적 테스트 결과

| 회차 | passed | 회귀 |
|---|---|---|
| 18-0 baseline | ~150 | — |
| 18-1 | ~190 | 0 |
| 18-2 | ~210 | 0 |
| 18-3 | ~245 | 0 |
| 18-4 | 269 | 0 |
| 18-5 | 349 | 0 |
| 18-6 | 410 | 0 |
| 18-7 | 476 | 0 |
| **18-8** | **529 passed, 1 skipped, 7 xfailed** | **0** |

ruff: All checks passed!
check_db_path: OK
PyInstaller hidden import 사전 검증: 53 passed

## 3. 주요 아키텍처 결정 (Local-First 원칙)

### 3-1. 외부 API 토큰 최소화 구조

호출 게이트 다층 (`should_call_llm`):
1. `provider_disabled` (AiSetting.enabled=False / api_key 없음 / model 없음)
2. `pii_detected` (외부 전송 직전 차단)
3. `local_only` 모드
4. `no_sources` (RAG 결과 0건 → 할루시네이션 위험)
5. `low_confidence` (final_score < 0.3)
6. 통과 시에만 LLM 1회 호출

각 게이트는 독립 reason_code 발급. `manual_qa._rag_search` → `top_score < 2` 면 LLM 호출 0 (v1.3.3 정책 그대로).

### 3-2. 응답 9키 후방호환

`/api/ai/manual/{search,ask}` v1.3.3 응답 키 100% 보존:
- `manual/search`: `sources / masked_question / top_score` (3키)
- `manual/ask`: `answer / sources / confidence / not_found / blocked / blocked_reason / guard_hits / top_score / masked_question` (9키)
- `sources[]` 항목: `title / path / snippet` (3키)
- 신규 optional 키 5개 (`reason_code` / `llm_called` / `embedding_called` / `ai_mode` / `prompt_version`) — **18-8 시점 응답에 미도입** (별도 m014 + 라우터 wire-in 세션)

### 3-3. 외부 API 실연동은 선택/후속

- **18-0~18-8 시점**: FakeProvider / FakeEmbeddingProvider 만 사용. SDK slot 만 존재.
- **운영 환경**: 사용자가 `AiSetting.enabled=True` + `api_key` + `model` 설정 시 실제 OpenAI/Anthropic LLM 1회 호출 가능 (manual_ask 게이트 통과 케이스).
- **Embedding 외부 연동**: 18-5/18-7 모두 slot 만. 실제 OpenAIEmbeddingProvider 구현은 별도 세션.
- **Vector / Hybrid path**: m014 (`AiSetting.AI_RAG_HYBRID_ENABLED` 컬럼) 도입 + 라우터 wire-in 시점에 활성. 18-8 시점은 코드 path 만 존재.

### 3-4. 관리자 상태 API

`GET /api/ai/status` 가 read-only 집계 단일 진입점:
- AI 모드 자동 파생 (enabled/api_key/model 조합)
- 검색 모드 (현재 항상 "keyword" — pipeline 미통합)
- knowledge 카운트 (documents/chunks/vectors)
- vector_status (m014 미도입 → 항상 "vector_disabled")
- external_api 가용성 (sdk_installed + key + enabled)
- 최근 24시간 AI 로그 요약 (PII 마스킹)
- prompt_versions
- 폴링 안전 (AiUsageLog 미기록)

## 4. PyInstaller 빌드 검증 결과

```
명령: venv/Scripts/python.exe -m PyInstaller --noconfirm dosu_clinic.spec
exit: 0
산출물: dist/도수치료예약/도수치료예약.exe (14,915,945 bytes, 2026-05-02 18:01:35)
spec post-build:
  - migration auto-register: 13 modules (m001~m013)
  - updater.bat → dist/도수치료예약/ 루트 배치
```

`_internal/` 동봉 (Codex 18-8 권고 4):
- knowledge/manuals 6개 .md + knowledge/sms_guides 4개 .md
- app/templates 4개 .html + app/static/css/app.css
- m001~m013 마이그레이션 — PYZ archive 포함
- anthropic / certifi / openai 등 SDK 데이터 파일

격리 APPDATA exe smoke (Codex 18-8 권고 3):
- listen ready: 2초
- 5개 엔드포인트 모두 200 + 응답 키 정확
- 한글/영어 manual/search 매칭 정확
- API key / api_key_masked 키 응답 부재 입증
- 운영 DB 미접근 (APPDATA 격리)

## 5. 수정 금지 / 후방호환 보장

| 항목 | 상태 |
|---|---|
| `/api/ai/manual/{search,ask}` 응답 9키/3키 | 100% 보존 |
| `/api/ai/health` admin 9키 / `/api/ai/health/public` 4키 | 100% 보존 |
| `manual_qa.ask_manual_question(provider_override=)` 시그니처 | 보존 |
| `pii.scan(text)` 반환형 | 보존 |
| `AiSetting`/`AiUsageLog` 기존 컬럼 | 보존 |
| `app/migrations/m001~m011` | diff 0 (m012/m013 만 신규) |
| 기존 SMS AI / 휴무 AI 동작 | 보존 (action_leave/sms_draft 무수정) |
| `pyproject.toml` per-file-ignores | 보존 |
| `requirements.txt` | 무수정 |

## 6. 변경 파일 (누적 + 신규)

### 신규 코드 (~30 파일)
- `app/services/ai/health.py` (18-7)
- `app/services/ai/rag/{schemas,prompts,safety,retriever,pipeline,reranker,confidence}.py` (18-1~18-6)
- `app/services/ai/knowledge/{loader,normalizer,chunker,keyword_index,indexer,__init__}.py` (18-2~18-4)
- `app/services/ai/vector/{embeddings,store,similarity,__init__}.py` (18-5)
- `app/migrations/m012_knowledge_chunks.py`, `m013_knowledge_vectors.py`

### 신규 테스트 (~14 파일, 379 신규 tests)
- 18-0: `test_rag_pipeline.py`, `test_rag_safety.py`, `test_local_only_mode.py`, `test_full_harness.py`, `test_ai_full_harness.py`
- 18-1~18-2: `test_ai_manual_rag_harness.py`, `test_ai_manual_rag_contract.py`, `test_ai_safety_harness.py`
- 18-3: `test_ai_chunker_harness.py`
- 18-4: `test_ai_reindex_harness.py`
- 18-5: `test_ai_vector_harness.py`
- 18-6: `test_hybrid_retriever.py`, `test_ai_assist_mode.py`
- 18-7: `test_ai_health_status.py`, `test_ai_contract_manual.py`, `test_admin_ui_smoke.py`
- 18-8: `test_pyinstaller_hidden_imports.py`

### 신규 하네스 helpers (~8 파일)
- `tests/harness/{contract,fake_provider,rag_harness,safety_harness,chunk_harness,reindex_harness,vector_harness,hybrid_harness}.py`

### 신규 문서 (~25 파일)
- `docs/AI_WORKING_RULES.md`, `docs/ai_code_session_protocol.md`, `docs/ai_docs_index.md`
- `docs/ai_rag_{architecture,migration,test,rollout,decision_record,error_codes,quality_eval,current_state}_plan.md`
- `docs/ai_harness_overview.md`, `docs/ai_codex_review_protocol.md`
- `docs/harnesses/{full,rag,safety,chunk,vector,hybrid,component}_harness_*.md`
- `docs/checklists/18-0_*.md` ~ `18-8_*.md`
- `docs/migrations_rollback/m012_rollback.sql`, `m013_rollback.sql`

### 수정 (4 파일)
- `app/routers/ai.py` — `/api/ai/status` 엔드포인트 추가 (+42줄)
- `app/services/ai/manual_qa.py` — wrapper 로 축소 (-298줄, rag.pipeline 위임)
- `app/models/models.py` — KnowledgeChunk / KnowledgeIndexRun / KnowledgeVector ORM (+123줄)
- `tests/conftest.py` — FakeProvider + SDK 차단 + 격리 강화 (+132줄)
- `dosu_clinic.spec` — 18-1~18-7 신규 모듈 17개 hidden imports 추가
- `.gitignore` — 1줄 (이전 세션)

## 7. Codex 검증 이력

| 세션 | 1회차 | 2회차 |
|---|---|---|
| 18-0 ~ 18-3 | 통과 | — |
| 18-4 | 통과 + 권고 (T-1/T-2) | 권고 반영 + 통과 |
| 18-5 | 통과 + M-1 (spec 변경) | revert 후 통과 |
| 18-6 | 통과 | — |
| 18-7 | M-1 (PII) + M-2 (작업트리) + 사소한 개선 + 테스트 부족 | 모두 해결 + 통과 |
| 18-8 | 치명적 (빌드 미수행) | 빌드 + smoke 완료 후 사용자 결정 단계로 종료 |

## 8. 다음 단계

### 8-1. v1.4.0 배포 (사용자 결정)
1. APP_VERSION 갱신 (1.3.3 → 1.4.0) — `app/config.py`
2. CHANGELOG.txt / VERSION.txt / `versions/INDEX.txt` 갱신
3. ZIP 패키징 (`dosu_clinic_v1.4.0_20260502.zip`)
4. `gh release create` + `clinic-updates` repo 에 manifest.json/README.md 푸시
5. `versions/v1.4.0/` 백업 폴더 생성

자세한 절차: `CLAUDE.md` 배포 규칙 + `docs/releases/18_ai_rag_final_checklist.md`.

### 8-2. 19-P 단위화 리팩토링 진입
v1.4.0 안정화 후 19-P (예약/휴무/문자/AI/RAG/통계 모듈 분리). 진입 기준점은
`docs/refactor/19_refactor_entry_notes.md`.

### 8-3. 후속 별도 세션 (우선순위 LOW)
- m014: AiSetting `ai_mode` / `AI_RAG_HYBRID_ENABLED` / `alpha`/`beta` 컬럼
- 외부 OpenAIEmbeddingProvider 실제 구현 (현재 slot 만)
- 응답 optional 5키 (reason_code/llm_called/embedding_called/ai_mode/prompt_version) 노출
- main.html UI 통합 (Reindex 버튼 / vector 토글)
- pipeline.run_manual_ask 가 hybrid_retrieve 사용하도록 통합
