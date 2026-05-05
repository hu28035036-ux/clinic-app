# PHASE_02_TO_PHASE_03_AUTO_PROCEED.md

## 이전 / 다음
- 이전: Phase 2 — `create_appointment` 파서 + resolver
- 다음: **Phase 3 — validator + preview UI**

## 자동 진행 근거 (추가수정사항 5)

| 조건 | 상태 |
|---|---|
| Claude Code 자체 10회 검증 (`PHASE_02_CLAUDE_SELF_CHECK.md`) | ✅ |
| 10회차 자만 없는 판단 통과 | ✅ |
| `PHASE_02_RUNTIME_TEST_REPORT.md` 작성 | ✅ |
| 실제 작동테스트 (49/49 + 1895 회귀) | ✅ |
| 진행 금지 조건 (§ 6.1~6.5) 없음 | ✅ |
| 사용자 중단 / 대기 미명시 | ✅ |
| Codex 검증 | ⚠️ 생략 (사용자 추가수정사항 5) |

## 남은 위험 인정

1. 정규식 기반 parser 는 사용자 spec 의 명시 케이스만 검증. 실 provider 호출 미검증.
2. Phase 3 의 validator 가 필수값 누락 / 휴무 충돌 / 시간 겹침을 잡음 — Phase 2 만으로는 incomplete.
3. `treatment_aliases` 시드 데이터 미존재 (사용자 운영 환경에서 등록 필요).

## Phase 3 시작 시간 / 범위

- 시작: 2026-05-04
- 범위 (`AI_IMPLEMENTATION_PHASES.md § Phase 3`):
  - `app/ai/ai_validator.py` 신규 (휴무 / 반차 / 중복 / 시간겹침 / 권한)
  - `app/ai/ai_preview.py` 신규 (사용자 승인 화면 데이터)
  - 환자 후보 선택 / 치료항목 선택 UI 데이터 구조 (실제 UI 는 적용 미시작 — 디자인 적용 시점 원칙)
  - 신환 등록 제안 UI (실제 등록은 Phase 4)
  - **승인 전 저장 금지 보장**
  - Validator Harness, Patient Candidate Harness

## Phase 3 종료 후 자동 진행 규칙

- 자체 10회 검증 + Runtime Test + 자만 없는 판단 통과 시 → Phase 4 자동 진행.
- 진행 금지 조건 발생 시 자동 진행 중단.
