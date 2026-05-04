# 20-3-1 Codex 검증 결과

## 1. 검증 대상

- 요청서: `reports/refactor/latest_codex_review_request.md`
- 세션 요청서: `reports/refactor/20-3-1_codex_review_request.md`
- 세션명: `20-3-1_no_show`
- 검증 일시: 2026-05-04

## 2. 결론

**통과.**

Claude Code 요약만 보지 않고 실제 변경 파일, diff, 테스트 결과, 보고서를 직접 비교했다. 20-P-2 §3-7 권장값에 맞춰 F-10 노쇼 기능이 백엔드 범위로 구현되어 있으며, 기존 status enum, cancel URL, 기존 extendedProps key, 기존 stats summary key 를 보존한 상태에서 `no_show` / `no_show_count` 만 추가됐다.

다음 세션 `20-3-2 F-11 권한 다중 등급` 으로 진행 가능하다.

## 3. 실제 변경 파일 확인

### 신규 파일

- `app/migrations/m014_appointment_no_show.py`
- `tests/test_20_3_1_no_show.py`
- `reports/refactor/20-3-1_fix_summary.md`
- `reports/refactor/20-3-1_test_report.md`
- `reports/refactor/20-3-1_codex_review_request.md`

### 수정 파일

- `app/models/models.py`
- `app/models/schemas.py`
- `app/modules/appointments/schemas.py`
- `app/modules/stats/aggregators.py`
- `app/modules/stats/schemas.py`
- `app/modules/stats/service.py`
- `app/routers/api.py`
- `tests/test_19_11_stats.py`
- `reports/refactor/latest_fix_summary.md`
- `reports/refactor/latest_test_report.md`
- `reports/refactor/latest_codex_review_request.md`

`git diff --stat` 의 tracked 범위에서는 신규 untracked 파일이 제외되므로, 실제 파일 목록은 `git status` 와 `Get-ChildItem` 으로 별도 확인했다.

## 4. 구현 검증

- `Appointment.no_show` 컬럼이 `Boolean(nullable=False, default=False)` 로 추가됨.
- m014 마이그레이션은 `appointments` 테이블 존재 여부와 `no_show` 컬럼 존재 여부를 확인한 뒤 `ALTER TABLE appointments ADD COLUMN no_show INTEGER DEFAULT 0 NOT NULL` 을 수행하므로 idempotent 하다.
- `_serialize_appointment()` 의 `extendedProps` 에 `no_show` 가 추가됨.
- `CancelAction.no_show` 기본값은 `False` 로 기존 cancel 호출 호환성을 유지함.
- `/api/appointments/{aid}/cancel` 은 `no_show=True` 요청 시 `obj.no_show=True` 를 함께 반영하고, 기존 승인 예약 취소 차단 로직은 유지됨.
- `/api/appointments/{aid}/mark-no-show` 가 추가되어 `no_show=True` 와 `status="canceled"` 를 동시에 적용함.
- `aggregate_summary()`, `build_summary_response()`, legacy `stats_summary()` 모두 `no_show_count` 를 응답에 포함함.
- `APPOINTMENT_EXTENDED_PROPS_KEYS` 는 기존 16개 + `no_show` 로 갱신됨.
- `SUMMARY_RESPONSE_KEYS` 는 기존 12개 + `no_show_count` 로 갱신됨.

## 5. 테스트 재실행 결과

직접 재실행한 결과:

```text
ruff check app tests scripts
All checks passed!
```

```text
pytest tests/test_20_3_1_no_show.py tests/test_19_11_stats.py tests/test_pyinstaller_hidden_imports.py tests/test_migration_spec_discovery.py -q
314 passed, 1 warning in 0.95s
```

```text
pytest tests -q
1735 passed, 1 skipped, 10 xfailed, 27 warnings in 13.65s
```

```text
scripts/check_db_path.py
exit 0
```

전체 테스트 결과는 `reports/refactor/20-3-1_test_report.md` 의 reported result 와 일치한다. 경고는 기존 테스트 함수 return warning 및 pytest cache 경로 warning 이며, 이번 no-show 구현 실패는 아니다.

## 6. 확인한 로그/보고서 정합성

- `latest_fix_summary.md` 와 `20-3-1_fix_summary.md` 는 동일했다.
- `latest_test_report.md` 와 `20-3-1_test_report.md` 는 동일했다.
- `latest_codex_review_request.md` 와 `20-3-1_codex_review_request.md` 는 동일했다.
- test report 의 `1735 passed / 1 skipped / 10 xfailed` 는 직접 재실행 결과와 일치했다.

## 7. Caveat

- PyInstaller 실제 exe build 는 실행하지 않았다. 대신 hidden import/spec discovery 테스트 215개가 통과해 m014 발견과 import 가능성은 확인했다.
- UI 체크박스, 캘린더 노쇼 표시, 노쇼 알림 트리거는 이번 v1 범위 밖이다.
- `git status` 의 `C:\Users\user/.config/git/ignore` permission warning 은 기존 환경 경고로 보이며 검증 판정에는 영향이 없다.
- `reports/refactor/20-3-1_fix_summary.md` 내부의 "수정 (6개)" 표기는 실제 표 항목 수와 맞지 않는 문서상 사소한 불일치가 있다. 구현/테스트 판정에는 영향이 없지만 후속 정리 시 고치면 좋다.

## 8. 최종 판정

**20-3-1 검증 통과.**

백엔드 F-10 노쇼 구현은 요청서 범위와 테스트 결과에 부합한다. 다음 단계는 `20-3-2 F-11 권한 다중 등급` 이다.
