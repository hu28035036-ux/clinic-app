# 20-3-1 F-10 노쇼 테스트 리포트

## 환경

- 직전 commit: `62ca82d` (20-P-2 그룹 C 상세 기획)

## 결과

| 검증 | 결과 |
|---|---|
| ruff | All checks passed (3 autofix) |
| check_db_path | exit 0 |
| `pytest tests/test_20_3_1_no_show.py -v` | **9 passed** in 0.22s |
| `pytest tests/test_pyinstaller_hidden_imports.py + test_migration_spec_discovery.py` | **215 passed** (m014 자동 글롭 발견 + import 가능 확인) |
| `pytest tests -q` 전체 | **1735 passed / 1 skipped / 10 xfailed** in 13.77s |

### baseline 비교

| 시점 | passed | 증가 |
|---|---:|---:|
| 20-2 baseline | 1726 | — |
| 20-3-1 (본 세션) | **1735** | **+9** |

증가 9 = test_20_3_1_no_show.py 9 cases. 19-9 contract + 19-11 contract 갱신 (no_show / no_show_count 추가) — 기존 회귀는 갱신 후 통과.

## 자동 테스트 확인

- m014 마이그레이션 + Appointment.no_show 컬럼 + 기본값 False (2 cases)
- _serialize_appointment extendedProps 에 no_show 추가 (TestClient endpoint, 1 case)
- POST /api/appointments/{aid}/cancel 의 no_show 파라미터 (1 case)
- POST /api/appointments/{aid}/mark-no-show 신설 endpoint + 승인 차단 (2 cases)
- aggregate_summary 의 no_show_count + SUMMARY_RESPONSE_KEYS contract + GET /api/stats/summary endpoint (3 cases)

## TestClient 호출 확인

- GET /api/appointments → no_show=False 응답 단언
- POST /api/appointments/{aid}/cancel?no_show=true → DB 반영 확인
- POST /api/appointments/{aid}/mark-no-show → status="canceled" + no_show=True + [노쇼] 메모
- GET /api/stats/summary → no_show_count int 응답

## 수동 확인 필요 항목

- 운영 환경에서 노쇼 마킹 흐름이 UI 체크박스로 트리거 — 본 v1 백엔드만 (UI 별도 후속).
- 노쇼 통계가 캘린더 / 통계 화면에 표시되는지 — UI 후속.
- 노쇼 알림 트리거 — F-4 (그룹 D) 도입 시.

## 영향 없음

- 19-C §B 휴무 / §C 치료항목 / §D 환자 / §G SMS / §K Health: 영향 0.
- DB schema: m001~m013 변경 0, m014 신설만.

## 보안

- 운영 DB 접근: 없음
- 외부 API 호출: 없음
- 실제 문자 발송: 없음
- PII / API key 원문 노출: 없음 (응답 dict 에 boolean / 카운트만 추가)

## 결론

다음 단계 진행 가능: **yes**. 남은 위험: UI 체크박스 후속 분할 + 노쇼 알림 (F-4 도입 시).
