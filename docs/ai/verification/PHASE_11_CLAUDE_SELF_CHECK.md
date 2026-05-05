# PHASE_11_CLAUDE_SELF_CHECK.md

Phase 11 (data_quality_check / ops_assistant) 자체 10회 검증.

## 시작 전 체크리스트

- [x] § Phase 11 / § 5.5 — 13 필드 (2 intent)
- [x] 자동 수정 ⊥ / 자동 예약 ⊥ / 자동 휴무 ⊥
- [x] 환자 목록 외부 AI API 전송 ⊥

## 회차 요약

1. 단위화 — `ai_ops.py` (4 quality check + 2 ops + 3 preview). 20 단위. ✅
2. 안전정책 — DB 직접 수정 0 / 자동 수정 함수 미노출 (`test_module_does_not_expose_auto_modify_functions`) / canceled 제외 / 비활성 치료사 제외. ✅
3. 개인정보 — 환자 정보 *내부 표시용* (외부 AI API 전송 ⊥ / caller 책임). ✅
4. 기존 기능 — 2114 passed / 0 failed / Ruff 0. ✅
5. 하네스 / Runtime — 20 단위 + Runtime Test Report. ✅
6. 단위화 — 검사 종류별 함수 분리 / preview 별도. ✅
7. Cross-doc — § 5.5 (2 intent 13 필드) / § 5.5 결정 ("5차 기능 공통: 모두 read-only + 추천. 수정은 별도 승인형 intent"). ✅
8. 표현 — actions 에 "자동 수정" / "자동 예약" 없음. preview read_only=True. ✅
9. 추가수정사항 + 실수 기록 적용. ✅
10. **자만 없는 판단** — ❌ 자동 수정 함수 미노출 가드는 함수명 기준 (다른 이름으로 우회 가능) / 환자 목록을 caller 가 외부 AI 로 보내면 PII 노출 — caller 책임 / find_empty_slots 의 hour_range 가 점심 시간 / 영업 시간 미고려 (기존 `_lunch_window` 와 통합 안 함). ✅

→ **Phase 11 완료. Phase 1~11 1차 진행 완료. 재검증 루프 시작 가능.**
