# 19-P-7 Codex 검증 결과 (r3)

- 대상 요청서: `reports/refactor/latest_codex_review_request.md`
- 대상 산출물: `docs/refactor/19_refactor_risk_register.md`
- 검증 시각: 2026-05-03
- 종합 판정: **pass with caveat**

## 1. 종합 판정

**pass with caveat**.

19-P-7 r3는 r2 fail 사유였던 taxonomy 숫자 불일치를 실제 파일 기준으로 정정했다.

직접 확인한 값:

- `#### R-*` 형식의 실제 Risk ID 제목 수: **77개**
- `§2` 섹션 제목 수 (`2-A` ~ `2-W`): **23개**
- `§1-3` 카테고리 키 표: **23행** (단독 Risk prefix 20개 + 통합 키 3개)
- `R-LOCK-04`: 별도 Risk ID 제목이 아니라 `(통합 메모)`로 격하됨

요청서와 위험 등록 문서의 주요 taxonomy 설명은 이제 위 실측값과 맞다. 단, `§6-2`와 요청서 일부에 남은 "약 70 Risk" 표현은 77개를 넓게 부르는 표현이라 큰 결함은 아니지만, 아카이브 전에는 "77 Risk ID"로 통일하는 편이 더 깔끔하다.

## 2. 게이트별 결과

### G-1 코드 무수정

판정: **pass with caveat**

`git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 결과는 기존 5개 tracked 변경만 보인다.

- `app/models/models.py`
- `app/routers/ai.py`
- `app/services/ai/manual_qa.py`
- `dosu_clinic.spec`
- `tests/conftest.py`

이번 r3 보정이 app/tests/spec/UI/requirements를 새로 수정했다는 증거는 없다. 다만 기존 dirty/untracked 상태는 계속 caveat다.

### G-2 핵심 위험 등록 정합

판정: **pass**

taxonomy가 r3 기준으로 정리되었다.

- §1-3: 23행, 단독 prefix 20개 + 통합 키 3개
- §2: 23개 섹션
- Risk ID 제목: 77개
- notes / feature_flags / privacy는 통합 메모 섹션
- LOCK atomic rename은 `R-BAK-03` 통합 메모

핵심 위험 카테고리도 appointments / patients / therapists / doctors / leaves / treatments / stats / sms / admin / backup / AI/RAG / calendar / audit / health / export_import / core / batch / locking / time_utils / OPS를 포괄한다.

### G-3 위험도 분류 현실성

판정: **pass**

§3-A 치명 위험 8개와 §3-B 높은 위험 14개 표는 실제 행 수와 맞다.

### G-4 응답 키 / URL 후방호환

판정: **pass**

R-APPT-01, R-PAT-02, R-STAT 계열, R-SMS 계열, R-CORE-04/05 등에서 응답 키와 UI 의존 키 보존 위험을 명시한다. 실제 endpoint count도 `app/routers/api.py` 86개, `app/routers/ai.py` 13개로 기존 전제와 맞다.

### G-5 AI/RAG local-first

판정: **pass**

R-AI-01~07, R-LOCK-03, R-OPS-03에서 local-first, local_only 외부 호출 0, `_block_sdk_modules`, provider call 차단, PII 마스킹을 위험으로 등록한다.

### G-6 doctors / medical_staff 부재 단정 X

판정: **pass**

doctors / `Patient.doctor_id` / `Department` / `Room` / `DoctorSchedule` / `Order` / `Prescription` / `Resource` / `/api/health` / no_show 부재 전제는 실제 grep 결과와 맞다.

### G-7 19-P-4 caveat 위험 등록

판정: **pass**

R-APPT-02 / R-APPT-03 / R-APPT-04가 `xfail` 7건 + `skip` 1건의 정방향 전환 필요성을 명시한다. 실제 테스트 표식도 `tests/test_appointment_rules.py` `xfail` 3건 + `skip` 1건, `tests/test_therapist_leave.py` `xfail` 4건으로 맞다.

### G-8 PyInstaller 검증 시점

판정: **pass**

R-OPS-04 / R-OPS-05 / R-OPS-06에서 hidden imports, 실제 exe smoke, requirements 변경 위험을 분리해 등록한다.

### G-9 운영 DB / 외부 API 차단

판정: **pass**

R-OPS-01~03, R-BAK-01, R-AI-06, R-SMS-04가 운영 DB 접근과 외부 API 호출 차단을 위험으로 등록한다.

### G-10 후속 검토 단정 X

판정: **pass**

doctors, recurring appointments, resources, notifications, printing, `/api/health`, no_show, AI 의사 가드 등은 현재 구현으로 단정하지 않는다.

### G-11 주석 / 문서화 기준 정합

판정: **pass with caveat**

§6-2 주석 태그 매트릭스가 존재하고 주요 Risk ID와 COMPAT / SAFETY / NOTE / RISK / TODO 태그를 연결한다. 단, 아직 "약 70 Risk" 표현이 남아 있으므로 "77 Risk ID"로 통일하면 더 정확하다.

### G-12 세션별 위험 연결 정합

판정: **pass**

§5는 19-0~19-14를 모두 매핑한다. 19-4, 19-9, 19-13, 19-14의 핵심 위험도 19-P-6 롤아웃 계획과 맞다.

## 3. 추가 발견 / 위험 / 불확실

1. **잔여 표현 caveat**

`§6-2`와 요청서 일부에 "약 70 Risk" 표현이 남아 있다. 77개와 크게 충돌하지는 않지만, r3에서 숫자를 엄밀하게 맞춘 만큼 "77 Risk ID"로 바꾸는 편이 낫다.

2. **dirty 워크트리**

기존 dirty/untracked 변경이 많다. 이번 문서 검증 실패 사유는 아니지만 19-0에서 반드시 정리/commit 기준을 좁혀야 한다.

3. **pytest 미실행**

이번 검증은 문서, 실제 파일 구조, grep/카운트 기반 대조로 수행했다. 테스트 실행 결과를 새로 보증하지 않는다.

## 4. 19-P-8 진입 권고

**yes — 19-P-8 진입 가능.**

r3는 r2 fail의 핵심이던 taxonomy 숫자 불일치를 해소했다. 다음 단계인 `docs/refactor/19_refactor_decision_record.md` 작성으로 넘어가도 된다. 아카이브 전에는 남은 "약 70 Risk" 표현만 77 기준으로 다듬는 것을 권장한다.
