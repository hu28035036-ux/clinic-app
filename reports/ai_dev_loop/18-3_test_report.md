# 18-3 Chunker 구현 — 테스트 리포트 (Codex 재검증 후 보강)

세션: 18-3 (Markdown chunker — heading 기준 결정적 분리)
일시: 2026-05-02
대상 브랜치: ai-rag-v1-integration
선행 세션: 18-2 (keyword RAG 분리)

업데이트 (Codex 재검증 후):
- schemas.py 의 stale 18-2 시기 주석 정리 (Chunk 가 18-3 에 재도입됨을 명시)
- chunker.py / normalizer.py 가 네트워크/LLM/embedding/DB/provider 어떤 모듈도
  import 하지 않음을 AST 기반으로 정밀 검증 (`test_15b_*`)
- 실제 매뉴얼 다수 (backup.md, no_therapist.md 등) chunk 품질 테스트 추가
  (`test_real_all_manuals_chunked_safely`, `test_real_backup_md_chunk_quality`,
  `test_real_no_therapist_md_procedure_intact`)

## 1. 실행 명령 및 결과 요약

| # | 명령 | 결과 |
|---|---|---|
| 1 | `pytest tests/test_ai_chunker_harness.py -v` | **35 passed** (이전 33 + golden 스냅샷 2개) |
| 2 | `pytest tests/test_ai_manual_rag_harness.py -v` | **18 passed** |
| 3 | `pytest tests/test_ai_manual_rag_contract.py -v` | **9 passed** |
| 4 | `pytest tests/test_ai_safety_harness.py -v` | **12 passed** |
| 5 | `pytest tests/test_ai_full_harness.py -v` | **8 passed** |
| 6 | `pytest tests -v` | **289 passed**, 1 skipped, 7 xfailed |
| 7 | `ruff check app tests scripts` | **All checks passed!** |
| 8 | `python scripts/check_db_path.py` | **EXIT_CODE=0** |

전체 테스트 수 254 → 289 (35 추가, 0 약화/제거).

## 골든 스냅샷 fingerprint (chunker 회귀 가드)

`test_chunker_golden_fingerprints_for_all_manuals` — 6개 매뉴얼 각각의 chunk 결과
content_hash 들을 ":" 로 join → sha256 해시:

| 매뉴얼 | chunks | fingerprint (앞 12자) |
|---|---:|---|
| `manuals/ai_settings.md` | 3 | `b9804746e487..` |
| `manuals/backup.md` | 3 | `892b415b9cb8..` |
| `manuals/munjanara_error.md` | 4 | `343491c8ee9f..` |
| `manuals/no_therapist.md` | 3 | `3cb531f7e100..` |
| `manuals/sms_compose.md` | 4 | `a33c2b635e6f..` |
| `manuals/therapist_leave.md` | 3 | `997f6b2c21ec..` |

매뉴얼 내용 / chunker 알고리즘 / normalizer 동작 변경 시 즉시 fail.
의도적 변경이라면 fix_summary 에 사유 기록 후 fingerprint 갱신 강제.

## 2. 사용자 지정 15개 단언 — 테스트 매핑

| # | 단언 | 테스트 함수 | 결과 |
|---|---|---|:---:|
| 1 | heading 기준으로 chunk 가 나뉨 | `test_1_heading_splits_into_sections`, `test_1b_heading_extraction_basic` | ✅ |
| 2 | 너무 짧은 chunk 가 병합됨 | `test_2_short_sections_get_merged` | ✅ |
| 3 | 너무 긴 chunk 가 문단 기준으로 나뉨 | `test_3_long_section_splits_at_paragraph_boundary` | ✅ |
| 4 | overlap 적용 가능 | `test_4_overlap_applied_between_subchunks`, `test_4b_overlap_disabled_means_no_overlap` | ✅ |
| 5 | 표/목록 중간 절단 금지 | `test_5_table_kept_in_one_chunk`, `test_5b_list_kept_in_one_chunk`, `test_5c_code_block_not_parsed_as_heading` | ✅ |
| 6 | 메뉴 경로와 설명 분리 금지 | `test_6_menu_path_not_split` | ✅ |
| 7 | 예약문자 예시 중간 절단 금지 | `test_7_sms_example_braces_balanced`, `test_7b_real_sms_compose_md_chunked` | ✅ |
| 8 | source_path / title / heading / section_path / chunk_index 유지 | `test_8_metadata_preserved_for_each_chunk`, `test_8b_section_path_includes_parent_headings` | ✅ |
| 9 | content_hash 생성됨 | `test_9_content_hash_generated` | ✅ |
| 10 | 같은 입력에서 content_hash 안정 | `test_10_content_hash_stable_for_same_input` (5회 반복 + BOM/CRLF 동등) | ✅ |
| 11 | 내용 변경 시 content_hash 변경 | `test_11_content_hash_changes_when_content_changes` | ✅ |
| 12 | chunk 순서 안정 (chunk_index 0,1,2,...) | `test_12_chunk_index_sequential_no_gaps`, `test_12b_chunk_documents_per_doc_index_resets` | ✅ |
| 13 | 외부 LLM provider 호출 0 | `test_13_chunker_does_not_call_llm_provider` | ✅ |
| 14 | embedding provider 호출 0 | `test_14_chunker_does_not_call_embedding_provider` | ✅ |
| 15 | 운영 DB 미사용 | `test_15_chunker_does_not_touch_operational_db` (import-graph 검사) + conftest db_guard | ✅ |

## 3. 추가 검증

- `test_18_2_keyword_rag_not_broken_by_chunker` ✅ — 18-2 manual_search API 회귀 0
- `test_chunker_default_constants_documented` ✅ — 기본값 200/1200/150 (변경 시 fix_summary 기록 의무)
- `test_normalize_markdown_idempotent` ✅ — 정규화 멱등성
- `test_empty_document_returns_no_chunks` ✅
- `test_no_heading_document_returns_single_chunk` ✅
- `test_chunker_oversize_soft_limit` ✅ — 단일 보호 블록(표/목록/코드) 초과 허용
- `test_chunker_invalid_params_raise` ✅ — 음수/역순 파라미터 ValueError

### Codex 재검증 후 추가 테스트 (4개)

- `test_15b_chunker_does_not_import_network_or_provider_modules` ✅ — AST 기반 정밀
  import 검사. requests/httpx/urllib/socket/openai/anthropic/sqlite3/app.database/
  app.models/app.services.ai.{provider,pii}/app.services.ai.rag.{pipeline,retriever,prompts,safety}/
  app.services.ai.manual_qa/app.services.rag 모두 import 부재 확인.
- `test_real_all_manuals_chunked_safely` ✅ — `knowledge/manuals/*.md` 6개 모두에
  대해 chunk 결정성/순서/메타/SMS 변수/메뉴 경로 보존 단언.
- `test_real_backup_md_chunk_quality` ✅ — backup.md 의 핵심 키워드(자동백업/수동백업/
  복원/clinic_/%APPDATA%) 보존 + 파일명 포맷(`clinic_YYYYMMDD_HHMMSS.db`) 단일 chunk.
- `test_real_no_therapist_md_procedure_intact` ✅ — no_therapist.md 의 1~4단계
  절차가 한 chunk 안에 모임.

## 4. 18-1/18-2 회귀

- 4개 RAG 하네스 (47 tests) 그대로 통과 — 응답 9키, sources 3키, manual_qa 시그니처/`LOW_SCORE_THRESHOLD`/`_MANUAL_SYSTEM_PROMPT` 보존
- 18-1 stub 단언 (`run_manual_qa`/`retrieve` NotImplementedError) 그대로
- 18-2 엄격화 결과 (vector/ 부재, embedding_called 부재) 유지
- SMS AI / 휴무 AI / sms_draft / sms_validate 회귀 0

## 5. 외부 호출 차단 검증

- conftest 의 `_block_sdk_modules()` 활성 (openai/anthropic 클래스 fail stub)
- chunker 는 순수 함수 (pii/provider 어떤 모듈도 import 안 함)
- chunker import-graph 에 `sqlite3`, `SessionLocal`, `from app.database`, `from app.models` 부재 (test_15 검증)

## 6. 수정 루프

총 3회. **최종 결과는 §1 표 / §7 결론 참조 (chunker 35/35, 전체 289/289).**

각 회차의 수행 작업:

**1회차** (초기 chunker 도입):
- `test_1_heading_splits_into_sections` 실패 — heading-only 첫 섹션(`# 긴 문서`)이 다음 섹션과 병합될 때 chunk metadata 가 첫 섹션 heading 을 그대로 가져가 `섹션 A` 가 metadata 에 안 보임. → `_merge_short_sections` 에 heading-only 섹션 promote 로직 추가.
- ruff 6건 (B905 zip strict, F841 unused var, B007 unused loop var) → 모두 수정.

**2회차** (Codex 1차 재검증 후 보강):
- schemas.py 상단 docstring 정리 — Chunk 가 18-3 재도입됨을 명시 (이전: "18-5 에 다시 추가" stale 주석).
- AST 기반 import-graph 단언 추가 (`test_15b_*`) — chunker.py / normalizer.py 가 17종 금지 모듈 (network/LLM/embedding/DB/provider) 어느 것도 import 하지 않음 정밀 검증.
- 도중 발견: `_resolve_relative` 의 level off-by-one 버그 (Python 의 ImportFrom level=1 은 "현재 패키지", level=2 는 "1단계 위") → 수정.
- 실제 매뉴얼 다수 chunk 품질 테스트 3종 추가 (`test_real_all_manuals_chunked_safely`, `test_real_backup_md_chunk_quality`, `test_real_no_therapist_md_procedure_intact`).
- ruff F541 (extraneous f-prefix) 1건 수정.

**3회차** (Codex 2차 재검증 후 보강 — 골든 스냅샷):
- `test_chunker_golden_fingerprints_for_all_manuals` 추가 — 6개 매뉴얼 각각의 chunk content_hash 들을 ":" 로 join → sha256 fingerprint 를 골든 값으로 baked-in. 매뉴얼 / chunker / normalizer 어느 쪽이든 변경되면 즉시 fail.
- `test_chunker_fingerprints_stable_across_runs` 추가 — 같은 입력 5회 반복 fingerprint 동일 (loader 캐시 reset 후에도 동일). 결정성/안정성 추가 입증.

## 7. 결론

15개 사용자 지정 단언 + 골든 스냅샷 6개 매뉴얼 fingerprint 모두 통과. 18-1/18-2 회귀 0. ruff/check_db_path 통과.
DB 영속화·embedding·vector store 미포함 (스코프 준수). 18-4 (knowledge_chunks 테이블) 진입 가능 상태.
