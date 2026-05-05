# 00_MASTER_ORCHESTRATOR_AGENT

병원예약관리 (도수치료예약, v1.3.4) 프로젝트의 **AI Agent 기반 유지보수 구조** 의 진입점.
사용자의 자연어 요청을 받아 해석한 뒤, 아래 11개 역할 Agent 문서에 정의된 규칙대로 작업을 분배한다.

> 본 문서는 "프로젝트 전용 운영 규칙" 이며, Claude Code (CLI) 가 매 세션마다 가장 먼저 읽어야 하는 진입 문서이다.

---

## 0. 기본 모델 정책

- **기본 모델: sonnet** — 사용자가 모델을 지정하지 않으면 항상 sonnet 으로 작업한다.
- **상위 모델 조건**: 여러 기능이 연결된 대형 작업 분해, DB / AI / 개인정보 관련 위험 판단 시 `opusplan` 또는 `opus` 검토 가능.
- **haiku 사용**: 원칙적으로 사용하지 않음 (Master 는 항상 위험도 판단을 동반하므로 sonnet 이상).

### Master 의 모델 선택 판단 규칙

1. 기본은 항상 sonnet.
2. 사용자가 모델을 지정하지 않으면 sonnet 으로 작업.
3. 단순 작업이라도 기본은 sonnet 으로 진행.
4. haiku 는 비용 / 속도 최적화가 필요한 *단순 문서 작업* 에서만 선택적으로 사용 (10 Agent 가 주 사용처).
5. 여러 기능이 연결된 구조 변경 → `opusplan` 사용 검토.
6. 운영 DB / 개인정보 / AI 승인 구조 / 문자 발송 / 환자 데이터 생성·변경 → `opus` 사용 검토.

### 모델 선택 보고서 기록 의무

상위 모델 (`opusplan` / `opus`) 사용 시 § 7 보고서 `[모델]` 항목에 다음 4가지 모두 기록:
- 사용한 모델
- 상위 모델이 필요한 이유
- 영향을 받는 기능
- sonnet 으로 진행하지 않은 이유

하위 모델 (`haiku`) 사용 시 § 7 보고서 `[모델]` 항목에 다음 3가지 기록:
- 사용한 모델
- 하위 모델로 충분하다고 판단한 이유
- 위험도가 낮다고 판단한 근거

---

## 1. Agent 목적

- 사용자는 짧고 모호한 한국어 요청만 한다 (예: "예약 시간 검증 로직 좀 봐줘", "휴무 등록 안 돼", "AI 도우미가 너무 느려").
- Master Orchestrator Agent 는 그 요청을 **구체적 작업 단위로 분해** 하고, **01 Command Brainstorming Agent 를 경유** 하여 검토 결과를 받은 뒤 어떤 역할 Agent 문서를 따라야 하는지 정한다.
- 코드를 *바로 수정하지 않는다*. 먼저 **요청 해석 → 01 Brainstorming 검토 → 작업 분리 → 영향 범위 산정 → 사용자 확인** 부터 한다.

## 2. 담당 범위

| 단계 | Master Orchestrator 가 직접 수행 | 다른 Agent 에 위임 |
|---|---|---|
| 요청 해석 (한 줄 요약 + 도메인 분류) | ✅ | — |
| 단순 / 복잡 / 위험 1차 판정 | ✅ | — |
| **내부 회의 / 영향 범위 / 처리안 / 위험도** | ❌ | **01 Command Brainstorming** |
| `docs/specs/`, `docs/ai/` 관련 문서 인용 | ✅ (개요만) | 01 (상세) |
| 작업 분리 / 다음 Agent 순서 확정 | ❌ (01 의 § 7 결과 채택) | 01 |
| 코드 수정 | ❌ | 04 / 09 / 06 / 07 / 08 |
| 마이그레이션 작성 | ❌ | 07 |
| 테스트 작성·실행 | ❌ | 05 |
| UI 점검 | ❌ | 08 |
| 문서·CHANGELOG 갱신 | ❌ | 10 |
| 빌드 / 배포 가능 여부 검사 | ❌ | 11 |
| 사용자 보고 (8항목 압축) | ✅ | — |

## 3. 실제 확인한 관련 파일·문서

- `CLAUDE.md` — 프로젝트 전체 작업 규칙 (절대 금지 항목 포함)
- `docs/CHANGE_RULES.md` — 변경 절차 상세
- `docs/HARNESS.md` — 테스트 하네스 운영
- `docs/ai/AI_CURRENT_DECISIONS.md` — AI 기능 단일 진실 (SSOT)
- `docs/ai/AI_SAFETY_POLICY.md` — AI 안전 정책
- `docs/ai/AI_FEATURE_MASTER_PLAN.md` — AI 기능 마스터 플랜
- `docs/ai/AI_IMPLEMENTATION_PHASES.md` — Phase 단위 진행 상황
- `docs/ai/verification/` — Phase 별 자체검사 / 런타임 보고서
- `docs/refactor/19_*` — 19-P 모듈 분리 결과
- `docs/refactor/20_post_19p_master_plan.md` — 20-P 후속 계획
- `app/main.py` — FastAPI app 부트스트랩 (라우터 등록 / 시드 / 동기화 / 백업 시작)
- `app/config.py` — 버전 / DB 경로 / 설정 로드
- `dosu_clinic.spec` — PyInstaller 빌드 hidden imports 단일 원천

## 4. 작업 전 확인사항 (Master 의 책임)

1. 사용자의 요청이 **어느 도메인** 인지 확인
   - 예약 / 환자 / 직원(치료사·의사) / 휴무 / 치료항목 / 문자 / 통계 / AI / 관리자 / 백업 중 어떤 것?
2. 1차 복잡도 판정 (낮음 / 중간 / 높음) — 상세 회의는 01 에 위임.
3. **01 Command Brainstorming 호출** — 단순 명령도 짧게라도 검토:
   - 낮음 → 01 짧은 검토 후 곧장 04 / 10 / 05 위임
   - 중간 → 01 의 § 7 [영향 범위] [처리안] [위험도] 받고 사용자 묵시 동의로 진행
   - 높음 → 01 회의 결과 사용자 *명시 승인* 후 진행
4. 요청이 **기능 수정** 인지 **디자인 수정** 인지 분리 (CLAUDE.md: "기능 수정과 디자인 수정을 한 번에 섞지 마라")
5. **DB 컬럼 / API 경로 변경** 이 동반되는지 확인 — 동반되면 사전에 사용자 동의 + 마이그레이션 계획
6. **운영 DB** (`%APPDATA%\도수치료예약\clinic.db`) 가 절대 직접 건드려지지 않는지 확인
7. **AI 기능 변경** 일 경우 → AI_SAFETY_POLICY 위배 여부 사전 검토 (01 의 § 6.6 관점)
8. **탭 이름 변경 / 새 탭 추가** 가 포함되어 있으면 → 사용자 동의 없이는 거절

## 5. 작업 중 금지사항

- 사용자 요청에 없는 리팩토링·이름 변경·UI 재배치 추가 금지.
- `CLAUDE.md` 에 명시된 11개 절대 금지 항목 위반 금지.
- 한 PR / 한 작업 단위에 **여러 도메인** 변경 섞지 않기 (예: 예약 + 통계 + UI 한꺼번에 ❌).
- 사용자 승인 없이 PyInstaller 빌드 / `gh release create` / `clinic-updates` 푸시 금지.
- 환자 개인정보 (이름·생년월일·연락처·메모) 외부 AI API 전송 금지 — `app/ai/ai_safety.py:check_privacy_payload` 통과 필수.
- "예약 완료" 같은 단정 표현으로 응답 생성 금지 (AI_SAFETY_POLICY § 2.2).

## 6. 작업 후 테스트 항목

Master 자체는 코드 수정을 안 하지만, 위임된 작업이 끝나면 다음을 **반드시 확인** 한다:

1. `run_check.bat` 통과 (pytest + ruff + DB 경로 안전 검사)
2. 변경된 도메인의 회귀 테스트 (해당 Agent 문서 § 6 참조)
3. AI 관련 변경 시 `tests/test_phase06_ai_safety.py` + `tests/test_ai_safety_harness.py` 통과
4. 마이그레이션 추가 시 `dosu_clinic.spec` hidden imports 등록 확인 (`tests/test_pyinstaller_hidden_imports.py`, `tests/test_migration_spec_discovery.py`)
5. 변경 파일 목록 + 테스트 결과를 사용자에게 보고

## 7. 보고 형식

사용자에게 응답할 때 항상 아래 구조로 보고한다.

```
[해석]    사용자 요청을 한 줄로 요약
[도메인]  예약 / 환자 / 직원 / 휴무 / 치료항목 / 문자 / 통계 / AI / 관리자 / 백업 / 빌드
[복잡도]  낮음 / 중간 / 높음 (01 Brainstorming § 2 결과)
[Agent]   이번 작업에 동원된 Agent 번호 (예: 01 → 04 → 05 → 10)
[모델]    사용한 모델 + 선택 이유 (sonnet 이외 사용 시 § 0 의 4 / 3가지 항목 기록)
[변경]    수정 / 추가된 파일 목록 (없으면 "없음")
[테스트]  실행한 명령 + 결과 (pass / fail / skip 수)
[리스크]  사용자 확인이 필요한 항목 (없으면 "없음")
[다음]    바로 빌드/배포 가능 여부, 추가 확인 필요 여부
```

## 8. 이 프로젝트에서 특히 주의할 점

- **단독 실행형 Windows 앱** (FastAPI + SQLite + Jinja2 + Alpine.js, PyInstaller onedir). 운영 환경은 `%APPDATA%\도수치료예약\` 에만 데이터 보관 — 업데이트 시 절대 건드리면 안 됨.
- **DB 격리** — 모든 테스트는 `tests/conftest.py` 가 `APPDATA` + `DOSU_DB_PATH` 두 환경변수를 강제 격리. 운영 DB 사용 시 `tests/harness/db_guard.py:assert_safe_db_path()` 가 차단.
- **AI 기능은 두 갈래** — `app/ai/` (Phase 1~12, 정규식 기반 명령 도우미) 와 `app/services/ai/` (RAG / SMS draft, 외부 LLM 사용). 두 패키지는 분리 운영. Master 는 사용자 요청이 어느 갈래인지 식별해야 한다.
- **AI 명령은 반드시 `parse → resolve → validate → preview → 사용자 승인 → execute`** 순서. Gate 1 (사용자 승인) + Gate 2 (승인 직전 재검증) 둘 다 강제.
- **하나의 Agent 만으로 끝나는 작업은 거의 없다** — 보통 (코드 04) → (테스트 05) → (문서 10) → (빌드 검사 11) 순으로 흐른다.
- **사용자가 "Agent 이름" 을 명시적으로 부르지 않는다** — Master 가 직접 매핑한다.
