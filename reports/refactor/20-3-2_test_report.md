# 20-3-2 F-11 권한 다중 등급 테스트 리포트

## 환경

- 직전 commit: `319a5aa` (20-3-1 F-10 노쇼)

## 결과

| 검증 | 결과 |
|---|---|
| ruff | All checks passed (3 autofix) |
| check_db_path | exit 0 |
| `pytest tests/test_20_3_2_permission_level.py -v` | **13 passed** in 0.5s |
| `pytest tests/test_pyinstaller_hidden_imports.py + spec_discovery` | **215 passed** (m015 자동 글롭 + import 가능) |
| `pytest tests -q` 전체 | **1748 passed / 1 skipped / 10 xfailed** in 13.20s |

### baseline 비교

| 시점 | passed | 증가 |
|---|---:|---:|
| 20-3-1 baseline | 1735 | — |
| 20-3-2 (본 세션) | **1748** | **+13** |

증가 13 = test_20_3_2 13 cases. 19-8 contract 갱신 (permission_level 추가) — 기존 회귀는 갱신 후 통과.

## 자동 테스트 확인

- m015 + Employee.permission_level 컬럼 + 기본값 'staff' (2 cases)
- _serialize_employee 응답 12키 + therapists.service 동등 (3 cases)
- /api/admin/employees/{eid}/permission endpoint 인증 + 등급 검증 (2 cases)
- EMPLOYEE_PERMISSION_LEVELS 상수 (staff / admin / super 3등급, viewer 미도입) (1 case)
- 호환성 보존 — 기존 11키 + permission_level / role 컬럼 / audit (3 cases)
- 보안 회귀 — 기존 admin 로그인 / require_admin 흐름 (2 cases)

## TestClient / API 호출 확인

- POST /api/admin/employees/{eid}/permission → 인증 없이 401/403 / 잘못된 등급 400 단언

## 수동 확인 필요

- 운영 환경에서 등급 변경 흐름 (직원 관리 화면 select) — 본 v1 백엔드만 (UI 후속).
- 등급별 화면 분기 (예: staff 통계 접근 ⊥) — 후속 분할.
- F-15 의사 가드 + permission_level 결합 (super 만 의사 정보 노출) — 후속 분할.

## 영향 없음

- 19-C §A 예약 / §B 휴무 / §C 치료항목 / §D 환자 / §G SMS / §H 통계 / §K Health: 영향 0.
- DB schema m001~m014: 변경 0.
- 기존 admin 로그인 / PBKDF2 / 5회 잠금 / 8h 세션 / require_admin 86 endpoint: 변경 0.
- main.html JS: 변경 0.

## 보안

- 운영 DB 접근: 없음
- 외부 API 호출: 없음
- 실제 문자 발송: 없음
- PII / API key 원문 노출: 없음 (audit detail = 등급 명만)

## 결론

다음 단계: **20-3-3 F-1 doctors 진입 전 사용자 §5-7 결정 (가장 큰 결정 — EMR 도입 범위)**.
