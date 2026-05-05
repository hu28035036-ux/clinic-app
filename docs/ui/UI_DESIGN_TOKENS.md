# UI_DESIGN_TOKENS

병원예약관리 (도수치료예약, v1.3.5+) 의 **디자인 토큰 단일 원천**.

- 작성: 2026-05-05 (Phase A — 사용자 통합 디자인 지시문에 따른 토큰 정의)
- 적용: `app/static/css/app.css` `:root {}` 블록
- 참고: Dribbble — CompteExpress CRM Dashboard (재구성, 그대로 복사 ❌)

> 본 문서는 **단일 원천** — `app.css` 의 `:root {}` 토큰값을 변경하려면 *반드시 본 문서도 같이 갱신*.

---

## 1. 적용 원칙

- **기존 토큰명 보존** — `app.css` 233곳에서 `var(--*)` 사용 중. 토큰명 변경 시 회귀 폭증.
- **값만 갱신** — 사용자 명시 13 색상 + 신규 2종 = 15 토큰.
- **`_ai_helper.css` 의 `--ai-helper-*` 19종은 별도** — Phase E 에서 일관 처리.
- **CSS 변수 글로벌 스코프** — 한 곳 (`app.css`) 정의로 모든 사용처 자동 반영.

## 2. 색상 토큰 단일 원천

### 2.1 기본 / 배경

| 의미 | 토큰 | 값 | 용도 |
|---|---|---|---|
| 전체 배경 | `--bg-page` | `#F5F7FA` | `body` / 탭 컨테이너 외부 |
| 카드 배경 | `--bg-card` | `#FFFFFF` | 모든 카드 / 박스 / 표 셀 |
| 입력창 배경 | `--bg-input` | `#FFFFFF` | `input` / `select` / `textarea` |

### 2.2 상단 / 탭 / 네비게이션 (다크 톤)

| 의미 | 토큰 | 값 | 용도 |
|---|---|---|---|
| 메인 다크 네이비 | `--nav-bg` | `#1F2937` | `<nav class="tabs-nav">` 컨테이너, 상단 바 |
| 보조 다크 블루그레이 | `--tab-bg` | `#273449` | 비활성 탭 배경 |
| 탭 hover | `--tab-hover` | `#2D425A` | 마우스 hover 시 탭 |
| 탭 active | `--tab-active` | `#3B82F6` | 선택된 탭 (포인트 블루) |
| 탭 텍스트 | `--tab-text` | `#FFFFFF` | 탭 글자 |
| 탭 텍스트 (muted) | `--tab-text-muted` | `#E8EEF5` | 비활성 탭 글자 / 카드 헤더 (블루그레이) |

### 2.3 경계 / 분리

| 의미 | 토큰 | 값 | 용도 |
|---|---|---|---|
| 테두리 | `--border-color` | `#D9E2EC` | 카드 / 입력창 / 표 외곽선 |
| 분리선 | `--divider-color` | `#E6EDF3` | 표 행간 / 카드 내부 분리 |

### 2.4 텍스트

| 의미 | 토큰 | 값 | 용도 |
|---|---|---|---|
| 기본 텍스트 | `--text-main` | `#1F2937` | 본문 글 |
| 보조 텍스트 | `--text-sub` | `#6B7280` | 메타 / 설명 |
| 흐림 텍스트 | `--text-muted` | `#6B7280` | placeholder / 약한 라벨 |
| 제목 | `--text-title` | `#1F2937` | 카드 제목 / 섹션 헤더 |

### 2.5 포인트 / 액션

| 의미 | 토큰 | 값 | 용도 |
|---|---|---|---|
| 포인트 블루 | `--primary` | `#3B82F6` | 저장 / 등록 / 확인 / active 탭 (Tailwind blue-500) |
| 포인트 hover | `--primary-hover` | `#2563EB` | 위 hover 상태 (blue-600) |
| 보조 포인트 | `--secondary` | `#22B8CF` | 보조 액션 (cyan) |
| 부드러운 포인트 | `--accent-soft` | `#DBEAFE` | 선택된 행 배경 / 강조 영역 (blue-100, **신규**) |

### 2.6 상태

| 의미 | 토큰 | 값 | 용도 |
|---|---|---|---|
| 성공/완료 | `--success` | `#10B981` | 완료 / 승인 / OK (emerald-500) |
| 경고 | `--warning` | `#F59E0B` | 주의 / 미확정 (amber-500) |
| 위험/취소 | `--danger` | `#EF4444` | 삭제 / 취소 / 오류 (red-500) |
| 정보 | `--info` | `#4A90E2` | 안내 / 진단 |

### 2.7 비활성 / 휴무

| 의미 | 토큰 | 값 | 용도 |
|---|---|---|---|
| 휴무/비활성 배경 | `--disabled-bg` | `#E5E7EB` | 휴무 슬롯 / 비활성 행 (gray-200, **신규**) |

## 3. 사용 규칙

### 3.1 새 코드에서

- 색상값을 *직접* 작성하지 않고 `var(--*)` 사용
- 예: `color: #3B82F6;` ❌ → `color: var(--primary);` ✅

### 3.2 기존 hardcoded 색상

- Phase A 에서는 *건드리지 않음* — 토큰 값 갱신만으로 자동 반영되는 범위가 우선
- Phase B / C / D / E / F 에서 단계적으로 hardcoded → token 전환

### 3.3 `_ai_helper.css` 의 `--ai-helper-*`

- 별도 그린 톤 시스템 — AI 도우미 카드 *고유 디자인*
- Phase E (AI 도우미 카드 가독성 정리) 에서 본 토큰과 일관 매핑 검토

## 4. 변경 이력

| 일자 | Phase | 변경 |
|---|---|---|
| 2026-05-05 | Phase A | 사용자 명시 13색 적용 + 신규 2종 (`--accent-soft`, `--disabled-bg`) |
| 2026-05-05 | Phase B | 탭/네비 다크 톤 정리 — `.tabs-nav` / `.tab-btn` / `.topbar-info` 추가 정의 |
| 2026-05-05 | Phase C | 표/카드 일관 — 사이드바 카드 헤더 톤 + 표 헤더 #E8EEF5 + hover --accent-soft |
| 2026-05-05 | Phase D | 버튼/입력/체크박스 통일 — 높이 36px / radius 8px / 포커스 ring 일관 |
| 2026-05-05 | Phase E | `_ai_helper.css` 토큰 → `app.css` 단일 원천 alias (그린 → 블루 톤) |
| 2026-05-05 | Phase F | 통계 카드 / 위험 영역 / 섹션 제목 / 노쇼 배지 / 색상 팔레트 정합 |
| 2026-05-05 | Phase G | 글로벌 폰트 시스템 — Pretendard fallback + typography scale (--fs-xs~3xl, --fw-*, --lh-*) |
| 2026-05-05 | Phase H | 헤더/탭/메인 영역 모던화 — topbar 카드, tabs-nav 카드형 띄움, 메인 max-width 1480px, 버튼 그림자/lift/icon-btn/ghost-btn |
| 2026-05-05 | Phase I | 그림자 시스템 (--shadow-xs~xl) + 라운드 (--radius-xs~2xl) + 스페이싱 토큰 (--space-1~10) |
| 2026-05-05 | Phase J | 사이드바 그리드 / 메인 캘린더 카드화 / 환자 검색 패널 + 모바일 1열 대응 |
| 2026-05-05 | Phase K | **가독성 보강** — `--text-sub` #6B7280→#4B5563 + status text 토큰 4종 신규 (`--success-text` #047857 / `--warning-text` #B45309 / `--danger-text` #B91C1C / `--info-text` #1D4ED8). AI 카드 badge/msg/tag, 노쇼 배지, 위험 영역 텍스트 모두 진한 토큰 사용 |
| 2026-05-05 | Phase L | **전수 가독성 (사용자 지적 반영)** — Phase K 후 *토큰만 갱신* 한계 보완. main.html 인라인 33곳 + app.css hardcoded 23곳 모두 #4B5563 또는 var(--text-sub) 로 교체. `.muted`/`<small>` 후속 정의로 진하게. 모든 탭 (예약/환자/직원/문자/AI/관리자/휴무/통계) 보조 텍스트 일괄 보강. UI_REVIEW_CHECKLIST.md 신규 작성 |
| 2026-05-05 | Phase M | **헤더 흰글씨/!important 충돌 fix (사용자 재지적 반영)** — 환자관리/직원관리/개별문자/일괄안내 헤더 글씨 안 보임 원인 분석. Phase C 가 .sheet-head background 만 밝게 변경했으나 line 3307 의 `color: var(--subhead-text) !important` 흰글씨 강제 → 밝은 배경 + 흰 글씨 contrast 1:1 충돌. `.sheet-head h2/.muted/small`, `.today-header h3/today-date`, `.mini-cal-wrap > h3`, `.legend-box > h3`, `.settings-card-head h3/small` 모두 var(--text-title) !important 로 통일. .today-list.today-canceled 는 연한 코랄 #FCE7E7 |

## 5. 참조

- 사용자 통합 지시문 (2026-05-05) — 색상 13종 명시
- Dribbble: https://dribbble.com/shots/27338618-CompteExpress- (참고용 — 재구성)
- `app/static/css/app.css` — `:root {}` 블록 단일 원천
- `docs/agent/01_COMMAND_BRAINSTORMING_AGENT.md` — Phase 단계 분해 회의 결과
- `docs/agent/08_UI_QA_AGENT.md` — UI 검증 책임
- 기존 `docs/ai/AI_DESIGN_TOKENS.md` — AI 카드 한정 토큰 (Phase E 에서 본 문서와 일관 정리 예정)
