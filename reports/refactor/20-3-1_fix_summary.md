# 20-3-1 F-10 변경 요약

## 변경 파일 목록

### 신규 (2개)

| 파일 | 줄 수 | 내용 |
|---|---:|---|
| `app/migrations/m014_appointment_no_show.py` | 47 | Appointment.no_show BOOLEAN DEFAULT 0 (idempotent ALTER TABLE) |
| `tests/test_20_3_1_no_show.py` | 247 | 9 cases (m014 / 모델 / serialize / cancel / mark-no-show / stats) |

### 수정 (6개)

| 파일 | diff | 의도 |
|---|---:|---|
| `app/models/models.py` | +2 | Appointment.no_show 컬럼 추가 |
| `app/models/schemas.py` | +2 | CancelAction.no_show: bool = False |
| `app/routers/api.py` | ~30 | _serialize_appointment + cancel + mark-no-show + stats_summary |
| `app/modules/appointments/schemas.py` | +3 | APPOINTMENT_EXTENDED_PROPS_KEYS 에 no_show |
| `app/modules/stats/aggregators.py` | +9 | aggregate_summary 에 no_show_count |
| `app/modules/stats/schemas.py` | +2 | SUMMARY_RESPONSE_KEYS 에 no_show_count |
| `app/modules/stats/service.py` | +2 | build_summary_response 에 no_show_count |
| `tests/test_19_9_appointments.py` | (간접 — schemas 갱신으로 통과) | — |
| `tests/test_19_11_stats.py` | +5 | aggregate_summary_basic + summary_keys_contract 갱신 |

## 호환성

- 20-2 baseline 1726 → 20-3-1 baseline **1735** (+9 신설, 회귀 0)
- 기존 `Appointment.status` ENUM 보존 (`reserved` / `approved` / `canceled`)
- 기존 33+ 응답 key + 16 extendedProps 키 보존 (no_show 만 추가 — 17키)
- 기존 `/api/appointments/{aid}/cancel` URL / 기존 동작 보존 (no_show 옵션은 default False)
- 기존 stats summary 12키 보존 (no_show_count 만 추가 — 13키)
- m001~m013 변경 0, m014 신설만

## 정책 정합 (사용자 §3-7 권장값)

- (a) boolean 컬럼: `Appointment.no_show: bool DEFAULT False`
- (i) cancel 동시: `mark-no-show` 시 `no_show=True` + `status="canceled"` 동시 적용
- (ii) 통계 별도: `no_show_count` 별도 항목 (cancel 의 부분집합)

## 5회 루프

1회차: 코드 작성 + ruff (3 autofix) + 9 cases passed
2회차: 19-9 contract fail (2건) → APPOINTMENT_EXTENDED_PROPS_KEYS 갱신 → 81 passed
3회차: 19-11 contract fail (2건) → aggregate_summary_basic + summary_keys_contract 갱신 → 1735 passed

5회 루프 안에 통과.
