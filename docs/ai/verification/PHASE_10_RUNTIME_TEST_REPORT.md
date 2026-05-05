# PHASE_10_RUNTIME_TEST_REPORT.md

## Phase / 시각

- Phase 10 — summarize_today / summarize_tomorrow / analyze_stats
- 시각: 2026-05-05

## 명령

```bash
venv/Scripts/python.exe -m pytest tests/test_phase10_ai_summary.py -v   # 19/19
venv/Scripts/python.exe -m pytest tests -q                                # 2094 passed
venv/Scripts/python.exe -m ruff check app tests                           # 0 error
```

## 테스트 (19 케이스)

- 일일 요약 7 (total / by_therapist / by_hour / by_treatment / empty / today / tomorrow)
- 기간 통계 5 (total / by_day / therapist filter / treatment filter / invalid range)
- 한국어 텍스트 2 (요약 / 분석 — 가장 바쁜 시간 포함)
- preview 2 (read_only=True 명시)
- 안전 2 (DB 직접 수정 0 / 결정적 응답)
- manual60=1 정책 1 (단순 row count 검증)

## 결과

✅ 19/19 통과 / 2094 회귀 0 fail / Ruff 0

## 최종 판단

**정상 작동** ✅

- 모든 수치 = DB 쿼리 결과 (AI 임의 생성 ⊥)
- 결정적 한국어 응답 (외부 LLM 미사용)
- canceled 제외 / manual60=1 정책 유지
