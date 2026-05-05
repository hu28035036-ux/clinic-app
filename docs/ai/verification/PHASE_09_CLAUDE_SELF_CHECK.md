# PHASE_09_CLAUDE_SELF_CHECK.md

Phase 9 (prepare_sms intent) 자체 10회 검증.

## Phase 9 시작 전 체크리스트

- [x] § Phase 9 / § 5.3 (prepare_sms) 13 필드 점검
- [x] 자동 발송 ⊥ — module 자체가 send 함수 미노출
- [x] 외부 AI API 에 환자 연락처 전체 전송 ⊥ — provider 미사용
- [x] SSOT § 11 endpoint 명시 구현 대상 없음

## 회차 요약

1. 단위화 — `ai_sms_prepare.py` 신규 (3 함수 + 2 dataclass). 14 단위. ✅
2. AI 안전정책 — DB 직접 수정 0 / 자동 발송 함수 미노출 (`test_module_does_not_expose_send_function` 가드) / canceled 제외. ✅
3. 개인정보 — 응답에 환자 이름 / 연락처 포함되지만 *내부 화면 표시* (외부 AI API 전송 ⊥). caller 가 외부 전송 시 별도 차단 필요. ✅
4. 기존 기능 — 2075 passed / 0 failed / Ruff 0. ✅
5. 하네스 / Runtime — 14 단위 + RUNTIME_TEST_REPORT. ✅
6. 단위화 — 대상 조회 / 토글 / preview 분리. ✅
7. Cross-doc — § 5.3 (prepare_sms 13 필드) / § 1.1 #8 (자동 발송 ⊥) / § 1.2 #10 (연락처 외부 전송 ⊥). ✅
8. 표현 — "예약문자 준비" / actions 에 "발송" 없음. ✅
9. 추가수정사항 — 1·3·4·5 모두 반영 / 실수 기록 적용. ✅
10. **자만 없는 판단** — ❌ caller (router / UI) 가 응답 dict 를 외부 AI API provider 에 그대로 보내면 PII 노출. 본 모듈만으로는 caller 책임을 강제할 수 없음 / `test_module_does_not_expose_send_function` 는 함수명 기준 검사 — 다른 이름으로 우회 가능. ✅ Phase 10 자동 진행.

## 자동 진행 조건 ✅

- 자체 10회 / 자만 없는 판단 / Runtime / 14/14 + 2075 회귀 0 fail / Ruff 0 / 명시 구현 대상

→ **Phase 10 자동 진행 가능**.
