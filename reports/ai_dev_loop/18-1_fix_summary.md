# latest_fix_summary.md — 18-1_structure_refactor

## 변경 파일 목록 (신규 18, 수정 0)

### 신규 — `app/services/ai/rag/` (6개)
- `__init__.py` — 패키지 골격 + 의존 규칙 docstring (circular import 방지)
- `schemas.py` — `Source`/`Document`/`Chunk`/`Answer` dataclass + `ALL_REASON_CODES` 29개 + `AI_MODE_*` 3개 + `CONFIDENCE_*` 3개
- `safety.py` — `SafetyDecision` dataclass + `check_query()` stub (빈 질문 → `invalid_query` 만 처리, 정상 입력은 통과)
- `prompts.py` — `PROMPTS["manual_qa.system"]["v1"]` = 현행 `manual_qa._MANUAL_SYSTEM_PROMPT` 1:1 + `get_prompt(name, version)` + `DEFAULT_VERSIONS`
- `pipeline.py` — `run_manual_qa(...)` / `run_manual_search(...)` stub (NotImplementedError)
- `retriever.py` — `retrieve(...)` / `reset_cache()` stub (NotImplementedError)

### 신규 — `app/services/ai/knowledge/` (4개)
- `__init__.py` — 패키지 골격
- `loader.py` — `load_documents(...)` stub
- `normalizer.py` — `normalize_markdown(...)` / `extract_headings(...)` stub
- `keyword_index.py` — `build_index(...)` / `search(...)` stub

### 신규 — `app/services/ai/vector/` (4개)
- `__init__.py` — 패키지 골격 (ADR-005~007 명시)
- `embeddings.py` — `EmbeddingProvider` 추상 클래스 (`name`, `dimension`, `calls: list`, `is_ready`, `embed_documents`, `embed_query`) + `get_embedding_provider(...)` factory stub
- `store.py` — `upsert(...)` / `search(...)` / `count()` stub
- `similarity.py` — `cosine(...)` / `top_k(...)` stub

### 신규 — `tests/` (4개, 사용자 명시 명령)
- `test_ai_full_harness.py` — 9 tests (패키지 import + 라우터 smoke + 회귀 0)
- `test_ai_manual_rag_harness.py` — 19 tests (schemas 8 + prompts 4 + safety stub 2 + pipeline/retriever NotImpl 2 + manual_qa unchanged 2 + 추가 3)
- `test_ai_manual_rag_contract.py` — 9 tests (manual/search 3개 키 + manual/ask 9개 키 + sources 3개 키 + optional)
- `test_ai_safety_harness.py` — 11 tests (PII 마스킹 회귀 0 3 + 위험 단정 차단 2 + unknown_feature 1 + API key 미노출 1 + safety stub 신규 4)

### 수정 — 0건
**기존 파일 1줄도 수정/삭제 없음.**
- `app/**` 모든 기능 코드: 0 diff
- `app/services/ai/manual_qa.py`: 0 diff (시스템 프롬프트는 `prompts.py` 의 v1 으로 **복사 인용**, 원본 미수정)
- `app/services/rag/search.py`: 0 diff
- `app/routers/ai.py`: 0 diff
- `tests/conftest.py`: 0 diff (18-0 형태 그대로)
- 기존 `tests/test_*.py` 18개: 0 diff
- `dosu_clinic.spec`: **0 diff** (사용자 명시 "PyInstaller spec 수정 금지". 체크리스트 18-1 의 hidden import 추가 항목은 18-2 또는 18-8 로 이전.)
- `requirements.txt`/`pyproject.toml`/`pytest.ini`: 0 diff
- `app/migrations/**`: 0 diff
- UI/static/knowledge: 0 diff

## 변경 요약 (의도 / 이유)

### 1) 14개 신규 모듈 = 빈 골격 + stub
- **모든 실제 로직은 18-2 이후로 이전.** 18-1 은 폴더 구조와 인터페이스 stub 만.
- `pipeline.run_manual_qa()` / `retriever.retrieve()` / `loader.load_documents()` 등은 모두 `NotImplementedError` raise.
- 라우터/`manual_qa` 가 본 모듈을 호출하지 않음 → 회귀 0.

### 2) `Source` / `Answer` dataclass = v1.3.3 응답 키 1:1
- `Source.{title, path, snippet}` — 응답 `sources[]` 항목 키 보존.
- `Answer` 필수 9개 필드 — manual/ask 응답 9개 키 보존.
- `Answer` optional 5개 필드 (`reason_code`/`llm_called`/`embedding_called`/`ai_mode`/`prompt_version`) — 18-2 이후 점진 도입 자리만 마련.
- 18-1 은 응답에 새 키를 추가하지 **않음** (라우터/`manual_qa` 모두 0 diff).

### 3) reason_code 29개 + AI 모드 3개 상수화
- `ALL_REASON_CODES` 에 `unsupported_question` 단일 표준 + 별칭(`unsupported_claim`) 부재 자동 단언.
- 모든 후속 세션에서 `from app.services.ai.rag.schemas import REASON_*` 사용 가능.

### 4) `prompts.py` v1 = 현행 시스템 프롬프트 1:1
- `manual_qa.py:33-45` 의 `_MANUAL_SYSTEM_PROMPT` 를 `PROMPTS["manual_qa.system"]["v1"]` 로 그대로 인용.
- 테스트 `test_prompts_v1_matches_current_manual_qa_system` 가 1글자 변경도 잡아냄.
- 라우터/`manual_qa` 는 본 dict 를 사용하지 않음 (18-2 이후 채택).

### 5) circular import 방지
- 신규 패키지(`rag`/`knowledge`/`vector`) 의 모든 모듈은 **자기 폴더 내 + `app.services.ai.{provider, pii}` + stdlib + `app.services.ai.rag.schemas`** 만 import.
- `manual_qa.py` / `rag.search` 를 import 하지 않음 (역의존 회피).
- `tests/test_ai_full_harness.py::test_no_circular_import_when_loading_skeleton` 가 14개 모듈 독립 import 검증.

### 6) ruff 4 errors → `--fix` 자동 수정
- I001 (Import block un-sorted) — 신규 4개 테스트 파일에서 발생. `ruff check --fix` 적용 → 모두 정렬됨.
- 4개 파일은 자동 정렬 후 의미 변동 0 (import 순서만).

### 7) test_existing_rag_search_still_importable 의 import 패턴 학습
- `app/services/rag/__init__.py` 의 `from .search import search` 때문에 `app.services.rag.search` 의 attribute access 시 함수가 우선.
- 모듈 객체는 `importlib.import_module("app.services.rag.search")` + `sys.modules` 로 명시 획득.
- 본 패턴은 18-2 keyword RAG 분리 시 동일 함정에 빠지지 않도록 docstring 에 기록함.

## diff 규모
- 신규 파일 LOC 합계: 약 880줄 (모듈 14 + 테스트 4)
- 기존 파일 0 diff
- ruff `--fix` 가 자동 변경한 import 정렬 4 파일은 신규 파일 내 변경 (기존 파일 영향 없음)

## 사용자 명시 "PyInstaller spec 수정 금지" 처리
체크리스트 18-1 §2 는 `dosu_clinic.spec` 에 hidden import 등록을 작업 가능 범위로 명시했으나, 본 세션 사용자 메시지가 명시적으로 spec 수정을 **금지**했다. 신규 14개 모듈은 PyInstaller 정적 분석으로는 발견되지 않을 가능성이 있으나:
- 본 세션에서는 어떤 라우터/기존 모듈도 신규 패키지를 import 하지 않음 → 빌드 시 PyInstaller 에 영향 0.
- 18-2 keyword RAG 분리 시 라우터/`manual_qa` 가 신규 모듈을 import 하기 시작하면 spec hidden import 등록 필수.
- 본 항목을 `latest_codex_review_request.md` §17 잔여 위험에 명시.
