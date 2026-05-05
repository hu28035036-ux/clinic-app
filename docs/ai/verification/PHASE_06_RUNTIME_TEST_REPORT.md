# PHASE_06_RUNTIME_TEST_REPORT.md

## Phase / 시각

- Phase 6 — 하네스 풀세트 (10종 통합) + router endpoint + CI 통합
- 시각: 2026-05-05 (router / CI 보강)

## 명령

```bash
venv/Scripts/python.exe -m pytest tests/test_phase06_ai_harness.py -v          # 29/29
venv/Scripts/python.exe -m pytest tests/test_phase06_ai_harness_router.py -v   # 10/10 (신규)
venv/Scripts/python.exe -m pytest tests -q                                       # 1994 passed, 1 skipped, 10 xfailed, 0 failed
venv/Scripts/python.exe -m ruff check app tests                                  # 0 error
venv/Scripts/python.exe scripts/check_db_path.py                                 # 운영 DB 경로 검출 (단독 실행 시 정상 안내)
```

## 테스트 (29 + 10 = 39 케이스)

### 모듈 통합 (29) — `tests/test_phase06_ai_harness.py`


### 1) 정상 파이프라인 (5)

- 차트번호 단일 환자 확정 → NEEDS_APPROVAL → preview 정상
- 동명이인 → patient_selection_required, selected=None (AI 임의 선택 차단)
- selected_patient_id 명시 시 동명이인 중 확정 → validation 진행
- 차트+이름 mismatch → patient_mismatch
- 검색 실패 → patient_not_found + 신환 등록 제안 카드 (생년월일/연락처 prefill=None)

### 2) 충돌 / 차단 (3)

- 시간 겹침 → validation_failed
- 휴무 (full) → validation_failed
- alias 충돌 → treatment_alias_conflict

### 3) Approval + Executor (Gate 1 / Gate 2) (4)

- 정상 경로 (Gate 1 통과 + Gate 2 통과 + service 호출 + audit 기록)
- 동명이인 상태에서 승인 시도 → Gate 1 차단, service 호출 0
- 승인 후 다른 사용자가 같은 시간에 예약 끼어들기 → Gate 2 차단
- service 예외 → ExecutionResult.success=False (기존 프로그램 보호)

### 4) 신환 + 예약 두 단계 (2)

- 정상 경로 → 두 service 호출 + audit 2 row
- 신환 등록 실패 → 예약 단계 건너뜀, 예약 service 호출 0

### 5) Privacy 하네스 (6)

- ParserContext 통과 (raw_text + 캘린더 + intent + 치료항목명만)
- patient_list 차단
- all_phones / all_birth_dates 차단
- patient_memo 차단
- 중첩 dict (`outer.inner.appointment_memo`) 차단
- run_pipeline 의 provider 페이로드 PII 미포함

### 6) Hallucination 하네스 (4)

- "예약 완료" 단정 표현 차단
- 치료항목 status=needs_clarification + matched_id 채워짐 → 위반
- status=db_verified + matched_id None → 위반
- 정상 파이프라인 결과 → 위반 0

### 7) Regression smoke / 안전 (5)

- Phase 1~5 모듈 import / 호출 가능 (parser / resolver / validator / preview)
- run_pipeline 후 DB row 변화 0
- 외부 AI API 호출 0 (provider 미주입 → 정규식 fallback)
- provider 실패 시 정규식 fallback 으로 파이프라인 끝까지 진행
- preview['title'] = "예약 후보" (예약 완료 표현 금지)

### Router endpoint Runtime (10) — `tests/test_phase06_ai_harness_router.py`

- 토큰 없음 → 401
- 잘못된 토큰 → 401
- 정상 요청 → 200 + status / parsed / preview / diagnostics
- 차트번호 단일 매칭 → selected_patient 채워짐
- 동명이인 → patient_selection_required, selected=None
- 동명이인 + selected_patient_id → 확정 + validation
- 알 수 없는 환자 → patient_not_found + new_patient_proposal (생년월일/연락처 prefill=None)
- DB 직접 수정 0 — endpoint 호출 전후 row 동일
- raw_text 누락 → 422
- today_iso 형식 오류 → 400

## 결과

✅ 모듈 29/29 통과
✅ Router 10/10 통과
✅ 1994 passed / 0 failed (Phase 5 까지 1955 + Phase 6 모듈 29 + Phase 6 router 10)
✅ Ruff 0 error
✅ DB 직접 수정 0 / 외부 API 호출 0
✅ Gate 1 + Gate 2 모두 입증 (시간 겹침 끼어들기 시나리오 통과)

## 발견 / 수정

| # | 항목 | 처리 |
|---|---|---|
| 1 | Phase 2 parser `_extract_patient_name` false positive (치료항목 키워드 미제거) | 보강 — `PHASE_06_CLAUDE_SELF_FIXES.md § 1` |
| 2 | `_FORBIDDEN_PHRASES` 의 "환자입니다" 너무 광범위 | 단어 단위 정합 — `PHASE_06_CLAUDE_SELF_FIXES.md § 2` |
| 3 | Ruff 1 (사용 안 하는 import) | 자동 수정 |
| 4 | router endpoint `POST /api/ai/harness/run` 미구현 — 사용자가 "마음대로 만드는게 아니라 문서대로 만들고 있지?" 지적 | `app/routers/ai_harness_router.py` 신규 + main.py include + spec hidden import + 10 Runtime Test 추가 |
| 5 | CI 통합 — `.github/workflows/ai-harness-ci.yml` 점검 | Ruff + DB 안전검사 + Phase 1~6 + 전체 회귀 자동 실행 워크플로우 정합 확인 |

## 최종 판단

**정상 작동** ✅

- Phase 1~5 모듈을 end-to-end 흐름으로 통합 검증 가능
- 10 하네스 (Parser / Resolver / Patient Candidate / Validator / Approval / Executor / Privacy / Hallucination / Regression / Runtime) 모두 구현 + 테스트
- Gate 1 (사용자 승인 가능 상태 검사) + Gate 2 (executor 의 validator 재호출) 통합 동작 입증
- DB 직접 수정 0 / 외부 AI API 호출 0 / "예약 완료" 표현 0
- AI 가 임의로 환자 / 치료항목 / 차트번호 / 생년월일 / 연락처를 확정 / 생성하지 않음

## 남은 위험 (자만 없는 인정)

1. ~~**router endpoint 미구현**~~ — ✅ 구현 완료. `app/routers/ai_harness_router.py` + 10 Runtime Test
2. **운영 DB 검증 미수행** — in-memory SQLAlchemy 만 사용. 실제 `%APPDATA%\도수치료예약\clinic.db` 에서의 동작은 미검증
3. **외부 LLM provider 실제 페이로드** — MockProvider + 정규식 fallback 만 검증. OpenAI / Anthropic 실제 SDK 호출 시의 전송 페이로드는 미검증
4. **Phase 2 parser 의 다른 false positive** — 치료항목 키워드 1건은 잡았으나 의사명 / 메모 / 한자 / 영문 환자명 등 미점검
5. **Codex 검증 생략** (사용자 추가수정사항 5) — 다른 시각의 검증 부재

이 위험들은 Phase 7 / 향후 Phase 에서 점진 보강.
