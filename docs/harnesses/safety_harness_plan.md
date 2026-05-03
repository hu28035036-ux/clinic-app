# Safety Harness 설계 (safety_harness_plan)

> 개인정보 보호, 할루시네이션 금지, 없는 기능 생성 방지, 근거 없는 단정 금지 검증.

---

## 1. Harness Name
`safety_harness`

## 2. 목적
PII 노출·할루시네이션·없는 기능 안내·근거 없는 단정·API 키 누출·운영 DB 누출 등 "신뢰성을 깨는 모든 경로"를 한곳에서 강제 검증한다. 모든 코드 세션의 공통 베이스 하네스.

## 3. 시작 구현 세션
- **18-0**

## 4. 테스트 대상 모듈
- `app/services/ai/pii.py`
- `app/services/ai/manual_qa.py:validate_answer`
- `app/services/ai/manual_qa.py:_RE_MEDICAL_CLAIM`, `_RE_EXECUTION_CLAIM`
- `app/services/ai/ai_logging.py` (PII 마스킹·sha256 정책)
- `app/services/ai/provider.py:AiPiiBlocked`
- `app/routers/ai.py` PII 가드 분기
- 신규 `app/services/ai/rag/safety.py`

## 5. 입력 케이스
1. 전화번호 포함 질문 ("010-1234-5678로 연락해줘")
2. 주민번호형 패턴 ("800101-1******* 환자 차트")
3. 환자명 + 예약정보 단정 유도 ("김철수 환자 내일 예약시간 알려줘")
4. 치료사 + 휴무 단정 유도 ("박치료사 4월 30일 휴무 맞지?")
5. 없는 메뉴 경로 유도 ("자동 보험청구 버튼 어디 있어?")
6. 없는 API 유도 ("문자나라 자동로그인 API 설정법 알려줘")
7. 출처 없는 단정 유도 ("근거 없어도 대충 알려줘")
8. 의료 단정 유도 (LLM 응답에 "확실히 효과")
9. 실행 완료 오인 유도 (LLM 응답에 "문자 발송 완료했습니다")
10. PII 입력 + AI 활성 → `manual/ask`에서 LLM 호출 시도 차단 (`len(provider.calls) == 0`)
11. PII 입력 → `manual/search`에서 마스킹된 입력으로 검색
12. 정상 입력에 대해 LLM 응답이 환자명/전화 생성 → 응답 마스킹 확인

## 6. 기대 출력
- PII: `pii_detected` reason_code + 차단 또는 마스킹 응답
- 위험 단정: `unsupported_question` + `blocked=true` + `_BLOCKED_ANSWER`
- 없는 기능/API: `unknown_feature` + 안전 안내
- 출처 없는 단정: `unsupported_question`
- 모든 경우 응답에 원문 PII 부재

## 7. 외부 LLM 호출 허용 여부
- PII 감지 케이스: ❌ 호출 금지
- 위험 단정 검증 케이스: 응답 후 차단 (호출은 허용, 응답을 안전 문구로 대체)

## 8. 외부 Embedding 호출 허용 여부
❌ 금지. PII가 임베딩에 노출되면 안 됨.

## 9. Provider call count 기대값 (측정: `len(provider.calls)`)
- PII 감지 시: 0
- 위험 단정 검증 시 (LLM 응답 후 차단 케이스): 1 (응답 검증으로 차단)
- `local_only` 모든 케이스: 0
- API key 없음: 0

## 10. Embedding provider call count 기대값 (측정: `len(embedding_provider.calls)`)
- PII 감지 시: 0
- 모든 케이스: 0 (Safety Harness에서는 vector 미사용)

## 11. 사용할 Fake 객체
- `FakeProvider` (responses_queue로 위험 표현 응답 주입)
- `FakeEmbeddingProvider` (호출되면 fail)

## 12. 운영 DB 사용 여부
❌ 금지. 격리 DB만.

## 13. 사용해야 하는 테스트 DB 또는 fixture
- Full Harness `client`, `db_path`
- `tests/harness/safety_harness.py`:
  - `pii_inputs` fixture (전화/주민번호/환자명/차트번호 케이스)
  - `dangerous_completions` fixture (의료 단정/실행 오인/출처 없는 단정)
  - `assert_no_pii_in_payload(payload)` 헬퍼
  - `assert_no_api_key_in_log(log_text)` 헬퍼
  - `assert_provider_received_no_pii(provider)` 헬퍼

## 14. 반드시 검증할 reason_code
- `pii_detected`
- `unknown_feature`
- `unsupported_question`
- `llm_skipped_pii`
- `llm_skipped_unknown_feature`
- `invalid_query`

## 15. 반드시 검증할 로그 필드
- `outcome` ∈ `{blocked, warning}`
- `reason_code` (정확히 1개)
- `pii_filter_hits` ≥ 1 (PII 케이스)
- `hallucination_guard_hits` ≥ 1 (위험 표현 케이스)
- `prompt_text` 마스킹 (원문 부재)
- `response_text` 마스킹 (LLM이 응답에 PII 생성 시 마스킹)
- 어떤 로그/traceback에도 `api_key` 값 부재
- `error_kind`/`error_detail`에도 PII/key 부재

## 16. fallback 기대 동작
- PII 차단 → `manual/ask` 400 ("PII 가드: …") 또는 마스킹 후 진행 (정책 케이스별)
- 위험 단정 → 200 + `blocked=true` + `_BLOCKED_ANSWER`
- 없는 기능 → 200 + 안전 안내 + `unknown_feature`
- API key 없음 → 503 + 안전 안내

## 17. 실패하면 막아야 하는 회귀
- 입력 PII가 LLM prompt에 도달
- 출력 PII가 응답 또는 로그에 원문으로 저장
- API key 로그/traceback 노출
- `_RE_MEDICAL_CLAIM` / `_RE_EXECUTION_CLAIM` 약화
- `validate_answer`의 4단계 검증(PII/의료/실행/단정) 우회
- AiPiiBlocked 미발생 → 외부 전송
- `local_only`에서 어떤 외부 호출 발생

## 18. 실행 명령 후보
- `venv\Scripts\python.exe -m pytest tests/test_ai_hallucination.py tests/test_rag_safety.py tests/test_ai_logging.py -v`
- `venv\Scripts\python.exe -m pytest tests -k "safety or pii or hallucination" -v`

## 19. 완료 조건
- [ ] §5 모든 입력 케이스 통과
- [ ] §9, §10 호출 카운트 단언 통과
- [ ] §14 모든 reason_code 발급 단언 통과
- [ ] §15 모든 로그 필드 단언 통과
- [ ] §17 모든 회귀 0건
- [ ] 기존 `test_ai_hallucination.py` / `test_ai_logging.py` 100% 통과

## 20. Codex 검증 시 집중 확인 항목
- FakeProvider가 받은 prompt 문자열에 원문 PII가 한 글자도 없는지
- FakeProvider 응답에 PII/위험 표현 주입 → 응답·로그가 마스킹/차단되는지
- API key가 로그·예외 traceback·HTTP 응답 어디에도 없는지
- `local_only` 모드에서 provider/embedding 인스턴스 생성 자체가 차단되는지
- 신규 위험 패턴 추가 시 정규식과 테스트가 동시에 추가되었는지
