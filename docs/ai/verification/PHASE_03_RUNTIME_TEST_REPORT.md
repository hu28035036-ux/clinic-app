# PHASE_03_RUNTIME_TEST_REPORT.md

## Phase / 시각

- Phase 3 — validator + preview UI 데이터
- 시각: 2026-05-05

## 실행 환경

- Windows 11 / venv / in-memory SQLite

## 실행한 명령

```bash
venv/Scripts/python.exe -m pytest tests/test_phase03_ai_validator_preview.py -v
# 33 passed in 0.56s

venv/Scripts/python.exe -m pytest tests -q
# 1928 passed, 0 failed, 1 skipped, 10 xfailed in 15.30s

venv/Scripts/python.exe -m ruff check --fix app/ai tests/test_phase03_ai_validator_preview.py
# 1 fixable → fixed, 0 remaining
```

## 서버 / 화면

- Phase 3 는 라우터 / API / UI 없음 (validator + preview 모듈만). 서버 영향 없음.
- UI 데이터 구조 (`build_*_panel` / `build_appointment_preview`) 만 정의. 실제 UI 적용은 디자인 적용 시점 원칙에 따라 추후.

## 테스트한 기능 (33 케이스)

### Validator (14 케이스)
- 환자 / 날짜 / 시간 / 치료항목 미확정 → can_approve=False
- 치료항목 alias 충돌 / NOT_FOUND 차단
- 종일 휴무 / 오전반차 / 오후반차 충돌
- 시간 겹침 차단 / 인접 (back-to-back) 허용
- 과거 날짜 차단
- 모두 통과 시 can_approve=True

### 신환 등록 중복 검사 (5 케이스)
- 차트번호 / 이름+생년월일 / 연락처 중복 검출
- 중복 없음 + 필수값 충족 → 등록 가능
- 이름 누락 → missing_required

### Preview — 환자 후보 (4 케이스)
- 단일 후보 → patient_confirmed
- 동명이인 → patient_selection_required + 차트번호/이름/생년월일/연락처 표시 + approval_disabled=True
- 차트-이름 불일치 → patient_mismatch + approval_disabled=True
- 미존재 → patient_not_found + 신환 등록 제안

### Preview — 치료항목 (3 케이스)
- 모두 db_verified → approval_disabled=False
- needs_clarification → approval_disabled=True
- alias_conflict → approval_disabled=True

### Preview — 신환 등록 (3 케이스)
- 중복 없음 → 일반 권한 승인 가능
- 중복 있음 + 일반 권한 → needs_admin
- 중복 있음 + 관리자 권한 → 강제 가능

### Preview — 최종 예약 후보 (2 케이스)
- 환자 정보 (차트번호/이름/생년월일/연락처) + 예약 정보 + 검증 결과
- "예약 후보" 표시 / "예약 완료" 표현 미사용
- 검증 실패 시 approval_disabled=True

### 안전 (2 케이스)
- validator 호출 후 DB row 변화 0
- preview 외부 API 호출 0

## 정상 / 실패 케이스 결과

✅ 33/33 통과. 모든 실패 / 예외 케이스 안전 처리.

## 승인 전 / 후 DB 변경

- 승인 전: 0건 (Phase 3 의 validator / preview 는 read-only)
- 승인 후: 해당 없음 (Phase 3 에 approve 흐름 미존재)

## 기존 기능 회귀

✅ **1928 passed, 0 failed**

## AI API 실패 시 정상 동작

✅ Phase 3 는 외부 API 미사용 (DB select 만). API 키 / 네트워크 무관.

## 발견한 오류

1. (보완) Ruff 1 error → 자동 수정 (import 정렬).

## 최종 판단

**정상 작동** ✅
