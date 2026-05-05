# PHASE_02_RUNTIME_TEST_REPORT.md

## Phase 번호 / 시각

- Phase 2 — `create_appointment` 파서 + resolver
- 시각: 2026-05-04

## 실행 환경

- OS: Windows 11
- Python: venv/Scripts/python.exe
- DB: in-memory SQLite (테스트), 운영 DB 미사용

## 실행한 명령

```bash
venv/Scripts/python.exe -m pytest tests/test_phase02_ai_parser_resolver.py -v
# 49 passed in 0.44s

venv/Scripts/python.exe -m pytest tests -q
# 1895 passed, 0 failed, 1 skipped, 10 xfailed in 15.00s

venv/Scripts/python.exe -m ruff check --fix app/ai tests/test_phase02_ai_parser_resolver.py
# 5 fixable → fixed (import 정렬 / 사용 안 하는 import 제거), 0 remaining
```

## 서버 실행 / 화면 로딩

- Phase 2 는 라우터 / API / UI 없음 (parser + resolver 만). 서버 영향 없음.

## 테스트한 기능

### Parser (24 케이스)
- intent: create_appointment / update_appointment / cancel_appointment / create_leave
- 차트번호: "차트번호 12345" / "12345번 환자"
- 날짜: 오늘 / 내일 / 4월30일 / 30일 (월 누락) / 다음주 월요일
- 시간: 9시 / 오전 10시 / 오후 2시 / 14:30
- 치료사명: 박치료사 (1글자 성)
- 치료항목: 단일 (도수30) / 다중 약어 (도수30 주 충) / ESWT
- 환자명: 박환자
- 메모: "메모: 통증 심함"
- Provider 실패 시 정규식 fallback

### Resolver — 환자 (5 케이스)
- 차트번호 일치 → match_rank=1
- 동명이인 박환자 2명 → 후보 2개 (차트번호/이름/생년월일/연락처 표시)
- 차트번호 + 이름 불일치 → mismatch=True
- 차트번호 + 이름 일치 → match_rank=2
- 미존재 → not_found=True

### Resolver — 치료사 (2 케이스)
- 정확 일치
- 미존재

### Resolver — 치료항목 (5 케이스)
- 단일 alias (도수30 → 도수치료 30분)
- 다중 alias (도수30 주 충 → 3개 매칭)
- ESWT
- 미존재 → NOT_FOUND
- alias 충돌 (동일 alias 가 여러 treatment_id) → ALIAS_CONFLICT

### Resolver — 날짜 (8 케이스)
- 오늘 / 내일
- M월 D일
- D일 (현재 캘린더 월 기준)
- 다음주 월요일 / 이번주 금요일
- 과거 날짜 → is_past=True
- 모호 → is_ambiguous=True

### Resolver — 시간 (5 케이스)
- 9시 / 오전 10시 / 오후 2시 / 14:30 / 9시 30분

## 정상 케이스 결과

✅ 49/49 통과

## 실패 케이스 결과

✅ 모든 실패 / 예외 케이스 안전 처리:
- ProviderError 발생 시 정규식 fallback
- 환자 미존재 → not_found=True (예외 미발생)
- 치료항목 미존재 → NOT_FOUND status
- alias 충돌 → ALIAS_CONFLICT status, candidates list 반환
- 날짜 모호 → is_ambiguous=True

## 승인 전 DB 변경 여부

✅ **0 건** — Phase 2 의 resolver 는 read-only.
- `test_resolver_does_not_modify_db` 가 입증: resolver 호출 후 DB row 개수 변화 0.

## 승인 후 DB 변경 여부

해당 없음 (Phase 2 에 approve 흐름 미존재).

## 기존 기능 회귀 테스트 결과

✅ **1895 passed, 0 failed** — 영향 없음.

## AI API 실패 시 기존 프로그램 정상 동작

✅ Phase 2 의 parser 는 정규식 fallback 으로 동작.
- `test_parser_provider_failure_fallback`: ProviderError 던져도 정규식이 모든 9 필드 추출.
- `test_parser_no_external_api_call_in_phase2`: provider 없이도 정규식만으로 정상 동작.

## 발견한 오류

1. (보완) `_extract_date_text` 의 lookahead `(?!\s*\d)` 가 "30일 9시" 매칭 실패 → `(?!요)` 로 변경 (요일 충돌 방지만 유지).
2. (보완) `_extract_therapist_name` 이 `[가-힣]{2,4}` 으로 1글자 성 (박, 김 등) 매칭 실패 → `{1,4}` 로 변경.
3. (보완) `_extract_patient_name` 의 치료사 제거 정규식도 `{1,4}` 로 통일.
4. (보완) Ruff 5 error → 자동 수정 (import 정렬 / 사용 안 하는 import 제거).

## 수정 여부

- 위 4건 모두 수정 완료. 재테스트 후 49/49 통과.

## 최종 판단

**정상 작동** ✅

- Phase 2 의 모든 산출물 (parser + resolver + 49 단위 테스트) 정상 동작.
- 회귀 0건 (1895 passed).
- API 키 / 외부 호출 의존성 없음 (Mock + 정규식 fallback).
- DB 직접 수정 0건 (resolver read-only).
- 단위화 / 모듈화 원칙 준수: parser / resolver 가 단일 책임. resolve_patient / resolve_therapist / resolve_treatment_items / resolve_date / resolve_time 함수 단위 분리.

## Phase 3 자동 진행 가능 여부

✅ 자동 진행 조건 만족 (자체 10회 검증 별도 문서 참조).
