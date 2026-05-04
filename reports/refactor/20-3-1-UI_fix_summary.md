# 20-3-1-UI F-10 노쇼 UI 변경 요약 (자기편향 검토 후 보강 포함)

## 변경 파일 목록 (1차 main.html + 2차 자기편향 보강)

### 신규 (0개)

(본 세션은 신규 파일 없음)

### 수정 (6개)

| 파일 | diff | 의도 |
|---|---:|---|
| `app/templates/main.html` | +24 / -6 (4 hunks) | 노쇼 체크박스 + 노쇼 배지 + cancelAppt body.no_show + 통계 6번째 카드 |
| `app/routers/api.py` | +5 / -2 | cancel endpoint memo prefix 분기 ([노쇼] / [취소]) — mark-no-show 와 데이터 일관성 |
| `app/modules/appointments/service.py` | +5 / -3 | build_cancel_response 3키 (`{ok, version, no_show}`) — router 정합 |
| `app/modules/appointments/schemas.py` | +12 / -2 | CANCEL_RESPONSE_KEYS 3키 + MARK_NO_SHOW_RESPONSE_KEYS 신설 |
| `tests/test_19_9_appointments.py` | +9 / -3 | build_cancel_response 테스트 갱신 — no_show=False / True 양쪽 |
| `tests/test_20_3_1_no_show.py` | +47 / -0 | memo prefix [노쇼] 단언 + 회귀 보호 신규 테스트 (`test_cancel_without_no_show_keeps_cancel_prefix`) |

## 1차 main.html 4 hunks

### hunk 1 — 예약 모달 badge 분기 (line 2831~2841)

`status === 'canceled' && ep.no_show` 인 경우 "⚠ 노쇼" 배지로 대체.

### hunk 2 — cancelBlock 노쇼 체크박스 (line 2920~2932)

`status === 'reserved'` 일 때 취소 사유 input 아래에 노쇼 체크박스 + 라벨 추가.

### hunk 3 — cancelAppt body.no_show 전송 (line 3148~3157)

체크박스 상태 → body 에 `no_show: bool` 동반 전송.

### hunk 4 — 통계 카드 6번째 "노쇼" (line 5310~5326)

`summary.no_show_count` 사용. 색상 #B45309 (amber-700). sub: "취소 중 X%".

## 2차 자기편향 보강

### 보강 1 — `app/routers/api.py` cancel memo prefix 분기

**기존 결함**: cancel?no_show=true → memo `[취소]` prefix (mark-no-show endpoint 만 `[노쇼]`). **데이터 일관성 결함**: 같은 효과의 두 흐름이 memo prefix 만 달라 향후 메모 분석 시 두 패턴 처리 필요.

```python
prefix = "[노쇼]" if p.no_show else "[취소]"
obj.memo = (obj.memo or "") + (f"\n{prefix} {p.memo}" if p.memo else f"\n{prefix}")
```

이제 cancel?no_show=true 와 mark-no-show endpoint 의 결과가 (status / no_show / memo prefix) 모두 동일.

### 보강 2 — `app/modules/appointments/service.py` build_cancel_response 3키

**기존 결함**: service helper 가 2키 (`{ok, version}`) 만 반환, router 는 3키 (`{ok, version, no_show}`) 반환 → service 가 router 미채택. 19-9 contract test 가 service 만 검사해서 router 응답 회귀 검출 불능.

```python
def build_cancel_response(*, version: int | None, no_show: bool = False) -> dict:
    return {"ok": True, "version": int(version or 0), "no_show": bool(no_show)}
```

### 보강 3 — `app/modules/appointments/schemas.py` CANCEL_RESPONSE_KEYS 3키 + MARK_NO_SHOW_RESPONSE_KEYS 신설

**기존 결함**: CANCEL_RESPONSE_KEYS = `{ok, version}` 2키 — router 응답과 미정합. mark-no-show endpoint 의 contract 부재 (4키 응답 회귀 보호 ⊥).

```python
CANCEL_RESPONSE_KEYS = frozenset({"ok", "version", "no_show"})
MARK_NO_SHOW_RESPONSE_KEYS = frozenset({"ok", "no_show", "status", "version"})
```

### 보강 4 — `tests/test_19_9_appointments.py` build_cancel_response 테스트 갱신

```python
out = _service.build_cancel_response(version=4, no_show=False)
assert out == {"ok": True, "version": 4, "no_show": False}
out2 = _service.build_cancel_response(version=5, no_show=True)
assert out2 == {"ok": True, "version": 5, "no_show": True}
```

### 보강 5 — `tests/test_20_3_1_no_show.py` memo prefix 단언 + 회귀 보호

**갱신**: `test_cancel_with_no_show_true` 에 memo `[노쇼]` prefix 단언 추가.
**신규**: `test_cancel_without_no_show_keeps_cancel_prefix` — no_show=false 시 memo `[취소]` prefix 보존 (기존 흐름 회귀 보호).

## 호환성

- 20-3-5 baseline 1825 → 20-3-1-UI 2차 baseline **1826** (+1 회귀 보호)
- 기존 `/api/appointments/{aid}/cancel` URL 보존
- **응답 dict 변경**: 2키 → 3키 (`no_show` 추가). 기존 UI 가 `no_show` 키를 무시해도 회귀 0 (frontend 가 응답에서 no_show 미사용 — refresh 후 GET /api/appointments 로 재조회).
- m001~m018 변경 0
- 기존 33+ 응답 key + 19 extendedProps 키 + 12 stats summary 키 보존 → cancel 3키 정합화 + mark-no-show 4키 contract 신설

## 데이터 일관성 정리

| 흐름 | status | no_show | memo prefix |
|---|---|---|---|
| cancel?no_show=false | canceled | false | `[취소]` |
| **cancel?no_show=true** (UI) | **canceled** | **true** | **`[노쇼]`** ← 보강으로 mark-no-show 와 동일 |
| mark-no-show endpoint | canceled | true | `[노쇼]` |

이제 두 흐름이 데이터 측면에서 완전 동일 (둘 중 하나만 사용해도 OK).

## 정책 정합 (사용자 §3-7 권장값)

- (a) boolean 컬럼: `Appointment.no_show` ✅ (백엔드 commit 319a5aa)
- (i) cancel 동시: ✅ (cancel?no_show=true → status="canceled" + no_show=true + [노쇼] prefix)
- (ii) 통계 별도: ✅ (no_show_count 카드 별도 — sub 라벨 "취소 중 X%")
