# 18-3 Chunker 구현 — Codex 검증 요청

세션: 18-3
브랜치: ai-rag-v1-integration
선행 세션: 18-2 (keyword RAG 분리, Codex 통과)
다음 세션 후보: 18-4 (knowledge_chunks 테이블 + reindex API) 또는 18-5 (vector/embedding)

## 1. 검증 요청 요지

`app/services/ai/knowledge/chunker.py` 를 신규 구현하여 마크다운 문서를 결정적 chunk 리스트로 분리. 사용자 지정 15개 단언 + 추가 7개 단언 모두 통과. 18-2 keyword RAG / manual API 회귀 0.

본 세션에서는 chunk 를 DB 에 저장하지 않고, embedding 을 생성하지 않고, vector store 를 사용하지 않음. chunker 는 순수 함수 (외부 호출 0).

## 2. 신규/수정 파일

| 분류 | 파일 |
|---|---|
| 신규 | `app/services/ai/knowledge/chunker.py` |
| 신규 | `tests/harness/chunk_harness.py` |
| 신규 | `tests/test_ai_chunker_harness.py` (29 tests) |
| 수정 | `app/services/ai/rag/schemas.py` — `Chunk` dataclass 추가 |
| 수정 | `app/services/ai/knowledge/normalizer.py` — stub → 정식 구현 |
| 수정 | `app/services/ai/knowledge/__init__.py` — docstring |

손대지 않은 영역: 라우터, manual_qa wrapper, rag.pipeline/retriever, app.services.rag.search, requirements, spec, UI, migrations.

## 3. Chunker 알고리즘 (3단계)

1. `normalizer.extract_sections(raw_text)` — heading 경계로 섹션 분리. 코드블록 내부 `#` 는 heading 으로 인식 안 함.
2. `_merge_short_sections(sections, min, max)` — `min_chunk_chars` 미만이면 다음 섹션과 병합. heading-only 섹션은 다음 섹션 heading/section_path 로 promote.
3. `_split_large_section_content(content, max, overlap)` — `max_chunk_chars` 초과면 `\n\n` 문단 단위 분할. `overlap_chars > 0` 이면 sub-chunk 사이 중첩.

기본값: `MIN_CHUNK_CHARS=200`, `MAX_CHUNK_CHARS=1200`, `OVERLAP_CHARS=150`. 변경 시 latest_fix_summary.md 기록 의무 (회귀 가드 테스트 `test_chunker_default_constants_documented`).

## 4. Chunk dataclass

```
doc_id, source_path, category, title, heading, section_path,
chunk_index, content, content_hash, token_count, tags, document_version
```

18-2 엄격화 시 제거되었던 dataclass 를 18-3 chunker 산출물용으로 재도입. 18-4 `knowledge_chunks` 테이블 컬럼과 정렬.

## 5. 사용자 15개 단언 → 테스트 매핑

| # | 단언 | 테스트 |
|---|---|---|
| 1 | heading 분리 | `test_1_*`, `test_1b_*` |
| 2 | 짧은 chunk 병합 | `test_2_*` |
| 3 | 긴 chunk 문단 분할 | `test_3_*` |
| 4 | overlap 적용 | `test_4_*`, `test_4b_*` |
| 5 | 표/목록 보존 | `test_5_*`, `test_5b_*`, `test_5c_*` |
| 6 | 메뉴 경로 분리 금지 | `test_6_*` |
| 7 | 예약문자 예시 보존 | `test_7_*`, `test_7b_*` (실제 sms_compose.md) |
| 8 | metadata 5종 유지 | `test_8_*`, `test_8b_*` |
| 9 | content_hash 생성 | `test_9_*` |
| 10 | 동일 입력 → 동일 hash | `test_10_*` (5회 반복 + BOM/CRLF 동등) |
| 11 | 내용 변경 시 hash 변경 | `test_11_*` |
| 12 | 순서 안정성 | `test_12_*`, `test_12b_*` |
| 13 | LLM provider 호출 0 | `test_13_*` |
| 14 | embedding provider 호출 0 | `test_14_*` |
| 15 | 운영 DB 미사용 | `test_15_*` (import-graph 검사) + conftest db_guard |

## 6. 결정성/안정성 입증

- `assert_chunks_deterministic(text, times=5)` 로 5회 반복 수행 — 동일 chunks/hash/index 보장
- `content_hash = sha256(content).hexdigest()` — content 만 입력. 위치/메타 미포함
- `normalize_markdown` 의 BOM/CRLF 정규화로 입력 형식 차이가 hash 에 영향 없음

## 7. 회귀 0 입증

- 4개 RAG 하네스 (manual_rag/safety/full/contract) 47 tests 모두 통과
- 18-2 manual_qa import 경로/시그니처/응답 키 보존
- 18-1 stub 단언 (`run_manual_qa`/`retrieve` NotImplementedError) 보존
- 18-2 엄격화 (vector/ 부재, embedding_called 부재) 유지
- SMS AI / 휴무 AI / sms_draft / sms_validate 회귀 0

## 8. 금지 사항 점검

- ❌ vector/embedding 구현 0 (Chunk dataclass 만 단독 추가)
- ❌ hybrid retriever 0
- ❌ knowledge_chunks DB 테이블 0
- ❌ reindex API 0
- ❌ DB migration 0
- ❌ requirements / spec / UI / 라우터 변경 0
- ❌ 운영 DB 접근 0 (import-graph 검사 통과)
- ❌ 실제 외부 LLM/Embedding 호출 0
- ❌ 기존 SMS AI / 휴무 AI 동작 변경 0
- ❌ 하네스/테스트 약화 0 (skip/xfail 추가 없음)

## 9. 테스트 결과

- `pytest tests/test_ai_chunker_harness.py`: **29 passed**
- `pytest tests/test_ai_manual_rag_harness.py`: 18 passed
- `pytest tests/test_ai_manual_rag_contract.py`: 9 passed
- `pytest tests/test_ai_safety_harness.py`: 12 passed
- `pytest tests/test_ai_full_harness.py`: 8 passed
- `pytest tests`: **283 passed**, 1 skipped, 7 xfailed (이전 254 + 29 신규 chunker)
- `ruff check app tests scripts`: All checks passed!
- `python scripts/check_db_path.py`: exit 0

수정 루프: 1회 (heading-only promote 로직 + ruff 6건 정리).

## 10. Codex 가 직접 확인할 항목

1. `chunker.py` 가 외부 호출 0 (provider, embedding, DB, 네트워크) — import 그래프 확인.
2. `Chunk` dataclass 필드가 18-4 `knowledge_chunks` 스키마 (`docs/ai_rag_migration_plan.md`) 와 정렬되는지.
3. `_merge_short_sections` 의 heading-only promote 로직이 의도대로 작동 (chunk metadata 의미성).
4. `_split_large_section_content` 의 `\n\n` 문단 분할이 표/목록/코드블록을 절단하지 않는지 — 실제 `sms_compose.md` / `backup.md` chunk 결과 시각 검증.
5. content_hash 가 sha256(content) 만 — 위치/메타 미포함 (decoupled identifier).
6. normalize_markdown 의 BOM/CRLF/우측 공백 정규화가 hash 안정성에 충분한지.
7. 사용자 15개 단언 중 누락 없이 테스트화되었는지.
8. 18-2 회귀 0 (4개 RAG 하네스 47 tests 통과 + manual_qa import 경로 보존).

## 11. 다음 세션 진입 yes/no 자체 판단

**yes**.
- 사용자 15개 단언 모두 통과
- 18-2 회귀 0
- 외부 호출 0, DB 접근 0
- 스코프 엄격 준수 (DB 영속화/embedding/vector 모두 부재)

**다음 세션 후보**:
- **18-4**: `knowledge_chunks` 테이블 + reindex API + chunker 결과 영속화. 본 세션의 chunker 가 그대로 입력으로 사용됨.
- **18-5**: embedding/vector store. 18-4 가 선행되어야 효율적.

권장 순서: 18-4 → 18-5.

## 12. 다음 세션 진입 시 주의

- chunker 기본값 (200/1200/150) 변경 시 모든 기존 chunk 의 hash/경계가 바뀜 → 18-4 reindex 시 영향. 변경하려면 `document_version` 로 추적.
- `test_chunker_default_constants_documented` 가 기본값 변경을 즉시 fail 로 알려줌.
- chunker 는 순수 함수 — 18-4 에서 영속화 layer 와 분리 유지 권장 (chunker 자체는 DB 모름).
- `Chunk.tags` / `Chunk.document_version` 은 현재 빈 문자열 — 18-4 이후 채움.
