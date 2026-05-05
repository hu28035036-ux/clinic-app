# CODEX_REVIEW_REQUEST — <task-id> (<YYYY-MM-DD>)

> 본 파일을 복사 → `<TIMESTAMP>_<task-id>_CODEX_REVIEW_REQUEST.md` 로 이름 변경 후 11 항목 채움.
> stdin 으로 `codex.cmd exec` 에 전달.

---

## 1. 사용자 원래 요청

```
(사용자가 한국어로 한 짧은 요청 원문 그대로 인용)
```

## 2. Claude Code 작업 요약

(한 단락으로 무엇을 했는지 — 변경 의도 / 도메인 / 핵심 결정사항)

## 3. 사용한 내부 Agent 목록

- 01 Command Brainstorming
- (해당 도메인 Agent 들)
- 05 Test/Harness
- 10 Docs/CHANGELOG

## 4. 수정한 파일 목록

| 파일 | 변경 라인 |
|---|---|
| `app/...` | +X / -Y |

## 5. 새로 만든 파일 목록

- `docs/...`

## 6. 실행한 테스트 명령

```powershell
venv\Scripts\python.exe -m pytest tests -q
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts\check_db_path.py
```

## 7. 테스트 결과

- pytest: **N passed / M failed / X xfail / Y skipped (Zs)**
- ruff: **All checks passed / N errors**
- DB safety: **OK / FAIL**

## 8. 영향 범위

| 영역 | 영향 |
|---|---|
| 화면 | (탭 / 모달 / 카드) |
| API | (/api/...) |
| DB | (테이블 / 컬럼 / 마이그레이션) |
| 테스트 | (test_*.py) |
| AI 기능 | (app/ai/* / app/services/ai/*) |

## 9. Codex 가 검증해야 할 체크리스트

(작업 도메인 별 — 다음 중 해당 항목)

- [ ] 사용자 의도 정합 (요청 1번과 변경 결과)
- [ ] 모든 탭 / 화면 일관성 (사용자가 한 곳 지적해도 비슷한 모든 곳 검사)
- [ ] CSS contrast 4.5:1+ (UI 변경 시)
- [ ] cascade !important 충돌 (CSS 변경 시)
- [ ] AI 안전 정책 (preview/approve, 단정 표현 ❌, Privacy)
- [ ] DB 마이그레이션 안전성 (m0XX 신규 시)
- [ ] 운영 DB 미접근 (모든 변경)
- [ ] 회귀 테스트 충분성 (test 추가 / 갱신)
- [ ] 문서 정합 (CHANGELOG / spec / 4점 버전)
- [ ] CLAUDE.md 절대 금지 11 항목 준수

## 10. Codex 금지사항

- 코드 직접 수정 ❌
- 운영 DB (`%APPDATA%\도수치료예약\clinic.db`) 직접 수정 ❌
- 기존 탭 이름 변경 ❌
- 사용자 미요청 새 탭 추가 ❌
- AI preview → approve 구조 변경 ❌
- 환자 개인정보 외부 전송 ❌
- 문자 자동 발송 구조 변경 ❌
- Claude Code 설명 그대로 신뢰 ❌ — *실제 파일 기준* 검증

## 11. Codex 보고 형식 (9 항목)

다음 9 항목을 *반드시* 포함한 RESULT.md 작성:

```markdown
# CODEX_REVIEW_RESULT — <task-id> (<date>)

## 1. 전체 판정
승인 / 조건부 승인 / 반려

## 2. 잘 된 부분
## 3. 문제점
## 4. 위험한 변경
## 5. 누락된 테스트
## 6. 추가 테스트 제안
## 7. 수정 제안 (파일:라인)
## 8. 반드시 수동 확인할 화면
## 9. 최종 의견
```

---

> 본 요청서는 *Claude Code 가 작성* — Codex 는 본 요청서를 *입력* 으로 받아 RESULT.md 로 응답.
> Codex 응답은 참고 자료 — Claude Code 가 [반영 / 미반영 / 보류] 분류 + 최종 판단.
