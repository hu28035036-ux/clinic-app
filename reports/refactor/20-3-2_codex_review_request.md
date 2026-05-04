# 20-3-2 Codex 검증 요청서

## 1. 세션 이름

`20-3-2_permission_level` — F-11 권한 다중 등급 도입 (m015 + Employee.permission_level + permission endpoint).

## 2. 작업 목표

20-P-2 §4 사용자 §4-6 권장값 정합:
- (a) 3등급: staff / admin / super
- (i) admin 별도 게이트 보존 — 기존 PBKDF2 / 5회 잠금 / 8h 세션 / require_admin 86 endpoint 무수정.
- (ii) viewer 미도입.

본 v1 = 백엔드만. UI 등급 select 화면 분기는 후속 분할.

## 3. 변경 파일 목록

### 신규 (2개)
```
app/migrations/m015_employee_permission_level.py  (49줄)
tests/test_20_3_2_permission_level.py             (207줄, 13 cases)
```

### 수정 (5개)
```
app/models/models.py                  (+3, permission_level Column)
app/models/schemas.py                 (+9, EmployeePermissionIn)
app/routers/api.py                    (~35, _serialize_employee + endpoint)
app/modules/therapists/service.py     (+2, serialize_employee 동기)
tests/test_19_8_therapists.py         (+6, 12키 contract)
```

## 4. 수정 가능 / 금지 범위

- 가능: m015, Employee.permission_level, _serialize_employee 12키, EmployeePermissionIn, /api/admin/employees/{eid}/permission, 19-8 contract.
- 금지: m001~m014, Employee.role 컬럼 (직군 분기), admin 로그인 / PBKDF2 / 5회 잠금 / 8h 세션 / require_admin 86 endpoint, 기존 33+ 응답 key, main.html JS.

## 5. 실제 변경

- m015: ALTER TABLE employees ADD COLUMN permission_level VARCHAR(20) DEFAULT 'staff' NOT NULL (idempotent).
- Employee.permission_level: String(20) nullable=False default='staff'.
- _serialize_employee: 11키 → 12키 (permission_level 추가).
- therapists.service.serialize_employee: 동일 키 셋 동기 (byte-equivalent 단언 통과).
- POST /api/admin/employees/{eid}/permission: require_admin 의존. EMPLOYEE_PERMISSION_LEVELS 검증. audit("employee.permission_update", eid, f"level={...}").
- 19-8 test_serialize_employee_byte_equivalent_with_api + test_get_employees_endpoint_keys_match_serialize_employee 갱신.

## 6. 실행한 테스트 + 결과

```
ruff check app tests scripts                                    → All passed (3 autofix)
scripts/check_db_path.py                                        → exit 0
pytest tests/test_20_3_2_permission_level.py -v                 → 13 passed
pytest tests/test_pyinstaller_hidden_imports.py + spec_discovery → 215 passed (m015 자동 글롭 + import)
pytest tests -q                                                 → 1748 passed / 1 skipped / 10 xfailed
```

20-3-1 baseline 1735 → 20-3-2 **1748** (+13, 회귀 0).

## 7. 수정 루프

1회차 코드 + ruff + 12 passed → 1 fail (require_admin import 위치).
2회차 require_admin = routers.api 정정 + 19-8 contract 갱신 → 1748 passed.

총 2회 루프.

## 8. 작동확인 (19-C §E 치료사·의사 + §I 관리자 + §M 보안)

- §E 치료사·의사: serialize_employee 12키 + therapists.service 동기 단언.
- §I 관리자: require_admin 86 endpoint 무수정 + admin 로그인 흐름 보존 + audit detail PII 부재.
- §M 보안: 운영 DB / 외부 API / 문자 발송 / PII·API key 원문 모두 부재.

## 9. 수정 루프 횟수

2회차 안에 통과 (5회 한도 내).

## 10. 자동 테스트로 확인한 항목

- m015 + permission_level 컬럼 + 기본값 'staff' (2)
- _serialize_employee 12키 + therapists.service 동기 (3)
- permission endpoint (인증 / 등급 검증) (2)
- EMPLOYEE_PERMISSION_LEVELS 3등급 + viewer 부재 (1)
- 호환성 (11+1 키 / role 컬럼 / audit) (3)
- 보안 회귀 (admin 로그인 / require_admin) (2)

## 11. 테스트 클라이언트 / API 호출

- POST /api/admin/employees/{eid}/permission → 인증 없이 401/403 / 잘못된 등급 400.

## 12. 수동 확인 필요

- UI 등급 select / 직원 관리 화면 — 후속 분할.
- 등급별 화면 분기 (staff 통계 접근 ⊥ 등) — 후속 분할.
- F-15 가드 강화 (super 만 의사 정보 노출) — 후속 분할.

## 13. 영향 없음

- 19-C §A 예약 / §B 휴무 / §C 치료항목 / §D 환자 / §G SMS / §H 통계 / §K Health: 영향 0.
- m001~m014 변경 0. main.html JS 변경 0.

## 14. 운영 DB / 외부 API / 문자 발송 / PII

- 운영 DB: 없음
- 외부 API: 없음
- 실제 문자 발송: 없음
- PII / API key 원문 노출: 없음

## 15. 응답 key 유지

- 12 employee 키 (11 + permission_level) — 기존 11 보존.
- 기존 33+ 응답 key 셋 보존.

## 16. 다음 세션 진행

**yes** Codex 통과 시. 다음 = 20-3-3 F-1 doctors 진입 전 사용자 §5-7 결정 — EMR 도입 범위 (가장 큰 결정 — 도수치료 전문 vs 일반 진료 정체성 결정).

## 17. Codex 결과 위치

- [reports/refactor/20-3-2_codex_review.md](20-3-2_codex_review.md)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md)

## 18. 사용자 → Codex 전달 문구

> "reports/refactor/latest_codex_review_request.md 20-3-2 F-11 권한 다중 등급 검증 시작해줘. Claude Code 요약만 믿지 말고 m015 마이그레이션 / Employee.permission_level / _serialize_employee 12키 / therapists.service 동기 / /api/admin/employees/{eid}/permission endpoint / EMPLOYEE_PERMISSION_LEVELS 3등급 / 19-8 contract 갱신 / require_admin 보존 정책을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md 와 reports/refactor/20-3-2_codex_review.md 에 남겨줘."
