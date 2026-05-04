# 19-11 stats 분리 — 테스트 리포트

## 환경

- 작업 디렉토리: `C:\Users\user\Desktop\새 폴더\병원예약관리\병원예약관리`
- 브랜치: `ai-rag-v1-integration`
- Python: `venv\Scripts\python.exe` (3.12.10)
- pytest: 8.4.2
- ruff: 프로젝트 설정 (`pyproject.toml` 의 `app/**` per-file-ignores 유지)
- DB: 격리된 `.test-tmp/` 경로 (운영 DB 미참조).

## 실행한 명령

| 명령 | 결과 |
|---|---|
| `venv/Scripts/python.exe -m pytest tests/test_19_11_stats.py -q` | **90 passed** |
| `venv/Scripts/python.exe -m pytest tests -q` | **1335 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **155 passed** |
| `venv/Scripts/python.exe -m pytest tests -k "ai_sms or ai_leave or rag or safety or contract" -q` | **142 passed, 1201 deselected, 21 warnings** |
| `venv/Scripts/python.exe -m ruff check app tests scripts` | **All checks passed!** |
| `venv/Scripts/python.exe scripts/check_db_path.py` | exit 0 |

## 테스트 통과 카운트

- 19-11 전용 contract: **90 passed** (1회차 — 코드 수정 0회, ruff I001 자동 보정 1회).
- 전체 회귀: **1335 passed, 1 skipped, 7 xfailed**. (19-10 통과 시점 1233 → 19-11
  추가 90 + 신규 spec 12 = 1335).
- PyInstaller 스펙: **155 passed** (19-11 신규 6개 모듈 등록 검증 12건 추가).
- AI 회귀 (SMS / Leave / RAG / Safety / contract): **142 passed**.

## 자동 수정 루프

- **1회차** : 90 cases 작성 → 90 / 90 통과 (코드 수정 0회).
- ruff 자동 보정 1회 — `tests/test_19_11_stats.py` 의 import 정렬 (I001) 자동 fix.
- **총 0회 코드 수정 루프** (모든 contract 가 1회차에서 통과).

## 핵심 신규 테스트 (90 cases)

### 1. 카운트 정책 상수 (시간 가중치 회귀 방지) (2 cases)
- `MANUAL_COUNT_INCREMENT_PER_APPT == 1` 상수 검증.
- aggregator 본체에 `+= 2` / `* 2` / `*= 2` 패턴 부재 검증.

### 2. mode / treatment_code 매칭 byte-equivalent (29 parametrize)
- `treatment_code_matches` 9 케이스 (빈/all/manual_all/특정 코드).
- `is_counted_for_mode` 13 케이스 (all/approved/reserved/None/unknown).
- `is_counted_for_treatment_mode` 7 케이스 (by_treatment 의 mode 분기 다름).

### 3. weekday / 미배정 / ESWT 상수 (3 cases)
- `WEEKDAY_LABELS == ("월", "화", "수", "목", "금", "토", "일")`.
- `weekday_label` 0~6 + 범위 밖 (7 / -1) → 빈 문자열.
- `UNASSIGNED_SENTINEL == "__none__"` / `UNASSIGNED_LABEL == "미배정"`.
- `ESWT_CODE` ↔ `app.models.constants` 정합.

### 4. resolve_stats_range / date_list (8 cases)
- date_from/date_to 분기 / year/month 분기 / 12월 → 다음 해 / 잘못된 형식 /
  inverted (date_to < date_from).
- `api.py:_resolve_stats_range` byte-equivalent 비교 (3 케이스).
- `date_list` byte-equivalent + 빈 범위.

### 5. aggregators — summary (3 cases)
- 기본 케이스 (4 row, 5 카운트 검증).
- treatment_code 필터.
- **시간 가중치 회귀 방지 검증** : manual30 + manual60 = total 2 (시간 가중치라면 3).

### 6. aggregators — by_hour / by_weekday (3 cases)
- by_hour 기본 + mode=approved.
- by_weekday 기본 (2026-05-04 월요일).

### 7. aggregators — by_treatment (1 case)
- 한 예약에 여러 코드면 *각 코드마다* +1 (합산 가중치 ⊥).

### 8. aggregators — daily (1 case)
- 8키 dict + manual_by_code / manual_approved_by_code.

### 9. service — 응답 빌더 (5 cases)
- summary 12키 / by_hour 24항목 / by_weekday 7요일 / by_treatment 내림차순 정렬 /
  daily 10키.

### 10. repository — DB 격리 fixture (4 cases)
- list_appointments_in_range byte-equivalent.
- list_manual_treatment_rows / list_manual_treatment_codes / list_therapist_employees.

### 11. schemas — contract 회귀 보호 (6 cases)
- SUMMARY / BY_HOUR / BY_WEEKDAY / BY_TREATMENT / DAILY / AGGREGATE.

### 12. 단방향 경계 D-4 (8 cases)
- rules / aggregators / repository / service / schemas 가 `app.routers` 미참조.
- rules / aggregators 가 ORM / DB / sqlalchemy / fastapi 미참조.
- repository.py 가 `app.models` 함수 안 lazy import.
- 6개 모듈 import 가능.

### 13. 라우터 시그니처 무수정 (9 parametrize)
- `stats_summary` / `stats_by_hour` / `stats_by_weekday` / `stats_by_treatment` /
  `stats_daily` / `stats_aggregate` / `stats_by_therapist` /
  `stats_manual_by_therapist` / `stats_daily_by_therapist`.

### 14. 기존 흐름 영향 없음 (6 cases)
- `/api/stats/summary` / `/by-hour` / `/by-weekday` / `/by-treatment` /
  `/daily` / `/aggregate` 응답 키 contract 검증.

### 15. stats 모듈 read-only + 외부 호출 ⊥ (2 cases)
- 모든 stats 파일에 `db.commit` / `db.add` / `db.delete` / `db.flush` 부재.
- `urllib.request` / `requests` / `httpx` import 부재.

## 운영 DB 보호 검사 결과

`scripts/check_db_path.py` exit 0 — 운영 DB 경로 출력만, 실제 접근 ⊥.

## 시간 가중치 회귀 방지 가드

- `rules.MANUAL_COUNT_INCREMENT_PER_APPT = 1` 상수.
- `rules.TIME_WEIGHTED_COUNT_DENIED = True` 상수.
- aggregator 본체 단위 테스트로 `+= 2` / `* 2` 패턴 부재 검증.
- summary 집계 단위 테스트로 manual30 + manual60 = 2 (시간 가중치라면 3) 검증.

## RAG / SMS AI / Leave AI / Safety 회귀

| 테스트 묶음 | 결과 |
|---|---|
| `tests -k "ai_sms"` | 통과 (142 passed 안에 포함) |
| `tests -k "ai_leave"` | 통과 |
| `tests -k "rag or safety"` | 통과 |
| `tests -k "contract"` | 통과 |
| 종합 | **142 passed** |

## 주요 로그 발췌

```
============================= 90 passed in 0.35s ==============================
========== 1335 passed, 1 skipped, 7 xfailed, 27 warnings in 12.29s ===========
============================= 155 passed in 0.62s =============================
============== 142 passed, 1201 deselected, 21 warnings in 2.27s ==============
All checks passed!
```

## 결론

- 19-11 신규 contract 90 cases 모두 통과 (수정 루프 0회).
- 전체 회귀 1335 passed.
- ruff / DB 경로 / 기존 SMS AI / 휴무 AI / RAG / 계약 테스트 모두 통과.
- **시간 가중치 방식 회귀 방지 가드** 적용 (정책 상수 + 코드 패턴 검증 + 집계 결과 검증).
- **stats 모듈 read-only 보장** (DB 변경 메서드 부재 검증).
- **외부 API 호출 부재** (외부 호출 라이브러리 import 부재 검증).
- **19-11 → 19-12 진입 후보** (Codex 검증 후 최종 결정).
