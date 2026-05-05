# PHASE_07_RUNTIME_TEST_REPORT.md

## Phase / 시각

- Phase 7 — update_appointment / cancel_appointment intent
- 시각: 2026-05-05

## 명령

```bash
venv/Scripts/python.exe -m pytest tests/test_phase07_ai_update_cancel.py -v   # 26/26
venv/Scripts/python.exe -m pytest tests -q                                     # 2034 passed, 0 failed
venv/Scripts/python.exe -m ruff check app tests                                # 0 error
```

## 테스트 (26 케이스)

### 1) 대상 예약 식별 (4)

- 환자 + 날짜 + 시간 → 단일 Appointment 확정
- canceled 예약 자동 제외 (시간 명시 시 not_found)
- 시간 누락 시 같은 날 환자 예약 모두 candidates
- 환자 누락 → not_found

### 2) 변경 전·후 비교 (4)

- 시간 변경 → start_time changed_field
- 치료사 변경 → therapist_id changed_field
- 변경 사항 0 → empty changed_fields
- 치료항목 변경 → treatment_codes changed_field

### 3) update validator (3)

- 자기 자신 시간 충돌 회피 (exclude_appointment_id)
- 다른 환자 예약과의 시간 겹침 차단
- 변경 후 날짜의 치료사 휴무 차단

### 4) update executor (4)

- 정상 service 호출 + 인자 정합
- 변경 사항 없음 → service 호출 0
- 변경 후 충돌 → service 호출 0
- service 예외 → ExecutionResult.success=False

### 5) cancel validator (3)

- 정상 취소 가능
- 이미 취소된 예약 → 차단
- target=None → 차단

### 6) cancel executor (4)

- 정상 service 호출 + reason 전달
- 물리 삭제 0 (DB row 수 동일)
- 이미 취소된 예약 → service 호출 0
- service 예외 → ExecutionResult.success=False

### 7) preview (2)

- update preview — 변경 후보 카드 + diff + validation
- cancel preview — 취소 후보 카드 + reason

### 8) 안전 (2)

- resolver 호출 후 DB row 변화 0
- executor 호출 후 DB row 변화 0

## 결과

✅ 26/26 통과
✅ 2034 passed / 0 failed (Phase 6 까지 1994 + ai_safety 14 + Phase 7 26)
✅ Ruff 0 error
✅ DB 직접 수정 0 / 외부 API 호출 0 / 물리 삭제 0
✅ Gate 1 + Gate 2 모두 입증 (자기 자신 exclude / 다른 환자 충돌 차단 / 휴무 차단)

## 발견 / 수정

| # | 항목 | 처리 |
|---|---|---|
| 1 | resolve_target_appointment 가 시간 명시 시 미매칭이면 자동으로 같은 날 다른 시간 예약을 fallback 으로 자동 확정 | 수정 — 시간 명시 시 정확 매칭 실패는 not_found 반환 (자동 fallback 금지). AI 임의 확정 정책 정합 |
| 2 | Ruff 5 (import 정렬) | 자동 수정 |

## 최종 판단

**정상 작동** ✅

- 변경 / 취소 intent 모듈이 read-only resolver + validator + executor + preview 로 분리
- 의존성 역전 (Update / Cancel ServiceCallable Protocol) — 직접 SQL ⊥
- 물리 삭제 금지 정책 — service callable 만 호출 (DELETE 시도 ⊥)
- AI 임의 확정 금지 — resolve_target_appointment 의 시간 명시 시 fallback 차단

## 남은 위험 (자만 없는 인정)

1. **실제 service 시그니처 정합 미검증** — Protocol 만 정의, `app.modules.appointments.service` 의 실제 시그니처 매핑은 router 통합 시
2. **Audit 통합 미수행** — Phase 5 의 `finalize_audit` 패턴 재사용 가능하나 Phase 7 범위 외 (caller 책임)
3. **Parser 의 변경 사항 추출 미구현** — "10시로 변경" 같은 변경 항목 자체 추출은 미구현. caller 가 변경 인자 명시 필요
4. **Cancel reason 추출 미구현** — 자연어에서 reason 추출은 caller 책임
5. **Router endpoint 미구현** — Phase 7 명시 구현 대상이 아니므로 추가 안 함 (실수 #001 재발 방지)
