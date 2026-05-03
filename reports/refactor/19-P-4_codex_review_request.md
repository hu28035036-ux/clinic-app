# 19-P-4 Codex 검증 요청서 (revision 2 — r1 minor issues 후 보정본)

> **사용자가 Codex에게 전달할 최소 문구**
>
> > "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

## 0. Revision 이력

| 회차 | 날짜 | 결과 | 변경 |
|---|---|---|---|
| r1 | 2026-05-02 | **pass with caveat** ([reports/refactor/19-P-4_codex_review.md](19-P-4_codex_review.md), G-8 minor — §0-1 "2개 → 3개" / "~640줄 → 620줄" / §2-B PII 경로 명시) | 초기 작성 |
| r2 | 2026-05-02 | (본 revision) | **3개 부정확 항목 보정**. dependency_map.md §0-1 신규 카운트 "2개→3개" + §2-B PII 경로 "현재 vs 목표 후속" 명시. 본 요청서 §3 줄수 "640→620". 코드/테스트/spec/UI/migrations/requirements 무수정 유지. Codex 재검증 요청. |

본 요청서는 19-P 단위화 리팩토링 네 번째 세션의 산출물 (의존성 맵 문서) 1건을 Codex 가 독립적으로 검증할 수 있도록 작성한 표준 패키지다.

---

## 0. Baseline

- HEAD commit: `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 Codex 판정: **pass / pass / pass with caveat** ([reports/refactor/19-P-3_codex_review.md](19-P-3_codex_review.md))
- 19-P-3 caveat 3개 본 19-P-4 반영: 줄 번호 대신 symbol grep / `leave_type="am"`/`"pm"` 구체화 / dirty/untracked 표현 정확.
- 본 세션은 위 commit 위에 신규 commit 없이 untracked 문서 추가만 수행. 코드/테스트/spec/UI 무수정.

## 1. 세션 이름

**19-P-4 단위화 리팩토링 의존성 맵 문서 작성**

- 19-P-3 [모듈 매핑](../../docs/refactor/19_refactor_module_map.md) 의 30 모듈 + 19-P-2 [목표 아키텍처](../../docs/refactor/19_refactor_target_architecture.md) 를 기반으로 **모듈 간 의존성 그래프 + 위험도 + 순환참조 + 분리 순서 영향** 정리.
- read-only 문서 세션. 실제 코드 이동 없음.

## 2. 이번 세션 목표

| # | 목표 |
|---|---|
| 1 | §1 의존성 설계 원칙 D-1 ~ D-13 (13개) — router → service → repository / core ⊥ modules / AI ⊥ 도메인 / stats / sms read-only / audit 단방향 / 등 |
| 2 | §2 주요 의존성 맵 16개 모듈 그룹 — appointments / patients / staff / doctors / leaves / treatments / stats / sms / admin / backup / ai / calendar / notes / health / export_import / core |
| 3 | §3 의존성 분류표 50+행 — From / To / 목적 / 현재 / 허용 / 위험도 / 순환위험 / 테스트 / 주석 / 비고 |
| 4 | §4 금지/줄여야 할 의존성 9개 (F-1 ~ F-9) |
| 5 | §5 순환참조 위험 구간 9개 (5-1 ~ 5-9) — appointments↔leaves / appointments↔availability / appointments↔sms / appointments↔stats / patients↔notes / staff↔leaves / admin↔settings↔feature_flags / ai/commands↔도메인 / health↔ai/backup/settings / audit↔모든 모듈 |
| 6 | §6 안전한 분리 순서 영향 — 6-A 먼저 분리 / 6-B 나중 분리 / 6-C 테스트 보강 / 6-D wrapper 필요 / 6-E DB schema 무관 |
| 7 | §7 주석 / 문서화 기준 (의존성 지점) — COMPAT / SAFETY / NOTE / RISK / TEMP-TODO 카테고리별 위치 |

## 3. 작성한 문서

### 신규 (3)

- [docs/refactor/19_refactor_dependency_map.md](../../docs/refactor/19_refactor_dependency_map.md) — 의존성 맵 (§0~§8). 620줄 (`wc -l` 실측, r2 보정).
- [reports/refactor/19-P-4_codex_review_request.md](19-P-4_codex_review_request.md) (본 문서, 영구 보존본)
- [reports/refactor/latest_codex_review_request.md](latest_codex_review_request.md) (Codex 진입점 — 본 문서와 동일)

### Codex 작성 예정

- [reports/refactor/19-P-4_codex_review.md](19-P-4_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

## 4. 수정 금지였던 범위

11개 금지 항목:
1. 코드 수정 / 2. `app/` 코드 / 3. `tests/` 코드 / 4. migration / 5. `requirements.txt` / 6. PyInstaller spec / 7. UI / 8. 응답 구조 / 9. 운영 DB / 10. 외부 API / 11. 하네스 약화.

추가:
- 18-8 baseline 회귀 보호.
- m001~m013 diff 0.
- 19-P-1 / 19-P-2 / 19-P-3 산출물 무수정.

## 5. 실제 수정한 파일 목록

### r1 신규 (3, 1차 작성)

- `docs/refactor/19_refactor_dependency_map.md`
- `reports/refactor/19-P-4_codex_review_request.md` (본 문서)
- `reports/refactor/latest_codex_review_request.md`

### r2 수정 (3, r1 minor issues 후 보정)

- `docs/refactor/19_refactor_dependency_map.md` — 표제 r2 + §0-1 "2개 → 3개" + §2-B PII 경로 "현재 vs 목표 후속" 명시
- `reports/refactor/19-P-4_codex_review_request.md` — r2 revision 추가 + §3 "~640줄 → 620줄"
- `reports/refactor/latest_codex_review_request.md` — 본 문서와 동기화

### 무수정 (회귀 보호) — r1 / r2 동일

19-P-1 / 19-P-2 / 19-P-3 산출물 모두 미수정.

> `latest_codex_review_request.md` 는 19-P-4 진입점으로 덮어쓰여진다 (19-P-3 본문은 `19-P-3_codex_review_request.md` 영구 보존).

### 무수정 (회귀 보호)

`app/**`, `tests/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`, `CLAUDE.md`, `app/services/**`, 19-P-1~19-P-3 산출물.

## 6. 코드 수정 없이 docs/refactor + reports/refactor 문서만 작성했는지 확인

| 검사 | 결과 |
|---|---|
| 본 19-P-4 신규 파일 | `dependency_map.md` + `{19-P-4,latest}_codex_review_request.md` (3개) |
| `app/**` / `tests/**` / migrations / spec / UI / `pyproject.toml` 변경 | 0 |
| 19-P-1 / 19-P-2 / 19-P-3 산출물 변경 | 0 |

→ **코드 수정 없이 docs/refactor + reports/refactor 문서만 작성**.

### Codex 가 직접 검증할 명령

```bash
git status --short
git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml
# 결과: 18-0~18-8 변경분만 + 본 19-P-4 추가 변경분 0
```

> **dirty/untracked 표현 (19-P-3 caveat 반영)**: 본 19-P-4 산출 = 신규 문서 3개. 18-0~18-8 변경분 (m012/m013, AI RAG/knowledge/vector, harness/test) 은 작업트리에 dirty/untracked 로 남아 있지만 본 세션과 무관.

## 7. Codex 가 검증해야 할 문서

### 1차 (필수)

- [docs/refactor/19_refactor_dependency_map.md](../../docs/refactor/19_refactor_dependency_map.md) (본 세션 신규)

### 2차 (대조 기준)

- [docs/refactor/19_refactor_current_state.md](../../docs/refactor/19_refactor_current_state.md) (19-P-1 r2)
- [docs/refactor/19_refactor_target_architecture.md](../../docs/refactor/19_refactor_target_architecture.md) (19-P-2 r3)
- [docs/refactor/19_refactor_module_map.md](../../docs/refactor/19_refactor_module_map.md) (19-P-3)
- [docs/AI_WORKING_RULES.md](../../docs/AI_WORKING_RULES.md) (local-first)
- [docs/ai_rag_architecture_plan.md](../../docs/ai_rag_architecture_plan.md) (RAG 목표)
- [reports/refactor/19-P-3_codex_review.md](19-P-3_codex_review.md) (직전 r1 pass with caveat)

## 8. 주요 모듈 간 의존성이 빠짐없이 정리되었는지 확인할 항목

| 의존성 | 본 문서 위치 |
|---|---|
| appointments → patients / staff / treatments / leaves / availability / audit | §2-A |
| patients → notes / audit / privacy + ?→ doctors | §2-B |
| staff (doctor + therapist 통합) → audit / treatments | §2-C |
| doctors 별도 모듈 (post-19-P, M-31~M-35) | §2-D |
| leaves → staff / audit + ← appointments.availability + ← ai/commands/action_leave | §2-E |
| treatments → patients (write done_count) + ← appointments / stats / sms | §2-F |
| stats → appointments / patients / staff / treatments / leaves (read only — D-7) | §2-G |
| sms → appointments / patients / staff / templates / settings / audit / provider (read + audit + provider only — D-8) | §2-H |
| admin → settings / feature_flags / backup / audit / core/security / ai/health | §2-I |
| backup → core/database / settings / audit | §2-J |
| ai router → manual_qa / commands / health / provider / logging + rag → 도메인 ⊥ (D-6) | §2-K |
| calendar → appointments / leaves / staff (post-19-P, read only — D-11) | §2-L |
| notes → patients (현재) + 통합 후속 | §2-M |
| health → core/database / backup / ai/health (post-19-P, read only — D-12) | §2-N |
| export_import → stats / appointments / patients (read + import write 만) | §2-O |
| core (D-4: core ⊥ modules) | §2-P |

### Codex 검증 명령

```bash
# 의존성 정합 검증
grep -n "_upsert_employee_leave_core\|action_leave\|_check_version\|_bump_version\|_bump_patient_count\|_doctor_codes_set\|is_doctor_filter" app/routers/api.py
grep -n "leave_type\|am\|pm\|full" app/services/ai/action_leave.py | head -20
grep -nE "ENTITY_MAP|sync_pull|sync_push" app/services/sync.py app/routers/api.py
grep -n "manual60\|count_increment" app/models/constants.py app/routers/api.py
grep -n "LOW_SCORE_THRESHOLD\|HIGH_THRESHOLD\|LOW_THRESHOLD\|QUERY_MIN_CHARS" app/services/ai/rag/pipeline.py app/services/ai/rag/confidence.py app/services/ai/vector/embeddings.py
```

## 9. 금지 / 제한해야 할 의존성이 현실적으로 정리되었는지 확인할 항목

| F-ID | 항목 | 본 문서 위치 |
|---|---|---|
| F-1 | repository → service 역참조 ⊥ | §1 D-1 + §4 |
| F-2 | core → modules 참조 ⊥ | §1 D-4 + §4 |
| F-3 | stats → 도메인 write ⊥ | §1 D-7 + §4 |
| F-4 | sms → appointments write ⊥ | §1 D-8 + §4 |
| F-5 | AI/RAG → 도메인 임의 생성 ⊥ | §1 D-6 + §4 |
| F-6 | UI/static JS → DB 구조 직접 의존 줄임 | §4 (19-P 비-목표) |
| F-7 | 같은 DB query 중복 줄임 | §4 (`_doctor_codes_set` 통합) |
| F-8 | 설정 / API key 분산 줄임 | §4 (settings 통합 read 인터페이스) |
| F-9 | 개인정보 원문 로그 ⊥ | §4 + §1 D-9 |

## 10. 순환참조 위험 구간이 잘 식별되었는지 확인할 항목

§5 9개 위험 구간:

| ID | 위험 구간 | 정리 방향 | 테스트 |
|---|---|---|---|
| 5-1 | appointments ↔ leaves | leaves.repository read-only 인터페이스 + leaves → appointments ⊥ | 휴무 차단 + am/pm/full 회귀 |
| 5-2 | appointments ↔ availability | 같은 모듈 안 (M-01) — 외부 의존성 명시 | 통합 회귀 |
| 5-3 | appointments ↔ sms | sms read-only — 자동 발송 트리거 ⊥ | `test_ai_sms_*` |
| 5-4 | appointments ↔ stats | stats read-only (D-7) — appointments → stats 호출 ⊥ | stats contract |
| 5-5 | patients ↔ notes | 본 19-P 안 patients/notes_service. 통합은 post-19-P | 메모 PATCH + PII |
| 5-6 | staff ↔ leaves | staff → leaves 호출 ⊥. 표시는 view-model | alias 이중 키 회귀 |
| 5-7 | admin ↔ settings ↔ feature_flags | 단방향 admin → settings → feature_flags. settings ⊥ admin 역참조. feature_flags read-only | ai_assist_mode + local_only |
| 5-8 | ai/commands ↔ appointments / leaves / sms | ai/commands → 도메인 호출만. 도메인 → ai 호출 ⊥. action_leave 는 leaves.service 호출 (단일 진실원천) | `test_ai_action_leave.py` |
| 5-9 | health ↔ ai / backup / settings | health 가 모든 모듈 read-only. 다른 모듈 → health 호출 ⊥. core/feature_flags 는 ai/health 의존성 끊기 (T-8) | `test_ai_health_status.py` |

추가: audit ↔ 모든 모듈 — audit 단방향 (§1 D-9).

## 11. 주석 / 문서화 기준이 의존성 맵에 반영되었는지 확인할 항목

§7 5개 주석 카테고리:

| 카테고리 | 위치 |
|---|---|
| `# COMPAT:` | §7-A — wrapper 시그니처 / 이중 alias / 응답 키 33+ / ENTITY_MAP |
| `# SAFETY:` | §7-B — PII / API key / 외부 SDK 차단 / engine.dispose / PBKDF2 / AI/RAG ⊥ 도메인 / 의사 가드 |
| `# NOTE:` | §7-C — manual60=1 / 임계치 / 점심창 / role=doctor / per-file-ignores / `leave_type` DB 표준 |
| `# RISK:` | §7-D — 낙관적 락 / TOCTOU / HMAC / reindex lock / atomic rename / ENTITY_MAP / spec hidden imports / availability 추출 / feature_flags 순환 |
| `# TEMP/TODO(19-P-N):` | §7-E — wrapper 일시 보유 / legacy import / availability 인라인 |

## 12. 다음 단계 (19-P-5 테스트 전략) 진입 가능 판단 기준

| 게이트 | 통과 조건 |
|---|---|
| G-1 코드 무수정 | `git diff --stat bcd74a7 -- ...` 본 19-P-4 추가 변경분 0. 19-P-1~19-P-3 산출물 무수정. |
| G-2 의존성 정합 | §2 16 모듈 그룹의 의존성 화살표가 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 의 코드 라인 / 함수명 / 응답 키와 100% 일치 |
| G-3 응답 키 / URL 후방호환 | §3 분류표 + §7-A COMPAT 위치에 33+ 키 셋 + alias 이중 키 명시 |
| G-4 AI/RAG local-first | §1 D-6 + §2-K + §7-B SAFETY (AI ⊥ 도메인) 명시 |
| G-5 후속 검토 분류 | §2-D doctors 별도 모듈 / §2-L calendar / §2-N health / §6-E m014+ 동반 항목 모두 후속 분류 |
| G-6 doctors / medical_staff | §2-C staff (doctor+therapist 통합) + §2-D doctors 별도 (post-19-P) + §3 분류표 staff.doctors_service |
| G-7 (신규) 순환 위험 + 분리 순서 | §5 9개 위험 + §6 분리 순서 영향 명시. wrapper / adaptor 가 §6-D 표로 분리됨 |
| G-8 (신규) 19-P-3 caveat 반영 | symbol 위주 (줄 번호 참고만) + `leave_type` DB 표준 명시 + dirty 표현 정확 |

→ G-1 ~ G-8 전부 통과 시 **yes — 19-P-5 진입 가능**.

## 13. Codex 가 반드시 확인할 항목 (사용자 명시)

| 검증 항목 | 본 문서 위치 |
|---|---|
| `app/`, `tests/`, migrations, requirements.txt, PyInstaller spec, UI 무수정 | §5 / §6 |
| `docs/refactor/19_refactor_dependency_map.md` 작성 | §3 신규 |
| `reports/refactor/{19-P-4,latest}_codex_review_request.md` 작성 | §3 신규 |
| appointments / patients / staff / doctors / leaves / treatments / stats / sms / admin / backup / ai / calendar / notes / settings / audit / health / export_import / core 의존성 검토 | §8 (16개 항목) |
| 허용 / 제한 / 금지 / 후속 검토 의존성 분류 현실적 | §3 분류표 50+ 행 |
| 순환참조 위험 구간 누락 X | §10 (9개 + audit) |
| AI/RAG local-first 보존 | §1 D-6 + §2-K + §7-B |
| 개인정보 / API key / 운영DB 안전 경계 반영 | §7-B SAFETY (12개 위치) |
| COMPAT / SAFETY / NOTE / RISK / TODO 주석 지점 반영 | §11 (5 카테고리) |
| 다음 단계 19-P-5 테스트 전략 진입 가능 | §12 G-1 ~ G-8 |

## 14. Codex 검증 결과 기록 위치

- [reports/refactor/19-P-4_codex_review.md](19-P-4_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

응답 형식 권장:

```markdown
# 19-P-4 Codex 검증 결과

## 1. 종합 판정
{pass | pass with caveat | fail}

## 2. 게이트별 결과
- G-1 ~ G-8: {결과 + 근거}

## 3. 추가 발견 위험 / 누락 / 부정확 항목
{있으면 bullet}

## 4. 19-P-5 진입 권고
{yes / no + 근거}
```

## 15. Claude Code 자체 판단

**yes (19-P-5 진입 권고)** — Codex 검증 후 다음 세션 진입 가능.

근거 (r2 기준):
1. 본 세션 (r1+r2 통틀어) 은 read-only — 코드 변경 0, 응답 키/마이그레이션/spec/UI/테스트 무수정.
2. `dependency_map.md` 8개 섹션 + 의존성 분류표 50+행 + 순환 위험 9개 + 분리 순서 5개 분류 + 주석 지점 5 카테고리 = 사용자 §1-7 모두 커버.
3. 19-P-3 Codex r1 caveat 3개 모두 반영 — symbol 위주 / `leave_type="am"`/`"pm"` 명시 / dirty 표현 정확.
4. **r2 보정**: 19-P-4 r1 Codex minor issues 3개 정정 — §0-1 신규 2개→3개 / 줄수 640→620 / §2-B PII 경로 "현재 vs 목표 후속" 명시.
4. 의존성 원칙 D-1 ~ D-13 + 금지 의존성 F-1 ~ F-9 + 순환 5-1 ~ 5-9 + 분리 순서 6-A ~ 6-E 정합.
5. AI/RAG local-first 보존 — D-6 / §2-K / §7-B (AI ⊥ 도메인 + 의사 가드 후속).
6. 의사 / 진료진 보강 — §2-C staff 통합 + §2-D doctors 별도 (post-19-P) + §7-B (의사 가드 후속).
7. 응답 키 보호 — §3 분류표 + §7-A COMPAT (wrapper / alias / 33+ 키 / ENTITY_MAP).
8. 18-8 baseline 회귀 보호 100%.
9. 19-P-1 / 19-P-2 / 19-P-3 산출물 무수정.

남은 위험:
- T-1 ~ T-15 (19-P-2) 의사결정 항목 — 19-P-5+ 점진 결정.
- 비-AI 86 endpoint contract 미작성 (C-1~C-7) — 19-P-5 테스트 전략에서 보강 계획.
- §5-2 availability 차단 로직 위치 — 분리 직전 grep 후 헬퍼 추출 시점 결정.
- 18-0~18-8 변경분 main 머지 / `docs/ai_rag_current_state.md` stale 보정 — 별도 세션.
- 세션 경계 Git 검증 caveat — 18-0~18-8 미커밋 (이전 세션부터 알려진 사항).
