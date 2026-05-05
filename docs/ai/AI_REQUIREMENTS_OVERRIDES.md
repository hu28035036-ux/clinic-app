# AI_REQUIREMENTS_OVERRIDES.md

> AI 설계 문서의 요구사항 변경 이력.
> 사용자가 추가수정사항을 전달할 때마다 본 문서에 기록하고, 관련 문서를 덮어씁니다.

---

## 1. 덮어쓰기 규칙

1. 사용자가 "추가수정사항"을 전달하면 기존 문서에 반영합니다.
2. 기존 내용과 새 내용이 겹치거나 충돌하면 **최신 사용자 지시를 우선**합니다.
3. 겹치는 내용은 중복으로 남기지 말고 최신 내용으로 덮어씁니다.
4. 덮어쓴 내용은 본 문서에 기록합니다.
5. 충돌이 있었던 경우 다음 형식으로 기록합니다.

### 1.1 기록 형식

```
- 변경 시각:
- 기존 내용:
- 최신 수정 내용:
- 최종 반영 내용:
- 덮어쓴 이유:
- 반영 문서:
```

6. `AI_CURRENT_DECISIONS.md` 에는 현재 기준으로 확정된 최신 의사결정만 정리합니다.
7. 과거 내용은 참고만 하고, 현재 설계 기준은 `AI_CURRENT_DECISIONS.md` 를 우선합니다.
8. 이후 사용자가 "추가수정사항" 으로 전달하는 내용은 기존 내용과 겹치면 **최신 지시가 덮어씁니다.**

---

## 2. 변경 이력

### 2026-05-03 (Phase 0 초기 작성) — 베이스라인

- 변경 시각: 2026-05-03 (Phase 0 문서 최초 작성 시점)
- 기존 내용: 없음 (최초 작성)
- 최신 수정 내용: 본 디렉토리(`docs/ai/`) 모든 문서 최초 작성
- 최종 반영 내용:
  - `AI_FEATURE_MASTER_PLAN.md`
  - `AI_COMMAND_ARCHITECTURE.md`
  - `AI_SAFETY_POLICY.md`
  - `AI_HARNESS_PLAN.md`
  - `AI_IMPLEMENTATION_PHASES.md`
  - `AI_CODEX_VERIFICATION_PLAN.md`
  - `AI_REQUIREMENTS_OVERRIDES.md` (본 문서)
  - `AI_CURRENT_DECISIONS.md`
  - `verification/AI_PHASE_VERIFICATION_SKILL.md`
  - `.claude/skills/ai-phase-verification/SKILL.md`
- 덮어쓴 이유: 최초 작성 (베이스라인)
- 반영 문서: 위 전부

---

### 2026-05-03 (Phase 0 추가수정사항 1) — 단위화 / 모듈화 원칙 강제

- 변경 시각: 2026-05-03 (사용자 추가수정사항 전달 시점)
- 기존 내용:
  - `AI_COMMAND_ARCHITECTURE.md` 가 `app/ai/` 모듈 10종 정도만 명시.
  - 기존 도메인(`app/appointments/`, `app/patients/`, `app/treatments/`, `app/therapists/`, `app/messages/`, `app/stats/`) 의 service / validator / repository 분리 원칙은 명시되지 않았음.
  - 함수 단위화 (`parse_and_resolve_and_validate_and_save()` 같은 거대 함수 금지) 원칙 미명시.
  - UI 컴포넌트 분리 권장 (AiCommandInput / PatientCandidateList / AppointmentPreviewCard 등) 미명시.
  - 주석 작성 원칙 (역할 / DB 직접 수정 여부 / 기존 service 호출 여부 / 안전 규칙 / 개인정보 / 하네스 연결지점) 미명시.
  - Phase별 단위화 완료 조건 미명시.
  - Codex 검증 항목에 단위화 점검 7개 항목 미포함.
  - Claude 자체 5회 검증의 1회차·5회차에 단위화 점검 항목 미포함.
- 최신 수정 내용: 다음 원칙을 모든 AI 기능 / 이후 코드 작성에 강제로 적용.
  1. 한 파일 / 함수에 기능 몰아넣기 금지.
  2. parser / resolver / validator / preview / executor / audit / safety / harness 역할별 분리.
  3. 기존 도메인도 service / validator / repository 분리 유지.
  4. AI executor는 DB 직접 수정 금지, 기존 service 호출.
  5. 기존 예약 / 환자 / 치료항목 / 휴무 / 문자 / 통계 / 완료체크 로직 중복 구현 금지.
  6. 거대 함수(`parse_and_resolve_and_validate_and_save()` 등) 금지, 역할 분리 함수 사용.
  7. UI 도 컴포넌트 단위 분리 (AiCommandInput / PatientCandidateList / AppointmentPreviewCard 등).
  8. Phase 단위를 작게 나누어 각 Phase 단독 검증 가능.
  9. 새 / 크게 수정한 파일·함수에 역할 주석 작성.
  10. 단위화가 부족해 한 파일 / 함수에 로직이 과도하게 몰리면 해당 Phase는 완료 불가.
  11. Claude 자체 검증 / Codex 검증에 단위화 점검 항목 추가.
- 최종 반영 내용:
  - `AI_FEATURE_MASTER_PLAN.md` § 14 단위화 / 모듈화 원칙 추가.
  - `AI_COMMAND_ARCHITECTURE.md` § 10 기존 도메인 모듈 분리, § 11 함수 단위화, § 12 UI 단위화, § 13 주석 작성 원칙, § 14 기존 로직 재사용 추가.
  - `AI_IMPLEMENTATION_PHASES.md` 각 Phase 공통 완료 조건에 단위화 6개 조건 추가.
  - `AI_CODEX_VERIFICATION_PLAN.md` § 2.11 Codex 단위화 검증 항목 7개 추가 (49~55).
  - `verification/AI_PHASE_VERIFICATION_SKILL.md` § 2.1 / 2.5 에 단위화 8개 점검 항목 추가.
  - `.claude/skills/ai-phase-verification/SKILL.md` § 2 / § 4 단위화 항목 반영.
  - `AI_CURRENT_DECISIONS.md` 신규 § 15 단위화 / 모듈화 원칙 추가, 기존 § 9 모듈 구조 보강.
- 덮어쓴 이유: 사용자가 단위화 / 모듈화를 AI 기능 전체 구조 + 이후 코드 작성에 강제로 적용하도록 요청. 기존 문서가 이를 부분적으로만 반영하고 있었으므로, 최신 사용자 지시를 우선해 전체 문서를 갱신.
- 반영 문서:
  - `AI_FEATURE_MASTER_PLAN.md`
  - `AI_COMMAND_ARCHITECTURE.md`
  - `AI_IMPLEMENTATION_PHASES.md`
  - `AI_CODEX_VERIFICATION_PLAN.md`
  - `AI_CURRENT_DECISIONS.md`
  - `verification/AI_PHASE_VERIFICATION_SKILL.md`
  - `.claude/skills/ai-phase-verification/SKILL.md`
- 영향받은 Phase: Phase 1~11 모두 (단위화 완료 조건이 공통으로 추가됨).
- 영향받은 하네스: 모듈별 독립 검증 가능 여부가 추가 점검 항목이 됨.
- 영향받은 검증 항목: Codex 49~55 신규, Claude 자체 1·5회차 단위화 점검 추가.

---

### 2026-05-03 (Phase 0 추가수정사항 2) — 디자인 설계 문서 작성 / 디자인 적용 시점 명문화

- 변경 시각: 2026-05-03 (사용자 추가수정사항 전달 시점)
- 기존 내용:
  - `docs/ai/` 아래 디자인 설계 문서가 존재하지 않음 (UI / UX / 스타일 / 토큰).
  - 디자인 적용 시점이 명문화되지 않음. 일부 사용자가 AI 구현 전에 UI 코드를 먼저 손댈 수 있다는 오해 여지.
  - 탭 / 메뉴 / 기능 이름 변경 금지 원칙은 AI 안전 정책에 일부 명시되어 있으나, 디자인 변경에 한정한 명시는 없음.
  - AI 도우미를 위한 새 탭 추가 가능성에 대한 명확한 금지 규칙 부재.
  - 참고 디자인 (CompteExpress CRM Dashboard) 기반 스타일 언어가 문서화되지 않음.
- 최신 수정 내용:
  1. **이번 단계는 디자인 설계 문서 작성만 진행**. 실제 CSS / HTML / JS UI 수정 금지.
  2. 실제 디자인 적용은 **AI 기능 구현 + Phase별 Runtime Test + Codex 재검증 + 기존 기능 회귀 검증이 모두 끝난 뒤** 진행.
  3. 기존 **탭 이름 / 메뉴명 / 기능명 / 필드명** 변경 금지. 새 탭 추가 금지. 기능 삭제 금지.
  4. AI 도우미 전용 탭은 만들지 않음. 예약관리 / 휴무일관리 화면 **내부**에 카드 형태로 배치.
  5. 관리자 화면 내부에 AI 설정 / 로그 / 하네스 섹션을 추가하되 **관리자 탭 이름은 변경 금지**.
  6. 디자인 방향: 밝은 회색 배경 + 흰색 카드 + 진한 그린 / 차콜 그린 포인트. SaaS 관리자 대시보드 톤.
  7. 디자인 토큰 (색상 / 간격 / 크기 / 라운드 / 그림자 / 타이포그래피) 단일 소스 정의.
  8. 화면별 적용 우선순위: 예약관리 → 휴무일관리 → 환자관리 → 통계 → 관리자.
  9. 디자인 적용 전 충족 조건 12개 체크리스트 명문화.
  10. CompteExpress 참조는 **스타일 언어만** 차용, CRM 콘텐츠 / 용어 / 카드 구성은 차용하지 않음.
- 최종 반영 내용:
  - `AI_UI_UX_DESIGN_PLAN.md` 신규 — 전체 UI/UX 방향, 화면별 디자인 방향, AI 예약·휴무 도우미 UI 구조, 접기·펼치기·초기화 규칙, 우선순위, 디자인 적용 전 체크리스트.
  - `AI_UI_STYLE_GUIDE.md` 신규 — 카드 / 표 / 사이드바 / 버튼 / 입력창 / 상태 badge / 메시지 / 폼 / AI 도우미 카드 / 캘린더 / AI 로그 화면 스타일 규칙.
  - `AI_DESIGN_TOKENS.md` 신규 — 색상 / 간격 / 크기 / 라운드 / 테두리·그림자 / 타이포그래피 토큰 정의 + 참고용 의사 CSS.
  - `AI_CURRENT_DECISIONS.md` § 17 디자인 설계 / 적용 시점 원칙 신규 추가.
  - `AI_REQUIREMENTS_OVERRIDES.md` (본 문서) 본 항목 추가.
- 덮어쓴 이유: 사용자가 전체 UI 디자인 개선을 위한 설계 문서 작성을 요청했으며, 동시에 "현재 단계에서는 UI 코드 수정 금지 / 탭·메뉴·기능명 변경 금지 / AI 기능 구현·검증 완료 후 디자인 적용"을 명확히 못박음. 기존 문서가 이를 부분적으로만 다루고 있었으므로 최신 사용자 지시를 우선해 디자인 영역을 분리·신규 작성.
- 반영 문서:
  - `AI_UI_UX_DESIGN_PLAN.md` (신규)
  - `AI_UI_STYLE_GUIDE.md` (신규)
  - `AI_DESIGN_TOKENS.md` (신규)
  - `AI_CURRENT_DECISIONS.md` (§ 17 추가)
  - `AI_REQUIREMENTS_OVERRIDES.md` (본 항목)
- 영향받은 Phase: Phase 1~5 진행 중에는 디자인 코드 수정 금지. 디자인 적용은 별도 후속 Phase로 분리 (적용 단계는 AI 구현 / 검증 완료 후).
- 영향받은 하네스: 디자인 영역은 코드 변경이 없으므로 하네스 영향 없음. 단, 디자인 적용 단계에 진입하면 Regression Harness 로 기존 기능 회귀 확인 필요.
- 영향받은 검증 항목: 디자인 적용 단계에서 별도 점검 항목 추가 예정 (현 Phase 0 / 1~5 에는 영향 없음).

---

### 2026-05-03 (Phase 0 추가수정사항 3) — 실제 작동테스트 / Runtime Test 강제

- 변경 시각: 2026-05-03 (사용자 추가수정사항 전달 시점)
- 기존 내용:
  - 5회차 검증 제목이 "하네스 / 로그 / 문서 / 주석 / 실제 동작 검증" — 표현이 약하고 "실제 동작 확인"이 단일 항목으로만 표기됨.
  - Runtime Test Report 양식은 § 4 에 정의되어 있으나, 자동 진행 조건과 진행 금지 조건에서 Runtime Test 통과·실패가 명확히 구분되지 않음.
  - `.claude/skills/ai-phase-verification/SKILL.md` 의 자동 진행 조건에 Runtime Test Report 작성과 작동테스트 통과가 별도 항목으로 분리되어 있지 않음.
  - 실패 / 누락 / 서버 실행 실패 / 화면 로딩 실패 / 승인 전 DB 변경 / 승인 후 실행 실패 / 기존 기능 회귀 오류 같은 구체적 차단 조건이 § 6 에 누락됨.
- 최신 수정 내용:
  1. **5회차 제목 변경**: "하네스 / 로그 / 문서 / 주석 검증" → "**하네스 / 로그 / 문서 / 주석 / 실제 작동테스트 검증**".
  2. 5회차 안에 § 2.5.1 Runtime Test 항목 신규 — 서버 실행 / 화면 로딩 / 정상·실패 케이스 / 승인 전·후 DB 변경 / 기존 9개 기능 회귀 / AI API 실패 시 기존 프로그램 정상 동작 / Runtime Test Report 작성 확인.
  3. 각 Phase 마다 `docs/ai/verification/PHASE_XX_RUNTIME_TEST_REPORT.md` **반드시** 작성. (Phase 0 은 코드 변경 없으므로 해당사항 없음.)
  4. Runtime Test Report 양식 (§ 4) 보강 — 모든 항목을 굵게 표기하여 누락 방지, AI API 실패 시 기존 프로그램 정상 동작 항목 추가, 작성 원칙 § 4.1 신규 (실제 실행 기준, 실패 시 Codex 이전에 Claude 가 먼저 수정·재테스트, "정상 작동" 으로 기재하려면 § 2.5.1 모든 항목 통과 필요, Codex 가 본 보고서를 그대로 믿지 않고 독립 확인).
  5. § 6 다음 Phase 진행 금지 조건을 § 6.1 안전 / 설계 / § 6.2 기능 / 검증 누락 / **§ 6.3 실제 작동테스트 위반**으로 분리. § 6.3 신규 항목: 실제 작동테스트 실패 / Runtime Test Report 누락 / 서버 실행 실패 / 화면 로딩 실패 / 승인 전 DB 변경 발생 / 승인 후 실행 실패 / 기존 핵심 기능 회귀 오류.
  6. § 7.1 자동 진행 조건에 "PHASE_XX_RUNTIME_TEST_REPORT.md 작성 완료" + "실제 작동테스트 정상 통과" + "Codex 의 Runtime 독립 재확인 결과 일치" 명시. "실제 작동테스트가 실패하면 다른 모든 항목과 무관하게 다음 Phase 진행 금지" 강조.
  7. `.claude/skills/ai-phase-verification/SKILL.md` 의 검증 절차 / 자동 진행 조건 / 핵심 위반 항목을 위와 동일하게 동기화. § 4 를 § 4.1 안전 / § 4.2 기능 / **§ 4.3 실제 작동테스트 위반**으로 분리.
  8. **Codex 는 Claude Code 의 Runtime Test Report 를 그대로 믿지 않고 독립적으로 같은 항목을 다시 확인**한다는 원칙을 5회차 / 산출 양식 / 검증 절차 모두에 명시.
- 최종 반영 내용:
  - `docs/ai/verification/AI_PHASE_VERIFICATION_SKILL.md` § 2.5 / § 2.5.1 / § 4 / § 4.1 / § 6.1~6.3 / § 7.1 갱신.
  - `.claude/skills/ai-phase-verification/SKILL.md` § 2 / § 4.1~4.3 / § 5 갱신.
  - `AI_REQUIREMENTS_OVERRIDES.md` (본 문서) 본 항목 추가.
- 덮어쓴 이유: 사용자가 작동테스트 / Runtime Test 를 문서·코드 검토와 **별개의 강제 단계**로 못박아 달라고 요청. Codex 도 Claude 의 Runtime Test Report 를 그대로 믿지 말고 독립 확인하라는 원칙을 명시. 기존 문서가 이를 부분적으로만 다루고 있어 누락 / 오해 여지가 있었으므로 최신 사용자 지시를 우선해 갱신.
- 반영 문서:
  - `docs/ai/verification/AI_PHASE_VERIFICATION_SKILL.md`
  - `.claude/skills/ai-phase-verification/SKILL.md`
  - `AI_REQUIREMENTS_OVERRIDES.md` (본 항목)
- 영향받은 Phase: Phase 1~11 모두. Phase 0 은 코드 변경 없으므로 Runtime Test 해당사항 없음 — 단, 이 정책은 Phase 1 시작 시점부터 강제.
- 영향받은 하네스: Runtime Harness 가 Phase 별 강제 항목으로 명문화됨.
- 영향받은 검증 항목: 자동 진행 조건 (Runtime Test 통과 / 보고서 작성 / Codex Runtime 독립 재확인 일치) + 진행 금지 조건 (§ 6.3 신규 7개 항목).

---

### 2026-05-03 (Phase 0 보강 — 누락 점검 결과 반영) — 2~5차 기능 13개 필드 보강

- 변경 시각: 2026-05-03 (사용자 "빠진 게 없는지 다시 확인" 요청 시점)
- 기존 내용:
  - 사용자 첫 요청 § 5 에서 "각 기능마다 13개 필드 (intent / 명령 예시 / 필수·선택 입력 / DB 조회 / 승인 / 실행 가능·금지 조건 / 호출 service / 하네스 / 실제 동작 확인 / 정상·실패 케이스) 정의" 요구.
  - `create_appointment` (1차) 만 13개 필드 완비.
  - `update_appointment` / `cancel_appointment` / `create_leave` / `prepare_sms` / `summarize_today` / `summarize_tomorrow` / `analyze_stats` / `data_quality_check` / `ops_assistant` 는 4~6개 필드만 약식 기록.
- 최신 수정 내용:
  - `AI_FEATURE_MASTER_PLAN.md` § 5.2~5.5 의 모든 기능에 13개 필드 완비.
  - 각 기능의 명령 예시 / 필수·선택 입력 / 실행 가능 조건 / 실행 금지 조건 / 호출 서비스 / 하네스 / 실제 동작 확인 / 정상·실패 케이스를 누락 없이 채움.
  - 5차 기능 (`data_quality_check`, `ops_assistant`) 공통 원칙 (읽기 전용 + 추천 / 수정은 별도 승인형 intent) 명시.
  - `prepare_sms` 의 자동 발송 금지, `analyze_stats` 의 도수 30=1·60=2 가중치 합산 금지·치료항목별 개별 집계 유지, `data_quality_check` / `ops_assistant` 의 자동 수정·자동 예약·자동 휴무 시도 차단을 실행 금지 조건으로 각각 명시.
- 최종 반영 내용: `AI_FEATURE_MASTER_PLAN.md` § 5.2~5.5.
- 덮어쓴 이유: 사용자가 "빠진 게 없는지 다시 확인"을 요청했고, 점검 결과 1차 외 기능에서 13개 필드 중 일부가 누락되어 있어 사용자 첫 요청 § 5 의 명시적 요구를 만족시키지 못한 상태였음. 누락분을 보강.
- 반영 문서: `AI_FEATURE_MASTER_PLAN.md` (본 변경)
- 영향받은 Phase: Phase 7~11 (해당 기능들이 실제 구현되는 Phase). 명세가 명확해져 구현 / Codex 검증 시 누락 위험 감소.
- 영향받은 하네스: 각 기능의 하네스 매핑이 명확해짐. 기존 하네스 종류는 변경 없음.
- 영향받은 검증 항목: Codex 검증 항목은 변경 없음. 단, 항목 19~24 / 49~55 적용 시 본 문서에 정의된 13개 필드를 기준으로 일관 점검 가능.

---

### 2026-05-03 (Phase 0 보강 — 2차 재검증 결과 반영) — 누락된 cross-doc 참조 / Phase 0 체크리스트 / create_appointment 13번째 필드 보강

- 변경 시각: 2026-05-03 (사용자 "다시 한번 검증해" 요청 시점)
- 기존 내용:
  - `AI_IMPLEMENTATION_PHASES.md` § "Phase 0 완료 조건" 에 디자인 설계 문서 3개 (`AI_UI_UX_DESIGN_PLAN.md` / `AI_UI_STYLE_GUIDE.md` / `AI_DESIGN_TOKENS.md`) 가 누락되어 있었음. 추가수정사항 1·2·3 / 1~5차 13필드 보강 사실도 체크리스트에 반영되지 않음.
  - `AI_FEATURE_MASTER_PLAN.md` § 1 "문서 위치 및 목적" 에 디자인 설계 문서 3개가 참조되지 않음.
  - `AI_FEATURE_MASTER_PLAN.md` § 5.1 `create_appointment` 가 사용자 첫 요청 § 5 의 13개 필드 중 "실제 동작 확인 방법" 필드만 누락된 상태였음 (다른 12개는 모두 정의됨).
- 최신 수정 내용:
  1. `AI_IMPLEMENTATION_PHASES.md` § Phase 0 완료 조건 — `docs/ai/` 하위를 "핵심 설계 문서 / 디자인 설계 문서" 로 분리하고, 디자인 문서 3개 체크 박스 추가. 추가 조건 목록에 "단위화 / 모듈화 원칙 (추가수정사항 1) / 디자인 설계·적용 시점 (추가수정사항 2) / 실제 작동테스트 강제 (추가수정사항 3) / 1~5차 AI intent 13필드 정의 (보강)" 4 항목 추가. UI 코드 미수정 명시 추가.
  2. `AI_FEATURE_MASTER_PLAN.md` § 1 — 문서 위치를 § 1.1 핵심 설계 문서 / § 1.2 디자인 설계 문서로 분리. 디자인 3종 명시.
  3. `AI_FEATURE_MASTER_PLAN.md` § 5.1 `create_appointment` 에 "실제 동작 확인" 필드 추가 (입력 → 후보 카드 → 선택 → 최종 후보 → 승인 → DB row → 캘린더 / 표 / 통계 반영, 승인 전 DB 변경 0건, 승인 후 1건).
- 최종 반영 내용:
  - `AI_IMPLEMENTATION_PHASES.md` § Phase 0 완료 조건 갱신.
  - `AI_FEATURE_MASTER_PLAN.md` § 1 / § 5.1 갱신.
- 덮어쓴 이유: 사용자가 "다시 한번 검증해"라고 재점검을 요청했고, 2차 점검 결과 위 3건이 누락된 상태였음. 사용자 첫 요청 § 5 의 13필드 요구 / 3차 추가수정사항의 디자인 문서 추가 요구를 일관되게 반영.
- 반영 문서: `AI_IMPLEMENTATION_PHASES.md`, `AI_FEATURE_MASTER_PLAN.md`
- 영향받은 Phase: Phase 0 체크리스트 명확화 (실제 작업 변경 없음). Phase 1~ 진입 시 본 체크리스트 기준으로 통과 / 미통과 판정.
- 영향받은 하네스: 영향 없음.
- 영향받은 검증 항목: Codex 검증 시 Phase 0 산출물이 디자인 3개 + 추가수정사항 1·2·3 반영 + 1~5차 13필드까지 모두 충족됐음을 본 체크리스트로 점검.

---

### 2026-05-03 (Phase 0 보강 — 3차 재검증 결과 반영) — 모듈 설명 강화 / Codex 검증 항목 수 정합성 / 치명적 위반 / Phase 매핑 보강

- 변경 시각: 2026-05-03 (사용자 "다시 검증해" 3차 요청 시점)
- 기존 내용:
  - `AI_COMMAND_ARCHITECTURE.md` § 2.8 `ai_audit.py` 설명이 사용자 1차 요청 § 16 의 8개 기록 항목 (원본 명령 / AI 파싱 / DB 매칭 / 검증 / 사용자 선택 / 승인 / 실행 결과 / 오류 메시지) 중 일부만 명시. 상세는 § 5 에 있어 cross-reference 가 약함.
  - `AI_COMMAND_ARCHITECTURE.md` § 2.10 `ai_harness.py` 설명에 9종 하네스 연결 명시가 빠짐. 사용자 1차 요청 § 16 의 명세를 만족하지 못함.
  - `AI_CODEX_VERIFICATION_PLAN.md` § 2 제목이 "전체 48 항목" 으로 남아 있어 단위화 49~55 추가 후 갱신 누락.
  - `AI_CODEX_VERIFICATION_PLAN.md` § 3 "위 48 항목 중 해당 Phase 관련 항목" 이 동일하게 갱신 누락.
  - `AI_CODEX_VERIFICATION_PLAN.md` § 4 치명적 위반 목록이 `AI_PHASE_VERIFICATION_SKILL.md` § 6 / `.claude/skills/ai-phase-verification/SKILL.md` § 4 진행 금지 조건과 정합되지 않음 (환자 후보 선택 전 예약 등록 / 차트번호·동명이인 / 치료항목 alias / 신환 중복 / Runtime Test 위반 7항목 / 단위화 위반 누락).
  - `AI_CODEX_VERIFICATION_PLAN.md` § 5 Phase 매핑에 단위화 49~55 가 반영되지 않음 (Phase 1 이후로 한정 표기).
- 최신 수정 내용:
  1. `ai_audit.py` § 2.8 — 8개 기록 항목 모두 명시 (원본 명령 / AI 파싱 결과 / DB 매칭 결과 / 검증 결과 / 사용자 선택 (환자·치료항목) / 승인 여부 / 실행 결과 / 오류 메시지). § 5.1 cross-reference 추가.
  2. `ai_harness.py` § 2.10 — 10종 하네스 연결 명시 (parser / resolver / patient-candidate / validator / approval / executor / privacy / hallucination / regression / runtime). `AI_HARNESS_PLAN.md` § 1 cross-reference 추가. 운영 환경 권한 제한 + harness/run API 명시.
  3. `AI_CODEX_VERIFICATION_PLAN.md` § 2 제목 "전체 55 항목 (1~48 + 단위화 49~55)" 으로 수정.
  4. `AI_CODEX_VERIFICATION_PLAN.md` § 3 "위 55 항목" 으로 수정.
  5. `AI_CODEX_VERIFICATION_PLAN.md` § 4 치명적 위반 — `AI_PHASE_VERIFICATION_SKILL.md` § 6 와 정합. 환자 후보 선택 전 예약 / 차트번호·동명이인·생년월일 표시 / 치료항목 alias / 신환 중복 / Runtime Test 위반 (서버 / 화면 / 승인 전 DB / 승인 후 실행 / 회귀) / 단위화 위반 모두 추가.
  6. `AI_CODEX_VERIFICATION_PLAN.md` § 5 Phase 매핑 — 단위화 49~55 가 Phase 0 부터 모든 Phase 에 적용됨을 명시. Runtime Test (40, 41) 가 Phase 1 부터 강제됨도 함께 명시.
- 최종 반영 내용:
  - `AI_COMMAND_ARCHITECTURE.md` § 2.8 / § 2.10 갱신.
  - `AI_CODEX_VERIFICATION_PLAN.md` § 2 / § 3 / § 4 / § 5 갱신.
- 덮어쓴 이유: 사용자가 "다시 검증해"라고 3차 재점검을 요청. 점검 결과 (a) 모듈 설명이 사용자 1차 요청 § 16 명세 대비 일부 압축 / (b) Codex 검증 항목 수 갱신 누락 / (c) Codex 치명적 위반 목록이 다른 진행 금지 조건과 비정합 / (d) Codex Phase 매핑이 단위화 / Runtime Test 강제 정책을 반영하지 않음 — 4 가지 정합성 문제가 발견되어 모두 보완.
- 반영 문서: `AI_COMMAND_ARCHITECTURE.md`, `AI_CODEX_VERIFICATION_PLAN.md`
- 영향받은 Phase: Phase 0 ~ 11 모두. 매핑 / 치명적 위반 정합화로 Codex 검증 시 일관된 기준 적용 가능.
- 영향받은 하네스: 영향 없음 (10종 하네스 명시는 cross-reference 강화).
- 영향받은 검증 항목: Codex 검증 시 항목 1~55 가 일관되게 인용 가능. 치명적 위반은 다른 진행 금지 문서와 정합.

---

### 2026-05-03 (Phase 0 보강 — 4차 재검증 결과 반영) — 단일 진실의 원천 누락 보완

- 변경 시각: 2026-05-03 (사용자 "다시 검증해" 4차 요청 시점)
- 기존 내용:
  - **`AI_CURRENT_DECISIONS.md` 가 단일 진실의 원천 (Single Source of Truth) 으로 선언되어 있는데, 추가수정사항 3 (실제 작동테스트 / Runtime Test 강제) 가 별도 섹션으로 반영되지 않음.** § 15 (단위화), § 16 (디자인) 에서 § 17 (보류 항목) 으로 바로 건너뜀.
  - § 11 (API 설계) 에서 신환 등록 관련 API 2개 (`POST /api/ai/commands/{id}/propose-new-patient`, `POST /api/ai/commands/{id}/approve-new-patient`) 가 명시 누락 (단순히 "Phase 4 에서 상세화" 로만 언급).
  - § 12 (검증 / 자동 진행) 가 추가수정사항 3 의 핵심 ("실제 작동테스트 정상 통과 / Codex Runtime 독립 재확인 일치 / Codex 가 Runtime Test Report 그대로 믿지 않음") 를 명시하지 않음.
  - **`AI_FEATURE_MASTER_PLAN.md` 가 추가수정사항 1 (단위화) § 14 만 cross-reference 하고, 추가수정사항 2 (디자인) 와 3 (Runtime Test) 의 cross-reference 가 누락.** 마스터 플랜이 단일 진입점인데 두 항목 cross-reference 가 빠지면 다른 문서로의 길잡이 역할이 약함.
  - 1~5차 13필드 정의가 `AI_CURRENT_DECISIONS.md` 에 별도 § 으로 명시되지 않음 (마스터 플랜 § 5 에 정의되어 있으나 단일 진실의 원천 차원에서 누락).
- 최신 수정 내용:
  1. **`AI_CURRENT_DECISIONS.md` § 17 신규** — "실제 작동테스트 / Runtime Test 강제" 섹션 추가. § 17.1 (10개 점검 항목) / § 17.2 (진행 금지 7조건) / § 17.3 (Codex 독립 재확인) / § 17.4 (적용 시점) 으로 구성.
  2. **`AI_CURRENT_DECISIONS.md` § 18 신규** — "1~5차 AI 기능 13필드 정의" 섹션 추가. 13개 필드 + Phase 매핑 (1차 Phase 2~5 / 2차 Phase 7 / 3차 Phase 8~9 / 4차 Phase 10 / 5차 Phase 11) 명시.
  3. `AI_CURRENT_DECISIONS.md` § 11 (API 설계) — 신환 관련 API 2개 명시.
  4. `AI_CURRENT_DECISIONS.md` § 12 (검증 / 자동 진행) — Codex Runtime 독립 재확인 / 실제 작동테스트 정상 통과 / Codex 가 Claude 의 Runtime Test Report 그대로 믿지 않음 명시.
  5. `AI_CURRENT_DECISIONS.md` § 17 (기존) → § 19 로 번호 이동 (현재 보류 / 미정 항목).
  6. **`AI_FEATURE_MASTER_PLAN.md` § 15 신규** — "디자인 설계 / 적용 시점 원칙" cross-reference 섹션 추가.
  7. **`AI_FEATURE_MASTER_PLAN.md` § 16 신규** — "실제 작동테스트 / Runtime Test 강제" cross-reference 섹션 추가.
  8. `AI_FEATURE_MASTER_PLAN.md` § 14 헤더에 "추가수정사항 1" 명시 (기존엔 "2026-05-03 추가수정사항" 으로만 표기되어 1·2·3 구분 안 됨).
- 최종 반영 내용:
  - `AI_CURRENT_DECISIONS.md` § 11 / § 12 / § 17 / § 18 (신규) / § 19 (이동) 갱신.
  - `AI_FEATURE_MASTER_PLAN.md` § 14 (헤더) / § 15 (신규) / § 16 (신규) 갱신.
- 덮어쓴 이유: 사용자가 "다시 검증해" 4차 재점검 요청. 점검 결과 단일 진실의 원천 (`AI_CURRENT_DECISIONS.md`) 이 4가지 추가수정사항 중 추가수정사항 3 (Runtime Test) 와 13필드 보강을 별도 § 으로 반영하지 않은 가장 중요한 누락이 발견됨. 마스터 플랜도 디자인·Runtime Test cross-reference 가 빠져 있어 다른 문서로의 길잡이 역할이 부족했음. 모두 보완.
- 반영 문서: `AI_CURRENT_DECISIONS.md`, `AI_FEATURE_MASTER_PLAN.md`
- 영향받은 Phase: Phase 0 ~ 11 모두. 단일 진실의 원천이 4가지 추가수정사항 + 13필드 보강을 모두 반영하므로 향후 Phase 진행 시 일관 기준 확보.
- 영향받은 하네스: 영향 없음 (cross-reference 강화).
- 영향받은 검증 항목: Codex 검증 시 `AI_CURRENT_DECISIONS.md` 만 봐도 Runtime Test 강제 / 13필드 정의 / 신환 API 등 모든 핵심 결정을 확인 가능.

---

### 2026-05-03 (Phase 0 보강 — 5차 재검증 결과 반영) — 진행 금지 조건 4 카테고리 정합

- 변경 시각: 2026-05-03 (사용자 "다시 검증해" 5차 요청 시점)
- 기존 내용:
  - **`AI_SAFETY_POLICY.md` § 7 진행 금지 조건이 `AI_PHASE_VERIFICATION_SKILL.md` § 6 / `AI_CODEX_VERIFICATION_PLAN.md` § 4 / `.claude/skills SKILL.md` § 4 와 정합되지 않음**. SAFETY § 7 은 단순 list 인 반면 다른 문서는 6.1/6.2/6.3 또는 4.1/4.2/4.3 카테고리로 분리. SAFETY § 7 에 Runtime Test 위반 7항목 / 단위화 위반이 명시적 § 으로 분리되어 있지 않음.
  - **`AI_PHASE_VERIFICATION_SKILL.md` § 6 에 § 6.4 단위화 / 모듈화 위반 카테고리가 누락**. § 6.1 (안전), § 6.2 (기능), § 6.3 (Runtime Test) 만 있음.
  - **`.claude/skills/ai-phase-verification/SKILL.md` § 4 에 § 4.4 단위화 / 모듈화 위반 카테고리가 누락**.
  - 위 결과로 4개 진행 금지 조건 문서 (SAFETY / verification skill / claude skill / Codex plan) 가 단위화 위반 항목 분류에서 정합되지 않음.
- 최신 수정 내용:
  1. `AI_SAFETY_POLICY.md` § 7 — § 7.1 (안전 / 설계) / § 7.2 (기능 / 검증 누락) / § 7.3 (Runtime Test) / § 7.4 (단위화) 4 카테고리로 분리. 다른 3 문서와 1:1 정합되도록 마지막 줄에 "본 § 7 의 4 카테고리는 ... 와 1:1 정합되어야 합니다" 명시.
  2. `verification/AI_PHASE_VERIFICATION_SKILL.md` § 6 — § 6.4 단위화 / 모듈화 위반 카테고리 신규 (5 항목: 거대 함수 / executor DB 조작 / 도메인 중복 구현 / 모듈 독립 검증 불가 / 역할 주석 누락). 마지막 줄에 다른 3 문서와의 정합 명시.
  3. `.claude/skills/ai-phase-verification/SKILL.md` § 4 — § 4.4 단위화 / 모듈화 위반 카테고리 신규 (5 항목).
- 최종 반영 내용: `AI_SAFETY_POLICY.md`, `verification/AI_PHASE_VERIFICATION_SKILL.md`, `.claude/skills/ai-phase-verification/SKILL.md`
- 덮어쓴 이유: 사용자 "다시 검증해" 5차 재점검 요청. 점검 결과 (a) SAFETY § 7 이 다른 진행 금지 조건 문서와 카테고리 분리 / 단위화 위반 명시 차이로 정합되지 않음 / (b) verification skill 과 claude skill 에 단위화 위반 § 누락 발견. 4 문서가 1:1 정합되도록 동기화.
- 반영 문서: `AI_SAFETY_POLICY.md` (§ 7), `verification/AI_PHASE_VERIFICATION_SKILL.md` (§ 6), `.claude/skills/ai-phase-verification/SKILL.md` (§ 4)
- 영향받은 Phase: Phase 0 ~ 11 모두. Codex 검증 시 4 진행 금지 조건 문서 모두에서 일관 기준으로 점검 가능.
- 영향받은 하네스: 영향 없음 (cross-reference 정합).
- 영향받은 검증 항목: 진행 금지 조건이 정확히 정합되어 1 카테고리 위반 시 4 문서 모두에서 동일하게 차단.

---

### 2026-05-03 (Phase 0 보강 — 6차 재검증 결과 반영) — 4문서 4카테고리 항목 수 1:1 정합

- 변경 시각: 2026-05-03 (사용자 "다시 검증해" 6차 요청 시점)
- 기존 내용:
  - 5차 점검에서 4 진행 금지 조건 문서를 4 카테고리 (안전 / 기능 / Runtime Test / 단위화) 로 정합화했으나 **항목 수까지는 1:1 정합되지 않음**.
  - `AI_SAFETY_POLICY.md` § 7.4 단위화 위반: **4 항목** (역할 주석 누락 빠짐). 다른 문서는 5 항목.
  - `AI_CODEX_VERIFICATION_PLAN.md` § 4 치명적 위반: 다른 3 문서는 4.1/4.2/4.3/4.4 카테고리로 분리, **Codex Plan 만 단일 list**. 또한 단위화 위반은 5 항목 중 3 항목만 명시.
  - `.claude/skills/ai-phase-verification/SKILL.md` § 4.1: **4 항목** (압축 형태). 다른 3 문서는 8 항목.
  - `.claude SKILL § 4.2`: **6 항목** (압축 형태). 다른 3 문서는 9 항목.
  - `AI_REQUIREMENTS_OVERRIDES.md` 베이스라인 항목 날짜가 `2025-XX-XX` placeholder 로 남음 (실제 시점은 2026-05-03).
  - `AI_FEATURE_MASTER_PLAN.md` § 13 다음 단계 cross-reference 에 디자인 docs 3개 + verification skill 누락 (5 docs only).
- 최신 수정 내용:
  1. `AI_SAFETY_POLICY.md` § 7.4 — "역할 주석 누락" 추가 + 다른 항목들도 다른 문서와 동일한 자세한 표현으로 갱신. **4 → 5 항목**.
  2. `AI_CODEX_VERIFICATION_PLAN.md` § 4 — 치명적 위반을 § 4.1 (안전 / 설계 8) / § 4.2 (기능 / 검증 9) / § 4.3 (Runtime Test 7) / § 4.4 (단위화 5) **4 카테고리로 재구성**.
  3. `.claude SKILL § 4.1` — 4 항목 (압축) → **8 항목 (자세한 표현)**, 다른 3 문서와 정합.
  4. `.claude SKILL § 4.2` — 6 항목 (압축) → **9 항목 (자세한 표현)**, 다른 3 문서와 정합.
  5. `AI_REQUIREMENTS_OVERRIDES.md` 베이스라인 — `2025-XX-XX` → `2026-05-03` 실제 시점으로 수정.
  6. `AI_FEATURE_MASTER_PLAN.md` § 13 — 디자인 docs 3개 (`AI_UI_UX_DESIGN_PLAN.md` / `AI_UI_STYLE_GUIDE.md` / `AI_DESIGN_TOKENS.md`) + `verification/AI_PHASE_VERIFICATION_SKILL.md` cross-reference 추가. **5 → 9 docs**.
- 최종 반영 내용:
  - `AI_SAFETY_POLICY.md` § 7.4
  - `AI_CODEX_VERIFICATION_PLAN.md` § 4
  - `.claude/skills/ai-phase-verification/SKILL.md` § 4.1, § 4.2
  - `AI_REQUIREMENTS_OVERRIDES.md` 베이스라인 항목
  - `AI_FEATURE_MASTER_PLAN.md` § 13
- 덮어쓴 이유: 사용자 "다시 검증해" 6차 재점검 요청. 5차에서 카테고리 분리는 했으나 **항목 수까지 1:1 정합되지 않음**을 발견. 4 진행 금지 조건 문서 (SAFETY / verification / claude / Codex) 의 4 카테고리 × 4 문서 = 16 셀 항목 수가 모두 동일 (8/9/7/5) 하도록 동기화. 또한 베이스라인 placeholder / 마스터플랜 cross-reference 누락도 함께 수정.
- 반영 문서: `AI_SAFETY_POLICY.md`, `AI_CODEX_VERIFICATION_PLAN.md`, `.claude/skills/ai-phase-verification/SKILL.md`, `AI_REQUIREMENTS_OVERRIDES.md`, `AI_FEATURE_MASTER_PLAN.md`
- 영향받은 Phase: Phase 0 ~ 11 모두. 이제 **어떤 위반이든 4 문서에서 동일한 카테고리 / 동일한 항목 수로 차단**됨. Codex 검증 시 일관 기준 확보.
- 영향받은 하네스: 영향 없음.
- 영향받은 검증 항목: 4 진행 금지 조건 문서가 16 셀 1:1 정합 — Codex 가 어느 문서를 보더라도 동일한 결정 가능.

---

### 2026-05-03 (Phase 0 보강 — 7차 재검증 결과 반영) — 4문서 4카테고리 표현 100% 정합 + Master § 5 13필드 line 통일

- 변경 시각: 2026-05-03 (사용자 "다시 검증해" 7차 요청 시점)
- 기존 내용:
  - 6차에서 4 카테고리 4 문서의 **항목 수** 1:1 정합을 완료했으나 **표현 (wording) 까지는 100% 동일하지 않음**.
  - `.claude/skills SKILL § 4.4` 단위화 위반 — "(`parse_and_resolve_and_validate_and_save()` 같은 통합 함수)" 부연 누락. "(예약 / 환자 / 치료항목 / 휴무 / 문자 / 통계 / 완료체크)" 부연 누락. "새 / 크게 수정한 파일·함수에" 수식어 누락.
  - `verification skill § 6.4` 단위화 위반 3번 — "...로직을 AI 모듈에서 재구현" 추가 표현이 SAFETY / Codex Plan 과 다름.
  - `AI_FEATURE_MASTER_PLAN.md` § 5 가 13필드를 10 line 묶음 형태로 표기 (필수+선택 / 실행가능+금지 / 정상+실패). SSOT § 18 은 13 line 명확 분리. 표기 불일치.
  - 마스터 § 5 에 "13필드 누락 시 Phase 진입 / 검증 통과 불가" 강제 메시지 누락.
- 최신 수정 내용:
  1. `.claude/skills SKILL § 4.4` — 부연 표현 추가하여 **SAFETY § 7.4 / Codex § 4.4 와 100% 동일 표현**.
  2. `verification skill § 6.4` — "AI 모듈에서 재구현" 표현을 단순화하여 다른 3 문서와 정합.
  3. `AI_FEATURE_MASTER_PLAN.md` § 5 — **13필드를 1-13 명확 분리** 로 표기 (SSOT § 18 과 동일 형식).
  4. `AI_FEATURE_MASTER_PLAN.md` § 5 — "13필드가 누락된 intent 는 해당 Phase 진입 / 검증 통과 불가" 강제 메시지 추가.
  5. SSOT § 18 cross-reference 명시 (`AI_CURRENT_DECISIONS.md § 18 과 1:1 정합`).
- 최종 반영 내용:
  - `.claude/skills/ai-phase-verification/SKILL.md` § 4.4
  - `verification/AI_PHASE_VERIFICATION_SKILL.md` § 6.4
  - `AI_FEATURE_MASTER_PLAN.md` § 5
- 덮어쓴 이유: 사용자 "다시 검증해" 7차 재점검 요청. 6차에서 항목 수까지는 정합했으나 **표현 (wording)** 이 100% 동일하지 않음을 발견. 4 문서 4 카테고리에서 한 카테고리만 골라 비교해도 동일 표현이 나오도록 동기화. 또한 마스터 § 5 가 13필드 묶음 표기로 SSOT § 18 과 형식 불일치 — 1:1 line 분리로 통일.
- 반영 문서: `.claude/skills/ai-phase-verification/SKILL.md`, `verification/AI_PHASE_VERIFICATION_SKILL.md`, `AI_FEATURE_MASTER_PLAN.md`
- 영향받은 Phase: Phase 0 ~ 11 모두. 4 진행 금지 조건 문서가 **표현까지 100% 정합** — Codex 가 어느 문서를 보더라도 단어 단위로 동일 결정.
- 영향받은 하네스: 영향 없음.
- 영향받은 검증 항목: 표현 통일로 검증 시 ambiguity 제거.

---

### 2026-05-03 (Phase 0 보강 — 8차 재검증 결과 반영) — Cat .3 Runtime Test 4문서 표현 100% 정합

- 변경 시각: 2026-05-03 (사용자 "재검증해" 8차 요청 시점)
- 기존 내용:
  - 7차 점검에서 Cat .4 단위화는 4 문서 100% 일치, Cat .1/.2 도 정합화. 그러나 **Cat .3 Runtime Test 7항목의 표현이 4 문서 간 비정합**.
  - `verification skill § 6.3`: 굵게 (`**...**`) + 자세한 부연 (예: "단 1건이라도 변경 시 즉시 실패", "예약 / 환자 / 치료사 / 의사 / 치료항목 / 휴무 / 문자 / 통계 / 완료체크 중 하나라도")
  - `claude SKILL § 4.3`: 굵게 + 중간 길이 부연
  - `SAFETY § 7.3`: 평문 + 짧은 부연 + "Runtime Test Report 누락" (백틱 없음)
  - `Codex § 4.3`: 평문 + 짧은 부연 + `PHASE_XX_RUNTIME_TEST_REPORT.md` (백틱 있음)
  - 항목 수는 7개 모두 동일하지만 굵기 / 부연 길이 / 문서명 코드 표기에서 4 문서가 모두 다름.
- 최신 수정 내용:
  1. 통일 기준: **평문 + 짧은 부연 + 문서명 백틱 표기** (가장 깔끔한 SAFETY 형식 + Codex 의 코드 표기 채택).
  2. `verification/AI_PHASE_VERIFICATION_SKILL.md` § 6.3 — 굵게·긴 부연 제거, 평문화.
  3. `.claude/skills/ai-phase-verification/SKILL.md` § 4.3 — 굵게·중간 부연 제거, 평문화.
  4. `AI_SAFETY_POLICY.md` § 7.3 — `Runtime Test Report` → `` `PHASE_XX_RUNTIME_TEST_REPORT.md` `` 백틱 표기 통일.
  5. `AI_CODEX_VERIFICATION_PLAN.md` § 4.3 — (변경 없음, 기준에 맞음).
- 최종 반영 내용:
  - `AI_SAFETY_POLICY.md` § 7.3
  - `verification/AI_PHASE_VERIFICATION_SKILL.md` § 6.3
  - `.claude/skills/ai-phase-verification/SKILL.md` § 4.3
- 검증: `diff` 명령으로 4 문서 § 7.3 / 6.3 / 4.3 / 4.3 모두 0 차이 확인. **Cat .1, .2, .3, .4 4 카테고리 × 4 문서 = 16 셀 모두 표현 100% 정확 일치** (이전 6차 / 7차 누계 합산 + 8차 보강).
- 덮어쓴 이유: 사용자 "재검증해" 8차 재점검 요청. 7차에서 Cat .3 minor 표현 차이를 알고 있었으나 그대로 둠 — 이번엔 100% 정합 차원에서 통일. 이제 4 진행 금지 조건 문서가 4 카테고리 × 4 문서 모두에서 단어 단위로 동일.
- 반영 문서: `AI_SAFETY_POLICY.md`, `verification/AI_PHASE_VERIFICATION_SKILL.md`, `.claude/skills/ai-phase-verification/SKILL.md`
- 영향받은 Phase: Phase 0 ~ 11 모두. 4 진행 금지 조건이 단어 단위 정합 — Codex 가 어느 문서를 보더라도 100% 동일 결정.
- 영향받은 하네스: 영향 없음.
- 영향받은 검증 항목: 4 진행 금지 조건이 표현 / 항목 수 / 카테고리 모두 1:1 정합.
- 8차에서 정합 확인된 영역 (이상 없음):
  - AI_HARNESS_PLAN § 4 vs Implementation Phases Phase별 하네스 (Phase 2: Parser/Resolver / Phase 3: Validator/Patient Candidate / Phase 4: 신환 흐름 / Phase 5: Approval/Executor 모두 정합)
  - 8개 산출 문서 이름 (verification skill / claude SKILL 정확 일치)
  - 디자인 docs 3개 cross-reference 일관성
  - SSOT § 9 모듈 10개 vs Architecture § 2 모듈 10개

---

### 2026-05-03 (Phase 0 보강 — 9차 재검증 결과 반영) — 추가수정사항 번호 일관성

- 변경 시각: 2026-05-03 (사용자 "재검증해" 9차 요청 시점)
- 기존 내용:
  - SSOT § 16 / § 17 은 "(2026-05-03 추가수정사항 2)" / "(추가수정사항 3)" 으로 번호 명시.
  - **SSOT § 15 단위화 / 모듈화 헤더는 "(2026-05-03 추가수정사항)"** — 추가수정사항 1 / 2 / 3 중 어느 것인지 번호 누락 (실제로는 1).
  - **`AI_COMMAND_ARCHITECTURE.md` § 10, § 11, § 12, § 13, § 14 모두 "(2026-05-03 추가수정사항)"** — 모두 추가수정사항 1 (단위화) 인데 번호 누락.
  - 결과: 다른 문서가 "추가수정사항 1" 을 cross-reference 할 때 SSOT § 15 / Architecture § 10~14 가 "추가수정사항 1" 인지 직접 확인이 어려움.
- 최신 수정 내용:
  1. `AI_CURRENT_DECISIONS.md` § 15 헤더 — `(확정, 2026-05-03 추가수정사항)` → `(확정, 2026-05-03 추가수정사항 1)`.
  2. `AI_COMMAND_ARCHITECTURE.md` § 10 헤더 — `(단위화 / 모듈화 원칙, 2026-05-03 추가수정사항)` → `(단위화 / 모듈화 원칙, 2026-05-03 추가수정사항 1)`.
  3. `AI_COMMAND_ARCHITECTURE.md` § 11 / § 12 / § 13 / § 14 헤더 모두 `(2026-05-03 추가수정사항)` → `(2026-05-03 추가수정사항 1)` 추가.
- 최종 반영 내용:
  - `AI_CURRENT_DECISIONS.md` § 15
  - `AI_COMMAND_ARCHITECTURE.md` § 10, § 11, § 12, § 13, § 14
- 덮어쓴 이유: 사용자 "재검증해" 9차 점검. 검증 결과 추가수정사항 번호 (1 / 2 / 3) 가 일부 헤더에서 누락. SSOT § 15 와 Architecture § 10~14 모두 추가수정사항 1 (단위화) 임을 명시. 이로써 cross-doc 검색 시 "추가수정사항 1" 키워드로 모든 단위화 관련 § 을 찾을 수 있게 됨.
- 반영 문서: `AI_CURRENT_DECISIONS.md`, `AI_COMMAND_ARCHITECTURE.md`
- 영향받은 Phase: 영향 없음 (헤더 표기 정합화).
- 영향받은 하네스: 영향 없음.
- 영향받은 검증 항목: cross-doc 검색 시 추가수정사항 번호 기준으로 일관 검색 가능.
- 9차에서 정합 확인된 영역 (이상 없음):
  - AI 명령 상태값 23개 = 9 (기본) + 4 (환자 후보) + 6 (신환) + 4 (치료항목) ✅
  - API 10개 = 8 (main) + 2 (신환 propose / approve) ✅
  - 자동 진행 조건 SSOT § 12 vs verification skill § 7.1 정합 ✅
  - 추출 필드 9개 (intent / patient_name / chart_number / date_text / time_text / therapist_name / treatment_text / treatment_items / memo) Master § 6.1 vs Architecture § 2.1 정합 ✅
  - 변경 이력 12개 (베이스라인 + 추가수정사항 1·2·3 + 보강 1~8) 모두 기록 ✅

---

### 2026-05-04 (Phase 0 추가수정사항 4) — Claude Code 자체 검증 5회 → 10회 확장 + 자만 없는 냉정한 판단 원칙

- 변경 시각: 2026-05-04 (사용자 직접 지시)
- 사용자 원문: "코덱스 사용량이 꽉차서 앞으로 검증횟수를 10번으로 조정한다 추가로 자만하지않고 냉정하게 판단한다. 이걸 스킬에 추가수정해줘"
- 기존 내용:
  - `verification skill` § 1 / § 2: "Claude Code 자체 5회 검증" — 1~5회차로 한정.
  - `.claude SKILL` § 2: "5회 검증" 1~5회차.
  - `AI_CURRENT_DECISIONS.md` § 12: "Claude 자체 5회 검증" 명시.
  - `AI_IMPLEMENTATION_PHASES.md` 각 Phase 공통 완료 조건 #2: "Claude Code 자체 5회 검증 완료".
  - SSOT 에 자만 없는 냉정한 판단 원칙 미명시.
- 최신 수정 내용:
  1. **Claude Code 자체 검증 횟수: 5회 → 10회 확장**.
  2. 6~10회차 신규 정의:
     - 6회차: 단위화 / 모듈화 깊이 검증
     - 7회차: Cross-doc 정합성 검증 (4 진행 금지 조건 16셀 / 8 산출 / 10 모듈·하네스·API / 23 상태값 / 9 추출 필드)
     - 8회차: 표현 / 명명 / 헤더 일관성 검증
     - 9회차: 추가수정사항 반영 / SSOT 우선 검증
     - 10회차: **자만 없는 냉정한 최종 판단** (자체 검증 결과 그대로 신뢰 금지 / 미점검 영역 적극 탐색 / 성과 과장 경계 / 추가 누락 가능성 인정 / Codex 가 모든 것을 잡아주지 못함을 전제 / 사용자 의도 따름)
  3. **자만 없는 냉정한 판단 원칙** 6 항목 신규 — verification skill § 1 / SSOT § 19.3 / Master § 17 에 명시.
  4. Codex 사용량 제약 인지 명시 — Codex 가 모든 것을 잡아주지 못하므로 Claude Code 가 끝까지 책임 검증.
- 최종 반영 내용:
  - `verification/AI_PHASE_VERIFICATION_SKILL.md` § 1 (12번째 항목 추가) / § 2 (제목 변경 + 냉정한 판단 원칙) / § 2.6 ~ § 2.10 (6~10회차 신규).
  - `.claude/skills/ai-phase-verification/SKILL.md` § 2 (1~10회차 명시).
  - `AI_CURRENT_DECISIONS.md` § 12 (10회 검증 / 자만 없는 판단 추가) / § 19 신규 (검증 횟수 / 냉정한 판단 원칙) / § 20 (현재 보류 항목 번호 이동).
  - `AI_IMPLEMENTATION_PHASES.md` 각 Phase 공통 완료 조건 #2 (10회 검증 / +#3-1 10회차 냉정한 판단 통과).
  - `AI_FEATURE_MASTER_PLAN.md` § 17 신규 (cross-reference 섹션).
  - `AI_REQUIREMENTS_OVERRIDES.md` (본 문서) 본 항목 추가.
- 덮어쓴 이유: 사용자 지시. Codex 사용량 제약으로 Codex 가 모든 것을 잡아주지 못하는 상황. Claude Code 가 자체 검증 깊이를 늘리고 자만 없이 끝까지 책임 검증하는 체제로 전환.
- 반영 문서: `verification/AI_PHASE_VERIFICATION_SKILL.md`, `.claude/skills/ai-phase-verification/SKILL.md`, `AI_CURRENT_DECISIONS.md`, `AI_IMPLEMENTATION_PHASES.md`, `AI_FEATURE_MASTER_PLAN.md`, `AI_REQUIREMENTS_OVERRIDES.md`
- 영향받은 Phase: Phase 0 ~ Phase 11 모두. Phase 0 자체검증을 9차까지 진행했지만 본 추가수정사항 적용 후 10회 검증 + 냉정한 판단 원칙으로 재검증 필요 (10회 검증 첫 회차로 진행 가능).
- 영향받은 하네스: 영향 없음.
- 영향받은 검증 항목:
  - 1~5회차 기존 검증 항목 유지.
  - 6~10회차 신규 추가.
  - 10회차 (냉정한 판단) 미통과 시 다음 Phase 진행 금지.
- 1차 점검까지 9차 누계 31건 + 본 추가수정사항 4 = 누락 / 정합성 / 강화 32건째 변경 사항.

---

### 2026-05-04 (Phase 0 보강 — 10회차 자만 없는 판단 검증 결과 반영)

- 변경 시각: 2026-05-04 (사용자 "10회차 검증진행" 지시)
- 본 회차의 점검 원칙: **자체 검증 결과를 그대로 신뢰하지 않음 / 미점검 영역 적극 탐색 / 성과 과장 경계**.
- 10회차 점검에서 발견한 누락 (자만 없이 인정):
  1. **`AI_SAFETY_POLICY.md` § 7 진행 금지 조건에 10회차 / 자만 없는 판단 언급 0건** — 추가수정사항 4 반영 시 SAFETY 갱신 누락. 4 진행 금지 조건 문서 중 SAFETY / Codex 가 자만 없는 판단을 언급조차 하지 않음.
  2. **`AI_CODEX_VERIFICATION_PLAN.md` § 4 / § 2 에 10회차 / 자만 없는 판단 언급 0건** — Codex 검증 항목에도 추가수정사항 4 가 반영되지 않음.
  3. **4 진행 금지 조건 문서 모두에 § X.5 (10회차 미통과) 카테고리가 누락** — 사용자가 자만 경계를 강조했으나 실제로는 진행 금지 조건이 아닌 단순 권장사항 수준.
  4. **`Codex Plan § 2` 검증 항목 수가 55 로 그대로** — 추가수정사항 4 의 새 검증 항목 (10회 검증 / 자만 없는 판단) 이 Codex 검증 항목에 반영되지 않음.
  5. **자동 진행 조건에 "10회 검증 완료" / "10회차 통과" 누락** — verification skill § 7.1, claude SKILL § 5 모두 누락.
  6. **claude SKILL § 4.5 / Codex § 4.5 의 부연 표현이 SAFETY / verification 과 다름** — 7차 점검에서 이미 패턴을 알았으면서도 동일 실수 반복 (자만 경계 사례).
- 최신 수정 내용:
  1. **4 진행 금지 조건 문서에 § X.5 신규 카테고리 추가** (`AI_SAFETY_POLICY.md` § 7.5 / `verification/AI_PHASE_VERIFICATION_SKILL.md` § 6.5 / `.claude SKILL` § 4.5 / `AI_CODEX_VERIFICATION_PLAN.md` § 4.5). 5 항목 1:1 정합 (diff 0 검증).
  2. **Codex Plan § 2.12 신규** — 검증 항목 56~61 추가 (10회 검증 수행 / 10회차 통과 / 자만 없는 판단 / 미점검 탐색 / 성과 과장 경계 / Codex 사용량 인지).
  3. **Codex Plan § 2 제목** — "55 항목" → "61 항목 (1~48 + 49~55 + 56~61)".
  4. **Codex Plan § 5 Phase 매핑** — 모든 Phase 에 56~61 추가.
  5. **Codex Plan § 5 끝부분** — "검증 횟수 / 자만 없는 판단 (56~61) 은 Phase 0 부터 강제" 명시.
  6. **자동 진행 조건 갱신** — verification skill § 7.1 / claude SKILL § 5 에 "Claude Code 자체 10회 검증 완료" + "10회차 자만 없는 냉정한 판단 통과" 추가. 진행 금지 사유 § 6.5 / § 4.5 명시.
  7. **claude § 4.5 / Codex § 4.5 부연 표현 보강** — SAFETY § 7.5 와 동일 표현으로 정합 (7차 점검 패턴 반복 인정).
- 최종 반영 내용:
  - `AI_SAFETY_POLICY.md` § 7.5 (신규)
  - `verification/AI_PHASE_VERIFICATION_SKILL.md` § 6.5 (신규) / § 7.1 (자동 진행 조건 보강)
  - `.claude/skills/ai-phase-verification/SKILL.md` § 4.5 (신규) / § 5 (자동 진행 조건 보강)
  - `AI_CODEX_VERIFICATION_PLAN.md` § 4.5 (신규) / § 2.12 (검증 항목 56~61 신규) / § 2 제목 / § 5 매핑
- 덮어쓴 이유: 10회차 자만 없는 판단 회차에서 추가수정사항 4 의 반영이 표면적이었음을 발견. 4 진행 금지 조건 문서 중 SAFETY / Codex 는 추가수정사항 4 자체를 인지하지 않은 상태였음. 사용자가 "냉정하게 판단" 을 명시했으므로 단순 권장이 아니라 진행 금지 조건으로 강제.
- 반영 문서: 위 4 진행 금지 조건 문서 + Codex Plan
- 영향받은 Phase: Phase 0 ~ Phase 11 모두. 10회차 미통과 시 자동 진행 금지가 강제됨.
- 영향받은 하네스: 영향 없음.
- 영향받은 검증 항목: Codex 검증 항목 55 → 61 확장. 4 진행 금지 조건 문서 4 카테고리 → 5 카테고리.
- **냉정한 판단 결과**: 추가수정사항 4 반영이 표면적이었음을 인정. 9차 점검까지 31건 누락 발견 후 추가수정사항 4 적용 시점에서 새로 6건 (본 회차) 의 누락이 또 발생. 누적 38건. **추가 누락 가능성을 여전히 배제할 수 없음**.

---

## 3. 향후 추가 변경 (템플릿)

새로운 추가수정사항이 들어오면 아래 템플릿을 복사해서 채워주세요.

### YYYY-MM-DD — 변경 제목

- 변경 시각:
- 기존 내용:
- 최신 수정 내용:
- 최종 반영 내용:
- 덮어쓴 이유:
- 반영 문서:

(필요 시 영향받은 Phase 번호, 영향받은 하네스, 영향받은 검증 항목도 함께 기록)

---

## 4. 운영 가이드

- **Claude Code**: 사용자가 "추가수정사항" 또는 그에 준하는 변경 요구를 전달하면, 본 문서에 항목을 추가하고 관련 문서를 갱신한 뒤 `AI_CURRENT_DECISIONS.md`도 함께 갱신합니다.
- **Codex**: Phase 검증 시 본 문서의 최근 변경이 모든 관련 문서에 반영되었는지, 누락된 문서가 없는지 점검합니다.
- 충돌 / 누락이 발견되면 Codex는 해당 Phase를 "조건부 통과" 또는 "실패"로 판정합니다.
