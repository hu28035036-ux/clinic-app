# 19-P-6 Codex 검증 결과 (r2)

- 대상 요청서: `reports/refactor/latest_codex_review_request.md`
- 대상 산출물: `docs/refactor/19_refactor_rollout_plan.md`
- 검증 시각: 2026-05-02
- 종합 판정: **pass with caveat**

## 1. 종합 판정

**pass with caveat**.

19-P-6 r2는 r1 Codex caveat 2개를 실제로 정정했다.

- "추천 순서 14단계" 표현은 `19-1~19-14`의 14개 리팩토링 세션 + `19-0` baseline = 15개 실행 세션으로 분해되어 설명된다.
- `docs/refactor/19_refactor_rollout_plan.md` §0의 19-P-5 r3 판정 링크는 덮어쓰기 파일 `latest_codex_review.md`가 아니라 영구본 `19-P-5_codex_review.md`를 가리킨다.

revision history에 남은 과거 "14단계" / `latest_codex_review.md` 문구는 r1 이력 설명이므로 결함으로 보지 않는다.

남은 caveat는 작업 환경 caveat다. 워크트리는 여전히 기존 dirty/untracked 변경을 포함하고 있고, 이번 검증에서는 pytest를 실행하지 않았다.

## 2. 게이트별 결과

### G-1 코드 무수정

판정: **pass with caveat**

`git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 결과는 기존 5개 tracked 변경만 보인다.

- `app/models/models.py`
- `app/routers/ai.py`
- `app/services/ai/manual_qa.py`
- `dosu_clinic.spec`
- `tests/conftest.py`

이번 r2 보정이 app/tests/spec/UI/requirements를 새로 수정했다는 증거는 없다. 다만 워크트리 dirty 상태는 계속 별도 caveat다.

### G-2 리팩토링 순서 정합

판정: **pass**

단계 수 표현은 r2에서 정정되었다.

- `§2-1`은 `19-P` 구조 계획, `19-0` baseline, `19-1~19-14` 14개 실제 리팩토링 세션을 분리한다.
- `§2-1` 표 합계는 16행으로 명시된다.
- 실행 세션 수는 `19-0~19-14` 15개로 명시된다.
- `§10` 종합도 같은 기준으로 정정되었다.
- 요청서 `§2`, `§8`, `§12`, `§15`도 15개 실행 세션 기준으로 동기화되어 있다.

appointments는 19-9로 여전히 후반부에 배치되며, availability/leaves/treatments/patients/staff가 선행된다.

### G-3 세션별 계획 12 컬럼

판정: **pass**

`§3-0` ~ `§3-14`까지 15개 세션 표가 존재한다. 각 표는 세션 번호 / 이름 / 목표 / 수정 가능 / 금지 / 선행 조건 / 테스트 / 응답 키 / 위험도 / rollback / Codex / 주석 항목을 포함한다.

### G-4 응답 키 / URL 후방호환

판정: **pass**

R-4, 세션별 응답 key 행, RB-1에서 기존 API URL과 응답 키 보존 원칙을 유지한다.

### G-5 AI/RAG local-first

판정: **pass**

R-12, 19-13, RB-8에서 local-only 외부 호출 0, `_block_sdk_modules`, AI/RAG의 도메인 DB 임의 생성 금지를 유지한다.

### G-6 doctors / medical_staff 부재 단정 X

판정: **pass**

doctors / `Patient.doctor_id` / `Department` / `Room` / `DoctorSchedule` / `Order` / `Prescription` 등은 후속 검토로 남아 있다.

### G-7 19-P-4 caveat 반영

판정: **pass**

`leave_type=am/pm/full` 백엔드 차단은 19-4/19-5에서 보강 및 정방향 전환 대상으로 명시되어 있다.

### G-8 PyInstaller 검증 시점

판정: **pass**

hidden imports 테스트와 실제 PyInstaller 빌드/smoke 검증 시점이 분리되어 있다. 실제 빌드는 사용자 승인 시점으로 둔다.

### G-9 5회 루프 + Codex 게이트

판정: **pass**

R-9/R-10, §7 rollback 절차, §8 Codex 운영 방식이 유지되어 있다.

### G-10 하네스 약화 금지

판정: **pass**

R-11/R-12와 §5가 `db_guard`, `_block_sdk_modules`, `check_db_path.py`, harness 재확인을 유지한다.

### G-11 후속 검토 단정 X

판정: **pass**

§9 F-1~F-15는 후속 검토 항목을 현재 구현으로 단정하지 않는다.

### G-12 워크트리 dirty 정리 게이트

판정: **pass**

19-0 통과 기준에 dirty/untracked 정리 또는 commit 완료가 포함되어 있다. 19-P-5 r3 caveat가 롤아웃 계획에 반영되어 있다.

## 3. 추가 발견 / 위험 / 불확실

1. **r1 caveat 해소 확인**

두 r1 caveat는 r2 본문 기준으로 해소되었다. 과거 이력 표에 남은 문구는 historical record라 문제로 보지 않는다.

2. **dirty 워크트리**

기존 dirty/untracked 변경이 많다. r2 보정의 실패 사유는 아니지만 19-0에서 반드시 정리/commit 기준을 좁혀야 한다.

3. **pytest 미실행**

이번 검증은 문서와 실제 파일 구조/문구/diff 범위 대조로 진행했다. 테스트 실행 결과를 새로 보증하지 않는다.

## 4. 19-P-7 진입 권고

**yes — 19-P-7 진입 가능.**

r2는 r1에서 남긴 단계 수 표현과 시간 의존 링크 caveat를 정리했다. 다음 단계인 `docs/refactor/19_refactor_risk_register.md` 작성으로 넘어가도 된다.
