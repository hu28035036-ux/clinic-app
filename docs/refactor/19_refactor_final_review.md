# 19-P-10 단위화 리팩토링 — 구조계획 최종 점검 (19_refactor_final_review)

> 19-P-1 ~ 19-P-9 (준비 단계 9개 문서) **최종 점검 + 19-0 진입 권고** 문서.
> 본 문서는 *최종 점검* 문서 — 코드 / 테스트 / migration / spec / UI / requirements 무수정.
> 본 문서는 사용자 양식 (§1 ~ §10) 정합. 19_refactor_final_check.md (cross-check 매트릭스 중심) 와 보완 관계.

## 0. 메타

- 작성일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed** ([reports/ai_dev_loop/18-8_test_report.md](../../reports/ai_dev_loop/18-8_test_report.md) + [reports/ai_dev_loop/19-0_test_report.md](../../reports/ai_dev_loop/19-0_test_report.md) 19-0 시점 재검증 100% 일치)
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 / 19-P-6 r1+r2 / 19-P-7 r3 / 19-P-8 r1 / 19-P-9 r1 + (별도) 19-P-10 final_check r1 + 19-0 r1 Codex 판정: **모두 pass / pass with caveat (yes 진입 가능)** ([reports/refactor/](../../reports/refactor/) 영구 보존본)
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.
- 본 문서는 *최종 점검* 문서 — 새 폴더 / 파일 / 테스트 / fixture / 마이그레이션 미생성.

### 0-1. 본 문서 vs 19_refactor_final_check.md 관계

| 문서 | 중심 | 양식 |
|---|---|---|
| 19_refactor_final_check.md (직전 세션) | cross-check 매트릭스 (절대 원칙 / 모듈 분리 순서 / 부재 항목 / 의존성 방향) + caveat 누적 분류 + baseline 실측 + 진입 게이트 FG-1~FG-10 | 자체 정의 |
| **19_refactor_final_review.md (본 문서)** | **사용자 양식 §1~§10** — 최종 점검 목적 / 작성 완료 문서 / 기능 누락 / 리팩토링 순서 / 위험 / 테스트 / 주석 / 19-0 진입 조건 / 19-0에서 할 일 + 금지 / 최종 판단 | 사용자 명시 |

→ 두 문서는 *보완 관계* — 모두 19-0 진입 권고로 일치.

---

## 1. 최종 점검 목적

| # | 목적 | 본문 |
|---|---|---|
| 1 | 19-P 계획 문서 전체가 서로 일관적인지 확인 | 9개 준비 단계 문서 (19-P-1 현재 구조 / 19-P-2 목표 아키텍처 / 19-P-3 모듈 매핑 / 19-P-4 의존성 맵 / 19-P-5 테스트 전략 / 19-P-6 롤아웃 계획 / 19-P-7 위험 등록 / 19-P-8 의사결정 기록 / 19-P-9 공통 체크리스트) 의 P-* / R-* / D-* / T-* / RB-* / Risk ID / DEC-* / 79+ 체크 단위가 서로 충돌 없이 일관 정합한지 검증. |
| 2 | 실제 코드 리팩토링 전 빠진 기능 / 위험 / 테스트가 없는지 확인 | 핵심 기능 14개 + 보조 기능 19개 = **33개 기능 / 책임** 이 19-P-3 모듈 매핑 + 19-P-2 §4 분류표에서 빠짐없이 검토되었는지. 위험 77개 (19-P-7) + 테스트 보강 9개 (19-P-5 §4) 가 누락 없이 등록되었는지. |
| 3 | 19-0 기준 테스트 재확인 단계로 넘어갈 수 있는지 판단 | 19-0 진입 조건 (§8) 충족 여부 + 19-0 에서 할 일 (§8) + 19-0 에서 절대 하지 말아야 할 것 (§9) 명시 후 최종 판단 (§10). |

---

## 2. 작성 완료 문서 목록

> 9개 준비 단계 문서 모두 작성 완료. 각 문서별 작성 여부 / 핵심 내용 / 확인 필요 / 다음 세션 참조 이유.

### 2-1. [19_refactor_current_state.md](19_refactor_current_state.md)

| 항목 | 값 |
|---|---|
| 작성 여부 | ✓ 완료 (r2 — Codex r2 pass) |
| 핵심 내용 | 19-P 진입 직전 baseline 스냅샷. `app/routers/api.py` 5127줄 / 86 endpoint, `app/routers/ai.py` 929줄 / 13 endpoint, `app/templates/main.html` 7331줄, ORM 19개, 마이그레이션 m001~m013, 33+ 응답 키 셋 (§21), 86 endpoint 도메인 분류 (§3), Codex 검증 / 한계 인지 (§22, §24). |
| 확인 필요 | §22 C-1 비-AI 86 endpoint contract 미작성 — 분리 직전 보강 필수. §24 stale caveat — `docs/ai_rag_current_state.md` 18-1~18-8 변경분 일부 미반영 (19-0 시점에 r2 보정 완료). |
| 다음 세션 참조 이유 | **19-x 모든 코드 세션의 baseline** — 분리 후 회귀 비교 기준. 응답 키 / endpoint / DB / UI 의존 키 보존 검증의 1차 기준. |

### 2-2. [19_refactor_target_architecture.md](19_refactor_target_architecture.md)

| 항목 | 값 |
|---|---|
| 작성 여부 | ✓ 완료 (r3 — Codex r3 pass, r1+r2 fail 후 보정) |
| 핵심 내용 | 목표 모듈 구조 — `app/core/` (config / database / errors / responses / time_utils / security / feature_flags) + `app/modules/` 13개 (appointments / patients / staff / leaves / treatments / stats / sms / admin / backup / ai / audit / settings / export_import). 절대 원칙 P-1 ~ P-12. 모듈 간 의존성 방향 (§6). 분류표 37행 (M-01~M-36 + M-03b) — 즉시 분리 21 / 하위 책임 6 / 후속 검토 10. post-19-P 후보 6개 (calendar / notes / health / doctors / resources / emr). |
| 확인 필요 | T-1 ~ T-15 (§11) — 19-x 코드 세션 진입 시점 결정 항목. doctors / EMR / 노쇼 / 반복예약 / 자원 / 알림 / 출력물 모두 후속 검토. |
| 다음 세션 참조 이유 | **19-x 모든 코드 세션의 목표 위치** — 분리 시 어디로 이동할지 결정 기준. P-1~P-12 절대 원칙은 모든 세션 적용. |

### 2-3. [19_refactor_module_map.md](19_refactor_module_map.md)

| 항목 | 값 |
|---|---|
| 작성 여부 | ✓ 완료 (r1 — Codex pass with caveat) |
| 핵심 내용 | 30 모듈 매핑 (현재 위치 → 목표 위치) + 분류 (현재 기능 / 부분 존재 / 후속 검토). 우선순위 14단계 (§31). 주석 카테고리 5종 + TEMP 1종 정의 (§0-2). |
| 확인 필요 | T-13 staff 단일 vs `staff/{doctors,therapists}` 서브 디렉토리 — 19-8 결정. T-11 data-convert 분리 단위 — 19-7 결정. |
| 다음 세션 참조 이유 | **19-x 코드 세션의 코드-단위 매핑** — 함수 / 클래스 / 헬퍼가 어느 모듈로 이동하는지. |

### 2-4. [19_refactor_dependency_map.md](19_refactor_dependency_map.md)

| 항목 | 값 |
|---|---|
| 작성 여부 | ✓ 완료 (r2 — Codex r2 pass with caveat) |
| 핵심 내용 | 의존성 원칙 D-1 ~ D-13. 모듈 간 의존성 맵 (§2 — appointments / patients / staff / leaves / treatments / stats / sms / admin+settings / backup / ai / audit / health / export_import / core). 분리 순서 영향 (§6 먼저 분리 vs 나중 분리). 외부 API / sync 경계 (§3). |
| 확인 필요 | T-3 sync 위치 (services/sync vs core/sync vs modules/sync). T-9 ENTITY_MAP 9개 키 외부 노드 호환. |
| 다음 세션 참조 이유 | **19-x 코드 세션의 import 구조 / 호출 방향** — D-1~D-13 위반 검증. 순환참조 / core→modules 역참조 방지. |

### 2-5. [19_refactor_test_strategy.md](19_refactor_test_strategy.md)

| 항목 | 값 |
|---|---|
| 작성 여부 | ✓ 완료 (r3 — Codex r3 pass with caveat, r1 fail 후 r2 + r3 보정) |
| 핵심 내용 | 테스트 원칙 T-1 ~ T-15. 공통 검증 명령 (run_check.bat / pytest -v / ruff / check_db_path) + AI 하네스 6개 + 운영 DB 보호 5단계 + PyInstaller 53 tests. 모듈별 전략 (§3) — 6 existing / 9 needed / 5 follow-up. 분리 직전 보강 9개 항목 (§4-1). |
| 확인 필요 | 비-AI 86 endpoint contract 미작성 (C-1 / API-3) — 각 19-x 분리 직전 신규 추가 필수. xfail 7건 + skip 1건 → 정방향 전환 (19-4 / 19-5). |
| 다음 세션 참조 이유 | **19-x 코드 세션의 테스트 명령 + 보강 항목** — 분리 직전 신규 contract 테스트 / 분리 후 회귀 검증 / 5회 루프 정책. |

### 2-6. [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md)

| 항목 | 값 |
|---|---|
| 작성 여부 | ✓ 완료 (r2 — Codex r2 pass with caveat, r1 caveat 보정) |
| 핵심 내용 | 롤아웃 원칙 R-1 ~ R-14. **15개 실행 세션** (19-0 baseline + 19-1 core ~ 19-14 종료 게이트). 각 세션 12개 컬럼 (목표 / 가능 범위 / 금지 범위 / 선행 조건 / 테스트 / 응답 키 / 위험도 / rollback / Codex 포인트 / 주석). RB-1 ~ RB-10 rollback 기준. |
| 확인 필요 | 18-0~18-8 dirty/untracked 변경분 처리 (사용자 결정) — 19-0 / 19-P-10 §5-1 1번. `docs/ai_rag_current_state.md` stale 보정 (19-0 시점에 r2 보정 완료). |
| 다음 세션 참조 이유 | **19-x 코드 세션의 진행 순서 + 5회 루프 + rollback 기준** — 매 세션 §3-N 참조. |

### 2-7. [19_refactor_risk_register.md](19_refactor_risk_register.md)

| 항목 | 값 |
|---|---|
| 작성 여부 | ✓ 완료 (r3 — Codex r3 pass with caveat, r1 + r2 fail 후 taxonomy 정정) |
| 핵심 내용 | **77 Risk ID** (단독 prefix 20 + 통합 키 3 = 23 카테고리). 위험도 매트릭스 (가능성 × 영향도). 14 필드 (Risk ID / 위험 이름 / 모듈 / 설명 / 가능성 / 영향도 / 전체 위험도 / 발생 징후 / 방지 / 테스트 / 주석 태그 / rollback / Codex / 비고). 위험도별 분류 (치명 8 / 높음 14 / 중간 다수 / 낮음 3 / 후속 14). 세션별 위험 연결 (§5 19-0~19-14). 주석 매트릭스 (§6 약 70 Risk × 5 카테고리). |
| 확인 필요 | R-APPT-02 (도수 중복 차단 백엔드 미구현 — xfail 3건 + skip 1건) / R-APPT-03 (휴무 차단 백엔드 미구현 — xfail 4건) — 19-4 / 19-5 정방향 전환. |
| 다음 세션 참조 이유 | **19-x 코드 세션의 위험 우선순위 + 방지 / 검증 / rollback** — 매 세션 영향 Risk ID 식별. |

### 2-8. [19_refactor_decision_record.md](19_refactor_decision_record.md)

| 항목 | 값 |
|---|---|
| 작성 여부 | ✓ 완료 (r1 — Codex pass with caveat) |
| 핵심 내용 | **20 의사결정 (DEC-A ~ DEC-T)** — 단위화 / 세션 1개 / API 보존 / DB 보존 / router-service-repository / appointments 마지막 / availability / leaves / treatments+completion / stats / sms / patients+notes / staff / AI local-first / AI commands / settings+health+feature_flags / audit / PyInstaller / 주석 / Codex 게이트. 9 대안 (§3-1~9). 위험 매핑 (§4). 테스트 매핑 (§5). 주석 매트릭스 (§6 — 결정 20 × 6 카테고리 + 위치 16개). 재검토 기준 10 트리거 (§7). |
| 확인 필요 | DEC-T 매 세션 Codex 게이트 — 19-x 진입 시 사용자 결정 (현재 세션 단위). |
| 다음 세션 참조 이유 | **19-x 코드 세션의 결정 근거** — "왜 이 구조로 분리하는지" 답변. Codex 검증 시 판단 기준. |

### 2-9. [19_refactor_checklists.md](19_refactor_checklists.md)

| 항목 | 값 |
|---|---|
| 작성 여부 | ✓ 완료 (r1 — Codex pass with caveat) |
| 핵심 내용 | 9 카테고리 (§1 세션 시작 전 / §2 코드 수정 전 / §3 코드 이동 / §4 주석 / §5 테스트 / §6 모듈별 특수 / §7 실패 대응 / §8 완료 / §9 Codex 요청) — **총 79+ 체크 단위 (실측 328 체크박스)**. 모듈별 특수 8 모듈 (appointments / leaves / treatments+completion / stats / sms / patients+notes / admin+settings / ai+rag). |
| 확인 필요 | 19-P-9 caveat 1 (`## [0-9]+\.` grep 명령 — fenced markdown 예시까지 잡음, 19-0 시점에 r2 보정 완료). 19-P-9 caveat 3 (요청서 r2 → r3 표기, 19-0 시점에 r2 보정 완료). |
| 다음 세션 참조 이유 | **19-x 코드 세션의 매-세션 적용 체크리스트** — 시작 전 / 수정 전 / 이동 / 주석 / 테스트 / 실패 / 완료 / Codex 요청 9 단계 적용. |

### 2-10. (참고) [19_refactor_final_check.md](19_refactor_final_check.md) + 본 문서

| 항목 | 값 |
|---|---|
| 작성 여부 | ✓ 완료 (final_check r1 — Codex pass with caveat 별도 검증 / 본 final_review = 본 세션 신규) |
| 핵심 내용 | 19-P-1 ~ 19-P-9 cross-check + Codex caveat 누적 정리 + baseline 실측 (final_check) + 사용자 양식 §1~§10 (본 문서). |
| 확인 필요 | 본 세션 = 사용자 양식 §1~§10 정합 검증. final_check 와 보완. |
| 다음 세션 참조 이유 | **19-0 진입 직전 최종 점검 baseline**. 본 문서 + final_check.md 가 19-P 시리즈 종합 마지막 산출. |

---

## 3. 기능 누락 최종 확인

> 핵심 기능 14개 + 보조 기능 19개 = **33개 기능 / 책임** 분류. 사용자 명시 4분류 (현재 기능 / 부분 존재 / 후속 검토 / 확인 필요).
>
> **주의: 현재 없는 기능을 실제 구현된 것처럼 단정 ⊥** — 19-P-2 §3-3-4 / 19-P-7 §2-D / 19-P-8 DEC-M / 19-P-9 §6 / 19_refactor_final_check.md §2-3 정합.

### 3-1. 핵심 기능 (14개)

| # | 기능 | 분류 | 19-P 매핑 | 비고 |
|---|---|---|---|---|
| 1 | 예약 (appointments) | **현재 기능** | M-01 (19-9) / DEC-F / R-APPT-01~07 | 86 endpoint 중 10. FullCalendar 의존. 마지막 분리. |
| 2 | 환자 (patients) | **현재 기능** | M-02 (19-7) / DEC-L / R-PAT-01~05 | PII 보호 + 검색 + 메모 + counts dict. data-convert 동시 분리. |
| 3 | 치료사 (therapists) | **현재 기능** | M-03 (19-8) / DEC-M / R-THER-01~03 | Employee role="therapist" 분기 + alias `therapist_id` 이중 키. |
| 4 | 의사 / 진료진 후보 (doctors) | **부분 존재 + 후속 검토** | M-03b (19-8) staff.doctors_service / M-31 post-19-P / DEC-M / R-DOC-01~02 / R-32~R-35 | 현재: Employee role="doctor" + Treatment role="doctor" + `_doctor_codes_set` + `is_doctor_filter` (얇은 분기). **부재**: Patient.doctor_id / Doctor 별도 / Department / Room / DoctorSchedule / Order / Prescription — EMR 도입 시 후속. |
| 5 | 휴무 (leaves) | **현재 기능** | M-04 (19-5) / DEC-H / R-LEAVE-01~04 | `_upsert_employee_leave_core` 단일 진실원천. AI action_leave 호출. xfail 4건 정방향 전환. |
| 6 | 치료항목 (treatments) | **현재 기능** | M-05 (19-6) / DEC-I / R-TX-01~04 | manual60 = 1 카운트 정책 보존 ([CLAUDE.md](../../CLAUDE.md)). |
| 7 | 완료체크 (completion_rules) | **현재 기능** | M-06 (19-6) / DEC-I / R-TX-04 | approve/revert ±N. done_count 0 미만 방지. |
| 8 | 통계 (stats) | **현재 기능** | M-07 + M-08 (19-11) / DEC-J / R-STAT-01~05 | 8 GET endpoint + 엑셀 export 2 + manual-counts upsert 1. read-only (D-7). |
| 9 | 문자 / SMS (sms) | **현재 기능** | M-09 + M-29 (19-10) / DEC-K / R-SMS-01~05 | 외부 munjanara API. provider 분리. munjanara_key 마스킹. 자동 트리거 ⊥ (D-8). |
| 10 | 관리자 설정 (admin / settings) | **현재 기능** | M-10 + M-15 + M-16 (19-2 + 19-12) / DEC-P / R-ADM-01~05 | API key 원문 ⊥. PBKDF2 + 5회 잠금 + 세션 TTL. |
| 11 | 백업 / 복구 (backup) | **현재 기능** | M-11 (19-12) / DEC-P + DEC-Q / R-BAK-01~05 | atomic rename + integrity_check + UploadFile. 자동 백업 + 수동. |
| 12 | AI 명령 (ai/commands) | **현재 기능** | M-18 (19-13) / DEC-O / R-AI-* | action_leave 917줄. parse / preview / execute + HMAC 토큰 + TOCTOU. AI commands → leaves.service (write) 만 허용. |
| 13 | AI Safety | **현재 기능** | M-23 (19-13) / DEC-N + DEC-O / R-AI-01~07 | `pii.scan` + `_RE_MEDICAL_CLAIM` + `_RE_EXECUTION_CLAIM` + 출처 없는 단정 차단. AI 의사 가드 (M-36) post-19-P 후속. |
| 14 | RAG / Knowledge / Vector / Hybrid | **현재 기능** | M-23 (19-13) / DEC-N / R-AI-* | 18-1 RAG / 18-3 chunker / 18-4 reindex / 18-5 vector / 18-6 hybrid / 18-7 health 통합. local-first 절대 원칙. `local_only` 호출 0. |

### 3-2. 보조 기능 (19개)

| # | 기능 | 분류 | 19-P 매핑 | 비고 |
|---|---|---|---|---|
| 1 | calendar / schedule_view | **후속 검토** | M-26 post-19-P / R-CAL-01~04 | UI 분리는 19-P 비-목표. main.html 7331줄 + JS 미수정. |
| 2 | availability | **현재 기능** (M-01 하위) | (M-01 19-4 + 19-9) / DEC-G / R-APPT-02~06 | 점심창 + 충돌 + 휴무 + 반차 + 백엔드 우회 방지. xfail 8건 정방향 전환. |
| 3 | notes | **현재 기능** + **후속 검토** (통합) | M-02 하위 (19-7) + M-27 post-19-P / R-PAT-04~05 / DEC-L | 환자별 (Patient.memo) + 예약별 (Appointment.memo). 통합 modules/notes/ 신설 후속. |
| 4 | permissions / auth | **현재 기능** | M-25 core/security (19-1) / DEC-P / R-ADM-01 | PBKDF2 + 세션 TTL + 5회 잠금. admin 단일 등급 (직원/관리자 분리는 후속). |
| 5 | settings | **현재 기능** | M-15 (19-2) / DEC-P / R-ADM-04~05 | SystemSetting + SmsSetting + AiSetting 통합. AI key 갱신은 modules/ai/router.py. |
| 6 | audit / logs | **현재 기능** | M-14 (19-12) / DEC-Q / R-AUDIT-01~02 | audit() 시그니처 보존. PII 원문 audit_log 부재. 보존 정책 후속. |
| 7 | export_import | **현재 기능** | M-12 (19-7) / DEC-L / R-EXIM-01~02 | 엑셀 export 2 + data-convert ~600줄 (`_dc_*`). |
| 8 | health / diagnostics | **부분 존재** + **후속 검토** | (현재 부분 — `/api/ai/health` + `/api/ai/status`) + M-28 post-19-P (`/api/health` 신설) / R-HEALTH-01 / DEC-P | `/api/ai/health` (admin 9키 + public 4키) + `/api/ai/status` (18-7 9 top-level) 존재. **부재**: `/api/health` (서버 상태) — 후속 결정 필요. |
| 9 | core responses / errors | **부분 존재** | M-25 core (19-1) / DEC-E + DEC-A / R-CORE-04~05 | 신설 (`core/responses.py` + `core/errors.py`) — 표준 envelope + reason_code → HTTPException. 응답 키 100% 보존 (추가만). |
| 10 | feature_flags | **부분 존재** (분산) | M-30 core (19-2 + 19-13) / DEC-P / R-ADM-04 | 현재: AiSetting + 환경변수 분산. 신설 `core/feature_flags.py` 단일 진입점 — ai_mode (local_only / local_first / ai_assist). 환경변수 vs DB 단일 진실원천 결정 (T-8). |
| 11 | batch / jobs | **부분 존재** + **후속 검토** | (현재: 자동 백업 타이머 + reindex lock) + 통합 스케줄러 후속 / R-BATCH-01 | 동시 실행 lock 은 각 모듈. SMS 자동 발송 트리거 ⊥ (D-8 정합). |
| 12 | privacy / retention | **부분 존재** + **후속 검토** | (현재: PII 마스킹 `pii.scan` + sha256) + 보존 정책 (오래된 AI / audit 로그 자동 삭제) 후속 / R-PAT-01 + R-AI-07 + R-AUDIT-02 / DEC-N + DEC-Q | 환자 정보 비활성/삭제 정책 후속. 무한 보존 현재. |
| 13 | concurrency / locking | **부분 존재** | (현재: 예약 낙관적 락 `version` + reindex lock + backup engine.dispose) / R-LOCK-01~03 | 복원 중 다른 작업 차단 후속 검토. RB 기준 정합. |
| 14 | time_utils | **부분 존재** | M-25 core (19-1) / DEC-E / R-TIME-01 | 신설 `core/time_utils.py` — 오늘 / 내일 / 점심창 / 반차 / Asia/Seoul 통합. 현재 datetime 직접 사용 다수. |
| 15 | cancellations / no_show | **부분 존재** + **후속 검토** | (현재: status="canceled" 만) + Appointment.no_show m014+ 후속 / DEC-D + DEC-J / R-STAT-? | 노쇼 별도 필드 부재. m014+ 컬럼 추가는 본 19-P 비-목표. |
| 16 | recurring_appointments | **후속 검토** | (부재) post-19-P / DEC-D / §3-2 후속 | 주기 / 반복 예약 미구현. |
| 17 | resources | **후속 검토** | M-33 post-19-P / R-?? / DEC-M | 진료실 / 장비 / 자원 미구현. EMR 도입 시. |
| 18 | printing / documents | **후속 검토** | (부재) post-19-P / §3-2 후속 | 예약표 / 통계표 / 환자 안내문 출력 미구현. |
| 19 | notifications | **후속 검토** | (부재) post-19-P / §3-2 후속 | 내부 알림 / reindex 실패 / 백업 실패 알림 미구현. |

### 3-3. 분류 합계

> **r3 보정 (Codex r2 caveat 4 — follow-up row 산술 라벨 명시)**: 일부 기능은 *현재 기능 또는 부분 존재* 분류와 *후속 검토* 분류에 **동시 매핑** (예: notes 는 환자별 메모 = 현재 기능 + `modules/notes/` 통합 = 후속 검토). 본 §3-3 표는 분류별 *카운트 기준* 을 명시한다.

| 분류 (단독 카운트 기준) | 핵심 (14) | 보조 (19) | 합계 |
|---|---|---|---|
| **현재 기능** (단독 또는 + 후속 검토) | 13 (#1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14) | 6 (#2 availability, #3 notes, #4 permissions, #5 settings, #6 audit, #7 export_import) | **19** |
| **부분 존재** (단독 또는 + 후속 검토) | 1 (#4 doctors 분기) | 8 (#8 health, #9 core, #10 feature_flags, #11 batch, #12 privacy, #13 concurrency, #14 time_utils, #15 cancellations) | **9** |
| **후속 검토 단독** (다른 분류 부재) | 0 | 5 (#1 calendar, #16 recurring, #17 resources, #18 printing, #19 notifications) | **5** |
| **확인 필요** | 0 | 0 | **0** |
| **합계** | 14 | 19 | **33** ✓ |

#### 3-3-1. 동시 매핑 항목 (현재 기능 또는 부분 존재 + 후속 검토 동시)

> 위 표의 "현재 기능" + "부분 존재" 행에 카운트되었지만, *추가로* 후속 검토 분류도 갖는 항목 = **6개**.

| # | 기능 | 1차 분류 | 후속 검토 항목 |
|---|---|---|---|
| 4 (핵심) | doctors / 진료진 후보 | 부분 존재 (`Employee.role="doctor"` 분기) | EMR 도입 시 별도 `modules/doctors/` (M-31) + Patient.doctor_id (M-32) + DoctorSchedule (M-34) + Order/Prescription (M-35) |
| 3 (보조) | notes | 현재 기능 (Patient.memo + Appointment.memo) | 통합 `modules/notes/` (M-27) — 지속/당일 메모 정책 결정 후 |
| 8 (보조) | health / diagnostics | 부분 존재 (`/api/ai/health` + `/api/ai/status`) | `/api/health` 서버 상태 (M-28) — 별도 도메인 |
| 11 (보조) | batch / jobs | 부분 존재 (자동 백업 / reindex lock) | 통합 스케줄러 + SMS 자동 발송 통합 |
| 12 (보조) | privacy / retention | 부분 존재 (PII 마스킹 `pii.scan` + sha256) | 자동 삭제 / 보관 기간 정책 |
| 15 (보조) | cancellations / no_show | 부분 존재 (`status="canceled"`) | `Appointment.no_show` (m014+) |

> **결과**: 33개 기능 모두 19-P-3 / 19-P-2 / 19-P-7 / 19-P-8 / 19-P-9 에서 분류 정합. **확인 필요 0건** — 모든 기능 명확하게 4분류 중 하나 또는 두 분류에 매핑됨. 동시 매핑 6 항목은 *현재 기능 / 부분 존재* 행에 카운트되며, *후속 검토 단독 (5)* 행과는 중복 없음 — 산술 합계 19 + 9 + 5 + 0 = **33 ✓**.

---

## 4. 리팩토링 순서 최종 확인

> [19_refactor_rollout_plan.md §2-1](19_refactor_rollout_plan.md) 의 15개 실행 세션 (19-0 ~ 19-14) 적절성 검증.

### 4-1. 사용자 명시 7개 확인 항목

| # | 확인 항목 | 결과 | 근거 |
|---|---|---|---|
| 1 | 19-0 에서 기준 테스트를 먼저 재확인하는가 | ✓ pass | [19_refactor_rollout_plan.md §3-0](19_refactor_rollout_plan.md) 19-0 = "리팩토링 전 기준 테스트 / 하네스 재확인 (baseline 재고정)". 본 19-P-10 은 그 직전 단계. |
| 2 | appointments 를 너무 초반에 크게 건드리지 않는가 | ✓ pass | [19_refactor_target_architecture.md §9 M-01 우선순위 14](19_refactor_target_architecture.md) (마지막) + [19_refactor_dependency_map.md §6-B 나중 분리](19_refactor_dependency_map.md) + [19_refactor_decision_record.md DEC-F](19_refactor_decision_record.md) + [19_refactor_rollout_plan.md §3-9 19-9](19_refactor_rollout_plan.md). |
| 3 | availability / leaves / treatments / patients / therapists 경계를 먼저 정리하는가 | ✓ pass | 19-4 availability + 19-5 leaves + 19-6 treatments + 19-7 patients + 19-8 staff (therapists+doctors) — 모두 19-9 appointments 이전. |
| 4 | SMS / stats / admin / backup / AI commands 분리가 적절한 순서인지 | ✓ pass | 19-10 sms (appointments 이후 — read-only 의존) / 19-11 stats (도메인 모두 안정 후 read-only) / 19-12 admin+backup+audit+export_import (낮은 위험 묶음) / 19-13 AI commands 연결부 (도메인 안정 후 local-first). |
| 5 | PyInstaller 검증 시점이 포함되어 있는가 | ✓ pass | [19_refactor_test_strategy.md §2-6](19_refactor_test_strategy.md) — 53 hidden imports tests 매 세션 + 실제 빌드는 주요 묶음 후 + 19-14 종료 게이트 + 사용자 명시 승인. |
| 6 | 각 세션별 Codex 검증 게이트가 있는가 | ✓ pass | [19_refactor_decision_record.md DEC-T](19_refactor_decision_record.md) + [19_refactor_checklists.md §8-12 + §9](19_refactor_checklists.md) + [19_refactor_rollout_plan.md §1 R-10](19_refactor_rollout_plan.md). 매 세션 끝에 영구 보존본 + latest 진입점 작성. |

### 4-2. 추가 확인 — 사용자 §6 (롤아웃) 정합

| 19-x 세션 | 분리 대상 | 위험도 | 권고 순서 정합 |
|---|---|---|---|
| 19-0 | baseline 재고정 | 낮음 | ✓ |
| 19-1 | core (config / database / errors / responses / time_utils / security / feature_flags) | 낮음 | ✓ — 모든 modules 의존 |
| 19-2 | settings / feature_flags / health 분류 | 낮음~중간 | ✓ — health 신설은 후속 |
| 19-3 | calendar view-model 검토 | 낮음 / 0 (분리 패스 시) | ✓ — 사용자 §2 명시 + post-19-P 후속 결정 |
| 19-4 | availability | 중간 | ✓ — appointments 사전 준비 + xfail 8건 정방향 |
| 19-5 | leaves + am/pm/full 백엔드 차단 | 높음 | ✓ — 단일 진실원천 + AI action_leave 의존 |
| 19-6 | treatments + completion_rules | 중간 | ✓ — manual60 = 1 정책 + approve/revert |
| 19-7 | patients + notes + data-convert | 중간 | ✓ — PII 보호 + 검색 + 환자 import |
| 19-8 | staff (therapists + doctors 통합) | 낮음~중간 | ✓ — Employee 단일 테이블 + role 분기 + 의사 시드 ⊥ |
| 19-9 | appointments | 높음 (마지막) | ✓ — 의존 도메인 모두 안정 후 |
| 19-10 | sms (provider 외부 경계 분리) | 중간 | ✓ — 외부 API mock + munjanara 마스킹 |
| 19-11 | stats (8 GET + 엑셀 export) | 중간 | ✓ — read-only 의존 |
| 19-12 | admin + backup + audit + export_import | 낮음~중간 | ✓ — 위험도 낮은 묶음 |
| 19-13 | AI commands 연결부 | 중간 | ✓ — local-first + leaves.service 호출만 |
| 19-14 | 종료 게이트 (전체 회귀 + PyInstaller 빌드) | 낮음 | ✓ — 사용자 명시 승인 시 빌드 |

→ **결과**: 15개 실행 세션 모두 의존성 / 위험 / 테스트 전략과 정합. 순서 변경 권고 사항 없음.

---

## 5. 위험도 최종 확인

> [19_refactor_risk_register.md §2](19_refactor_risk_register.md) 의 77 Risk ID 중 사용자 명시 13개 위험이 누락 없이 등록되었는지 검증.

| # | 사용자 명시 위험 | 19-P-7 매핑 | 등록 여부 |
|---|---|---|---|
| 1 | 예약 API 응답 key 변경 위험 | R-APPT-01 | ✓ 치명 위험 8개 중 |
| 2 | 휴무 차단 누락 위험 | R-APPT-03 + R-LEAVE-01 + R-LEAVE-03 | ✓ 치명 위험 8개 중 (R-APPT-03 — 백엔드 미구현) |
| 3 | 오전 / 오후 반차 기준 변경 위험 | R-APPT-04 | ✓ 높음 위험 14개 중 (12:00 정확 기준) |
| 4 | 완료체크 카운트 방식 변경 위험 | R-TX-01 + R-TX-04 | ✓ 높음 위험 14개 중 (manual60 = 1 / done_count 0 미만 방지) |
| 5 | 통계 집계 기준 변경 위험 | R-STAT-01 ~ R-STAT-05 | ✓ 5건 모두 등록 |
| 6 | 문자 대상 추출 오류 위험 | R-SMS-01 + R-SMS-04 | ✓ R-SMS-04 치명 위험 (실제 외부 발송 ⊥) |
| 7 | API key / 개인정보 노출 위험 | R-ADM-02 + R-AI-07 + R-PAT-01 + R-AUDIT-02 | ✓ R-ADM-02 + R-PAT-01 치명 위험 |
| 8 | 운영 DB 접근 위험 | R-OPS-01 ~ R-OPS-03 + R-BAK-01 | ✓ R-BAK-01 치명 위험 |
| 9 | 외부 API 호출 위험 | R-AI-06 + R-SMS-04 + R-OPS-03 | ✓ R-AI-06 + R-SMS-04 + R-OPS-03 등록 |
| 10 | local-first AI 원칙 훼손 위험 | R-AI-01 ~ R-AI-04 + R-LOCK-02~03 | ✓ R-AI-01 치명 위험 (provider call 0) |
| 11 | PyInstaller 빌드 실패 위험 | R-OPS-04 + R-OPS-05 + R-OPS-06 | ✓ 높음 위험 (53 hidden imports + exe smoke + requirements) |
| 12 | 순환참조 위험 | R-CORE-01 + R-CORE-02 | ✓ 등록 (router→service→repository / core→modules ⊥) |
| 13 | 프론트 JS 의존 key 변경 위험 | R-CORE-04 + R-CORE-05 + R-APPT-01 + R-PAT-02 + R-STAT-* + R-SMS-* | ✓ 다수 등록 (33+ 키 셋 보존) |

→ **결과**: 사용자 명시 13개 위험 모두 19-P-7 §2 에 등록됨. 누락 0건.

### 5-1. 추가 확인 — 위험도 분류 합리성

[19_refactor_risk_register.md §3](19_refactor_risk_register.md) 정합:
- **치명 위험 8개** — R-APPT-02 (도수 중복) / R-APPT-03 (휴무 차단) / R-PAT-01 (PII) / R-SMS-04 (외부 발송) / R-ADM-01 (admin 노출) / R-ADM-02 (API key) / R-AI-01 (local-first) / R-BAK-01 (운영 DB)
- **높은 위험 14개** — 응답 키 / 12:00 기준 / devtools / doctors 단정 / 표시-차단 / manual60 / 계정 노출 / local_only / 외부 API / AI 로그 PII / UI 키 / DB 경로 / PyInstaller / exe smoke
- **중간 위험 다수** / **낮은 위험 3개** (R-THER-03 / R-CAL-04 / R-HEALTH-01) / **후속 검토 14개**

---

## 6. 테스트 전략 최종 확인

> [19_refactor_test_strategy.md §2 + §3 + §4](19_refactor_test_strategy.md) 의 테스트 항목이 사용자 명시 15개를 포함하는지 검증.

| # | 사용자 명시 테스트 | 19-P-5 매핑 | 반영 여부 | 보강 시점 |
|---|---|---|---|---|
| 1 | `pytest tests -v` | C-2 (전체 회귀) | ✓ 있음 | 큰 모듈 분리 후 매 세션 종료 |
| 2 | `ruff check app tests scripts` | C-3 | ✓ 있음 | 매 세션 종료 |
| 3 | `python scripts/check_db_path.py` | C-4 | ✓ 있음 | 매 세션 시작 + 종료 |
| 4 | API contract 테스트 | API-1 (manual_qa) + API-2 (health) | △ 부분 — API-3 비-AI 86 endpoint contract **부재 (C-1)** | **각 19-x 분리 직전 신규 추가 필수 — 19-0에서 보강 필요 (도메인별 우선순위 결정)** |
| 5 | 예약 핵심 테스트 | [test_appointment_rules.py](../../tests/test_appointment_rules.py) | △ 부분 — xfail 3건 + skip 1건 + 점심창/PUT/DELETE/409 부재 | **19-4 / 19-9 분리 직전 보강** |
| 6 | 휴무 차단 테스트 | [test_therapist_leave.py](../../tests/test_therapist_leave.py) | △ 부분 — xfail 4건 (백엔드 미구현) | **19-4 / 19-5 분리 직전 백엔드 차단 코드 + 정방향 전환** |
| 7 | 완료체크 테스트 | [test_employee_can_manual_contract.py](../../tests/test_employee_can_manual_contract.py) + [test_stats_counts.py](../../tests/test_stats_counts.py) | △ 부분 — approve / revert / done_count 0 미만 contract 부재 | **19-6 분리 직전 보강** |
| 8 | 통계 테스트 | [test_stats_counts.py](../../tests/test_stats_counts.py) | △ 부분 — 8 endpoint 응답 키 contract 부재 | **19-11 분리 직전 보강** |
| 9 | 문자 대상 추출 테스트 | [test_sms_validation.py](../../tests/test_sms_validation.py) | △ 부분 — `tomorrow-targets` 응답 contract + 외부 HTTP mock 부재 | **19-10 분리 직전 보강** |
| 10 | 기존 SMS AI 테스트 | A-1 ([test_ai_sms_validate.py](../../tests/test_ai_sms_validate.py) + [test_ai_sms_draft.py](../../tests/test_ai_sms_draft.py) + [test_ai_sms_draft_hallucination.py](../../tests/test_ai_sms_draft_hallucination.py)) | ✓ 있음 | 매 세션 회귀 |
| 11 | 기존 휴무 AI 테스트 | A-2 ([test_ai_action_leave.py](../../tests/test_ai_action_leave.py)) | ✓ 있음 | 매 세션 회귀 |
| 12 | AI / RAG 하네스 전체 | H-1~H-6 (Full / RAG / Safety / Chunk / Reindex / Vector / Hybrid + Health) | ✓ 있음 | 매 세션 회귀 |
| 13 | 운영 DB 보호 검사 | S-1 ~ S-5 (check_db_path / 4단계 격리 / db_guard) | ✓ 있음 | 매 세션 자동 |
| 14 | 외부 API 호출 금지 검사 | S-4 (`_block_sdk_modules`) | ✓ 있음 | 매 세션 자동 |
| 15 | PyInstaller 검증 | P-1 (53 tests) + P-2 (migration_spec_discovery) + P-3 (실제 빌드) + P-4 (exe smoke) | ✓ 있음 | P-1 매 세션 / P-3 주요 묶음 / P-4 종료 게이트 |

### 6-1. 19-0 에서 보강 필요 항목

| 영역 | 현재 상태 | 보강 시점 |
|---|---|---|
| **API-3 비-AI 86 endpoint contract** | 부재 (C-1) | **19-0에서 도메인별 우선순위 결정** + 각 19-x 분리 직전 신규 추가 |
| **예약 점심창 / PUT / DELETE / 409 contract** | 부재 | 19-4 / 19-9 분리 직전 |
| **xfail 3건 + skip 1건 정방향 전환** (도수 중복 차단) | 백엔드 미구현 | 19-4 백엔드 차단 코드 추가 + 전환 |
| **xfail 4건 정방향 전환** (휴무 차단) | 백엔드 미구현 | 19-4 / 19-5 백엔드 차단 코드 추가 + 전환 |
| **approve / revert / done_count 0 미만 contract** | 부재 | 19-6 분리 직전 |
| **8 endpoint 응답 키 contract** (통계) | 부재 | 19-11 분리 직전 |
| **`tomorrow-targets` contract + 외부 HTTP mock** | 부재 | 19-10 분리 직전 |
| **자동 grep 명령 보정** (19-P-9 caveat 1) | 부재 | 19-0 시점에 r2 보정 완료 |

→ **결과**: 사용자 명시 15개 테스트 모두 19-P-5 에서 등록됨. **9개 보강 항목** (C-1 외) 은 각 19-x 분리 직전 신규 추가. **19-0 에서 도메인별 contract 우선순위 결정**.

---

## 7. 주석 / 문서화 기준 최종 확인

> [19_refactor_checklists.md §4 + §6](19_refactor_checklists.md) + [19_refactor_decision_record.md DEC-S + §6](19_refactor_decision_record.md) 정합.

| # | 사용자 명시 주석 / 문서화 기준 | 19-P 매핑 | 반영 여부 |
|---|---|---|---|
| 1 | 새 파일 상단 docstring | 19-P-9 §4-1 | ✓ — 1줄 docstring (역할 + 책임), 의미 있는 주석만 |
| 2 | 주요 service / rules / repository 함수 docstring | 19-P-9 §4-2 | ✓ — 핵심 헬퍼 (`_upsert_employee_leave_core`, `_bump_patient_count`, `_check_lunch_block`, `_check_version`, `_serialize_appointment`, `_doctor_codes_set`) 1줄 docstring |
| 3 | 기존 API / UI 호환 wrapper 의 COMPAT 주석 | 19-P-9 §4-3 + DEC-C | ✓ — wrapper / 응답 dict 빌더 / alias 이중 키 / sync `ENTITY_MAP` / FullCalendar event / version 필드 |
| 4 | 개인정보 / 운영 DB / 외부 API 차단 부분의 SAFETY 주석 | 19-P-9 §4-4 + DEC-D + DEC-N + DEC-K | ✓ — `core/config.py:get_db_path` / `core/security.py` / `patients/notes_service.py` / `audit/service.py` / `sms/provider.py` / `ai/router.py` / `ai/commands/action_leave.py` / `settings/service.py` / `tests/conftest.py:_block_sdk_modules` |
| 5 | 업무 규칙 부분의 NOTE 또는 RISK 주석 | 19-P-9 §4-5 + DEC-G + DEC-H + DEC-I + DEC-J + DEC-K | ✓ — 점심창 / 휴무 차단 / 반차 12:00 / 도수 중복 / manual60=1 / approve-revert / read-only / 자동 트리거 ⊥ / local-first / 낙관적 락 TOCTOU / HMAC 토큰 / reindex lock |
| 6 | TODO(19-x) 형식 | 19-P-9 §4-6 + DEC-S | ✓ — 세션 번호 / 제거 조건 의무. 단순 `# TODO:` ⊥ |
| 7 | 의미 없는 모든 줄 주석 금지 | 19-P-9 §4-8 + [CLAUDE.md](../../CLAUDE.md) | ✓ — "Default to writing no comments" / 자명한 부분에 설명 ⊥ |
| 8 | 주석 작성 때문에 기능 동작 변경 금지 | 19-P-9 §4-9 + DEC-S | ✓ — 주석-코드 일치 / drift ⊥ |

→ **결과**: 사용자 명시 8개 주석 / 문서화 기준 모두 19-P-9 + 19-P-8 에서 반영됨. 향후 코드 이동 시 주석 위치 16개 (19-P-8 §6-2) 명시.

---

## 8. 19-0 진입 조건

### 8-1. 진입 가능 조건 (사용자 명시 8개)

| # | 조건 | 본 19-P-10 시점 결과 |
|---|---|---|
| 1 | 19-P 문서 전체 작성 완료 | ✓ — 9개 준비 단계 (19-P-1 ~ 19-P-9) + 본 19-P-10 = 10 문서 작성 완료 |
| 2 | Codex 검증에서 치명적 문제 없음 | ✓ — 9개 모두 pass / pass with caveat (yes 진입 가능). 진행 차단 caveat 0건 |
| 3 | 리팩토링 순서 확정 | ✓ — 19-0 ~ 19-14 = 15개 실행 세션 (§4 정합) |
| 4 | 위험 등록 완료 | ✓ — 77 Risk ID + 사용자 명시 13개 모두 등록 (§5 정합) |
| 5 | 테스트 전략 확정 | ✓ — 사용자 명시 15개 + 보강 9개 항목 (§6 정합) |
| 6 | 공통 체크리스트 확정 | ✓ — 9 카테고리 + 79+ 체크 단위 (실측 328 체크박스, §2-9 정합) |
| 7 | 현재 없는 기능은 후속 검토로 분류 | ✓ — 33개 기능 중 후속 검토 분류 명확 (§3 정합). 부재 항목 단정 ⊥ (Doctor / Patient.doctor_id / no_show / `/api/health` / Resource 등 grep 0건) |
| 8 | 코드 수정 없이 계획 문서만 작성 완료 | ✓ — 본 19-P-10 + 모든 19-P 시리즈 read-only. `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements*.txt app/templates app/static pyproject.toml` = 18-0~18-8 기존 5 tracked 만 (본 19-P 추가 0) |

→ **결과**: 사용자 명시 8개 진입 조건 모두 충족.

### 8-2. 19-0 에서 할 일 (사용자 명시 4개)

| # | 할 일 | 본문 |
|---|---|---|
| 1 | 리팩토링 전 기준 테스트 / 하네스 재확인 | `run_check.bat` (pytest + ruff + check_db_path) + `pytest tests -v` (전체 회귀 — 18-8 baseline 529/1/7) + AI 하네스 6개 (Full / RAG / Safety / Chunk / Reindex / Vector / Hybrid) + PyInstaller 53 tests + 운영 DB 보호 5단계 + 외부 API 차단. |
| 2 | 현재 테스트 통과 여부 기록 | `reports/ai_dev_loop/19-0_test_report.md` (영구) + `latest_test_report.md` (덮어쓰기). 통과 / 실패 카운트 + 실행 환경 + 주요 로그 발췌. |
| 3 | 부족한 기준 테스트 확인 | §6-1 보강 9개 항목 인덱싱 — 비-AI 86 endpoint contract / 점심창 / PUT / DELETE / 409 / xfail 7+1건 정방향 전환 / approve-revert / 8 endpoint stats / tomorrow-targets / 외부 HTTP mock. **각 19-x 분리 직전 신규 추가 시점 결정**. |
| 4 | 이후 19-1 core 공통 유틸 정리로 넘어갈 수 있는지 판단 | 19-0 검증 결과 (529/1/7 회귀 0 + PyInstaller 53 tests 통과 + 운영 DB 보호 + 외부 API 차단) + 사용자 결정 (dirty 변경분 처리 / stale 보정 시점 / caveat 보정 시점) 답변 후 19-1 진입. |

> **참고**: 본 19-0 자체는 이미 [reports/ai_dev_loop/19-0_test_report.md](../../reports/ai_dev_loop/19-0_test_report.md) (직전 세션) 에서 baseline 검증 완료 — 18-8 100% 일치 + 53 tests 통과 + 환경 정상.

---

## 9. 19-0 에서 절대 하지 말아야 할 것

> 사용자 명시 8개 금지 항목 + 본 19-P-10 자체 적용.

| # | 금지 항목 | 19-0 적용 |
|---|---|---|
| 1 | 아직 실제 모듈 이동 금지 | 19-0 = baseline 재고정 *검증* 만. 신규 modules 폴더 / 신규 파일 생성 ⊥. 코드 함수 이동 ⊥ |
| 2 | 대규모 리팩토링 금지 | 단일 함수 / 단일 클래스 이동도 ⊥ — 19-1 부터 진행 |
| 3 | DB schema 변경 금지 | m001~m013 diff 0. m014+ 신규 마이그레이션 ⊥ |
| 4 | UI 변경 금지 | `app/templates/main.html` 7331줄 + `app/static/css/app.css` 3626줄 + 인라인 JS / FullCalendar / Alpine 무수정 |
| 5 | API 응답 key 변경 금지 | 33+ 키 셋 보존. 비-AI alias (`therapist_id` 이중 키) 보존 |
| 6 | 하네스 약화 금지 | `tests/conftest.py` 4단계 격리 / `_block_sdk_modules` / `tests/harness/db_guard.py` 약화 ⊥ |
| 7 | 운영 DB 접근 금지 | `%APPDATA%\도수치료예약\clinic.db` 미접근. `scripts/check_db_path.py` 통과 |
| 8 | 외부 API 호출 금지 | 실제 OpenAI / Anthropic / 문자나라 API 호출 ⊥. FakeProvider / FakeEmbeddingProvider 만 |

→ **결과**: 19-0 = read-only 검증 세션. 사용자 명시 8개 금지 항목 모두 적용.

---

## 10. 최종 판단

### 10-1. 종합 결과

| 항목 | 결과 |
|---|---|
| §1 최종 점검 목적 3개 | ✓ 모두 충족 |
| §2 작성 완료 문서 9 + 1 (final_check) + 1 (final_review) = 11 | ✓ 모두 작성 완료 |
| §3 기능 누락 — 핵심 14 + 보조 19 = 33 | ✓ 누락 0건 (확인 필요 0) |
| §4 리팩토링 순서 — 사용자 명시 7 항목 | ✓ 모두 정합 |
| §5 위험 — 사용자 명시 13개 + 77 Risk ID | ✓ 누락 0건 |
| §6 테스트 — 사용자 명시 15개 + 보강 9개 | ✓ 모두 등록 (보강은 분리 직전) |
| §7 주석 / 문서화 — 사용자 명시 8개 | ✓ 모두 반영 |
| §8 19-0 진입 조건 — 사용자 명시 8개 | ✓ 모두 충족 |
| §9 19-0 금지 — 사용자 명시 8개 | ✓ 모두 적용 |

### 10-2. 자체 판단

**19-0 진행 가능** (yes — 19-0 baseline 재고정 진입 가능).

판단 이유:
1. **9개 준비 단계 문서 (19-P-1 ~ 19-P-9) + 본 19-P-10 모두 작성 완료**. revision 이력 18 회 + fail 5회 (모두 보정 후 pass / pass with caveat 복귀).
2. **9개 모두 Codex 검증 pass / pass with caveat (yes 진입 가능)**. 진행 차단 caveat 0건.
3. **사용자 명시 모든 항목 정합 — 기능 누락 0 / 리팩토링 순서 정합 / 위험 13개 등록 / 테스트 15개 등록 / 주석 8개 반영 / 19-0 진입 조건 8개 충족 / 금지 8개 적용**.
4. **부재 항목 단정 ⊥ 100% 정합** — Doctor / Patient.doctor_id / Doctor.schedule / Department / Room / Order / Prescription / Resource / `/api/health` / no_show / 반복 예약 / 자원 / 알림 / 출력물 모두 후속 검토 분류.
5. **18-8 baseline 100% 일치 (529 passed, 1 skipped, 7 xfailed)** — 직전 세션 [19-0_test_report.md](../../reports/ai_dev_loop/19-0_test_report.md) 에서 재검증 완료.
6. **PyInstaller 53 tests 산출 공식 (15 + 19×2 = 53) 정확** — 직전 세션에서 collected 53 + passed 53 검증.
7. **`.venv` Python 3.12.10 / pytest 8.4.2 / ruff 0.15.12 환경 정상** — 직전 세션 검증.
8. **운영 DB 보호 (S-1~S-5) + 외부 API 차단 (`_block_sdk_modules`) 자동 동작**.
9. **본 19-P-10 코드 / 테스트 / spec / UI / migrations / requirements 변경 0** — read-only 정책 100% 준수.
10. **19-P-1 ~ 19-P-9 + 19-0 산출물 (이미 작성된 파일) 외 추가 변경 0**.

남은 위험 / 사용자 결정 필요 (19-1 진입 직전):
- (1) 18-0 ~ 18-8 dirty/untracked 변경분 처리 (머지 / commit / 유지) — *직전 세션에서 사용자가 옵션 1-a-① 선택 + commit 진행 중단된 상태*. 본 세션은 새 세션으로 전환됨. 19-1 진입 전 결정 필요.
- (2) `docs/ai_rag_current_state.md` stale 보정 — *직전 세션에서 r2 보정 완료* (line 18-1~18-8 변경분 인지 + 19-P-1 권위 baseline 참조).
- (3) 19-P-9 / 19-P-10 caveat 5건 보정 — *직전 세션에서 r2 보정 완료* (caveat 1~8 모두 read-only 문서 보정 완료).

→ **남은 결정 = 1건 (dirty 변경분 처리)**. 19-1 진입 시 결정 답변 후 [19-P-9 §1 ~ §2 체크리스트](19_refactor_checklists.md) 적용.

다음 단계: **19-0 baseline 재고정 진입 가능** → (직전 세션 baseline 검증 완료 시) → **19-1 core 공통 유틸 정리 진입** (사용자 결정 1건 답변 후).

---

## 11. 종합

- 본 19-P-10 = 사용자 양식 §1~§10 정합 최종 점검. 직전 세션 19_refactor_final_check.md (cross-check 매트릭스 중심) 와 보완.
- **9개 준비 단계 문서 모두 작성 완료** + revision 18회 + fail 5회 (모두 보정 후 복귀) + Codex 검증 9건 모두 pass / pass with caveat.
- 33개 기능 (핵심 14 + 보조 19) 모두 분류 — **단독 카운트: 현재 기능 19 + 부분 존재 9 + 후속 검토 단독 5 + 확인 필요 0 = 33** (§3-3 표). **동시 매핑 6 항목** (#4 doctors / #3 notes / #8 health / #11 batch / #12 privacy / #15 cancellations) 은 *현재 기능 또는 부분 존재* 행에 이미 카운트되며 *추가로* 후속 검토 분류도 갖음 (§3-3-1 표). 산술 정합: 19 + 9 + 5 + 0 = 33 ✓ — r5 보정 (Codex r4 caveat 3 정합).
- 사용자 명시 13개 위험 / 15개 테스트 / 8개 주석 / 8개 진입 조건 / 8개 금지 항목 모두 정합.
- 부재 항목 단정 ⊥ 100% 정합 (grep 0건).
- 18-8 baseline (529 passed, 1 skipped, 7 xfailed) + PyInstaller 53 tests + `.venv` 정상 — 직전 세션에서 모두 검증 완료.
- 본 19-P-10 코드 / 테스트 / spec / UI / migrations / requirements 변경 0.
- **자체 판단: 19-0 진행 가능 (yes — 19-0 baseline 재고정 진입 가능)**. 다음 단계 = 사용자 결정 1건 (dirty 변경분 처리) 답변 후 19-1 core 공통 유틸 정리 진입.
