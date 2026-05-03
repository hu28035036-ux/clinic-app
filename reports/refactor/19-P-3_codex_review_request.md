# 19-P-3 Codex 검증 요청서

> **사용자가 Codex에게 전달할 최소 문구**
>
> > "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

본 요청서는 19-P 단위화 리팩토링 세 번째 세션의 산출물 (모듈 매핑 문서) 1건을 Codex 가 독립적으로 검증할 수 있도록 작성한 표준 패키지다.

---

## 0. Baseline

- HEAD commit: `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 19-P-1 r2 / 19-P-2 r3 Codex 판정: **pass / pass** ([reports/refactor/19-P-1_codex_review.md](19-P-1_codex_review.md), [reports/refactor/latest_codex_review.md](latest_codex_review.md))
- 본 세션은 위 commit 위에 신규 commit 없이 untracked 문서 추가만 수행. 코드/테스트/spec/UI 무수정.

## 1. 세션 이름

**19-P-3 단위화 리팩토링 모듈 매핑 문서 작성**

- 19-P-1 ([현재 구조](../../docs/refactor/19_refactor_current_state.md)) + 19-P-2 ([목표 아키텍처](../../docs/refactor/19_refactor_target_architecture.md)) 를 기반으로 **30개 모듈 매핑 표** 작성.
- read-only 문서 세션. 실제 코드 이동 없음.

## 2. 이번 세션 목표

| # | 목표 |
|---|---|
| 1 | 30개 모듈 (사용자 §1-30) 각각에 대해 15항목 매핑표 작성 — 분류 / 현재 위치 / 목표 위치 / 난이도 / 위험도 / 응답 키 보존 / 프론트 호환 / 하네스 / Codex 검증 포인트 / 비고 / 주석 필요 |
| 2 | 분류: **현재 기능** / **부분 존재** / **후속 검토** — 현재 부재 항목을 단정하지 않음 |
| 3 | 9개 하단 섹션 — §31 우선 분리 / §32 나중 분리 / §33 위험 모듈 / §34 테스트 보강 / §35 응답 키 위험 / §36 프론트 의존 / §37 DB schema 무관 / §38 후속 검토 only / §39 주석 필요 위험 지점 |
| 4 | 19-P-2 §9 분류표 (M-01~M-36 + M-03b = 37행) 와 1:1 연결 |
| 5 | 향후 코드 이동 시 추가할 주석 카테고리 (COMPAT/SAFETY/NOTE/RISK/TODO) 표시 — 본 세션은 코드 무수정이므로 위치만 |

## 3. 작성한 문서

### 신규 (3)

- [docs/refactor/19_refactor_module_map.md](../../docs/refactor/19_refactor_module_map.md) — 30 모듈 매핑 (§2-1 ~ §2-30) + 9 하단 섹션 (§31~§39) + §40 종합. 약 1100줄.
- [reports/refactor/19-P-3_codex_review_request.md](19-P-3_codex_review_request.md) (본 문서, 영구 보존본)
- [reports/refactor/latest_codex_review_request.md](latest_codex_review_request.md) (Codex 진입점 — 본 문서와 동일)

### Codex 작성 예정

- [reports/refactor/19-P-3_codex_review.md](19-P-3_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

## 4. 수정 금지였던 범위

사용자 지시문 11개 금지 항목:

1. 코드 수정 금지
2. `app/` 기능 코드 수정 금지
3. `tests/` 테스트 코드 작성 금지
4. migration 생성 금지
5. `requirements.txt` 수정 금지
6. PyInstaller spec (`dosu_clinic.spec`) 수정 금지
7. UI (`app/templates/`, `app/static/`) 수정 금지
8. 기존 API 응답 구조 변경 금지
9. 운영 DB 접근 금지
10. 실제 외부 API 호출 금지
11. 하네스/테스트 약화 금지

추가:
- 18-8 baseline (529 passed, 1 skipped, 7 xfailed) 회귀 보호.
- m001~m013 마이그레이션 diff 0 유지.
- 19-P-1 / 19-P-2 산출물 무수정 유지.

## 5. 실제 수정한 파일 목록

### 신규 (3)

- `docs/refactor/19_refactor_module_map.md`
- `reports/refactor/19-P-3_codex_review_request.md` (본 문서)
- `reports/refactor/latest_codex_review_request.md`

### 수정 (0)

없음. 19-P-1 / 19-P-2 산출물 ([19_refactor_current_state.md](../../docs/refactor/19_refactor_current_state.md), [19_refactor_target_architecture.md](../../docs/refactor/19_refactor_target_architecture.md), [19-P-1_codex_review_request.md](19-P-1_codex_review_request.md), [19-P-2_codex_review_request.md](19-P-2_codex_review_request.md), [19-P-1_codex_review.md](19-P-1_codex_review.md)) 는 본 19-P-3 세션에서 미수정.

> `latest_codex_review_request.md` 는 19-P-3 진입점으로 덮어쓰여진다 (19-P-2 r3 본문은 `19-P-2_codex_review_request.md` 영구 보존본에 보존).

### 무수정 (회귀 보호)

`app/**`, `tests/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`, `CLAUDE.md`, `app/models/models.py`, `app/routers/api.py`, `app/routers/ai.py`, `tests/conftest.py`, `app/services/**`, `docs/refactor/19_refactor_current_state.md` (19-P-1 산출물 보존), `docs/refactor/19_refactor_target_architecture.md` (19-P-2 산출물 보존).

## 6. 코드 수정 없이 docs/refactor + reports/refactor 문서만 작성했는지 확인

### Claude Code 자체 점검

| 검사 | 결과 |
|---|---|
| 본 19-P-3 세션이 새로 만든 파일 | `docs/refactor/19_refactor_module_map.md` + `reports/refactor/{19-P-3,latest}_codex_review_request.md` |
| `app/**` 변경 | 0 |
| `tests/**` 변경 | 0 |
| `app/migrations/**` 변경 | 0 |
| `requirements*.txt` 변경 | 0 |
| `dosu_clinic.spec` 변경 | 0 |
| `app/templates/**` 변경 | 0 |
| `app/static/**` 변경 | 0 |
| `pyproject.toml` 변경 | 0 |
| 19-P-1 / 19-P-2 산출물 변경 | 0 |

→ **코드 수정 없이 docs/refactor + reports/refactor 문서만 작성**.

### Codex 가 직접 검증할 명령

```bash
git status --short
git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml
# 결과: 18-0~18-8 변경분만 표시되어야 하며, 본 19-P-3 세션의 추가 변경분은 0.
```

## 7. Codex 가 검증해야 할 문서

### 1차 (필수)

- [docs/refactor/19_refactor_module_map.md](../../docs/refactor/19_refactor_module_map.md) (본 세션 신규)

### 2차 (대조 기준)

- [docs/refactor/19_refactor_current_state.md](../../docs/refactor/19_refactor_current_state.md) (19-P-1 r2 통과본 — 현재 구조 단정)
- [docs/refactor/19_refactor_target_architecture.md](../../docs/refactor/19_refactor_target_architecture.md) (19-P-2 r3 통과본 — 목표 구조)
- [docs/refactor/19_refactor_entry_notes.md](../../docs/refactor/19_refactor_entry_notes.md) (19-P 진입 기준)
- [docs/AI_WORKING_RULES.md](../../docs/AI_WORKING_RULES.md) (local-first 보존)
- [docs/ai_rag_architecture_plan.md](../../docs/ai_rag_architecture_plan.md) (RAG 목표)
- [reports/refactor/19-P-2_codex_review.md](19-P-2_codex_review.md) (직전 r3 pass)
- [CLAUDE.md](../../CLAUDE.md) (manual60=1 + per-file-ignores)

## 8. 현재 구조와 목표 구조의 매핑이 현실적인지 확인할 항목

| 항목 | 검증 방법 |
|---|---|
| §2-1 appointments | 라인 1608-2057 (10 endpoint) 가 [api.py](../../app/routers/api.py) 에 존재 + `_check_version` 1664 / `_bump_version` 1676 / `_bump_patient_count` 1934 정합 |
| §2-3 therapists alias | `/api/therapists` ([api.py:1175-1182](../../app/routers/api.py:1175)) + `/api/therapist-leaves` ([api.py:1184-1199](../../app/routers/api.py:1184)) `therapist_id` 이중 키 보존 명시 |
| §2-4 doctors / medical_staff | `_doctor_codes_set` ([api.py:153-156](../../app/routers/api.py:153)) + `is_doctor_filter` ([api.py:3464](../../app/routers/api.py:3464)) + assign role=doctor ([api.py:1773-1775](../../app/routers/api.py:1773)) + 엑셀 doctor suffix ([api.py:4339,4362-4465](../../app/routers/api.py:4339)) 라인 정합 |
| §2-5 leaves | `_upsert_employee_leave_core` ([api.py:1098-1118](../../app/routers/api.py:1098)) 단일 진실원천 + AI action_leave 호출 명시 |
| §2-6 treatments | manual60 `count_increment=1` ([constants.py:20](../../app/models/constants.py:20)) 보존 명시 |
| §2-11 ai | 13 endpoint + 18-1~18-7 패키지 + manual_qa wrapper 시그니처 |
| §2-13 availability | 점심창 `_lunch_window` ([api.py:64-107](../../app/routers/api.py:64)) + 휴무 차단 + 반차 차단 (확인 필요 — 반차 코드 위치) |
| §2-26 cancellations / no_show | `Appointment.status="canceled"` 만 + 노쇼 별도 필드 부재 명시 |
| §31 우선순위 14 | core 1번 → appointments 14번 — 의존도 합리적 |
| §37 DB schema 무관 | m001~m013 그대로 진행 가능 13 modules + core |

### 검증 명령 모음

```bash
# 모듈별 라인 정합
grep -n "_doctor_codes_set\|is_doctor_filter\|_upsert_employee_leave_core\|_check_version\|_bump_version\|_bump_patient_count" app/routers/api.py
grep -n "_lunch_window\|_check_lunch_block" app/routers/api.py
grep -n "manual60" app/models/constants.py app/routers/api.py
grep -nE "^@router\.(get|post|patch|put|delete)\(" app/routers/api.py | wc -l    # 86
grep -nE "^@router\.(get|post|patch|put|delete)\(" app/routers/ai.py | wc -l     # 13

# 의사 EMR 부재 검증
grep -nE "doctor_id|class Doctor\(Base\)|class Order\(Base\)|class Prescription\(Base\)|class Resource\(Base\)|class DoctorSchedule\(Base\)" app/models/models.py
# 결과: 없어야 함

# leave_type 반차 값 (T-13 19-P-2 / availability 보강 필요)
grep -nE "leave_type|반차|half_morning|half_afternoon" app/routers/api.py app/services/ai/action_leave.py
```

## 9. 빠진 기능 / 책임이 없는지 확인할 항목

| 책임 (사용자 §1 + 추가 보완) | 본 문서 위치 |
|---|---|
| 예약 생성/수정/삭제/조회 | §2-1 |
| 예약 취소 / 노쇼 후보 | §2-26 (cancellations / no_show) |
| 예약 가능 시간 계산 | §2-13 (availability) |
| 중복 예약 방지 | §2-1 (`_check_version`) + §2-13 |
| 치료사 휴무 차단 | §2-13 + §2-5 |
| 오전반차/오후반차 차단 | §2-13 (확인 필요 — `leave_type` 값 매핑) |
| 환자 정보 / 신환 / 메모 | §2-2 + §2-14 |
| 당일 메모 vs 지속 메모 | §2-14 (notes — 후속 검토) |
| 치료사 정보 | §2-3 |
| 의사 / 진료진 / 담당의 | §2-4 |
| 치료항목 + 도수치료 시간별 + ESWT | §2-6 |
| 완료체크 + 항목별 카운트 | §2-6 (completion_rules) |
| 통계 집계 | §2-7 |
| 예약문자 + 문자나라 연동 | §2-8 |
| 관리자 설정 / AI 설정 / API key 비노출 | §2-9 + §2-16 |
| 백업/복구 | §2-10 |
| AI/RAG/Safety/Vector/Hybrid | §2-11 |
| health/diagnostics | §2-19 (후속) |
| export/import | §2-18 |
| audit/logs | §2-17 |
| feature flag | §2-21 |
| PyInstaller 배포 안정성 | §39 (주석 필요 위험 지점) |

## 10. 현재 없는 기능을 구현된 것처럼 단정하지 않았는지 확인할 항목

| 모듈 | 분류 | 검증 |
|---|---|---|
| §2-12 calendar | 후속 검토 | "서버 사이드 view-model 부재" 명시 |
| §2-19 health | 후속 검토 | "전용 부재 — `/api/admin/status` 만" 명시 |
| §2-27 recurring_appointments | 후속 검토 | "현재 부재" 명시 |
| §2-28 resources | 후속 검토 | "Resource 모델 부재" 명시 |
| §2-29 printing | 후속 검토 | "현재 부재" 명시 |
| §2-30 notifications | 후속 검토 | "알림 테이블 부재" 명시 |
| §2-26 cancellations | 부분 존재 (취소만) | "노쇼 별도 필드 부재" 명시 |
| §2-4 doctors EMR | 부분 존재 (분기만) + 후속 검토 (EMR) | "Patient.doctor_id, Doctor 별도 테이블, Department, Room, DoctorSchedule, Order, Prescription 부재" 명시 |
| §2-13 availability | 부분 존재 | "오전/오후 반차 차단 코드 위치는 별도 grep 필요" 명시 |
| §2-21 feature_flags | 부분 존재 | "환경 변수 — 확인 필요" 명시 |

→ 본 문서는 모든 부재 항목을 "부재" 또는 "부분 존재" 또는 "후속 검토" 로 분류 — 단정 X.

## 11. 주석 / 문서화 기준이 모듈 매핑에 반영되었는지 확인할 항목

| 카테고리 | §39 위험 지점 |
|---|---|
| `# COMPAT:` (응답 키 / wrapper / alias) | manual_qa 9키 빌더 / wrapper 시그니처 / `_upsert_employee_leave_core` / treatment-meta / therapist alias / restore atomic / ENTITY_MAP / spec hidden imports |
| `# SAFETY:` (PII / 운영 DB / 외부 API / API key) | PII 마스킹 + sha256 + 200자 cap / munjanara_key / API key / FakeProvider / restore engine.dispose |
| `# NOTE:` (업무 규칙 / 정책) | manual60=1 / LOW_SCORE_THRESHOLD=2 / HIGH/LOW=0.7/0.3 / 점심창 / role=doctor 분기 / per-file-ignores / 자동 백업 타이머 |
| `# RISK:` (TOCTOU / 동시성 / 외부 노드) | 낙관적 락 / split-code TOCTOU / AI action_leave HMAC / reindex lock / atomic rename / ENTITY_MAP / spec hidden imports |
| `# TODO(19-P-N):` (wrapper 일시 보유 + 제거 조건) | 모든 wrapper 함수 — 분리 후 N+1 세션에서 제거 조건 명시 |

→ §0-2 주석 카테고리 정의 + §39 19개 위험 지점에서 모두 분류됨.

## 12. 다음 단계 (19-P-4 의존성 맵) 진입 가능 판단 기준

Codex 가 다음 6개 게이트를 모두 통과 처리할 때만 19-P-4 진입.

| 게이트 | 통과 조건 |
|---|---|
| G-1 코드 무수정 | `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements*.txt app/templates app/static pyproject.toml` 출력이 18-0~18-8 변경분만 + 본 19-P-3 추가 변경분 0. 19-P-1 / 19-P-2 산출물 무수정. |
| G-2 매핑 정합 | 30 모듈 § 의 라인 번호 / 함수명 / 클래스명 / 응답 키 셋이 19-P-1 r2 / 19-P-2 r3 통과본과 100% 일치 |
| G-3 응답 키 / URL 후방호환 | §35 응답 키 위험 모듈 표 + §39 COMPAT 주석 위치가 명시 |
| G-4 AI/RAG local-first 보존 | §2-11 ai 책임에 local-first / 의사 정보 임의 생성 금지 / manual_qa wrapper 시그니처 보존 명시 |
| G-5 후속 검토 분류 적절성 | §2-12 / §2-19 / §2-27~§2-30 / §2-26 노쇼 모두 *현재 부재* 또는 *부분 존재* 로 분류 — 추측 단정 X |
| G-6 doctors / medical_staff 검토 | §2-4 doctors / §2-3 therapists (staff 통합) + §38 doctors 별도 모듈 / Patient.doctor_id / DoctorSchedule / Order / Prescription / 의사 가드 모두 후속 검토 분류 |

→ G-1 ~ G-6 전부 통과 시 **yes — 19-P-4 진입 가능**.

→ 1개라도 실패 시 Codex 응답에 "재작업 필요"로 표기하고 사용자가 19-P-3 후속 보강 (r2) 결정.

## 13. Codex 가 반드시 확인할 항목 (사용자 명시)

| 검증 항목 | 본 문서 위치 |
|---|---|
| 이번 세션에서 `app/`, `tests/`, migrations, requirements.txt, PyInstaller spec, UI 파일이 수정되지 않았는가 | §5 / §6 |
| `docs/refactor/19_refactor_module_map.md` 가 작성/수정되었는가 | §3 신규 |
| `reports/refactor/{19-P-3,latest}_codex_review_request.md` 가 작성되었는가 | §3 신규 |
| 현재 파일 / API / DB / UI 위치와 목표 모듈 매핑이 실제 구조와 크게 어긋나지 않는가 | §8 (10개 검증 항목) |
| 예약/환자/치료사/의사/휴무/치료항목/완료체크/통계/문자/관리자/백업/AI/RAG 매핑이 빠지지 않았는가 | §9 (21개 책임 항목) |
| calendar / availability / notes / permissions / settings / audit / export_import / health / feature_flags / jobs / privacy / locking / time_utils 보조 기능 검토 | §2-12 ~ §2-25 |
| 현재 없는 기능은 후속 검토로 분류했는가 | §10 (10개 부재 항목) |
| 리팩토링 위험도와 난이도가 현실적으로 표시되었는가 | §2-1~§2-30 매핑표 + §33 위험 모듈 + §31 우선순위 |
| 기존 API 응답 key 와 프론트 호환 주의사항 표시 | §35 + §36 |
| 향후 코드 이동 시 COMPAT / SAFETY / NOTE / RISK 주석 지점 반영 | §0-2 + §39 (19개 위험 지점) |
| 다음 단계 19-P-4 의존성 맵 진입 가능 | §12 G-1 ~ G-6 |

## 14. Codex 검증 결과 기록 위치

Codex 는 검증 결과를 다음 2개 파일에 동일 내용으로 작성한다.

- [reports/refactor/19-P-3_codex_review.md](19-P-3_codex_review.md) (영구 보존본)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (다음 세션 진입 시 참조 — 19-P-2 r3 pass 본문 위에 19-P-3 으로 덮어쓰기)

응답 형식 권장 (필수 아님):

```markdown
# 19-P-3 Codex 검증 결과

## 1. 종합 판정
{pass | fail}

## 2. 게이트별 결과
- G-1 코드 무수정: {pass|fail} — 근거
- G-2 매핑 정합: {pass|fail} — 근거
- G-3 응답 키 / URL 후방호환: {pass|fail} — 근거
- G-4 AI/RAG local-first: {pass|fail} — 근거
- G-5 후속 검토 분류 적절성: {pass|fail} — 근거
- G-6 doctors/medical_staff: {pass|fail} — 근거

## 3. 추가 발견 위험 / 누락 / 부정확 항목
{있으면 bullet}

## 4. 19-P-4 진입 권고
{yes/no + 근거}
```

## 15. Claude Code 자체 판단

**yes (19-P-4 진입 권고)** — Codex 검증 후 다음 세션 진입 가능.

근거:
1. 본 세션은 read-only — 코드 변경 0, 응답 키/마이그레이션/spec/UI/테스트 무수정.
2. `docs/refactor/19_refactor_module_map.md` 30 모듈 § + 9 하단 섹션 + §40 종합 = 사용자 §1-30 + §31-39 모두 커버.
3. 19-P-1 §22 C-1~C-7 + 19-P-2 §9 M-01~M-36 + M-03b 모든 매핑이 본 문서 §2 와 1:1 정합.
4. 추측 단정 회피 — 현재 부재 항목 (calendar / health / EMR / 노쇼 / recurring / printing / notifications / resources) 모두 후속 검토 또는 부분 존재 분류.
5. 의사 / 진료진 보강 — §2-4 + §39 (의사 단정 가드 후속) + §38 (M-31~M-36 후속 분류).
6. 응답 키 보호 — §35 (현재 contract 작성 모듈 / 미작성 모듈 분리) + §39 COMPAT 위험 지점 명시.
7. 주석 카테고리 (COMPAT/SAFETY/NOTE/RISK/TODO) — §0-2 정의 + §39 19개 위험 지점에서 분류.
8. 18-8 baseline 회귀 보호 100%.
9. 19-P-1 / 19-P-2 산출물 무수정.

남은 위험:
- T-1 ~ T-15 의사결정 항목 — 19-P-4 의존성 맵 단계에서 일부 결정.
- 비-AI 86 endpoint 응답 키 전수표 (C-1~C-7) — 도메인 분리 *직전* 별도 보강 (§34 명시).
- §2-13 availability 의 오전/오후 반차 차단 코드 위치 — 별도 grep 후 보강 가능 (확인 필요).
- 18-0~18-8 변경분 main 머지 / `docs/ai_rag_current_state.md` stale 보정 — 19-P-1 r2 §3 권고 그대로 별도 세션.
- 세션 경계 Git 검증 caveat — 18-0~18-8 미커밋 (이전 세션부터 알려진 사항).
