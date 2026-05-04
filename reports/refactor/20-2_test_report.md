# 20-2 그룹 B 테스트 리포트

## 환경

- 브랜치: `ai-rag-v1-integration`
- 직전 commit: `2c2f0d1` (20-1 그룹 A)

## 실행 명령

```
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts/check_db_path.py
venv\Scripts\python.exe -m pytest tests/test_20_2_group_b.py -v
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q
venv\Scripts\python.exe -m pytest tests -q
```

## 결과

| 검증 | 결과 |
|---|---|
| `ruff check app tests scripts` | All checks passed (3 autofix — unused import / import order) |
| `scripts/check_db_path.py` | exit 0 |
| `pytest tests/test_20_2_group_b.py -v` | **24 passed** in 0.17s |
| `pytest tests/test_pyinstaller_hidden_imports.py -q` | **211 passed** (신설 3 모듈 × 2 parametrized = +6) |

### baseline 비교

| 시점 | passed | skipped | xfailed |
|---|---:|---:|---:|
| 20-1 baseline | 1696 | 1 | 10 |
| 20-2 (본 세션) | **1726** | 1 | 10 |
| 증가분 | **+30** | 0 | 0 |

증가 30 = 20-2 group_b test 24 + PyInstaller 신설 3 모듈 × 2 parametrized = 6 = 30. 회귀 0건.

`pytest tests -q`: **1726 passed, 1 skipped, 10 xfailed, 27 warnings in 14.03s**.

## 자동 테스트로 확인한 항목

- F-13 health snapshot 단위: 7 cases (6키 셋 정합 + 타입 단언 + uptime 증가)
- F-13 health TestClient endpoint: 2 cases (200 + 6키 응답 + PII 비노출)
- F-12 notes service: 5 cases (read/write/cancel prefix/by_kind dispatch)
- F-14 calendar view-model 회귀: 8 cases (19-3 helper 보존)
- 보안 회귀: 2 cases (health 응답 API key 부재 + notes mask)
- PyInstaller hidden imports: 3 신설 모듈 등록 + 실제 import 확인 (6 cases)

## 테스트 클라이언트 / API 호출로 확인한 항목

- F-13 `GET /api/health` → 200 + 6키 응답 dict 정합 + PII / API key / password / phone 부재.

## 수동 확인 필요 항목

- 운영 환경에서 `/api/health` 가 외부 모니터링 (예: cron / nagios / prometheus) 도구로 호출되는지 — 후속 결정.
- F-12 notes service 가 기존 `api.py:update_patient_memo` 호출지에서 *점진 위임* 되는 시점 — 후속 세션.

## 이번 세션 영향 없음으로 판단한 항목

- 19-C §4 A 예약 / B 휴무 / C 치료항목·완료체크 / G SMS / H 통계: 영향 0.
- DB schema (m001~m013): 변경 0.
- main.html / FullCalendar JS: 변경 0 (F-14 = 19-3 view-model 회귀만).

## 확인하지 못한 항목과 이유

- PyInstaller 실제 빌드 + exe smoke: 본 20-2 자체 회귀에서 미실행 (Codex 빌드 검증으로 미룸).
- F-13 backup_age / disk_free 가 운영 환경에서 실제 백업 / 디스크 상태와 정합하는지 — 운영 DB 접근 ⊥.

## 보안 확인 결과

- 운영 DB 접근: **없음** (4단계 격리 + db_guard).
- 외부 API 호출: **없음** (health 진단 = 로컬 DB / 파일시스템 / config 만).
- 실제 문자 발송: **없음**.
- 개인정보 / API key 원문 노출: **없음** — `/api/health` 응답에 6키만, API key / PII 부재 단언 통과.

## 결론

- 다음 단계 진행 가능: **yes** (전체 회귀 baseline 1726 예상 → 별도 백그라운드 결과 추가).
- 남은 위험: F-12 service 점진 위임 / F-13 외부 모니터링 통합 — 후속 결정.
