# PHASE_04_RUNTIME_TEST_REPORT.md

## Phase / 시각
- Phase 4 — 신환 등록 연계 흐름
- 시각: 2026-05-05

## 실행 환경 / 명령

```bash
venv/Scripts/python.exe -m pytest tests/test_phase04_ai_new_patient_flow.py -v
# 16 passed in 0.20s

venv/Scripts/python.exe -m pytest tests -q
# 1944 passed, 0 failed, 1 skipped, 10 xfailed in 14.99s

venv/Scripts/python.exe -m ruff check --fix
# 1 fixable → fixed
```

## 테스트 (16 케이스)

### 검색 실패 → 신환 제안 (2)
- not_found 시 prefill 제공 (차트번호/이름만, 생년월일/연락처는 None — AI 추측 금지)
- 후보 있으면 None 반환

### 권한 정책 (4)
- 중복 없음 + 일반 직원 → OK
- 중복 있음 + 일반 직원 → 차단 (관리자 필요)
- 중복 있음 + 관리자 → 강제 가능
- 필수값 누락 → 모든 권한 차단

### 입력 평가 (4)
- 중복 없음 + 일반 직원 → can_approve=True
- 차트번호 중복 + 일반 직원 → needs_admin=True
- 차트번호 중복 + 관리자 → 강제 가능
- 이름 누락 → blocks

### 별도 로그 (2)
- 신환 등록 + 예약 등록 별도 row + cross-reference (new_patient_log_id)
- 중복 카운트 정확 기록

### 재검증 트리거 (2)
- APPOINTMENT_NEEDS_REVALIDATION 상태 / 컨텍스트 구조

### 안전 (2)
- DB 직접 수정 0 / 외부 API 호출 0

## 정상 / 실패 / 회귀 / API 실패

✅ 16/16 통과 / 1944 회귀 0 fail / 외부 API 미사용 / 자동 저장 0건.

## 발견 / 수정

- Ruff 1 → 자동 수정.

## 최종 판단

**정상 작동** ✅
