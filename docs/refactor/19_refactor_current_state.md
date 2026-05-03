# 19-P 단위화 리팩토링 — 현재 구조 스냅샷 (19_refactor_current_state)

> 19-P 단위화 리팩토링 진입 직전의 **기준점 문서**.
> 이후 모듈 분리 변경마다 본 문서를 회귀 비교 기준으로 사용한다.
> 모든 항목은 실제 파일/그렙 결과로 확인했고, 미확인 항목은 §22 "확인 필요"로 표시한다.

## 0. 메타

- 스냅샷 작성일: 2026-05-02
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (full sha) / `bcd74a7` (short) — release v1.3.3: AI/RAG v1 후속 보강 + SDK 진단 강화
- 기준 버전: `APP_VERSION = "1.3.3"` ([app/config.py:10](app/config.py:10))
- 빌드 일자: `APP_BUILD_DATE = "2026-05-01"` ([app/config.py:11](app/config.py:11))
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed** ([reports/ai_dev_loop/18-8_test_report.md](reports/ai_dev_loop/18-8_test_report.md))
- 본 세션은 **읽기 전용** — 코드/테스트/마이그레이션/spec/UI/requirements 무수정.
- 1차 Codex 검증 (2026-05-02 fail) 후 본 문서를 보정 — 보정 항목: `/api` 86개, ORM 19개, 테스트 40파일, harness 1420줄, §22 C-9/C-10/C-14/C-18 → §22-A 로 이동, [docs/ai_rag_current_state.md](docs/ai_rag_current_state.md) 2차 기준 stale caveat 추가 (§24).

---

## 1. 현재 주요 폴더 구조

```
병원예약관리/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 앱 부트스트랩 (init_db + 라우터 + 워커)
│   ├── config.py                # APP_VERSION, get_db_path, load_config
│   ├── database.py              # SQLAlchemy 엔진 + init_db + 마이그레이션 호출
│   ├── routers/
│   │   ├── pages.py             # / / setup HTML 라우트 (~58줄)
│   │   ├── api.py               # 도메인 통합 REST API (~5127줄, 다수 도메인 혼재)
│   │   └── ai.py                # AI/RAG 라우터 (~929줄, /api/ai/*)
│   ├── models/
│   │   ├── models.py            # ORM 19개 테이블
│   │   ├── schemas.py           # Pydantic 스키마
│   │   └── constants.py         # ROLE_*, SEED_TREATMENTS, ESWT_CODE
│   ├── migrations/              # m001~m013 (13개)
│   ├── services/
│   │   ├── auth.py              # 관리자 PBKDF2 + 세션 토큰
│   │   ├── backup.py            # 자동 백업 + 복원
│   │   ├── seed.py              # 시드 (Treatment 5개, SystemSetting, SmsSetting, SmsTemplate)
│   │   ├── sync.py              # 분산 노드 동기화 (sync_ops + 워커)
│   │   ├── ai/                  # AI 공용 + manual_qa wrapper
│   │   │   ├── provider.py / openai_client.py / anthropic_client.py
│   │   │   ├── pii.py / prompts.py / validators.py / ai_logging.py
│   │   │   ├── sms_draft.py / manual_qa.py / action_leave.py / date_resolver.py
│   │   │   ├── health.py        # 18-7 /api/ai/status 본체
│   │   │   ├── rag/             # 18-1~18-6 RAG 본체
│   │   │   ├── knowledge/       # 18-2~18-4 chunker / loader / indexer
│   │   │   └── vector/          # 18-5 embeddings / store / similarity
│   │   └── rag/                 # v1.3.3 keyword 인덱스 로더 (분리 전 잔존)
│   ├── static/                  # css/app.css + vendor JS (Alpine/FullCalendar/Sortable)
│   ├── templates/               # base.html / main.html / setup.html / server_info.html
│   └── tools/                   # db_check.py
├── tests/
│   ├── conftest.py              # 4단계 격리 + FakeProvider + SDK 차단 (269줄)
│   ├── harness/                 # 도메인별 하네스 헬퍼 (12 파일)
│   └── test_*.py                # pytest 테스트 40개 파일
├── docs/                        # AI/RAG 설계·체크리스트·릴리즈 노트
├── reports/ai_dev_loop/         # 18-0~18-8 세션별 리포트
├── knowledge/                   # 매뉴얼 + SMS 톤 가이드 (.md 10개) + _index.json
├── scripts/check_db_path.py     # 운영 DB 경로 안전 검사
├── tools/build_knowledge_index.py
├── dosu_clinic.spec             # PyInstaller 빌드 설정 (~194줄)
├── run.py / run_check.bat / run_tests.bat / run_lint.bat
├── pyproject.toml               # ruff + per-file-ignores app/**
├── requirements.txt / requirements-dev.txt
├── pytest.ini
└── CHANGELOG.txt / VERSION.txt / versions/
```

---

## 2. app/ 내부 주요 파일 역할

| 파일 | 줄수 | 역할 |
|---|---|---|
| [app/main.py](app/main.py) | 26 | FastAPI 앱 생성 + `init_db()` + `start_sync_worker()` + `start_auto_backup()` |
| [app/config.py](app/config.py) | 81 | `APP_VERSION`, `APP_BUILD_DATE`, `get_db_path` (DOSU_DB_PATH 우선), `load_config`, `resource_path` |
| [app/database.py](app/database.py) | 148 | `engine`, `SessionLocal`, `Base`, `init_db()` (create_all + legacy ALTER + 마이그레이션 + seed) |
| [app/routers/pages.py](app/routers/pages.py) | 58 | `/`, `/setup` HTML 렌더 + `_local_ips()` |
| [app/routers/api.py](app/routers/api.py) | 5127 | **거대 라우터** — 예약/환자/직원/휴무/치료항목/통계/SMS/관리자/백업/sync/엑셀변환 |
| [app/routers/ai.py](app/routers/ai.py) | 929 | AI/RAG 라우터 — settings/health/status/sms/manual/action |
| [app/models/models.py](app/models/models.py) | 464 | ORM 19개 (도메인 + AI/RAG + sync + audit) |
| [app/models/schemas.py](app/models/schemas.py) | 153 | Pydantic In/Out 스키마 |
| [app/models/constants.py](app/models/constants.py) | 24 | `ROLE_*`, `SEED_TREATMENTS`, `ESWT_CODE` |
| [app/services/auth.py](app/services/auth.py) | 119 | 관리자 PBKDF2 해시 + 인메모리 세션 + 5회 잠금 |
| [app/services/backup.py](app/services/backup.py) | 180 | `make_backup()`, `restore_latest()`, `restore_by_name()`, 타이머 스레드 |
| [app/services/seed.py](app/services/seed.py) | 208 | `seed_defaults()` (Treatment 5개 + SystemSetting + SmsSetting + SmsTemplate) |
| [app/services/sync.py](app/services/sync.py) | 212 | `record_op()`, `start_sync_worker()`, `_apply_op()` last-write-wins |
| [app/services/ai/manual_qa.py](app/services/ai/manual_qa.py) | 78 | wrapper — 본체는 `rag.pipeline` |
| [app/services/ai/health.py](app/services/ai/health.py) | 563 | 18-7 `/api/ai/status` 응답 본체 |
| [app/services/ai/sms_draft.py](app/services/ai/sms_draft.py) | 469 | LLM 기반 SMS 초안 |
| [app/services/ai/action_leave.py](app/services/ai/action_leave.py) | 917 | 자연어 휴무 등록 (parse/preview/execute + HMAC) |
| [app/services/ai/rag/pipeline.py](app/services/ai/rag/pipeline.py) | 295 | manual_search / manual_ask 본체 + `LOW_SCORE_THRESHOLD=2` |
| [app/services/ai/rag/retriever.py](app/services/ai/rag/retriever.py) | 438 | hybrid retriever (keyword + vector) |
| [app/services/ai/rag/confidence.py](app/services/ai/rag/confidence.py) | 311 | `HIGH/LOW/LLM_CALL_THRESHOLD` 0.7/0.3/0.3 |
| [app/services/ai/rag/reranker.py](app/services/ai/rag/reranker.py) | 326 | 18-6 reranker |
| [app/services/ai/knowledge/indexer.py](app/services/ai/knowledge/indexer.py) | 543 | reindex (knowledge_chunks 영속화 + lazy vector hook) |
| [app/services/ai/knowledge/chunker.py](app/services/ai/knowledge/chunker.py) | 297 | 18-3 결정적 chunker |
| [app/services/ai/vector/embeddings.py](app/services/ai/vector/embeddings.py) | 397 | EmbeddingProvider 추상 + FakeEmbeddingProvider + `QUERY_MIN_CHARS=2` |
| [app/services/ai/vector/store.py](app/services/ai/vector/store.py) | 279 | knowledge_vectors upsert/find |
| [app/services/rag/search.py](app/services/rag/search.py) | 129 | v1.3.3 keyword 인덱스 로더 (분리 전 코드, /api/ai/health에서 직접 import) |

---

## 3. 현재 API router 구조

### 3-1. `/api` ([app/routers/api.py](app/routers/api.py)) — 도메인 통합

| 엔드포인트 | 줄 | 도메인 | 메모 |
|---|---|---|---|
| `GET /api/admin/status` | 224 | 관리자 | 첫 실행 비밀번호 변경 여부 |
| `POST /api/admin/login` | 232 | 관리자 | PBKDF2 + 5회 잠금 |
| `POST /api/admin/logout` | 247 | 관리자 |  |
| `POST /api/admin/change-password` | 253 | 관리자 |  |
| `GET /api/about` | 271 | 관리자 | APP_VERSION 등 |
| `POST /api/about/check-update` | 292 | 업데이트 |  |
| `POST /api/about/download-update` | 371 | 업데이트 |  |
| `POST /api/about/apply-update` | 509 | 업데이트 |  |
| `GET /api/about/update-log` | 623 | 업데이트 |  |
| `GET /api/config` | 669 | 관리자 |  |
| `GET /api/config/sync-secret` | 688 | 관리자 |  |
| `POST /api/config/regenerate-sync-secret` | 699 | 관리자 |  |
| `POST /api/config` | 712 | 관리자 |  |
| `POST /api/mode` | 744 | 관리자 |  |
| `GET /api/treatment-meta` | 858 | 치료항목 | 코드/단축어 메타 |
| `GET /api/treatments` | 865 | 치료항목 |  |
| `POST /api/treatments` | 881 | 치료항목 |  |
| `PUT /api/treatments/{tid}` | 922 | 치료항목 |  |
| `GET /api/treatments/{tid}/references` | 958 | 치료항목 |  |
| `DELETE /api/treatments/{tid}` | 982 | 치료항목 |  |
| `GET /api/employees` | 1009 | 직원 |  |
| `POST /api/employees/reorder` | 1021 | 직원 |  |
| `POST /api/employees` | 1033 | 직원 |  |
| `PUT /api/employees/{eid}` | 1050 | 직원 |  |
| `DELETE /api/employees/{eid}` | 1066 | 직원 |  |
| `GET /api/employee-leaves` | 1082 | 휴무 |  |
| `POST /api/employee-leaves` | 1121 | 휴무 |  |
| `DELETE /api/employee-leaves/{lid}` | 1133 | 휴무 |  |
| `POST /api/employee-leaves/bulk-set` | 1144 | 휴무 |  |
| `GET /api/therapists` | 1175 | 치료사 alias | role=therapist 필터 |
| `GET /api/therapist-leaves` | 1184 | 휴무 alias | `therapist_id`도 키로 반환 |
| `POST /api/therapist-leaves/bulk-set` | 1202 | 휴무 alias |  |
| `GET /api/patients` | 1280 | 환자 |  |
| `GET /api/patients/search` | 1301 | 환자 |  |
| `GET /api/patients/{pid}` | 1348 | 환자 |  |
| `POST /api/patients` | 1431 | 환자 |  |
| `PATCH /api/patients/{pid}/memo` | 1444 | 환자 |  |
| `PUT /api/patients/{pid}` | 1456 | 환자 |  |
| `DELETE /api/patients/{pid}` | 1474 | 환자 |  |
| `GET /api/patients/last-appointments` | 1487 | 환자 |  |
| `GET /api/patients/{pid}/manual-history-summary` | 1498 | 환자 |  |
| `GET /api/patients/{pid}/history` | 1525 | 환자 |  |
| `GET /api/appointments` | 1608 | 예약 |  |
| `POST /api/appointments` | 1621 | 예약 | 점심창 + 충돌 검사 |
| `PUT /api/appointments/{aid}` | 1680 | 예약 | 낙관적 락 (version) |
| `POST /api/appointments/{aid}/assign` | 1747 | 예약 | 담당자 변경 |
| `POST /api/appointments/{aid}/split-code` | 1794 | 예약 | 코드 분리 |
| `POST /api/appointments/{aid}/approve` | 1956 | 예약/완료체크 | done_count +N |
| `POST /api/appointments/{aid}/revert-approve` | 1982 | 예약/완료체크 | done_count -N |
| `POST /api/appointments/{aid}/cancel` | 2006 | 예약 |  |
| `DELETE /api/appointments/{aid}` | 2024 | 예약 |  |
| `GET /api/system-settings` | 2058 | 관리자 |  |
| `POST /api/system-settings` | 2074 | 관리자 |  |
| `GET /api/sync/pull` | 2098 | sync | X-Sync-Token |
| `POST /api/sync/push` | 2114 | sync |  |
| `POST /api/sync/now` | 2144 | sync |  |
| `GET /api/backup` | 2159 | 백업 |  |
| `POST /api/restore` | 2168 | 백업 | UploadFile + integrity_check |
| `POST /api/data-convert/preview` | 2683 | 환자/엑셀변환 |  |
| `POST /api/data-convert/apply` | 2753 | 환자/엑셀변환 |  |
| `GET /api/backup/list` | 2856 | 백업 |  |
| `POST /api/backup/now` | 2863 | 백업 |  |
| `GET /api/backup/dir` | 2873 | 백업 |  |
| `POST /api/backup/restore-latest` | 2878 | 백업 |  |
| `POST /api/backup/restore-by-name` | 2890 | 백업 |  |
| `GET /api/audit-logs` | 2907 | 관리자 |  |
| `GET /api/sms/setting` | 2927 | SMS |  |
| `POST /api/sms/setting` | 2941 | SMS |  |
| `GET /api/sms/tomorrow-targets` | 2998 | SMS |  |
| `GET /api/sms/templates` | 3047 | SMS |  |
| `POST /api/sms/templates` | 3054 | SMS |  |
| `PUT /api/sms/templates/{tid}` | 3084 | SMS |  |
| `DELETE /api/sms/templates/{tid}` | 3100 | SMS |  |
| `POST /api/sms/send` | 3225 | SMS | 외부 munjanara API 호출 |
| `GET /api/stats/by-therapist` | 3450 | 통계 |  |
| `GET /api/stats/manual-by-therapist` | 3560 | 통계 |  |
| `GET /api/stats/aggregate` | 3647 | 통계 |  |
| `GET /api/stats/daily-by-therapist` | 3758 | 통계 |  |
| `POST /api/manual-counts` | 3883 | 통계 | 수동 카운트 upsert |
| `GET /api/stats/summary` | 3983 | 통계 |  |
| `GET /api/stats/by-hour` | 4057 | 통계 |  |
| `GET /api/stats/by-weekday` | 4106 | 통계 |  |
| `GET /api/stats/by-treatment` | 4159 | 통계 |  |
| `GET /api/stats/daily` | 4214 | 통계 |  |
| `GET /api/export/manual-schedule.xlsx` | 4333 | 통계/엑셀 |  |
| `GET /api/export/stats.xlsx` | 4576 | 통계/엑셀 |  |

> 합계: **86개 엔드포인트** (`grep -cE "^@router\." app/routers/api.py` 실측) 가 단일 `api.py` 안에 도메인 혼재 상태로 존재. 위 표는 주요 라인만 발췌 — 상세 라인 매칭은 `grep -nE "^@router\." app/routers/api.py` 결과와 1:1 대조하라.

### 3-2. `/api/ai` ([app/routers/ai.py](app/routers/ai.py))

| 엔드포인트 | 줄 | 비고 |
|---|---|---|
| `GET /api/ai/health` | 138 | admin 전용 9키 |
| `GET /api/ai/health/public` | 167 | 인증 불필요 4키 |
| `GET /api/ai/status` | 187 | 18-7 admin 9 top-level |
| `GET /api/ai/providers` | 228 | admin |
| `GET /api/ai/settings` | 243 | admin (api_key 마스킹) |
| `PUT /api/ai/settings` | 250 | admin (AuditLog 기록) |
| `POST /api/ai/sms/validate` | 366 | 결정론적 검증 (LLM 미사용) |
| `POST /api/ai/sms/draft` | 416 | LLM 호출 |
| `POST /api/ai/manual/search` | 609 | 키워드 RAG (LLM 미사용) |
| `POST /api/ai/manual/ask` | 645 | RAG + LLM |
| `POST /api/ai/action/parse` | 874 | 자연어 → JSON (디버그) |
| `POST /api/ai/action/preview` | 889 | LLM + 매칭 + HMAC 토큰 |
| `POST /api/ai/action/execute` | 900 | TOCTOU + EmployeeLeave upsert |

### 3-3. HTML 라우트 ([app/routers/pages.py](app/routers/pages.py))

| 엔드포인트 | 줄 | 비고 |
|---|---|---|
| `GET /` | 44 | mode 미정이면 /setup 으로 redirect |
| `GET /setup` | 53 | 첫 실행 셋업 화면 |

---

## 4. 현재 DB model 구조

[app/models/models.py](app/models/models.py) 안에 ORM **19개** 정의 (라인 표기는 모델 클래스 시작 줄). 실측: `grep -cE "^class \w+\(Base\)" app/models/models.py` = 19.

| 모델 | 라인 | 테이블 | 도메인 | 비고 |
|---|---|---|---|---|
| `Employee` | 22 | `employees` | 직원/치료사 | role(`doctor`/`therapist`), `can_eswt`, `can_manual`, `hire_date` |
| `EmployeeLeave` | 43 | `employee_leaves` | 휴무 | `(employee_id, leave_date)` UNIQUE, `leave_kind` (annual/monthly) |
| `Treatment` | 58 | `treatments` | 치료항목 | `count_increment`(=1), `price`, `incentive_pct`/`incentive_amount` |
| `Patient` | 90 | `patients` | 환자 | `gender`, name/phone/chart_no INDEX |
| `PatientTreatmentCount` | 110 | `patient_treatment_counts` | 환자/완료체크 | `(patient_id, treatment_id)` UNIQUE, `rx_count`/`done_count` |
| `Appointment` | 134 | `appointments` | 예약 | `treatment_codes` JSON, `version` (낙관적 락), `status` |
| `TreatmentAssignment` | 165 | `treatment_assignments` | 예약 | `(appointment_id, treatment_code)` UNIQUE, `handler_id` |
| `SystemSetting` | 182 | `system_settings` | 관리자/백업 | `auto_backup_*`, `manual_slot_limit`, `sms_template`(legacy) |
| `AuditLog` | 194 | `audit_logs` | 관리자 | actor/action/entity_id/detail |
| `SyncOp` | 205 | `sync_ops` | sync | append-only |
| `ManualCount` | 216 | `manual_counts` | 통계 | `(count_date, therapist_id, treatment_code)` UNIQUE |
| `SmsSetting` | 236 | `sms_settings` | SMS | munjanara_id/key/pw, sender_phone, api_url |
| `SmsLog` | 252 | `sms_logs` | SMS | 발송 이력 |
| `SmsTemplate` | 263 | `sms_templates` | SMS | sort_order=1이 기본 템플릿 |
| `AiSetting` | 280 | `ai_settings` | AI | enabled, provider, model, api_key, max_tokens, temperature, pii_guard_enabled |
| `AiUsageLog` | 304 | `ai_usage_logs` | AI | feature/outcome/error_detail/prompt_hash/response_hash 등 (m008 확장) |
| `KnowledgeChunk` | 360 | `knowledge_chunks` | RAG (m012) | `(doc_id, chunk_index)` UNIQUE |
| `KnowledgeIndexRun` | 388 | `knowledge_index_runs` | RAG (m012) | reindex 이력 |
| `KnowledgeVector` | 432 | `knowledge_vectors` | RAG (m013) | `(chunk_id, provider, model)` UNIQUE, ON DELETE CASCADE |

### 4-1. 마이그레이션 (m001~m013)

| 번호 | 파일 | 내용 |
|---|---|---|
| m001 | `m001_baseline.py` | 베이스라인 (테이블 생성 위임) |
| m002 | `m002_add_gender.py` | `patients.gender` |
| m003 | `m003_add_api_url.py` | `sms_settings.api_url` |
| m004 | `m004_add_indexes.py` | 인덱스 |
| m005 | `m005_treatment_price_incentive.py` | `treatments.price/incentive_*` |
| m006 | `m006_manual_counts.py` | `manual_counts` 테이블 |
| m007 | `m007_ai_settings.py` | `ai_settings` 시드 (enabled=0) |
| m008 | `m008_ai_usage_log_extended.py` | `ai_usage_logs` 확장 컬럼 |
| m009 | `m009_employee_leave_kind.py` | `employee_leaves.leave_kind` |
| m010 | `m010_employee_hire_date.py` | `employees.hire_date` |
| m011 | `m011_employee_leave_unique.py` | `(employee_id, leave_date)` UNIQUE |
| m012 | `m012_knowledge_chunks.py` | `knowledge_chunks` + `knowledge_index_runs` |
| m013 | `m013_knowledge_vectors.py` | `knowledge_vectors` |

→ 다음 마이그레이션은 **m014부터** (m001~m013 diff 0).

---

## 5. static / UI 구조

| 항목 | 위치 | 줄/크기 | 비고 |
|---|---|---|---|
| 메인 페이지 | [app/templates/main.html](app/templates/main.html) | 7331줄 | Jinja + Alpine + 인라인 `<script>` 521~7330 (~6800줄 JS) |
| 셋업 화면 | [app/templates/setup.html](app/templates/setup.html) | 43줄 | 첫 실행 |
| 베이스 레이아웃 | [app/templates/base.html](app/templates/base.html) | 23줄 |  |
| 서버 정보 | [app/templates/server_info.html](app/templates/server_info.html) | 18줄 |  |
| CSS | [app/static/css/app.css](app/static/css/app.css) | 3626줄 |  |
| Vendor JS | [app/static/vendor/](app/static/vendor/) | 3 파일 | Alpine 3.14.1 / FullCalendar 6.1.15 / Sortable 1.15.2 |

### 5-1. main.html 탭 구조

| 탭 ID | 줄 | 도메인 |
|---|---|---|
| `tab-reserve` | 41 | 예약 (FullCalendar) |
| `tab-patients` | 89 | 환자 관리 |
| `tab-therapists` | 110 | 직원/치료사 |
| `tab-sms` | 206 | 예약 문자 |
| `tab-ai-manual` | 330 | AI 매뉴얼 Q&A |
| `tab-admin` | 377 | 관리자 (mode=main 일 때만 표시) |

> JS 인라인 블록은 단일 `<script>` 521~7330 안에 모든 탭 핸들러가 혼재. 외부 JS 파일 분리 안 됨.

---

## 6. 현재 테스트 구조

### 6-1. 테스트 파일 (40 파일, 합 ~10770 줄)

| 분류 | 파일 | 줄수 |
|---|---|---|
| AI/RAG (18-0~18-8) | `test_full_harness.py` `test_ai_full_harness.py` `test_rag_pipeline.py` `test_rag_safety.py` `test_ai_safety_harness.py` `test_ai_manual_rag_harness.py` `test_ai_manual_rag_contract.py` `test_ai_contract_manual.py` `test_local_only_mode.py` `test_ai_chunker_harness.py` `test_ai_reindex_harness.py` `test_ai_vector_harness.py` `test_hybrid_retriever.py` `test_ai_assist_mode.py` `test_ai_health_status.py` `test_admin_ui_smoke.py` | 4194 |
| 기존 AI (v1.3.3 이전) | `test_ai_sms_validate.py` `test_ai_sms_draft.py` `test_ai_sms_draft_hallucination.py` `test_ai_action_leave.py` `test_ai_logging.py` `test_ai_hallucination.py` `test_ai_manual_qa.py` `test_ai_health_public.py` | 2724 |
| 비-AI 기능 | `test_appointment_rules.py` `test_employee_*` 4개 `test_stats_counts.py` `test_therapist_leave.py` `test_admin_auth_required.py` `test_db_restore_safety.py` `test_graceful_shutdown.py` `test_migration_spec_discovery.py` `test_smoke.py` `test_sms_secret_masking.py` `test_update_log.py` `test_updater_invocation.py` | ~1900 |
| PyInstaller (18-8) | `test_pyinstaller_hidden_imports.py` | 370 |

전체: **529 passed, 1 skipped, 7 xfailed** (18-8 baseline).

### 6-2. 테스트 격리 정책 ([tests/conftest.py](tests/conftest.py))

import-time 4단계 격리:
1. `APPDATA` → `tests/temp/appdata_<uuid>/`
2. `DOSU_DB_PATH` → `tests/temp/test_clinic_<uuid>.db`
3. `start_sync_worker` / `start_auto_backup` 람다 no-op 교체
4. `app.main` import (init_db 자동 실행)

추가 안전망:
- `tests.harness.db_guard.assert_safe_db_path()` 2회 (import-time + session fixture)
- `_block_sdk_modules()` — openai/anthropic SDK 클래스를 RuntimeError 로 교체
- `FakeProvider` (line 112) — 호출 기록은 `self.calls: list` (no `call_count`)

---

## 7. 현재 하네스 구조

[tests/harness/](tests/harness/) — 12 모듈 (`harness/*.py` 합 1420 줄, `wc -l tests/harness/*.py | tail -1`).

| 파일 | 줄 | 역할 |
|---|---|---|
| `db_guard.py` | 59 | `assert_safe_db_path()` — 운영 DB 경로 차단 |
| `seed_data.py` | 168 | 세션 스코프 시드 (직원/환자/휴무) |
| `helpers.py` | 64 | 공용 유틸 |
| `fake_provider.py` | 61 | conftest의 FakeProvider 외 추가 stub |
| `contract.py` | 113 | 응답 키 계약 단언 (manual/search/ask) |
| `rag_harness.py` | 52 | 18-0 RAG 검색 단언 |
| `safety_harness.py` | 73 | 18-0 PII/할루시네이션 단언 |
| `chunk_harness.py` | 207 | 18-3 chunker 결정성/메타데이터 |
| `reindex_harness.py` | 125 | 18-4 reindex skip/upsert/실패 보존 |
| `vector_harness.py` | 188 | 18-5 embedding/store/local_only |
| `hybrid_harness.py` | 310 | 18-6 keyword+vector 결합 |

---

## 8. 예약 관련 코드 위치

| 항목 | 위치 |
|---|---|
| 모델 | [app/models/models.py:134](app/models/models.py:134) `Appointment`, [app/models/models.py:165](app/models/models.py:165) `TreatmentAssignment` |
| 스키마 | [app/models/schemas.py:99](app/models/schemas.py:99) `AppointmentIn`/`AppointmentUpdate`/`AssignmentIn`/`AssignmentChange`/`ApproveAction`/`CancelAction` |
| 라우터 | [app/routers/api.py:1608-2057](app/routers/api.py:1608) (list/create/update/assign/split-code/approve/revert-approve/cancel/delete) |
| 점심창 검증 | [app/routers/api.py:64](app/routers/api.py:64) `_lunch_window`, [app/routers/api.py:87](app/routers/api.py:87) `_check_lunch_block` |
| 코드 파싱 | [app/routers/api.py:129](app/routers/api.py:129) `_parse_codes` |
| 직렬화 | [app/routers/api.py:186](app/routers/api.py:186) `_serialize_appointment` |
| 낙관적 락 | [app/routers/api.py:1664](app/routers/api.py:1664) `_check_version`, [app/routers/api.py:1676](app/routers/api.py:1676) `_bump_version` |
| sync 로깅 | [app/services/sync.py](app/services/sync.py) `record_op("appointment", ...)` (api.py 의 `_log()` 가 위임) |
| 회귀 테스트 | `tests/test_appointment_rules.py` (232줄) |
| UI | [app/templates/main.html:41-88](app/templates/main.html:41) (예약 탭 + FullCalendar) |

---

## 9. 환자 관련 코드 위치

| 항목 | 위치 |
|---|---|
| 모델 | [app/models/models.py:90](app/models/models.py:90) `Patient`, [app/models/models.py:110](app/models/models.py:110) `PatientTreatmentCount` |
| 스키마 | [app/models/schemas.py:75](app/models/schemas.py:75) `PatientCountIn`, [app/models/schemas.py:82](app/models/schemas.py:82) `PatientIn` |
| 라우터 | [app/routers/api.py:1280-1607](app/routers/api.py:1280) (list/search/get/create/update/memo/delete/last-appointments/manual-history/history) |
| 카운트 적용 | [app/routers/api.py:1213](app/routers/api.py:1213) `_patient_counts_dict`, [app/routers/api.py:1250](app/routers/api.py:1250) `_apply_patient_counts` |
| 환자 직렬화 | [app/routers/api.py:1235](app/routers/api.py:1235) `_patient_to_dict`, [app/routers/api.py:1357](app/routers/api.py:1357) `_serialize_patients_bulk` |
| 중복 검사 | [app/routers/api.py:1408](app/routers/api.py:1408) `_check_patient_duplicate` |
| 엑셀 변환 | [app/routers/api.py:2258-2855](app/routers/api.py:2258) (data-convert/preview, data-convert/apply) |
| UI | [app/templates/main.html:89-109](app/templates/main.html:89) (환자 탭) |

---

## 10. 치료사 / 직원 관련 코드 위치

| 항목 | 위치 |
|---|---|
| 모델 | [app/models/models.py:22](app/models/models.py:22) `Employee` (의사/치료사 통합, `role` 컬럼) |
| 스키마 | [app/models/schemas.py:7](app/models/schemas.py:7) `EmployeeIn` |
| 직렬화 | [app/routers/api.py:169](app/routers/api.py:169) `_serialize_employee` |
| 라우터 (직원) | [app/routers/api.py:1009-1079](app/routers/api.py:1009) (list/reorder/create/update/delete) |
| 라우터 (치료사 alias) | [app/routers/api.py:1175](app/routers/api.py:1175) `GET /api/therapists`, [app/routers/api.py:1184](app/routers/api.py:1184) `GET /api/therapist-leaves`, [app/routers/api.py:1202](app/routers/api.py:1202) `POST /api/therapist-leaves/bulk-set` |
| 회귀 테스트 | `tests/test_employee_*` (4 파일) `tests/test_employee_leave_*` |
| UI | [app/templates/main.html:110-205](app/templates/main.html:110) (직원 탭) |

---

## 11. 휴무 관련 코드 위치

| 항목 | 위치 |
|---|---|
| 모델 | [app/models/models.py:43](app/models/models.py:43) `EmployeeLeave` (`(employee_id, leave_date)` UNIQUE) |
| 스키마 | [app/models/schemas.py:24](app/models/schemas.py:24) `EmployeeLeaveIn` |
| 라우터 (직접) | [app/routers/api.py:1082-1170](app/routers/api.py:1082) (list/create/delete/bulk-set) |
| 라우터 (alias) | [app/routers/api.py:1184-1208](app/routers/api.py:1184) (`/api/therapist-leaves/*`) |
| 단일 진실원천 헬퍼 | [app/routers/api.py:1098](app/routers/api.py:1098) `_upsert_employee_leave_core` (AI 자연어 휴무 등록도 같은 헬퍼 사용) |
| AI 자연어 휴무 | [app/services/ai/action_leave.py](app/services/ai/action_leave.py) (917줄) — parse/preview/execute + HMAC 토큰 + TOCTOU |
| AI 라우터 | [app/routers/ai.py:874](app/routers/ai.py:874) action/parse, [app/routers/ai.py:889](app/routers/ai.py:889) preview, [app/routers/ai.py:900](app/routers/ai.py:900) execute |
| 회귀 테스트 | `tests/test_employee_leave_unique.py` `tests/test_employee_leave_kind.py` `tests/test_therapist_leave.py` `tests/test_ai_action_leave.py` (1232줄) |

---

## 12. 치료항목 관련 코드 위치

| 항목 | 위치 |
|---|---|
| 모델 | [app/models/models.py:58](app/models/models.py:58) `Treatment` (`count_increment=1`, price/incentive) |
| 스키마 | [app/models/schemas.py:39](app/models/schemas.py:39) `TreatmentIn`/`TreatmentOut` |
| 시드 데이터 | [app/models/constants.py:14](app/models/constants.py:14) `SEED_TREATMENTS` (5개: injection/cartilage/eswt/manual30/manual60), [app/models/constants.py:24](app/models/constants.py:24) `ESWT_CODE` |
| 시드 적용 | [app/services/seed.py:23](app/services/seed.py:23) `_seed_treatments` |
| 라우터 | [app/routers/api.py:858-1008](app/routers/api.py:858) (treatment-meta/treatments CRUD/references) |
| 직렬화 | [app/routers/api.py:767](app/routers/api.py:767) `_serialize_treatment`, [app/routers/api.py:786](app/routers/api.py:786) `_normalize_incentive` |
| 코드 분류 | [app/routers/api.py:148-168](app/routers/api.py:148) `_existing_codes_set`/`_doctor_codes_set`/`_therapist_codes_set`/`_therapist_only_codes_set` |
| 메타 빌더 | [app/routers/api.py:816](app/routers/api.py:816) `_build_treatment_meta` |
| 매뉴얼 분류 (통계) | [app/routers/api.py:3732](app/routers/api.py:3732) `_get_manual_treatment_rows`, [app/routers/api.py:3752](app/routers/api.py:3752) `_get_manual_therapy_codes` |

---

## 13. 완료체크 관련 코드 위치

| 항목 | 위치 |
|---|---|
| 모델 | [app/models/models.py:110](app/models/models.py:110) `PatientTreatmentCount` (`done_count`, `rx_count`) |
| 카운트 증감 헬퍼 | [app/routers/api.py:1934](app/routers/api.py:1934) `_bump_patient_count` (Lazy 생성, 0 미만 방지) |
| Approve | [app/routers/api.py:1956-1981](app/routers/api.py:1956) `approve_appointment` (treatment_codes 별로 +N) |
| Revert approve | [app/routers/api.py:1982-2005](app/routers/api.py:1982) `revert_approve` (-N) |
| 적용 입력 | [app/routers/api.py:1250](app/routers/api.py:1250) `_apply_patient_counts` (PUT 환자 시) |
| 카운트 직렬화 | [app/routers/api.py:1213](app/routers/api.py:1213) `_patient_counts_dict` |
| 회귀 테스트 | `tests/test_appointment_rules.py` `tests/test_stats_counts.py` |

> **manual60 정책**: `count_increment=1` ([app/models/constants.py:20](app/models/constants.py:20)). CLAUDE.md 명시 — 절대 2로 되돌리지 않을 것.

---

## 14. 통계 관련 코드 위치

| 항목 | 위치 |
|---|---|
| 모델 (수동 카운트) | [app/models/models.py:216](app/models/models.py:216) `ManualCount` |
| 라우터 | [app/routers/api.py:3450-4332](app/routers/api.py:3450) (8개 stats GET + manual-counts POST) |
| 범위 헬퍼 | [app/routers/api.py:3944](app/routers/api.py:3944) `_resolve_stats_range`, [app/routers/api.py:3971](app/routers/api.py:3971) `_date_list` |
| 매뉴얼 분류 | [app/routers/api.py:3732](app/routers/api.py:3732) `_get_manual_treatment_rows`, [app/routers/api.py:3752](app/routers/api.py:3752) `_get_manual_therapy_codes` |
| 엑셀 export | [app/routers/api.py:4333](app/routers/api.py:4333) `export_manual_schedule` (`/api/export/manual-schedule.xlsx`), [app/routers/api.py:4576](app/routers/api.py:4576) `export_stats_xlsx` |
| 색상 유틸 | [app/routers/api.py:4316](app/routers/api.py:4316) `_lighten_hex`, [app/routers/api.py:5115](app/routers/api.py:5115) `_lighten_hex_inner` |
| 회귀 테스트 | `tests/test_stats_counts.py` (162줄) |

---

## 15. 문자 / SMS 관련 코드 위치

| 항목 | 위치 |
|---|---|
| 모델 | [app/models/models.py:236](app/models/models.py:236) `SmsSetting`, [app/models/models.py:252](app/models/models.py:252) `SmsLog`, [app/models/models.py:263](app/models/models.py:263) `SmsTemplate` |
| 라우터 (설정) | [app/routers/api.py:2927-2997](app/routers/api.py:2927) sms/setting GET/POST |
| 라우터 (대상자) | [app/routers/api.py:2998](app/routers/api.py:2998) sms/tomorrow-targets |
| 라우터 (템플릿) | [app/routers/api.py:3047-3114](app/routers/api.py:3047) sms/templates CRUD |
| 라우터 (발송) | [app/routers/api.py:3225](app/routers/api.py:3225) sms/send (외부 munjanara API 호출) |
| 시리얼라이즈 | [app/routers/api.py:3036](app/routers/api.py:3036) `_serialize_sms_template` |
| 전화/마스킹 | [app/routers/api.py:3115-3149](app/routers/api.py:3115) `_normalize_phone_for_sms`/`_is_valid_kr_mobile`/`_mask_phone_for_log` |
| 응답 디코딩 | [app/routers/api.py:3183](app/routers/api.py:3183) `_smart_decode_response` |
| 비밀 마스킹 | [app/routers/api.py:3160](app/routers/api.py:3160) `_sms_sanitize` |
| 시드 | [app/services/seed.py:56](app/services/seed.py:56) `_seed_sms_setting`, [app/services/seed.py:63](app/services/seed.py:63) `_seed_sms_template` |
| AI SMS 검증 | [app/routers/ai.py:366](app/routers/ai.py:366) `/api/ai/sms/validate` (LLM 미사용) |
| AI SMS 초안 | [app/routers/ai.py:416](app/routers/ai.py:416) `/api/ai/sms/draft` (LLM 호출) — [app/services/ai/sms_draft.py](app/services/ai/sms_draft.py) (469줄) |
| AI 검증 로직 | [app/services/ai/validators.py](app/services/ai/validators.py) (285줄) |
| 회귀 테스트 | `tests/test_ai_sms_validate.py` `tests/test_ai_sms_draft.py` `tests/test_ai_sms_draft_hallucination.py` `tests/test_sms_secret_masking.py` |

---

## 16. 관리자 설정 관련 코드 위치

| 항목 | 위치 |
|---|---|
| 인증 모듈 | [app/services/auth.py](app/services/auth.py) (119줄) — PBKDF2 + 8h 세션 + 5회 잠금 |
| 의존성 | [app/routers/api.py:34](app/routers/api.py:34) `require_admin`, [app/routers/api.py:40](app/routers/api.py:40) `require_admin_or_sync_token` |
| AI 의존성 | [app/routers/ai.py:51](app/routers/ai.py:51) `require_admin` (별도 정의) |
| 라우터 (admin) | [app/routers/api.py:224-269](app/routers/api.py:224) status/login/logout/change-password |
| 라우터 (about/업데이트) | [app/routers/api.py:271-668](app/routers/api.py:271) about/check-update/download-update/apply-update/update-log |
| 라우터 (config) | [app/routers/api.py:669-743](app/routers/api.py:669) config GET/POST + sync-secret |
| 라우터 (mode) | [app/routers/api.py:744](app/routers/api.py:744) mode |
| 시스템 설정 | [app/models/models.py:182](app/models/models.py:182) `SystemSetting`, [app/routers/api.py:2058-2096](app/routers/api.py:2058) get/set |
| 감사 로그 | [app/routers/api.py:110](app/routers/api.py:110) `audit`, [app/models/models.py:194](app/models/models.py:194) `AuditLog`, [app/routers/api.py:2907](app/routers/api.py:2907) list_audit_logs |

---

## 17. 백업 / 복구 관련 코드 위치

| 항목 | 위치 |
|---|---|
| 서비스 | [app/services/backup.py](app/services/backup.py) (180줄) — `make_backup`, `restore_latest`, `restore_by_name`, 타이머 스레드 |
| 시작 시 호출 | [app/main.py:22](app/main.py:22) `start_auto_backup()` |
| 라우터 (직접) | [app/routers/api.py:2159-2167](app/routers/api.py:2159) GET /api/backup |
| 라우터 (UploadFile 복원) | [app/routers/api.py:2168-2256](app/routers/api.py:2168) POST /api/restore (integrity_check + atomic rename) |
| 라우터 (백업 관리) | [app/routers/api.py:2856-2906](app/routers/api.py:2856) backup/list / backup/now / backup/dir / restore-latest / restore-by-name |
| 백업 폴더 | [app/config.py:29](app/config.py:29) `get_backup_dir()` (`%APPDATA%\도수치료예약\backups\`) |
| 회귀 테스트 | `tests/test_db_restore_safety.py` (151줄) |

---

## 18. AI / RAG 관련 코드 위치

> 상세 스냅샷은 [docs/ai_rag_current_state.md](docs/ai_rag_current_state.md) 참조. 본 §은 19-P 분리 대상의 위치만 정리.

### 18-1. AI 라우터 ([app/routers/ai.py](app/routers/ai.py), 929줄)

13개 엔드포인트가 단일 파일에 혼재:
- 관리자: `health`, `health/public`, `status`, `providers`, `settings(GET/PUT)`
- SMS: `sms/validate`, `sms/draft`
- 매뉴얼 Q&A: `manual/search`, `manual/ask`
- 휴무 액션: `action/parse`, `action/preview`, `action/execute`

### 18-2. AI 서비스 모듈

| 모듈 | 위치 | 역할 |
|---|---|---|
| Provider 추상 | [app/services/ai/provider.py](app/services/ai/provider.py) | 113줄, factory `get_provider`, `KNOWN_PROVIDERS=("openai","anthropic","local")` |
| OpenAI | [app/services/ai/openai_client.py](app/services/ai/openai_client.py) | 58줄, lazy import |
| Anthropic | [app/services/ai/anthropic_client.py](app/services/ai/anthropic_client.py) | 59줄 |
| PII | [app/services/ai/pii.py](app/services/ai/pii.py) | 127줄, `scan(text)` |
| 프롬프트 | [app/services/ai/prompts.py](app/services/ai/prompts.py) | 45줄 |
| 검증 (SMS) | [app/services/ai/validators.py](app/services/ai/validators.py) | 285줄 |
| 로깅 | [app/services/ai/ai_logging.py](app/services/ai/ai_logging.py) | 225줄 |
| SMS 초안 | [app/services/ai/sms_draft.py](app/services/ai/sms_draft.py) | 469줄 |
| 매뉴얼 Q&A wrapper | [app/services/ai/manual_qa.py](app/services/ai/manual_qa.py) | 78줄 |
| 자연어 휴무 | [app/services/ai/action_leave.py](app/services/ai/action_leave.py) | 917줄 |
| 날짜 파서 | [app/services/ai/date_resolver.py](app/services/ai/date_resolver.py) | 233줄 |
| 18-7 status | [app/services/ai/health.py](app/services/ai/health.py) | 563줄, `build_admin_status()` |

### 18-3. RAG 본체 (`app/services/ai/rag/`)

| 모듈 | 줄 |
|---|---|
| `schemas.py` | 231 |
| `prompts.py` | 54 |
| `safety.py` | 50 |
| `retriever.py` | 438 |
| `pipeline.py` | 295 (`LOW_SCORE_THRESHOLD=2`) |
| `reranker.py` | 326 |
| `confidence.py` | 311 (`HIGH=0.7`, `LOW=0.3`, `LLM_CALL=0.3`) |

### 18-4. Knowledge (`app/services/ai/knowledge/`)

| 모듈 | 줄 |
|---|---|
| `loader.py` | 128 |
| `normalizer.py` | 154 |
| `chunker.py` | 297 |
| `keyword_index.py` | 103 |
| `indexer.py` | 543 (vector lazy import 포함) |

### 18-5. Vector (`app/services/ai/vector/`)

| 모듈 | 줄 |
|---|---|
| `embeddings.py` | 397 (`QUERY_MIN_CHARS=2`) |
| `store.py` | 279 |
| `similarity.py` | 116 |

### 18-6. Legacy keyword RAG (`app/services/rag/`)

- [app/services/rag/search.py](app/services/rag/search.py) (129줄) — `_load_index()` 가 [app/routers/ai.py:43](app/routers/ai.py:43) 에서 직접 import 되어 `health.knowledge_doc_count` 산정에 사용. **18-2에서 본체는 분리됐지만 본 모듈은 잔존**.

### 18-7. 지식 베이스

[knowledge/](knowledge/):
- `manuals/` 6개 (.md): ai_settings / backup / munjanara_error / no_therapist / sms_compose / therapist_leave
- `sms_guides/` 4개 (.md): tone_confirm / tone_noshow / tone_reminder / tone_reschedule
- `_index.json` — `tools/build_knowledge_index.py` 산출

---

## 19. 코드가 섞여 있는 위험 구간

> 19-P 단위화 리팩토링의 핵심 분리 대상. 한 파일에 다수 도메인 혼재.

### 19-1. [app/routers/api.py](app/routers/api.py) (5127줄, 86개 엔드포인트)

| 위험 항목 | 라인 | 영향 도메인 |
|---|---|---|
| 단일 라우터에 ~80 엔드포인트 | 1-5127 | 모든 비-AI 도메인 |
| 점심창 헬퍼 | 64-107 | 예약 |
| 공용 직렬화 함수 (`_serialize_*`) | 169-209, 767, 1213, 1235, 1357, 3036 | 직원/예약/환자/치료항목/SMS |
| treatment 코드 분류 | 148-168 | 치료항목 ↔ 통계 ↔ 예약 ↔ SMS 모두 사용 |
| 환자 카운트 증감 (`_bump_patient_count`) | 1934-1953 | 예약 ↔ 환자 ↔ 통계 결합 |
| `_log()` (sync 위임) | 118-127 | 모든 CUD 도메인 |
| audit() (감사 로그) | 110-116 | 거의 모든 라우터 |
| 엑셀 변환 (data-convert/*) | 2258-2855 | 환자 ↔ 통계 ↔ 외부 입력 (~600줄) |
| 통계 + 엑셀 export | 4316-5115 | 통계 ↔ 디자인 색상 헬퍼 (~800줄) |
| `/api/restore` UploadFile | 2169-2255 | 백업 ↔ DB 엔진 lifecycle |
| therapist alias | 1175-1208 | 직원 ↔ 휴무 (응답 키 호환) |

### 19-2. [app/templates/main.html](app/templates/main.html) (7331줄)

- 단일 `<script>` (521-7330) 안에 모든 탭 JS 혼재 — 외부 분리 안 됨.
- 6개 탭 (예약/환자/직원/SMS/AI/관리자) 핸들러 + Alpine 데이터 + FullCalendar 콜백이 같은 스코프.
- AI 매뉴얼 Q&A JS는 5747-5793 (응답 키 5개 사용).

### 19-3. [app/routers/ai.py](app/routers/ai.py) (929줄)

- 13개 엔드포인트가 단일 파일 — 도메인별로는 (settings/health/status), (sms), (manual), (action) 4개로 나뉨.
- `_action_leave_provider`, `_get_or_create_setting`, `_serialize_setting`, `_mask_api_key`, `_check_sdk` 등 다수의 비공개 헬퍼 혼재.

### 19-4. [app/services/ai/action_leave.py](app/services/ai/action_leave.py) (917줄)

- 자연어 파싱 + LLM 호출 + DB 매칭 + HMAC 토큰 + TOCTOU 검사 + 휴무 등록을 단일 파일에서 관리. 분리 시 토큰/락 정책 변경 위험.

### 19-5. [app/services/ai/health.py](app/services/ai/health.py) (563줄)

- 18-7 신설로 단일 파일이지만 다수 모듈 (provider/settings/vector/knowledge/AiUsageLog) 의 상태를 한 곳에서 집계. 응답 9키 후방호환.

### 19-6. RAG 모듈 간 의존

- `manual_qa.py` (wrapper) → `rag/pipeline.py` → `rag/retriever.py` → `rag/reranker.py` + `rag/confidence.py` + `vector/store.py` + `knowledge/keyword_index.py`
- `knowledge/indexer.py` → `vector/*` lazy import (`_embed_chunks_into_vectors` 가 try/except 로 감쌈)
- 분리 시 lazy import 위치 변경하면 **vector 패키지 부재 환경 호환 깨짐**.

### 19-7. 호환 alias

- `/api/therapists`, `/api/therapist-leaves*` ([app/routers/api.py:1175-1208](app/routers/api.py:1175)) — `Employee` (role=therapist) 와 `EmployeeLeave` 의 응답에 `therapist_id` 키를 같이 반환.

---

## 20. 리팩토링 시 건드리면 위험한 파일

### 20-1. **수정 절대 금지** (이미 배포된 마이그레이션 + 격리 정책)

| 파일 | 이유 |
|---|---|
| `app/migrations/m001_*.py` ~ `m013_*.py` (13개) | 운영 환경에 이미 적용된 마이그레이션. m014부터 신규 추가만. |
| `tests/conftest.py` 의 4단계 격리 (line 32-75) | APPDATA / DOSU_DB_PATH / 워커 무력화 / SDK 차단. 약화 시 운영 DB 사고. |
| `tests/conftest.py:_block_sdk_modules` | 외부 LLM 호출 차단. 약화 시 비용/PII 사고. |
| `pyproject.toml`의 `app/**` per-file-ignores | CLAUDE.md 명시. 풀면 대량 포맷 변경 발생. |
| [app/models/constants.py](app/models/constants.py) `manual60` count_increment | CLAUDE.md 명시 — 1 그대로 유지. |
| `scripts/check_db_path.py` | 운영 DB 경로 안전 검사. 머지 게이트. |

### 20-2. **수정 시 응답 후방호환 깨짐 직격탄**

| 파일 | 이유 |
|---|---|
| [app/routers/ai.py](app/routers/ai.py) | manual/{search,ask}/health/health-public/status 응답 키 33개 후방호환. |
| [app/services/ai/manual_qa.py](app/services/ai/manual_qa.py) | `ask_manual_question(db, question, *, provider_override=)` 시그니처 보존. |
| [app/services/ai/rag/pipeline.py](app/services/ai/rag/pipeline.py) | `LOW_SCORE_THRESHOLD=2` 노출 + 응답 9키 본체. |
| [app/services/ai/rag/confidence.py](app/services/ai/rag/confidence.py) | HIGH/LOW/LLM_CALL 임계치. |
| [app/services/ai/health.py](app/services/ai/health.py) | `/api/ai/status` 9키 단일 진실원천. |
| [app/services/ai/pii.py](app/services/ai/pii.py) | `scan(text).cleaned/found/has_blocking` 반환형 의존 코드 다수. |
| [app/services/ai/provider.py](app/services/ai/provider.py) | `KNOWN_PROVIDERS`, `get_provider()`, `AiUnavailable`/`AiPiiBlocked` 예외 시그니처. |

### 20-3. **수정 시 PyInstaller 빌드 누락 위험**

| 파일 | 이유 |
|---|---|
| [dosu_clinic.spec](dosu_clinic.spec) | 18-8에서 추가한 hidden imports 17개 (rag/knowledge/vector/health) + collect_submodules 가드 + migrations 자동 글롭 + updater.bat post-build 복사. 18-8 baseline. ※ ORM 19개 vs hidden imports 17개는 서로 다른 카운트(모델 수 vs spec 추가분)이므로 혼동 주의. |
| [tests/test_pyinstaller_hidden_imports.py](tests/test_pyinstaller_hidden_imports.py) (370줄) | 53 tests — spec hidden imports 검증. 신규 모듈 분리 시 등록 필수. |

### 20-4. **수정 시 라우터/UI/통계가 깨질 수 있는 헬퍼**

| 파일/함수 | 이유 |
|---|---|
| [app/routers/api.py:148-168](app/routers/api.py:148) `_doctor_codes_set` 등 | 통계/예약/SMS가 동시 의존 |
| [app/routers/api.py:1098](app/routers/api.py:1098) `_upsert_employee_leave_core` | 휴무 라우터 + AI action_leave 가 같이 호출 |
| [app/routers/api.py:1934](app/routers/api.py:1934) `_bump_patient_count` | approve/revert-approve가 의존 |
| [app/routers/api.py:3732-3757](app/routers/api.py:3732) `_get_manual_treatment_rows` | 통계/예약/엑셀 export 가 의존 |
| [app/services/sync.py](app/services/sync.py) `ENTITY_MAP` (line 21) | 모든 도메인 모델 등록. 분리 시 sync 큐 호환 위험 |

### 20-5. **수정 시 백그라운드 워커가 운영 환경에서만 동작**

| 파일 | 이유 |
|---|---|
| [app/services/backup.py](app/services/backup.py) `start_auto_backup()` | 데몬 스레드. 테스트는 conftest 가 람다로 교체. |
| [app/services/sync.py](app/services/sync.py) `start_sync_worker()` | 분산 노드 push/pull 워커. 동상. |

---

## 21. 현재 구조에서 유지해야 할 API 응답 key / 호환 포인트

### 21-1. AI 응답 키 (절대 제거/이름변경/타입변경 X — 추가만 허용)

| 엔드포인트 | 키 셋 | 출처 |
|---|---|---|
| `POST /api/ai/manual/search` | `sources / masked_question / top_score` (3키) | [app/services/ai/rag/pipeline.py](app/services/ai/rag/pipeline.py) |
| `POST /api/ai/manual/ask` | `answer / sources / confidence / not_found / blocked / blocked_reason / guard_hits / top_score / masked_question` (9키) | 동상 |
| `sources[]` 항목 | `title / path / snippet` (3키) | 동상 |
| `GET /api/ai/health` (admin) | `enabled / provider / model / api_key_set / sdk_installed / sdk_errors / knowledge_doc_count / ready / version` (9키) | [app/routers/ai.py:154-164](app/routers/ai.py:154) |
| `GET /api/ai/health/public` | `enabled / ready / provider / api_key_set` (4키) | [app/routers/ai.py:179-184](app/routers/ai.py:179) |
| `GET /api/ai/status` (18-7) | `ai_mode / search_mode / version / ai_settings / vector_status / external_api / knowledge / prompt_versions / recent_ai_logs` (9키 top-level) | [app/services/ai/health.py](app/services/ai/health.py) `build_admin_status` |

→ **프론트가 실제 사용하는 manual_qa 키 5개**: `not_found`, `answer`, `confidence`, `sources[].title`, `sources[].path` ([app/templates/main.html:5747-5793](app/templates/main.html:5747))

### 21-2. 비-AI 응답 호환 alias

| 엔드포인트 | 호환 알리아스 | 출처 |
|---|---|---|
| `GET /api/therapists` | `Employee` role=therapist 필터 (직렬화는 `_serialize_employee`) | [app/routers/api.py:1175](app/routers/api.py:1175) |
| `GET /api/therapist-leaves` | `EmployeeLeave` 응답에 `therapist_id` 키 추가 (이중 키) | [app/routers/api.py:1184](app/routers/api.py:1184) |
| `POST /api/therapist-leaves/bulk-set` | `therapist_id` 필드 → `employee_id` 변환 | [app/routers/api.py:1202](app/routers/api.py:1202) |
| `POST /api/employee-leaves/bulk-set` | `item.therapist_id` 도 `employee_id` 로 인식 | [app/routers/api.py:1158](app/routers/api.py:1158) |

### 21-3. 모델 컬럼 보존 (rename 금지)

| 모델 | 보존 컬럼 |
|---|---|
| `AiSetting` | `enabled / provider / model / api_key / base_url / max_tokens / temperature / pii_guard_enabled` |
| `AiUsageLog` | `feature / outcome / error_detail / prompt_hash / response_hash / pii_filter_hits / hallucination_guard_hits / response_used / sms_sent` |
| `EmployeeLeave` | `(employee_id, leave_date)` UNIQUE + `leave_kind` (annual/monthly) |
| `Treatment` | `count_increment` (특히 manual60=1) |
| `Appointment` | `version` (낙관적 락), `treatment_codes` JSON |
| `PatientTreatmentCount` | `(patient_id, treatment_id)` UNIQUE + `rx_count`/`done_count` |
| `KnowledgeChunk` | `(doc_id, chunk_index)` UNIQUE |
| `KnowledgeVector` | `(chunk_id, provider, model)` UNIQUE + ON DELETE CASCADE |

### 21-4. 핵심 정책 상수 (변경은 별도 결정 + eval 측정 후)

| 상수 | 위치 | 값 |
|---|---|---|
| `LOW_SCORE_THRESHOLD` | [app/services/ai/rag/pipeline.py](app/services/ai/rag/pipeline.py) | 2 |
| `HIGH_THRESHOLD` / `LOW_THRESHOLD` | [app/services/ai/rag/confidence.py](app/services/ai/rag/confidence.py) | 0.7 / 0.3 |
| `LLM_CALL_THRESHOLD` | 동상 | 0.3 |
| `QUERY_MIN_CHARS` | [app/services/ai/vector/embeddings.py](app/services/ai/vector/embeddings.py) | 2 |
| `ERROR_DETAIL_DISPLAY_LIMIT` | [app/services/ai/health.py](app/services/ai/health.py) | 200 |
| `DEFAULT_RECENT_HOURS` / `_LIMIT` | 동상 | 24 / 5 |
| `SESSION_TTL_SEC` | [app/services/auth.py:8](app/services/auth.py:8) | 28800 (8h) |
| `MAX_FAILURES` / `LOCK_DURATION_SEC` | [app/services/auth.py:16-17](app/services/auth.py:16) | 5 / 300 |
| `KNOWN_PROVIDERS` | [app/services/ai/provider.py](app/services/ai/provider.py) | `("openai","anthropic","local")` |

### 21-5. PyInstaller spec hidden imports (이미 17개 추가됨, 18-8 baseline)

[dosu_clinic.spec](dosu_clinic.spec) 의 hidden imports 목록 (line 31-97). 19-P에서 새 모듈을 분리할 때마다 본 목록에 등록 필수. [tests/test_pyinstaller_hidden_imports.py](tests/test_pyinstaller_hidden_imports.py) 53 tests 가 검증.

### 21-6. FakeProvider / FakeEmbeddingProvider 컨벤션

- 호출 관찰: `len(provider.calls)` (별도 `call_count` 속성 없음)
- 위치: [tests/conftest.py:112](tests/conftest.py:112) `class FakeProvider`
- 외부 SDK 차단: [tests/conftest.py:_block_sdk_modules](tests/conftest.py:140) — openai/anthropic 클래스 RuntimeError 교체

---

## 22. "확인 필요" 항목

> 본 세션 (코드 수정 금지) 안에서 확인할 수 없거나, 19-P 진입 직전에 별도 검증이 필요한 항목.
>
> 19-P-1 Codex 검증 (2026-05-02) 결과 C-9/C-10/C-14/C-18 은 본 세션에서 이미 코드 그렙으로 확인된 항목이라 §22-A "확인 완료 / 19-P 의사결정 항목" 으로 분리했다.

| ID | 항목 | 사유 / 다음 검증 시점 |
|---|---|---|
| C-1 | 86개 라우터 엔드포인트별 프론트 사용 응답 키 표 | [app/templates/main.html](app/templates/main.html) 7331줄 JS 안에서 fetch 호출지를 전수 grep해야 함. 19-1 통계/19-3 예약 분리 직전에 도메인별로 별도 보강 필요. |
| C-2 | `/api/sms/send` 응답 키 후방호환 셋 | 발송 result/detail 등 SMS 탭이 표시. SMS 모듈 분리 직전에 별도 표 작성 필요. |
| C-3 | `/api/sms/draft` 응답 키 후방호환 셋 | LLM 호출 응답. 19-5 AI 라우터 분리 직전에 contract 테스트로 보강 필요. |
| C-4 | `/api/ai/action/{parse,preview,execute}` 응답 키 셋 | [app/routers/ai.py:858-928](app/routers/ai.py:858) 의 `_serialize_*_result` 정의는 있으나 프론트 사용 키 매트릭스는 미작성. 19-5 분리 직전 보강. |
| C-5 | `/api/about/check-update` 응답 키 셋 | 자동 업데이트 흐름. 19-2 관리자 모듈 분리 시 보강. |
| C-6 | `data-convert/preview`/`apply` 응답 키 셋 | 엑셀 변환 (~600줄). 19-1 환자 모듈 분리 직전 보강. |
| C-7 | 통계 8개 endpoint 응답 키 셋 | 통계 탭 + 엑셀 export. 19-1 통계 모듈 분리 직전 보강. |
| C-8 | `app/services/sync.py:ENTITY_MAP` 분리 영향 | 모듈 분리 시 sync 큐 entity 문자열 호환 깨짐 위험. 별도 ADR 필요. |
| C-11 | `update_log` 라우트 + `updater.bat` 결합 | [app/routers/api.py:613-668](app/routers/api.py:613) + [updater.bat](updater.bat) (9362B). 19-2 관리자 모듈 분리 시 PyInstaller post-build 영향 확인 필요. |
| C-12 | `tests/test_pyinstaller_hidden_imports.py` 의 `EXPECTED_18_X_MODULES` 19개 | 18-8 baseline. 19-P 단위화 후 신규 모듈 추가/이동 시마다 본 목록 동기화 필요. |
| C-13 | `app/templates/main.html` 의 외부 JS 분리 가능성 | 7331줄 단일 파일. 19-P 비-목표 (별도 UI 세션) — 본 리팩토링 기간 동안 무수정 유지. |
| C-15 | dosu_clinic.spec 의 `app.tools.db_check` 사용처 | hidden import 등록만 있고 실제 호출지 미확인. 모듈 이동/제거 시 영향 검증 필요. |
| C-16 | `_dc_*` (data-convert) 헬퍼의 분리 단위 | [app/routers/api.py:2276-2682](app/routers/api.py:2276) ~400줄. 19-1 환자 모듈 분리 시 `app/services/data_convert.py` 로 별도 분리 결정 필요. |
| C-17 | sync ENTITY 키 `treatment_assignment`/`patient_treatment_count`/`employee_leave` | 모듈 분리 후에도 동일 문자열 유지해야 외부 노드와 호환. |

> ID 비어 있는 C-9/C-10/C-14/C-18 은 §22-A 로 이동.

## 22-A. 확인 완료 / 19-P 의사결정 항목 (Codex 1차 검증 후 §22 에서 분리)

> 본 세션에서 코드 그렙으로 확인이 끝났지만 19-P 분리 단계에서 의사결정이 필요한 항목.

| ID | 항목 | 확인 결과 / 19-P 의사결정 |
|---|---|---|
| C-9 | [app/services/rag/search.py](app/services/rag/search.py) 잔존 모듈 | **확인 완료**: v1.3.3 keyword 인덱스 로더가 [app/routers/ai.py:43](app/routers/ai.py:43) `_load_kb_index` 에서 직접 import 됨. `health.knowledge_doc_count` 산정 + `/api/ai/health` 응답에 사용. ▶ 의사결정: 19-5 에서 `app/services/ai/knowledge/` 로 통합할지 / 잔존 유지할지. |
| C-10 | `knowledge/` 카테고리 결정 로직 | **확인 완료**: [app/services/rag/search.py:53](app/services/rag/search.py:53) `_build_runtime_index` 가 path 첫 segment ("manuals" / "sms_guides") 로 카테고리 추출. ▶ 의사결정: 신규 카테고리 추가 시 코드 동기화 절차 명문화. |
| C-14 | `manual_qa` wrapper 의 `_pipeline.run_manual_*` 호출지 | **확인 완료**: [app/services/ai/manual_qa.py:39-69](app/services/ai/manual_qa.py:39) 가 `manual_search()` / `ask_manual_question()` / `validate_answer()` 3개를 `_pipeline.run_*` 로 위임. wrapper 시그니처 (`provider_override=`) + 공개 상수 (`LOW_SCORE_THRESHOLD`, `_MANUAL_SYSTEM_PROMPT`) 보존. ▶ 의사결정: 19-5 라우터 분리 시 wrapper 시그니처 그대로 유지 필수. |
| C-18 | `/api/ai/status` 의 `recent_ai_logs.error_detail` 200자 컷 | **확인 완료**: §21-4 에 `ERROR_DETAIL_DISPLAY_LIMIT=200` 으로 이미 확정 기록. ▶ 의사결정: 19-5 분리 시 동일 cap 유지 필수 (응답 키 후방호환). |

---

## 23. 종합

- 단일 라우터 [app/routers/api.py](app/routers/api.py) (5127줄, **86개** endpoint, `grep -cE "^@router\." app/routers/api.py` 실측) 가 9개 도메인을 혼재 — 19-P 단위화의 핵심 분리 대상.
- [app/routers/ai.py](app/routers/ai.py) (929줄, 13 endpoint) 도 4개 부도메인 (settings/sms/manual/action) 혼재.
- AI/RAG 코드는 18-1~18-7 결과로 `rag/` `knowledge/` `vector/` 서브패키지 골격이 이미 잡혀 있음 — 19-P 에서 큰 추가 분리 불필요.
- 응답 키 후방호환은 33+개 키 셋 (manual/search 3 + manual/ask 9 + sources 3 + health 9 + health/public 4 + status 9) 이 명시적으로 잠겨 있음. 추가만 허용.
- 백그라운드 워커 (sync / backup) 는 [app/main.py](app/main.py) 에서 시작 — 테스트는 conftest 가 람다로 교체.
- 위험 결합 1순위: api.py 의 통계 ↔ 치료항목 ↔ 예약 ↔ 환자 카운트 헬퍼들 (`_doctor_codes_set`, `_get_manual_*`, `_bump_patient_count`, `_apply_patient_counts`).
- 위험 결합 2순위: AI action_leave (917줄) 의 `_upsert_employee_leave_core` 공유 — 19-2 휴무 분리 시 토큰/락 정책 보존 필수.
- 위험 결합 3순위: knowledge/indexer 의 vector lazy import — 19-5 분리 시 import 위치 변경하면 vector 패키지 부재 환경 호환 깨짐.
- 다음 문서: [docs/refactor/19_refactor_target_state.md](docs/refactor/19_refactor_target_state.md) (목표 구조) 또는 19-0 베이스라인 하네스 강화 체크리스트.

---

## 24. 2차 기준 문서 stale 주의 (Codex 1차 검증 후 추가)

본 문서의 2차 대조 기준으로 [docs/ai_rag_current_state.md](docs/ai_rag_current_state.md) 를 사용할 때 **stale 항목** 에 주의한다. 18-8 baseline 도달 이전(18-0 시점) 작성된 문서이므로 일부 사실이 v1.3.3 현재 상태와 어긋난다.

| stale 항목 위치 | 문서 표기 (작성 당시) | 현재 (v1.3.3 / m013) |
|---|---|---|
| §1-4 "마지막 마이그레이션" | `m011_employee_leave_unique.py` | **m013_knowledge_vectors.py** (m012/m013 추가됨) |
| §1-4 "다음 마이그레이션 번호" | `m012` | **m014** |
| §1-5-1 "FakeEmbeddingProvider는 현재 없음" | (18-5에서 신규 작성 필요) | **18-5에서 작성 완료** — `app/services/ai/vector/embeddings.py:FakeEmbeddingProvider` 존재 |
| §11 "마지막: m011 / 다음: m012" | 동상 | **마지막: m013 / 다음: m014** |

→ **19-P 검증 시 [docs/ai_rag_current_state.md](docs/ai_rag_current_state.md) 의 마이그레이션/FakeEmbeddingProvider 섹션은 stale**. 응답 키 셋 표 (§3-7), AiUsageLog 컬럼 (§1-4), FakeProvider 시그니처 (§1-5-1 후반), 안전 정책 (§6/§7) 등은 v1.3.3 현재와 일치하므로 그대로 사용 가능.
→ 본 문서 (`19_refactor_current_state.md`) 는 v1.3.3 / m013 / 18-8 baseline 기준으로 작성되었으므로 **마이그레이션·벡터 관련 사항은 본 문서가 우선**.
