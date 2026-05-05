# AI_MISTAKES_LOG.md

> Claude Code 가 AI 기능 Phase 진행 중 저지른 모든 실수와 재발 방지책을 영구 기록하는 문서.
> 사용자 지시 (2026-05-05): "모든 실수는 문서로 작성해서 기록하고 재실수를 방지한다."
>
> 모든 실수마다 다음 4 항목을 명시한다:
> 1. **무엇** — 실수의 정확한 내용
> 2. **언제 / 어디서** — Phase / 파일 / 시점
> 3. **왜** — 근본 원인 (자만 / 임의 판단 / 문서 미숙독 / 정책 위반)
> 4. **재발 방지** — 다음번에는 어떻게 막을지 구체적 절차

---

## 실수 #001 — Phase 6 의 `POST /api/ai/harness/run` router endpoint 임의 보류

### 무엇

`AI_IMPLEMENTATION_PHASES.md § Phase 6` 의 **구현 대상 3 항목 중 1 항목 (`POST /api/ai/harness/run` 관리자 전용)** 을 구현하지 않은 채 Phase 6 자체 검증 "통과" 를 선언했다.

### 언제 / 어디서

- 시점: 2026-05-05 Phase 6 작업 중
- 영향 문서: `PHASE_06_CLAUDE_SELF_CHECK.md` / `PHASE_06_RUNTIME_TEST_REPORT.md` / `PHASE_06_TO_PHASE_07_AUTO_PROCEED.md`
- 영향 범위: SSOT (`AI_CURRENT_DECISIONS.md § 11 API 설계`) 의 `POST /api/ai/harness/run` 정합 위반

### 왜

1. **임의 판단** — "router 통합 위험" 이라고 자체적으로 판단하고 "향후 Phase" 로 미룸. 문서가 명시한 Phase 6 구현 대상을 임의로 보류한 결정.
2. **자체 10회 검증 회차 7 (Cross-doc 정합성) 의 부실** — SSOT § 11 API 설계 8 endpoint 중 본 endpoint 미구현을 자체 회차 7 에서 검출하지 못함. 회차 10 (자만 없는 판단) 에서도 "router 통합 미구현" 을 *남은 위험* 으로 인정만 했지 *진행 불가 사유* 로 격상하지 않음.
3. **사용자 지적 후 발견** — Claude Code 가 자체 검증 10회 동안 못 잡았고, 사용자의 "문서대로 만들고 있지?" 지적 후에야 누락 자각.

### 재발 방지

1. **Phase 시작 전 체크리스트 작성 강제**:
   - `AI_IMPLEMENTATION_PHASES.md § Phase X` 의 *구현 대상* 모든 항목 (예외 없이) 을 체크박스로 옮긴 뒤 시작.
   - SSOT (`AI_CURRENT_DECISIONS.md § 9 모듈 / § 11 API / § 18 13필드`) 와의 정합 항목도 같은 체크리스트에 포함.
   - 체크박스 미해소 항목이 1건이라도 있으면 자체 검증 통과 선언 금지.
2. **자체 10회 검증 회차 7 강화**:
   - 회차 7 (Cross-doc 정합성) 에서 SSOT § 9 모든 모듈 / § 11 모든 endpoint / § 18 모든 13필드 vs 실제 산출 1:1 매핑.
   - "미구현 → 향후 Phase" 같은 임의 보류 금지. 미구현이면 *진행 불가* 처리하고 사유 명시.
3. **"위험" 을 임의 보류 사유로 사용 금지**:
   - 위험은 *작업 후 검증 결과* 로 평가. 작업 전에 "위험성" 으로 작업 자체를 보류 금지.
   - 정말 위험이 크면 *사용자에게 명시적으로 보류 동의 요청* 후 결정.
4. **회차 10 (자만 없는 판단) 의 "남은 위험" 격상 기준 명시**:
   - 남은 위험 중 *해당 Phase 구현 대상에 명시된 항목* 이 있으면 → *진행 불가* 로 격상.
   - 단순 *후속 보강 가능 항목* 은 남은 위험 유지.

---

## 실수 #002 — Phase 6 CI 통합 임의 보류

### 무엇

`AI_IMPLEMENTATION_PHASES.md § Phase 6` 와 `AI_HARNESS_PLAN.md § 6` 의 **CI 통합** 명시를 "CI 환경 부재" 를 핑계로 보류했다.

### 언제 / 어디서

- 시점: 2026-05-05 Phase 6 작업 중
- 영향: `.github/workflows/` 디렉토리 부재 → CI 자동 실행 미구현

### 왜

1. **임의 판단** — "프로젝트에 `.github/workflows/` 가 없으니 CI 통합은 향후 Phase" 라고 자체 결정.
2. **문서 의도 무시** — `AI_HARNESS_PLAN.md § 6` 는 "CI 환경에서는 자동 실행 (Phase 6부터)" 로 *Phase 6 부터 강제* 라고 명시. 환경 부재가 정당한 보류 사유가 아니라 *환경 신설* 이 Phase 6 작업 범위였음.

### 재발 방지

1. **"환경 부재" 가 작업 보류 사유가 되지 않는다**:
   - 문서가 명시한 작업 범위에 *환경 신설* 이 포함되면 환경부터 신설.
   - 신설이 운영에 영향을 줄 가능성이 있으면 사용자 확인.
2. **체크리스트에 *환경 / 인프라* 항목도 포함**:
   - "GitHub Actions workflow 파일 신설" 같은 인프라 작업도 Phase 시작 전 체크리스트에 반영.

---

## 실수 #003 — `ai_safety.py` 모듈 미구현 (SSOT § 9 모듈 구조 정합 위반) — **보강 완료**

### 무엇

`AI_CURRENT_DECISIONS.md § 9 모듈 구조` 에 명시된 10 모듈 중 `ai_safety.py` 1 모듈이 Phase 1~6 중 어디에서도 구현되지 않았다.

### 언제 / 어디서

- 누적 누락: Phase 1 ~ Phase 6 (SSOT 명시 후 6 Phase 진행 동안 미발견)
- SSOT 위치: `AI_CURRENT_DECISIONS.md § 9` (10 모듈 목록)

### 왜

1. **각 Phase 의 *구현 대상* 에 `ai_safety.py` 명시 누락** — `AI_IMPLEMENTATION_PHASES.md` 의 Phase 1~6 어디에도 본 모듈을 직접 구현 대상으로 명시하지 않음. SSOT § 9 와 Phase 별 구현 대상 사이의 불일치.
2. **Phase 별 자체 검증이 § 9 vs 산출 1:1 매핑을 안 함** — 회차 7 (Cross-doc 정합성) 에서 § 9 모듈 10 항 모두 점검 의무가 명시되지 않았음.

### 보강 (2026-05-05)

- ✅ `app/ai/ai_safety.py` 신규 — Privacy / Hallucination 검사 helper 단일 원천
- ✅ `PRIVACY_FORBIDDEN_KEYS` (12 키) / `FORBIDDEN_PHRASES` (4 문구) 상수
- ✅ `check_privacy_payload(payload)` / `check_hallucination(parsed, ...)`  순수 함수
- ✅ `app.ai.ai_harness` 가 `ai_safety` 를 import (단일 원천 보장)

### 재발 방지

1. **AI_IMPLEMENTATION_PHASES.md 갱신** — Phase 별 구현 대상에 SSOT § 9 모듈 1:1 매핑 표 추가. 어느 Phase 에서 어느 모듈을 만드는지 명시.
2. **자체 검증 회차 7 강화** — § 9 모듈 10 항 / § 11 endpoint 8 항 / § 18 13필드 모두 체크리스트화.

---

## 운영 원칙

### 실수 기록 시점

- 발견 즉시 본 문서에 항목 추가.
- Phase 자체 검증 시 SSOT 위반 / 임의 판단을 1건이라도 발견하면 본 문서에 추가하고 *진행 불가* 처리.
- 사용자 지적으로 발견된 실수도 *Claude Code 가 직접* 본 문서에 추가 (사용자가 작성하지 않음).

### 실수 분류

- **A 등급** — Phase 구현 대상 명시 항목 미구현 / 정책 위반 (예: DB 직접 수정 / 외부 API 로 PII 전송 / 승인 없이 실행)
- **B 등급** — SSOT 정합 위반 / 임의 판단으로 보류
- **C 등급** — 자체 검증 누락 / 표현·명명 일관성 부재

현재 기록:
- #001 — B 등급 (Phase 6 구현 대상 명시 항목 임의 보류 → 결과적으로 A 등급에 가까움)
- #002 — B 등급
- #003 — B 등급

---

## 실수 #004 — SSOT § 11 의 commands router endpoint 미구현 (Phase 1~6 누적)

### 무엇

`AI_CURRENT_DECISIONS.md § 11 API 설계` 의 endpoint 8개 중 7개 (`POST /api/ai/commands/parse`,
`select-patient`, `select-treatment`, `approve`, `reject`, `GET /api/ai/commands/{id}`,
`GET /api/ai/commands/logs`) 가 Phase 1~6 어디에서도 구현되지 않음. 본 7개 endpoint
중 Phase 8 인 `POST /api/ai/harness/run` 만 Phase 6 보강에서 추가됨.

### 언제 / 어디서

- 누적 누락: Phase 1 ~ Phase 6
- SSOT 위치: `AI_CURRENT_DECISIONS.md § 11`
- AI_IMPLEMENTATION_PHASES.md 어느 Phase 도 본 7개 endpoint 를 *구현 대상* 으로 명시하지 않음

### 왜

1. **SSOT 와 PHASES 의 정합 부족** — § 11 endpoint 가 어느 Phase 에서 구현되는지 매핑이 없음.
2. **각 Phase 는 모듈 + 단위 테스트 + (Phase 6 부터) router 만 다룸** — 일반 사용자용 commands router 는 별도 작업으로 인식.

### 재발 방지

1. **SSOT § 11 매핑 표 추가 필요** — 각 endpoint 가 어느 Phase 에서 구현되는지 명시.
2. **본 시점 결정 보류** — Phase 7~11 진행 중에는 본 endpoint 를 추가로 *임의 구현하지 않음*. 사용자 결정에 따라 후속 Phase 에서 처리.
3. **실수 #001 재발 방지 체크리스트 (Phase 시작 전)** 에 본 항목 인지 명시 — *명시 구현 대상이 아니면 추가 금지*.

---

### 재발 방지 누적 규칙 (모든 후속 Phase 에 적용)

1. **Phase 시작 전 체크리스트 작성** — 구현 대상 + SSOT § 9/§ 11/§ 18 정합 + 환경 / 인프라 항목.
2. **체크박스 미해소 시 자체 검증 통과 선언 금지**.
3. **"위험" / "환경 부재" 를 임의 보류 사유로 사용 금지**.
4. **자체 검증 회차 7 (Cross-doc 정합성)** 에서 SSOT 모든 § 항목 1:1 매핑 강제.
5. **회차 10 (자만 없는 판단)** 에서 *남은 위험* 중 Phase 구현 대상 항목이 있으면 → *진행 불가* 격상.
6. **모든 실수는 본 문서에 즉시 기록**.
