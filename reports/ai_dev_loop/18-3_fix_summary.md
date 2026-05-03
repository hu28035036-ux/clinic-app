# 18-3 Chunker 구현 — Fix Summary

## 1. 신규/수정 파일 목록

### 신규
1. `app/services/ai/knowledge/chunker.py` — heading 기준 결정적 chunker (순수 함수)
2. `tests/harness/chunk_harness.py` — chunk 단언 helper 9종
3. `tests/test_ai_chunker_harness.py` — 사용자 15개 단언 + 추가 7개 (총 29 tests)

### 수정
4. `app/services/ai/rag/schemas.py` — `Chunk` dataclass 추가 (18-2 엄격화에서 제거됐던 항목, 18-3 chunker 산출물용으로 다시 도입)
5. `app/services/ai/knowledge/normalizer.py` — `normalize_markdown`, `extract_headings`, `extract_sections` 정식 구현 (18-1 stub 제거)
6. `app/services/ai/knowledge/__init__.py` — 패키지 docstring 갱신 (chunker 추가 명시)

### 손대지 않은 파일
- `app/routers/ai.py`, `app/services/ai/manual_qa.py`, `app/services/ai/rag/{pipeline,retriever,prompts,safety}.py`
- `app/services/rag/search.py`, `app/services/ai/knowledge/{loader,keyword_index}.py`
- `tests/conftest.py`, `tests/test_ai_manual_rag_*.py`, `tests/test_ai_safety_harness.py`, `tests/test_ai_full_harness.py`, `tests/harness/*` (`chunk_harness.py` 외)
- `requirements.txt`, `dosu_clinic.spec`, `app/migrations/`, `app/templates/`, `app/static/`, `pyproject.toml`

## 2. Chunker 알고리즘 (3단계 파이프라인)

```
Document.raw_text
   │
   ▼
[1] normalizer.extract_sections()    # heading 경계로 섹션 분리, 코드블록 보호
   │
   ▼
[2] _merge_short_sections()          # min_chunk_chars 미만 → 인접 섹션과 병합
   │                                  # heading-only 섹션은 다음 섹션 metadata 로 promote
   ▼
[3] _split_large_section_content()   # max_chunk_chars 초과 → \n\n 문단 단위 분할
   │                                  # overlap_chars > 0 이면 sub-chunk 사이 중첩
   ▼
list[Chunk]  (chunk_index 0,1,2,...)
```

각 단계는 순수 함수. 외부 호출 0.

## 3. 기본값

| 상수 | 값 | 변경 시 의무 |
|---|---:|---|
| `MIN_CHUNK_CHARS` | 200 | latest_fix_summary.md 기록 |
| `MAX_CHUNK_CHARS` | 1200 | latest_fix_summary.md 기록 |
| `OVERLAP_CHARS` | 150 | 사용자 권장 100~200 의 중앙값 |

본 세션에서는 사용자 지정 후보값 그대로 사용 — **변경 없음**.
`test_chunker_default_constants_documented` 가 변경 시 즉시 실패하여 회귀 가드.

## 4. Chunk dataclass (rag/schemas.py)

```python
@dataclass
class Chunk:
    doc_id: str = ""           # sha1(source_path)
    source_path: str = ""      # knowledge/<category>/<file>.md
    category: str = ""         # "manuals" | "sms_guides"
    title: str = ""            # 문서 제목 (첫 h1)
    heading: str = ""          # chunk 의 가장 가까운 heading
    section_path: str = ""     # "h1 > h2 > h3"
    chunk_index: int = 0       # 0-based, 문서 내 안정 인덱스
    content: str = ""          # heading 라인 포함
    content_hash: str = ""     # sha256(content) hex 64자
    token_count: int = 0       # len(content) (Korean char count)
    tags: str = ""             # csv (현재 빈 값)
    document_version: str = "" # reindex 추적 (18-4 이후)
```

18-2 엄격화에서 제거한 후, 18-3 chunker 산출물 dataclass 로서 재도입.
18-4 `knowledge_chunks` 테이블 컬럼과 1:1 정렬.

## 5. 결정성 보증

`content_hash = sha256(content).hexdigest()` — content 만 입력. doc_id, chunk_index, source_path 등 메타는 hash 입력 미포함. 따라서:
- 동일 content → 동일 hash (위치 무관) — 요구사항 #10
- content 1글자 변경 → hash 변경 — 요구사항 #11

`normalize_markdown` 이 BOM 제거 + CRLF→LF + 라인 우측 공백 strip 적용 — BOM/줄바꿈 차이가 hash 에 영향 없음 (`test_10` 가 명시 단언).

## 6. 보호 블록 처리

- **코드블록** (` ``` ... ``` `): heading 추출 시 코드블록 내부 `#` 무시 (`_RE_CODE_FENCE` toggle).
- **표** (`| col |`): 한 문단 내에 연속된 라인 → `\n\n` 분할에서 자연 보존.
- **목록** (`1.`, `-`): 연속 라인이 한 문단 → `\n\n` 분할에서 자연 보존.
- **메뉴 경로** (`A → B → C`): 한 라인 안에 있어 절대 절단 안 됨.
- **SMS 변수** (`{환자명}`): 한 라인 / 한 문단 안에 있어 절단 안 됨.

단일 문단이 `max_chunk_chars` 를 초과하면 그 chunk 가 max 를 넘어도 그대로 유지 (soft max). `assert_no_chunk_exceeds_soft_max(chunks, max, soft_factor=2.0)` 로 한도 검증.

## 7. heading-only 섹션 promote 로직 (수정 루프 1회차)

문제: LONG_DOC 의 첫 섹션 `# 긴 문서` (heading 라인만, body 없음) 이 다음 섹션과 병합될 때, chunk metadata 가 첫 섹션의 heading (`긴 문서`) 을 그대로 가져가 의미 있는 heading (`섹션 A`) 이 metadata 에서 사라짐.

수정: `_is_heading_only_section(buf)` 가 True 면 sec 의 heading/section_path/level 로 promote (content 는 정상 병합).

이로써:
- `chunk[0].heading == "섹션 A"` (보다 의미 있는 heading)
- `chunk[0].section_path == "긴 문서 > 섹션 A"`
- `chunk[0].title == "긴 문서"` (전체 문서 title 은 그대로)
- `chunk[0].content` 안에 `# 긴 문서` 라인은 여전히 포함 (content_hash 안정)

## 8. ruff 정리 (수정 루프 동일 회차)

- B905 (zip strict): 결정성 단언에는 `strict=True`, overlap 검사에는 `strict=False`
- F841 (unused doc var): test_5c 에서 doc 변수 제거
- B007 (unused loop var): `path` → `_path`

## 9. 18-2 엄격화 유지

- `app/services/ai/vector/` 부재 그대로 ✅
- `Answer.embedding_called` 부재 그대로 ✅
- `REASON_VECTOR_DISABLED`, `REASON_EMBEDDING_SKIPPED_*` 부재 그대로 ✅
- `vector/embedding/hybrid` 코드 작성 0 ✅
- DB migration 0 / requirements 변경 0 / spec 변경 0 / UI 변경 0 / 라우터 변경 0 ✅

`Chunk` dataclass 만 단독 추가 (18-3 chunker 산출물에 한정).

## 10. 수정 루프 횟수

총 2회.

**1회차** (초기 chunker 도입):
1. `test_1_heading_splits_into_sections` 실패 → heading-only promote 로직 추가
2. ruff 6건 → zip strict / unused var 수정
→ chunker 29/29, 전체 283/283 통과

**2회차** (Codex 재검증 후 보강):
1. schemas.py 상단 주석 정리 — Chunk 가 18-3 에 재도입됨을 명시 (이전: "18-5 에 다시 추가"라는 stale 18-2 문맥 잔존)
2. AST 기반 import-graph 정밀 단언 추가 (`test_15b_*`) — chunker.py / normalizer.py 가 네트워크/LLM/embedding/DB/provider 어떤 모듈도 import 하지 않음 확인.
   - 도중 발견: `_resolve_relative` 의 level off-by-one 버그 (Python 의 ImportFrom level=1 은 "현재 패키지", level=2 는 "1단계 위") → 수정.
3. 실제 매뉴얼 다수에 대한 chunk 품질 테스트 추가 (3종):
   - `test_real_all_manuals_chunked_safely`: 6개 매뉴얼 모두에 대해 결정성/순서/메타/변수/메뉴 보존 단언
   - `test_real_backup_md_chunk_quality`: backup.md 핵심 키워드 + 파일명 포맷 보존
   - `test_real_no_therapist_md_procedure_intact`: 1~4단계 절차가 한 chunk 안에 모임
4. ruff F541 (extraneous f-prefix) 1건 수정.

## 11. Codex 재검증 후속 액션 매핑

| Codex 지적 | 처리 |
|---|---|
| schemas.py 주석에 "18-5 에 다시 추가" 문구 (Chunk) — 18-3 재도입과 어긋남 | schemas.py docstring + §1 reason_code 주석 양쪽 정리 (`schemas.py:1-26`). Chunk 는 18-3 재도입 / vector·embedding 항목만 18-5 보류로 명시. |
| 외부 LLM/embedding 호출 0 테스트가 fake `.calls==0` 수준 — 강한 감시 아님 | `test_15b_*` 추가: AST 로 chunker.py / normalizer.py 의 모든 import 를 절대경로로 변환 후, 17종 금지 모듈 (network/LLM/SDK/provider/pii/pipeline/retriever/safety/db) 중 하나라도 import 되면 fail. |
| 표/목록/메뉴/SMS 보존 테스트가 대표 샘플 위주 (sms_compose.md 만 실문서) | 실문서 3종 추가 (전체 매뉴얼 일괄 + backup.md 품질 + no_therapist.md 절차). 6개 매뉴얼 모두에 대해 결정성/순서/메타/변수 보존을 한 번에 검증. |
| 18-3 만의 delta 는 적절. 다만 working tree 에 18-0~18-2 변경이 같이 섞임 (HEAD 기준 리뷰 시 범위 초과) | 본 세션의 책임 범위 외 (18-2 통과 후 commit 분할 권장은 이미 전달). 18-3 자체의 delta 는 chunker / normalizer / schemas::Chunk / chunk_harness / test_ai_chunker_harness 5개 파일로 한정. |
| Codex 환경에서 python 실행 불가 (PATH 부재 + WindowsApps 깨짐 + 번들 Python pytest 미설치) | 환경 이슈 — 본 세션 코드 변경으로 해결 불가. 본 환경(`venv/Scripts/python.exe`)에서 실행 결과만 보고. |

## 12. Codex 3차 재검증 후속 (테스트 부족 부분 보강)

Codex 재검증 후속에서 추가 지적된 "chunk 품질 더 많은 실제 문서 기반 golden/snapshot
테스트가 있으면 좋음" 항목을 처리:

### test_chunker_golden_fingerprints_for_all_manuals (신규)

`knowledge/manuals/*.md` 6개 모두에 대해 chunker 결과 content_hash 들을 ":" 로
join → sha256 해시 = "fingerprint". 각 매뉴얼의 (chunk 수, fingerprint) 쌍을
테스트 코드에 골든 값으로 baked in.

baked-in 값:
```
manuals/ai_settings.md     → (3, b9804746...)
manuals/backup.md          → (3, 892b415b...)
manuals/munjanara_error.md → (4, 343491c8...)
manuals/no_therapist.md    → (3, 3cb531f7...)
manuals/sms_compose.md     → (4, a33c2b63...)
manuals/therapist_leave.md → (3, 997f6b2c...)
```

회귀 검출 능력:
- 매뉴얼 내용 변경 → fingerprint 변경 → fail
- chunker 알고리즘 (병합/분할/promote 로직) 변경 → fingerprint 변경 → fail
- normalizer 정규화 (BOM/CRLF/whitespace) 변경 → fingerprint 변경 → fail
- chunk_index 순서 변경 → join 순서 영향 → fingerprint 변경 → fail
- 신규 매뉴얼 추가 → `missing` 검출 후 GOLDEN_FINGERPRINTS 추가 강제 → fail

의도적 변경 시 새 fingerprint 를 fix_summary 에 기록 후 dict 갱신 — 절차 강제.

### test_chunker_fingerprints_stable_across_runs (신규)

같은 입력에서 5회 반복 fingerprint 동일 — loader 캐시 reset 후에도 동일.
결정성/안정성 추가 입증.

### Codex 환경 (4차 재검증 시점에 정상 복구 확인)

이전 회차에서 Codex 환경의 python/pytest 실행 불가 (PATH 부재, WindowsApps 깨짐,
번들 pytest 미설치) 가 보고됐으나, 4차 재검증 시점에 정상 복구 확인:
- `venv\Scripts\python.exe`: Python 3.12.10
- `pytest`: 8.4.2

Codex 측 직접 실행 결과 (4차):
- `tests/test_ai_chunker_harness.py`: **35 passed**
- 18-0/18-2 RAG/Safety/Full 4종: **47 passed**
- 기존 SMS AI / 휴무 AI: **69 passed, 4 xfailed**
- 기존 RAG/local-only: **24 passed**

본 세션 결과 (`venv/Scripts/python.exe`) 와 Codex 환경 실행 결과 100% 일치.

**최종 결과: chunker harness 35/35, 전체 289/289 통과.**
