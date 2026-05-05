# CODEX_REVIEW_REQUEST — excel-lunch-window (2026-05-05)

## 1. 사용자 원래 요청

```
다른수정있는데 예약표 엑셀 다운로드에서 점심시간설정하면 그시간도 엑셀에 적용되게 바꿔줘
그리고 다시 코덱스 위험 수정해
```

## 2. Claude Code 작업 요약

`/api/export/manual-schedule.xlsx` (도수치료 예약현황 엑셀) 가 점심시간 (`cfg.lunch_enabled` / `lunch_start` / `lunch_end`) 을 반영하지 않던 사용자 보고 fix.

설계:
- cfg 에서 점심 시간 읽기 → 슬롯 [m, m+SLOT) 가 점심창 [l_start, l_end) 와 *겹치는* ri 식별 (`lunch_slots`)
- 데이터 행 처리 루프에서:
  - 시간 셀 (A 컬럼) 배경 `#E5E7EB` (UI `--disabled-bg` 정합)
  - 점심 슬롯 + 예약 *없는* 셀 배경 `#E5E7EB`
  - 첫 점심 슬롯 첫 빈 컬럼에 `"점심시간 HH:MM~HH:MM"` 라벨 1회
  - 점심 슬롯 + *예약 있는* 셀은 기존 흐름 그대로 (예약 표시 우선 — 보고서 정확성)

## 3. 사용한 내부 Agent 목록

01 Brainstorming → 09 Business Logic (점심 정책) → 04 Code → 05 Test → 10 Docs (보류 — CHANGELOG)

## 4. 수정한 파일 목록

| 파일 | 변경 |
|---|---|
| `app/routers/api.py` | `export_manual_schedule()` 에 lunch_slots 식별 (+22) + 데이터 행 처리에 회색 분기 (+5) |

## 5. 새로 만든 파일 목록

- `tests/test_export_lunch_window.py` — 회귀 가드 3건 (비활성 / 활성 / 회색 배경)
- `docs/codex_reviews/2026-05-05_excel-lunch-window_CODEX_REVIEW_REQUEST.md` (본 파일)

## 6. 실행한 테스트 명령

```powershell
venv\Scripts\python.exe -m pytest tests/test_export_lunch_window.py -v
venv\Scripts\python.exe -m pytest tests -q
venv\Scripts\python.exe -m ruff check app tests scripts
```

## 7. 테스트 결과

- 신규 가드: **3 passed (0.62s)**
- 전체 pytest: **2149 passed / 1 skipped / 10 xfailed / 0 failed (21.76s)** (이전 2146 + 3 신규)
- ruff: **All checks passed!**

## 8. 영향 범위

| 영역 | 영향 |
|---|---|
| API | `/api/export/manual-schedule.xlsx` (엑셀 응답 본문만, status code 변경 ⊥) |
| DB | 영향 ⊥ (cfg 읽기만) |
| 기능 | 점심 시간 *시각 표시* 추가 — 실제 예약 등록/차단 로직 무수정 (`_check_lunch_block` 그대로) |
| AI | 영향 ⊥ |
| 운영 DB | 영향 ⊥ (cfg.json 읽기만) |
| UI 보드 | 영향 ⊥ (엑셀 출력만 변경) |

## 9. Codex 가 검증해야 할 체크리스트

- [ ] **lunch_slots 식별 정확성** — 슬롯이 점심창과 *겹치는지* (`not (slot_end <= l_start or m >= l_end)`) 의 경계 조건
- [ ] **lunch_enabled=False 시 회색 ❌** — 토글 OFF 시 엑셀에 영향 ⊥ 보장
- [ ] **lunch_start/end 형식 오류 시 graceful** — `_hm_to_min` 예외 시 lunch_slots 빈 set, 라벨 빈 문자열
- [ ] **점심 슬롯에 *예약 있는* 셀** — 기존 예약 표시 보존 (보고서 정확성)
- [ ] **세로 병합 (60분 예약, span > 1) 충돌** — 점심 슬롯의 skip 셀 처리 정합
- [ ] **회귀 가드 충분성** — 3건 (비활성 / 활성 / 회색 배경) 외 부족 영역
- [ ] **CLAUDE.md 절대 금지 11항목 위반 ❌** — 도메인 정책 / API 경로 / 자동 발송 등

## 10. Codex 금지사항

- 코드 직접 수정 ❌
- 운영 DB 수정 ❌
- 기존 탭 이름 변경 ❌
- 새 탭 추가 ❌
- AI preview → approve 구조 변경 ❌
- 환자 개인정보 외부 전송 ❌
- 문자 자동 발송 구조 변경 ❌
- Claude Code 설명 그대로 신뢰 ❌ — 실제 파일 (`app/routers/api.py:4412~`, `tests/test_export_lunch_window.py`) 기준 검증

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
