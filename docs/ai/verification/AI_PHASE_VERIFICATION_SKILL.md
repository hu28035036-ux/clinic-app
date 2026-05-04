# AI_PHASE_VERIFICATION_SKILL.md

> 본 문서는 병원 예약관리 프로그램의 AI 기능 개발에서, **각 Phase**마다 강제되는 검증 스킬을 정의합니다.
> 같은 내용이 `.claude/skills/ai-phase-verification/SKILL.md` 에도 등록되어 있어, Claude Code Skill로도 호출 가능합니다.
> Phase 검증을 통과하지 못하면 다음 Phase로 진행할 수 없습니다.

---

## 1. 검증 스킬 핵심

1. **Claude Code 자체 5회 검증**을 수행합니다.
2. Claude Code 자체검증 결과와 수정사항은 **문서로 남깁니다**.
3. Claude Code는 **실제 동작 확인**을 수행하고 **Runtime Test Report**를 남깁니다.
4. **Codex**는 Claude Code 결과를 신뢰하지 않고 **독립 검증**합니다.
5. Codex 수정사항은 문서로 남깁니다.
6. Claude Code는 Codex 수정사항을 **참고만** 하고 독립 검토합니다.
7. Claude Code는 수정사항별 반영 / 부분반영 / 미반영 사유를 **문서로 남깁니다**.
8. Codex는 Claude Code 수정 보고서를 신뢰하지 않고 **독립 재검증**합니다.
9. **Codex 재검증이 "통과"** 일 때만 다음 Phase를 **자동 진행**합니다.
10. **"조건부 통과" / "실패"** 는 자동 진행하지 않습니다.
11. 치명적 위험 항목이 있으면 조건부 통과여도 다음 Phase로 진행하지 않습니다.

---

## 2. Claude Code 자체 5회 검증

각 Phase 종료 시 다음 5회를 모두 수행하고, 결과를 `PHASE_XX_CLAUDE_SELF_CHECK.md` 에 기록합니다.

### 2.1 1회차 — 요구사항 검증
- 사용자가 정한 Phase 목표 / 요구사항 / 입력·출력 명세를 만족하는가?
- 누락 / 과잉 구현이 없는가?
- 환자 검색 / 차트번호 / 동명이인 / 신환 / 치료항목 다중 입력 등 핵심 시나리오가 반영되었는가?
- (단위화) 새 기능이 **하나의 큰 파일에 몰려 있지 않은가**?
- (단위화) parser / resolver / validator / preview / executor / audit / safety 가 역할별로 분리되어 있는가?
- (단위화) AI executor 가 DB 를 직접 수정하지 않고 기존 service 를 호출하는가?
- (단위화) 기존 도메인 로직을 중복 구현하지 않았는가?

### 2.2 2회차 — AI 안전정책 / 금지기능 검증
- `AI_SAFETY_POLICY.md` 의 금지 사항 위반이 없는가?
- 승인 없이 DB / SQL / 예약 / 휴무 / 신환 / 문자가 동작하는 경로가 없는가?
- 승인 직전 최종 재검증이 있는가?

### 2.3 3회차 — 개인정보 / API 키 / 외부 전송 검증
- 외부 AI API 페이로드에 환자 전체 / 생년월일 / 연락처 / 메모 / 진료 내용이 포함되지 않는가?
- API 키가 코드에 직접 저장되어 있지 않은가?
- AI API 실패 시 기존 프로그램이 정상 동작하는가?

### 2.4 4회차 — 기존 기능 영향 검증
- 예약 / 통계 / 문자 / 완료체크 / 휴무 / 환자 등록 / 마이그레이션 / `manual60` 카운트 정책에 영향이 없는가?
- 기존 라우트 / 서비스 / DB 스키마가 깨지지 않았는가?

### 2.5 5회차 — 하네스 / 로그 / 문서 / 주석 / 실제 작동테스트 검증
- 본 Phase에 필요한 하네스가 추가되었는가?
- `ai_command_logs` / 신환 등록 / 예약 등록 로그가 각각 남는가?
- 문서가 갱신되었는가? (`AI_CURRENT_DECISIONS.md`, `AI_REQUIREMENTS_OVERRIDES.md`, 영향받은 설계 문서)
- 주석이 과하거나 모자라지 않는가?
- (단위화) **함수 하나**가 너무 많은 역할을 하지 않는가? (`parse_and_resolve_and_validate_and_save()` 같은 통합 함수 금지)
- (단위화) 각 모듈을 **독립적으로 테스트하거나 하네스에서 검증**할 수 있는가?
- (단위화) 주요 파일·함수에 **역할 주석** (담당 역할 / DB 직접 수정 여부 / 기존 service 호출 여부 / 안전 규칙 / 개인정보 / 하네스 연결 지점) 이 있는가?
- (단위화) 기존 기능을 깨지 않도록 **작은 단위로 변경**했는가?

#### 2.5.1 실제 작동테스트 (Runtime Test) — **반드시 실행 기준으로 확인**

문서 검증·코드 검토와 **별개로**, 실제 서버를 띄우고 클릭·API 호출까지 수행하여 다음 항목을 모두 확인합니다.

- **서버가 정상 실행**되는지 확인
- **화면이 정상 로딩**되는지 확인
- 해당 Phase에서 추가한 기능이 **실제 UI / API에서 동작**하는지 확인
- **정상 케이스**가 성공하는지 확인
- **실패 / 예외 케이스**가 안전하게 처리되는지 확인 (앱이 크래시하지 않음, 사용자에게 안내 표시)
- **승인 전에는 DB가 변경되지 않는**지 확인 (parse / preview 단계에서 0건)
- **승인 후에만 DB가 변경**되는지 확인 (approve 직후 정확한 row 변경)
- 기존 **예약 / 환자 / 치료사 / 의사 / 치료항목 / 휴무 / 문자 / 통계 / 완료체크** 기능이 깨지지 않았는지 확인
- **AI API 실패 시 기존 프로그램이 정상 동작**하는지 확인 (API 키 없는 상태 / 네트워크 차단 / provider 오류 시뮬레이션)
- 실제 작동테스트 결과를 **`PHASE_XX_RUNTIME_TEST_REPORT.md` 문서로 기록**했는지 확인

> **Codex는 Claude Code의 Runtime Test Report를 그대로 믿지 않고 독립적으로 동일 항목을 다시 확인합니다.**

---

## 3. Phase별 산출 문서 (필수)

각 Phase XX마다 다음 문서를 모두 작성해야 합니다 (XX는 Phase 번호):

| 문서 | 작성 주체 | 설명 |
|---|---|---|
| `PHASE_XX_CLAUDE_SELF_CHECK.md` | Claude | 자체 5회 검증 결과 |
| `PHASE_XX_CLAUDE_SELF_FIXES.md` | Claude | 자체 검증으로 발견 / 수정한 내용 |
| `PHASE_XX_RUNTIME_TEST_REPORT.md` | Claude | 실제 동작 확인 보고서 |
| `PHASE_XX_CODEX_REVIEW.md` | Codex | 독립 1차 검증 |
| `PHASE_XX_CODEX_FIX_REQUESTS.md` | Codex | Codex 수정 요청 |
| `PHASE_XX_CLAUDE_FIX_REPORT.md` | Claude | 반영 / 부분반영 / 미반영 사유 |
| `PHASE_XX_CODEX_RECHECK.md` | Codex | 독립 재검증 |
| `PHASE_XX_TO_PHASE_YY_AUTO_PROCEED.md` | Claude | 자동 진행 근거 (통과 시) |

모든 문서는 `docs/ai/verification/` 아래에 저장합니다.

---

## 4. Runtime Test Report 형식

`docs/ai/verification/PHASE_XX_RUNTIME_TEST_REPORT.md` 는 **각 Phase 마다 반드시** 작성합니다 (Phase 0 제외 — 코드 변경이 없으므로 해당사항 없음).

다음 항목을 **모두** 기록합니다.

- **Phase 번호**
- **실행 환경** (OS / Python 버전 / DB 경로 — 운영 DB(`%APPDATA%\도수치료예약\clinic.db`) 미사용 확인)
- **실행한 명령** (`run_check.bat`, `pytest`, 서버 기동 명령, 브라우저 / API 호출 명령 등)
- **서버 실행 여부** — 정상 / 실패
- **화면 로딩 여부** — 정상 / 실패 (화면별)
- **테스트한 기능** — Phase에서 추가·변경된 기능 목록
- **정상 케이스 결과** — 통과 / 실패 / 케이스별 상세
- **실패 케이스 결과** — 안전 처리 통과 / 실패
- **승인 전 DB 변경 여부** — **없어야 함**. 발생 시 즉시 실패 처리.
- **승인 후 DB 변경 여부** — 정확한 row 변경 / 부정확 / 누락
- **기존 기능 회귀 테스트 결과** — 예약 / 환자 / 치료사 / 의사 / 치료항목 / 휴무 / 문자 / 통계 / 완료체크 / `manual60` 카운트 정책
- **AI API 실패 시 기존 프로그램 정상 동작 확인** — 통과 / 실패
- **발견한 오류** — 목록
- **수정 여부** — 어떻게 수정했는지 / 수정 후 재실행 결과
- **최종 판단** — `정상 작동` / `조건부 정상` / `실패`

### 4.1 작성 원칙

- **반드시 실제 실행 기준**으로 기록. 문서 검토만으로 채우지 않습니다.
- 실패가 발견되면 Codex 재검증 이전에 Claude Code가 **먼저 수정**하고 재테스트한 뒤 보고서를 갱신합니다.
- "정상 작동"으로 기재하려면 § 2.5.1 의 모든 항목을 통과해야 합니다.
- **Codex는 본 보고서를 그대로 믿지 않고 독립적으로 같은 항목을 다시 확인**합니다 (§ 5).

---

## 5. 서로를 신뢰하지 않는 원칙

- Claude Code는 Codex 검증 결과를 그대로 믿고 무조건 반영하지 않습니다.
- Codex는 Claude Code 자체검증 결과를 그대로 믿지 않습니다.
- Codex는 Claude Code Runtime Test Report도 그대로 믿지 않고 독립적으로 확인합니다.
- 서로의 문서는 **참고 자료**로만 사용합니다.
- 각자 독립적으로 검토합니다.
- 판단 근거를 문서로 남깁니다.
- 반영하지 않는 경우에도 **미반영 사유**를 남깁니다.

---

## 6. 다음 Phase 진행 금지 조건 (치명적 위험)

다음 항목이 하나라도 발견되면 자동 진행 불가:

### 6.1 안전 / 설계 위반

- AI가 직접 DB 수정 가능
- AI가 직접 SQL 실행 가능
- 승인 없이 예약 생성 / 변경 / 취소 가능
- 승인 없이 휴무 등록 가능
- 승인 없이 신환 등록 가능
- 문자 자동 발송 가능
- 환자 전체 목록 / 전화번호 / 생년월일 / 상세 메모 / 민감정보가 외부 AI API로 전달됨
- API 키가 코드에 직접 저장됨

### 6.2 기능 / 검증 누락

- 예약 중복 검증 누락
- 휴무 / 반차 검증 누락
- 차트번호 / 동명이인 / 생년월일 표시 검증 누락
- 환자 후보 선택 전 예약 등록 가능
- 치료항목 DB / alias 검증 누락
- `treatment_items` 다중 치료항목 처리 누락
- 신환 등록 중복 검사 누락
- 기존 예약 / 통계 / 문자 / 완료체크 기능 손상
- AI API 실패 시 기존 프로그램 전체 오류 발생

### 6.3 실제 작동테스트 (Runtime Test) 위반 (2026-05-03 추가수정사항 3)

- 실제 작동테스트 실패
- `PHASE_XX_RUNTIME_TEST_REPORT.md` 누락
- 서버 실행 실패
- 화면 로딩 실패
- 승인 전 DB 변경 발생 (parse / preview 단계)
- 승인 후 실행 실패 (approve 했으나 DB 미반영 / 잘못된 row 변경)
- 기존 핵심 기능 회귀 오류 발생

### 6.4 단위화 / 모듈화 위반 (2026-05-03 추가수정사항 1)

- 한 파일 또는 한 함수에 로직 과도하게 몰림 (`parse_and_resolve_and_validate_and_save()` 같은 통합 함수)
- AI executor 가 직접 DB 조작 (기존 service 우회)
- 기존 도메인 로직 중복 구현 (예약 / 환자 / 치료항목 / 휴무 / 문자 / 통계 / 완료체크)
- 모듈 / 함수 단위 독립 검증 불가
- 새 / 크게 수정한 파일·함수에 역할 주석 누락

> 본 § 6 의 4 카테고리는 `AI_SAFETY_POLICY.md` § 7 / `AI_CODEX_VERIFICATION_PLAN.md` § 4 / `.claude/skills/ai-phase-verification/SKILL.md` § 4 와 1:1 정합되어야 합니다.

---

## 7. Codex 통과 시 자동 진행 규칙

Codex 최종 재검증이 **"통과"** 로 나오면 Claude Code는 사용자에게 매번 다음 단계 진행 여부를 묻지 말고 **다음 Phase를 자동으로 진행**합니다.

### 7.1 자동 진행 조건

- `PHASE_XX_CLAUDE_SELF_CHECK.md` 작성 완료
- `PHASE_XX_CLAUDE_SELF_FIXES.md` 작성 완료
- **`PHASE_XX_RUNTIME_TEST_REPORT.md` 작성 완료**
- **실제 작동테스트 정상 통과** (§ 2.5.1 모든 항목)
- `PHASE_XX_CODEX_REVIEW.md` 작성 완료
- `PHASE_XX_CODEX_FIX_REQUESTS.md` 작성 완료
- `PHASE_XX_CLAUDE_FIX_REPORT.md` 작성 완료
- `PHASE_XX_CODEX_RECHECK.md` 작성 완료
- Codex 최종 판단: **통과**
- Codex 의 Runtime 독립 재확인 결과 일치
- 다음 Phase 진행 금지 조건 (§ 6) 없음
- 사용자가 "중단 / 대기" 를 명시하지 않음

> **실제 작동테스트가 실패하면 다른 모든 항목과 무관하게 자동 진행 금지** (§ 6.3).

조건이 모두 충족되면 다음 Phase 시작 시 다음 문서를 작성합니다.

`docs/ai/verification/PHASE_XX_TO_PHASE_YY_AUTO_PROCEED.md`

내용:
- 이전 Phase 번호
- 다음 Phase 번호
- Codex 최종 통과 문서 경로
- 자동 진행 근거 요약
- 남은 위험 없음 확인
- 다음 Phase 시작 시간

### 7.2 조건부 통과 처리

- 자동 진행하지 않습니다.
- 남은 조건을 Claude Code가 정리하거나 수정합니다.
- 필요 시 Codex 재검증을 다시 받아야 합니다.

### 7.3 실패 처리

- 자동 진행하지 않습니다.
- 해당 Phase를 수정하고 다시 검증 루프를 반복합니다.

---

## 8. Skill 호출 가이드 (요약)

Claude Code 환경에서 본 스킬은 다음과 같이 사용됩니다.

- 사용자가 어떤 Phase 작업을 마무리한 직후 또는 직전에 자동으로 호출됨.
- 호출 시 Claude Code는:
  1. 자체 5회 검증 수행
  2. Runtime Test Report 작성
  3. Codex 검증 요청 / 결과 기록
  4. Codex 재검증 결과 확인
  5. 통과 시 자동 진행, 그 외에는 대기
- 사용자는 언제든지 "중단" / "대기" / "사용자 확인 후 진행" 으로 자동 진행을 멈출 수 있습니다.

---

## 9. 기존 프로젝트 하네스와의 관계

- 본 스킬은 기존 `tests/`, `docs/specs/`, `run_check.bat` 하네스 위에 **추가**됩니다.
- 기존 하네스 항목 (pytest / ruff / DB 경로 안전 검사) 도 모두 통과해야 합니다.
- `manual60` 1카운트 정책 / `app/**` lint per-file-ignores 등 기존 규칙은 변경 금지.
- 운영 DB(`%APPDATA%\도수치료예약\clinic.db`)는 절대 사용하지 않습니다.
