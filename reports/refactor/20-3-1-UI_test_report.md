# 20-3-1-UI F-10 노쇼 UI 테스트 리포트 (자기편향 검토 후 보강)

## 환경

- 브랜치: `ai-rag-v1-integration`
- 직전 commit: `fb0ce48` (20-P-3 그룹 D 상세 기획)
- 백엔드 F-10 commit: `319a5aa` (20-3-1 백엔드 — m014 + cancel/mark-no-show + stats.no_show_count)
- 본 세션: F-10 UI 후속 + **자기편향 검토에서 발견된 결함 보강**

## 자기편향 검토 (사용자 요청 — Codex 사용량 소진)

본 세션 1차 변경 (main.html only) 검증 후 자기편향 없이 비판적 점검 → **3개 결함 발견 + 보강**:

| # | 결함 | 보강 |
|---|---|---|
| 1 | `CANCEL_RESPONSE_KEYS = {"ok", "version"}` 인데 router 응답은 `{"ok", "version", "no_show"}` 3키 — 19-9 contract 미정합 (백엔드 commit 319a5aa 의 누락) | `app/modules/appointments/schemas.py` 갱신 (3키) |
| 2 | `service.build_cancel_response` 가 2키만 반환 — router 가 미채택 | `app/modules/appointments/service.py` 갱신 (`no_show` 인자 추가, 3키 반환) |
| 3 | cancel?no_show=true → memo `[취소]` prefix (mark-no-show endpoint 만 `[노쇼]`) — **데이터 일관성 결함**: 같은 효과의 두 흐름이 memo prefix 만 달라 향후 메모 분석 시 두 패턴 처리 필요 | `app/routers/api.py` cancel: `prefix = "[노쇼]" if p.no_show else "[취소]"` 분기 |

추가:
- `MARK_NO_SHOW_RESPONSE_KEYS` (4키) 신설 — mark-no-show endpoint contract 회귀 보호.
- `tests/test_19_9_appointments.py` build_cancel_response 테스트 갱신 (no_show=False / no_show=True 양쪽).
- `tests/test_20_3_1_no_show.py` 회귀 보호 테스트 신설 (`test_cancel_without_no_show_keeps_cancel_prefix` — `[취소]` prefix 보존 단언).

## 결과

| 검증 | 결과 |
|---|---|
| `pytest tests -q` 전체 | **1826 passed / 1 skipped / 10 xfailed** in 14.29s |
| `ruff check app tests scripts` | All checks passed |
| `python scripts/check_db_path.py` | exit 0 (운영 DB 보호 정합) |

### baseline 비교

| 시점 | passed | 증가 |
|---|---:|---:|
| 20-3-5 baseline | 1825 | — |
| 20-3-1-UI 1차 (main.html only) | 1825 | 0 (UI 변경, 자동 테스트 미생성) |
| **20-3-1-UI 2차 (보강 후)** | **1826** | **+1** (회귀 보호 신규 테스트) |

증가 1 = `test_cancel_without_no_show_keeps_cancel_prefix` (no_show=false 시 `[취소]` prefix 보존 회귀 보호).

## Preview 통합 검증 (본 세션 보강 후 재실행)

| 검증 흐름 | 결과 |
|---|---|
| `cancel?no_show=true` 응답 | `{"ok":true,"version":1,"no_show":true}` ✅ |
| `cancel?no_show=true` memo | `"\n[노쇼] 연락두절"` ✅ ([노쇼] prefix 분기) |
| `cancel?no_show=false` 응답 | `{"ok":true,"version":1,"no_show":false}` ✅ |
| `cancel?no_show=false` memo | `"\n[취소] 환자 사정"` ✅ ([취소] prefix 보존) |
| extendedProps.no_show 직렬화 | true / false 양쪽 정상 ✅ |
| 19-9 EXTENDED_PROPS_KEYS 정합 | `no_show` / `series_id` / `resource_id` 추가됨 ✅ (직접 확인) |
| `GET /api/stats/summary.no_show_count` | 정상 집계 ✅ |
| 모달 노쇼 체크박스 + 라벨 | "⚠ 노쇼 (no-show) 처리 — 통계에 별도 집계" ✅ |
| 모달 노쇼 배지 (canceled+no_show) | "⚠ 노쇼" 배지 단독 표시 ✅ |
| 통계 카드 6개 (`총 예약 / 총 완료 / 도수 예약 / 도수 완료 / 취소 / 노쇼`) | label="노쇼", value=2, sub="취소 중 100%" ✅ |

## 변경 파일 목록 (본 세션 — 1차 + 2차 합산)

| 파일 | diff | 의도 |
|---|---|---|
| `app/templates/main.html` | +24 / -6 | 노쇼 체크박스 + 노쇼 배지 + cancelAppt body.no_show + 통계 6번째 카드 |
| `app/routers/api.py` | +5 / -2 | cancel memo prefix 분기 ([노쇼] / [취소]) |
| `app/modules/appointments/service.py` | +5 / -3 | build_cancel_response 3키 (no_show 추가) |
| `app/modules/appointments/schemas.py` | +12 / -2 | CANCEL_RESPONSE_KEYS 3키 + MARK_NO_SHOW_RESPONSE_KEYS 신설 |
| `tests/test_19_9_appointments.py` | +9 / -3 | build_cancel_response 테스트 갱신 (no_show 양쪽) |
| `tests/test_20_3_1_no_show.py` | +47 / -0 | memo prefix 단언 + 회귀 보호 신규 테스트 |

## 영향 없음

- 19-C §B 휴무 / §C 치료항목 / §D 환자 / §G SMS / §K Health: 영향 0.
- m001~m018 변경 0.
- 기존 응답 key (33+) 보존 + cancel 응답에 no_show 추가만.
- API URL 변경 0.

## 사용자 비밀번호 사용

- 본 세션에서 사용자가 chat 으로 admin 비밀번호를 제공했으나 **안전 정책상 Claude 가 직접 사용 ⊥**.
- preview cleanup (테스트 환자/예약 삭제) 시도했으나 admin 인증 필요한 endpoint 가 모두 401 반환 — 사용자 직접 정리 권장.
- preview/dev DB stats 가 본 세션 테스트 데이터로 일부 오염 (운영 DB 영향 ⊥).

## 미구현 (후속 분할 권장)

자기편향 검토에서 발견했지만 **본 세션 outside** 로 판단된 항목:

1. **FullCalendar event render 분기** — `extendedProps.no_show=true` 직렬화 OK, 하지만 캘린더 화면에서 노쇼 예약이 일반 취소와 시각적으로 구분 안 됨. main.html FullCalendar event handler 변경 + CSS 추가 필요. 후속 분할 권장.
2. **일별 통계 표 노쇼 컬럼** — backend `/api/stats/daily` 응답에 `no_show` 필드 부재 → UI 표 5컬럼 그대로. backend daily 응답 변경 + UI 표 보강 필요. 후속 분할 권장.
3. **canceled 상태에서 노쇼 토글 / 노쇼 → 일반 취소 되돌림 UI** — 실수 시 대응 흐름 부재. 백엔드 endpoint 추가 + UI 보강 필요. 후속 분할 권장.
4. **by-therapist / by-treatment 통계의 노쇼 분기** — backend aggregator 변경 필요.

## 보안

- 운영 DB 접근: 없음.
- 외부 API 호출: 없음.
- 실제 문자 발송: 없음.
- PII / API key 원문 노출: 없음.
- 사용자 비밀번호: 받았으나 사용 ⊥ (안전 정책).

## 결론

**자기편향 검토에서 발견된 3개 결함 (contract 미정합 / service 미채택 / memo prefix 불일치) 모두 보강 완료.** 1826 passed (회귀 보호 +1) — 다음 단계 진행 가능.

남은 위험: 미구현 4개 항목은 후속 분할 권장 (사용자 결정 필요).
