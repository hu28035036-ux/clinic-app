# 19-P-4 Codex 검증 결과 (r2)

## 1. 종합 판정

pass with caveat

`reports/refactor/latest_codex_review_request.md`가 19-P-4 r2 보정본으로 갱신되어 있어, `docs/refactor/19_refactor_dependency_map.md` r2를 실제 파일 구조와 다시 대조했다.

r1에서 지적한 핵심 부정확 항목 중 `문서 2개 → 3개`와 PII 경로(`현재: app/services/ai/pii.py / 목표 후속: modules/ai/safety/pii.py`)는 실제로 보정되었다. 의존성 방향, 금지 의존성, doctors/medical_staff 후속 분류, AI/RAG local-first 원칙도 실제 코드 구조와 대체로 정합하다.

다만 현재 작업트리는 여전히 18-0~18-8 변경분이 dirty/untracked 상태이고, r2 요청서의 줄 수 620은 현재 PowerShell 실측 622와 맞지 않는다. 또한 availability의 `am`/`pm` 반차 차단은 실제 예약 생성/수정 코드에서 명확한 백엔드 차단 로직으로 확인되지 않아, 문서의 "현재 인라인" 표현은 계속 caveat로 둔다.

## 2. 게이트별 결과

- G-1 코드 무수정: pass with caveat
  - `HEAD`는 baseline과 같은 `bcd74a7aabc9de8d735425863254cfc393bda580`.
  - `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml`는 기존 18-0~18-8 범위로 보이는 tracked 변경 5개만 표시한다: `app/models/models.py`, `app/routers/ai.py`, `app/services/ai/manual_qa.py`, `dosu_clinic.spec`, `tests/conftest.py`.
  - `git status`에는 m012/m013, AI RAG/knowledge/vector, harness/test 파일 등 untracked 변경이 다수 남아 있다. r2 자체가 코드 변경을 추가했다는 증거는 발견하지 못했지만, Git만으로 세션 경계를 완전 분리 증명할 수는 없다.
  - `reports/refactor/19-P-4_codex_review_request.md`와 `reports/refactor/latest_codex_review_request.md`는 동일 내용이다.

- G-2 의존성 정합: pass
  - dependency map은 D-1~D-13, 16개 주요 의존성 그룹, 50행 이상 의존성 분류표, F-1~F-9, 순환 위험, 분리 순서, 주석 후보를 포함한다.
  - 실제 symbol 확인 결과 `_upsert_employee_leave_core`, `_check_version`, `_bump_version`, `_bump_patient_count`, `_doctor_codes_set`, `is_doctor_filter`가 문서 설명과 맞다.
  - 실제 endpoint 수는 `/api` 86개, `/api/ai` 13개로 기존 19-P 문서와 맞다.

- G-3 응답 키 / URL 후방호환: pass
  - §3 분류표와 §7-A가 manual_qa wrapper, therapist/employee alias, AI 33+ 응답 키, `ENTITY_MAP`, `treatment-meta` 키를 COMPAT 지점으로 둔다.
  - 실제 `app/routers/ai.py`는 `/api/ai/status` 조립을 `ai_health.build_admin_status()`에 위임하고, API key는 boolean으로만 노출한다.

- G-4 AI/RAG local-first: pass
  - D-6, §2-K, §4 F-5, §7-B가 AI/RAG의 도메인 DB 임의 생성 금지와 외부 호출 차단 원칙을 명시한다.
  - 실제 `LOW_SCORE_THRESHOLD=2`, `HIGH_THRESHOLD=0.7`, `LOW_THRESHOLD=0.3`, `QUERY_MIN_CHARS=2`도 문서와 맞다.

- G-5 후속 검토 분류: pass
  - doctors 별도 모듈, Patient.doctor_id, DoctorSchedule, Order/Prescription, calendar, health, notes 통합, resources, 노쇼 컬럼은 후속/m014+ 분류로 남아 있다.
  - 실제 `app/models/models.py`에도 `Doctor`, `Resource`, `DoctorSchedule`, `Order`, `Prescription`, `Patient.doctor_id`는 없다.

- G-6 doctors / medical_staff: pass
  - 현재 구현은 `Employee.role="doctor"`와 `Treatment.role="doctor"` 기반의 얇은 분기이며, 문서도 이를 staff 하위 M-03b로 둔다.
  - `_doctor_codes_set`, `is_doctor_filter`, 의사 항목 배정 시 role=doctor 강제 정책이 실제 코드와 맞다.

- G-7 순환 위험 + 분리 순서: pass
  - §5는 5-1~5-10까지 총 10개 섹션을 가진다. 요청서는 "9개 + audit"이라고 설명하므로 audit을 별도 추가로 본다면 정합하다.
  - §6은 core/audit/settings 우선, appointments 마지막, AI/SMS/stats/leaves 테스트 보강 후 분리라는 19-P-3 우선순위와 대체로 일치한다.

- G-8 19-P-3 caveat 반영: pass with caveat
  - symbol 중심 검증, `leave_type ∈ {am, pm, full}`, dirty/untracked 문서 3개 표현은 반영되었다.
  - PII 경로도 현재와 목표 후속을 구분하도록 보정되었다.
  - 단, `docs/refactor/19_refactor_dependency_map.md`는 현재 `Get-Content` 기준 622줄이다. 요청서 §3의 "620줄"과 다르다.
  - `app/routers/api.py` 예약 생성/수정 흐름에서는 `_check_lunch_block` 호출은 명확하지만, `leave_type=am/pm/full` 기반 반차 차단 로직은 백엔드에서 명확히 확인되지 않는다. 문서 내부에도 "확인 필요 / 현재 인라인 가정"이라고 적혀 있으므로 19-P-5에서 반드시 테스트 전략 항목으로 가져가야 한다.

## 3. 추가 발견 위험 / 누락 / 부정확 항목

- r2 요청서의 dependency map 줄 수 "620줄"은 현재 실측 622줄과 다르다. 의미상 큰 문제는 아니지만, r1에서 줄 수 caveat를 보정했다고 주장하는 항목이라 계속 minor issue로 둔다.
- `leave_type="am"`/`"pm"` 차단 정책은 action_leave와 leave API의 DB 표준으로는 확인되지만, 예약 생성/수정 백엔드 차단 로직으로는 확인되지 않았다. "현재 인라인"이라고 단정하기보다 "현재 위치 확인 필요"가 더 정확하다.
- pytest는 실행하지 않았다. 이번 검증은 문서/구조/symbol 대조이며, 실제 회귀 실행은 19-P-5 테스트 전략의 범위로 보는 것이 맞다.

## 4. 19-P-5 진입 권고

yes, with caveat

r2 dependency map은 19-P-5 테스트 전략 문서의 기준으로 사용할 수 있다. 다음 단계에서는 줄 수 표기 같은 숫자성 메타보다 실제 테스트 대상이 더 중요하다. 특히 appointments/availability/leaves 경계에서 점심창, 충돌, 휴무, `am`/`pm` 반차 차단을 분리 직전 contract/rules 테스트로 명확히 잠가야 한다.
