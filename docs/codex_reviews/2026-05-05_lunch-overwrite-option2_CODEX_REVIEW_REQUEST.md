# CODEX_REVIEW_REQUEST — lunch-overwrite-option2 (2026-05-05)

## 1. 사용자 원래 요청

```
2
(직전 보고의 [다음] 옵션 ② — 점심 슬롯에 예약 있어도 점심 라벨로 덮어쓰기)
```

## 2. Claude Code 작업 요약

엑셀 다운로드 정책 변경 — 점심 슬롯 가독성 우선:
- **이전**: 점심 슬롯 + 예약 있으면 *예약 표시* (보고서 정확성 우선)
- **변경**: 점심 슬롯 = *항상 점심 라벨/회색* (보고서 가독성 우선). 예약은 시각적 가리기 — 실제 데이터는 DB 그대로 (UI 보드에서 확인 가능)

세로 병합 충돌 방지:
- 예약 *시작* 이 점심 슬롯 → cell_map 등록 ❌
- 일반→점심 걸치는 60분 예약 → span 점심 직전까지 자름 (예: 12:00 시작 60분, 12:30 점심 → span 1)

## 3. 사용한 내부 Agent 목록

01 Brainstorming → 09 Business Logic (점심 정책 변경) → 04 Code → 05 Test (회귀 가드 갱신)

## 4. 수정한 파일 목록

| 파일 | 변경 |
|---|---|
| `app/routers/api.py` | cell_map 빌드: 점심 시작 skip + span 자르기 (+10) / 데이터 행: is_lunch 우선 (+5 -3) |

## 5. 새로 만든 파일 목록

- `docs/codex_reviews/2026-05-05_lunch-overwrite-option2_CODEX_REVIEW_REQUEST.md` (본 파일)

## 6. 실행한 테스트 명령

```powershell
venv\Scripts\python.exe -m pytest tests/test_export_lunch_window.py -v
venv\Scripts\python.exe -m pytest tests -q
venv\Scripts\python.exe -m ruff check app tests scripts
```

## 7. 테스트 결과

- 점심 가드: **8 passed** (이전 7 + 신규 2 - 갱신 1)
- 전체: **2154 passed / 1 skipped / 10 xfailed / 0 failed (25.53s)**
- ruff: **All checks passed!**

## 8. 영향 범위

| 영역 | 영향 |
|---|---|
| API | `/api/export/manual-schedule.xlsx` 응답 본문만 변경 |
| DB | 영향 ⊥ (cfg 읽기만, 데이터 무수정) |
| 등록 차단 | `_check_lunch_block` 별도 정책 — 변경 ⊥ |
| 운영 DB | 영향 ⊥ |
| AI 안전 | 영향 ⊥ |
| UI 보드 | 영향 ⊥ (엑셀만 변경) |

## 9. Codex 가 검증해야 할 체크리스트

- [ ] **점심 시작 예약 가리기 정확성** — `if row_idx in lunch_slots: continue` 가 cell_map 등록 차단
- [ ] **span 자르기 경계** — 12:00 시작 60분 + 12:30 점심 → span 1 / 13:00 시작 30분 + 12:30 점심 (없는 경우) 정상
- [ ] **세로 병합 충돌 ❌** — 예약 병합이 점심 슬롯을 침범하지 않는지
- [ ] **점심 슬롯 cell 처리 우선순위** — is_lunch 가 entry 보다 우선
- [ ] **점심 라벨 1회 보장** — 첫 빈 점심 셀 (ci=0 첫 점심 row) 에 라벨
- [ ] **invalid lunch config graceful** — 형식 오류 시 lunch_slots 빈 set, 가독성 정책 적용 ❌
- [ ] **운영 외부 점심 graceful** — 운영 슬롯과 겹치지 않으면 영향 ⊥
- [ ] **AI / 도메인 정책 / DB / 운영 DB / 자동 발송 영향 ⊥** 검증

## 10. Codex 금지사항

- 코드 직접 수정 ❌
- 운영 DB 수정 ❌
- 기존 탭 이름 변경 ❌
- 새 탭 추가 ❌
- AI preview → approve 구조 변경 ❌
- 환자 개인정보 외부 전송 ❌
- 문자 자동 발송 구조 변경 ❌
- Claude Code 설명 그대로 신뢰 ❌ — `app/routers/api.py:4515~` (lunch_slots 식별), `app/routers/api.py:4569~` (cell_map 빌드 점심 skip + span 자르기), `app/routers/api.py:4625~` (데이터 행 is_lunch 우선) 실제 파일 검증

## 11. Codex 보고 형식

1. 전체 판정 (승인 / 조건부 승인 / 반려)
2. 잘 된 부분
3. 문제점
4. 위험한 변경
5. 누락된 테스트
6. 추가 테스트 제안
7. 수정 제안 (파일:라인)
8. 반드시 수동 확인할 화면
9. 최종 의견
