# 19-P-5 Codex 검증 결과 (r3)

- 대상 요청서: `reports/refactor/latest_codex_review_request.md`
- 대상 산출물: `docs/refactor/19_refactor_test_strategy.md`
- 검증 시각: 2026-05-02
- 종합 판정: **pass with caveat**

## 1. 종합 판정

**pass with caveat**.

r3 요청서는 r2 Codex caveat였던 `latest_codex_review_request.md` 내부의 잔여 `9/7/4` 요약 문구를 실제로 동기화했다. `§9` 표는 `5 existing + 1 partial + 9 needed + 5 follow-up = 20` 구조로 정정되었고, `§13`의 검증 항목도 같은 기준으로 바뀌었다.

핵심 전략 문서인 `docs/refactor/19_refactor_test_strategy.md` 는 r2 시점의 정정 상태를 유지한다. 실제 테스트 파일과 다시 대조해도 appointments/leaves의 `xfail`/`skip` 상태 설명이 맞다.

남은 caveat는 이번 r3의 실패 사유가 아니라 작업 환경 caveat다.

- 워크트리에 18-0~18-8 계열로 보이는 기존 dirty/untracked 변경이 많다.
- 이번 검증은 문서/파일 구조 대조이며 pytest는 실행하지 않았다.

## 2. 게이트별 결과

### G-1 코드 무수정

판정: **pass with caveat**

`git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 결과는 기존 5개 파일 변경만 보인다.

- `app/models/models.py`
- `app/routers/ai.py`
- `app/services/ai/manual_qa.py`
- `dosu_clinic.spec`
- `tests/conftest.py`

이는 이전 18-0~18-8 계열 dirty 변경분으로 보이며, r3 요청서가 주장하는 “요청서만 정합, 코드/테스트/spec/UI 추가 수정 없음”과 충돌하는 새 증거는 없다.

### G-2 테스트 전략 정합

판정: **pass**

`docs/refactor/19_refactor_test_strategy.md` 는 실제 테스트 상태를 과장하지 않는다.

- `tests/test_appointment_rules.py`
  - 도수 중복 차단 3건: `xfail`
  - 취소 후 중복 제외 1건: `skip`
  - 점심창/PUT/DELETE/409 전용 테스트: 부재로 분류
- `tests/test_therapist_leave.py`
  - full/am/pm 휴무 차단 4건: `xfail`
  - 반대 시간대 허용 테스트: 정방향 존재

### G-3 응답 키 / URL 후방호환

판정: **pass**

전략 문서는 API contract, 응답 키 alias, `data-convert`, sync/entity key를 리팩토링 전 보호/보강 대상으로 유지한다. 구현 완료로 단정하지 않는다.

### G-4 AI/RAG local-first

판정: **pass**

AI/RAG local-first, 외부 API 차단, harness 기반 검증 기준이 유지되어 있다.

### G-5 후속 검토 분류

판정: **pass**

doctors / medical_staff, calendar, notes, health / diagnostics 등 구현 부재 또는 경계 불명확 영역은 후속 검토로 분류된다.

### G-6 doctors / medical_staff 부재 항목 단정 X

판정: **pass**

`app/models/models.py` 에서 `class Doctor`, `class Department`, `class Room`, `class DoctorSchedule`, `class Order`, `class Prescription`, `doctor_id` 검색 결과가 없었다. 요청서와 전략 문서가 이 항목들을 후속 검토로 둔 것은 실제 구조와 맞다.

### G-7 19-P-4 caveat 반영

판정: **pass**

`leave_type=am/pm/full` 백엔드 차단은 구현 완료가 아니라 분리 직전 보강 및 `xfail` 정방향 전환 대상으로 분류되어 있다.

### G-8 PyInstaller 검증 시점

판정: **pass**

PyInstaller hidden imports 단위 테스트와 실제 빌드/smoke 검증 시점을 분리해서 설명한다. read-only 문서 세션에서 실제 빌드를 요구하지 않는다.

### G-9 5회 루프 + Codex 게이트

판정: **pass**

5회 루프, rollback/재작성, Codex 게이트 기준이 문서에 유지되어 있다.

### G-10 하네스 약화 금지

판정: **pass**

`tests/conftest.py`, SDK block, `db_guard`, `check_db_path.py` 관련 보호 기준이 약화 대상이 아니라 유지 대상으로 문서화되어 있다.

## 3. 추가 발견 / 위험 / 불확실

### r2 caveat 해소 확인

이전 r2 review의 주요 caveat였던 요청서 자체의 잔여 `9/7/4` 문구는 r3에서 해소되었다.

- `§9` 표: `5 / 1 / 9 / 5` 네 분류로 정리됨
- `§13` 행: `20개 항목 — r2 정정: 5 existing + 1 partial + 9 needed + 5 follow-up` 으로 정리됨

revision history에서 r1/r2 과거 판정 설명으로 `9/7/4`가 남는 것은 정상적인 이력 기록이다.

### 기존 dirty 워크트리

워크트리에는 여전히 기존 수정/미추적 파일이 많다. 이 상태는 r3 문서 검증을 실패시키지는 않지만, 19-P-6 구현 세션에서는 변경 소유권과 diff 기준을 다시 좁혀야 한다.

### pytest 미실행

이번 검증은 요청서와 실제 파일 구조/테스트 표식 대조로 진행했다. 테스트 실행 결과를 새로 보증하지 않는다.

## 4. 19-P-6 진입 권고

**yes — 19-P-6 진입 가능.**

r3는 r2 caveat였던 요청서 요약 동기화 문제를 해결했다. 핵심 전략 문서도 실제 테스트/모델 구조와 정합하다. 다음 단계인 `docs/refactor/19_refactor_rollout_plan.md` 작성으로 넘어가도 된다.
