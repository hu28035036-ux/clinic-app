# CODEX_REVIEW_REQUEST — remove-ai-manual-tab (2026-05-05)

## 1. 사용자 원래 요청

```
수정사항이야 ai 도우미탭이 필요가없을거같아 지워줘
```

## 2. Claude Code 작업 요약

`tab-ai-manual` (업무 매뉴얼 Q&A, RAG 기반) 탭의 **UI 만 제거**. 백엔드 (`/api/ai/manual/ask`, `app/services/ai/manual_qa.py`, RAG 모듈, `app/services/ai/knowledge/*`, `app/services/ai/rag/*`, `app/services/ai/vector/*`, m012/m013 마이그레이션, `knowledge/` 폴더, 관련 10+ 테스트) **보존** — 추후 재활성 가능 + 사용자 의사 ("필요 없을 것 같아") 의 보수적 해석.

AI 예약 도우미 / AI 휴무 도우미 (예약/휴무 화면 *내부 카드*, AI_CURRENT_DECISIONS § 16.2) 는 *별개 영역* 으로 영향 ⊥.

## 3. 사용한 내부 Agent 목록

01 Command Brainstorming → 04 Code Maintenance → 05 Test/Harness → 10 Docs

## 4. 수정한 파일 목록

| 파일 | 변경 |
|---|---|
| `app/templates/main.html` | -83줄 (탭 버튼 1줄 + section 46줄 + JS askManualQa() 함수 + 주석 81줄 / 보존 주석 4줄 추가) |
| `tests/test_ai_helper_ui_integration.py` | 탭 존재 검증 → 탭 *제거* 검증으로 회귀 가드 갱신 (정책 변경 회귀 가드) |
| `scripts/ui_integration_check.py` | dict key "AI 도우미 탭 (기존 RAG)" → "AI 도우미 탭 제거 (UI)" |
| `docs/agent/08_UI_QA_AGENT.md` | 탭 인덱스 표 — `tab-ai-manual` 행 ~~취소선~~ + UI 제거 명시 |

## 5. 새로 만든 파일 목록

- `docs/codex_reviews/2026-05-05_remove-ai-manual-tab_CODEX_REVIEW_REQUEST.md` (본 파일)

## 6. 실행한 테스트 명령

```powershell
venv\Scripts\python.exe -m pytest tests -q
venv\Scripts\python.exe -m ruff check app tests scripts
```

## 7. 테스트 결과

- pytest: **2143 passed / 1 skipped / 10 xfailed / 0 failed (20.12s)**
- ruff: **All checks passed!**

## 8. 영향 범위

| 영역 | 영향 |
|---|---|
| 화면 | 메인 탭 nav 에서 "AI 도우미" 버튼 제거 (탭 6 → 5 표시) |
| API | `/api/ai/manual/ask` 그대로 (호출처만 사라짐) |
| DB | 영향 ⊥ (m012 knowledge_chunks / m013 knowledge_vectors 보존) |
| 테스트 | `test_ai_helper_ui_integration.py` 회귀 가드 갱신, RAG 테스트 10+ 그대로 |
| AI 기능 | AI 예약 도우미 / AI 휴무 도우미 (내부 카드) 영향 ⊥ |
| 백엔드 모듈 | `app/services/ai/manual_qa.py`, RAG / knowledge / vector 패키지 그대로 |
| `dosu_clinic.spec` | 영향 ⊥ — hidden imports 그대로 |

## 9. Codex 가 검증해야 할 체크리스트

- [ ] **사용자 의도 정합** — "필요 없을 것 같아 지워줘" 가 *UI 만* 제거 (보수적) vs *전체* 제거 어느 쪽 의미인지 추정 적정성
- [ ] **다른 탭 영향 ❌** — 예약 / 환자 / 직원 / 예약 문자 / 관리자 모든 탭 정상 동작
- [ ] **AI 예약 / 휴무 도우미 영향 ❌** — 예약 화면 내부 카드 / 휴무 서브탭 내부 카드 그대로
- [ ] **백엔드 endpoint 보존** — `/api/ai/manual/ask` 가 라우터에 등록되어 있는지 확인
- [ ] **CSS 영향 ❌** — `tab-ai-manual` 관련 스타일이 다른 곳에 영향 안 미치는지
- [ ] **JS 함수 제거 후 다른 곳 호출 ❌** — `askManualQa` 호출처가 다른 곳에 남아 있는지
- [ ] **회귀 가드 갱신 적정성** — `test_ai_helper_ui_integration.py` 의 새 assertion 정합
- [ ] **CLAUDE.md 절대 금지 11항목 위반 ❌** — 특히 "AI 가 직접 DB 수정 / 자동 발송"
- [ ] **사용자 통합 디자인 지시문의 "기존 메뉴 구조 변경 ❌"** 와 정합 (사용자 명시 변경 요청이라 예외)

## 10. Codex 금지사항

- 코드 직접 수정 ❌
- 운영 DB (`%APPDATA%\도수치료예약\clinic.db`) 직접 수정 ❌
- 기존 탭 이름 변경 ❌
- 사용자 미요청 새 탭 추가 ❌
- AI preview → approve 구조 변경 ❌
- 환자 개인정보 외부 전송 ❌
- 문자 자동 발송 구조 변경 ❌
- Claude Code 설명 그대로 신뢰 ❌ — 실제 파일 (`app/templates/main.html`, `tests/test_ai_helper_ui_integration.py`, `scripts/ui_integration_check.py`, `docs/agent/08_UI_QA_AGENT.md`) 기준으로 검증

## 11. Codex 보고 형식

다음 9 항목 그대로 RESULT.md 작성:

1. 전체 판정 (승인 / 조건부 승인 / 반려)
2. 잘 된 부분
3. 문제점
4. 위험한 변경
5. 누락된 테스트
6. 추가 테스트 제안
7. 수정 제안 (파일:라인)
8. 반드시 수동 확인할 화면
9. 최종 의견
