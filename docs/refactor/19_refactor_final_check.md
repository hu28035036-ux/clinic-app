# 19-P-10 단위화 리팩토링 — 최종 점검 (19_refactor_final_check)

> 19-P-1 ~ 19-P-9 (준비 단계 9개 문서) 의 **cross-check + Codex caveat 누적 정리 + 19-0 진입 준비 완료 확인** 문서.
> 본 문서는 *최종 점검* 문서 — 실제 코드 / 테스트 / 폴더 / 파일 / fixture / mock / 마이그레이션 미생성.
> 본 문서 통과 시 다음 단계 = **19-0 baseline 재고정** (실제 코드 세션 진입 직전 baseline 확보).

## 0. 메타

- 작성일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed** ([reports/ai_dev_loop/18-8_test_report.md](../../reports/ai_dev_loop/18-8_test_report.md))
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 / 19-P-6 r1+r2 / 19-P-7 r3 / 19-P-8 r1 / 19-P-9 r1 Codex 판정: **pass / pass / pass with caveat / pass with caveat / pass with caveat / pass with caveat / pass with caveat / pass with caveat / pass with caveat (yes — 19-P-10 진입 가능)** (영구 보존본 링크 — [19-P-9_codex_review.md](../../reports/refactor/19-P-9_codex_review.md))
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.
- 본 문서는 *최종 점검* 문서 — 새 폴더 / 파일 / 테스트 / fixture / 마이그레이션 미생성.

### 0-1. 본 19-P-10 의 위치

- 19-P-1 ~ 19-P-9 = 단위화 리팩토링 *준비 단계* 문서들 (9개).
- **19-P-10 (본 문서) = 19-P-1 ~ 19-P-9 산출물 cross-check + Codex caveat 누적 정리 + 19-0 진입 권고.**
- 다음 단계 = **19-0 baseline 재고정** — 19-x 코드 세션 진입 직전 baseline 확보 (사용자 결정 후 진입).

### 0-2. 본 문서가 다루지 않는 범위

- 실제 코드 이동 / 테스트 작성 — 19-0 이후 별도 세션.
- m014+ 마이그레이션 도입 결정 — 본 19-P 비-목표.
- v1.4.0 배포 절차 — [docs/releases/18_ai_rag_final_checklist.md](../releases/18_ai_rag_final_checklist.md) 별도 게이트.
- 19-P-1 ~ 19-P-9 산출물의 *세부 보정* — 본 19-P-10 은 *cross-check* 만, caveat 보정은 후속 세션 또는 19-0.

---

## 1. 19-P-1 ~ 19-P-9 산출물 인벤토리

> **r2 보정 (19-P-10 caveat 1 정합)**: 9개 준비 단계 문서 + 9개 Codex 검증 결과 + 9개 검증 요청서 + 본 19-P-10 산출 3개 (`19_refactor_final_check.md` + `19-P-10_codex_review_request.md` + `latest_codex_review_request.md`) = **총 30 산출물** (§7 종합과 정합). r1 의 "27 + 1 + 1 = 29" 표기는 본 19-P-10 산출 3개를 누락한 산술 오류였음.

### 1-1. 준비 단계 문서 (9개)

| # | 파일 | 역할 | 메타 (revision) |
|---|---|---|---|
| 19-P-1 | [docs/refactor/19_refactor_current_state.md](19_refactor_current_state.md) | 현재 구조 스냅샷 — 86 endpoint / 19 ORM / 13 마이그레이션 / 7331줄 main.html 등 baseline | r2 |
| 19-P-2 | [docs/refactor/19_refactor_target_architecture.md](19_refactor_target_architecture.md) | 목표 모듈 구조 — `app/core/` + `app/modules/{appointments,patients,staff,leaves,treatments,stats,sms,admin,backup,ai,audit,settings,export_import}/` (modules 13 + core 1 = 14) | r3 |
| 19-P-3 | [docs/refactor/19_refactor_module_map.md](19_refactor_module_map.md) | 30 모듈 매핑 (현재 위치 → 목표 위치) | r1 |
| 19-P-4 | [docs/refactor/19_refactor_dependency_map.md](19_refactor_dependency_map.md) | 모듈 간 의존성 D-1 ~ D-13 + 분리 순서 영향 | r2 |
| 19-P-5 | [docs/refactor/19_refactor_test_strategy.md](19_refactor_test_strategy.md) | 테스트 전략 T-1 ~ T-15 + 보강 9개 항목 | r3 |
| 19-P-6 | [docs/refactor/19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) | 롤아웃 계획 R-1 ~ R-14 + 19-0 ~ 19-14 (15개 실행 세션) | r2 |
| 19-P-7 | [docs/refactor/19_refactor_risk_register.md](19_refactor_risk_register.md) | 위험 등록 77 Risk ID + RB-1 ~ RB-10 | r3 |
| 19-P-8 | [docs/refactor/19_refactor_decision_record.md](19_refactor_decision_record.md) | 의사결정 기록 DEC-A ~ DEC-T (20 결정) + 9 대안 | r1 |
| 19-P-9 | [docs/refactor/19_refactor_checklists.md](19_refactor_checklists.md) | 공통 체크리스트 9 카테고리 + 79+ 체크 단위 (실측 328 체크박스) | r1 |

### 1-2. Codex 검증 영구 보존본 (9개)

| # | 파일 | 판정 | 다음 진입 권고 |
|---|---|---|---|
| 19-P-1 | [reports/refactor/19-P-1_codex_review.md](../../reports/refactor/19-P-1_codex_review.md) | **pass** (r2 — r1 fail 후 보정) | yes — 19-P-2 |
| 19-P-2 | [reports/refactor/19-P-2_codex_review.md](../../reports/refactor/19-P-2_codex_review.md) | **pass** (r3 — r1/r2 fail 후 보정) | yes — 19-P-3 |
| 19-P-3 | [reports/refactor/19-P-3_codex_review.md](../../reports/refactor/19-P-3_codex_review.md) | **pass with caveat** | yes — 19-P-4 |
| 19-P-4 | [reports/refactor/19-P-4_codex_review.md](../../reports/refactor/19-P-4_codex_review.md) | **pass with caveat** (r2 보정) | yes — 19-P-5 |
| 19-P-5 | [reports/refactor/19-P-5_codex_review.md](../../reports/refactor/19-P-5_codex_review.md) | **pass with caveat** (r3 — r1 fail 후 보정) | yes — 19-P-6 |
| 19-P-6 | [reports/refactor/19-P-6_codex_review.md](../../reports/refactor/19-P-6_codex_review.md) | **pass with caveat** (r2 보정) | yes — 19-P-7 |
| 19-P-7 | [reports/refactor/19-P-7_codex_review.md](../../reports/refactor/19-P-7_codex_review.md) | **pass with caveat** (r3 — r2 fail 후 taxonomy 정정) | yes — 19-P-8 |
| 19-P-8 | [reports/refactor/19-P-8_codex_review.md](../../reports/refactor/19-P-8_codex_review.md) | **pass with caveat** | yes — 19-P-9 |
| 19-P-9 | [reports/refactor/19-P-9_codex_review.md](../../reports/refactor/19-P-9_codex_review.md) | **pass with caveat** | yes — 19-P-10 또는 19-0 |

### 1-3. Codex 검증 요청서 영구 보존본 (9개)

[reports/refactor/19-P-1_codex_review_request.md](../../reports/refactor/19-P-1_codex_review_request.md) ~ [reports/refactor/19-P-9_codex_review_request.md](../../reports/refactor/19-P-9_codex_review_request.md). 본 19-P-10 산출 = `19-P-10_codex_review_request.md` (영구) + `latest_codex_review_request.md` (덮어쓰기).

### 1-4. 종합

- **준비 단계 = 9개 문서 모두 작성 완료**.
- **Codex 검증 = 9개 모두 pass / pass with caveat (yes 진입 가능)**.
- **fail 이력** = 19-P-1 r1 fail / 19-P-2 r1 fail + r2 fail / 19-P-5 r1 fail / 19-P-7 r2 fail = **총 5회 fail → revision 보정 후 모두 pass / pass with caveat 복귀**.
- **revision 카운트** = 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 / 19-P-6 r2 / 19-P-7 r3 / 19-P-8 r1 / 19-P-9 r1 = **합계 18 revision**.

---

## 2. Cross-check — 절대 원칙 / 정책 정합

> 19-P-2 P-1 ~ P-12 / 19-P-6 R-1 ~ R-14 / 19-P-8 DEC-A ~ DEC-T 의 *절대 원칙* 이 9개 준비 단계 문서 모두에서 일관 정합한지 검증.

### 2-1. 절대 원칙 매트릭스 — 9개 문서 cross-check

| 절대 원칙 | 19-P-1 | 19-P-2 | 19-P-3 | 19-P-4 | 19-P-5 | 19-P-6 | 19-P-7 | 19-P-8 | 19-P-9 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 기능 변경 ⊥ (구조 안정화) | §1-1 | P-1 | §1 | D-1 | T-1 | R-1 | §0-2 | DEC-A | §0-2 |
| API URL / 응답 키 보존 | §3 + §21 | P-2 + §7-1-2 | §2-N | D-1 | T-3 | R-4 | R-APPT-01 외 | DEC-C | §2-1 |
| DB schema 최소 변경 (m001~m013) | §4-1 | P-4 + §7-3 | §2-N | (모든 §) | T-5 | R-6 | R-BAK-01~05 | DEC-D | §2-4 |
| AI/RAG local-first | §3-2 | P-7 + §3-10 + §7-7 | §2-11 (ai) | D-6 + §2-K | T-12 + T-13 | R-12 | R-AI-01~07 | DEC-N + DEC-O | §6-8 |
| 운영 DB 미접근 | (전제) | P-12 | (전제) | (전제) | T-11 + S-1~S-5 | R-11 | R-OPS-01~03 | DEC-D | §5-3 + §5-10 |
| 외부 API 호출 0 | (전제) | P-12 | (전제) | (전제) | T-12 + S-4 | R-11 | R-AI-06 + R-SMS-04 + R-OPS-03 | DEC-N | §5-4 |
| per-file-ignores 보존 | (전제) | P-11 | (전제) | (전제) | T-14 | R-13 | (전제) | (전제) | §1-4 |
| manual60 = 1 카운트 | §4 (Treatment) | P-? + §3-5 | §2-6 (treatments) | §2-F | T-15 | R-13 | R-TX-01 | DEC-I | §6-3 |
| Codex 검증 게이트 | (전제) | (전제) | (전제) | (전제) | T-9 | R-10 | (전제) | DEC-T | §8-12 + §9-4 |
| PyInstaller 53 tests | §1 (test) | P-10 + §7-6 | §2-N | (전제) | §2-6 P-1~P-4 | R-14 (배포) | R-OPS-04~06 | DEC-R | §5-12 |

> **결과**: 모든 절대 원칙이 9개 문서 전체에서 일관 등록 — 충돌 / 누락 / 모순 0건 발견.

### 2-2. 모듈 분리 순서 cross-check (19-P-6 §2-1 = 19-0 ~ 19-14, 15개 실행 세션)

| 세션 | 19-P-3 우선순위 | 19-P-4 §6 | 19-P-6 §3 | 19-P-7 § | 19-P-8 DEC-* | 19-P-9 §6 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 19-0 baseline | (모든 모듈 진입 전) | (전제) | §3-0 | §0-1 | (전제) | §1-2 + §1-5 |
| 19-1 core | 1 (M-25) | §6-A | §3-1 | R-CORE-01~05 | DEC-A + DEC-E | §6 (없음 — core 는 모든 모듈 공통) |
| 19-2 settings / feature_flags / health | 3 (M-15) + 13 (M-30) + 후속 (M-28) | §6-A | §3-2 | R-ADM-04 + R-HEALTH-01 | DEC-P | §6-7 |
| 19-3 calendar view-model | 후속 (M-26) | §6-? | §3-3 | R-CAL-01~04 | (후속) | §6 (없음 — post-19-P 후속) |
| 19-4 availability | (M-01 사전) | §6-A + §5-2 | §3-4 | R-APPT-02~06 | DEC-G | §6-1 |
| 19-5 leaves + am/pm/full 백엔드 차단 | 6 (M-04) + 18 (M-18) | §6-A + §5-2 | §3-5 | R-LEAVE-01~04 + R-APPT-03 | DEC-H | §6-2 |
| 19-6 treatments / completion_rules | 5 (M-05 + M-06) | §6-A | §3-6 | R-TX-01~04 | DEC-I | §6-3 |
| 19-7 patients / notes + data-convert | 7 (M-02 + M-12) | §6-A | §3-7 | R-PAT-01~05 + R-EXIM-01-02 | DEC-L | §6-6 |
| 19-8 staff (doctor + therapist) | 4 (M-03 + M-03b) | §6-A | §3-8 | R-THER-01~03 + R-DOC-01~02 | DEC-M | §6 (staff 내 admin §6-7 일부) |
| 19-9 appointments | 14 마지막 (M-01) | §6-B 마지막 | §3-9 | R-APPT-01~07 + R-LOCK-01 | DEC-F | §6-1 |
| 19-10 sms | 9 (M-09 + M-29) | §6-A | §3-10 | R-SMS-01~05 | DEC-K | §6-5 |
| 19-11 stats | 8 (M-07 + M-08) | §6-A | §3-11 | R-STAT-01~05 | DEC-J | §6-4 |
| 19-12 admin / backup / audit / export_import | 11 (M-10 + M-11 + M-14 + M-16) | §6-A | §3-12 | R-ADM-01~05 + R-BAK-01~05 + R-AUDIT-01~02 + R-EXIM-01-02 | DEC-P + DEC-Q | §6-7 |
| 19-13 AI commands 연결부 | 12 (M-17~M-24) | §6-A | §3-13 | R-AI-01~07 | DEC-N + DEC-O | §6-8 |
| 19-14 종료 게이트 (전체 회귀 + PyInstaller 빌드) | (전제) | §6-? | §3-14 | R-OPS-04~06 | DEC-R | §5-12 |

> **결과**: 15개 실행 세션 모두 19-P-3 / 19-P-4 / 19-P-6 / 19-P-7 / 19-P-8 / 19-P-9 에서 일관 매핑 — 우선순위 / 위험 / 결정 / 체크리스트 충돌 0건 발견.

### 2-3. 부재 항목 단정 ⊥ cross-check

| 부재 항목 | 19-P-1 | 19-P-2 | 19-P-3 | 19-P-7 | 19-P-8 | 19-P-9 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `Doctor` 별도 테이블 | (부재) | §3-3-4 + §2-2 (M-31) | §2-4 | R-DOC-01~02 | DEC-M / §3-2 | §6 admin / §12 |
| `Patient.doctor_id` | (부재) | §3-2 (후속) + §3-3-4 | §2-2 (M-32) | (R-32 후속) | DEC-M | §6 patients / §12 |
| `Department` / `Room` / `DoctorSchedule` | (부재) | §3-3-4 + §2-2 (M-33~M-34) | §2-4 + §2-28 (resources) | (R-33~R-34 후속) | DEC-M | §12 |
| `Order` / `Prescription` (EMR) | (부재) | §3-3-4 + §2-2 (M-35) | §2-4 | (R-35 후속) | DEC-M | §12 |
| `Appointment.no_show` | (부재) | §3-6 (후속) | §2-26 | R-STAT-? (후속) | DEC-D / §3-2 | §12 |
| `/api/health` (서버 상태) | (부재) | §3-8 + §2-2 (M-28) | §2-19 | R-HEALTH-01 | DEC-P | §12 |
| `Resource` (진료실 / 장비) | (부재) | §2-2 (M-33) | §2-28 | (R-33 후속) | DEC-M | §12 |
| 반복 예약 (recurring) | (부재) | §4 (후속) | §2-27 | (후속) | §3-2 | §12 |
| 알림 (notifications) | (부재) | §4 (후속) | §2-30 | (후속) | §3-2 | §12 |
| 출력물 (printing) | (부재) | §4 (후속) | §2-29 | (후속) | §3-2 | §12 |

> **결과**: 부재 항목 10개 모두 6개 문서에서 일관 *후속 검토* 분류 — 단정 ⊥ 정책 정합. 19-P-7 G-6 / 19-P-8 G-11 / 19-P-9 G-? 모두 pass.

### 2-4. 의존성 방향 cross-check (19-P-4 D-1 ~ D-13)

| 의존성 원칙 | 19-P-2 | 19-P-3 | 19-P-4 | 19-P-7 | 19-P-8 | 19-P-9 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| D-1 router → service → repository | §6 | (전제) | §1 D-1 + §3 | R-CORE-01 | DEC-E | §3-1 |
| D-3 repository → models 만 | §6 | (전제) | §1 D-3 | R-CORE-01 | DEC-E | §3-2 |
| D-4 core → modules ⊥ | §6 | (전제) | §1 D-4 | R-CORE-02 | DEC-E | §3-3 |
| D-6 AI/RAG ⊥ 도메인 DB 임의 생성 | §3-10 | §2-11 | §1 D-6 + §2-K | R-AI-05 | DEC-N + DEC-O | §6-8 |
| D-7 stats → 도메인 (read only) | §6-1 | §2-7 | §1 D-7 + §2-G | R-STAT-* | DEC-J | §6-4 |
| D-8 sms ⊥ appointments (write) | §6-1 | §2-8 | §1 D-8 + §2-H | R-SMS-05 | DEC-K | §6-5 |
| D-9 audit 단방향 | §6-1 | §2-17 | §1 D-9 + §2-N | R-AUDIT-01 | DEC-Q | §6 audit |
| D-10 settings / feature_flags 단방향 read | §6-1 | §2-16 | §1 D-10 + §2-I | R-ADM-04 | DEC-P | §6-7 |

> **결과**: D-1 ~ D-13 모두 9개 문서에서 일관 정합 — 순환참조 위험 / 책임 혼재 위험 모두 등록.

---

## 3. Codex caveat 누적 정리

> 19-P-1 ~ 19-P-9 Codex 검증 결과의 caveat 를 누적 분류 — *해소 / 미해소 / 후속 검토*.

### 3-1. 해소된 caveat (revision 보정 완료)

| caveat | 발견 세션 | 보정 세션 | 해소 근거 |
|---|---|---|---|
| 19-P-1 r1 fail — `/api` 엔드포인트 수 / ORM / 테스트 / harness 줄수 / §22 자체 모순 / stale 2차 기준 | 19-P-1 r1 | 19-P-1 r2 | §3 86 endpoint / §4 19 ORM / §5 40 tests / harness 1420줄 + §22-A 보정 + stale caveat |
| 19-P-2 r1 + r2 fail — V2 트리 modules 개수 / §9 A/B/C 카운트 | 19-P-2 r1+r2 | 19-P-2 r3 | §0 + §2-1 트리 13 modules / §12 21+6+10=37 |
| 19-P-5 r1 fail — appointments / leaves "있음" 과장 + §4/§9 분류 9/7/4 vs 6/9/5 + §2-5 db_guard 표현 | 19-P-5 r1 | 19-P-5 r3 (r2 추가 보정) | §3-1 / §3-5 실제 xfail 상태 / §4 종합 6/9/5 정정 / §2-5 import-time + session fixture |
| 19-P-6 r1 caveat — "추천 순서 14단계" / 영구 링크 | 19-P-6 r1 | 19-P-6 r2 | §2-1 19-1~19-14 = 14 + 19-0 = 15 / `19-P-5_codex_review.md` 영구 링크 |
| 19-P-7 r2 fail — taxonomy 숫자 (21 prefix / 78 제목 / 약 74) vs 실제 (23행 / 77 제목) | 19-P-7 r2 | 19-P-7 r3 | §0 + §1-3 + §8 = 23행 / 77 Risk ID / 단독 prefix 20 + 통합 키 3 |
| 19-P-8 caveat 1 — 19-P-7 r3 결과 링크 latest → 영구 보존본 | 19-P-8 r1 | 19-P-9 r1 | 19-P-9 §0 + §0-A + §9-4 영구 보존본 사용 명시 |
| 19-P-8 caveat 2 — api.py 5127 (bash) vs 5128 (PowerShell) drift | 19-P-8 r1 | 19-P-9 r1 | 19-P-9 §0-2 baseline 측정값 표 (도구 / 결과 명시) |
| 19-P-8 caveat 3 — PyInstaller "53 tests" 산출 공식 | 19-P-8 r1 | 19-P-9 r1 | 19-P-9 §5-12 산출 공식 = 15 + 19×2 = 53 |

### 3-2. 미해소 caveat — 19-P-10 시점에 보정 권장

| caveat | 발견 세션 | 보정 권장 시점 | 19-P-10 처리 |
|---|---|---|---|
| 19-P-9 r1 caveat 1 — `## [0-9]+\.` grep 명령이 fenced markdown 예시까지 잡음 (15 / 11) | 19-P-9 r1 | 19-P-10 또는 19-0 | 본 §5-3 에 명령 보정안 (코드블록 제외 권장) 명시. 실제 본문 §0~§10 11개 정확 — 명령만 보정. |
| 19-P-9 r1 caveat 3 — 19-P-9 요청서 2차 대조 기준에 `19-P-5 r2` 표기 (실제 r3) | 19-P-9 r1 | 19-P-10 또는 19-0 | 19-P-9 검증 요청서 (`reports/refactor/19-P-9_codex_review_request.md`) §7 의 `(19-P-5 r2)` → `(19-P-5 r3)` 보정 권장. 본 §5-2 에 표기 정정 명시. **단, 진행 차단 ⊥** — 본 19-P-10 도 read-only 정책상 수정 ⊥, 19-0 시점에 정정 가능. |

### 3-3. 미해소 caveat — 19-0 / 19-x 시점에 해소

| caveat | 발견 세션 | 해소 시점 |
|---|---|---|
| dirty/untracked 워크트리 (18-0~18-8 변경분) | 19-P-1 ~ 19-P-9 (모두 G-1 pass with caveat) | **19-0** — 사용자 결정 후 main 머지 또는 별도 commit (19-P-6 §0-1 / §2 / §5-2 / 19-P-9 §1-2 / 19-P-9 §1-5 명시) |
| `docs/ai_rag_current_state.md` stale (18 시리즈 일부 항목) | 19-P-1 r1 (19-P-1 §24 caveat) | **19-0** 또는 별도 문서 갱신 세션 (19-P-2 §10 / 19-P-1 §24) |
| 비-AI 86 endpoint contract 부재 (C-1) | 19-P-1 §22 | **각 19-x 분리 직전** — 도메인별 contract 테스트 신규 추가 (19-P-5 §4 보강 9개 / 19-P-9 §2-2) |
| `test_appointment_rules.py` xfail 3건 + skip 1건 → 정방향 전환 | 19-P-5 §3-1 | **19-4 availability** — 백엔드 차단 코드 추가 + xfail → 정방향 (19-P-7 R-APPT-02) |
| `test_therapist_leave.py` xfail 4건 → 정방향 전환 | 19-P-5 §3-5 | **19-4 / 19-5 leaves** — 백엔드 차단 코드 추가 (19-P-7 R-APPT-03 + R-LEAVE-01) |
| PyInstaller 53 tests collection 미실행 (`.venv` Python 런처 부재) | 19-P-8 r1 caveat 3 / 19-P-9 r1 caveat 2 | **19-0** — `.venv` 복구 + 실제 `pytest --collect-only` |
| 18-0~18-8 변경분 main 머지 결정 | 19-P-1 r2 / 19-P-6 r1 | **19-0** 시점에 사용자 결정 |

### 3-4. 후속 검토 (post-19-P) caveat

| caveat | 후속 시점 |
|---|---|
| `modules/notes/` 통합 (`Patient.memo` / `Appointment.memo` 정책 결정) | post-19-P (19-P-2 §2-2 M-27) |
| `modules/health/` `/api/health` 신설 | post-19-P (19-P-2 §2-2 M-28) |
| `modules/calendar/` view-model 분리 + main.html UI 분리 | post-19-P (19-P-2 §2-2 M-26 / P-3 / R-5) |
| `modules/doctors/` 별도 모듈 (EMR 도입 시) | post-19-P (19-P-2 §2-2 M-31) |
| `Patient.doctor_id` / `Doctor.schedule` / `Order` / `Prescription` (m014+) | post-19-P (19-P-2 §2-2 M-32~M-35) |
| AI 의사 / 진료진 hallucination guard 보강 | post-19-P (19-P-2 §3-10 M-36) |
| `Appointment.no_show` 컬럼 (m014+) | post-19-P |
| 보존 정책 (audit / AiUsageLog 자동 삭제) | post-19-P |
| sms / ai 자동 트리거 통합 (notifications) | post-19-P |
| 반복 예약 (recurring) | post-19-P |
| 자원 관리 (resources / 진료실 / 장비) | post-19-P |
| 출력물 (printing — 예약표 / 통계표) | post-19-P |

### 3-5. 종합

- **해소된 caveat = 8개** (revision 보정 완료).
- **19-P-10 / 19-0 시점에 보정 권장 = 2개** (grep 명령 보정 + 19-P-5 r2/r3 표기) — *진행 차단 ⊥*.
- **19-0 / 19-x 시점에 해소 = 7개** (dirty 워크트리 / stale 문서 / contract 부재 / xfail 정방향 / PyInstaller collection / main 머지 결정).
- **post-19-P 후속 검토 = 12개** (notes / health / calendar / doctors / EMR / no_show 등).

---

## 4. 실측 baseline 재확인

> 19-P-9 §0-2 baseline 측정값 + 19-P-8 caveat 2/3 정합. 본 19-P-10 시점 재실측.

### 4-1. 본 19-P-10 시점 실측

| 항목 | 19-P-9 §0-2 | 19-P-10 실측 | 일치 |
|---|---|---|:---:|
| `app/routers/api.py` 라인 수 (bash `wc -l`) | 5127 | **5127** | ✓ |
| `app/routers/api.py` endpoint 수 | 86 | **86** | ✓ |
| `app/routers/ai.py` 라인 수 | 929 | **929** | ✓ |
| `app/routers/ai.py` endpoint 수 | 13 | **13** | ✓ |
| `app/templates/main.html` 라인 수 | 7331 | **7331** | ✓ |
| `app/static/css/app.css` 라인 수 | 3626 | **3626** | ✓ |
| `tests/test_*.py` 파일 수 | 40 | **40** | ✓ |
| ORM 모델 수 | 19 | **19** | ✓ |
| 마이그레이션 수 (m001 ~ m013) | 13 | **13** | ✓ |
| PyInstaller 테스트 산출 공식 | 15 + 19×2 = 53 | **17 def test_ (15 non-parametrized + 2 parametrized) × `EXPECTED_18_X_MODULES` 19개 = 15 + 19×2 = 53** ✓ | ✓ |

> **결과**: 19-P-9 §0-2 baseline 측정값과 19-P-10 시점 실측 100% 일치. drift 0.

### 4-2. 부재 항목 단정 ⊥ 재확인

| 부재 항목 | grep 결과 | 일치 |
|---|---|:---:|
| `class Doctor\|class Department\|class Room\|class DoctorSchedule\|class Order\|class Prescription\|class Resource` in `app/models/models.py` | 0건 | ✓ |
| `doctor_id` in `app/models/models.py` | 0건 | ✓ |
| `no_show` in `app/models/models.py` | 0건 | ✓ |
| `/api/health` (서버 상태, `/api/ai/health` 와 별개) | 0건 | ✓ |

> **결과**: 부재 항목 단정 ⊥ 정책 100% 정합 — 19-P-7 G-6 / 19-P-8 G-11 / 19-P-9 부재 항목 grep 모두 일관.

---

## 5. 19-0 baseline 재고정 진입 전 점검 항목

> 19-0 (실제 코드 세션 직전 baseline 확보) 진입 *전* 사용자 결정 / 환경 복구 필요 항목.

### 5-1. 사용자 결정 필요 항목

| # | 결정 항목 | 근거 |
|---|---|---|
| 1 | **18-0 ~ 18-8 dirty/untracked 변경분 main 머지 vs 별도 commit vs 그대로 유지** | 19-P-1 r2 caveat / 19-P-6 §0-1 / 19-P-9 §1-2. 19-0 시점에 *워크트리 cleanliness* 확보 필요. 머지 / 별도 commit 시 [v1.4.0 release notes](../releases/) 작성 후속. 그대로 유지 시 19-x 코드 세션마다 G-1 pass with caveat 누적. |
| 2 | **`docs/ai_rag_current_state.md` stale 보정 세션 진행 vs 19-0 안에서 처리 vs post-19-P** | 19-P-1 §24 / 19-P-2 §10. 18-1 ~ 18-8 변경분 일부가 본 문서에 미반영. 보정은 read-only 문서 세션. |
| 3 | **PyInstaller `.venv` Python 런처 복구 시점 — 19-0 안에서 vs 19-1 진입 직전** | 19-P-8 caveat 3 / 19-P-9 caveat 2. 53 tests `--collect-only` 실행 환경 확보 필요. |

### 5-2. 환경 복구 필요 항목

| # | 항목 | 진단 명령 |
|---|---|---|
| 1 | `.venv\Scripts\python.exe` 존재 여부 | `ls -la venv/Scripts/python.exe` |
| 2 | pytest 실행 가능 여부 | `venv\Scripts\python.exe -m pytest --version` |
| 3 | ruff 실행 가능 여부 | `venv\Scripts\python.exe -m ruff --version` |
| 4 | check_db_path 실행 가능 여부 | `venv\Scripts\python.exe scripts/check_db_path.py` |

### 5-3. 19-P-9 caveat 미해소 항목 보정 (19-0 안에서 처리 가능)

| caveat | 보정 안 |
|---|---|
| **19-P-9 caveat 1** — 자동 grep 명령 `^## [0-9]+\.` 가 fenced markdown 예시까지 잡음 | 19-P-9 §11 G-2 검증 명령에 *코드블록 제외* 권장 추가: `awk '/^```/{c=!c} !c && /^## [0-9]+\\./' docs/refactor/19_refactor_checklists.md \| wc -l` 또는 ripgrep `--glob=!**/*.md` 옵션 활용. **본 19-P-10 은 read-only — 보정은 19-0 또는 별도 세션**. |
| **19-P-9 caveat 3** — 19-P-9 검증 요청서에 `19-P-5 r2` 표기 (실제 r3) | 19-P-9 검증 요청서 (`reports/refactor/19-P-9_codex_review_request.md`) §7 의 `(19-P-5 r2)` → `(19-P-5 r3)` 보정. **본 19-P-10 은 read-only — 보정은 19-0 또는 별도 세션**. 진행 차단 ⊥ (실제 문서 링크와 메타는 r3). |

### 5-4. 19-0 진입 직전 baseline 확보 체크리스트 (19-P-9 §1 + 19-P-6 §3-0 정합)

- [ ] `git status --short` 결과 = 18-0~18-8 변경분 + 본 19-P 산출물 외 변경 0
- [ ] `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 결과 = 5개 tracked (`models.py` / `routers/ai.py` / `manual_qa.py` / `dosu_clinic.spec` / `conftest.py`) 만
- [ ] `run_check.bat` 통과 (pytest + ruff + check_db_path)
- [ ] `pytest tests -v` 결과 = 18-8 baseline (529 passed, 1 skipped, 7 xfailed) 일치 — 또는 19-x 진행 후 갱신 baseline
- [ ] AI 하네스 6개 (Full / RAG / Safety / Chunk / Reindex / Vector / Hybrid) 통과
- [ ] PyInstaller 53 tests `--collect-only` + `pytest tests/test_pyinstaller_hidden_imports.py -v` 통과
- [ ] 운영 DB 보호 5단계 (S-1 ~ S-5) 통과
- [ ] 외부 API 차단 (`_block_sdk_modules`) 활성

---

## 6. 19-0 진입 권고

### 6-1. 진입 게이트

| 게이트 | 조건 | 본 19-P-10 시점 결과 |
|---|---|---|
| FG-1 9개 준비 단계 문서 모두 작성 완료 | 19-P-1 ~ 19-P-9 | ✓ pass |
| FG-2 9개 모두 Codex 검증 pass / pass with caveat | 19-P-1 ~ 19-P-9 (yes 진입 가능) | ✓ pass |
| FG-3 절대 원칙 9개 문서 충돌 ⊥ | §2-1 매트릭스 | ✓ pass |
| FG-4 모듈 분리 순서 9개 문서 충돌 ⊥ | §2-2 매트릭스 | ✓ pass |
| FG-5 부재 항목 단정 ⊥ | §2-3 매트릭스 + §4-2 grep 0건 | ✓ pass |
| FG-6 의존성 방향 D-1~D-13 일관 | §2-4 매트릭스 | ✓ pass |
| FG-7 baseline 측정값 drift 0 | §4-1 매트릭스 | ✓ pass |
| FG-8 19-P-8 caveat 3개 19-P-9 반영 | §3-1 (영구 링크 / api.py 5127↔5128 / PyInstaller 53 산출 공식) | ✓ pass |
| FG-9 19-P-9 caveat 2개 19-0 보정 가능 | §5-3 (grep 명령 / r2 표기) | ✓ pass with caveat (read-only 정책상 본 세션 수정 ⊥, 19-0 안에서 보정) |
| FG-10 dirty/untracked 워크트리 19-0 정리 가능 | §3-3 + §5-1 (사용자 결정 필요) | ✓ pass with caveat (사용자 결정 필요) |

→ FG-1 ~ FG-10 = **8 pass + 2 pass with caveat** = **종합 pass with caveat** = **yes — 19-0 baseline 재고정 진입 가능**.

### 6-2. 19-0 baseline 재고정 진입 권고

**yes — 19-0 baseline 재고정 진입 가능**.

근거:
1. 9개 준비 단계 문서 모두 작성 완료 (19-P-1 ~ 19-P-9).
2. 9개 모두 Codex 검증 pass / pass with caveat (yes 진입 가능).
3. 절대 원칙 / 모듈 분리 순서 / 부재 항목 단정 ⊥ / 의존성 방향 / baseline 측정값 모두 9개 문서에서 일관 정합 — 충돌 0건 발견.
4. revision 이력 = 18 revision (5회 fail → 모두 보정 완료).
5. caveat 누적 정리 — 해소 8개 / 19-P-10 보정 2개 (read-only 정책상 19-0 안에서 처리) / 19-0 ~ 19-x 시점에 해소 7개 / post-19-P 후속 12개. **진행 차단 caveat 0건**.
6. 본 19-P-10 시점 실측 baseline 측정값 (19-P-9 §0-2) 와 100% 일치.
7. 부재 항목 (Doctor / Department / Room / DoctorSchedule / Order / Prescription / Resource / Patient.doctor_id / no_show / `/api/health`) 모두 grep 0건 — 단정 ⊥ 정책 100% 정합.

남은 위험 / 사용자 결정 필요:
- §5-1 1번: 18-0~18-8 dirty 변경분 처리 결정 (머지 / 별도 commit / 유지).
- §5-1 2번: `ai_rag_current_state.md` stale 보정 시점.
- §5-1 3번: `.venv` Python 런처 복구 시점.

### 6-3. 옵션 비교

| 옵션 | 설명 | 권장 |
|---|---|---|
| **A: 19-0 baseline 재고정 진입** (사용자 §A → §B 명시) | (a) `.venv` 복구 / (b) `pytest tests -v` 18-8 baseline 재확인 / (c) 19-P-9 caveat 2개 보정 / (d) 18-0~18-8 머지 결정 / (e) 19-1 진입 직전 깨끗한 baseline | ✓ 권장 (사용자 명시) |
| B: 별도 보정 세션 (19-P-9 caveat 만) | 19-P-9 §11 G-2 grep 명령 보정 + r2 → r3 표기 정정 만 read-only 처리 | △ 우선순위 낮음 (19-0 안에서 처리 가능) |
| C: post-19-P 후속 검토 보류 | 본 19-P-10 종료 + 19-x 코드 세션 진행 보류 | ✗ 사용자 §A → §B 명시와 충돌 |

### 6-4. 다음 단계

**19-0 baseline 재고정 (사용자 §B)** — 본 19-P-10 Codex 검증 pass / pass with caveat 후 진입.

---

## 7. 종합

- 본 19-P-10 = 19-P-1 ~ 19-P-9 산출물 cross-check + Codex caveat 누적 정리 + baseline 실측 + 19-0 진입 권고.
- 9개 준비 단계 문서 + 9개 Codex 검증 결과 + 9개 검증 요청서 + 본 19-P-10 산출 3개 = **총 30 산출물**.
- **revision 이력 18 회 + fail 이력 5회 (모두 revision 보정 후 pass / pass with caveat 복귀)**.
- **절대 원칙 / 모듈 분리 순서 / 부재 항목 단정 ⊥ / 의존성 방향 / baseline 측정값 = 9개 문서에서 일관 정합** — 충돌 / 누락 / 모순 0건 발견.
- **Codex caveat 누적 = 해소 8개 / 19-0 보정 2개 / 19-0~19-x 해소 7개 / post-19-P 후속 12개** = 총 29개. 진행 차단 caveat 0건.
- **19-0 진입 게이트 FG-1 ~ FG-10 = 8 pass + 2 pass with caveat = 종합 pass with caveat = yes 진입 가능**.
- **다음 단계 = 19-0 baseline 재고정** (사용자 §A → §B 명시) — Codex 검증 pass / pass with caveat 후 진입.
- **19-0 진입 직전 사용자 결정 필요 = 3건** (dirty 변경분 처리 / `ai_rag_current_state.md` stale 보정 시점 / `.venv` 복구 시점).
