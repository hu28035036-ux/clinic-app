# Chunk Harness 설계 (chunk_harness_plan)

> 문서가 검색 품질을 해치지 않는 방식으로 chunk 분리되는지 검증.

---

## 1. Harness Name
`chunk_harness`

## 2. 목적
마크다운 문서의 청킹이 결정적이고 의미 단위 보존이 적절한지 검증한다. 청킹 변동이 RAG 검색 결과 회귀를 유발하지 않도록 한다.

## 3. 시작 구현 세션
- **18-3**

## 4. 테스트 대상 모듈
- `app/services/ai/knowledge/loader.py`
- `app/services/ai/knowledge/normalizer.py`
- `app/services/ai/knowledge/chunker.py`
- `app/services/ai/knowledge/synonyms.py` (간접)

## 5. 입력 케이스
1. heading 깊이 다양한 마크다운 (h1/h2/h3)
2. 짧은 문단 여러 개 (병합 대상)
3. 긴 단락 (분리 대상)
4. 표(`| col |`) 포함 — 절단 금지
5. 순서/번호 목록 — 중간 절단 금지
6. 코드블록 — 절단 금지 / 마스킹
7. 메뉴 경로 + 설명 짝 (한 chunk에 묶임)
8. SMS 예시 문구 (예시-설명 짝 보존)
9. 빈 섹션 / 헤딩만 있는 섹션
10. 동일 문서 재로드 → 동일 chunk_index/content_hash
11. 문서 내용 1글자 변경 → 영향 chunk만 hash 변경
12. 인코딩(UTF-8 BOM, CRLF) 차이

## 6. 기대 출력
- `Chunk(doc_id, source_path, title, heading, section_path, chunk_index, content, content_hash, token_count, tags, category, document_version)` 리스트
- 결정적 (동일 입력 → 동일 출력 리스트, 순서 동일)
- 표/목록/코드블록은 chunk 경계와 무관하게 보존

## 7. 외부 LLM 호출 허용 여부
❌ 금지 (chunker는 순수 텍스트 처리)

## 8. 외부 Embedding 호출 허용 여부
❌ 금지 (Vector 단계는 vector_harness)

## 9. Provider call count 기대값 (측정: `len(provider.calls)`)
모든 시나리오: 0

## 10. Embedding provider call count 기대값 (측정: `len(embedding_provider.calls)`)
모든 시나리오: 0

## 11. 사용할 Fake 객체
- 별도 Fake 불필요 (외부 호출 없음)
- FakeProvider/FakeEmbeddingProvider는 conftest 기본 시드 그대로 — 호출되면 fail

## 12. 운영 DB 사용 여부
❌ 금지 (chunker 단위는 DB 없이 동작)

## 13. 사용해야 하는 테스트 DB 또는 fixture
- `tests/harness/chunk_harness.py`:
  - `markdown_samples` fixture (테스트 전용 markdown 묶음)
  - `chunker_default` fixture (기본 설정 청커)
  - `assert_chunks_deterministic(input)` 헬퍼
  - `assert_table_unsplit(chunks)` 헬퍼
  - `assert_codeblock_unsplit(chunks)` 헬퍼

## 14. 반드시 검증할 reason_code
- (chunker 단위는 reason_code 직접 발급 없음)
- 간접: indexer가 chunk 실패 시 부분 실패 처리 → vector_harness/full_harness에서 검증

## 15. 반드시 검증할 로그 필드
- chunker는 별도 로그 없음
- indexer 호출 시: `knowledge_index_runs.{total_chunks, succeeded_docs, failed_docs}`

## 16. fallback 기대 동작
- 빈 문서 → chunk 0개, 오류 없음
- 잘못된 인코딩 → 안전 실패 + 해당 문서만 skip (전체 인덱스 보존)

## 17. 실패하면 막아야 하는 회귀
- 동일 입력에 대해 chunk 결과가 매번 달라짐 (비결정성)
- 표 중간 절단
- 코드블록 중간 절단
- 메뉴 경로/설명 분리
- chunk_index 누락 또는 중복
- content_hash 알고리즘 변경 (sha256 고정)
- 문서 내용 안 바뀌었는데 hash가 바뀜

## 18. 실행 명령 후보
- `venv\Scripts\python.exe -m pytest tests/test_chunker.py -v`
- `venv\Scripts\python.exe -m pytest tests -k chunk -v`

## 19. 완료 조건
- [ ] §5 모든 입력 케이스 통과
- [ ] 같은 입력 → 같은 chunks 결정성 통과
- [ ] §17 모든 회귀 0건
- [ ] heading/code/list/table 보호 단언 통과

## 20. Codex 검증 시 집중 확인 항목
- 청킹이 정말 결정적인가 (랜덤성·시간 의존성 없음)
- chunk 경계 결정 로직이 표/목록/코드블록을 침범하지 않는가
- content_hash가 콘텐츠 외 메타(타임스탬프 등)에 의존하지 않는가
- 비ASCII(한글) 처리 시 token_count가 일관된 정의를 쓰는가
- chunker 변경이 기존 keyword_index 검색 결과를 회귀시키지 않는가 (eval set 비교 권장)
