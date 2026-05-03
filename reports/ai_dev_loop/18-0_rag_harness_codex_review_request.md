# latest_codex_review_request.md — 18-0_rag_harness

## 1. 세션 이름
`18-0_rag_harness` (RAG/Safety/Full 하네스 최소 버전 작성)

## 2. 작업 목표
v1.3.3 동작 회귀 0을 보장하면서 외부 SDK 호출 차단·FakeProvider 재사용·응답 9개 키 계약 단언·`len(provider.calls)` 표준 측정 컨벤션을 도입한 RAG/Safety/Full 하네스 최소 버전을 만든다.

## 3. 변경 파일 목록
신규 8 (LOC ~520) + 수정 1:
- `tests/harness/fake_provider.py` (신규, 64줄)
- `tests/harness/contract.py` (신규, 116줄)
- `tests/harness/rag_harness.py` (신규, 50줄)
- `tests/harness/safety_harness.py` (신규, 76줄)
- `tests/test_full_harness.py` (신규, 9 tests)
- `tests/test_rag_pipeline.py` (신규, 5 tests)
- `tests/test_rag_safety.py` (신규, 6 tests)
- `tests/test_local_only_mode.py` (신규, 4 tests)
- `tests/conftest.py` (수정 — 끝에 §7 SDK monkeypatch + §8 fixture 2개 추가, 기존 1~6단계 1줄도 미수정)

## 4. 변경 요약
- FakeProvider 재사용 helper(`call_count(p)=len(p.calls)`, `last_prompt`, `last_system`, `assert_no_external_call`, `assert_provider_received_no_pii`).
- 응답 키 계약 단언 모듈(`assert_manual_search_contract`, `assert_manual_ask_contract`, `assert_source_item_contract`).
- conftest §7: `_block_sdk_modules()`이 import 시점에 `openai.{OpenAI,Client,AsyncOpenAI}` / `anthropic.{Anthropic,Client,AsyncAnthropic}`을 `_raise_external_call`로 교체. SDK 미설치 환경은 자동 패스.
- conftest §8: `ai_disabled_setting`/`ai_enabled_with_fake` fixture로 라우터 통합 테스트 가능. `app.routers.ai.ai_provider.get_provider`를 monkeypatch해 FakeProvider 반환.
- 24개 신규 테스트가 회귀 모드(A: 매뉴얼 매칭+key/model 있음 → `==1`)와 목표 local-first 모드(B: 차단/0건/저신뢰/PII → `==0`)를 분리 단언.

## 5. 절대 바뀌면 안 되는 기능 (회귀 보호 대상)
- `/api/ai/manual/{search,ask}` 응답 9개+3개 키 + `sources[].{title,path,snippet}`
- AI disabled/API key 없음/model 없음 → 503 + "AI 기능이 꺼져…" 메시지
- 빈 질문 → 400
- `manual_qa.ask_manual_question(db, q, *, provider_override=None)` 시그니처
- `LOW_SCORE_THRESHOLD = 2`
- `_NOT_FOUND_ANSWER`/`_NOT_FOUND_PROMPT`/`_BLOCKED_ANSWER` 문구
- `category="manuals"` 단일 검색 정책
- 기존 18개 AI 테스트 (`test_ai_*`) 동작
- SMS AI / 휴무 AI / health public·admin 권한 분리
- `tests/conftest.py` 1~6단계 격리

## 6. 실행한 테스트 명령
```
venv\Scripts\python.exe -m pytest tests -v
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts\check_db_path.py
```
(`run_check.bat`은 `pause`로 직접 호출이 멈춰 동일 3단계를 수동 실행했다.)

## 7. 테스트 결과 요약
- pytest: **207 passed, 1 skipped, 7 xfailed, 27 warnings in 6.75s** (회귀 0)
- 신규만: **24 passed in 0.20s**
  - test_full_harness.py: 9
  - test_rag_pipeline.py: 5
  - test_rag_safety.py: 6
  - test_local_only_mode.py: 4
- ruff: `All checks passed!`
- check_db_path.py: 정상 종료 (스크립트 단독 실행 시 운영 경로 안내는 의도된 동작 — 테스트 중에는 conftest 4단계 격리가 작동)

## 8. 자동 수정 루프 횟수
**1/5** (1차 만에 통과)

## 9. 5회 실패 여부
No

## 10. 운영 DB 보호 검사 결과
`scripts/check_db_path.py` 정상 종료. 모든 pytest 실행에서 `tests/conftest.py:54-57`의 `assert_safe_db_path()`가 import-time 1차 + session-scoped fixture 2차로 통과 → 격리 DB(`tests/temp/test_clinic_<uuid>.db`)만 사용됨이 입증.

## 11. RAG 하네스 결과
- `test_rag_pipeline.py` 5/5 통과
- 매뉴얼 매칭 케이스: `len(fake.calls) == 1` (회귀 모드 A), `not_found=False`, sources≥1, 응답 9개 키 계약 통과
- 매뉴얼 미매칭 케이스: `len(fake.calls) == 0`, `not_found=True`, sources=[], `confidence="unknown"`, "매뉴얼에서 답을 찾지 못했습니다." 문구 포함
- `manual_search` 단독: `len(fake.calls) == 0` (정의상 LLM 미사용), 키 3개 계약

## 12. API 계약 테스트 결과
- `test_full_harness.py::test_manual_ask_200_contract_with_fake`가 `assert_manual_ask_contract(body)`로 9개 키 + 타입 검증 통과
- `test_full_harness.py::test_manual_search_200_contract`가 `assert_manual_search_contract(body)`로 3개 키 + 타입 검증 통과
- `sources[]` 항목별 `title/path/snippet` 키도 검증 통과
- 신규 optional 키(`reason_code` 등)는 본 세션에서 응답에 추가되지 않았고, 계약 단언에도 포함되지 않음(있어도 OK 정책 유지)

## 13. 할루시네이션 금지 테스트 결과
- `test_safety_dangerous_medical_claim_blocked`: "이 환자는 확실히 효과가 있습니다." 응답 → `blocked=true`, blocked_reason 비어있지 않음, "검증 단계에서 차단" 또는 "관리자에게 확인" 문구 포함
- `test_safety_execution_claim_blocked`: "예약문자를 발송했습니다." 응답 → `blocked=true`
- `test_safety_unknown_feature_question_safe_response`: 매뉴얼에 없는 기능("자동 보험청구") 질문 → `not_found=true` 또는 `blocked=true`. sources 0건이면 `len(fake.calls) == 0` 단언

## 14. PII 보호 테스트 결과
- `test_safety_phone_pii_masked_in_question_and_not_in_prompt`: 전화번호 입력 → `masked_question`에 `[PHONE]` 포함, 원본 부재. **provider가 받은 prompt 전체에 원본 PII 부재** 단언 통과 (`assert_provider_received_no_pii`)
- `test_safety_phone_pii_in_llm_response_masked_in_answer`: LLM 응답에 환각 PII → `answer`에서 사후 마스킹
- `test_safety_birth_pii_masked`: 생년월일 입력 → `masked_question`에 `[BIRTH]` 또는 `[NUM]` 포함
- `test_no_api_key_in_503_response`: 503 응답 본문에 `test-fake-key` / `sk-` 부재

## 15. 기존 SMS AI 회귀 테스트 결과
- `test_ai_sms_validate.py`, `test_ai_sms_draft.py`, `test_ai_sms_draft_hallucination.py` 전체 통과
- pytest 전체 실행에서 회귀 0건. 27개 PytestReturnNotNoneWarning은 18-0 이전부터 존재하던 것 (18-0 작업과 무관, 변동 0)

## 16. 기존 휴무 AI 회귀 테스트 결과
- `test_ai_action_leave.py` 전체 통과 (T1~T29 시나리오 + 회귀)
- 회귀 0건

## 17. 남은 위험 요소
1. **`test_external_sdk_blocked_on_instantiation`이 SDK 인스턴스화 단계만 검증** — SDK 별로 인스턴스화 자체는 통과하고 호출 시 fail하는 패턴은 본 테스트가 PASS로 처리한다. 18-5 직전 `pytest-socket` 또는 동등 도구 도입 결정이 필요 (`docs/ai_harness_overview.md` §4-2).
2. **AiUsageLog 신규 컬럼(reason_code 등) 미적용** — 18-2/18-7 시점에 m012/m015로 추가 결정. 본 세션에서는 응답 optional 키만 계약 호환.
3. **`ai_enabled_with_fake` fixture가 운영 DB 미접근 보장은 conftest 격리에 위임** — db_guard가 테스트 진입 시 검증. fixture 자체는 격리된 SessionLocal만 사용.
4. **conftest §7 monkeypatch는 module attribute만 교체** — 일부 SDK 가 `from openai import OpenAI as _O` 패턴으로 이미 import한 코드는 영향 받지 않음. 다행히 `app/services/ai/openai_client.py`는 lazy import이므로 본 영향 없음, 다만 18-5에서 embedding 클라이언트 추가 시 동일 패턴 강제 필요.

## 18. Codex가 집중 검토할 파일
1. `tests/conftest.py` §7 (외부 SDK monkeypatch) — 모든 lazy import 경로를 막는지 확인
2. `tests/conftest.py` §8 (`ai_disabled_setting` / `ai_enabled_with_fake`) — 다른 테스트에 부수 영향 없도록 cleanup 적절한지
3. `tests/harness/fake_provider.py` — `len(provider.calls)` 컨벤션 일관성, 기존 `FakeProvider` 변경 없음
4. `tests/harness/contract.py` — v1.3.3 응답 키 정의가 실제 `app/services/ai/manual_qa.py` 반환과 1:1 일치
5. `tests/test_rag_safety.py::test_safety_phone_pii_masked_in_question_and_not_in_prompt` — provider가 받은 prompt에 원본 PII가 정말 없는지

## 19. Codex가 반드시 확인할 체크리스트
- [ ] `app/`/`app/migrations/`/`requirements.txt`/`dosu_clinic.spec`/`app/templates/`/`app/static/`/`knowledge/` 변경 0
- [ ] `tests/conftest.py` 1~6단계 격리 부분 변경 0 (§7·§8만 추가)
- [ ] 기존 `tests/test_ai_*.py` 18개 파일 변경 0
- [ ] `pyproject.toml`/`pytest.ini` 변경 0
- [ ] `docs/ai_rag_test_plan.md` §0-0의 "provider call count = `len(provider.calls)`" 표준이 하네스/테스트 코드에서 일관 적용
- [ ] 응답 9개 키(`MANUAL_ASK_REQUIRED`)가 `app/services/ai/manual_qa.py:270-280` 반환 키와 정확히 일치
- [ ] 외부 SDK 호출 시도 시 RuntimeError가 raise (인스턴스화 또는 호출 단계)
- [ ] FakeProvider 받은 prompt에 원본 PII 부재
- [ ] 503/400 응답에 API key 노출 0
- [ ] `local_only` 단언 케이스 4개에서 `len(fake.calls) == 0`
- [ ] `LOW_SCORE_THRESHOLD=2`/`_NOT_FOUND_*`/`_BLOCKED_ANSWER` 문구 보존

## 20. 다음 세션으로 넘어가도 되는지 Claude Code의 자체 판단
**Yes** — 다음 세션(18-1 폴더 구조 생성)으로 진입 가능.

근거:
- 207 passed / 0 failed, 신규 24개 모두 1차 통과, 회귀 0건
- 응답 9개 키 계약 보호 자동 단언 도입 → 18-1 이후 골격 추가 시 자동 회귀 감지
- `len(provider.calls)` 컨벤션 일관 적용 → 18-2 keyword RAG 분리 시 동일 단언 그대로 사용 가능
- 외부 SDK 호출 차단 monkeypatch 작동 확인 → 18-5 vector 도입 직전까지는 보강 불필요
- 운영 DB 미접근 + API key 미노출 + PII 마스킹 모두 통과
- 18-0 체크리스트 §완료 조건 모두 충족, `app/` 0 diff

권고:
- Codex 검증 통과 후 18-1 시작. 18-1은 폴더 골격만이라 회귀 위험이 가장 낮음.
- `docs/ai_rag_current_state.md` §14 18-0 전 선행 TODO 6개 중 §1(`call_count` 컨벤션)·§2(manual_ask 주입 경로)는 본 세션에서 helper(`tests/harness/fake_provider.py`) + monkeypatch 패턴(`ai_enabled_with_fake`)으로 해소됨. §3(FakeEmbeddingProvider)·§4(AiUsageLog 신규 컬럼)·§5(knowledge 카테고리 로직)·§6(SMS/휴무 응답 키 표)는 해당 후속 세션에서 처리.
