# CODEX_REVIEW_GUIDE

병원예약관리 (도수치료예약, v1.3.5+) 의 **Codex CLI 검증 워크플로우 단일 원천**.

- 작성: 2026-05-05
- 정책 출처: 사용자 명시 통합 지시문
- Claude Code = 총괄 에이전트 / Codex = 검증·리뷰 전용 외부 에이전트

> 본 가이드는 *Claude Code 가 작업 완료 후* Codex 에 검증을 의뢰하는 표준 절차.
> 모든 비-사소 작업 (UI 대규모 변경 / DB 스키마 / AI 게이트 / 도메인 정책 변경 / 배포) 후 적용.

---

## 1. Codex CLI 호출 명령 (Windows PowerShell 표준)

```powershell
codex.cmd exec --sandbox read-only --ephemeral --output-last-message "docs\codex_reviews\<TIMESTAMP>_<TASK>_CODEX_REVIEW_RESULT.md" - < "docs\codex_reviews\<TIMESTAMP>_<TASK>_CODEX_REVIEW_REQUEST.md"
```

- `codex.cmd` 사용 — `.ps1` ExecutionPolicy 회피
- `--sandbox read-only` — Codex 가 파일 *수정 ❌*. 검증만.
- `--ephemeral` — 세션 휘발 (history 기록 ❌)
- `--output-last-message <path>` — Codex 마지막 응답을 결과 파일로 저장
- `- <` — stdin 으로 요청서 파일 전달 (PowerShell 리다이렉션)

### 1.1 호출 전 확인

```powershell
codex.cmd --help
```
정상 출력 + exit 0 이어야 진행. 미설치 / 로그인 ❌ 시 사용자에게 보고하고 *자동 검증 진행 ❌*.

## 2. 처리 흐름 (12 단계)

```
1. Claude Code 작업 완료
2. Claude Code 자체 테스트 (run_check.bat: pytest + ruff + DB 안전검사)
3. Claude Code 가 docs/codex_reviews/<TIMESTAMP>_<TASK>_CODEX_REVIEW_REQUEST.md 작성
4. 파일명 규칙: YYYY-MM-DD_<task-id>_CODEX_REVIEW_REQUEST.md
                YYYY-MM-DD_<task-id>_CODEX_REVIEW_RESULT.md
5. Claude Code 가 codex.cmd exec 실행
6. Codex 가 코드 미수정 + 검증 리포트 작성
7. 결과는 RESULT.md 에 자동 저장 (--output-last-message)
8. Claude Code 가 RESULT.md 읽고 *독립 재검토*
9. Claude Code 가 지적사항을 [반영 / 미반영 / 보류] 분류
10. 필요한 수정만 *최소 범위* 반영
11. 테스트 재실행
12. CHANGELOG / 작업 로그에 Codex 검증 결과 + 반영 여부 기록
```

## 3. 검증 요청서 (REQUEST.md) 11 필수 항목

```markdown
# CODEX_REVIEW_REQUEST — <task-id> (<date>)

## 1. 사용자 원래 요청
(사용자가 한국어로 한 짧은 요청 원문 그대로)

## 2. Claude Code 작업 요약
(한 단락으로 무엇을 했는지)

## 3. 사용한 내부 Agent 목록
(예: 01 Brainstorming → 04 Code → 05 Test → 10 Docs)

## 4. 수정한 파일 목록
- 절대경로 + 변경 라인 수

## 5. 새로 만든 파일 목록
- 절대경로

## 6. 실행한 테스트 명령
- venv\Scripts\python.exe -m pytest tests -q
- venv\Scripts\python.exe -m ruff check app tests scripts
- venv\Scripts\python.exe scripts\check_db_path.py

## 7. 테스트 결과
- pytest: N passed / M failed / X xfail / Y skipped
- ruff: All checks passed / N errors
- DB safety: OK / FAIL

## 8. 영향 범위
- 화면 / API / DB / 테스트 / AI 기능 별 영향 명시

## 9. Codex 가 검증해야 할 체크리스트
(작업 도메인 별 — 예: UI 변경이면 모든 탭 헤더 contrast / 기능 변경이면 회귀 / DB 면 마이그레이션 안전 등)

## 10. Codex 금지사항 (8개)
- 코드 직접 수정 ❌
- 운영 DB (`%APPDATA%\도수치료예약\clinic.db`) 직접 수정 ❌
- 기존 탭 이름 변경 ❌
- 사용자 미요청 새 탭 추가 ❌
- AI preview → approve 구조 변경 ❌
- 환자 개인정보 외부 전송 ❌
- 문자 자동 발송 구조 변경 ❌
- Claude Code 설명 그대로 신뢰 ❌ — *실제 파일 기준* 검증

## 11. Codex 보고 형식 (9 항목)
(아래 § 4 그대로)
```

## 4. 검증 결과서 (RESULT.md) 9 항목 형식

Codex 가 작성:

```markdown
# CODEX_REVIEW_RESULT — <task-id> (<date>)

## 1. 전체 판정
[ ] 승인 (approve)
[ ] 조건부 승인 (conditional)
[ ] 반려 (reject)

## 2. 잘 된 부분
- ...

## 3. 문제점
- ...

## 4. 위험한 변경
- 운영 DB 영향 / AI 안전 정책 / 도메인 정책 위반 가능성

## 5. 누락된 테스트
- ...

## 6. 추가 테스트 제안
- ...

## 7. 수정 제안
- 파일:라인 + 권장 수정안

## 8. 반드시 수동 확인할 화면
- 사용자가 dev 서버에서 직접 확인할 항목

## 9. 최종 의견
- 한 단락 종합
```

## 5. Claude Code 의 Codex 결과 처리 규칙

| 원칙 | 적용 |
|---|---|
| Codex 결과 = 참고 자료 | 최종 답 ❌, 무조건 반영 ❌ |
| 독립 재검토 | 각 지적사항을 *실제 파일 기준* 으로 다시 grep / Read |
| 분류 | [반영 / 미반영 / 보류] 3 선택지 |
| 미반영 사유 기록 | 왜 반영 안 했는지 기록 |
| 보류 = 추후 확인 | 다음 작업 시 또는 사용자 결정 시 |
| 최종 판단 | Claude Code 가 함 |
| 사용자 승인 영역 | Codex 가 승인했어도 사용자 승인 별도 — 빌드 / 배포 / 도메인 정책 |

## 6. 적용 범위

### 6.1 자동 Codex 검증 *대상*
- UI 대규모 변경 (Phase A~M 같은 풀세트)
- DB 스키마 변경 (m0XX 신규)
- AI 안전 정책 / 인증 정책 변경
- 도메인 규칙 변경 (manual60 카운트, 충돌 판정 등)
- 배포 직전 (PyInstaller 빌드 전)

### 6.2 자동 Codex 검증 *생략 가능*
- 단순 lint fix
- CHANGELOG 한 줄 추가
- 메모리 / docs 정리 (코드 무수정)
- 사용자가 "Codex 생략" 명시 (사용자 메모리 `feedback_ai_phase_workflow.md` 의 "Codex 생략 모드" 정합)

### 6.3 사용자 명시 영역
- 사용자가 "Codex 검증 해줘" 명시 → 무조건 진행
- 사용자가 "Codex 생략" 명시 → 진행 ❌

## 7. 파일명 / 폴더 규칙

```
docs/codex_reviews/
├── CODEX_REVIEW_GUIDE.md                            (본 문서)
├── 2026-05-05_<task-id>_CODEX_REVIEW_REQUEST.md     (예시)
├── 2026-05-05_<task-id>_CODEX_REVIEW_RESULT.md      (예시)
└── ...
```

- TIMESTAMP: `YYYY-MM-DD` (한 작업이 한 날에 여러 번이면 `YYYY-MM-DD_HHMM`)
- task-id: 짧은 영문 (예: `ui-contrast-fix`, `m021-doctor-extension`, `auth-policy-change`)

## 8. CHANGELOG 기록 형식

CHANGELOG.txt 또는 작업 로그에:

```
▸ Codex 독립 검증 (<task-id>)
  - 판정: 승인 / 조건부 / 반려
  - 반영: <지적 항목> (이유)
  - 미반영: <지적 항목> (이유)
  - 보류: <지적 항목>
  - 결과 파일: docs/codex_reviews/<...>_RESULT.md
```

## 9. 사용 메모리와의 관계

- `feedback_command_brainstorming.md` — 01 Brainstorming 경유 후 Codex 검증
- `feedback_ai_phase_workflow.md` — AI Phase 검증 워크플로우 (자체 10회 + Codex 생략 모드)
- `feedback_codex_review_workflow.md` — 본 가이드 단일 원천

## 10. 트러블슈팅

| 증상 | 해결 |
|---|---|
| `codex.cmd : 인식할 수 없는 명령` | 사용자에게 Codex CLI 설치 + 로그인 (`codex login`) 요청 |
| `codex.ps1 ExecutionPolicy` 오류 | `codex.cmd` 로 호출 (본 가이드 표준) |
| 결과 파일 빈 출력 | `--output-last-message` 경로 확인 / Codex 응답 길이 확인 |
| 파일 수정 시도 | `--sandbox read-only` 누락 — 명령 재확인 |
| 한글 깨짐 | PowerShell `chcp 65001` 또는 stdin 파일 UTF-8 확인 |
