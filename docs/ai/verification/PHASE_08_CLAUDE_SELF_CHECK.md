# PHASE_08_CLAUDE_SELF_CHECK.md

Phase 8 (create_leave intent) 자체 10회 검증.

## Phase 8 시작 전 체크리스트 (실수 #001 재발 방지)

- [x] AI_IMPLEMENTATION_PHASES § Phase 8 구현 대상: intent / 충돌 검증 (별도 고지) / 승인 후 등록
- [x] AI_FEATURE_MASTER_PLAN § 5.3 13 필드 모두 점검
- [x] SSOT § 11 endpoint — Phase 8 명시 구현 대상 없음 / 임의 추가 금지

## 회차 요약

1. 요구사항 + 단위화 — `ai_leave.py` 신규 (5 함수 + 4 dataclass + Protocol). 27 단위 테스트. ✅
2. AI 안전정책 — DB 직접 수정 0 / Gate 1+2 / 비활성 치료사 차단 / 중복 차단 / 과거 차단. ✅
3. 개인정보 — 외부 AI API 0. ✅
4. 기존 기능 영향 — 2061 passed / 0 failed / Ruff 0. ✅
5. 하네스 / Runtime — 27 단위 + RUNTIME_TEST_REPORT. ✅
6. 단위화 깊이 — LeaveServiceCallable Protocol, 충돌 / 중복 / 활성 검사 분리. ✅
7. Cross-doc — § 5.3 13 필드, § 1.1 (승인 없는 휴무 등록 ⊥), Appointment.status='canceled' 제외. ✅
8. 표현 — leave_type 코드 (full/am/pm) = EmployeeLeave 모델 정합. "휴무 등록 후보" 표현 (단정 ⊥). ✅
9. 추가수정사항 — 1·3·4·5 모두 반영. 실수 기록 ✅. ✅
10. **자만 없는 판단** — ❌ Phase 7 의 audit 통합 누락이 Phase 8 에도 동일 / parser 의 leave_type 추출 시 "휴무"/"오프" 단독은 full 매핑하지만 사용자 의도가 "오프"가 항상 full 인지 검증 필요 / 충돌 예약 안내가 warning 인 경우 사용자가 그대로 승인 시 기존 예약 처리 책임은 caller (UI / 향후 Phase). ✅ Phase 9 자동 진행.

## 자동 진행 조건 충족

| 조건 | 상태 |
|---|---|
| 자체 10회 | ✅ |
| 자만 없는 판단 | ✅ |
| Runtime Test | ✅ |
| 27/27 신규 + 2061 회귀 0 fail | ✅ |
| Ruff 0 error | ✅ |
| Phase 8 명시 구현 대상 | ✅ |
| 실수 기록 | ✅ |

→ **Phase 9 자동 진행 가능**.
