# 19-P-2 Codex 검증 결과 (r3)

## 1. 종합 판정

pass

`reports/refactor/latest_codex_review_request.md` r3 보정본과 `docs/refactor/19_refactor_target_architecture.md` r3를 실제 파일 구조와 다시 대조했다. r1/r2에서 지적된 V2 트리와 후속 검토 경계, 모듈 개수, §9 A/B/C 카운트 불일치가 해소되었다.

G-1은 이전과 동일하게 dirty/untracked 작업트리 caveat가 있다. 다만 실제 diff 대상은 기존 18-0~18-8 변경 범위와 일치하고, 이번 19-P-2 r3에서 코드/테스트/spec/UI/migrations/requirements를 추가 수정했다는 증거는 발견하지 못했다.

## 2. 게이트별 결과

- G-1 코드 무수정: pass with caveat
  - `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml`는 기존 18-0~18-8 변경 파일 5개만 표시한다: `app/models/models.py`, `app/routers/ai.py`, `app/services/ai/manual_qa.py`, `dosu_clinic.spec`, `tests/conftest.py`.
  - untracked 18-0~18-8 산출물은 여전히 남아 있다: m012/m013, AI RAG/knowledge/vector, 신규 harness/test 파일들.
  - 19-P-2 r3 문서 수정은 `docs/refactor/19_refactor_target_architecture.md`, `reports/refactor/19-P-2_codex_review_request.md`, `reports/refactor/latest_codex_review_request.md` 범위로 보인다.

- G-2 현재 구조 정합: pass
  - V2 트리의 실제 modules 수는 13개이고 문서도 13개로 보정되었다: appointments, patients, staff, leaves, treatments, stats, sms, admin, backup, ai, audit, settings, export_import.
  - post-19-P 후보 블록은 6개이고 문서도 6개로 보정되었다: calendar, notes, health, doctors, resources, emr.
  - `/api` 라우터 86개, `/api/ai` 13개, HTML 라우트 2개가 19-P-1 r2 기준과 맞다.
  - `Employee`는 단일 테이블 + `ROLE_DOCTOR="doctor"` / `ROLE_THERAPIST="therapist"` 분기 구조가 맞다.
  - `_doctor_codes_set`는 `app/routers/api.py:153`, `is_doctor_filter`는 `app/routers/api.py:3464`, 의사 role 배정 검증은 `app/routers/api.py:1775`에 존재한다.
  - `Patient.doctor_id`, `Doctor`, `Order`, `Prescription`, `Resource`, `DoctorSchedule` 등 EMR/담당의 관련 모델은 실제로 부재한다.

- G-3 응답 키 / URL 후방호환 원칙: pass
  - §7-1 URL 유지, §7-2 응답 키 보존, §7-3 DB schema/m001~m013 보존 정책이 명시되어 있다.
  - 비-AI 86개 endpoint 응답 키 매트릭스는 분리 직전 contract 테스트로 잠그겠다고 되어 있어 설계 문서 범위에서는 타당하다.

- G-4 AI/RAG local-first 보존: pass
  - §3-10, §6-1, §7-7에서 AI/RAG local-first와 도메인 DB 임의 의존 금지를 명시했다.
  - 실제 `app/services/ai/rag/pipeline.py`에는 `LOW_SCORE_THRESHOLD=2`, `_RE_MEDICAL_CLAIM`, `_RE_EXECUTION_CLAIM`, unsupported claim 가드가 존재한다.
  - `HIGH_THRESHOLD=0.7`, `LOW_THRESHOLD=0.3`, `QUERY_MIN_CHARS=2`도 실제 코드와 맞다.

- G-5 후속 검토 분류 적절성: pass
  - `calendar`, `notes`, `health`, `doctors`, `resources`, `emr`는 post-19-P 후보 블록으로 V2 트리에서 분리되었다.
  - §9 메인 분류표는 37행이고, 문서의 A/B/C 카운트와 실제 표가 일치한다: A=21, B=6, C=10.
  - M-13 sync, M-26 calendar, M-27 notes, M-28 /api/health, M-31~M-36 doctors/EMR/AI guard 항목은 현재 부재 또는 정책 미결정으로 후속 검토 분류가 적절하다.

- G-6 doctors/medical_staff 검토: pass
  - §3-3 staff, §3-3-3 doctors 책임, §3-3-4 부재/후속 검토, §4 doctors/medical_staff, §9 M-03b/M-31~M-36이 모두 존재한다.
  - 현재 구현되지 않은 담당의/진료과/진료실/오더/처방/EMR은 실제 구현 대상으로 단정하지 않고 후속 검토로 분류했다.
  - AI가 의사/진료진 정보를 DB 근거 없이 생성하지 말아야 한다는 정책도 §3-10과 M-36에 명시되어 있다.

## 3. 추가 발견한 위험 / 누락 / 부정확 / 과도한 이상화 항목

- 세션 경계 검증 caveat는 계속 남는다. 18-0~18-8 변경분이 커밋되지 않은 dirty/untracked 작업트리 위라, 19-P-2에서 코드가 0바이트 수정됐다는 사실을 Git만으로 완전 분리 증명하기는 어렵다.
- 19-P-3 모듈 매핑으로 넘어가기 전, 비-AI 86개 endpoint 중 실제 분리 대상 도메인부터 응답 키 contract를 선별해 잠그는 순서를 문서화하면 이후 구현 리스크가 줄어든다.
- `sync`는 C로 둔 판단이 타당하지만, 외부 노드 호환 키(`ENTITY_MAP`)가 매우 민감하므로 19-P-3 매핑 문서에서 "위치 유지"와 "키 불변"을 별도 빨간 줄로 두는 편이 좋다.

## 4. 19-P-3 진입 권고

yes

r3 보정본은 현재 파일 구조와 목표 구조 문서가 충분히 정합하다. 남은 사항은 구현 전 매핑/contract 테스트 설계의 문제이지, 19-P-2 목표 아키텍처 문서를 막을 수준의 불일치는 발견하지 못했다.

