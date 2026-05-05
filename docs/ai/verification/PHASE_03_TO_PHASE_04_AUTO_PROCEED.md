# PHASE_03_TO_PHASE_04_AUTO_PROCEED.md

## 이전 / 다음
- 이전: Phase 3 — validator + preview UI 데이터
- 다음: **Phase 4 — 신환 등록 연계 흐름**

## 자동 진행 조건 충족

- 자체 10회 검증 (`PHASE_03_CLAUDE_SELF_CHECK.md`) ✅
- 10회차 자만 없는 판단 통과 ✅
- Runtime Test Report ✅
- 33/33 + 1928 회귀 0 fail ✅
- 진행 금지 조건 없음 ✅
- Codex 검증 생략 (추가수정사항 5)

## 남은 위험

1. validator 가 권한 검사 안 함 — Phase 5 의 router 에서 require_admin 강제
2. 시간 겹침 검사가 같은 치료사 만 — 자원 / 환자 중복은 Phase 7 (update_appointment) 에서 보강
3. preview 데이터 구조는 dict — Pydantic schema 는 Phase 5 의 router 에서 정의

## Phase 4 시작 / 범위

- 시작: 2026-05-05
- 범위 (`AI_IMPLEMENTATION_PHASES.md § Phase 4`):
  - 신환 등록 흐름 통합 (validator 의 `check_new_patient_duplicates` + preview 의 `build_new_patient_proposal` 을 연계)
  - 신환 등록 / 예약 등록 각각 별도 로그 (`ai_audit.write_log` 두 번 호출)
  - 권한 정책 적용 (일반 직원 / 관리자)
  - 신환 흐름 통합 테스트 (parser → resolver → validator → preview 흐름)
  - 신환 등록 후 예약 후보 재검증

## Phase 4 종료 후 자동 진행 규칙

- 자체 10회 검증 + Runtime Test + 자만 없는 판단 통과 시 → Phase 5 자동 진행
