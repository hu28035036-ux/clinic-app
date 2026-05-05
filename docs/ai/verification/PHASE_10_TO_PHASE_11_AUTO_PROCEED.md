# PHASE_10_TO_PHASE_11_AUTO_PROCEED.md

- 이전: Phase 10 — summarize / analyze_stats
- 다음: **Phase 11 — 데이터 품질 검사 / 운영 도우미** (`data_quality_check` / `ops_assistant`)

## 자동 진행 조건 ✅

자체 10회 / 자만 없는 판단 / Runtime / 19 신규 + 2094 회귀 0 fail / Ruff 0 / 명시 구현 대상.

## 누적

| Phase | 신규 | 누계 | 회귀 |
|---|---|---|---|
| 9 | 14 | 233 | 2075 |
| 10 | 19 | **252** | **2094** |

## Phase 11 시작 전 체크리스트

- [ ] § Phase 11 / § 5.5 (data_quality_check / ops_assistant) 13 필드
- [ ] 자동 수정 ⊥ / 자동 예약 생성 ⊥ / 자동 휴무 등록 ⊥
- [ ] 외부 AI API 에 환자 목록 / 전체 일정 전송 ⊥
- [ ] 추천 / 분석 중심 — 수정은 별도 intent
