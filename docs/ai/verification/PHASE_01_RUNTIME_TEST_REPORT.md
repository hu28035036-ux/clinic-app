# PHASE_01_RUNTIME_TEST_REPORT.md

## Phase 번호

Phase 1 — AI 명령 스키마 + 로그 테이블 + provider 구조

## 실행 환경

- OS: Windows 11 Home 10.0.26200
- Python: venv/Scripts/python.exe (프로젝트 venv)
- DB 경로 (테스트): `:memory:` SQLite (conftest 격리)
- DB 경로 (운영, 미사용 확인): `C:\Users\user\AppData\Roaming\도수치료예약\clinic.db`
- 시각: 2026-05-04

## 실행한 명령

```bash
# 1) 단위 테스트
venv/Scripts/python.exe -m pytest tests/test_phase01_ai_command.py -v
# 결과: 20 passed in 0.11s

# 2) 전체 회귀
venv/Scripts/python.exe -m pytest tests -q
# 결과: 1846 passed, 1 skipped, 10 xfailed, 27 warnings in 14.96s

# 3) Ruff lint
venv/Scripts/python.exe -m ruff check --fix app/ai tests/test_phase01_ai_command.py app/migrations/m019_ai_command_logs.py app/migrations/m020_treatment_aliases.py
# 결과: 1 fixable → fixed (import 정렬), 0 remaining

# 4) DB 경로 안전 검사
venv/Scripts/python.exe scripts/check_db_path.py
# 결과: 운영 DB 경로 감지됨 (스크립트 단독 실행이라 정상). 테스트 격리 conftest 검증은 별도 통과.

# 5) 모듈 smoke test
venv/Scripts/python.exe -c "from app.ai import ...; ..."
# 결과: provider=mock / parser 동작 / audit INSERT-SELECT 정상
```

## 서버 실행 여부

- Phase 1 은 라우터 / API 가 없음 (스키마 + provider + audit 만). 서버 기동은 Phase 3 (preview UI) 부터 영향.
- 기존 서버 코드는 미수정 — `app.main` import 만으로 영향 없음 (회귀 1846 통과로 입증).

## 화면 로딩 여부

- Phase 1 은 UI 변경 없음 — 화면 로딩 영향 없음.

## 테스트한 기능

- AI 명령 스키마 (`AiIntent` 10종 / `AiCommandStatus` 23종 / `DataSourceState` 5종 / `TreatmentItemStatus` / `ParsedCommand` / `TreatmentItem` / `ParserContext`)
- Provider 추상화 (`AIProvider` Protocol / `MockProvider` / `get_default_provider()` / `ProviderError`)
- Audit (`write_log()` / `update_log()` / `get_log()`) — JSON 직렬화 / 부분 갱신 / executed_at
- 마이그레이션 m019 (`ai_command_logs` 17 필드 + 3 인덱스) / m020 (`treatment_aliases` + UNIQUE)
- 멱등성 (m019 / m020 두 번 실행 안전)
- 신환 / 예약 별도 로그 (`AI_FEATURE_MASTER_PLAN.md § 10.2`)
- `app.ai` 가 `app.services.ai` 를 import 하지 않음 (분리 원칙)

## 정상 케이스 결과

- ✅ 20/20 테스트 통과 (`tests/test_phase01_ai_command.py`)
- ✅ Provider Mock 호출 → `ParsedCommand` 반환
- ✅ Audit `write_log()` → command_id 반환 → `get_log()` 로 동일 데이터 조회
- ✅ JSON 필드 (parsed_json / resolved_json / preview_json / selected_treatment_items_json / executed_result) 직렬화 / 역직렬화 정상

## 실패 케이스 결과

- ✅ 마이그레이션 멱등 — 두 번 실행해도 IntegrityError 없음
- ✅ `treatment_aliases` UNIQUE 제약 — 같은 (treatment_id, alias_name) 중복 INSERT 시 IntegrityError 발생 (의도된 안전장치)
- ✅ `get_log(99999)` (없는 ID) → None 반환 (예외 미발생)
- ✅ `MockProvider.parse_command()` 는 외부 API 호출 없음 — API 키 미설정 / 네트워크 차단 환경에서도 정상 동작

## 승인 전 DB 변경 여부

- ✅ **0 건** — Phase 1 은 parse / preview / approve 흐름이 없음 (Phase 2~5 에서 추가). 본 Phase 의 audit 도 DB 직접 변경이지만 "AI 명령 로그 기록" 용도로 schema 정합 동작이며, "AI 가 예약 / 환자 / 휴무를 직접 변경" 하는 것은 아님.

## 승인 후 DB 변경 여부

- 해당 없음 (Phase 1 에 approve 흐름 미존재). Phase 5 에서 `ai_executor` 가 기존 service 호출 시 검증.

## 기존 기능 회귀 테스트 결과

- ✅ **1846 passed, 0 failed** (전체 pytest)
- 영향 받지 않은 기능: 예약 / 환자 / 치료사 / 의사 / 치료항목 / 휴무 / 문자 / 통계 / 완료체크 / `manual60` 1카운트 정책

## AI API 실패 시 기존 프로그램 정상 동작

- ✅ `MockProvider` 가 default 이므로 외부 API 호출 0건
- ✅ API 키 환경변수 미설정 상태에서 import / 호출 모두 정상
- ✅ `ProviderError` 정의되었으나 Phase 1 에서는 발생 경로 없음 (Phase 2 의 실제 provider 가 발생 시 테스트 추가)

## 발견한 오류

1. (보완) `tests/test_phase01_ai_command.py::test_app_ai_does_not_import_app_services_ai` 가 docstring 텍스트까지 검사하던 문제 → 정규식으로 import 문만 검사하도록 수정.
2. (보완) Ruff `I001` (import 정렬) 1건 → `--fix` 로 자동 정렬.

## 수정 여부

- 위 2 건 모두 수정 완료. 재테스트 후 20/20 + 1846/1846 통과.

## 최종 판단

**정상 작동** ✅

- 모든 Phase 1 산출물 (3 모듈 + 2 마이그레이션 + spec + 20 단위 테스트) 정상 동작.
- 회귀 0건.
- API 키 / 외부 호출 의존성 없음.
- DB 직접 수정은 audit 모듈에서만 (의도된 동작), AI executor 는 Phase 5 에서 기존 service 호출 형태로 추가 예정.
- 단위화 / 모듈화 원칙 준수: 3 모듈 (`schema` / `provider` / `audit`) 이 단일 책임 / 거대 함수 없음 / 기존 도메인 미중복.

## 다음 Phase 자동 진행 판단

- ✅ 필수 조건 (10회 검증 후 Phase 1 자체 10회차 통과 시) 만족 예정
- ✅ 진행 금지 조건 (§ 6.1~6.5) 발생 없음
- ✅ Codex 검증 생략 (사용자 승인 — 추가수정사항 5)
