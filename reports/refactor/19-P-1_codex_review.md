# 19-P-1 Codex 검증 결과 (r2)

## 1. 종합 판정

pass

`reports/refactor/latest_codex_review_request.md` r2 보정본을 기준으로 다시 검증했다. 1차 fail 항목이었던 `/api` 엔드포인트 수, ORM 모델 수, 테스트 파일 수, harness 줄수, §22 자체 모순, stale 2차 기준 문서 표시는 실제 파일/그렙 결과와 정합하게 보정되어 있다.

단, G-1은 dirty/untracked 작업트리 위에서 세션 경계를 Git만으로 완전 증명할 수는 없다. 다만 실제 diff 대상은 r2 요청서가 명시한 18-0~18-8 변경 범위와 일치하고, r2 이후 수정시각 기준으로 코드/테스트/spec 변경 흔적은 확인되지 않았다.

## 2. 게이트별 결과

- G-1 코드 무수정: pass with caveat
  - `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml`는 기존 18-0~18-8 변경 파일 5개를 표시한다: `app/models/models.py`, `app/routers/ai.py`, `app/services/ai/manual_qa.py`, `dosu_clinic.spec`, `tests/conftest.py`.
  - untracked 18-0~18-8 산출물도 남아 있다: m012/m013, AI RAG/knowledge/vector, 신규 harness/test 파일들.
  - r2 문서 수정시각 이후 `app/**`, `tests/**`, `dosu_clinic.spec`, requirements, UI, `pyproject.toml`의 추가 수정 흔적은 발견하지 못했다.

- G-2 문서 정합: pass
  - `app/routers/api.py`: `grep` 기준 라우터 데코레이터 86개. 문서 §3-1/§19/§23과 일치.
  - `app/routers/ai.py`: 13개, `app/routers/pages.py`: 2개. 문서와 일치.
  - `app/models/models.py`: `class *(Base)` 19개. 문서 §1/§2/§4와 일치.
  - `app/migrations/m*_*.py`: 13개, m001~m013. 문서와 일치.
  - `tests/test_*.py`: 40개. 문서 §1/§6과 일치.
  - `tests/harness/*.py`: 12개, `wc -l` 방식 합계 1420줄. 문서 §7과 일치.
  - 주요 파일 줄수도 `wc -l` 방식으로 문서 §2와 일치한다. 예: `api.py` 5127, `ai.py` 929, `models.py` 464, `app/static/css/app.css` 3626.

- G-3 응답 키 후방호환: pass
  - `run_manual_search()`는 `sources`, `masked_question`, `top_score` 3키를 반환한다.
  - `run_manual_ask()`는 `answer`, `sources`, `confidence`, `not_found`, `blocked`, `blocked_reason`, `guard_hits`, `top_score`, `masked_question` 9키를 유지한다.
  - `/api/ai/health`, `/api/ai/health/public`, `/api/ai/status`의 문서화된 키 셋도 실제 라우터와 `build_admin_status()` 흐름에 맞다.

- G-4 위험 구간 식별: pass
  - `api.py` 거대 라우터, `main.html` 단일 script, `ai.py` 13 endpoint, `action_leave.py` 휴무 액션 응집, `health.py` 집계, `knowledge/indexer.py` vector lazy import, therapist alias를 빠짐없이 식별했다.
  - `_doctor_codes_set`, `_get_manual_*`, `_bump_patient_count`, `_apply_patient_counts`, `_upsert_employee_leave_core` 위치도 실제 코드와 맞다.
  - `manual60 count_increment=1`, `pyproject.toml`의 `app/**/*.py` per-file-ignores, m001~m013 무수정 정책도 실제와 맞다.

- G-5 확인 필요 적절성: pass
  - r1에서 문제였던 C-9/C-10/C-14/C-18이 §22-A로 이동했고, 각 항목은 실제 코드 근거와 의사결정 사항으로 분리되었다.
  - 남은 C-1~C-17 항목은 비-AI 응답 키 전수표, SMS/action/data-convert/stats 응답 계약, sync/entity 분리 영향, UI 분리 등 도메인별 분리 직전 별도 검증이 필요한 항목으로 보는 것이 타당하다.

- G-6 stale 표시: pass
  - §24는 `docs/ai_rag_current_state.md`의 stale 항목을 정확히 집었다: 마지막 마이그레이션 m011/다음 m012, FakeEmbeddingProvider 부재 언급, §11의 m011/m012 반복.
  - 현재 기준은 m013 적용, 다음 m014, FakeEmbeddingProvider 존재가 맞다.

## 3. 추가 발견한 위험 / 누락 / 부정확 항목

- 세션 경계 검증은 여전히 Git만으로는 완전하지 않다. 18-0~18-8 변경이 커밋되지 않은 채 19-P 문서 작업이 진행되어, "본 세션에서 코드 0바이트 수정"은 baseline commit 하나만으로 기계적으로 분리 검증할 수 없다. 향후에는 19-P 진입 전 커밋 또는 태그가 있으면 G-1이 훨씬 깨끗해진다.
- `docs/ai_rag_current_state.md`는 §24 caveat 덕분에 19-P 기준 문서로 사용할 수 있지만, 별도 문서 갱신 세션에서 stale 항목을 정리하면 이후 검증 혼선이 줄어든다.
- 비-AI 86개 엔드포인트의 응답 키 전수표는 아직 별도 보강 대상이다. 19-P-2가 실제 분리 작업이라면 해당 도메인부터 contract 표/테스트를 먼저 잠그는 편이 안전하다.

## 4. 19-P-2 진입 권고

yes

r2 보정본은 현재 파일 구조와 문서 내용이 충분히 정합하며, 1차 검증 fail 항목도 해소되었다. 세션 경계 검증 caveat는 남지만, 코드/테스트/spec/UI 변경 없이 기준점 문서를 보정했다는 판단을 뒤집을 증거는 발견하지 못했다.

