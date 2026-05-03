# latest_fix_summary.md — 18-0_rag_harness

## 변경 파일 목록 (신규 8 + 수정 1 = 9개)

### 신규 작성
- `tests/harness/fake_provider.py` — 64줄. 기존 `tests/conftest.py:112` `FakeProvider` 재사용 wrapper + `call_count(p)` / `last_prompt(p)` / `last_system(p)` / `assert_no_external_call(p)` / `assert_provider_received_no_pii(p, *patterns)` helper.
- `tests/harness/contract.py` — 116줄. v1.3.3 응답 9개 키 계약 단언 (`MANUAL_ASK_REQUIRED`, `MANUAL_SEARCH_REQUIRED`, `SOURCE_ITEM_REQUIRED`, `assert_manual_ask_contract(body)`, `assert_manual_search_contract(body)`, `assert_source_item_contract(s)`).
- `tests/harness/rag_harness.py` — 50줄. `KNOWN_QUESTIONS`/`UNKNOWN_QUESTIONS` 상수 + `expect_no_external_call(provider, embedding_provider=None)` helper.
- `tests/harness/safety_harness.py` — 76줄. `PII_PHONE_TEXTS`/`PII_BIRTH_TEXTS`/`PII_RRN_TEXTS`/`DANGEROUS_RESPONSES`/`UNKNOWN_FEATURE_QUESTIONS` 상수 + `assert_no_pii_in_text` / `assert_no_api_key_in_text` / `assert_pii_marker_present` helper.
- `tests/test_full_harness.py` — 9개 테스트. 라우터 smoke + 응답 키 계약 단언 + 외부 SDK 차단 동작.
- `tests/test_rag_pipeline.py` — 5개 테스트. RAG 검색·LLM 게이트·계약.
- `tests/test_rag_safety.py` — 6개 테스트. PII 입력/응답 마스킹·위험 단정 차단·없는 기능 안전 응답.
- `tests/test_local_only_mode.py` — 4개 테스트. 모든 차단 분기에서 `len(provider.calls) == 0` 단언 (회귀 모드 A에서도 위반 없는 케이스).

### 수정 (최소 범위)
- `tests/conftest.py` — 기존 격리 1~6 단계 그대로. 끝에 §7(외부 SDK monkeypatch — `_block_sdk_modules()` 호출, `openai.OpenAI/Client/AsyncOpenAI`, `anthropic.Anthropic/Client/AsyncAnthropic`을 `_raise_external_call` stub으로 교체) + §8(2개 fixture: `ai_disabled_setting`, `ai_enabled_with_fake`) 추가.

## 변경 요약 (의도/이유)

### 1) FakeProvider 재사용 (helper만 추가)
Codex 보완 결정대로 기존 `FakeProvider`를 **그대로** 사용. 호출 카운트는 `len(provider.calls)` 표준. 새 클래스/속성을 도입하지 않아 기존 18개 AI 테스트와 충돌 0.

### 2) 응답 9개 키 계약 보호
v1.3.3 `manual/ask` 응답 9개 키(`answer/sources/confidence/not_found/blocked/blocked_reason/guard_hits/top_score/masked_question`) + `manual/search` 3개 키 + `sources[].{title,path,snippet}` 모두 `contract.py`에서 강제 단언. 신규 optional 키(`reason_code/llm_called/embedding_called/ai_mode/prompt_version`)는 **있어도 OK, 없어도 OK** — 18-2 이후 점진 도입 호환.

### 3) 외부 SDK monkeypatch
`conftest.py` module-level `_block_sdk_modules()`이 SDK 모듈의 진입 클래스를 즉시 `RuntimeError` raiser로 교체. SDK 미설치 환경(import 실패)은 자동 패스. `_check_sdk`(routers/ai.py:97-116)는 `importlib.import_module`만 시도하므로 **import 가능 + 인스턴스화 차단** 패턴이 유효.

### 4) 라우터 통합 fixture
`ai_disabled_setting` / `ai_enabled_with_fake` 두 fixture로 라우터 통합 테스트(라우터→`ai_provider.get_provider`→FakeProvider) 가능. monkeypatch는 `app.routers.ai.ai_provider.get_provider`를 lambda로 교체해 라우터 호출 시 FakeProvider가 반환되게 함. 라우터 코드 변경 0.

### 5) 신규 테스트 24개 → 모두 1차 통과
회귀 모드(A) 단언과 목표 local-first 모드(B) 단언을 분리 적용 (`docs/ai_rag_test_plan.md` §0-1). 매뉴얼 매칭 케이스만 `== 1`, 차단/저신뢰/sources 0건은 `== 0`.

## diff 규모
- 신규 파일 LOC 합계: ~520줄
- conftest.py 추가 LOC: ~115줄 (기존 138줄 보존, 끝에 추가)
- 기존 파일 1줄도 수정/삭제 없음
- `app/`, `tests/` 외 기존 테스트, `app/migrations/`, `requirements.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `knowledge/` 일체 변경 0
