# UI_REVIEW_CHECKLIST

UI / 디자인 / CSS 작업 시 *반드시 거쳐야 하는* 체크리스트. 사용자 메모리 `feedback_ui_review_patterns.md` 와 정합.

> 본 체크리스트는 Claude Code 가 UI 작업 후 **완료 선언 전** 에 거치는 검증 절차.
> 빠뜨린 항목이 있으면 사용자가 가독성 / 일관성 문제를 다시 지적하게 됨.

---

## 1. 색상 토큰 작업 시

- [ ] `app.css` `:root {}` 토큰값 갱신
- [ ] `grep -nE "color:\s*#" app/static/css/*.css app/templates/*.html` — **hardcoded 색상 전수** 식별
- [ ] `grep -cE "color:\s*#(9CA3AF|6B7280|6E7A86|7E8A97|5F6B76)"` — *흐린 회색* 카운트 0 확인
- [ ] 인라인 `style="color:..."` 도 검사 (templates 안)
- [ ] cascade 후속 정의 (같은 셀렉터 다중 정의) 위치 모두 식별
- [ ] WCAG AA 준수 — 일반 텍스트 4.5:1, 큰 텍스트 3:1

## 2. 상태색 (success/warning/danger/info) 사용 시

- [ ] *솔리드 배경 / 진행바 / 큰 영역* 만 솔리드 토큰 (`--success` 등) 사용
- [ ] *텍스트 / 배지 / 메시지* 는 별도 *-text 토큰 (`--success-text` 등) 사용
- [ ] `.ai-helper-msg--*`, `.ai-helper-badge--*`, `.ai-helper-tag--*` 모두 *-text 토큰
- [ ] `.no-show-badge`, `.danger-zone .section-title` 등 위험 영역 *-text 사용

## 3. 클래스 다중 정의 검사

- [ ] 동일 셀렉터 (`.muted`, `.btn`, `.tab-btn`, `.sheet`) 가 여러 곳 정의된 경우 모두 grep
- [ ] cascade 마지막 정의가 우선 → 후속 정의 추가 시 의도 명확히
- [ ] 기존 정의 손대지 않고 *후속 정의로 우선 적용* 패턴 안전

## 4. 모든 탭 / 화면 검사 (사용자가 한 곳만 지적해도)

| 탭 | 검사 항목 |
|---|---|
| ▦ 예약 | `<nav class="tabs-nav">` / 사이드바 카드 (mini-cal / legend / today-list) 헤더 / today-date / AI 도우미 카드 |
| ◎ 환자 | `.sheet-head <h2>` / `.sheet-toolbar` 라벨 / `<small class="muted">` / placeholder / 검색결과 행 |
| ◇ 직원 | `.sub-tabs` 텍스트 / 프로필 라벨 / 색상 팔레트 팝업 / 활성 토글 |
| ✉ 예약 문자 | 다음날 환자 리스트 / 체크박스 라벨 / 문자 내용 영역 |
| AI 도우미 | `.ai-helper-card` 헤더 / status badge / msg / candidate-sub / approval prompt |
| ≡ 관리자 | 설정 카드 / 위험 영역 (백업/복원) / 권한 안내 |
| 휴무 (직원 서브탭) | AI 휴무 도우미 카드 / 종일·반차 표시 / 충돌 안내 |
| 통계 | stat-card / summary-card / 노쇼 배지 / 차트 라벨 |

## 5. 인라인 partial 도 함께 검사

- `app/templates/_ai_appointment_helper.html`
- `app/templates/_ai_leave_helper.html`
- `app/templates/setup.html`
- `app/templates/server_info.html`
- `app/templates/base.html`

## 6. 작업 후 회귀 확인

- [ ] `venv\Scripts\python.exe -m pytest tests -q` 통과
- [ ] `venv\Scripts\python.exe -m ruff check app tests scripts` All passed
- [ ] `tests/test_admin_ui_smoke.py`, `test_ai_helper_ui_integration.py`, `test_ai_leave_integration.py` 모두 통과
- [ ] 정책 변경 시 회귀 가드 갱신 (예: hardcoded 검증 → 토큰 검증)

## 7. 시각 검증

- [ ] `venv\Scripts\python.exe run.py` 띄워 모든 탭 직접 확인 — *내가 검증할 수 없으면 그 사실 명시*
- [ ] Ctrl+Shift+R 강제 새로고침 후 변경 반영 확인
- [ ] 모바일 폭 (720px / 1024px) 에서 레이아웃 깨짐 ❌

## 8. 자주 빠뜨리는 항목 (실수 패턴)

| # | 실수 | 회피 방법 |
|---|---|---|
| 1 | 토큰만 갱신하고 hardcoded 사용처 검사 ❌ | grep 으로 전수 식별 후 일괄 교체 |
| 2 | cascade 후속 정의 충돌 인지 ❌ | 같은 셀렉터 다중 정의 grep |
| 3 | 인라인 `style="..."` 검사 ❌ | templates 까지 grep 확장 |
| 4 | 사용자 명시 한 곳만 fix, 다른 곳 빠뜨림 | 같은 패턴 모든 탭 동시 fix |
| 5 | 상태색 텍스트로 사용 시 *-text 토큰 빠뜨림 | success/warning/danger/info 모두 *-text 토큰 신설 |
| 6 | `<small>` / `.muted` / placeholder 구분 없이 한 색상 | 의도된 흐림 (placeholder/disabled) 만 --text-muted |
| 7 | 시각 검증을 사용자에게 떠넘김 | dev 서버 띄워 가능한 영역 직접 확인 |
| 8 | 정책 변경 후 회귀 가드 갱신 ❌ | 정책과 테스트 *동시* 수정 |
| 9 | 큰 파일 (app.css 4,000+) 에서 같은 셀렉터 새로 추가 시 중복 | grep 후 기존 위치 갱신 또는 후속 통합 정의 |
| 10 | 임의 컬러 시스템 도입 (Bootstrap / Material) | 사용자 명시 (Tailwind 계열) 안에서 결정 |
| 11 | 작업 보고에 "사용자 검증 필요" 만 적기 | 검증 가능한 건 먼저 검증 → 결과 보고 |
| 12 | 한 글자 / 한 영역만 보고 비슷한 패턴 영역 빠뜨림 | "비슷한 패턴 다른 곳" 추가 grep |
| 13 | background 만 변경 + 짝인 color 검증 ❌ → contrast 깨짐 | bg 변경 시 color 동시 검사. `!important` 강제 색 grep |
| 14 | cascade 다중 정의에서 후속 !important 우회 ❌ | `grep -n "셀렉터" *.css` 모든 위치 + !important 식별 |
| 15 | 디자인 짝 시스템 (subhead-bg+subhead-text) 부분만 변경 → 시스템 깨짐 | 짝 단위로 변경. 모든 사용처 정합 검증 |
| 16 | !important 사용처 일관 정렬 ❌ | 한 영역 !important 변경 시 같은 패턴 모든 영역 동시 |

## 9. 작업 완료 보고서에 포함할 항목

- 변경 파일 목록 + 각 파일 변경 라인 수
- 토큰 정의 / 사용처 / cascade 변화 요약
- 회귀 테스트 결과 (passed / failed / xfail)
- 시각 검증 가능 여부 + 사용자 의뢰 항목
- 가독성 contrast ratio 계산 (가능하면)
- 영향 받지 않은 영역 명시 (보존 확인)
