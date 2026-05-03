# AI/RAG 현재 상태 스냅샷 (ai_rag_current_state)

> 코드 변경 전 기준점. 이후 구조 변경의 회귀 비교 기준이다.
> 모든 항목은 실제 코드 확인을 거쳤다. 미확인은 "확인 필요"로 명시한다.

---

## 0. 메타

- 스냅샷 작성일: 2026-05-01 (r1) / 2026-05-03 (r2 보정)
- 기준 버전: `APP_VERSION = "1.3.3"` (`app/config.py:10`)
- 빌드 일자: `APP_BUILD_DATE = "2026-05-01"` (`app/config.py:11`)
- AI 라우터 표기 버전: `version: "v1.3-stage1"` (`app/routers/ai.py:162`)

### 0-1. r2 보정 — 19-0 baseline 재고정 시점 stale caveat 정리

본 문서는 **18-0 진입 직전 (v1.3.3)** baseline 으로 작성되었으며, 18-0 ~ 18-8 시리즈 (RAG / Knowledge / Vector / Hybrid / Health) 변경분 일부가 stale 상태다. 19-0 baseline 재고정 시점 (2026-05-03) 에 다음 사항을 보정 인지한다 (19-P-1 §24 + 19-P-2 §10 + 19_refactor_current_state.md §1 ~ §22 정합):

| 라인 | r1 (stale) | 19-0 시점 실측 | 보정 |
|---|---|---|---|
| §1-3 line 39 | `app/routers/ai.py` (~888줄) | **929줄** | 18-AI v1 추가 흐름 (manual_search/ask 보강 + action_leave) 반영 |
| §1-4 line 49 | 마지막 마이그레이션: `m011_employee_leave_unique.py` | **m013_knowledge_vectors.py** | m012 (knowledge_chunks) + m013 (knowledge_vectors) 추가 |
| §1-4 line 50 | 다음 마이그레이션 번호: `m012` | **m014** | 본 19-P 기간 내 미도입 (19-P-2 P-4 / 19-P-8 DEC-D 정합) |
| §1-5-1 line 64 | FakeEmbeddingProvider는 현재 없음 — 18-5에서 신규 작성 필요 | **18-5 완료 — `tests/harness/fake_provider.py` 에 `FakeEmbeddingProvider` 정의됨** | 18-5 vector 하네스 |
| §14 18-0 전 선행 TODO | 18-0 ~ 18-8 진입 전 TODO 6건 | **모두 18-0 ~ 18-8 안에서 처리 완료 (18-AI v1 통합 = release v1.3.3)** | 18-AI 시리즈 종료 |

추가 stale 영역 (본 r2 에서 *전체 재작성하지 않음* — 19-P-1 의 [docs/refactor/19_refactor_current_state.md](refactor/19_refactor_current_state.md) 가 권위 baseline):
- §1 AI/RAG 관련 파일 목록 — 18-1 RAG (`pipeline.py / retriever.py / reranker.py / confidence.py / safety.py / schemas.py`) + 18-3 chunker (`chunker.py / loader.py / normalizer.py / keyword_index.py`) + 18-4 indexer (`indexer.py`) + 18-5 vector (`embeddings.py / store.py / similarity.py`) + 18-7 health (`health.py`) 모두 추가됨.
- §3 manual/ask 동작 — 18-1 RAG pipeline + 18-6 hybrid retriever + 18-7 health.build_admin_status 통합으로 흐름 변경.
- §4 ~ §13 AI Provider / Logging / Settings — 18-AI v1 보강 사항 일부 반영 안 됨.

> **권위 baseline**: 19-P-1 [docs/refactor/19_refactor_current_state.md](refactor/19_refactor_current_state.md) (r2, Codex pass) 가 v1.3.3 + 18-1~18-8 통합 baseline. 본 문서는 *18-AI 진입 직전 v1.3.3 의 historical snapshot* 으로 보존. 19-x 코드 세션은 19_refactor_current_state.md 참조 우선.

---

## 1. AI/RAG 관련 파일 목록

### 1-1. 서비스 레이어
- `app/services/ai/__init__.py`
- `app/services/ai/provider.py` — 추상 Provider + 팩토리(`get_provider`, `KNOWN_PROVIDERS = ("openai","anthropic","local")`)
- `app/services/ai/openai_client.py` — OpenAI 구현
- `app/services/ai/anthropic_client.py` — Anthropic 구현
- `app/services/ai/sms_draft.py` — SMS 초안 생성
- `app/services/ai/manual_qa.py` — 매뉴얼 RAG + LLM Q&A
- `app/services/ai/action_leave.py` — 자연어 휴무 등록
- `app/services/ai/ai_logging.py` — AI 사용 로깅 (PII 마스킹 + sha256)
- `app/services/ai/date_resolver.py` — 날짜 파싱
- `app/services/ai/pii.py` — PII 마스킹/감지
- `app/services/ai/prompts.py` — 프롬프트 템플릿
- `app/services/ai/validators.py` — 응답 검증 유틸

### 1-2. RAG 레이어
- `app/services/rag/__init__.py`
- `app/services/rag/search.py` — 토큰 기반 키워드 검색 (외부 호출 0)
- 인덱스 빌드 도구: `tools/build_knowledge_index.py` (마크다운 → 인덱스)

### 1-3. 라우터
- `app/routers/ai.py` (~888줄)

### 1-4. 모델 / 마이그레이션 (확인 완료 — `app/models/models.py:280-343`)
- `AiSetting` (`models.py:280-302`) — `__tablename__="ai_settings"`. 컬럼: `id, enabled, provider, model, api_key, base_url, max_tokens(512), temperature(0.3), pii_guard_enabled(True), updated_at`
- `AiUsageLog` (`models.py:304-343`) — `__tablename__="ai_usage_logs"`. 컬럼:
  - 기본: `id(uid), ts, provider, model, feature, prompt_chars, completion_chars, prompt_tokens, completion_tokens, latency_ms, status(legacy), error_kind(legacy), actor`
  - m008 확장: `outcome(String 50), error_detail(String 500), prompt_hash(sha256), response_hash(sha256), pii_filter_hits, hallucination_guard_hits, response_used, sms_sent`
  - **원문 prompt/response 미저장 정책 — 해시만 보관**
- `m007_ai_settings.py` — AI 설정 시드(enabled=0)
- `m008_ai_usage_log_extended.py` — AI 로그 컬럼 확장
- 마지막 마이그레이션: `m011_employee_leave_unique.py`
- **다음 마이그레이션 번호: `m012` (이후로만 추가)**

### 1-5. 테스트
- AI 관련: `test_ai_action_leave.py`, `test_ai_sms_draft.py`, `test_ai_sms_validate.py`, `test_ai_manual_qa.py`, `test_ai_health_public.py`, `test_ai_hallucination.py`, `test_ai_sms_draft_hallucination.py`, `test_ai_logging.py`
- (그 외 16개 비-AI 테스트)
- 하네스: `tests/conftest.py`, `tests/harness/{db_guard,seed_data,helpers}.py`

### 1-5-1. FakeProvider (확인 완료 — `tests/conftest.py:104-137`)
- 위치: `tests/conftest.py:112` `class FakeProvider(_ai_provider.AiProvider)`
- 시그니처: `__init__(return_text="…")`, `name="fake"`, `is_ready()=True`, `generate(prompt, system="")`
- **호출 관찰 속성**: `self.calls: list` — 각 호출마다 `{"prompt": ..., "system": ...}` 추가. **`call_count` 별도 속성 없음** → 테스트는 `len(provider.calls)`로 카운트.
- 팩토리: `make_fake_provider(returns="")` (`conftest.py:135`)
- `return_text`가 callable이면 prompt 받아 동적 결정
- 사용 예: `test_ai_action_leave.py:24` `from tests.conftest import FakeProvider`
- **FakeEmbeddingProvider는 현재 없음** — 18-5에서 신규 작성 필요

### 1-5-2. manual/ask provider 호출 관찰 방법 (확인 완료)
현재 라우터(`app/routers/ai.py:658-666`)는 `ai_provider.get_provider(...)`로 매번 새 인스턴스 생성 → 직접 `provider.calls` 접근 어려움. 테스트 패턴:
- `client.app.dependency_overrides`로 `_action_leave_provider` 등 의존성 교체 (예: `test_ai_action_leave.py:86-87`)
- manual_ask는 동일 패턴의 의존성 훅이 없으므로 **18-0 하네스에서 `provider_override` 주입 경로(테스트 hook)를 conftest fixture로 노출하는 방식 검토 필요** (선행 TODO §16)
- 또는 `ai_provider.get_provider`를 monkeypatch (지금까지 일부 테스트가 사용)

### 1-6. 지식 베이스 문서
- `knowledge/manuals/sms_compose.md`
- `knowledge/manuals/no_therapist.md`
- `knowledge/manuals/munjanara_error.md`
- `knowledge/manuals/backup.md`
- `knowledge/manuals/therapist_leave.md`
- `knowledge/manuals/ai_settings.md`
- `knowledge/sms_guides/tone_confirm.md`
- `knowledge/sms_guides/tone_reminder.md`
- `knowledge/sms_guides/tone_reschedule.md`
- `knowledge/sms_guides/tone_noshow.md`

> 매뉴얼 Q&A는 `category="manuals"`만 검색 대상. `sms_guides`는 SMS 톤 가이드용이라 매뉴얼 답변 근거에서 제외 (`app/services/ai/manual_qa.py:13`).

---

## 2. `/api/ai/manual/search` 동작 요약

- 정의: `app/routers/ai.py:567-600` (`manual_search_endpoint`)
- 흐름:
  1. 빈 질문 → 400
  2. `ai_manual_qa.manual_search(question)` 호출 (LLM 미사용, 키워드 RAG만)
  3. `ai_log.log_ai_usage(feature="manual_search", outcome="success" if hits>0 else "warning", prompt_text=masked_question, latency_ms, error_detail="hits=N, top_score=K")`
  4. 결과 그대로 반환

### 2-1. 성공 응답 JSON key (`manual_qa.py:155-169`)
```json
{
  "sources": [{"title": "...", "path": "...", "snippet": "..."}],
  "masked_question": "...",
  "top_score": 0
}
```
- `sources` 항목 키: `title`, `path`, `snippet`

### 2-2. 검색 결과 없음 응답
- 동일 스키마, `sources: []`, `top_score: 0`. (200 OK, 별도 not_found 필드 없음)

### 2-3. 안전 차단 응답
- 현재 `manual_search` 자체에서 안전 차단 분기는 없음. PII 입력은 `pii.scan`으로 마스킹만 하고 검색 진행. (LLM 미사용이라 차단 필요성 낮음)

### 2-4. 오류 응답
- 400: 빈 질문 (`HTTPException(400, "질문(question)을 입력하세요.")`)
- 5xx: 검색 도중 예외 발생 시 `log_ai_error` 후 raise (사용자에게는 FastAPI 기본 500)

---

## 3. `/api/ai/manual/ask` 동작 요약

- 정의: `app/routers/ai.py:603-750` (`manual_ask_endpoint`)
- 흐름:
  1. 빈 질문 → 400
  2. `_get_or_create_setting(db)` 로 `AiSetting` 로드
  3. **차단 분기** (각각 `log_ai_blocked` + `log_ai_setting_change`):
     - `enabled=False` → 503 ("AI 기능이 꺼져 있습니다…")
     - `api_key` 미설정 → 503 ("AI API key 가 설정되지 않았습니다…")
     - `model` 미설정 → 503 ("AI 모델이 지정되지 않았습니다…")
  4. `ai_provider.get_provider(...)` 인스턴스 생성. 실패 시 503 ("AI provider 사용 불가: ... (kind=...)")
  5. `ai_manual_qa.ask_manual_question(db, question, provider_override=prov)` 호출
     - `AiUnavailable` → 503
     - `AiPiiBlocked` → 400 ("PII 가드: ...")
     - `ValueError` → 400
  6. 결과의 `blocked` / `not_found` 분기에 따라 `log_ai_blocked` / `log_ai_warning` / `log_ai_usage` 중 하나 기록
  7. 200 OK + 결과 반환

### 3-1. 성공 응답 JSON key (`manual_qa.py:270-280`)
```json
{
  "answer": "...",
  "sources": [{"title": "...", "path": "...", "snippet": "..."}],
  "confidence": "high|low|unknown",
  "not_found": false,
  "blocked": false,
  "blocked_reason": "",
  "guard_hits": 0,
  "top_score": 0,
  "masked_question": "..."
}
```

### 3-2. 검색 결과 없음 응답 (`manual_qa.py:211-222`)
- HTTP 200
- 동일 9개 키, 단:
  - `answer`: `"매뉴얼에서 답을 찾지 못했습니다. 관리자에게 확인해주세요."`
  - `sources`: `[]`
  - `confidence`: `"unknown"`
  - `not_found`: `true`
  - `blocked_reason`: `"no rag hit"`
  - `top_score`: `0`

### 3-3. Low confidence 응답 (`manual_qa.py:225-236`)
- `top_score < 2` (`LOW_SCORE_THRESHOLD`)일 때 LLM 호출 생략
- `not_found: true`, `blocked_reason: "low rag confidence"`, `sources` 채워짐, `top_score` 실제 값

### 3-4. Provider 없음 응답 (`manual_qa.py:239-250`)
- `not_found: true`, `blocked_reason: "no provider"`

### 3-5. 안전 차단(할루시네이션 가드) 응답 (`manual_qa.py:144-152`)
- HTTP 200, `blocked: true`
- `answer`: `"답변을 생성했지만 검증 단계에서 차단되었습니다. 관리자에게 확인해주세요."`
- `blocked_reason`: 다음 중 하나
  - `"unsafe medical advice"` (의료 단정)
  - `"execution claim blocked"` (실행 완료 오인)
  - `"unsupported claim"` (출처 없는 단정)
- `guard_hits`: PII + 위험표현 적중 합계

### 3-6. 오류 응답
- 400: 빈 질문 / `AiPiiBlocked` / `ValueError`
- 503: AI disabled / API key 없음 / model 없음 / `AiUnavailable`(SDK 미설치, kind="sdk_missing"|"no_api_key"|"disabled"|"unknown_provider")

### 3-7. 프론트에서 의존하는 key (확인 완료 — `app/templates/main.html:5747-5793`)
실제 매뉴얼 Q&A 탭 JS가 사용하는 키:
- `data.not_found` (boolean) — `if(data.not_found)` 분기로 not_found 박스 표시
- `data.answer` (string) — 본문 텍스트
- `data.confidence` (string) — `{high, low, unknown}` 라벨 매핑
- `data.sources[]` 의 `s.title`, `s.path` — 출처 리스트 (snippet은 사용 안 함)
- HTTP 503 / 400 분기 → `j.detail` 안내문

**프론트 사용 키 5개**: `not_found`, `answer`, `confidence`, `sources[].title`, `sources[].path`
**현재 프론트가 사용 안 하지만 응답에는 있는 키**: `blocked`, `blocked_reason`, `guard_hits`, `top_score`, `masked_question`, `sources[].snippet`

**후방호환 보호 대상**: 위 사용 5개는 절대 제거/이름 변경/타입 변경 금지. 미사용 키도 v1.3.3 응답 계약상 유지(추후 프론트 확장 가능성).

---

## 4. AI Provider 호출 흐름

`app/services/ai/provider.py` 기준:

1. 라우터에서 `_get_or_create_setting(db)` 로 `AiSetting` 읽음
2. `get_provider(name, model=, api_key=, base_url=, max_tokens=, temperature=)` 호출
   - `name == "openai"` → lazy import → `OpenAIProvider`
   - `name == "anthropic"` → lazy import → `AnthropicProvider`
   - `name == "local"` → `_LocalStubProvider` 반환 (호출 시 `AiUnavailable("disabled")`)
   - 기타 → `AiUnavailable("unknown_provider")`
3. 인스턴스에서 `.generate(prompt, system="")` → `AiResult(text, prompt_tokens, completion_tokens, raw)`

예외:
- `AiUnavailable(kind, message)` — kind ∈ `{sdk_missing, no_api_key, disabled, unknown_provider}`
- `AiPiiBlocked(fields)` — PII 가드 차단

---

## 5. LLM 호출 조건 (manual_ask 기준)

순서대로:
1. `AiSetting.enabled == True`
2. `api_key`, `model` 모두 설정됨
3. `_rag_search(category="manuals")` 결과 1건 이상
4. `top_score >= LOW_SCORE_THRESHOLD (=2)`
5. provider 인스턴스 정상 생성

위 5개를 모두 통과한 경우에만 외부 LLM 호출.

> SMS draft / action_leave는 별도 게이트. 본 문서 범위 외, 후속 세션에서 동일 정밀도로 보강.

---

## 6. PII 마스킹 / 차단 위치

- 모듈: `app/services/ai/pii.py` (`scan(text) → ScanResult{cleaned, found, has_blocking}`)
- 입력 마스킹:
  - `manual_qa.manual_search()` 진입 직후 (`manual_qa.py:161-162`)
  - `manual_qa.ask_manual_question()` 진입 직후 (`manual_qa.py:202-203`)
- 응답 마스킹:
  - `manual_qa.validate_answer()` 1단계 (`manual_qa.py:117-123`)
- 외부 전송 차단:
  - Provider 호출 전 PII 가드가 차단 시 `AiPiiBlocked(fields)` raise → 라우터에서 400

---

## 7. 할루시네이션 방지 정책 위치

- 시스템 프롬프트: `_MANUAL_SYSTEM_PROMPT` (`manual_qa.py:33-45`) — "매뉴얼 발췌에 없는 내용 금지", "기능명/버튼명/API 만들기 금지", "의료 판단 금지", "AI가 직접 실행했다는 진술 금지"
- 응답 검증: `validate_answer()` (`manual_qa.py:100-152`)
  - `_RE_MEDICAL_CLAIM` (완치/반드시 치료/확실히 효과/...)
  - `_RE_EXECUTION_CLAIM` (문자 발송했/예약 변경했/...)
  - 출처 없는데 단정 표현(반드시/무조건/확실히/항상) 차단
- 사전 차단: `top_score < 2` 면 LLM 미호출

---

## 8. SMS AI / 휴무 AI와 공유하는 모듈

- 공유: `provider.py`, `pii.py`, `ai_logging.py`, `prompts.py`, `validators.py`, `date_resolver.py`
- 매뉴얼 Q&A는 `_rag_search`(rag.search)를 단독 사용. SMS draft / action_leave는 RAG 미사용 (확인 필요 — 현재 구조상 매뉴얼만 RAG로 보임)

---

## 9. AI health public / admin 구조

- `GET /api/ai/health` — admin 전용. SDK 임포트 가능 여부, 설정 enabled, key/model 여부, provider 등 상세 (`app/routers/ai.py` health 핸들러)
- `GET /api/ai/health/public` — 일반 사용자용. enabled 여부 등 최소 정보만
- 권한 분리: v1.3.3에서 명확히 분리됨 (CHANGELOG 기준)

---

## 10. PyInstaller spec — AI 관련 hidden import

`dosu_clinic.spec` 기준:
- `openai`, `anthropic` SDK 서브모듈 자동 수집 (`collect_submodules` 루프, `dosu_clinic.spec:20-29`)
- 명시적 hidden import (`dosu_clinic.spec:32-53`):
  - `app.routers.ai`
  - `app.services.ai`, `app.services.ai.provider`, `app.services.ai.openai_client`, `app.services.ai.anthropic_client`
  - `app.services.ai.pii`, `app.services.ai.prompts`, `app.services.ai.validators`
  - `app.services.ai.ai_logging`
  - `app.services.ai.sms_draft`, `app.services.ai.manual_qa`
  - `app.services.ai.action_leave`, `app.services.ai.date_resolver`
  - `app.services.rag`, `app.services.rag.search`
- 데이터 파일 동봉:
  - `('knowledge', 'knowledge')` — knowledge/ 폴더 통째로 (`dosu_clinic.spec:99`)
  - `collect_data_files('openai')` (`dosu_clinic.spec:109`)

> **신규 모듈 추가 시 spec hiddenimports 등록 필수.** 누락 시 PyInstaller 빌드는 통과해도 런타임 ImportError.

---

## 11. 마이그레이션 마지막 번호

- 마지막: `m011_employee_leave_unique.py`
- 다음: **`m012`** (knowledge_chunks 등 신규 테이블은 m012부터)

---

## 12. 현재 구조에서 리팩터링 시 주의할 점

1. **`/api/ai/manual/search` / `/api/ai/manual/ask` 응답 키는 후방호환 깨지면 안 된다.**
   - 추가 OK. 제거 / 이름 변경 / 타입 변경 금지.
2. **`manual_qa.ask_manual_question()` 시그니처 유지** — 라우터에서 `provider_override=` 키워드로 호출. 테스트가 FakeProvider를 이 인자로 주입.
3. **`_rag_search(category="manuals")` 인터페이스 유지** — 매뉴얼 Q&A의 단일 진입점.
4. **`pii.scan(text)` 반환 형 유지** — `cleaned`, `found`, `has_blocking` 의존 코드 다수.
5. **`AiSetting` 컬럼명 변경 금지** — provider/model/api_key/base_url/max_tokens/temperature/enabled 등.
6. **`AiUsageLog` outcome/feature 값 유지** — 로그 분석 후방호환.
7. **`pyproject.toml` per-file-ignores `app/**`** 풀지 말 것 (대량 포맷 변경 방지).
8. **신규 마이그레이션은 m012 이후로만**, 기존 m001~m011 수정 금지.
9. **`dosu_clinic.spec`에 신규 모듈 hidden import 등록** 필수.
10. **`knowledge/` 데이터 파일 추가 시 spec datas는 폴더 단위라 자동 포함되지만,
    카테고리(`manuals` vs `sms_guides`) 구분이 코드 의존이므로 카테고리 추가 시 코드 동기화 필요.**
11. **`tests/conftest.py`의 4단계 격리 약화 금지** — APPDATA 강제 / DB 경로 강제 / 워커 무력화 / FakeProvider 시드.
12. **`scripts/check_db_path.py` 통과 안 하면 머지 금지.**

---

## 13. 확인 완료 후 남은 미확인 항목 (Open)

- SMS draft / action_leave 라우트 응답 키 전수 (본 스냅샷은 매뉴얼 Q&A 중심) — 회귀 보호용으로 필요 시 18-0/18-2에서 보강
- `knowledge/` 카테고리 결정 로직 (파일명/경로/`meta` 헤더 기반인지) — `app/services/rag/search.py` 추가 점검 필요

> 핵심 4개(프론트 의존 키 / AiUsageLog 컬럼 / FakeProvider 시그니처 / 마지막 마이그레이션)는 §3-7, §1-4, §1-5-1, §11에서 확인 완료.

---

## 14. 18-0 전 선행 확인 TODO

18-0 하네스 작성 직전에 사용자/Claude Code가 함께 점검할 잔여 항목.

- [ ] `tests/conftest.py` FakeProvider에 `call_count` property 추가 또는 `len(.calls)` 사용 컨벤션 확정 (어느 쪽이든 18-0 하네스 작성 시 단언 헬퍼 정의)
- [ ] `manual_ask` 라우트에 FakeProvider 주입 경로 결정 (a) 라우터 의존성 훅 추가 (b) `ai_provider.get_provider` monkeypatch — 18-0에서 (b)로 시작 권장
- [ ] `FakeEmbeddingProvider` 인터페이스 결정 (18-5 시점이지만 18-0 하네스에서 stub 선언만 도입 — 호출되면 fail)
- [ ] `AiUsageLog`에 신규 컬럼(`reason_code`/`ai_mode`/`llm_called`/`embedding_called` 등)을 추가하는 m012의 시점 (18-0에서는 미적용, 18-2 또는 18-7로 미룸)
- [ ] `knowledge/` 카테고리 결정 로직 read-only 확인 (`app/services/rag/search.py`)
- [ ] SMS draft / action_leave 응답 키 표 (회귀 보호 정밀도 향상용 — 18-0 후순위)
