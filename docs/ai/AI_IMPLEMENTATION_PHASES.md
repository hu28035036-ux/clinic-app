# AI_IMPLEMENTATION_PHASES.md

> AI 기능을 단계적으로 도입하기 위한 Phase 계획.
> 각 Phase 완료 조건은 `verification/AI_PHASE_VERIFICATION_SKILL.md`에서 강제됩니다.

---

## Phase 0. 전체 설계 문서 작성 (현재 단계)

- 실제 구현 없음
- `docs/ai/` 아래 설계 문서 일괄 작성
- 검증 스킬 작성
- Codex 검증 계획 작성

**완료 조건:**
- 본 문서 § "Phase 0 완료 조건"에 정의된 모든 문서 생성

---

## Phase 1. AI 명령 스키마 + 로그 테이블 + provider 구조

- 실제 예약 저장 기능 없음
- AI 명령 상태와 로그 기반 마련
- 외부 AI API provider 구조 설계 / 구현
- API 실패 시 기존 프로그램 보호

**구현 대상:**
- `app/ai/ai_command_schema.py`
- `app/ai/ai_provider.py` (인터페이스 + Mock + 1개 실제 provider)
- `app/ai/ai_audit.py`
- 마이그레이션: `ai_command_logs`, `treatment_aliases`
- `dosu_clinic.spec` `hiddenimports` 등록

**아직 하지 않음:**
- 실제 자연어 파싱 흐름
- DB 매칭
- 검증 / 승인 / 실행
- UI

---

## Phase 2. create_appointment 파서 + resolver

- 자연어 → 예약 후보 변환 (실행 없음)
- 환자명 / 차트번호 / 치료사 / 치료항목 / alias 매칭
- 생년월일 / 연락처는 AI가 아니라 DB에서 조회
- 환자 후보가 여러 명이면 선택 필요 상태로 처리
- **아직 예약 저장 없음**

**구현 대상:**
- `app/ai/ai_parser.py`
- `app/ai/ai_resolver.py`
- Parser Harness, Resolver Harness

---

## Phase 3. validator + preview UI

- 휴무 / 반차 / 중복 / 시간겹침 검증
- 환자 후보 선택 UI (차트번호 / 이름 / 생년월일 / 연락처 표시)
- 치료항목 다중 선택 / alias 충돌 UI
- 신환 등록 제안 UI (실제 등록은 Phase 4)
- **승인 전 저장 금지 보장**

**구현 대상:**
- `app/ai/ai_validator.py`
- `app/ai/ai_preview.py`
- 환자 후보 선택 / 치료항목 선택 UI
- Validator Harness, Patient Candidate Harness

---

## Phase 4. 신환 등록 연계 흐름

- 환자 검색 실패 시 신환 등록 제안
- 차트번호 / 이름 / 생년월일 / 연락처 입력 폼
- 중복 검사 (차트번호 / 이름+생년월일 / 이름+연락처 / 연락처)
- 신환 등록 승인 (별도 승인 게이트)
- 예약 재검증
- 예약 등록 승인

**구현 대상:**
- 신환 등록 흐름 통합 (validator 확장)
- 신환 등록 / 예약 등록 각각 별도 로그
- 권한 정책 적용 (일반 직원 / 관리자)
- 신환 흐름 하네스

---

## Phase 5. approve executor

- 승인 후 기존 예약 생성 로직 호출
- 승인 직전 **최종 재검증**
- 로그 저장
- 신환 등록과 예약 등록의 executor 분리

**구현 대상:**
- `app/ai/ai_executor.py`
- Approval Harness, Executor Harness

---

## Phase 6. 하네스 구축 (풀세트)

- Parser / Resolver / Patient Candidate / Validator / Approval / Executor / Privacy / Hallucination / Regression / Runtime 풀세트
- CI 통합

**구현 대상:**
- `app/ai/ai_harness.py`
- `tests/test_ai_*.py`
- `POST /api/ai/harness/run` (관리자 전용)

---

## Phase 7. 예약 변경 / 취소 AI

- intent: `update_appointment`, `cancel_appointment`
- 변경 전·후 비교
- 취소는 기존 취소 상태 처리 로직 사용 (물리 삭제 금지)
- 승인 후 실행

---

## Phase 8. 휴무 등록 AI

- intent: `create_leave`
- 치료사 휴무 / 반차 등록 후보 생성
- 기존 예약 충돌 검증 (해당 시간대 예약자 별도 고지)
- 승인 후 등록

---

## Phase 9. 예약문자 준비 AI

- intent: `prepare_sms`
- **문자 자동 발송 금지**
- 문자 내용 준비 + 체크박스 + 붙여넣기용 출력까지만

---

## Phase 10. 예약 요약 / 통계 분석 AI

- intent: `summarize_today`, `summarize_tomorrow`, `analyze_stats`
- **읽기 전용**
- DB 조회 결과만 요약
- 수치 생성 금지

---

## Phase 11. 운영 도우미 / 데이터 품질 검사 AI

- intent: `data_quality_check`, `ops_assistant`
- 추천 / 분석 중심
- 수정은 별도 승인형 intent로 분리 (자동 수정 금지)
- 빈 시간 추천 / 치료사별 과부하 분석 등

---

## 각 Phase 공통 완료 조건

각 Phase는 다음을 모두 만족해야 다음 Phase로 진행 가능:

1. 해당 Phase의 코드 또는 문서 작업 완료
2. **Claude Code 자체 10회 검증 완료** (2026-05-04 추가수정사항 4 — 5회 → 10회 확장)
3. 자체 수정사항 문서화 완료
3-1. **10회차 자만 없는 냉정한 최종 판단** 통과 (자체 검증 결과 그대로 신뢰 금지 / 미점검 영역 적극 탐색 / 성과 과장 경계)
4. 실제 동작 확인 완료
5. `PHASE_XX_RUNTIME_TEST_REPORT.md` 작성 완료
6. 정상 케이스 확인 완료
7. 실패 / 예외 케이스 확인 완료
8. 기존 핵심 기능 회귀 확인 완료
9. Codex 독립 검증 완료
10. Codex 수정 요청사항 문서화 완료
11. Claude Code 수정 반영 / 미반영 문서화 완료
12. Codex 독립 재검증 완료
13. **Codex 최종 판단이 "통과"**
14. Codex 통과 시 다음 Phase 자동 진행 문서 (`PHASE_XX_TO_PHASE_YY_AUTO_PROCEED.md`) 작성

### 단위화 / 모듈화 완료 조건 (2026-05-03 추가수정사항, Phase 공통)

다음 6개 항목도 **모두** 만족해야 합니다.

1. 해당 Phase 의 기능이 **역할별 모듈로 분리**되어 있다 (parser / resolver / validator / preview / executor / audit / safety / harness, 또는 도메인의 service / validator / repository).
2. 기존 기능을 **우회하거나 중복 구현하지 않았다** (예약 / 환자 / 휴무 / 치료항목 / 문자 / 통계 / 완료체크).
3. 새 / 크게 수정한 파일·함수에 **역할 주석**이 작성되어 있다.
4. 해당 모듈은 **하네스 또는 테스트로 독립 검증 가능**하다.
5. 기존 기능 **회귀 테스트가 가능**하다.
6. Codex 단위화 검증 항목 (49~55) 에서 "통과"로 확인되었다.

> 단위화가 부족해 한 파일 또는 한 함수에 로직이 과도하게 몰리면 해당 Phase 는 **완료로 보지 않습니다.**

각 Phase는 `AI_PHASE_VERIFICATION_SKILL`을 통과해야 다음 Phase로 진행합니다.
**자동 진행은 Codex 최종 판단이 "통과"일 때만 가능합니다.**

---

## Phase 0 완료 조건 (현재 단계)

다음 문서가 모두 생성되어 있어야 함:

### `docs/ai/` — 핵심 설계 문서
- [x] `AI_FEATURE_MASTER_PLAN.md`
- [x] `AI_COMMAND_ARCHITECTURE.md`
- [x] `AI_SAFETY_POLICY.md`
- [x] `AI_HARNESS_PLAN.md`
- [x] `AI_IMPLEMENTATION_PHASES.md` (본 문서)
- [x] `AI_CODEX_VERIFICATION_PLAN.md`
- [x] `AI_REQUIREMENTS_OVERRIDES.md`
- [x] `AI_CURRENT_DECISIONS.md`

### `docs/ai/` — 디자인 설계 문서 (2026-05-03 추가수정사항 2)
- [x] `AI_UI_UX_DESIGN_PLAN.md`
- [x] `AI_UI_STYLE_GUIDE.md`
- [x] `AI_DESIGN_TOKENS.md`

### `docs/ai/verification/`
- [x] `AI_PHASE_VERIFICATION_SKILL.md`

### `.claude/skills/ai-phase-verification/`
- [x] `SKILL.md` (YAML frontmatter 포함)

추가 조건:
- 실제 기능 구현 없음
- 기존 코드 (`app/`, API, DB) 미수정
- 실제 UI 코드 (`app/static/css/`, `app/templates/`, JS UI) 미수정
- AI 안전 정책의 모든 금지 사항 문서화
- 환자 검색 / 차트번호 / 생년월일 / 연락처 표시 규칙 문서화
- 환자 후보 다수 시 선택 전 예약 등록 불가 규칙 문서화
- 치료항목 기반 예약 / alias / `treatment_items` 다중 입력 문서화
- 신환 등록 후 예약 흐름 / 권한 정책 문서화
- 하네스 / Patient Candidate Harness / Runtime Test Report 문서화
- 단계별 구현 계획 문서화
- Codex 검증 기준 / 통과 시 자동 진행 / 조건부 통과·실패 시 자동 진행 금지 문서화
- 요구사항 덮어쓰기 규칙 문서화
- 단위화 / 모듈화 원칙 문서화 (2026-05-03 추가수정사항 1)
- 디자인 설계 / 적용 시점 원칙 문서화 (2026-05-03 추가수정사항 2)
- 실제 작동테스트 / Runtime Test 강제 정책 문서화 (2026-05-03 추가수정사항 3)
- 1차~5차 AI intent 13개 필드 정의 (2026-05-03 보강)
