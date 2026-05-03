# AI 코드 세션 공통 절차 (ai_code_session_protocol)

> 18-0 이후 모든 AI/RAG 코드 작성 세션에서 공통 적용한다.
> 본 문서는 절차만 다룬다. 규칙은 `AI_WORKING_RULES.md`, 문서 목차는 `ai_docs_index.md`.

---

## 1. 세션 시작 전 확인 문서 — 공통 베이스 5개 (통일 기준)

세션 진입 즉시 다음 5개를 **반드시** 읽는다.

1. `docs/AI_WORKING_RULES.md`
2. `docs/ai_code_session_protocol.md` (본 문서)
3. `docs/ai_docs_index.md`
4. `docs/ai_rag_current_state.md`
5. **해당 세션 체크리스트** `docs/checklists/18-X_*.md`

세션별 추가 참조 문서는 `ai_docs_index.md` §3 표 또는 해당 체크리스트 "참조해야 할 상세 문서 목록" 섹션에서 명시한 것만 읽는다. 상세 설계 문서를 매 세션 모두 읽지 않는다.

`reports/ai_dev_loop/latest_codex_review_request.md`가 존재하면 직전 세션의 미해결 위험 요소를 먼저 확인한다.

---

## 2. 세션 목표 확인 방법

1. 세션 이름 = `{SESSION_NAME}` 형식 고정 (예: `18-3_chunker`).
2. 사용자 지시문에서 다음을 추출:
   - 작업 목표(한 문장)
   - 수정 가능한 파일/모듈 범위
   - 명시적 금지 항목
3. 추출 결과를 세션 첫 응답에 한국어 3~5줄 요약으로 출력 후 작업 시작.

---

## 3. 수정 가능 / 금지 범위 확인

- **수정 가능 기본 범위**: 세션 지시문에 명시된 파일·테스트·문서.
- **자동 금지 범위**(지시문 명시 없으면 항상 금지):
  - 운영 DB 경로 관련 코드(`app/config.py:get_db_path` 등)
  - `tests/conftest.py`, `tests/harness/`의 격리 로직 약화
  - `pyproject.toml`의 `app/**` per-file-ignores
  - 기존 AI 라우터 응답 스키마(필드 제거/이름 변경/타입 변경)
  - 기존 마이그레이션 파일(역행/수정)
- 범위 밖 파일을 건드려야 할 정황이 보이면 작업을 멈추고 사용자에게 확인.

---

## 4. 코드 작성 절차 (자동 테스트·수정 루프)

다음 14단계를 순서대로 수행한다.

1. **세션 목표 확인** (§2)
2. **관련 설계 문서 확인** (§1 + 세션별 조합표)
3. **변경 전 관련 파일 파악**
   - 수정 대상 파일을 먼저 읽고 현재 흐름을 한국어로 짧게 요약(자체 메모).
4. **최소 범위로 코드 수정**
   - 한 회차에 한 가지 변경만. 디자인·리팩토링 혼합 금지.
5. **변경 파일 요약 작성**
   - 임시 메모로 보관. 5단계 완료 후 `latest_fix_summary.md`에 합산.
6. **테스트 실행**
   - 기본: `run_check.bat` (pytest + ruff + check_db_path).
   - 세션별로 추가 하네스 테스트가 정의되면 함께 실행.
7. **실패 시 원인 분석**
   - 실패 메시지·로그·관련 파일을 분석해 가설 작성.
8. **수정**
   - 가설 기반 최소 수정.
9. **다시 테스트**
10. **6~9를 최대 5회까지 반복** (테스트 루프 카운트 명시적으로 1~5).
11. **5회 안에 통과**하면 §5의 성공 리포트 작성.
12. **5회 실패**하면:
    - 부분 수정 즉시 중단.
    - `reports/ai_dev_loop/latest_failure_report.md` 작성.
    - 사용자에게 "코드 재작성 방향 검토 필요" 보고.
13. **`reports/ai_dev_loop/latest_codex_review_request.md`** 작성 (성공/실패 무관).
14. **Codex 검증 전 다음 세션으로 넘어가지 않음.**

---

## 5. 성공 시 작성 파일

루프가 5회 안에 통과한 경우:

1. `reports/ai_dev_loop/latest_test_report.md`
   - 실행 명령, 환경, 통과/실패 카운트, 주요 로그 발췌.
2. `reports/ai_dev_loop/latest_fix_summary.md`
   - 변경 파일 목록, 파일별 변경 요약, 의도/이유.
3. `reports/ai_dev_loop/latest_codex_review_request.md` (§7 참조)
4. 세션별 영구 보존본 (덮어쓰기 방지):
   - `reports/ai_dev_loop/{SESSION_NAME}_test_report.md`
   - `reports/ai_dev_loop/{SESSION_NAME}_fix_summary.md`
   - `reports/ai_dev_loop/{SESSION_NAME}_codex_review_request.md`

---

## 6. 실패 시 작성 파일

루프가 5회 실패한 경우:

1. `reports/ai_dev_loop/latest_failure_report.md`
   - 시도 회차별 가설 / 변경 / 결과
   - 마지막 테스트 출력
   - 코드 재작성 / 설계 재검토 권고
2. `reports/ai_dev_loop/latest_codex_review_request.md` (§7)
3. 세션별 영구 보존본:
   - `reports/ai_dev_loop/{SESSION_NAME}_failure_report.md`
   - `reports/ai_dev_loop/{SESSION_NAME}_codex_review_request.md`

이 시점부터 사용자 승인 없이 같은 작업을 재시도하지 않는다.

---

## 7. `latest_codex_review_request.md` 필수 항목

다음 20개 항목을 반드시 포함한다(번호 유지).

1. 세션 이름
2. 작업 목표
3. 변경 파일 목록
4. 변경 요약
5. 절대 바뀌면 안 되는 기능 (회귀 보호 대상)
6. 실행한 테스트 명령
7. 테스트 결과 요약
8. 자동 수정 루프 횟수 (1~5)
9. 5회 실패 여부
10. 운영 DB 보호 검사 결과 (`scripts/check_db_path.py` 출력)
11. RAG 하네스 결과
12. API 계약 테스트 결과 (응답 스키마 회귀)
13. 할루시네이션 금지 테스트 결과
14. PII 보호 테스트 결과
15. 기존 SMS AI 회귀 테스트 결과
16. 기존 휴무 AI 회귀 테스트 결과
17. 남은 위험 요소
18. Codex가 집중 검토할 파일
19. Codex가 반드시 확인할 체크리스트
20. 다음 세션으로 넘어가도 되는지에 대한 Claude Code의 자체 판단 (yes/no + 근거)

---

## 8. Codex 검증 원칙

1. Claude Code의 테스트 통과는 **최종 완료가 아니다**.
2. Codex 검증은 다음 세션으로 넘어가기 위한 **필수 게이트**다.
3. Codex는 `latest_codex_review_request.md`를 시작점으로 쓰되,
   **실제 diff·변경 파일·테스트 결과·로그를 독립적으로** 확인한다.
4. Codex 검증이 종료되기 전에는 다음 세션 진입 금지.
5. Codex 결과가 "재작업 필요"면 본 절차 §4의 1~10을 다시 실행.

---

## 9. 절차 위반 시

- Claude Code는 위반된 절차 항목 번호를 한국어로 명시 후 보고.
- 사용자 승인 없이 임의 우회 금지.
- `AI_WORKING_RULES.md` §5의 위반 처리 규정과 동일.
