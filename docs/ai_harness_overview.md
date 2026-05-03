# AI/RAG 하네스 전략 개관 (ai_harness_overview)

> 코드 작성 전 모든 도메인의 하네스를 먼저 잡는 이유와 분리 원칙.
> 본 문서는 **개관**만. 각 하네스의 fixture/시나리오/단언은 `docs/harnesses/*.md`,
> 컴포넌트별 매핑은 `docs/harnesses/component_harness_matrix.md`,
> 테스트 매트릭스 전체는 `docs/ai_rag_test_plan.md` 참조.

---

## 0. 하네스를 먼저 작성하는 이유

1. **회귀 방지**: v1.3.3 응답 키 / SMS AI / 휴무 AI 동작은 절대 깨지면 안 된다. 하네스가 없으면 리팩터링 중 미세 깨짐을 잡지 못한다.
2. **변경 영향 격리**: chunker/vector 같은 신규 도메인이 기존 RAG에 침범하는지 자동 감지.
3. **외부 API 호출 0 보장**: 모든 단위/통합 테스트는 FakeProvider만 쓴다. 실제 SDK 호출이 새어나가는 경로를 사전에 막는다.
4. **Local-First 검증 자동화**: `len(provider.calls) == 0` / `len(embedding_provider.calls) == 0` 단언으로 "local_only에서 외부 호출 없음"을 매번 보장.
5. **Codex 검증 자동화**: Codex가 독립 확인할 항목(`ai_codex_review_protocol.md` §5)을 코드로 표현 — 사람의 자유 검토 의존도 감소.

---

## 1. 하네스 분리 원칙

도메인별로 하네스를 분리한다. 하나의 거대 conftest에 몰아넣지 않는다.

| 하네스 | 책임 | 모듈 |
|---|---|---|
| **Full** | 전체 통합·앱 부팅·라우터·DB 격리 | `tests/conftest.py` + `tests/harness/{db_guard,seed_data,helpers}.py` |
| **RAG** | 검색·근거·confidence·degrade | `tests/harness/rag_harness.py` |
| **Safety** | PII·API key·운영 DB 가드·할루시네이션 가드 | `tests/harness/safety_harness.py` |
| **Chunk** | 청킹 결정성·경계·메타데이터 | `tests/harness/chunk_harness.py` |
| **Vector** | 임베딩·벡터 store·local_only 차단 | `tests/harness/vector_harness.py` |
| **Hybrid** | keyword+vector 통합·가중·fallback | `tests/harness/hybrid_harness.py` |

분리 효과:
- 도메인 변경이 다른 도메인 테스트를 깨지 않는다.
- fixture 결합도 ↓, 단일 책임 ↑.
- Codex가 변경 범위를 빠르게 파악.

---

## 2. 각 하네스 역할 (한 줄 요약)

- **Full Harness**: TestClient + 격리 DB + seed + 기본 FakeProvider 시드. 모든 통합 테스트의 토대.
- **RAG Harness**: 매뉴얼 fixture / pipeline fixture / `expect_no_external_call` 헬퍼.
- **Safety Harness**: PII/API key/운영 DB/할루시네이션 패턴 케이스를 한곳에 모음.
- **Chunk Harness**: 동일 입력→동일 chunk(결정성), heading/코드블록 보호, content_hash 안정성.
- **Vector Harness**: FakeEmbeddingProvider, vector_store fixture, 차원/실패/local_only 차단.
- **Hybrid Harness**: α/β 가중, vector 비활성 시 keyword fallback, dedup.

---

## 3. component_harness_matrix의 역할

각 RAG 구성요소(20여 개)가 어떤 하네스로 검증되는지 ●로 표시한 표.
- 새 컴포넌트 추가 시 어느 하네스에 fixture를 넣을지 즉시 결정.
- 하네스 누락(어느 하네스에도 없는 컴포넌트) 검출.
- Codex가 "이 컴포넌트가 정말 검증되고 있는가"를 매트릭스로 확인.

상세는 `docs/harnesses/component_harness_matrix.md`.

---

## 4. 외부 API 호출 금지 원칙 — **단계별 정책**

모든 하네스는 **실제 외부 API 호출을 절대 발생시키지 않는다.** 단계별 강제 수준은 다음과 같다.

### 4-1. 18-0 ~ 18-4 (현재 단계)
- conftest 단계에서 `openai.OpenAI`, `anthropic.Anthropic` 등 SDK 클래스 monkeypatch → 호출 시 즉시 RuntimeError.
- 모든 LLM 경로 `FakeProvider`만, 모든 Embedding 경로 `FakeEmbeddingProvider`(18-5에서 신규 작성)만.
- 실제 외부 API 호출이 발생하면 **테스트 실패**.

### 4-2. 18-5 vector/embedding 구현 **직전** — 강화 시점
다음 중 하나의 차단 도구를 도입한다 (별도 ADR로 18-5 직전 결정):
- (a) `pytest-socket` — `disable_socket()` autouse fixture로 네트워크 전면 차단
- (b) `httpx`/`requests` 레벨 monkeypatch 확대
- (c) 환경변수 + provider/embedding factory에서 명시적 RuntimeError

이 시점이 강화 필수인 이유: embedding 구현은 외부 API 호출 표면이 가장 넓어지는 첫 지점.

### 4-3. 18-8 — 최종 확인
PyInstaller 검증 단계에서 네트워크 차단 정책 최종 확정. 위반 시 머지 금지.

> 이 정책은 cost 보호 + 재현성 보호 + 사고 방지를 동시에 만족한다. (`docs/ai_rag_test_plan.md` §3-8 참조)

---

## 5. FakeProvider / FakeEmbeddingProvider 사용 원칙

### FakeProvider — 현재 구현 기준 (`tests/conftest.py:112-137`)
- 시그니처: `generate(prompt: str, system: str = "") -> AiResult`
- **현재 노출 속성**: `self.calls: list` — 호출마다 `{"prompt": ..., "system": ...}` append. 다른 속성은 없음.
- **provider call count 측정**: `len(provider.calls)`. 이것이 표준 표현.
- 응답 결정: `__init__(return_text=...)` 또는 callable 주입. (`responses_queue`는 신규 후보 — 필요 시점에만 도입, 기존 `self.calls` 구조 보존 전제)
- 팩토리: `make_fake_provider(returns="")` (`conftest.py:135`)
- **18-0 정책**: 기존 FakeProvider를 크게 바꾸지 않고 `len(.calls)`로 검증. `last_prompt` / `last_system` / `call_count` property는 helper에서 제공할 수 있으나 "선택 도입"이며 기존 `self.calls`와 반드시 일치.

### FakeEmbeddingProvider — 18-5에서 신규 작성
- 시그니처: `embed_documents(list[str]) -> list[list[float]]` / `embed_query(str) -> list[float]`
- 결정적 hash 기반 임베딩 (동일 입력 → 동일 벡터)
- 호출 카운트: 동일 컨벤션 (`len(embedding_provider.calls)`)
- `dimension` 고정 (테스트 fixture에서 설정)
- `local_only` 모드에서 factory가 인스턴스 생성을 차단 (instance조차 만들지 않음)
- 18-0~18-4까지는 **호출되면 fail이 정책** — 카운트 단언은 0으로만 사용

### 절대 사용 금지
- 실제 OpenAI/Anthropic SDK
- 네트워크 호출
- `temperature=0` 기반 LLM snapshot

---

## 6. 운영 DB 사용 금지

- 모든 하네스는 `tests/conftest.py`의 격리 경로(`tests/temp/test_clinic_<uuid>.db`)만 사용.
- `tests/harness/db_guard.assert_safe_db_path()`가 운영 경로(`%APPDATA%\도수치료예약\clinic.db`) 감지 시 즉시 fail.
- `scripts/check_db_path.py`는 `run_check.bat`에서 매번 실행.
- 하네스 fixture가 prod DB를 열 가능성이 있는 코드 경로를 도입하면 즉시 fail.

---

## 7. local_only / local_first 검증 원칙

각 하네스는 모드별 단언을 강제한다.

### local_only
- 모든 시나리오에서 `len(provider.calls) == 0`
- 모든 시나리오에서 `len(embedding_provider.calls) == 0`
- 외부 API key 없는 환경에서도 정상 동작 (keyword RAG·DB 조회·규칙 응답)
- LLM/Embedding factory 자체가 인스턴스 생성을 차단

### local_first (기본)
- sources 부족 / 저신뢰 / PII / unknown_feature 분기에서 `len(provider.calls) == 0`
- 게이트 통과한 케이스에 한해 `len(provider.calls) == 1`
- `reason_code`가 `llm_skipped_*`로 정확히 발급

### ai_assist
- sources 충분 + 게이트 통과 시 `len(provider.calls) == 1`
- sources 0건일 때는 여전히 `len(provider.calls) == 0`

---

## 8. 신규 하네스 추가 절차

1. 본 문서 §1 표에 추가
2. `docs/harnesses/<name>_harness_plan.md` 생성 (20개 공통 섹션, 본 폴더 다른 하네스 포맷 참고)
3. `docs/harnesses/component_harness_matrix.md`에 컬럼 추가 + 매핑 표시
4. `tests/harness/<name>_harness.py` 생성
5. `docs/ai_docs_index.md` §1-4 보강
6. 첫 사용 세션의 체크리스트(`docs/checklists/18-X_*.md`)에서 참조

---

## 9. 본 문서 범위 외

- 실제 fixture 코드 작성 (18-0)
- 실제 테스트 케이스 작성 (각 세션)
- pytest 플러그인 도입 결정 (`pytest-socket` 등)은 18-8까지 보류
