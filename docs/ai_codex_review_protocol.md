# Codex 검증 프로토콜 (ai_codex_review_protocol)

> Claude Code가 자체 테스트 통과 후 Codex 검증용 패키지를 자동 작성하고,
> 사용자가 Codex에 최소 문구로 위임하는 절차.
> 본 문서는 **Claude Code 측 작성 책임 + 사용자 위임 문구 + Codex 검증 항목**을 정의한다.
>
> 절차 자체는 `ai_code_session_protocol.md`, 규칙은 `AI_WORKING_RULES.md` §4와 함께 본다.

---

## 0. 핵심 원칙

1. Claude Code의 자체 테스트 통과는 최종 완료가 아니다.
2. Codex 검증은 다음 세션 진입의 **필수 게이트**.
3. Codex는 Claude Code 요약을 **맹신하지 않는다** — 실제 diff·변경 파일·테스트 결과·로그를 독립적으로 확인한다.
4. Codex 검증이 종료되기 전에는 다음 세션으로 진입 금지.
5. 사용자는 표준 위임 문구 한 줄만 Codex에 전달하면 된다.

---

## 1. Claude Code의 자동 작성 책임

세션 종료 시 Claude Code는 다음을 자동 작성한다(`ai_code_session_protocol.md` §5/§6).

### 1-1. 성공 시 (5회 이내 통과)
- `reports/ai_dev_loop/latest_test_report.md`
- `reports/ai_dev_loop/latest_fix_summary.md`
- `reports/ai_dev_loop/latest_codex_review_request.md` ← **본 문서 §3 형식**
- 세션별 영구 보존본 3개

### 1-2. 실패 시 (5회 실패)
- `reports/ai_dev_loop/latest_failure_report.md`
- `reports/ai_dev_loop/latest_codex_review_request.md` ← **본 문서 §3 형식 + 실패 진단 모드**
- 세션별 영구 보존본 2개

작성하지 않으면 세션 종료 불가. (세션 종료 전 자체 점검 체크리스트에 포함)

---

## 2. 사용자가 Codex에 전달할 최소 문구

### 2-1. 정상 (5회 이내 통과)
```
reports/ai_dev_loop/latest_codex_review_request.md 문서 확인하고 검증 시작해줘.
단, Claude Code 요약만 믿지 말고 실제 변경 파일, diff, 테스트 결과, 로그를
직접 확인해서 검증해줘.
```

### 2-2. 5회 실패 시
```
reports/ai_dev_loop/latest_codex_review_request.md 와
reports/ai_dev_loop/latest_failure_report.md 확인하고 실패 원인 검증해줘.
부분 수정으로 해결 가능한 문제인지, 코드 재작성으로 가야 하는지,
테스트가 과한지 또는 구현 방향이 잘못됐는지 판단해줘.
```

> 사용자는 위 두 문구 중 하나만 전달한다. 다른 정보는 Codex가 파일에서 직접 읽는다.

---

## 3. `latest_codex_review_request.md` 필수 항목 (20개)

번호와 순서를 유지한다. 비어 있는 항목은 "해당 없음"으로 명시.

1. **세션 이름** (예: `18-3_chunker`)
2. **작업 목표** (한 문장)
3. **변경 파일 목록** (절대 경로 또는 repo 상대 경로 모두)
4. **변경 요약** (파일별 1~3줄)
5. **절대 바뀌면 안 되는 기능** (회귀 보호 대상 — `ai_rag_current_state.md` 참조)
6. **실행한 테스트 명령** (예: `run_check.bat`, `pytest tests/test_chunker.py -v`)
7. **테스트 결과 요약** (passed/failed 카운트, 주요 로그 발췌)
8. **자동 수정 루프 횟수** (1~5)
9. **5회 실패 여부** (yes/no)
10. **운영 DB 보호 검사 결과** (`scripts/check_db_path.py` 출력)
11. **RAG 하네스 결과** (rag_harness 통과 카운트)
12. **API 계약 테스트 결과** (manual/search, manual/ask 응답 키 회귀 0)
13. **할루시네이션 금지 테스트 결과** (test_ai_hallucination 등)
14. **PII 보호 테스트 결과** (PII 마스킹 / 외부 전송 차단 테스트)
15. **기존 SMS AI 회귀 테스트 결과** (test_ai_sms_*)
16. **기존 휴무 AI 회귀 테스트 결과** (test_ai_action_leave)
17. **남은 위험 요소** (Claude Code가 인지한 잠재 이슈)
18. **Codex가 집중 검토할 파일** (특히 위험한 변경)
19. **Codex가 반드시 확인할 체크리스트** (본 문서 §5에서 발췌)
20. **다음 세션으로 넘어가도 되는지 Claude Code의 자체 판단** (yes/no + 근거 1~3줄)

---

## 4. 세션별 검증 패키지 형식

Codex가 보는 입력 = 다음 6개 (모두 repo 내 텍스트):

1. `reports/ai_dev_loop/latest_codex_review_request.md` — 시작점
2. `reports/ai_dev_loop/latest_test_report.md` (성공 시) 또는 `latest_failure_report.md` (실패 시)
3. `reports/ai_dev_loop/latest_fix_summary.md` (성공 시)
4. `git diff` (해당 세션 브랜치 vs 이전 머지 커밋) — Codex가 직접 실행
5. 변경 파일들 (Codex가 직접 읽기)
6. 관련 설계 문서 (`AI_WORKING_RULES.md`, `ai_rag_architecture_plan.md`, `ai_rag_test_plan.md`, `ai_rag_error_codes.md`, `ai_rag_current_state.md` 등)

Claude Code는 위 1~3을 작성, 4~6은 Codex가 독립 확인.

---

## 5. Codex가 반드시 독립적으로 확인할 항목

다음 항목은 Claude Code의 보고를 믿지 않고 Codex가 직접 검증.

### 5-1. 코드 안전
- [ ] 운영 DB 경로(`%APPDATA%\도수치료예약\clinic.db`) 직접 접근 코드가 없는가
- [ ] `tests/conftest.py` 4단계 격리 약화/우회 변경이 없는가
- [ ] `pyproject.toml` per-file-ignores 변경이 없는가
- [ ] 기존 마이그레이션(m001~m011) 파일 수정이 없는가

### 5-2. API 계약 후방호환
- [ ] `/api/ai/manual/search` 응답 키 9개 그대로 (sources/title/path/snippet, masked_question, top_score)
- [ ] `/api/ai/manual/ask` 응답 키 9개 그대로 (answer, sources, confidence, not_found, blocked, blocked_reason, guard_hits, top_score, masked_question)
- [ ] 추가 필드만 있고 제거/이름 변경/타입 변경 없음
- [ ] HTTP status 코드 정책 유지 (400/503/200)

### 5-3. PII / 보안
- [ ] 입력 PII가 LLM prompt에 도달하지 않는가 (FakeProvider 받은 prompt에 원문 PII 부재)
- [ ] 로그(prompt_text/response_text)에 원문 PII 부재 (마스킹 또는 sha256만)
- [ ] API key가 어떤 로그/예외 traceback에도 부재
- [ ] `AiPiiBlocked` 예외가 외부 전송 직전 적용

### 5-4. Local-First
- [ ] `local_only` 모드에서 `len(provider.calls) == 0` 단언 통과
- [ ] `local_only` 모드에서 `len(embedding_provider.calls) == 0` 단언 통과
- [ ] sources 부족/PII/저신뢰 분기에서 LLM 호출 0
- [ ] API key 없는 환경에서 keyword RAG 정상 동작

### 5-5. 할루시네이션 가드
- [ ] `_RE_MEDICAL_CLAIM` / `_RE_EXECUTION_CLAIM` 차단 동작
- [ ] 출처 없는 단정 표현 차단 (반드시/무조건/확실히/항상)
- [ ] 차단 시 `blocked: true` + 안내문 대체

### 5-6. 회귀
- [ ] 기존 SMS AI 테스트 100% 통과
- [ ] 기존 휴무 AI 테스트 100% 통과
- [ ] 기존 매뉴얼 Q&A 테스트 100% 통과
- [ ] 기존 health public/admin 권한 분리 유지

### 5-7. PyInstaller
- [ ] 신규 모듈이 `dosu_clinic.spec` `hiddenimports`에 등록됨
- [ ] 신규 마이그레이션이 등록됨
- [ ] knowledge/ 데이터 동봉 유지

### 5-8. reason_code 일관성
- [ ] 신규 reason_code가 `ai_rag_error_codes.md`에 정의됨
- [ ] 우선순위 규칙 (§5) 위반 없음

### 5-9. 5회 실패 케이스 추가 검증 (실패 시만)
- [ ] 부분 수정으로 해결 가능한가 / 코드 재작성이 필요한가
- [ ] 테스트가 과한가 (over-specified) / 구현 방향이 잘못됐는가
- [ ] 가설이 맞았으나 실행이 틀렸는가
- [ ] 설계 문서와 실제 의도가 어긋나는가

---

## 6. Codex 출력 형식

권장 양식: `reports/ai_dev_loop/latest_codex_review_response.md` (Codex가 작성, 사용자 또는 Claude Code가 검토)

```
# Codex 검증 보고서

세션: {세션 이름}
검증일: YYYY-MM-DD
판정: PASS | CONDITIONAL_PASS | FAIL
다음 세션 진입 가능: yes | no

## 1. 독립 확인 결과 (§5 체크리스트별)
- [x] 5-1.1 운영 DB 직접 접근 없음 — 확인
- [x] 5-2.* API 계약 후방호환 — 확인
- ...

## 2. Claude Code 보고와 실제의 차이
(있다면 기록)

## 3. 발견한 위험
(reason_code 누락, 회귀 가능성, 미커버 케이스 등)

## 4. 조건부 통과 시 조건
(있다면 명시 — 예: "다음 세션 시작 전 X 추가 테스트 필요")

## 5. 실패 시 권고
(코드 재작성 / 부분 수정 / 테스트 조정 / 설계 재검토 중 어느 것)

## 6. 다음 세션으로 넘어가는 기준
- 본 보고서가 PASS 또는 CONDITIONAL_PASS
- 조건부일 경우 명시 조건 충족 후 진입
```

---

## 7. 판정 규칙

| 판정 | 조건 |
|---|---|
| **PASS** | §5 체크리스트 전 항목 통과 + 위험 항목 0 또는 무시 가능 |
| **CONDITIONAL_PASS** | §5 통과하나 명시 조건(예: 추가 테스트, 문서 보강) 필요 |
| **FAIL** | §5 중 1개라도 실패, 또는 PII/할루시네이션 가드 깨짐, 또는 응답 스키마 회귀 |

다음 세션 진입 기준:
- PASS → 즉시 진입 가능
- CONDITIONAL_PASS → 조건 충족 후 진입 (충족 입증은 사용자/Claude Code가 책임)
- FAIL → 진입 금지. 본 세션 재작업 (5회 루프 재시작 또는 코드 재작성)

---

## 8. 5회 실패 시 검증 흐름

1. Claude Code: `latest_failure_report.md` + `latest_codex_review_request.md` 작성
2. 사용자: §2-2 문구 Codex에 전달
3. Codex 독립 확인 (§5에 추가):
   - 시도된 5회 가설이 같은 가정을 반복했는가
   - 실패 패턴이 코드 결함인가 / 테스트 과잉인가 / 설계 결함인가
   - 부분 수정 6회차로 해결 가능성이 있는가 (대부분 NO)
   - 다른 접근(전체 재작성/설계 변경)을 권고
4. Codex 보고서 기반으로 사용자 결정 (재작업/설계 변경/세션 분할)

---

## 9. Claude Code의 자기검열 vs Codex 검증 차이

| 항목 | Claude Code 자체 | Codex 독립 |
|---|---|---|
| 테스트 통과 | ✅ pytest 실행 | ✅ 결과 재확인 + 회피된 케이스 탐지 |
| 응답 스키마 | ✅ 코드 변경 점검 | ✅ diff에서 키 제거/이름 변경 탐지 |
| PII | ✅ 로그/응답 검증 | ✅ FakeProvider 받은 prompt까지 추적 |
| 5회 루프 | ✅ 카운트 | ✅ 가설 반복 패턴 진단 |
| 새 reason_code | ✅ error_codes.md 갱신 | ✅ 누락 코드 탐지 |
| 다음 세션 진입 자체 판단 | ✅ yes/no | ✅ 독립 yes/no (불일치 시 Codex 우선) |
| 디자인 의도와 구현의 일치 | ⚠️ 자기검열 한계 | ✅ 외부 시각 |

원칙: **Codex 결과가 Claude Code 자체 판단보다 우선한다**.

---

## 10. 보존 규칙

- `latest_codex_review_request.md` / `latest_codex_review_response.md`는 다음 세션에서 덮어쓰기 가능.
- 세션별 영구 보존본은 `{SESSION_NAME}_codex_review_request.md` / `{SESSION_NAME}_codex_review_response.md`로 동일 폴더에 사본.
- Codex 보고서가 PASS여도 `latest_*` 삭제는 금지 (다음 세션 시작 시 참고).

---

## 11. 절차 위반 시

- Claude Code가 Codex 검증 없이 다음 세션을 진행하려 하면, 사용자에게 멈춰 보고하고 검증 게이트 통과 여부 확인.
- Codex 결과가 FAIL인데 Claude Code가 무시하고 진행하려 하면 즉시 중단.
- 위반 사례는 `reports/ai_dev_loop/protocol_violations.md`에 기록 (이 파일은 누적).

---

## 12. 본 세션 범위 외

- Codex 자동 호출 자동화는 만들지 않는다 (사용자가 §2 문구로 수동 위임).
- Codex 보고서 자동 파싱·DB 저장은 만들지 않는다.
- 본 세션은 **프로토콜 정의만**.
