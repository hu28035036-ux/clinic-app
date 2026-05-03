# 19-P-2 Codex 검증 요청서 (revision 3 — r2 G-5 카운트 fail 후 보정본)

> **사용자가 Codex에게 전달할 최소 문구**
>
> > "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

## 0. Revision 이력

| 회차 | 날짜 | 결과 | 변경 |
|---|---|---|---|
| r1 | 2026-05-02 | **fail** (G-5 fail — V2 트리 vs 후속 검토 경계 모순 + 항목 수 36 vs 실제 37 + A/B/C 카운트 모호) | 초기 작성 |
| r2 | 2026-05-02 | **fail** ([reports/refactor/latest_codex_review.md](latest_codex_review.md), G-5 fail — modules 개수 표기 오류: "modules 11개" vs 실제 13개, "다음 4개 모듈" vs 실제 6개) | §2-1 V2 트리 정리 + §2-2 후속 블록 분리 + §9 항목 수 정정 + A/B/C 카운트 재계산 |
| r3 | 2026-05-02 | (본 revision) | **카운트 정정**. `docs/refactor/19_refactor_target_architecture.md` 의 §0 / §2-1 / §2-2 / §12 4개 위치에서 modules 개수 정정: "11개 → 13개" + "4개 모듈 → 6개 모듈". §0 메타에 r3 caveat. 코드/테스트/spec/UI/migrations/requirements 무수정 유지. Codex 재검증 요청. |

본 요청서는 19-P 단위화 리팩토링 두 번째 세션의 산출물 (목표 모듈 구조 설계 문서) 1건을 Codex 가 독립적으로 검증할 수 있도록 작성한 표준 패키지다.

---

## 0. Baseline (D안 — 19-P-1 r2 통과 후 동일)

- HEAD commit (full sha): `bcd74a7aabc9de8d735425863254cfc393bda580`
- HEAD short: `bcd74a7` — release v1.3.3: AI/RAG v1 후속 보강 + SDK 진단 강화
- 브랜치: `ai-rag-v1-integration`
- 19-P-1 결과: Codex r2 **pass** ([reports/refactor/19-P-1_codex_review.md](19-P-1_codex_review.md))
- 본 세션은 위 commit 위에 신규 commit 없이 untracked 파일 추가 + 기존 untracked 문서 수정만 수행. 코드/테스트/spec/UI/migrations/requirements 1바이트도 수정 금지.

---

## 1. 세션 이름

**19-P-2 단위화 리팩토링 목표 모듈 구조 설계**

- 19-P-1 ([19_refactor_current_state.md](../../docs/refactor/19_refactor_current_state.md) 24개 섹션 — Codex r2 pass) 의 현재 구조 스냅샷을 기준으로, **이후 단계적 분리 후 도달할 목표 모듈 구조** 를 설계한다.
- read-only 문서 세션. 실제 코드 이동 없음.
- 사용자 추가 보완: **의사 / 진료진 관련 책임 (doctors / medical_staff)** 누락 방지 — 본 r1 에서 §3-3 staff (doctors+therapists 통합) + §4 분류표 doctors 항목 + §9 M-03b/M-31~M-36 추가.

## 2. 이번 세션 목표

| # | 목표 |
|---|---|
| 1 | 사용자 §1 12개 설계 원칙 정리 (P-1 ~ P-12) |
| 2 | 목표 폴더 구조 (V2) 설계 — `app/core/` + `app/modules/{appointments,patients,staff,leaves,treatments,stats,sms,admin,backup,ai,audit,settings,export_import,health}/` |
| 3 | 핵심 10개 모듈 책임 정의 — appointments/patients/staff/leaves/treatments/stats/sms/admin/backup/ai |
| 4 | 보조/공통 18개 항목 분류 — calendar/availability/notes/permissions/settings/audit/export_import/health/responses+errors/feature_flags/batch+jobs/printing/notifications/cancellations/recurring/resources/privacy/concurrency/time_utils + doctors/medical_staff (사용자 추가) |
| 5 | 파일별 책임 기준 (router/service/repository/schemas/rules/availability/templates/provider/aggregators/completion_rules/view_models/diagnostics/responses/errors/feature_flags) |
| 6 | 모듈 간 의존성 방향 (router → service → repository → models, core 단방향, 도메인 간 read/write 매트릭스) |
| 7 | 호환성 보존 정책 (URL/응답 키/DB schema/UI/하네스/PyInstaller/AI local-first) |
| 8 | 단계 이동 원칙 (wrapper → 위임 → 제거, 5회 루프, rollback) |
| 9 | 모듈 분류표 (M-01 ~ M-36) — 즉시분리/하위책임/후속검토 + 난이도/위험도/선행테스트/관련 API/DB/UI/주의사항 |
| 10 | 보류 / 후속 검토 항목 정리 + 확인 필요 (T-1 ~ T-15) |

## 3. 작성한 문서

### r1 (초기 작성)

- [docs/refactor/19_refactor_target_architecture.md](../../docs/refactor/19_refactor_target_architecture.md) — 목표 모듈 구조 설계 (12 섹션 + 모듈 분류표 + 확인 필요 15항목).

### r2 (r1 G-5 fail 후 보정)

- `docs/refactor/19_refactor_target_architecture.md` — 보정 (r1과 동일 파일 갱신).
  - §0 메타: r2 보정 caveat 추가 + 19-P-1 Codex 결과 링크 정정 (`19-P-1_codex_review.md` 영구 보존본).
  - §2-1 V2 트리: `health/`, `calendar/`, `notes/` 3개 모듈 제거 → §2-2 로 이동.
  - §2-2: 후속 검토 블록 재구성 (calendar / notes / health / doctors / resources / emr) + sms.provider 시점 + sync 위치 + AI 의사 가드.
  - §3-8 admin: "modules/health 위임" → "modules/admin 안 + health 신설은 post-19-P" 정정.
  - §4 health / calendar / notes 행: 후속 검토 (post-19-P, M-26/M-27/M-28) 명시.
  - §12 종합: 분류표 합계 **37행** + 분류 카운트 **A=21 / B=6 / C=10**.

### r3 (r2 G-5 fail 카운트 오류 정정)

- `docs/refactor/19_refactor_target_architecture.md` — 보정 (r2와 동일 파일 갱신).
  - §0 메타: r3 caveat 추가 + r1/r2 보정 이력 보존.
  - §2-1 V2 트리 머리말: "modules **11개** + core" → "modules **13개** + core (총 14개)" + 13개 명시 (appointments / patients / staff / leaves / treatments / stats / sms / admin / backup / ai / audit / settings / export_import).
  - §2-2 후속 블록 머리말: "다음 **4개** 모듈" → "다음 **6개** 모듈" + 6개 ID 명시 (M-26/M-27/M-28/M-31/M-33/M-35).
  - §12 종합: "총 **modules 11개** + core" → "총 **modules 13개** + core".
  - 표제: "r2 보정본" → "r3 보정본".

### 함께 작성한 검증 패키지

- [reports/refactor/19-P-2_codex_review_request.md](19-P-2_codex_review_request.md) (본 문서, 영구 보존본 — r1 작성 후 r2 갱신)
- [reports/refactor/latest_codex_review_request.md](latest_codex_review_request.md) (Codex 진입점 — 본 문서와 동일)
- (Codex 작성) [reports/refactor/19-P-2_codex_review.md](19-P-2_codex_review.md) (r1 결과 — fail) + [reports/refactor/latest_codex_review.md](latest_codex_review.md) (Codex 가 r2 검증 결과를 같은 위치에 덮어쓸 것)

## 4. 수정 금지였던 범위

사용자 지시문 12개 금지 항목:

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
12. (CLAUDE.md 명시) `manual60` count_increment 변경 금지 + `pyproject.toml` `app/**` per-file-ignores 변경 금지

추가:
- 18-0~18-8 baseline (529 passed, 1 skipped, 7 xfailed) 회귀 보호.
- m001~m013 마이그레이션 diff 0 유지.
- 19-P-1 r2 보정본 ([19_refactor_current_state.md](../../docs/refactor/19_refactor_current_state.md)) 무수정 유지.

## 5. 실제 수정한 파일 목록

### r1 신규 (3, 1차 작성 시점)

- `docs/refactor/19_refactor_target_architecture.md`
- `reports/refactor/19-P-2_codex_review_request.md` (본 문서)
- `reports/refactor/latest_codex_review_request.md`

### r2 수정 (3, r1 G-5 fail 후 보정)

- `docs/refactor/19_refactor_target_architecture.md` (수정 — V2 트리 / 후속 블록 분리 + 항목 수 정정 + 카운트 재계산)
- `reports/refactor/19-P-2_codex_review_request.md` (본 문서, r2 revision 추가)
- `reports/refactor/latest_codex_review_request.md` (본 문서와 동기화)

### r3 수정 (3, r2 G-5 fail 카운트 오류 정정)

- `docs/refactor/19_refactor_target_architecture.md` (수정 — modules 11→13 + 4→6 + 표제 r3)
- `reports/refactor/19-P-2_codex_review_request.md` (본 문서, r3 revision 추가)
- `reports/refactor/latest_codex_review_request.md` (본 문서와 동기화)

### 무수정 (회귀 보호) — r1 / r2 / r3 동일

`app/**`, `tests/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`, `CLAUDE.md`, `app/models/models.py`, `app/routers/api.py`, `app/routers/ai.py`, `tests/conftest.py`, `app/services/**`.

19-P-1 산출물 (`19_refactor_current_state.md`, `19-P-1_codex_review_request.md`, `19-P-1_codex_review.md`) 도 본 19-P-2 (r1+r2 통틀어) 세션에서 미수정.

> 단, 19-P-2 r1 진행 중 사용자 추가 보완 (doctors/medical_staff) 요청 후 `docs/refactor/19_refactor_target_architecture.md` 의 §2 / §3-1 / §3-2 / §3-3 / §3-6 / §3-7 / §3-8 / §3-10 / §4 / §9 / §10 / §11 / §12 다수 섹션을 동일 파일 내에서 보강. r2 에서 §0 / §2-1 / §2-2 / §3-8 / §4 / §12 추가 보정. 신규 파일은 위 3개 외 추가 없음.

### 무수정 (회귀 보호)

`app/**`, `tests/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`, `CLAUDE.md`, `app/models/models.py`, `app/routers/api.py`, `app/routers/ai.py`, `tests/conftest.py`, `app/services/**`, `docs/refactor/19_refactor_current_state.md` (19-P-1 산출물 보존).

## 6. 코드 수정 없이 docs/refactor + reports/refactor 문서만 작성했는지 확인

### Claude Code 자체 점검

| 검사 | 결과 |
|---|---|
| 본 19-P-2 세션이 새로 만든 파일 | `docs/refactor/19_refactor_target_architecture.md` + `reports/refactor/{19-P-2,latest}_codex_review_request.md` |
| `app/**` 변경 | 0 |
| `tests/**` 변경 | 0 |
| `app/migrations/**` 변경 | 0 |
| `requirements*.txt` 변경 | 0 |
| `dosu_clinic.spec` 변경 | 0 |
| `app/templates/**` 변경 | 0 |
| `app/static/**` 변경 | 0 |
| `pyproject.toml` 변경 | 0 |
| 19-P-1 산출물 (`19_refactor_current_state.md`) 변경 | 0 |

→ **코드 수정 없이 docs/refactor + reports/refactor 문서만 작성**.

### Codex 가 직접 검증할 명령

```bash
git status --short
git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml
# 결과: 18-0~18-8 변경분만 표시되어야 하며, 본 19-P-2 세션의 추가 변경분은 0
```

또한 19-P-1 산출물이 본 세션에서 변경되지 않았는지:

```bash
# 19-P-1 r2 통과본 hash 와 현재 파일 hash 가 동일해야 함
sha256sum docs/refactor/19_refactor_current_state.md
sha256sum reports/refactor/19-P-1_codex_review_request.md
sha256sum reports/refactor/latest_codex_review_request.md  # 단, 본 19-P-2에서 r2→r3 동일 위치 덮어쓰기로 사용됨
```

→ `latest_codex_review_request.md` 는 19-P-2 r1 진입점으로 덮어쓰여졌다. 19-P-1 r2 본문은 `19-P-1_codex_review_request.md` 영구 보존본에 보존.

## 7. Codex 가 검증해야 할 문서

### 1차 (필수)

- [docs/refactor/19_refactor_target_architecture.md](../../docs/refactor/19_refactor_target_architecture.md) (본 세션 신규)

### 2차 (대조 기준)

- [docs/refactor/19_refactor_current_state.md](../../docs/refactor/19_refactor_current_state.md) (19-P-1 r2 통과본 — 현재 구조 단정)
- [docs/refactor/19_refactor_entry_notes.md](../../docs/refactor/19_refactor_entry_notes.md) (19-P 진입 기준 노트)
- [docs/AI_WORKING_RULES.md](../../docs/AI_WORKING_RULES.md) (AI/RAG 절대 원칙 — local-first 보존)
- [docs/ai_rag_architecture_plan.md](../../docs/ai_rag_architecture_plan.md) (RAG 목표 아키텍처 — 본 문서 §3-10 ai 정합)
- [docs/releases/18_ai_rag_release_notes.md](../../docs/releases/18_ai_rag_release_notes.md) (18-0~18-8 결과)
- [reports/refactor/19-P-1_codex_review.md](19-P-1_codex_review.md) (직전 r2 pass 결과)
- [CLAUDE.md](../../CLAUDE.md) (manual60=1 + per-file-ignores 정책)

## 8. 목표 모듈 구조가 현재 구조와 맞는지 확인할 항목

| 항목 | 검증 방법 |
|---|---|
| §2 폴더 구조 V2 의 modules 14개 | [19_refactor_current_state.md §1](../../docs/refactor/19_refactor_current_state.md) 의 현재 구조 트리와 1:1 대응 가능한지 |
| §3-1 appointments | 라인 1608-2057 (10개 endpoint) 가 실제 [api.py](../../app/routers/api.py) 에 존재하는지 |
| §3-3 staff (doctors+therapists 통합) | `Employee` 단일 테이블 + `role` 컬럼 ("doctor"/"therapist") 분기인지 — `grep -n "ROLE_DOCTOR\|ROLE_THERAPIST" app/models/constants.py` |
| §3-3-3 doctors 책임 | `_doctor_codes_set()` 가 [api.py:153-156](../../app/routers/api.py:153) 에 존재 + `is_doctor_filter` 가 [api.py:3464](../../app/routers/api.py:3464) 에 존재 + role=doctor handler 검증이 [api.py:1773-1775](../../app/routers/api.py:1773) 에 존재하는지 |
| §3-3-4 부재 항목 (진료과/진료실/담당의/오더/처방/EMR) | 실제로 부재 — `grep -nE "doctor_id\|department\|prescription\|order\|EMR" app/models/models.py` 결과가 비어야 함 (Patient.doctor_id / Doctor 테이블 / Order / Prescription 클래스 부재 확인) |
| §6 의존성 방향 | 현재 코드의 import 그래프와 정합 — `core → modules` 단방향 가능한가 |
| §7-1 API URL 보존 | 19_refactor_current_state.md §3 의 86 + 13 + 2 endpoint URL 모두 V2 에서도 동일 |
| §7-3 DB schema 보존 | m001~m013 diff 0 정책 명시 |
| §9 분류표 M-01 ~ M-36 | 각 항목의 "현재 위치" 라인 번호가 실제 `app/routers/api.py` 또는 `app/services/**` 에 존재 |
| §11 확인 필요 T-1 ~ T-15 | 본 세션 read-only 범위에서 진짜 결정 불가능한 항목인지 |

### 검증 명령 모음

```bash
# 현재 구조와 정합 검증
grep -nE "ROLE_DOCTOR|ROLE_THERAPIST" app/models/constants.py
grep -n "_doctor_codes_set\|is_doctor_filter" app/routers/api.py
grep -nE "doctor_id|department|prescription|class Order|class Prescription|class Doctor\(Base\)" app/models/models.py
grep -n "_seed_demo_data" app/services/seed.py    # 비활성화 확인 (line 21)
grep -nE "^class \w+\(Base\)" app/models/models.py | wc -l   # 19 (변동 없음)

# §9 분류표 라인 검증
grep -n "_doctor_codes_set\|change_assignment\|stats_by_therapist" app/routers/api.py
grep -n "is_doctor_filter" app/routers/api.py    # 3464

# AI safety 가드 패턴 (M-36 후속 검토 근거)
grep -n "_RE_MEDICAL_CLAIM\|_RE_EXECUTION_CLAIM" app/services/ai/rag/pipeline.py
```

## 9. 빠진 기능 / 책임이 없는지 확인할 항목

> 사용자 §3 핵심 책임 + §4 보조/공통 + 추가 보완 (doctors) 모두 §3 또는 §4 또는 §9 에 분류되었는지.

| 책임 | 본 문서 위치 |
|---|---|
| 예약 (appointments) | §3-1, §9 M-01 |
| 환자 (patients) | §3-2, §9 M-02 |
| **의사 / 진료진 (doctors / medical_staff)** | §3-3-3, §4 doctors/medical_staff 행, §9 M-03b + M-31~M-36 |
| 치료사 (therapists) | §3-3-2, §9 M-03 |
| 휴무 (leaves) | §3-4, §9 M-04 |
| 치료항목 (treatments) | §3-5, §9 M-05 |
| 완료체크 (completion) | §3-5 + completion_rules, §9 M-06 |
| 통계 (stats) | §3-6, §9 M-07 + M-08 |
| 문자 (sms) | §3-7, §9 M-09 + M-29 |
| 관리자 (admin) | §3-8, §9 M-10 + M-16 |
| 백업 (backup) | §3-9, §9 M-11 |
| AI / RAG | §3-10, §9 M-17~M-24 |
| sync (분산) | §6-2, §9 M-13 (후속 검토) |
| audit | §4 audit/logs, §9 M-14 |
| settings | §4 settings, §9 M-15 |
| export_import | §4, §9 M-12 |
| calendar / view-model | §4, §9 M-26 (후속) |
| availability | §4, §3-1 / availability.py |
| notes | §4, §9 M-27 (후속) |
| permissions / auth | §4, core/security |
| feature_flags | §4, §9 M-30 |
| batch / jobs | §4, 후속 |
| printing / notifications / recurring / resources | §4, 후속 |
| privacy / retention | §4, modules/ai/safety + audit |
| concurrency / locking | §4, 각 모듈 하위 |
| time_utils | §4, core/time_utils.py |
| **EMR 연동 (담당의 / 진료과 / 진료실 / 오더 / 처방)** | §3-3-4, §10 의사 EMR 연동 행, §9 M-31~M-35 (모두 후속) |
| **AI 의사 hallucination 가드** | §3-10, §9 M-36 (후속) |

## 10. 과도하게 이상적인 구조인지 확인할 항목

| 항목 | Codex 판정 기준 |
|---|---|
| `modules/calendar/` 신설 | 본 19-P 비-목표로 분류 (§9 M-26 = C 후속) — pass |
| `modules/notes/` 신설 | 정책 미결정으로 분류 (§9 M-27 = C 후속) — pass |
| `modules/health/router.py` 신규 (`/api/health`) | 추가 결정 필요로 분류 (§9 M-28 = C 후속) — pass |
| `modules/doctors/` 별도 분리 | EMR 연동 도입 시로 분류 (§9 M-31 = C 후속) — pass. **현재는 `modules/staff/doctors_service.py` 하위 책임 (M-03b)** 으로 통합. |
| `modules/resources/` (진료실 / 장비) | 후속 검토 (§9 M-33 = C) — pass |
| `modules/emr/` (오더 / 처방) | 후속 검토 (§9 M-35 = C) — pass |
| `core/` 신설 (config / database / errors / responses / time_utils / security / feature_flags) | 모든 modules 가 의존 — 즉시 분리 우선순위 1번 (§9-1) — pass. 단, 한 번에 7개 파일 생성은 부담 — 단계 이동 권장 (T-3 결정 필요). |
| `modules/sync/` 위치 | 도메인이 아니라 인프라 — `services/sync.py` 그대로 vs `core/sync.py` 결정 필요 (T-3) |
| 단계 이동 14순서 (§9-1) | M-25 core 1순위 → M-01 appointments 14순위 (마지막) — 의존도 기반 합리적 |

→ Codex 가 *너무 새 폴더가 많다* 고 판정 시 추가 통합 권고 가능.

## 11. 다음 단계 (19-P-3 모듈 매핑) 진입 가능 판단 기준

Codex 가 다음 6개 게이트를 모두 통과 처리할 때만 19-P-3 진입.

| 게이트 | 통과 조건 |
|---|---|
| G-1 코드 무수정 | `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements*.txt app/templates app/static pyproject.toml` 출력이 18-0~18-8 변경분만 포함하고 본 19-P-2 세션의 추가 변경분 0. 19-P-1 산출물 (`19_refactor_current_state.md` 등) 도 무수정. |
| G-2 현재 구조와 정합 | §3 / §9 의 라인 번호 / 함수명 / 클래스명이 19-P-1 r2 통과본과 100% 일치 |
| G-3 응답 키 / URL 후방호환 보존 원칙 명시 | §7-1 (URL) + §7-2 (응답 키) + §7-3 (DB schema) 정책이 명시되었는지 |
| G-4 AI/RAG local-first 보존 | §7-7 + §3-10 + §6-1 ai/rag → 도메인 의존성 ❌ 명시 |
| G-5 후속 검토 분류 적절성 | §4 / §9-2 / §10 의 후속 검토 항목 (M-13/M-26/M-27/M-28/M-31~M-36) 이 *현재 부재* 인지 검증 — 추측으로 단정 X. **r2 보정**: §2-1 V2 트리 vs §2-2 후속 검토 경계가 모순 없이 분리되었는지 (r1 G-5 fail 핵심) — `calendar/`, `notes/`, `health/` 가 §2-1 V2 에서 제거되고 §2-2 post-19-P 블록에만 존재하는지. |
| G-6 doctors/medical_staff 검토 누락 0 | §3-3 staff (doctors+therapists 통합) + §4 doctors/medical_staff 행 + §9 M-03b + M-31~M-36 모두 존재. 의사 EMR 연동 (담당의/진료과/진료실/오더/처방) 후속 검토로 분류, 실제 구현 대상으로 단정 X. AI 의사/진료진 정보 임의 생성 금지 §3-10 명시. |

→ G-1 ~ G-6 전부 통과 시 **yes — 19-P-3 진입 가능**.

→ 1개라도 실패 시 Codex 응답에 "재작업 필요"로 표기하고 사용자가 19-P-2 후속 보강 (r2) 을 결정.

## 12. Codex 가 반드시 확인할 항목 (사용자 명시)

| 검증 항목 | 본 문서 위치 |
|---|---|
| 이번 세션에서 `app/`, `tests/`, migrations, requirements.txt, PyInstaller spec, UI 파일이 수정되지 않았는가 | §5 / §6 |
| `docs/refactor/19_refactor_target_architecture.md` 가 작성/수정되었는가 | §3 (신규) |
| 목표 구조가 현재 프로젝트 구조에서 단계적으로 이동 가능한가 | §8 + §9-1 (14순서 권장) |
| 예약/환자/치료사/휴무/치료항목/완료체크/통계/문자/관리자/백업/AI 모듈 책임이 명확한가 | §3-1 ~ §3-10 |
| calendar / availability / notes / permissions / settings / audit / export_import / health / core responses+errors / feature_flags / batch+jobs / privacy+retention / concurrency+locking / time_utils 같은 빠지기 쉬운 책임이 검토되었는가 | §4 (18개 행) |
| 현재 기능에 없는 항목을 실제 구현 대상으로 단정하지 않고 후속 검토로 분류했는가 | §9-2 (M-13/M-26/M-27/M-28/M-31~M-36 = C) + §10 |
| router/service/repository/schemas/rules 책임이 명확한가 | §5 (15개 파일 패턴) |
| 기존 API URL 과 응답 key 유지 원칙이 명확한가 | §7-1 + §7-2 |
| 기존 UI / DB / PyInstaller 안정성 유지 원칙이 있는가 | §7-3 + §7-4 + §7-6 |
| AI/RAG local-first 원칙이 보존되는가 | §7-7 + §3-10 |
| 실제 코드 이동을 이번 세션에서 하지 않았는가 | §5 (수정 0) + §10 (보류) |
| 다음 단계 19-P-3 모듈 매핑 문서로 넘어가도 되는가 | §11 G-1 ~ G-6 |
| **의사 / 진료진 관련 책임이 빠지지 않았는가** | §3-3 (staff 통합) + §4 (doctors/medical_staff 행) + §9 (M-03b + M-31~M-36) |
| **현재 기능에 없는 의사 기능을 실제 구현 대상으로 단정하지 않고 후속 검토로 분류했는가** | §3-3-4 부재 항목 명시 + §9-2 M-31~M-36 = C + §10 EMR 연동 행 |
| **담당의 / 진료과 / 진료실 / 오더 / 처방 / EMR 연동 경계가 문서에 후보로 남아 있는가** | §3-3-4 + §4 doctors 행 + §9 M-31~M-35 + §10 |

## 13. Codex 검증 결과 기록 위치

Codex 는 검증 결과를 다음 2개 파일에 동일 내용으로 작성한다.

- [reports/refactor/19-P-2_codex_review.md](19-P-2_codex_review.md) (영구 보존본)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (다음 세션 진입 시 참조 — r2 pass 본문 위에 r3 으로 덮어쓰기)

응답 형식 권장 (필수 아님):

```markdown
# 19-P-2 Codex 검증 결과

## 1. 종합 판정
{pass | fail}

## 2. 게이트별 결과
- G-1 코드 무수정: {pass|fail} — 근거
- G-2 현재 구조 정합: {pass|fail} — 근거
- G-3 응답 키/URL 후방호환 원칙: {pass|fail} — 근거
- G-4 AI/RAG local-first 보존: {pass|fail} — 근거
- G-5 후속 검토 분류 적절성: {pass|fail} — 근거
- G-6 doctors/medical_staff 검토: {pass|fail} — 근거 (의사 EMR 후속 분류 + AI 가드 정책 포함)

## 3. 추가 발견한 위험 / 누락 / 부정확 / 과도한 이상화 항목
{있으면 bullet}

## 4. 19-P-3 진입 권고
{yes/no + 근거}
```

## 14. Claude Code 자체 판단

**yes (19-P-3 진입 권고)** — Codex 검증 후 다음 세션 진입 가능.

근거 (r3 기준):
1. 본 세션 (r1+r2+r3 통틀어) 은 read-only — 코드 변경 0, 응답 키/마이그레이션/spec/UI/테스트 무수정.
2. `docs/refactor/19_refactor_target_architecture.md` 12 섹션 + 모듈 분류표 **37행** (M-01~M-36 + M-03b) + 확인 필요 15항목 (T-1~T-15) 이 사용자 §1~§10 + 추가 보완 (doctors/medical_staff) 모두 커버.
3. **r2 보정으로 V2 트리 vs 후속 검토 경계 모순 해소** + **r3 보정으로 modules 카운트 정정** — calendar/notes/health 3개를 §2-2 post-19-P 후보 블록으로 분리. V2 트리는 modules **13개** + core (14개) 만 포함. post-19-P 후보 블록은 **6개 모듈** (calendar/notes/health/doctors/resources/emr).
4. 추측 단정 회피 — 현재 부재 항목 (calendar/notes/health/doctors EMR/resources/오더/처방) 모두 후속 검토 (C) 로 분류. 실제 구현 대상으로 단정 X.
5. 현재 코드 정합 — `Employee.role` 분기 (doctor/therapist), `_doctor_codes_set`, `is_doctor_filter`, role=doctor handler 검증 등 실제 코드 라인을 §3-3-3 / §9 M-03b 에 그대로 인용.
6. AI/RAG local-first 보존 — §3-10 + §7-7 + §6-1 의 ai/rag → 도메인 의존성 ❌ 명시 + 의사 정보 임의 생성 금지 정책 추가.
7. 단계 이동 14순서 (§9-1) 가 의존도 기반으로 합리적 — core 1번 → appointments 14번 (마지막).
8. 18-8 baseline 회귀 보호 100% — 529 passed 그대로.
9. 19-P-1 r2 pass 산출물 무수정.
10. **r1 fail 항목 모두 보정**: G-5 V2 트리 모순 (해소) + §9 항목 수 36→37 (정정) + §12 A/B/C 카운트 (재계산: 21/6/10).
11. **r2 fail 항목 모두 보정**: G-5 modules 카운트 오류 — "11개" → "13개" + "4개 모듈" → "6개 모듈" 4개 위치 동기화.

남은 위험:
- T-1 ~ T-15 의사결정 항목 — 19-P-3 모듈 매핑 단계에서 결정.
- 비-AI 86 endpoint 응답 키 전수표 (19-P-1 §22 C-1) — 19-P-4+ 도메인 분리 직전 별도 보강.
- 18-0~18-8 변경분 main 머지 / `docs/ai_rag_current_state.md` stale 보정 — 19-P-1 r2 §3 권고 그대로 별도 세션.
- 의사 EMR 도입 시 m014+ 마이그레이션 + 응답 키 추가 + UI 변경 동반 — 본 19-P 비-목표.
- 세션 경계 Git 검증 caveat — 18-0~18-8 미커밋 (이전 세션부터 알려진 사항).
