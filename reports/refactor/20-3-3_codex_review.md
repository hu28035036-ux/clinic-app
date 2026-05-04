# 20-3-3 Codex 검증 결과

## 1. 검증 대상

- 요청서: `reports/refactor/latest_codex_review_request.md`
- 세션 요청서: `reports/refactor/20-3-3_codex_review_request.md`
- 세션명: `20-3-3_doctors_light`
- 검증 일시: 2026-05-04

## 2. 결론

**통과.**

Claude Code 요약만 보지 않고 실제 변경 파일, diff, 테스트 결과, 로그를 직접 비교했다. 20-P-2 §5-7의 (c) “가벼운 의사만” 결정에 맞춰 `Doctor` 단일 테이블과 `/api/doctors` CRUD만 추가됐고, Department / Room / DoctorSchedule / Patient.doctor_id 는 추가되지 않았다. 기존 `Employee.role="doctor"` 및 `Treatment.role="doctor"` 분기는 보존됐다.

다음 세션은 `20-3-4 F-2 반복 예약` 이며, 진입 전 사용자 §6-6 반복 패턴/시리즈 처리/충돌 정책 결정이 필요하다.

## 3. 실제 변경 파일 확인

### 신규 파일

- `app/migrations/m016_doctors_table.py`
- `app/modules/doctors/__init__.py`
- `app/modules/doctors/schemas.py`
- `app/modules/doctors/service.py`
- `app/modules/doctors/router.py`
- `tests/test_20_3_3_doctors.py`
- `reports/refactor/20-3-3_fix_summary.md`
- `reports/refactor/20-3-3_test_report.md`
- `reports/refactor/20-3-3_codex_review_request.md`

### 수정 파일

- `app/main.py`
- `app/models/models.py`
- `dosu_clinic.spec`
- `tests/test_19_8_therapists.py`
- `tests/test_pyinstaller_hidden_imports.py`
- `reports/refactor/latest_fix_summary.md`
- `reports/refactor/latest_test_report.md`
- `reports/refactor/latest_codex_review_request.md`

`git diff --stat` 의 tracked 범위에서는 신규 untracked 파일이 제외되므로, 실제 파일 목록은 `git status`, `Get-ChildItem`, 신규 파일 직접 읽기로 별도 확인했다.

## 4. 구현 검증

- `Doctor` ORM 모델이 추가됐고 컬럼은 `id`, `name`, `specialty`, `license_no`, `color`, `active`, `sort_order`, `created_at`, `updated_at` 이다.
- m016 마이그레이션은 `doctors` 테이블 존재 시 `ix_doctors_active_sort`, `uq_doctors_license_no` 인덱스를 `IF NOT EXISTS` 로 보강하므로 idempotent 하다. 테이블 생성 자체는 기존 `Base.metadata.create_all()` 흐름이 담당한다.
- `app/modules/doctors` 에 router/service/schemas가 추가됐고 `DOCTOR_RESPONSE_KEYS` 는 8개 응답 key를 정의한다.
- `GET /api/doctors` 는 public 목록 조회이며, `POST/PUT/DELETE /api/doctors` 는 `require_admin` 을 사용한다.
- audit detail 은 name만 기록하고 `license_no` / `specialty` 는 audit detail 에 포함하지 않는다.
- `app/main.py` 에 doctors router가 include 됐다.
- `dosu_clinic.spec` 와 `tests/test_pyinstaller_hidden_imports.py` 에 doctors 모듈 4개가 hidden import 대상으로 추가됐다.
- 19-8의 “doctors 부재” 단언은 20-3-3 이후 상태에 맞게 “doctors 존재, medical_staff 부재”로 갱신됐다.

## 5. 테스트/로그 재실행 결과

직접 재실행한 결과:

```text
ruff check app tests scripts
All checks passed!
```

```text
pytest tests/test_20_3_3_doctors.py tests/test_19_8_therapists.py tests/test_pyinstaller_hidden_imports.py tests/test_migration_spec_discovery.py -q
318 passed, 1 warning in 0.92s
```

```text
pytest tests -q
1773 passed, 1 skipped, 10 xfailed, 27 warnings in 13.12s
```

```text
scripts/check_db_path.py
exit 0
```

추가로 테스트 격리 DB에서 실제 CRUD 성공 경로를 직접 확인했다.

```text
POST /api/admin/login -> 200
GET /api/doctors -> 200 []
POST /api/doctors -> 200
PUT /api/doctors/{id} -> 200
DELETE /api/doctors/{id} -> 200 {"ok": true}
```

격리 DB 시작 로그에서 m001~m016 마이그레이션 적용도 확인했다.

전체 테스트 결과는 `reports/refactor/20-3-3_test_report.md` 의 reported result 와 일치한다. 경고는 기존 테스트 함수 return warning 및 pytest cache 경로 warning 이며, 이번 doctors 구현 실패는 아니다.

## 6. 보고서 정합성

- `latest_fix_summary.md` 와 `20-3-3_fix_summary.md` 는 동일했다.
- `latest_test_report.md` 와 `20-3-3_test_report.md` 는 동일했다.
- `latest_codex_review_request.md` 와 `20-3-3_codex_review_request.md` 는 동일했다.
- test report 의 `1773 passed / 1 skipped / 10 xfailed` 는 직접 재실행 결과와 일치했다.

## 7. Caveat

- PyInstaller 실제 exe build 는 실행하지 않았다. 대신 hidden import 테스트 219개가 통과해 doctors 모듈 import 가능성과 spec 등록은 확인했다.
- UI 의사 등록 화면, 캘린더/환자 카드 표시, F-15 DB 근거 기반 의사 가드 강화는 이번 v1 범위 밖이다.
- `license_no` 는 응답 dict 에 평문 포함된다. 요청서에도 응답 노출이 명시되어 있으나, 실제 운영 UI에서 노출 범위는 후속 정책으로 정리하는 편이 좋다.
- m016은 `Base.metadata.create_all()` 이후 인덱스 보강을 수행하는 구조다. 현재 `init_db()` 순서상 정상이나, 마이그레이션만 독립 실행해 테이블이 없으면 skip 한다.
- `git status` 의 `C:\Users\user/.config/git/ignore` permission warning 은 기존 환경 경고로 보이며 검증 판정에는 영향이 없다.

## 8. 최종 판정

**20-3-3 검증 통과.**

백엔드 F-1 (c) 가벼운 의사만 구현은 요청서 범위와 테스트 결과에 부합한다. 다음 단계는 `20-3-4 F-2 반복 예약` 이며, 시작 전 사용자 §6-6 반복 패턴/시리즈 처리/충돌 정책 결정이 필요하다.
