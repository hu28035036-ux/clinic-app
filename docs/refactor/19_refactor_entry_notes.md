# 19-P 단위화 리팩토링 진입 기준 노트

> 18-0~18-8 (AI/RAG v1) 안정화 완료 후 19-P (예약/휴무/문자/AI/RAG/통계 모듈 단위화 리팩토링)
> 진입 시점에 반드시 확인할 기준점.

## 1. 리팩토링 진입 전제

### 1-1. v1.4.0 안정화 단계 통과
- [ ] v1.4.0 정식 배포 완료
- [ ] 운영 환경 1주일 이상 안정 동작 확인
- [ ] 사용자 사고 보고 0
- [ ] AI 비용 정상 범위 (사용자 한도 내)

### 1-2. 기준 테스트 통과 (회귀 baseline)
- [ ] `pytest tests` — **529 passed, 1 skipped, 7 xfailed** (18-8 baseline)
- [ ] `ruff check app tests scripts` — All checks passed
- [ ] `scripts/check_db_path.py` — OK
- [ ] PyInstaller 빌드 — exit 0, exe 정상 실행

### 1-3. Git 작업트리 정리
- [ ] 18-0~18-8 변경 커밋 완료 (옵션 A 세션별 또는 옵션 B 단일 release)
- [ ] `ai-rag-v1-integration` 브랜치 → `main` 머지 완료
- [ ] 19-P 작업용 별도 브랜치 생성 (예: `19-modular-refactor`)

## 2. 안정화 영역 — 건드리면 안 되는 곳

### 2-1. 응답 키 후방호환 (절대 변경 X)

| 엔드포인트 | 키 셋 |
|---|---|
| `/api/ai/manual/search` | `sources / masked_question / top_score` (3키) |
| `/api/ai/manual/ask` | `answer / sources / confidence / not_found / blocked / blocked_reason / guard_hits / top_score / masked_question` (9키) |
| `sources[]` 항목 | `title / path / snippet` (3키) |
| `/api/ai/health` admin | `enabled / ready / provider / api_key_set / model / sdk_installed / sdk_errors / knowledge_doc_count / version` (9키) |
| `/api/ai/health/public` | `enabled / ready / provider / api_key_set` (4키) |
| `/api/ai/status` (18-7) | top-level 9키 (ai_mode/search_mode/version/ai_settings/vector_status/external_api/knowledge/prompt_versions/recent_ai_logs) |

→ 추가만 허용. **이름 변경 / 제거 / 타입 변경 절대 금지**.

### 2-2. DB 마이그레이션 (m001~m013)

- m001~m013 파일 diff 0 (이미 배포된 마이그레이션은 수정 금지)
- 신규 마이그레이션은 m014 부터
- m012/m013 idempotent 정책 유지

### 2-3. 외부 API 차단 layer

- `tests/conftest.py:_block_sdk_modules` — openai/anthropic SDK 차단 무수정
- FakeProvider / FakeEmbeddingProvider 컨벤션 (`len(provider.calls)`) 유지
- 4단계 격리 (APPDATA / DOSU_DB_PATH / 워커 / SDK) 약화 금지

### 2-4. 핵심 정책 상수

| 상수 | 위치 | 값 |
|---|---|---|
| `LOW_SCORE_THRESHOLD` | `app/services/ai/rag/pipeline.py` | 2 (manual_qa keyword score) |
| `HIGH_THRESHOLD` / `LOW_THRESHOLD` | `app/services/ai/rag/confidence.py` | 0.7 / 0.3 (hybrid final_score) |
| `LLM_CALL_THRESHOLD` | 동상 | 0.3 (= LOW_THRESHOLD) |
| `QUERY_MIN_CHARS` | `app/services/ai/vector/embeddings.py` | 2 (짧은 query 차단) |
| `ERROR_DETAIL_DISPLAY_LIMIT` | `app/services/ai/health.py` | 200 (recent_ai_logs.error_detail cap) |
| `DEFAULT_RECENT_HOURS` / `DEFAULT_RECENT_LIMIT` | 동상 | 24 / 5 |

→ 임계 변경은 별도 결정 + eval 측정 후.

### 2-5. PyInstaller spec 핵심 정책

- `collect_submodules` 실패 가드 (`raise RuntimeError`) 유지
- excludes (tkinter/matplotlib/numpy/pandas/PyQt5/6) 유지
- console=False 유지
- 마이그레이션 자동 글롭 (`m*_*.py`) 유지
- updater.bat post-build 복사 유지

## 3. 리팩토링 전 반드시 통과해야 할 하네스

본 하네스들은 19-P 진입 시점 + 진입 후 매 변경마다 통과 검증:

### 3-1. AI/RAG 하네스 (18-0~18-7)

| 하네스 | 파일 | 테스트 수 |
|---|---|---|
| Full | `tests/test_full_harness.py` + `test_ai_full_harness.py` | 17 |
| RAG pipeline | `tests/test_rag_pipeline.py` | 5 |
| RAG safety | `tests/test_rag_safety.py` + `test_ai_safety_harness.py` | 18 |
| Manual RAG | `tests/test_ai_manual_rag_harness.py` | 18 |
| Contract (응답 키) | `tests/test_ai_manual_rag_contract.py` + `test_ai_contract_manual.py` | 18 |
| Local-only mode | `tests/test_local_only_mode.py` | 4 |
| Chunker | `tests/test_ai_chunker_harness.py` | 35 |
| Reindex | `tests/test_ai_reindex_harness.py` | 24 |
| Vector | `tests/test_ai_vector_harness.py` | 36 |
| Hybrid | `tests/test_hybrid_retriever.py` | 46 |
| AI mode | `tests/test_ai_assist_mode.py` | 15 |
| Admin status | `tests/test_ai_health_status.py` + `test_admin_ui_smoke.py` | 57 |
| **합계 (AI/RAG)** | — | **293** |

### 3-2. 기존 AI 하네스 (v1.3.3 이전)

| 하네스 | 파일 | 테스트 수 |
|---|---|---|
| SMS validate | `test_ai_sms_validate.py` | 11 |
| SMS draft | `test_ai_sms_draft.py` + `test_ai_sms_draft_hallucination.py` | ~30 |
| 휴무 자연어 | `test_ai_action_leave.py` | ~30 |
| AI logging | `test_ai_logging.py` | ~10 |
| AI hallucination | `test_ai_hallucination.py` | ~5 |
| AI manual_qa | `test_ai_manual_qa.py` | ~10 |
| AI health public | `test_ai_health_public.py` | 4 |
| **합계 (기존 AI)** | — | **~98** |

### 3-3. 비-AI 기능 하네스

| 하네스 | 파일 | 테스트 수 |
|---|---|---|
| 예약 규칙 | `test_appointment_rules.py` | ~10 |
| 직원/치료사 | `test_employee_*.py` (4 파일) | ~20 |
| 통계 | `test_stats_counts.py` | ~10 |
| 휴무 | `test_therapist_leave.py` | ~5 |
| 관리자 인증 | `test_admin_auth_required.py` | ~15 |
| DB 복원 | `test_db_restore_safety.py` | ~5 |
| Graceful shutdown | `test_graceful_shutdown.py` | 4 |
| 마이그레이션 spec | `test_migration_spec_discovery.py` | 4 |
| smoke | `test_smoke.py` | 8 |
| SMS 마스킹 | `test_sms_secret_masking.py` | 6 |
| Update log | `test_update_log.py` | 6 |
| Updater | `test_updater_invocation.py` | 4 |
| **합계 (비-AI)** | — | **~85** (1 skipped, 7 xfailed) |

### 3-4. PyInstaller 사전 검증

| 하네스 | 파일 | 테스트 수 |
|---|---|---|
| Hidden imports | `test_pyinstaller_hidden_imports.py` | 53 |

### 3-5. 종합

**전체**: **529 passed, 1 skipped, 7 xfailed** (18-8 baseline).

→ 19-P 진입 후 단일 변경마다 위 전체 회귀 통과 필수.

## 4. 모듈 분리 시 주의점 (단위화 리팩토링 가이드)

### 4-1. 예약 모듈

**현재 위치**: `app/routers/api.py` (~3800줄, 다수 도메인 혼재)

**분리 후보**:
- `app/routers/appointments.py` — POST/PATCH/DELETE 예약
- `app/services/appointments.py` — 예약 충돌/제약 검사 비즈니스 로직
- `app/services/treatments.py` — 치료항목/카운터/인센티브 (manual60 정책 보존 — `count_increment=1`)

**주의**:
- ⚠️ `manual60` 의 `count_increment=2` 로 되돌리지 않을 것 (CLAUDE.md 명시)
- ⚠️ `appointments` 응답 스키마 후방호환 (프론트 사용 키 확인)
- ⚠️ 예약 잠금 / TOCTOU 정책 보존 (`tests/test_appointment_rules.py`)

### 4-2. 휴무 모듈

**현재 위치**: `app/routers/api.py` + `app/services/ai/action_leave.py`

**분리 후보**:
- `app/routers/leaves.py` — POST/PATCH/DELETE employee_leaves
- `app/services/leaves.py` — `_upsert_employee_leave_core` 단일 진실원천

**주의**:
- ⚠️ AI 휴무 등록 (`/api/ai/action/{parse,preview,execute}`) 의 HMAC 토큰 + TOCTOU 보존
- ⚠️ `test_employee_leave_unique.py` + `test_ai_action_leave.py` 통과 유지
- ⚠️ `EmployeeLeave.kind` (휴무/연차/월차) 정책 보존

### 4-3. 문자 (SMS) 모듈

**현재 위치**: `app/routers/api.py` + `app/services/ai/sms_draft.py` + `app/services/ai/validators.py`

**분리 후보**:
- `app/routers/sms.py` — POST 발송 / draft / validate
- `app/services/sms/{send,draft,validate}.py`
- `app/services/sms/munjanara_client.py` — 외부 SMS API client

**주의**:
- ⚠️ `tests/test_ai_sms_*.py` 통과 유지 (validate / draft / hallucination)
- ⚠️ SmsSetting.munjanara_key 마스킹 패턴 (`SmsSetting._serialize`) 보존
- ⚠️ AI 가 직접 발송 금지 정책 (`AiUsageLog.sms_sent=0` 항상)

### 4-4. AI / RAG 모듈

**현재 위치**: `app/routers/ai.py` (888줄) + `app/services/ai/{...}` + `app/services/ai/{rag,knowledge,vector}/`

**현재 구조 (18-0~18-8 결과)**:
```
app/services/ai/
├── provider.py / openai_client.py / anthropic_client.py
├── pii.py / prompts.py / validators.py / ai_logging.py
├── sms_draft.py / manual_qa.py / action_leave.py / date_resolver.py
├── health.py (18-7)
├── rag/
│   ├── schemas.py / prompts.py / safety.py
│   ├── retriever.py / pipeline.py
│   ├── reranker.py / confidence.py (18-6)
├── knowledge/
│   ├── loader.py / normalizer.py / chunker.py
│   ├── keyword_index.py / indexer.py
└── vector/
    ├── embeddings.py / store.py / similarity.py
```

**분리 후보 (19-P)**:
- `app/routers/ai/{health,settings,manual,sms,action,status}.py` — 라우터를 도메인별로
- `app/services/ai/__init__.py` 가 facade 역할 (기존 import 경로 보존)

**주의**:
- ⚠️ **manual_qa wrapper 시그니처 보존** — `ask_manual_question(db, question, *, provider_override=)` 키워드 인자
- ⚠️ rag.pipeline 의 `LOW_SCORE_THRESHOLD=2` 보존 (manual_qa wrapper 가 export)
- ⚠️ rag.prompts.PROMPTS["manual_qa.system"]["v1"] 단일 진실원천 유지
- ⚠️ vector 패키지 import 가 lazy (knowledge/indexer.py:_embed_chunks_into_vectors) — 분리 시 import 위치 변경 시 vector 패키지 부재 환경 호환 깨짐 위험
- ⚠️ pii.scan(text).cleaned 반환형 보존
- ⚠️ FakeProvider / FakeEmbeddingProvider 호출 관찰 컨벤션 유지

### 4-5. 통계 모듈

**현재 위치**: `app/routers/api.py` 일부 + `app/services/seed.py` 일부

**분리 후보**:
- `app/routers/stats.py` — GET 통계 endpoints
- `app/services/stats.py` — 비즈니스 로직 (예약/매출/카운터 집계)

**주의**:
- ⚠️ `tests/test_stats_counts.py` 통과 유지
- ⚠️ 카운트 정책 (manual60 = 1, ESWT = 0 등) 보존

## 5. 리팩토링 절차 (1 변경당)

```
1. 변경 전 baseline pytest 통과 확인
2. 단일 모듈 분리 (예: appointments.py 만)
3. 변경 후 pytest 전체 재실행
4. 회귀 0 확인 (응답 키 100% 보존)
5. ruff + check_db_path 통과
6. PyInstaller hidden imports 갱신 (분리된 모듈 명시 등록)
7. test_pyinstaller_hidden_imports.py 53 tests 통과
8. 커밋 (단일 모듈 분리 = 단일 커밋)
```

→ 5회 루프 정책 (`docs/AI_WORKING_RULES.md` §3) 준수.

## 6. 19-P 단위화 리팩토링 비-목표 (Out of Scope)

본 리팩토링은 **모듈 단위 분리만** — 다음은 별도 세션:

- ❌ DB 스키마 변경 (m014+ 는 별도 세션)
- ❌ 응답 키 변경 (제거/이름변경 절대 X)
- ❌ AI/RAG 알고리즘 변경 (reranker/confidence/retriever 로직 무수정)
- ❌ 외부 API 실연동 추가 (별도 세션)
- ❌ UI / main.html 통합 (별도 UI 세션)
- ❌ 신규 기능 추가 (예약/휴무/문자 정책 변경 X)

## 7. 19-P 진입 후 매 세션 시작 시 확인

각 19-X 세션은 다음을 시작 시점에 확인:

1. `docs/AI_WORKING_RULES.md` (변경 없음 — 리팩토링도 동일 규칙 적용)
2. `docs/ai_code_session_protocol.md`
3. `docs/refactor/19_refactor_entry_notes.md` (본 문서 — 안정화 영역 + 하네스)
4. 직전 19-X 세션의 `latest_codex_review_request.md`
5. 본 세션의 분리 대상 모듈 + 의존성 분석

## 8. 19-P 종료 조건 (잠정)

19-P 세션 묶음 (예: 19-0 ~ 19-N) 종료 시:
- [ ] 모든 도메인 모듈 (예약/휴무/문자/AI/RAG/통계) 분리 완료
- [ ] `app/routers/api.py` 가 facade 또는 폐기
- [ ] 회귀 0 (529 passed 그대로 또는 +N 신규 분리 테스트)
- [ ] PyInstaller 빌드 + smoke 통과
- [ ] v1.5.0 (또는 v2.0.0) 배포 가능 상태

## 9. 19-P 시작 권장 순서 (제안)

1. **19-0**: 단위화 리팩토링 baseline + 하네스 강화 (통과 보호)
2. **19-1**: 통계 모듈 분리 (가장 간단, 의존성 적음)
3. **19-2**: 휴무 모듈 분리
4. **19-3**: 예약 모듈 분리 (가장 복잡, 다른 모듈이 의존)
5. **19-4**: 문자 (SMS) 모듈 분리
6. **19-5**: AI / RAG 라우터 분리 (`app/routers/ai/` 서브패키지)
7. **19-6**: facade / 의존성 정리
8. **19-7**: 회귀 + PyInstaller 검증
9. **19-8**: v1.5.0 (또는 v2.0.0) 릴리즈

→ 사용자 결정으로 순서/세션 수 조정 가능.

## 10. 종합

✅ **18-0~18-8 안정화 완료 후 19-P 진입 가능**.

⚠️ **본 문서의 §2 안정화 영역 + §3 하네스 통과는 19-P 진입 + 매 세션의 절대 조건**.

⏳ **사용자 결정**:
- v1.4.0 정식 배포 후 19-P 시작
- 또는 v1.4.x 패치 (m014/외부 API 실연동/UI 통합) 먼저 진행 후 19-P
