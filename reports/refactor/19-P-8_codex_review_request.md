# 19-P-8 Codex 검증 요청서

> **사용자가 Codex에게 전달할 최소 문구**
>
> > "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

## 0. Revision 이력

| 회차 | 날짜 | 결과 | 변경 |
|---|---|---|---|
| r1 | 2026-05-03 | (본 revision) | 초기 작성 — 19-P-8 단위화 리팩토링 의사결정 기록 문서 신규 작성. 19-P-7 r3 Codex `pass with caveat (yes — 19-P-8 진입 가능)` 위에서 진행. 코드/테스트/spec/UI/migrations/requirements 무수정. |

본 요청서는 19-P 단위화 리팩토링 여덟 번째 세션의 산출물 (의사결정 기록 문서) 1건을 Codex 가 독립적으로 검증할 수 있도록 작성한 표준 패키지다.

---

## 0-A. Baseline

- HEAD commit: `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 / 19-P-6 r1+r2 / 19-P-7 r3 Codex 판정: **pass / pass / pass with caveat / pass with caveat / pass with caveat / pass with caveat / pass with caveat (yes — 19-P-8 진입 가능)** ([reports/refactor/latest_codex_review.md](latest_codex_review.md) — 19-P-7 r3 결과)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed**
- 19-P-7 r3 caveat 본 19-P-8 반영:
  - "약 70 Risk" 잔여 표현은 위험 등록 §6-2 의 Risk × 주석 매트릭스 표현 — 본 19-P-8 의사결정 매트릭스 (§6-1) 는 "결정 20개 × 주석 6 카테고리" 표현으로 충돌 0.
  - 18-0~18-8 변경분 main 머지는 19-0 시점에 정리 (19-P-6 §0-1 / §2 / §5-2).
  - pytest 미실행 = read-only 검증 정합.
- 본 세션은 위 commit 위에 신규 commit 없이 untracked 문서 추가만 수행. 코드/테스트/spec/UI/migrations/requirements 무수정.

## 1. 세션 이름

**19-P-8 단위화 리팩토링 의사결정 기록 문서 작성**

- 19-P-1 [현재 구조](../../docs/refactor/19_refactor_current_state.md), 19-P-2 [목표 아키텍처](../../docs/refactor/19_refactor_target_architecture.md), 19-P-3 [모듈 매핑](../../docs/refactor/19_refactor_module_map.md), 19-P-4 [의존성 맵](../../docs/refactor/19_refactor_dependency_map.md), 19-P-5 [테스트 전략](../../docs/refactor/19_refactor_test_strategy.md), 19-P-6 [롤아웃 계획](../../docs/refactor/19_refactor_rollout_plan.md), 19-P-7 [위험 등록](../../docs/refactor/19_refactor_risk_register.md) 의 후속 문서.
- 단위화 리팩토링을 **왜 이 구조와 순서로 진행하는지** 의사결정 근거를 정리. 이후 코드 세션에서 방향이 흔들리지 않게 + Codex 검증 시 판단 기준 + 후속 재구조화 시 결정 이유 추적.
- read-only 문서 세션. 실제 코드 / 테스트 / fixture / mock / 마이그레이션 미작성.

## 2. 이번 세션 목표

| # | 목표 | 본문 위치 |
|---|---|---|
| 1 | §1 의사결정 기록 목적 5개 (기준/이유 / 방향 흔들림 방지 / Codex 판단 기준 / 재구조화 시 추적 / 18-AI 동일 형식) | docs/refactor/19_refactor_decision_record.md §1 |
| 2 | §2 핵심 의사결정 20개 — 사용자 §2 의 A ~ T (20개) 모두 등록. 각 항목 = 결정 ID / 결정 내용 / 결정 이유 / 대안 / 선택하지 않은 이유 / 기대 효과 / 위험 / 관련 문서 / 관련 테스트/하네스 / Codex 검증 포인트 (10 필드) | §2-A ~ §2-T |
| 3 | §3 선택하지 않은 대안 9개 — 사용자 §3 명시 8개 + 본 19-P-8 추가 1개 (3-9 단위화 보류) | §3-1 ~ §3-9 |
| 4 | §4 결정과 위험 등록 연결 — DEC-A ~ DEC-T 20개 → 19-P-7 Risk ID 77개 매핑 + 사용자 §4 예시 4개 정합 | §4 + §4-1 |
| 5 | §5 결정과 테스트 전략 연결 — DEC-* 14개 → 19-P-5 §3 + §4 보강 9개 매핑 + 사용자 §5 예시 6개 정합 | §5 + §5-1 |
| 6 | §6 결정과 주석 / 문서화 연결 — 결정 × 주석 카테고리 6종 (COMPAT/SAFETY/NOTE/RISK/TODO/TEMP) 매트릭스 + 향후 코드 이동 시 주석 위치 16개 | §6-1 + §6-2 |
| 7 | §7 변경 가능성 / 재검토 기준 10개 — 사용자 §7 명시 6개 + 본 19-P-8 추가 4개 | §7 + §7-1 |
| 8 | §8 종합 — 결정 20개 / 대안 9개 / Risk 매핑 / 테스트 매핑 / 주석 매트릭스 / 재검토 기준 / 19-P-9 진입 권고 | §8 |

## 3. 작성한 문서

### 신규 (3)

- [docs/refactor/19_refactor_decision_record.md](../../docs/refactor/19_refactor_decision_record.md) — 의사결정 기록 (§0 ~ §8). 본 19-P-8 신규.
- [reports/refactor/19-P-8_codex_review_request.md](19-P-8_codex_review_request.md) (본 문서, 영구 보존본)
- [reports/refactor/latest_codex_review_request.md](latest_codex_review_request.md) (Codex 진입점 — 본 문서와 동일)

### Codex 작성 예정

- [reports/refactor/19-P-8_codex_review.md](19-P-8_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

## 4. 수정 금지였던 범위

11개 금지 항목 (사용자 명시):
1. 코드 수정
2. `app/` 기능 코드 수정
3. `tests/` 테스트 코드 작성
4. migration 생성
5. `requirements.txt` 수정
6. PyInstaller spec 수정
7. UI 수정
8. 기존 API 응답 구조 변경
9. 운영 DB 접근
10. 실제 외부 API 호출
11. 하네스/테스트 약화

추가:
- 18-8 baseline 회귀 보호 (529 passed, 1 skipped, 7 xfailed).
- m001~m013 diff 0.
- 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 / 19-P-6 / 19-P-7 산출물 무수정.

## 5. 실제 수정한 파일 목록

### 신규 (3)

- `docs/refactor/19_refactor_decision_record.md`
- `reports/refactor/19-P-8_codex_review_request.md` (본 문서)
- `reports/refactor/latest_codex_review_request.md`

### 무수정 (회귀 보호)

`app/**`, `tests/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`, `CLAUDE.md`, `app/services/**`, 19-P-1~19-P-7 산출물.

> `latest_codex_review_request.md` 는 19-P-8 진입점으로 덮어쓰여진다 (19-P-7 본문은 [19-P-7_codex_review_request.md](19-P-7_codex_review_request.md) r3 영구 보존).

## 6. 코드 수정 없이 docs/refactor + reports/refactor 문서만 작성했는지 확인

| 검사 | 결과 |
|---|---|
| 본 19-P-8 신규 파일 | `19_refactor_decision_record.md` + `{19-P-8,latest}_codex_review_request.md` (3개) |
| `app/**` / `tests/**` / migrations / spec / UI / `pyproject.toml` 변경 | 0 |
| 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 / 19-P-6 / 19-P-7 산출물 변경 | 0 |
| 새 fixture / mock / harness 파일 추가 | 0 |
| 새 contract 테스트 추가 | 0 (의사결정 기록만 — 19-1~13 분리 직전 보강) |

→ **코드 수정 없이 docs/refactor + reports/refactor 문서만 작성**.

### Codex 가 직접 검증할 명령

```bash
git status --short
git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml
# 결과: 18-0~18-8 변경분만 + 본 19-P-8 추가 변경분 0
ls docs/refactor/
ls reports/refactor/
```

> **dirty/untracked 표현 (19-P-3 caveat 반영)**: 본 19-P-8 산출 = 신규 문서 3개. 18-0~18-8 변경분은 작업트리에 dirty/untracked 로 남아 있지만 본 세션과 무관 — 19-0 시점에 정리 (19-P-6 §0-1 / §2 / §5-2 명시).

## 7. Codex 가 검증해야 할 문서

### 1차 (필수)

- [docs/refactor/19_refactor_decision_record.md](../../docs/refactor/19_refactor_decision_record.md) (본 세션 신규)

### 2차 (대조 기준)

- [docs/refactor/19_refactor_current_state.md](../../docs/refactor/19_refactor_current_state.md) (19-P-1 r2)
- [docs/refactor/19_refactor_target_architecture.md](../../docs/refactor/19_refactor_target_architecture.md) (19-P-2 r3)
- [docs/refactor/19_refactor_module_map.md](../../docs/refactor/19_refactor_module_map.md) (19-P-3)
- [docs/refactor/19_refactor_dependency_map.md](../../docs/refactor/19_refactor_dependency_map.md) (19-P-4 r2)
- [docs/refactor/19_refactor_test_strategy.md](../../docs/refactor/19_refactor_test_strategy.md) (19-P-5 r2)
- [docs/refactor/19_refactor_rollout_plan.md](../../docs/refactor/19_refactor_rollout_plan.md) (19-P-6 r2)
- [docs/refactor/19_refactor_risk_register.md](../../docs/refactor/19_refactor_risk_register.md) (19-P-7 r3)
- [docs/AI_WORKING_RULES.md](../../docs/AI_WORKING_RULES.md) (절대 원칙 + local-first)
- [docs/ai_rag_decision_record.md](../../docs/ai_rag_decision_record.md) (18-AI 의사결정 기록 — 동일 형식 비교)
- [docs/releases/18_ai_rag_release_notes.md](../../docs/releases/18_ai_rag_release_notes.md) (18-AI baseline)
- [docs/releases/18_ai_rag_final_checklist.md](../../docs/releases/18_ai_rag_final_checklist.md) (18-AI 최종 체크리스트)
- [reports/refactor/19-P-7_codex_review.md](19-P-7_codex_review.md) (직전 r3 pass with caveat — yes 진입 가능)

## 8. 의사결정이 현재 구조 / 목표 구조 / 모듈 매핑 / 의존성 / 테스트 / 위험 문서와 일관적인지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 의사결정 기록 위치 | 대조 기준 문서 |
|---|---|---|
| DEC-A 단위화 = 구조 안정화 | §2-A | 19-P-1 §1-2 (현재 구조 혼재) / 19-P-2 §1 P-1 / 19-P-6 §1 R-1 |
| DEC-B 세션 1개 = 모듈 1개 | §2-B | 19-P-2 §1 P-5 + §8-1 + §8-3 / 19-P-6 §1 R-2 + R-3 + R-7 |
| DEC-C API URL / 응답 키 보존 | §2-C | 19-P-1 §21 (33+ 키 셋) / 19-P-2 §1 P-2 + §7-1 + §7-2 / 19-P-5 §1 T-3 / 19-P-6 §1 R-4 |
| DEC-D DB schema 최소 변경 | §2-D | 19-P-1 §4-1 (m001~m013) / 19-P-2 §1 P-4 + §7-3 / 19-P-6 §1 R-6 / [CLAUDE.md](../../CLAUDE.md) |
| DEC-E router/service/repository | §2-E | 19-P-2 §2 + §5 + §6 / 19-P-4 §1 D-1~D-13 + §2 + §3 |
| DEC-F appointments 마지막 분리 (19-9) | §2-F | 19-P-2 §3-1 + §9 (M-01 우선순위 14) / 19-P-3 §2-1 / 19-P-4 §2-A + §6 / 19-P-6 §3-9 / 19-P-7 §2-A |
| DEC-G availability 별도 책임 (19-4) | §2-G | 19-P-2 §2-1 + §4 + §3-1 / 19-P-4 §2-A + §5-2 / 19-P-5 §3-1 / 19-P-6 §3-4 / 19-P-7 §2-A |
| DEC-H leaves 분리 (19-5) | §2-H | 19-P-2 §3-4 / 19-P-3 §2-5 / 19-P-4 §2-E / 19-P-5 §3-5 / 19-P-6 §3-5 / 19-P-7 §2-E |
| DEC-I treatments / completion_rules (19-6) | §2-I | 19-P-2 §3-5 + §2-1 / 19-P-3 §2-6 / 19-P-4 §2-F / 19-P-5 §3-6 / 19-P-6 §3-6 / 19-P-7 §2-F / [CLAUDE.md](../../CLAUDE.md) (manual60=1) |
| DEC-J stats read-only (19-11) | §2-J | 19-P-2 §3-6 + §2-1 / 19-P-3 §2-7 / 19-P-4 §2-G + §1 D-7 / 19-P-5 §3-7 / 19-P-6 §3-11 / 19-P-7 §2-G + §2-P |
| DEC-K sms (19-10) | §2-K | 19-P-2 §3-7 + §2-1 / 19-P-3 §2-8 / 19-P-4 §2-H + §1 D-8 / 19-P-5 §3-9 / 19-P-6 §3-10 / 19-P-7 §2-H |
| DEC-L patients / notes (19-7) | §2-L | 19-P-2 §3-2 + §4 + §2-2 / 19-P-3 §2-2 + §2-14 / 19-P-4 §2-B / 19-P-5 §3-2 / 19-P-6 §3-7 / 19-P-7 §2-B + §2-M |
| DEC-M staff 통합 (19-8) | §2-M | 19-P-2 §3-3 + §2-2 / 19-P-3 §2-3 + §2-4 / 19-P-4 §2-C + §2-D / 19-P-5 §3-3 + §3-4 / 19-P-6 §3-8 / 19-P-7 §2-C + §2-D |
| DEC-N AI/RAG local-first | §2-N | [docs/AI_WORKING_RULES.md](../../docs/AI_WORKING_RULES.md) §1 + §2 / 19-P-2 §1 P-7 + §3-10 + §7-7 / 19-P-4 §1 D-6 + §2-K / 19-P-5 §1 T-12 + T-13 / 19-P-6 §1 R-12 / 19-P-7 §2-K |
| DEC-O AI commands DB 변경 조심 (19-13) | §2-O | 19-P-2 §3-10 + §6-1 / 19-P-4 §2-K + §1 D-6 / 19-P-6 §3-13 / 19-P-7 §2-K |
| DEC-P health / settings / feature_flags (19-2) | §2-P | 19-P-2 §3-8 + §4 + §2-2 / 19-P-3 §2-15 + §2-16 + §2-19 + §2-21 / 19-P-4 §2-I + §1 D-10 / 19-P-6 §3-2 / 19-P-7 §2-I + §2-O |
| DEC-Q audit / logs (19-12) | §2-Q | 19-P-2 §4 / 19-P-3 §2-17 + §2-23 / 19-P-4 §2-N + §1 D-9 / 19-P-6 §3-12 / 19-P-7 §2-N + §2-T |
| DEC-R PyInstaller 검증 | §2-R | 19-P-2 §1 P-10 + §7-6 / 19-P-5 §2-6 / 19-P-6 §3-14 / 19-P-7 §2-W / [CLAUDE.md](../../CLAUDE.md) (배포 규칙) |
| DEC-S 주석 / 문서화 기준 | §2-S | 19-P-3 §0-2 / 19-P-6 §4 / 19-P-7 §6-1 + §6-2 / [CLAUDE.md](../../CLAUDE.md) |
| DEC-T Codex 게이트 매 세션 | §2-T | [docs/AI_WORKING_RULES.md](../../docs/AI_WORKING_RULES.md) §4 / [docs/ai_code_session_protocol.md](../../docs/ai_code_session_protocol.md) §4 + §7 + §8 / [docs/ai_codex_review_protocol.md](../../docs/ai_codex_review_protocol.md) |

### Codex 검증 명령 — 결정 일관성

```bash
# 결정 ID 카운트 (20개 기대)
grep -nE "^### 2-[A-T]\." docs/refactor/19_refactor_decision_record.md | wc -l   # 20 기대
# DEC-A ~ DEC-T 결정 ID 명시
grep -nE "^\| 결정 ID \| \*\*DEC-[A-T]\*\*" docs/refactor/19_refactor_decision_record.md | wc -l   # 20 기대
# 19-P 문서 링크 정합 (19-P-1 ~ 19-P-7)
grep -nE "19_refactor_(current_state|target_architecture|module_map|dependency_map|test_strategy|rollout_plan|risk_register)\.md" docs/refactor/19_refactor_decision_record.md | wc -l   # 다수 기대
# Risk ID 매핑 카운트 (77 Risk 중 다수)
grep -nE "R-(APPT|PAT|THER|DOC|LEAVE|TX|STAT|SMS|ADM|BAK|AI|CAL|AUDIT|HEALTH|EXIM|CORE|TIME|BATCH|LOCK|OPS)-[0-9]" docs/refactor/19_refactor_decision_record.md | wc -l   # 다수 기대
```

## 9. 선택하지 않은 대안과 그 이유가 현실적인지 확인할 항목

### Codex 검증 포인트

| 사용자 §3 명시 대안 | 본 문서 매핑 | 검증 포인트 |
|---|---|---|
| 전체 app 구조를 한 번에 대규모 이동 | §3-1 | 코드 diff 검토 불가 / Codex 검증 불가 / rollback = 전체 무효 — DEC-B 와 정합 |
| 새 DB schema 를 먼저 대규모 정리 | §3-2 | 운영 DB 손상 / 마이그레이션 실패 / sync 키 변경 — DEC-D 와 정합 |
| 프론트 UI 까지 동시에 리팩토링 | §3-3 | main.html 7331줄 + JS 6800줄 동시 수정 회귀 폭증 — [CLAUDE.md](../../CLAUDE.md) 정합 |
| appointments 를 첫 번째로 크게 분리 | §3-4 | 의존 도메인 미분리 상태 wrapping 폭증 — DEC-F 와 정합 |
| AI/RAG 를 외부 LLM 중심으로 재설계 | §3-5 | 토큰 비용 / PII 외부 / API key / 할루시네이션 — DEC-N 와 정합 |
| 기존 API 응답 key 를 새 구조에 맞춰 변경 | §3-6 | main.html / sync 외부 호환 깨짐 — DEC-C 와 정합 |
| 테스트 없이 파일 이동부터 진행 | §3-7 | 응답 키 변경 / 헬퍼 누락 발견 못함 — [docs/AI_WORKING_RULES.md](../../docs/AI_WORKING_RULES.md) §3 정합 |
| Codex 검증 없이 다음 단계로 진행 | §3-8 | 변경 범위 초과 / 테스트 약화 누적 — DEC-T 와 정합 |
| (추가) 단위화 비활성 / 보류 | §3-9 | 사용자 보류 결정 시 baseline 유지 — 재개 가능 |

### Codex 검증 명령 — 대안 현실성

```bash
# 선택하지 않은 대안 9개 카운트 (3-1 ~ 3-9)
grep -nE "^### 3-[1-9]\." docs/refactor/19_refactor_decision_record.md | wc -l   # 9 기대
# 각 대안의 "후속 검토 가능성" 표기
grep -nE "후속 검토 가능성" docs/refactor/19_refactor_decision_record.md | wc -l   # 9 기대
```

## 10. 주석 / 문서화 기준이 의사결정 기록에 반영되었는지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 문서 위치 |
|---|---|
| §6-1 결정 × 주석 카테고리 6종 (COMPAT/SAFETY/NOTE/RISK/TODO/TEMP) 매트릭스 | §6-1 (결정 20개 × 6 카테고리) |
| §6-2 향후 코드 이동 시 주석이 필요한 위치 16개 | §6-2 (위치 + 주석 태그 + 근거 결정) |
| DEC-S 주석 카테고리 정의 일관 | §2-S |
| 본 19-P-8 산출이 코드 주석 작성 ⊥ (코드 무수정) | §0 + §6-2 머리말 |
| `# TODO(...)` 는 세션 번호 / 제거 조건 포함 의무 | §2-S 결정 내용 + §6-1 + §6-2 |
| 주석 작성으로 동작 변경 ⊥ | §2-S 결정 내용 + DEC-S |

### Codex 검증 명령 — 주석 매트릭스 정합

```bash
# 주석 카테고리 5종 + TEMP grep 카운트
grep -nE "(COMPAT|SAFETY|NOTE|RISK|TODO|TEMP)" docs/refactor/19_refactor_decision_record.md | wc -l   # 다수 기대
# §6-1 매트릭스 표 검증
grep -nE "^\| DEC-[A-T] " docs/refactor/19_refactor_decision_record.md | wc -l   # 20 기대 (§6-1 매트릭스 + §4 위험 매핑)
# §6-2 위치 16개
grep -nE "^\| `app/" docs/refactor/19_refactor_decision_record.md | wc -l   # 14~16 기대
```

## 11. 다음 단계 (19-P-9 공통 체크리스트 문서) 진입 가능 판단 기준

| 게이트 | 통과 조건 |
|---|---|
| G-1 코드 무수정 | `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 본 19-P-8 추가 변경분 0. 19-P-1 ~ 19-P-7 산출물 무수정. |
| G-2 핵심 의사결정 등록 정합 | 사용자 §2 의 A ~ T (20개) 가 §2-A ~ §2-T 에 모두 매핑. 각 결정에 10 필드 (결정 ID / 내용 / 이유 / 대안 / 선택하지 않은 이유 / 효과 / 위험 / 관련 문서 / 테스트 / Codex 검증 포인트) 모두 채워짐. |
| G-3 선택하지 않은 대안 정합 | 사용자 §3 명시 8개 + 본 19-P-8 추가 1개 = 9개 모두 §3-1 ~ §3-9 에 등록. 각 대안에 위험 / 후속 검토 가능성 표기. |
| G-4 위험 등록 매핑 정합 | §4 표 = 결정 20개 → Risk ID 77개 매핑. 사용자 §4 4개 예시 (appointments / availability / sms / local-first) 모두 §4-1 에 정합. |
| G-5 테스트 전략 매핑 정합 | §5 표 = 결정 14개 → 19-P-5 §3 + §4 보강 9개 매핑. 사용자 §5 6개 예시 모두 §5-1 에 정합. |
| G-6 주석 / 문서화 매트릭스 정합 | §6-1 매트릭스 = 결정 20 × 6 카테고리. §6-2 위치 16개. DEC-S 정의 + 주석 작성 ⊥ 명시. |
| G-7 재검토 기준 정합 | §7 = 사용자 §7 명시 6개 + 본 19-P-8 추가 4개 = 10개 트리거. 영향 결정 ID + 재검토 절차 명시. |
| G-8 19-P-1 ~ 19-P-7 충돌 ⊥ | 본 결정 20개가 모두 19-P-1 ~ 19-P-7 산출물의 P-* / R-* / D-* / T-* / RB-* / Risk ID 와 정합. |
| G-9 appointments 마지막 분리 (DEC-F) 타당성 | DEC-F 결정 이유가 19-P-2 §3-1 + §9 M-01 우선순위 14 + 19-P-3 §31 + 19-P-4 §6 + 19-P-6 §3-9 + 19-P-7 §2-A 와 정합. |
| G-10 응답 키 / DB / local-first / Codex 게이트 명확 | DEC-C / DEC-D / DEC-N / DEC-T 모두 *절대 원칙* 으로 명확 등록. 예외 / 우회 표현 ⊥. |
| G-11 부재 항목 단정 ⊥ | DEC-M (staff 통합) 의 doctors / Patient.doctor_id / Doctor / Department / Room / DoctorSchedule / Order / Prescription / Resource / `/api/health` / 노쇼 / 반복예약 / 자원 / 알림 / 출력물 / EMR 모두 후속 검토 분류. 단정 ⊥. |
| G-12 주석 매트릭스 정합 | §6-1 결정 20 × 6 카테고리 + §6-2 위치 16개. 코드 미수정 — 실제 주석 작성 ⊥. |

→ G-1 ~ G-12 전부 통과 시 **yes — 19-P-9 진입 가능**.

## 12. Codex 가 반드시 확인할 항목 (사용자 명시)

| 검증 항목 | 본 문서 위치 |
|---|---|
| `app/`, `tests/`, migrations, requirements.txt, PyInstaller spec, UI 무수정 | §5 / §6 |
| `docs/refactor/19_refactor_decision_record.md` 작성 또는 수정 | §3 신규 |
| `reports/refactor/{19-P-8,latest}_codex_review_request.md` 작성 | §3 신규 |
| 결정들이 19-P-1 ~ 19-P-7 문서들과 충돌 ⊥ | §11 G-8 + 본 §8 |
| appointments 를 초반에 크게 이동하지 않는 이유 타당 | §11 G-9 + 본 §8 (DEC-F) |
| API 응답 key 유지 / DB schema 최소 변경 / local-first AI 유지 / Codex 검증 게이트 명확 | §11 G-10 + DEC-C / DEC-D / DEC-N / DEC-T |
| 현재 없는 기능 (doctors / EMR / 노쇼 / 반복예약 / 자원 / 알림 / 출력물 등) 을 실제 구현된 기능처럼 단정 ⊥ | §11 G-11 + DEC-M / §3-2 / §7 트리거 9 |
| 선택하지 않은 대안의 위험 설명이 현실적 | §11 G-3 + §3-1 ~ §3-9 |
| 향후 코드 이동 시 필요한 COMPAT / SAFETY / NOTE / RISK / TODO 주석 지점 반영 | §11 G-12 + §6-1 + §6-2 |
| 다음 단계 19-P-9 공통 체크리스트 문서로 넘어가도 되는가 | §11 G-1 ~ G-12 |

### Codex 검증 명령 — 부재 항목 단정 ⊥

```bash
# doctors / EMR 부재 항목 grep — 0건 기대
grep -nE "class Doctor|class Department|class Room|class DoctorSchedule|class Order|class Prescription|class Resource" app/models/models.py
grep -n "doctor_id" app/models/models.py   # Patient 에 0건 기대
grep -n "no_show" app/models/models.py     # 0건 기대 (status="canceled" 만)
grep -n "@router.*\"/api/health\"" app/routers/ -r   # 0건 기대 (/api/ai/health 와 별개)
# 본 19-P-8 의사결정 기록의 부재 항목 단정 ⊥ 표현 grep
grep -nE "현재 부재|부재 항목 단정|후속 검토|post-19-P|m014\+" docs/refactor/19_refactor_decision_record.md | wc -l   # 다수 기대
```

## 13. Codex 검증 결과 기록 위치

- [reports/refactor/19-P-8_codex_review.md](19-P-8_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

응답 형식 권장:

```markdown
# 19-P-8 Codex 검증 결과

## 1. 종합 판정
{pass | pass with caveat | fail}

## 2. 게이트별 결과
- G-1 ~ G-12: {결과 + 근거}

## 3. 추가 발견 위험 / 누락 / 부정확 항목
{있으면 bullet}

## 4. 19-P-9 진입 권고
{yes / no + 근거}
```

## 14. Claude Code 자체 판단

**yes (19-P-9 진입 권고)** — Codex 검증 후 다음 세션 진입 가능.

근거:
1. 본 세션은 read-only — 코드 변경 0, 응답 키/마이그레이션/spec/UI/테스트 무수정.
2. `19_refactor_decision_record.md` 9개 섹션 (§0~§8) — 의사결정 목적 5개 + 핵심 결정 20개 (DEC-A ~ DEC-T) + 선택하지 않은 대안 9개 + 위험 매핑 + 테스트 매핑 + 주석 매트릭스 + 재검토 기준 10개 = 사용자 §1~§7 모두 커버.
3. 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 / 19-P-6 r1+r2 / 19-P-7 r3 모두 pass / pass with caveat — 19-P-8 진입 가능 명시.
4. 응답 키 보호 — DEC-C 절대 원칙 + 19-P-1 §21 33+ 키 셋 / 비-AI 86 endpoint contract 부재 caveat 19-x 분리 직전 보강 명시.
5. DB schema 최소 변경 — DEC-D + m001~m013 diff 0 + m014+ 후속 결정.
6. AI/RAG local-first 보존 — DEC-N + DEC-O ([docs/AI_WORKING_RULES.md](../../docs/AI_WORKING_RULES.md) §2 절대 원칙 정합).
7. appointments 마지막 분리 (19-9) — DEC-F + 19-P-2 §3-1 + §9 M-01 우선순위 14 + 19-P-7 R-APPT-* 정합.
8. 부재 항목 단정 ⊥ — DEC-M / §3-2 / §7 트리거 9 + 19-P-2 §3-3-4 / 19-P-7 R-DOC-* / R-32~R-36 후속 정합.
9. 주석 매트릭스 — DEC-S + §6-1 결정 20 × 6 카테고리 + §6-2 위치 16개. 본 19-P-8 코드 미수정 — 실제 주석 작성 ⊥.
10. Codex 게이트 매 세션 — DEC-T + 본 요청서 14 항목 정합.
11. 18-8 baseline 회귀 보호 100% (529 passed, 1 skipped, 7 xfailed).
12. 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 / 19-P-6 / 19-P-7 산출물 무수정.

남은 위험 / caveat:
- 19-P-2 T-1 ~ T-15 (확인 필요 항목) 중 일부 (T-1 ~ T-13) 는 19-x 코드 세션 진입 시점에 결정 — 본 19-P-8 은 *방향성* 만 합의.
- 19-P-7 r3 caveat "약 70 Risk" 잔여 표현은 위험 등록 §6-2 표현 — 본 19-P-8 의사결정 매트릭스와 충돌 0.
- 18-0~18-8 변경분 main 머지 / `docs/ai_rag_current_state.md` stale 보정 — 19-0 또는 별도 세션.
- 비-AI 86 endpoint contract 부재 (C-1) — 본 19-P-8 은 의사결정 기록만, 실제 보강은 각 19-x 분리 직전.

다음 세션:
- **19-P-9 공통 체크리스트 문서** (`docs/refactor/19_refactor_common_checklist.md` 후보) — 19-x 코드 세션이 매 세션 적용할 *체크리스트* 정리. 본 19-P-8 의사결정 기록을 *체크리스트로 재구성* 한 형태. 19-P-1 ~ 19-P-8 모든 결정 사항을 체크 단위로 분해.

## 15. 게이트 정합

| 게이트 (§11) | 통과 근거 |
|---|---|
| G-1 코드 무수정 | §5 + §6 — `app/**`, `tests/**`, migrations, spec, UI, requirements 변경 0 |
| G-2 핵심 의사결정 20개 | §2 = 20개 결정 (DEC-A ~ DEC-T), 각 10 필드 (사용자 §2 정합) |
| G-3 선택하지 않은 대안 9개 | §3 = 9개 (사용자 §3 명시 8개 + 추가 1개), 각 위험 / 후속 검토 가능성 표기 |
| G-4 위험 등록 매핑 | §4 = 결정 20개 → Risk ID 77개 (19-P-7 합계 정합) + 사용자 §4 예시 4개 §4-1 정합 |
| G-5 테스트 전략 매핑 | §5 = 결정 14개 → 19-P-5 §3 + §4 보강 매핑 + 사용자 §5 예시 6개 §5-1 정합 |
| G-6 주석 매트릭스 | §6-1 = 결정 20 × 6 카테고리 매트릭스 / §6-2 = 위치 16개. DEC-S 정의 + 주석 작성 ⊥ |
| G-7 재검토 기준 10개 | §7 = 사용자 §7 6개 + 추가 4개 (단위화 보류 / local-first 변경 / EMR 도입 / 5회 루프 반복) |
| G-8 19-P-1 ~ 19-P-7 충돌 ⊥ | 본 §8 검증 항목 표 = 결정 20개 → 7개 문서 매핑 정합 |
| G-9 appointments 마지막 분리 (DEC-F) | §2-F + 19-P-2 §3-1 / 19-P-3 §31 / 19-P-4 §6 / 19-P-6 §3-9 / 19-P-7 §2-A 정합 |
| G-10 절대 원칙 명확 | DEC-C (응답 키) / DEC-D (DB) / DEC-N (local-first) / DEC-T (Codex 게이트) — 모두 *절대 원칙* 등록 |
| G-11 부재 항목 단정 ⊥ | DEC-M + §3-2 + §7 트리거 9 + §3-9 — doctors / EMR / 노쇼 / 반복예약 / 자원 / 알림 / 출력물 모두 후속 검토 |
| G-12 주석 매트릭스 정합 | §6-1 + §6-2 — 본 19-P-8 코드 미수정 (실제 주석 작성 ⊥) |
