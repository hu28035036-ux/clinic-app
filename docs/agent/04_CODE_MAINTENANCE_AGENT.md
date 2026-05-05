# 04_CODE_MAINTENANCE_AGENT

비-AI / 비-DB-스키마 영역의 백엔드 + 프런트 일반 코드 수정. 가장 많이 호출되는 Agent.

---

## 0. 기본 모델 정책

- **기본 모델: sonnet**
- 상위 모델 조건: 여러 파일에 걸친 복잡한 버그 수정 / 대규모 코드 수정 → `opusplan` 가능.
- haiku 사용: 오타 / 라벨 / 작은 CSS 수정처럼 *매우 단순한 경우* 에만 가능. 도메인 / API / 권한 / DB 가 닿는 변경에는 ❌.

---

## 1. Agent 목적

- 사용자가 요청한 **버그 수정 / 동작 보강** 을 *최소 변경* 으로 적용한다.
- 거의 모든 작업의 마지막 단계 (코드 변경) 를 담당.
- AI 관련 변경은 06 Agent 와 협력. DB 스키마 변경은 07 Agent 와 협력. 도메인 규칙 변경은 09 Agent 와 협력.

## 2. 담당 범위

- `app/routers/api.py` (메인 핸들러, ~3800줄), `app/routers/pages.py`, `app/routers/ai.py`, `app/routers/ai_commands_router.py`, `app/routers/ai_harness_router.py`
- `app/modules/<도메인>/service.py`, `repository.py`, `rules.py`, `schemas.py`
- `app/services/auth.py`, `app/services/sync.py`, `app/services/backup.py`, `app/services/seed.py`
- `app/templates/main.html` (대형, ~5000줄), `base.html`, `_ai_appointment_helper.html`, `_ai_leave_helper.html`, `setup.html`, `server_info.html`
- `app/static/css/app.css`, `_ai_helper.css`
- `app/static/js/ai_helper.js`, `ai_leave_helper.js`
- `app/models/models.py`, `app/models/schemas.py`, `app/models/constants.py`

## 3. 실제 확인한 관련 파일/모듈

### 3.1 예약 관련
- `app/routers/api.py` — 예약 CRUD / 승인 / 취소 / split / 시리즈 / 충돌 검사 인라인.
- `app/modules/appointments/availability.py`, `rules.py`, `repository.py`, `service.py`, `schemas.py`
- `app/modules/appointment_series/service.py`, `router.py` (20-3-4)
- `docs/specs/01_예약_규칙.md`

### 3.2 환자 관련
- `app/routers/api.py` 의 환자 핸들러
- `app/modules/patients/{rules,repository,service}.py`
- `app/modules/notes/{rules,service}.py`

### 3.3 치료사 / 의사
- `app/modules/therapists/{rules,repository,service}.py`
- `app/modules/doctors/{router,service,schemas}.py` (20-3-3 가벼운 의사만)
- `app/migrations/m016_doctors_table.py`

### 3.4 휴무일
- `app/modules/leaves/{rules,repository,service}.py`
- `app/services/ai/action_leave.py` (RAG/LLM 기반 v1.3 흐름)
- `app/ai/ai_leave.py` (Phase 8 정규식 흐름)
- `docs/specs/02_치료사_휴무_규칙.md`

### 3.5 치료항목
- `app/modules/treatments/{rules,repository,service,completion_rules}.py`
- `app/migrations/m005_treatment_price_incentive.py`, `m006_manual_counts.py`, `m020_treatment_aliases.py`

### 3.6 예약 문자
- `app/modules/sms/{rules,service,provider,schemas,templates}.py`
- `app/services/ai/sms_draft.py`
- `app/services/ai/validators.py`

### 3.7 관리자 설정
- `app/routers/api.py` 의 admin 핸들러 (`require_admin`)
- `app/services/auth.py`
- `app/modules/admin/{service,schemas}.py`
- `app/modules/audit/{service,schemas,retention}.py`
- `app/modules/export_import/{service,schemas}.py`

### 3.8 통계
- `app/routers/api.py` 의 `/stats/*` 핸들러
- `app/modules/stats/{rules,repository,aggregators,service,schemas}.py`
- `docs/specs/03_완료카운트_통계_규칙.md`

### 3.9 자원 (치료실)
- `app/modules/resources/{router,service,schemas}.py` (20-3-5)
- `app/migrations/m018_resources.py`

## 4. 작업 전 확인사항

1. 사용자 요청을 한 줄 요약 → 영향 모듈을 § 3 표에서 식별.
2. 관련 `docs/specs/*.md` 가 있으면 먼저 읽음 (예약/휴무/통계).
3. 수정 대상 파일의 현재 흐름을 *읽고 요약* (CLAUDE.md 작업 전 필수 항목).
4. 도메인 규칙 변경이면 09 Agent 호출 후 시작 — 서비스 흐름과 통계 / 카운트 로직 먼저 정리.
5. 변경 범위 최소화 — 한 작업에 여러 도메인 동시 수정 ❌.

## 5. 작업 중 금지사항

- DB 컬럼명 / API 경로 / 응답 dict 키 변경 금지 (CLAUDE.md).
- 프런트(Alpine) 만 막고 백엔드를 안 막는 것 금지 — 반드시 양쪽 검증.
- `manual60` 의 `count_increment=2` 환원 금지 (CLAUDE.md). `manual30=1` / `manual60=1` 카운트 정책 단일 원천.
- `pyproject.toml` 의 `app/**` lint 면제 해제 금지.
- AI 흐름 변경은 06 Agent 협의 없이 단독으로 하지 않기.
- "한 줄 단순 변경" 처럼 보여도 라우터 / 서비스 / 통계 / UI 4 군데 모두 영향 받는 경우가 흔함 — 검색 후 변경.
- `app/routers/api.py` 안의 인라인 도메인 로직과 `app/modules/<x>/` helper 가 *byte-equivalent* 으로 유지되어야 함을 깨는 변경 금지 (19-P 결정).

## 6. 작업 후 테스트 항목

| 변경 영역 | 우선 실행 테스트 |
|---|---|
| 예약 | `tests/test_appointment_rules.py`, `tests/test_19_9_appointments.py`, `tests/test_20_3_4_appointment_series.py`, `tests/test_20_3_5_resources.py` |
| 환자 | `tests/test_19_7_patients_notes.py` |
| 치료사 | `tests/test_19_8_therapists.py`, `tests/test_employee_*.py` (`leave_kind`, `hire_date`, `leave_unique`, `can_manual_contract`) |
| 의사 | `tests/test_20_3_3_doctors.py` |
| 휴무 | `tests/test_therapist_leave.py`, `tests/test_19_5_leaves.py`, `tests/test_employee_leave_kind.py`, `tests/test_employee_leave_unique.py`, `tests/test_ai_action_leave.py` |
| 치료항목 | `tests/test_19_6_treatments.py` |
| 문자 | `tests/test_19_10_sms.py`, `tests/test_ai_sms_*.py`, `tests/test_sms_secret_masking.py` |
| 관리자 / 권한 | `tests/test_admin_auth_required.py`, `tests/test_19_12_admin.py`, `tests/test_admin_ui_smoke.py`, `tests/test_20_3_2_permission_level.py` |
| 통계 | `tests/test_stats_counts.py`, `tests/test_19_11_stats.py` |
| 노쇼 (F-10) | `tests/test_20_3_1_no_show.py` |
| 스모크 | `tests/test_smoke.py`, `tests/test_19_14_smoke_workflow.py` |

전체 회귀: `run_check.bat`

## 7. 보고 형식

```
[변경 파일] 절대경로 목록
[변경 라인 수] 추가 / 삭제
[관련 spec] docs/specs/*.md 참조 항목
[테스트] 실행 명령 + 결과 (예: pytest tests/test_appointment_rules.py -v → 12 passed)
[회귀 영향] 다른 도메인 파급 여부
[Open] 사용자 확인 필요 항목
```

## 8. 이 프로젝트에서 특히 주의할 점

- `app/routers/api.py` 는 *고의로* 큰 파일이다 — 분리 시도 금지 (19-P 결정).
- `main.html` (~5000줄) 은 모든 탭 JS 가 한 파일에 들어 있다 — 새 partial 분리는 사용자 동의 필요. 현재까지 분리된 partial: `_ai_appointment_helper.html`, `_ai_leave_helper.html`.
- 정적 자원 캐시 무효화는 `?v={{ app_version }}` 패턴 — 버전 올릴 때 자동 갱신. 손으로 갱신할 일 없음.
- `app/services/sync.py` 는 다중 노드 (메인/서브) 동기화 — 함부로 끄면 안 됨. 테스트에선 `conftest.py` 가 무력화.
- `app/services/backup.py` 의 자동 백업도 동일 — 테스트 격리 필수.
