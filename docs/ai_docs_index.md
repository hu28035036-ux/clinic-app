# AI/RAG 문서 목차 (ai_docs_index)

> 모든 AI/RAG 작업 세션 시작 시 이 문서를 먼저 확인한다.
> 각 세션에서 필요한 문서 조합은 본 문서 §3에 정의되어 있다.

---

## 1. 문서 분류 및 역할

### 1-1. 핵심 규칙 / 절차 (모든 세션 공통)
| 문서 | 역할 | 읽는 시점 |
|---|---|---|
| `docs/AI_WORKING_RULES.md` | 코드 세션 핵심 규칙(1~2p) | 모든 코드 세션 시작 시 |
| `docs/ai_code_session_protocol.md` | 공통 작업 절차 + 5회 루프 + Codex 게이트 | 모든 코드 세션 시작 시 |
| `docs/ai_docs_index.md` (본 문서) | 문서 목차 + 세션별 조합 | 모든 코드 세션 시작 시 |

### 1-2. 현재 상태 스냅샷
| 문서 | 역할 | 읽는 시점 |
|---|---|---|
| `docs/ai_rag_current_state.md` | 현재 AI/RAG 구현 실측 스냅샷(버전·파일·표·엔드포인트·의존성) | 18-0, 그리고 새 세션 시작 시 변경 여부 확인 |

### 1-3. 아키텍처 / 마이그레이션 / 에러 코드 / 의사결정
| 문서 | 역할 | 읽는 시점 |
|---|---|---|
| `docs/ai_rag_architecture_plan.md` | 목표 RAG 아키텍처(전체 그림: Local Composer / Chunker / Vector / Pipeline) | 18-1 이후 모든 RAG 세션 |
| `docs/ai_rag_migration_plan.md` | 키워드 전용 → 벡터 도입까지의 마이그레이션 단계·DB 변경·롤백 | 마이그레이션·청커·벡터 세션 |
| `docs/ai_rag_error_codes.md` | RAG/AI 에러 코드 목록(local_only 차단·근거 부족·임베딩 실패 등) | 라우터/벡터/Composer 세션 |
| `docs/ai_rag_decision_record.md` | 왜 이런 구조를 선택했는지 ADR (local-first / SQLite / 5회 루프 등) | 설계 변경 검토 시 |
| `docs/ai_rag_rollout_plan.md` | 18-0~18-8 구현 순서·릴리스 단계·관리자 화면·권한 | 모든 코드 세션 시작 시 (해당 단계 확인) |
| `docs/ai_rag_quality_eval_plan.md` | RAG 답변 품질 평가 데이터셋·점수 기준·합격 기준 | 18-2/18-5/18-6 머지 직전 |

### 1-4. 테스트 / 하네스 / Codex 검증
| 문서 | 역할 | 읽는 시점 |
|---|---|---|
| `docs/ai_rag_test_plan.md` | RAG/AI 통합 테스트 시나리오 매트릭스 | 18-0 및 모든 RAG 세션 |
| `docs/ai_harness_overview.md` | 하네스 분리 원칙·외부 호출 차단·local_only 검증 원칙 | 모든 하네스 세션 시작 시 |
| `docs/ai_codex_review_protocol.md` | Codex 검증 프로토콜 (요청서 작성·전달 문구·검증 항목·판정) | 모든 코드 세션 종료 시 |
| `docs/harnesses/full_harness_plan.md` | 전체 통합·라우터·DB 격리·smoke | 18-0 및 18-8 |
| `docs/harnesses/rag_harness_plan.md` | RAG 검색·근거·degrade·LLM 호출 조건 | RAG 검색·답변 세션 |
| `docs/harnesses/safety_harness_plan.md` | PII·API 키·운영 DB 가드·할루시네이션 가드 | 모든 코드 세션 (RAG/Vector/Composer 포함) |
| `docs/harnesses/chunk_harness_plan.md` | 청킹 결정성·경계·메타데이터 하네스 | Chunker 세션 (18-3) |
| `docs/harnesses/vector_harness_plan.md` | 임베딩·인덱스·local_only 차단·degrade 하네스 | Vector/Embedding 세션 (18-5) |
| `docs/harnesses/hybrid_harness_plan.md` | keyword+vector 결합·정규화·fallback 하네스 | Hybrid 세션 (18-6) |
| `docs/harnesses/component_harness_matrix.md` | 컴포넌트×하네스 매트릭스 (Query/Intent/Knowledge/Retrieval/Confidence/Local Answer/Source/Cache/Observability/Contract) | 신규 컴포넌트 추가 시 |

### 1-5. 세션별 체크리스트
| 문서 | 역할 |
|---|---|
| `docs/checklists/18-0_rag_harness_checklist.md` | RAG/Safety 하네스 + 전체 하네스 최소 버전 |
| `docs/checklists/18-1_structure_refactor_checklist.md` | RAG/Knowledge/Vector 폴더 구조 생성 |
| `docs/checklists/18-2_keyword_rag_refactor_checklist.md` | 기존 keyword RAG 구조 분리 |
| `docs/checklists/18-3_chunker_checklist.md` | Chunker 구현 |
| `docs/checklists/18-4_db_reindex_checklist.md` | knowledge_chunks DB / reindex (m012) |
| `docs/checklists/18-5_vector_embedding_checklist.md` | Vector store / embedding (m013) |
| `docs/checklists/18-6_hybrid_retriever_checklist.md` | Hybrid retriever (α/β + cache) |
| `docs/checklists/18-7_admin_ui_checklist.md` | 라우터/UI 통합 + API 계약 테스트 |
| `docs/checklists/18-8_final_release_checklist.md` | 회귀 + PyInstaller 검증 + 배포 |

### 1-6. 세션 로그 / 리포트
| 위치 | 역할 |
|---|---|
| `reports/ai_dev_loop/latest_test_report.md` | 직전 세션 테스트 결과 |
| `reports/ai_dev_loop/latest_fix_summary.md` | 직전 세션 변경 요약 |
| `reports/ai_dev_loop/latest_failure_report.md` | 직전 세션 5회 실패 시 |
| `reports/ai_dev_loop/latest_codex_review_request.md` | 직전 세션 Codex 검증 요청서 |
| `reports/ai_dev_loop/{SESSION_NAME}_*.md` | 세션별 영구 보존본 |

---

## 2. 디렉토리 트리(목표)

```
docs/
├── AI_WORKING_RULES.md                    # 핵심 규칙 (1단계 작성)
├── ai_docs_index.md                       # 본 문서 (1단계 작성)
├── ai_code_session_protocol.md            # 세션 공통 절차 (1단계 작성)
├── ai_rag_current_state.md                # 2단계 작성 (현재 코드 스냅샷)
├── ai_rag_architecture_plan.md            # 2단계 작성 (목표 아키텍처)
├── ai_rag_migration_plan.md               # 2단계 작성 (DB/롤백/reindex)
├── ai_rag_test_plan.md                    # 2단계 작성 (테스트 매트릭스)
├── ai_rag_rollout_plan.md                 # 2단계 작성 (구현 순서/릴리스/UI/권한)
├── ai_rag_decision_record.md              # 2단계 작성 (ADR)
├── ai_rag_error_codes.md                  # 2단계 작성 (reason_code 표준)
├── ai_rag_quality_eval_plan.md            # 2단계 작성 (품질 평가)
├── ai_codex_review_protocol.md            # 2단계 작성 (Codex 검증 절차)
├── ai_harness_overview.md                 # 3단계 작성 (하네스 분리 원칙)
├── harnesses/
│   ├── full_harness_plan.md               # 3단계
│   ├── rag_harness_plan.md                # 3단계
│   ├── safety_harness_plan.md             # 3단계
│   ├── chunk_harness_plan.md              # 3단계
│   ├── vector_harness_plan.md             # 3단계
│   ├── hybrid_harness_plan.md             # 3단계
│   └── component_harness_matrix.md        # 3단계
└── checklists/
    ├── 18-0_rag_harness_checklist.md           # 3단계
    ├── 18-1_structure_refactor_checklist.md    # 3단계
    ├── 18-2_keyword_rag_refactor_checklist.md  # 3단계
    ├── 18-3_chunker_checklist.md               # 3단계
    ├── 18-4_db_reindex_checklist.md            # 3단계
    ├── 18-5_vector_embedding_checklist.md      # 3단계
    ├── 18-6_hybrid_retriever_checklist.md      # 3단계
    ├── 18-7_admin_ui_checklist.md              # 3단계
    └── 18-8_final_release_checklist.md         # 3단계

reports/
└── ai_dev_loop/
    ├── latest_test_report.md
    ├── latest_fix_summary.md
    ├── latest_failure_report.md
    ├── latest_codex_review_request.md
    ├── latest_codex_review_response.md     # Codex 작성
    └── {SESSION_NAME}_*.md
```

---

## 3. 코드 세션별 필수 확인 문서 조합

> **모든 코드 작성 세션 공통 베이스 (5개 — 통일 기준)**:
> 1. `docs/AI_WORKING_RULES.md`
> 2. `docs/ai_code_session_protocol.md`
> 3. `docs/ai_docs_index.md` (본 문서)
> 4. `docs/ai_rag_current_state.md`
> 5. 해당 세션 체크리스트 (`docs/checklists/18-X_*.md`)
>
> 아래 표는 **공통 베이스에 추가로** 읽어야 할 **세션별 추가 참조 문서**를 정의한다.
> 상세 설계 문서를 매 세션 모두 읽지 않는다. 필요 시점에만 참조.
> 절차 부속 문서(`ai_codex_review_protocol.md`, `ai_harness_overview.md`, `ai_rag_rollout_plan.md`)는 **각 세션 체크리스트에서 명시한 시점**에만 참조.

### 18-0 RAG/Safety 하네스 + 전체 하네스 최소 버전
- `docs/checklists/18-0_rag_harness_checklist.md`
- `docs/ai_rag_test_plan.md`
- `docs/harnesses/full_harness_plan.md`
- `docs/harnesses/rag_harness_plan.md`
- `docs/ai_rag_error_codes.md`

### 18-1 RAG/Knowledge/Vector 폴더 구조 생성
- `docs/checklists/18-1_structure_refactor_checklist.md`
- `docs/ai_rag_architecture_plan.md`
- `docs/ai_rag_error_codes.md`
- `docs/ai_rag_decision_record.md`
- `docs/harnesses/component_harness_matrix.md`

### 18-2 기존 keyword RAG 구조 분리
- `docs/checklists/18-2_keyword_rag_refactor_checklist.md`
- `docs/ai_rag_architecture_plan.md`
- `docs/ai_rag_migration_plan.md`
- `docs/ai_rag_quality_eval_plan.md` (머지 직전 baseline 비교)
- `docs/harnesses/rag_harness_plan.md`

### 18-3 Chunker 구현
- `docs/checklists/18-3_chunker_checklist.md`
- `docs/ai_rag_architecture_plan.md`
- `docs/ai_rag_migration_plan.md`
- `docs/harnesses/chunk_harness_plan.md`

### 18-4 knowledge_chunks DB / reindex (m012)
- `docs/checklists/18-4_db_reindex_checklist.md`
- `docs/ai_rag_migration_plan.md` (m012 스키마)
- `docs/ai_rag_architecture_plan.md`
- `docs/ai_rag_rollout_plan.md` (관리자 화면 §7, 권한 §8)
- `docs/harnesses/chunk_harness_plan.md`

### 18-5 Vector / Embedding 구현
- `docs/checklists/18-5_vector_embedding_checklist.md`
- `docs/ai_rag_architecture_plan.md`
- `docs/ai_rag_migration_plan.md`
- `docs/harnesses/vector_harness_plan.md`
- `docs/ai_rag_error_codes.md`
- `docs/ai_rag_quality_eval_plan.md` (vector 머지 직전 비교)

### 18-6 Hybrid retriever (α/β + cache + LLM 게이트)
- `docs/checklists/18-6_hybrid_retriever_checklist.md`
- `docs/ai_rag_architecture_plan.md` (hybrid §15)
- `docs/ai_rag_error_codes.md`
- `docs/ai_rag_quality_eval_plan.md` (hybrid 머지 직전 비교)
- `docs/harnesses/hybrid_harness_plan.md`
- (기존) `docs/specs/04_ai_action_leave.md`

### 18-7 라우터/UI 통합 + API 계약 테스트
- `docs/checklists/18-7_admin_ui_checklist.md`
- `docs/ai_rag_architecture_plan.md`
- `docs/ai_rag_test_plan.md`
- `docs/ai_rag_rollout_plan.md` (관리자 화면 항목 + 권한)
- `docs/harnesses/rag_harness_plan.md`

### 18-8 회귀 + PyInstaller 검증 + 배포
- `docs/checklists/18-8_final_release_checklist.md`
- `docs/harnesses/full_harness_plan.md`
- `docs/ai_rag_test_plan.md`
- `docs/ai_rag_migration_plan.md` (spec hidden import 체크리스트)
- `docs/ai_rag_rollout_plan.md` (배포 순서)
- `docs/ai_rag_quality_eval_plan.md` (최종 합격 기준)

---

## 4. 문서 갱신 규칙

- 새 세션 시작 시 `ai_rag_current_state.md`의 마지막 갱신 시점이 직전 세션 종료 이후가 아니면 갱신한다.
- 본 목차는 새 문서 추가 시 같은 세션에서 함께 갱신한다.
- 문서 간 링크는 상대 경로 사용.
