# 20-3-1-UI F-10 노쇼 UI 검증 요청 (자기편향 검토 후)

## 메타

- 브랜치: `ai-rag-v1-integration`
- 직전 commit: `fb0ce48` (20-P-3 그룹 D 상세 기획)
- 본 세션: 1차 (main.html only) → 자기편향 검토 → 2차 (백엔드 보강) — Codex 사용량 소진으로 Claude 자체 검증 진행.
- 변경 파일: 6개 (main.html / api.py / service.py / schemas.py / test_19_9 / test_20_3_1)

## 자기편향 검토 결과 (Codex 대체)

본 세션 1차 (main.html only) 후 비판적 점검 → 3개 결함 발견 + 2차 보강:

| # | 결함 | 보강 |
|---|---|---|
| 1 | `CANCEL_RESPONSE_KEYS = {ok, version}` ↔ router 응답 3키 미정합 (19-9 contract 위반) | `schemas.py` 갱신 + `MARK_NO_SHOW_RESPONSE_KEYS` 신설 |
| 2 | `service.build_cancel_response` 2키, router 미채택 → contract test 가 router 응답 회귀 검출 불능 | `service.py` 갱신 (3키 + no_show 인자) |
| 3 | cancel?no_show=true memo prefix `[취소]` ↔ mark-no-show `[노쇼]` 데이터 일관성 결함 | `api.py` cancel memo prefix 분기 |

## 검증 항목

### 1. baseline 회귀 0

- pytest **1826 passed** / 1 skipped / 10 xfailed (1825 baseline + 1 회귀 보호 신규).
- ruff All checks passed.
- check_db_path exit 0.

### 2. 응답 key / API URL

- 33+ 응답 key 보존 + cancel 응답에 `no_show` 추가 (3키) — 19-9 contract 갱신.
- mark-no-show endpoint contract 신설 (4키) — 회귀 보호 추가.
- API URL 변경 0.

### 3. UI 변경 (1차 main.html 4 hunks)

- 노쇼 체크박스 (id=`c-no-show`) — `status === 'reserved'` 분기.
- 노쇼 배지 ("⚠ 노쇼") — `status === 'canceled' && ep.no_show=true` 분기.
- 통계 카드 6번째 ("노쇼") — `summary.no_show_count` 사용. canceled=0 시 noShowRate=0 fallback.

### 4. 백엔드 변경 (2차)

- `api.py` cancel: `prefix = "[노쇼]" if p.no_show else "[취소]"` — 단순 분기.
- `service.py` build_cancel_response: 3키 정합 + `no_show: bool = False` 기본 인자.
- `schemas.py` CANCEL_RESPONSE_KEYS / MARK_NO_SHOW_RESPONSE_KEYS — frozenset.

### 5. 핵심 보존 사항

- 19-9 EXTENDED_PROPS_KEYS 19키 보존 (no_show / series_id / resource_id 추가됨 — 직접 확인 OK).
- main.html FullCalendar event 형식 보존 (event handler 분기는 미반영, render 시각 표시는 후속 분할).
- m001~m018 변경 0.
- 운영 DB / 외부 API / 실제 문자 발송 ⊥.

### 6. 회귀 위험 점검 (보강 후)

| 위험 | 검증 |
|---|---|
| cancel 응답 2키 → 3키 변경 → 기존 UI 회귀 | UI 가 cancel 응답의 no_show 무시 (frontend cancelAppt 는 closeModal+refresh 만) — 회귀 0 |
| memo prefix `[취소]` → `[노쇼]` 분기 → 기존 메모 분석 회귀 | no_show=false 시 `[취소]` 그대로 보존 — 회귀 보호 테스트 신규 추가 |
| build_cancel_response 시그니처 변경 (no_show 인자 추가) | default=False 기본 인자 — 기존 호출자 회귀 0 |
| EXTENDED_PROPS_KEYS contract 갱신 (16→19 키) | 백엔드 commit 319a5aa 시점에서 갱신 완료 — 본 세션 변경 0 |

### 7. 데이터 일관성

cancel?no_show=true 와 mark-no-show endpoint 의 결과가 보강 후 완전 동일:
- status: "canceled"
- no_show: true
- memo prefix: `[노쇼]`

→ 두 흐름이 호환 가능 — UI 는 cancel?no_show=true 만 사용. mark-no-show endpoint 는 백엔드 보존.

### 8. Preview 통합 검증 (보강 후 재실행)

- A: cancel?no_show=true → `\n[노쇼] 연락두절` + no_show=true ✅
- B: cancel?no_show=false → `\n[취소] 환자 사정` + no_show=false ✅
- 응답 dict 3키 (`{ok, version, no_show}`) ✅
- extendedProps.no_show 직렬화 ✅
- 통계 카드 6개 + 노쇼 라벨 ✅
- 모달 노쇼 배지 + 체크박스 ✅

### 9. 미구현 (후속 분할 권장)

자기편향 검토에서 발견했지만 본 세션 outside 로 미룸:

1. **FullCalendar event render 분기** — 캘린더 화면 노쇼 시각 구분 부재. main.html event handler 변경 필요.
2. **일별 통계 표 노쇼 컬럼** — backend `/api/stats/daily` 응답 + UI 표 변경 필요.
3. **canceled 상태 노쇼 토글 / 노쇼 → 일반 취소 되돌림 UI** — endpoint 추가 + UI 보강 필요.
4. **by-therapist / by-treatment 노쇼 분기** — backend aggregator 변경 필요.

이들은 "수정해야 할 부분" 이지만 본 세션 범위 (UI + 데이터 일관성 보강) 초과. 사용자 결정 후 별도 분할.

## 검증 요청 (Claude 자체 검증)

1. 본 세션 변경 6개 파일 — 회귀 위험 (Section 6) 재검증.
2. 데이터 일관성 (Section 7) — cancel?no_show=true 와 mark-no-show endpoint 의 동등성.
3. 19-9 contract 정합 — CANCEL_RESPONSE_KEYS 3키 + MARK_NO_SHOW_RESPONSE_KEYS 4키.
4. baseline 1826 회귀 0 + ruff / check_db_path 통과.
5. 미구현 4개 (Section 9) — 후속 분할 권장 영역인지 또는 본 세션 진입 전 추가 진행해야 하는지.

## 자체 판단

- **통과**: 본 세션 사용자 결정 (i) "체크박스 + 통계 표시" 범위 + 자기편향 검토 결함 3개 모두 보강 완료.
- **commit 가능 조건**: 사용자가 미구현 4개 항목 (Section 9) 을 후속 분할로 인정하는 경우.

## 참조 문서

- [docs/refactor/20_post_19p_master_plan.md](../../docs/refactor/20_post_19p_master_plan.md)
- [docs/refactor/20_post_19p_group_c_detail_plan.md](../../docs/refactor/20_post_19p_group_c_detail_plan.md) §3 F-10
- [reports/refactor/20-3-1_test_report.md](20-3-1_test_report.md) (백엔드 commit 319a5aa)
- [reports/refactor/20-3-1-UI_test_report.md](20-3-1-UI_test_report.md) (본 세션 결과)
- [reports/refactor/20-3-1-UI_fix_summary.md](20-3-1-UI_fix_summary.md) (본 세션 변경 상세)
