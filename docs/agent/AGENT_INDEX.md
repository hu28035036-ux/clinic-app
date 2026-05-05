# AGENT_INDEX

병원예약관리 (도수치료예약) 프로젝트에 정의된 **12개 Agent 의 한 페이지 인덱스**. 각 Agent 의 책임 / 트리거 / 산출물 / 조합 패턴을 한 번에 본다.

> 본 문서는 *인덱스 / 매핑 표* — 자체 모델 정책 ❌, 자체 산출물 ❌. Master Orchestrator (00) 가 사용자 요청을 받았을 때 *어느 Agent 들을 동원할지* 결정하기 위한 빠른 참조표.

---

## 1. 12개 Agent 매핑

| # | Agent | 핵심 역할 | 트리거 (사용자 발화 예) |
|---|---|---|---|
| 00 | Master Orchestrator | 요청 해석 + Agent 분배 진입점 | 모든 사용자 요청의 진입점 |
| **01** | **Command Brainstorming** | **내부 회의 / 검토 / 분기 결정 (코드 수정 ❌)** | **모든 사용자 명령 — 단순도 짧게라도 검토** |
| 02 | Project Manager | Phase / 진행상태 / TODO 관리 | "지금 어디까지 했어", "다음 뭐 해야 해" |
| 03 | Architecture | 모듈 구조 / 의존성 / 신규 모듈 배치 | "이 코드 어디에 둬야 해", "구조 좀 정리하자" |
| 04 | Code Maintenance | 비-AI 백엔드/프런트 일반 코드 수정 | "예약 충돌 검사가 이상해", "환자 검색 결과가 빠져" |
| 05 | Test / Harness | pytest / ruff / DB 안전검사 / 하네스 | "테스트 실패 봐줘", "회귀 돌려줘" |
| 06 | AI Safety | AI 안전 정책 / Privacy / Hallucination | "AI 가 환자 이름 출력해", "AI 가 예약 완료라고 말해" |
| 07 | DB / Migration | `m0XX_*.py` 작성 + spec 등록 | "컬럼 추가", "유니크 제약" |
| 08 | UI / QA | `main.html` / `app.css` / Alpine 동작 점검 | "버튼이 안 눌려", "화면 깨짐" |
| 09 | Business Logic | 예약 / 통계 / 치료항목 / 휴무 도메인 규칙 | "manual60 카운트가 이상해", "통계 합계 오차" |
| 10 | Docs / CHANGELOG | `CHANGELOG.txt` / `VERSION.txt` / `versions/INDEX.txt` | "버전 올려줘", "변경 이력 정리" |
| 11 | Release Check | 빌드 가능 여부 / spec / hidden imports / 배포 게이트 | "배포해도 돼?", "빌드 깨질 위험 있어?" |

> 이 인덱스는 *총 12 Agent* 를 매핑하며, 본 인덱스 (`AGENT_INDEX.md`) 자체는 별도 Agent 가 아니다.

---

## 2. 표준 처리 흐름

```
사용자 명령
  ↓
[00 Master Orchestrator]   해석 + 복잡도 판정
  ↓
[01 Command Brainstorming] 내부 회의 + 영향 범위 + 처리안 + 위험도
  ↓                        (단순 명령은 짧게, 위험은 사용자 승인 필수)
하위 Agent 들 (02 ~ 11 중 선택)
  ↓
[05 Test/Harness]          run_check.bat + 도메인 회귀
  ↓
[Codex 외부 검증]          (대규모 변경 / 배포 직전 — codex.cmd exec)
  ↓                        (단일 원천: docs/codex_reviews/CODEX_REVIEW_GUIDE.md)
[Claude 독립 재검토]       반영 / 미반영 / 보류 분류 → 최소 수정 → 재테스트
  ↓
[10 Docs/CHANGELOG]        문서 / 버전 / spec / Codex 결과 기록
  ↓
[11 Release Check]         (배포 시점만)
  ↓
[00 Master 사용자 보고]
```

---

## 3. 자주 쓰이는 Agent 조합 패턴

| 사용자 요청 유형 | Agent 조합 (순서) |
|---|---|
| 단순 버그 픽스 (UI 변경 없음) | 01 → 04 → 05 → 10 |
| UI 만 수정 | 01 → 08 → 05 (스모크) → 10 |
| DB 컬럼 추가 + 도메인 규칙 변경 | 01 → 03 → 07 → 09 → 04 → 05 → 10 → 11 |
| AI 동작 수정 (인증 / 흐름 / 게이트) | 01 → 06 → 04 (또는 09) → 05 → 10 |
| AI 안전 위반 의심 | 01 → 06 → 05 (test_ai_safety_harness) → 10 |
| 예약 / 통계 도메인 규칙 변경 | 01 → 09 → 04 → 05 → 10 |
| 배포 직전 검사 | 01 → 11 → 10 (final CHANGELOG) |
| 코드 / 문서 / 폴더 정리 | 01 → 03 → 04 → 05 → 10 |
| 더미 / dev 환경 진입점 추가 | 01 → 04 → 10 → 05 |
| Phase 진척 확인 / 백로그 정리 | 01 → 02 → 10 |

---

## 4. 본 인덱스 유지 규칙

- 새 Agent 가 추가되거나 폐지되면 § 1 / § 3 갱신.
- 새로운 트리거 패턴이 발견되면 § 3 에 행 추가.
- 새 모듈 / 새 도메인 (예: 향후 doctors 확장, EMR) 이 들어오면 매핑 업데이트.
- 모든 처리 흐름은 **01 Command Brainstorming** 을 *경유* 한다 — 단순 요청도 짧게라도 검토.

---

## 5. 참조 문서

- `docs/agent/00_*.md` ~ `11_*.md` — 각 Agent 상세
- `CLAUDE.md` — 절대 금지 / 작업 전후 필수
- `docs/CHANGE_RULES.md` — 변경 절차
- `docs/specs/` — 도메인 규칙 단일 원천
- `docs/ai/AI_CURRENT_DECISIONS.md` / `AI_SAFETY_POLICY.md` — AI 단일 진실
- `docs/refactor/20_post_19p_master_plan.md` — 20-P 그룹 결정
- `MEMORY.md` — 사용자 자율 / 승인 / 절대 금지 3단계 정책
