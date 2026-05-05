# PHASE_08_RUNTIME_TEST_REPORT.md

## Phase / 시각

- Phase 8 — create_leave intent (휴무 / 반차 등록 AI)
- 시각: 2026-05-05

## 명령

```bash
venv/Scripts/python.exe -m pytest tests/test_phase08_ai_leave.py -v   # 27/27
venv/Scripts/python.exe -m pytest tests -q                              # 2061 passed
venv/Scripts/python.exe -m ruff check app tests                         # 0 error
```

## 테스트 (27 케이스)

- 휴무 유형 추출 6 (parametrize: full / am / pm / 연차 / 오프 / 미매칭)
- 검증 (필수값 / 비활성 / 미존재 치료사) 5
- 검증 (중복 휴무 / 다른 날짜) 2
- 검증 (충돌 예약 안내: full / am / pm / canceled 제외 / strict 모드) 5
- 검증 (과거 날짜 / 정상) 2
- 실행 (정상 / 비활성 차단 / 중복 차단 / 예외) 4
- preview (정상 / 충돌 포함) 2
- 안전 (DB 직접 수정 0) 1

## 결과

✅ 27/27 통과
✅ 2061 passed / 0 failed (Phase 7 까지 2034 + Phase 8 27)
✅ Ruff 0 error
✅ DB 직접 수정 0 / 외부 API 호출 0

## 발견 / 수정

- Ruff 1 (import 정렬) — 자동 수정.

## 최종 판단

**정상 작동** ✅

- create_leave 모듈이 read-only validator + service callable 패턴
- 충돌 예약은 warning 안내 (§ 5.3 "별도 고지") — 차단 ⊥, strict 모드도 옵션 제공
- canceled 예약은 충돌 후보에서 자동 제외
- 비활성 치료사 / 미존재 치료사 차단

## 남은 위험

1. parser 의 leave_type 추출은 본 모듈 helper (`parse_leave_type_from_text`) — Phase 2 parser 통합 미수행
2. 실제 휴무 service 시그니처 정합 미검증 (`app.modules.leaves.service`)
3. Audit 통합은 caller 책임 유지
4. Router endpoint 미구현 (Phase 8 명시 구현 대상 아님)
