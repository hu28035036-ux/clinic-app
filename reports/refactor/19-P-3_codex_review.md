# 19-P-3 Codex 검증 결과

## 1. 종합 판정

pass with caveat

`reports/refactor/latest_codex_review_request.md`와 신규 산출물 `docs/refactor/19_refactor_module_map.md`를 실제 파일 구조, 19-P-1 현재 구조 문서, 19-P-2 목표 구조 문서, 주요 코드 위치와 직접 대조했다.

모듈 매핑 자체는 19-P-1/19-P-2 기준과 대체로 정합하고, 현재 없는 기능을 현재 구현된 것처럼 단정한 치명적 오류는 발견하지 못했다. 다만 현재 작업트리는 이미 18-0~18-8 AI/RAG 변경분이 dirty/untracked 상태로 남아 있어, Git만으로 "19-P-3 세션에서 코드 변경 0"을 완전 분리 증명할 수는 없다. 따라서 G-1은 `pass with caveat`로 둔다.

## 2. 게이트별 결과

- G-1 코드 무수정: pass with caveat
  - `HEAD`는 요청 문서의 baseline과 동일한 `bcd74a7aabc9de8d735425863254cfc393bda580`.
  - `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml`는 기존 18-0~18-8 범위로 보이는 tracked 변경 5개를 표시한다: `app/models/models.py`, `app/routers/ai.py`, `app/services/ai/manual_qa.py`, `dosu_clinic.spec`, `tests/conftest.py`.
  - 현재 `git status`에는 m012/m013, AI RAG/knowledge/vector 코드, 신규 harness/test 파일 등 untracked 변경도 다수 남아 있다. 이는 19-P-3 문서만의 신규 변경이라고 보기 어렵지만, "현재 작업트리 전체가 문서만 변경"이라는 문장으로는 표현하면 안 된다.
  - `reports/refactor/19-P-3_codex_review_request.md`와 `reports/refactor/latest_codex_review_request.md`는 `Compare-Object` 결과 차이가 없어 동일 내용이다.

- G-2 매핑 정합: pass
  - `docs/refactor/19_refactor_module_map.md`는 인덱스 30개(appointments~notifications), 모듈별 상세 `2-1`~`2-30`, 후단 `31`~`40`을 갖춘다.
  - 19-P-2 §9의 37행(M-01~M-36 + M-03b)은 module_map에서 30개 사용자 모듈과 보조/후속 섹션으로 모두 연결된다.
  - 실제 `/api` endpoint 수는 86개, `/api/ai` endpoint 수는 13개로 19-P-1/19-P-3 문서와 맞다.
  - 실제 테스트 파일 수는 `tests/test_*.py` 기준 40개로 19-P-1 현재 구조 문서와 맞다.

- G-3 응답 키 / URL 후방호환: pass
  - module_map §35가 AI 33+ 키와 비-AI 주요 contract 미작성 영역을 분리해 적고, §34에서 appointments/patients/stats/sms/admin/export_import의 분리 직전 contract 보강 필요를 명시한다.
  - `/api/therapist-leaves`의 `therapist_id`/`employee_id` alias 보존, `manual_qa` wrapper 시그니처, `version` 키와 409 충돌 응답 등 호환 위험 지점이 §39에 포함되어 있다.

- G-4 AI/RAG local-first: pass
  - module_map §2-11과 §39는 local-first, PII/API key safety, manual_qa wrapper, `LOW_SCORE_THRESHOLD`, vector lazy import, ENTITY_MAP/hidden imports 위험을 별도 위험 지점으로 둔다.
  - 실제 `app/routers/ai.py`는 13개 endpoint를 가지며, AI health/status/manual/action 경계는 문서 설명과 맞다.

- G-5 후속 검토 분류 적절성: pass
  - calendar, health, recurring_appointments, resources, printing, notifications, no_show, doctors EMR, Patient.doctor_id, DoctorSchedule, Order/Prescription는 현재 부재 또는 부분 존재로 분류되어 있다.
  - 실제 `app/models/models.py`에는 `Doctor`, `Resource`, `DoctorSchedule`, `Order`, `Prescription`, `Patient.doctor_id`가 없다. module_map의 후속 검토 분류와 맞다.
  - recurring/printing/notifications는 M-ID가 없는 사용자 후보 기능으로 남겨져 있어 "현재 기능"으로 과장하지 않았다.

- G-6 doctors / medical_staff: pass
  - 실제 `_doctor_codes_set`는 `app/routers/api.py:153`, `is_doctor_filter`는 `app/routers/api.py:3464`, 의사 항목 handler 강제는 appointment assign 흐름에 존재한다.
  - module_map §2-4와 §38은 현재 role=doctor 분기와 EMR/담당의/진료과/진료실/오더/처방 후속 검토를 분리한다.
  - AI 의사 정보 임의 생성 금지는 §2-4/§38/§39에 후속 safety 위험으로 남아 있다.

## 3. 추가 발견한 위험 / 누락 / 부정확 항목

- 현재 작업트리 caveat: 요청 문서의 "신규 3개 문서만"이라는 표현은 19-P-3 산출 범위 설명으로는 수용 가능하지만, 현재 git 상태 전체 설명으로는 부정확하다. 실제로는 18-0~18-8 관련 tracked/untracked 코드/테스트 변경이 남아 있다.
- 일부 줄 번호는 현재 파일과 약간 어긋난다. 예를 들어 실제 `app/routers/api.py`는 5058줄, `app/routers/ai.py`는 925줄인데 19-P-1 문서에는 5127줄/929줄로 적힌 곳이 있다. 핵심 endpoint 라인과 함수명은 대체로 맞지만, 후속 구현 전에는 줄 번호보다 symbol grep 기준으로 재확인해야 한다.
- availability의 오전/오후 반차는 실제 코드에서 `leave_type` 값(`am`/`pm`)으로 존재하지만, 예약 차단 로직까지 완전한 독립 정책으로 추출된 상태는 아니다. module_map이 "부분 존재"로 둔 판단은 타당하며, 19-P-4 이후 의존성 문서에서 더 구체화가 필요하다.
- 19-P-3 문서는 테스트 실행 대상이 아니라 문서 검증이므로 pytest는 실행하지 않았다.

## 4. 19-P-4 진입 권고

yes, with caveat

모듈 매핑 문서는 다음 단계인 `docs/refactor/19_refactor_dependencies.md` 작성에 사용할 수 있을 만큼 정합하다. 단, 19-P-4 진입 전에 현재 dirty/untracked 작업트리 경계를 계속 명시하고, 이후 검증에서는 줄 번호보다 실제 symbol/API grep을 기준으로 삼는 것이 안전하다.
