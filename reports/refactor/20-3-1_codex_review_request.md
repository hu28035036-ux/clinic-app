# 20-3-1 Codex 검증 요청서

## 1. 세션 이름

`20-3-1_no_show` — F-10 노쇼 별도 필드 도입 (m014 + Appointment.no_show + cancel·mark-no-show + stats no_show_count).

## 2. 작업 목표

20-P-2 §3 사용자 §3-7 권장값 정합:
- (a) `Appointment.no_show: bool DEFAULT False` 단일 컬럼.
- (i) cancel 동시 — `no_show=True` 시 `status="canceled"` 함께.
- (ii) 통계 별도 — `no_show_count` (cancel 의 부분집합).

본 v1 = 백엔드만. UI 체크박스는 후속 분할.

## 3. 변경 파일 목록

### 신규 (2개)
```
app/migrations/m014_appointment_no_show.py  (47줄)
tests/test_20_3_1_no_show.py                (247줄, 9 cases)
```

### 수정 (8개)
```
app/models/models.py                         (+2, no_show 컬럼)
app/models/schemas.py                        (+2, CancelAction.no_show)
app/routers/api.py                           (~30, _serialize/cancel/mark-no-show/stats_summary)
app/modules/appointments/schemas.py          (+3, EXTENDED_PROPS_KEYS)
app/modules/stats/aggregators.py             (+9, no_show_count)
app/modules/stats/schemas.py                 (+2, SUMMARY_RESPONSE_KEYS)
app/modules/stats/service.py                 (+2, build_summary_response)
tests/test_19_11_stats.py                    (+5, contract 갱신)
```

## 4. 수정 가능 / 금지 범위

- 가능: m014 신설, Appointment.no_show 컬럼, _serialize_appointment 응답, cancel/mark-no-show, stats summary, 19-9/19-11 contract.
- 금지: m001~m013 / Appointment.status ENUM / 기존 33+ 응답 key / 기존 cancel URL / 기존 stats 12키.

## 5. 실제 변경

- m014: ALTER TABLE appointments ADD COLUMN no_show INTEGER DEFAULT 0 NOT NULL (idempotent).
- Appointment.no_show: Boolean nullable=False default=False.
- _serialize_appointment.extendedProps: 16키 → 17키 (`no_show` 추가).
- CancelAction.no_show: bool = False (옵션). cancel 시 True 면 obj.no_show=True.
- POST /api/appointments/{aid}/mark-no-show 신설: no_show=True + status="canceled" + 메모 [노쇼] prefix.
- aggregate_summary: no_show_count (canceled 의 부분집합 카운트).
- build_summary_response + SUMMARY_RESPONSE_KEYS: no_show_count 추가 (12키 → 13키).
- 19-9 APPOINTMENT_EXTENDED_PROPS_KEYS frozenset + 19-11 contract 갱신.

## 6. 실행한 테스트 + 결과

```
ruff check app tests scripts                                    → All passed
scripts/check_db_path.py                                        → exit 0
pytest tests/test_20_3_1_no_show.py -v                          → 9 passed
pytest tests/test_pyinstaller_hidden_imports.py + spec_discovery → 215 passed
pytest tests -q                                                 → 1735 passed / 1 skipped / 10 xfailed
```

20-2 baseline 1726 → 20-3-1 **1735** (+9 신설, 회귀 0).

## 7. 수정 루프

1회차 코드 + ruff + 9 cases → 2회차 19-9 contract fail → APPOINTMENT_EXTENDED_PROPS_KEYS +no_show → 3회차 19-11 contract fail → aggregate_summary_basic + summary_keys_contract 갱신 → 1735 passed.

총 3회 루프 안에 통과.

## 8. 작동확인 (19-C §A 예약 + §H 통계 + §M 보안)

- §A 예약: 생성 / cancel / mark-no-show TestClient 호출 + DB 반영 확인.
- §H 통계: aggregate_summary unit + GET /api/stats/summary endpoint + no_show_count int 단언.
- §M 보안: 운영 DB / 외부 API / 문자 발송 / PII·API key 원문 모두 부재.

## 9. 수동 확인 필요

- UI 체크박스 (예약 카드 모달) — 후속 분할.
- 노쇼 통계 / 캘린더 표시 — 후속 (UI 갱신).
- 알림 트리거 — F-4 도입 시.

## 10. 영향 없음

- 19-C §B 휴무 / §C 치료항목 / §D 환자 / §G SMS / §K Health: 영향 0.
- DB schema m001~m013: 변경 0.
- main.html JS: 변경 0 (백엔드만).

## 11. 보안

- 운영 DB 접근: 없음
- 외부 API 호출: 없음
- 실제 문자 발송: 없음
- PII / API key 원문 노출: 없음

## 12. 응답 key 유지

- 17 extendedProps (16 + no_show) — 기존 16 보존.
- 13 SUMMARY (12 + no_show_count) — 기존 12 보존.
- 기존 cancel 응답에 no_show key 추가만 (기존 ok / version 보존).

## 13. 다음 세션 진행

**yes** Codex 통과 시. 다음 = 20-3-2 F-11 권한 다중 등급 (사용자 §4-6 결정 후).

## 14. Codex 검증 결과 위치

- [reports/refactor/20-3-1_codex_review.md](20-3-1_codex_review.md)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md)

## 15. 사용자 → Codex 전달 문구

> "reports/refactor/latest_codex_review_request.md 20-3-1 F-10 노쇼 검증 시작해줘. Claude Code 요약만 믿지 말고 m014 마이그레이션 / Appointment.no_show 컬럼 / _serialize_appointment / cancel·mark-no-show endpoint / stats no_show_count / 19-9·19-11 contract 갱신을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md 와 reports/refactor/20-3-1_codex_review.md 에 남겨줘."
