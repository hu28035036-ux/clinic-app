# latest_codex_review_request.md — 18-1_structure_refactor

## 1. 세션 이름
`18-1_structure_refactor` (RAG / Knowledge / Vector 폴더 구조 생성)

## 2. 작업 목표
`app/services/ai/{rag,knowledge,vector}/` 14개 신규 모듈을 골격 + stub 으로 만든다. 실제 RAG 동작은 0 변경. v1.3.3 응답 9+3 키 계약을 코드(`schemas.Source`/`Answer`)로 1:1 고정. 18-0 하네스 회귀 0. 사용자 명시 "PyInstaller spec 수정 금지" 준수.

## 3. 변경 파일 목록 (신규 18, 수정 0)
**`app/services/ai/rag/`** (6): `__init__.py`, `schemas.py`, `safety.py`, `prompts.py`, `pipeline.py`, `retriever.py`
**`app/services/ai/knowledge/`** (4): `__init__.py`, `loader.py`, `normalizer.py`, `keyword_index.py`
**`app/services/ai/vector/`** (4): `__init__.py`, `embeddings.py`, `store.py`, `similarity.py`
**`tests/`** (4, 사용자 명시): `test_ai_full_harness.py`, `test_ai_manual_rag_harness.py`, `test_ai_manual_rag_contract.py`, `test_ai_safety_harness.py`

기존 파일 변경 **0건**.

## 4. 변경 요약
- 14개 신규 모듈은 모두 빈 골격 + stub. 실제 로직은 `NotImplementedError` 또는 stub 반환.
- `schemas.Source`/`Answer` 가 v1.3.3 응답 9+3 키와 1:1 dataclass 정합.
- `prompts.py` v1 = 현행 `manual_qa._MANUAL_SYSTEM_PROMPT` 1:1 인용 (원본 미수정).
- `ALL_REASON_CODES` 29개 정의 + `unsupported_claim` 별칭 부재 자동 단언.
- 신규 모듈은 `manual_qa`/`rag.search` 를 import 하지 않음 (circular 회피).
- 48개 신규 테스트 (사용자 명시 4개 파일) 모두 통과 + 기존 207 테스트 0 diff (전체 255 passed).

## 5. 절대 바뀌면 안 되는 기능 (회귀 보호 대상)
- `/api/ai/manual/{search,ask}` 응답 9+3 키 + `sources[].{title,path,snippet}` 보존
- AI disabled / API key 없음 / model 없음 → 503 + "AI 기능이 꺼져…" 메시지
- 빈 질문 → 400
- `manual_qa.ask_manual_question(db, q, *, provider_override=None)` 시그니처 + `LOW_SCORE_THRESHOLD=2`
- `_NOT_FOUND_ANSWER`/`_NOT_FOUND_PROMPT`/`_BLOCKED_ANSWER` 문구
- `category="manuals"` 단일 검색 정책
- `app.services.rag.search.search` / `reset_cache` 시그니처
- 기존 18개 테스트 동작
- 18-0 의 4개 테스트 파일 + helper 6개 (1줄도 미수정)
- conftest.py 1~8단계 (18-0 형태 그대로)

## 6. 실행한 테스트 명령
```
venv\Scripts\python.exe -m pytest tests/test_ai_full_harness.py tests/test_ai_manual_rag_harness.py tests/test_ai_manual_rag_contract.py tests/test_ai_safety_harness.py -v
venv\Scripts\python.exe -m pytest tests -v
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts\check_db_path.py
```

## 7. 테스트 결과 요약
- 신규 4개 파일: **48 passed in 0.40s**
- 전체: **255 passed, 1 skipped, 7 xfailed, 27 warnings in 6.84s** (회귀 0, 18-0 207 + 18-1 48)
- ruff: `All checks passed!` (`--fix` 적용 후)
- check_db_path.py: 정상

## 8. 자동 수정 루프 횟수
**4/5** (1차: import 패턴 1 fail → 2차: import 패턴 1 fail → 3차: 48 pass → 4차: ruff `--fix`)

## 9. 5회 실패 여부
No

## 10. 운영 DB 보호 검사 결과
`scripts/check_db_path.py` 정상 종료. 모든 pytest 실행에서 `tests/conftest.py:54-57` 의 `assert_safe_db_path()` 가 import-time 1차 + session-scoped fixture 2차로 통과. 신규 14개 모듈은 DB 접근 없음 (모두 stub).

## 11. RAG 하네스 결과
- `test_ai_manual_rag_harness.py` 19/19 통과
- 매뉴얼 매칭 케이스: `len(fake.calls) == 1` (회귀 모드 A) 유지
- 매뉴얼 미매칭 케이스: `len(fake.calls) == 0` (모든 모드 공통) 유지
- `Source` 9 키 + `Answer` 9+5 필드 단언 통과
- `reason_code` 29개 + `AI_MODE_*` 3개 + `unsupported_question` 단일 표준 단언 통과

## 12. API 계약 테스트 결과
- `test_ai_manual_rag_contract.py` 9/9 통과
- manual/search 3개 키 (`sources/masked_question/top_score`) 모두 응답 존재 확인
- manual/ask 9개 키 (`answer/sources/confidence/not_found/blocked/blocked_reason/guard_hits/top_score/masked_question`) 모두 응답 존재 확인
- `sources[].{title,path,snippet}` 3개 키 모두 응답 존재 확인
- 신규 optional 5개 키는 18-1 시점에 응답에 부재 (정상 — 18-2 이후 추가 가능)

## 13. 할루시네이션 금지 테스트 결과
- `test_ai_safety_harness.py::test_safety_medical_claim_still_blocked`: "확실히 효과" → `blocked=true` (회귀 0)
- `test_safety_execution_claim_still_blocked`: "예약문자 발송" → `blocked=true` (회귀 0)
- `test_safety_unknown_feature_safe_response`: 자동 보험청구 → `not_found=true` 또는 `blocked=true` + sources 0건이면 LLM 호출 0

## 14. PII 보호 테스트 결과
- `test_safety_phone_pii_in_question_still_masked`: 전화번호 입력 → `[PHONE]` 마스킹 + provider prompt 미도달 (회귀 0)
- `test_safety_phone_pii_in_llm_response_still_masked`: LLM 응답에 환각 PII → `answer` 사후 마스킹 (회귀 0)
- `test_safety_birth_pii_in_question_still_masked`: 생년월일 → `[BIRTH]` 또는 `[NUM]` 마스킹 (회귀 0)
- `test_safety_no_api_key_in_503_response`: 503 응답 본문에 API key 부재

## 15. 기존 SMS AI 회귀 테스트 결과
- `test_ai_sms_validate.py`/`test_ai_sms_draft.py`/`test_ai_sms_draft_hallucination.py` 전체 통과 (회귀 0)
- 27개 PytestReturnNotNoneWarning 은 18-0 이전부터 존재 — 18-1 작업과 무관

## 16. 기존 휴무 AI 회귀 테스트 결과
- `test_ai_action_leave.py` 전체 통과 (T1~T29 회귀 0)

## 17. 남은 위험 요소
1. **PyInstaller spec hidden import 미등록** — 사용자 명시 지시로 본 세션은 `dosu_clinic.spec` 0 diff. 18-1 시점에는 라우터/기존 모듈이 신규 14개 모듈을 import 하지 않으므로 빌드 영향 0. **18-2 keyword RAG 분리 시 라우터/`manual_qa` 가 신규 모듈을 import 하기 시작 → spec 등록 필수**. 누락 시 빌드 통과 + 런타임 ImportError 위험. (`docs/checklists/18-2_keyword_rag_refactor_checklist.md` §2 또는 §완료 조건 보강 권장)
2. **18-1 신규 모듈이 라우터/기존 코드와 단절** — 14개 모듈은 어디서도 import 되지 않음. import-only smoke 외에는 동작 검증 불가능. 의도적 — 18-2 에서 라우터/`manual_qa` 가 점진 채택 시 본격 검증.
3. **`pipeline.run_manual_qa` / `retriever.retrieve` / `loader.load_documents` 등은 모두 NotImplementedError** — 호출되지 않으므로 위험 0이나, 18-2 에서 라우터가 본 함수를 호출하기 시작하면 즉시 fail. 18-2 작업 시 stub → 실제 구현 교체가 첫 순서.
4. **`tests/conftest.py` 의 `ai_enabled_with_fake` fixture 가 `app.routers.ai.ai_provider.get_provider` 를 monkeypatch** — 18-1 도 동일 패턴 사용 (test_ai_full_harness, test_ai_manual_rag_contract). 라우터가 lazy import 패턴을 바꾸면 monkeypatch 회피 위험. 현재는 안전.
5. **import 패턴 함정 발견 + 기록** — `from app.services.rag import search` 가 함수를 export 함. 18-2 에서 신규 `keyword_index` 모듈을 만들 때 동일 함정 재발 가능. `__init__.py` 에 함수 직접 export 금지 컨벤션을 18-2 시점에 결정 권장.

## 18. Codex 가 집중 검토할 파일
1. `app/services/ai/rag/schemas.py` — `Source`/`Answer` 필드가 v1.3.3 응답 키와 정확히 1:1, `ALL_REASON_CODES` 29개 누락 없음
2. `app/services/ai/rag/prompts.py` — v1 프롬프트가 `manual_qa._MANUAL_SYSTEM_PROMPT` 와 1글자도 안 다른지 (`test_prompts_v1_matches_current_manual_qa_system` 검증)
3. 14개 신규 모듈의 import 의존성 — `manual_qa` / `rag.search` 를 import 하지 않는지 (circular 회피)
4. `tests/test_ai_full_harness.py::test_existing_rag_search_still_importable` — `importlib` + `sys.modules` 패턴이 정확
5. 기존 파일 0 diff (특히 `app/**`, `tests/conftest.py`, `tests/test_ai_*.py` 18개)

## 19. Codex 가 반드시 확인할 체크리스트
- [ ] `app/` 의 기존 파일(manual_qa, provider, pii, rag/search 등) 1줄도 변경 없음
- [ ] `tests/conftest.py` 18-0 형태 그대로 (0 diff)
- [ ] 18-0 의 4개 테스트 파일 + 4개 helper 모두 0 diff
- [ ] `dosu_clinic.spec` / `requirements.txt` / `pyproject.toml` / `pytest.ini` 0 diff
- [ ] DB 마이그레이션 추가 0
- [ ] knowledge/ / static/ / UI 변경 0
- [ ] `app.services.ai.rag.schemas.Source` 의 dataclass 필드 ⊇ `{title, path, snippet}`
- [ ] `Answer` 필수 9개 필드 모두 존재 + optional 5개 모두 존재
- [ ] `ALL_REASON_CODES` 에 `unsupported_question` 포함 + `unsupported_claim` 부재
- [ ] `prompts.PROMPTS["manual_qa.system"]["v1"]` == `manual_qa._MANUAL_SYSTEM_PROMPT`
- [ ] `pipeline.run_manual_qa` / `retriever.retrieve` / `loader.load_documents` 모두 `NotImplementedError` raise
- [ ] 14개 신규 모듈 모두 독립 import 가능 (circular 0)
- [ ] manual/{search,ask} 응답 9+3 키 단언 (`assert_manual_ask_contract`/`assert_manual_search_contract`) 통과
- [ ] PII 마스킹 / 위험 단정 차단 / API key 미노출 회귀 0
- [ ] 18-2 진입 전 spec hidden import 등록 항목을 18-2 체크리스트에 명시 또는 별도 보강

## 20. 다음 세션으로 넘어가도 되는지 Claude Code 의 자체 판단
**Yes** — 18-2 (keyword RAG 분리) 진입 가능.

근거:
- pytest 255 passed / 0 failed (회귀 0), 신규 48 모두 1차 통과 후 ruff 자동 정렬 1회로 마무리
- 응답 9+3 키 계약을 `schemas` 와 `tests/harness/contract.py` 양쪽에서 강제 → 18-2 keyword RAG 분리 중 발생할 회귀를 즉시 감지
- `prompts.py` v1 = 현행 시스템 프롬프트 1:1 → 18-2 에서 라우터/`manual_qa` 가 v1 을 채택할 때 1글자 변동도 잡힘
- 14개 신규 모듈은 어디서도 import 되지 않으므로 18-2 진입 시 영향 0 — 안전한 출발선
- `ai_enabled_with_fake` fixture 가 라우터 통합 테스트를 안정 지원 → 18-2 분리 후에도 동일 단언 그대로 사용 가능

권고:
- Codex 검증 통과 후 18-2 시작.
- **18-2 첫 단계**: spec hidden import 등록을 18-2 체크리스트에 추가하고, `pipeline`/`retriever`/`keyword_index` stub 을 실제 구현으로 교체 후 라우터/`manual_qa` 가 본 모듈을 import 하도록 점진 이전.
- `current_state` §14 18-0 전 선행 TODO 중 §3 (FakeEmbeddingProvider) / §4 (AiUsageLog 신규 컬럼) / §5 (knowledge 카테고리 로직) / §6 (SMS·휴무 응답 키 표) 는 본 세션 범위 외.
