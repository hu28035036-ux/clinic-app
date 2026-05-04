# 20-1 그룹 A 테스트 리포트

## 환경

- 브랜치: `ai-rag-v1-integration`
- Python: 3.12.10 (venv)
- pytest: 8.4.2
- 직전 commit: `1ca2d63` (20-P-1 마스터 플랜)

## 실행 명령

```
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts/check_db_path.py
venv\Scripts\python.exe -m pytest tests/test_20_1_group_a.py -v
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q
venv\Scripts\python.exe -m pytest tests -q
```

## 결과

| 검증 | 결과 |
|---|---|
| `ruff check app tests scripts` | **All checks passed!** (1회 자동 fix — import order) |
| `scripts/check_db_path.py` | exit 0 |
| `pytest tests/test_20_1_group_a.py -v` | **15 passed** in 0.21s |
| `pytest tests/test_pyinstaller_hidden_imports.py -q` | **205 passed** in 0.68s (신설 5개 모듈 검증 포함) |
| `pytest tests -q` (전체) | **1696 passed / 1 skipped / 10 xfailed** in 12.60s |

### baseline 비교

| 시점 | passed | skipped | xfailed |
|---|---:|---:|---:|
| 19-14 baseline | 1671 | 1 | 10 |
| 20-1 (본 세션) | **1696** | 1 | 10 |
| 증가분 | **+25** | 0 | 0 |

증가 25 = 20-1 group A test 15 cases + PyInstaller hidden_imports 신설 5개 모듈 × 2 parametrized = 10 = 25.

## 자동 테스트로 확인한 항목

- F-15 doctor_guard 단위 (의사 단정 / 일정 / 진단 차단 + 정상 텍스트 비차단 + 빈 문자열) — 7 cases
- F-15 RAG pipeline.validate_answer 통합 (의사 단정 차단 + 정상 비차단 + 기존 _RE_MEDICAL_CLAIM 동작 보존) — 3 cases
- F-7 환자 마스킹 + AI 로그 삭제 (활성/비활성 분기 + 멱등성 + dry_run + 권장값 상수 정합) — 3 cases
- F-8 audit_log 5년 후 삭제 (오래된/최신 분기 + dry_run + 권장값 상수 정합) — 2 cases
- 신설 5개 모듈 PyInstaller hidden_imports 등록 + 실제 import 가능 — 10 cases
- 19-14 baseline 1671 cases 회귀 0

## 테스트 클라이언트 / API 호출로 확인한 항목

- 본 20-1 v1 = 신설 모듈 + 헬퍼 함수만 (admin endpoint / 자동 트리거 ⊥) — TestClient 호출 없음.
- F-15 RAG pipeline 통합 = 함수 직접 호출 (`validate_answer`).

## 수동 확인 필요 항목

- 운영 환경에서 retention 헬퍼를 admin endpoint / cron 으로 트리거 할 시점 — 본 20-1 범위 밖. 사용자 결정 필요 (후속 세션).
- F-15 의사 가드가 실제 RAG 답변 흐름에서 차단되는지 UI 수동 확인 — 운영 데이터 필요 (테스트는 함수 단위만).

## 이번 세션 영향 없음으로 판단한 항목

- 19-C §4 A 예약 / B 휴무 / C 치료항목·완료체크 / F 캘린더 / G SMS / H 통계: 영향 0 (본 20-1 = 정책 / 가드 / retention 헬퍼만).
- 19-C §10 SMS / §11 통계: 영향 0.
- DB schema (m001~m013): 변경 0.

## 확인하지 못한 항목과 이유

- PyInstaller 실제 빌드 + exe smoke: 본 20-1 자체 회귀 단계에서는 미실행 (Codex 빌드 검증으로 미룸).
- AI 로그 / audit_log 가 *이미 6개월 / 5년 초과한 운영 데이터* 에서 어떻게 동작하는지: 운영 DB 접근 ⊥ — 후속 별도 admin 도구 (수동 트리거) 단계에서 확인.

## 보안 확인 결과

- 운영 DB 접근: **없음** (`scripts/check_db_path.py` exit 0 / 4단계 격리 + db_guard).
- 외부 API 호출: **없음** (`_block_sdk_modules` 활성 / FakeProvider 만 사용 — 본 20-1 은 LLM 호출 없음).
- 실제 문자 발송: **없음** (sms 모듈 무영향).
- 개인정보 / API key 원문 노출: **없음** — `mask_inactive_patients` 가 PII 마스킹 후 commit. 응답 dict 에는 candidates / masked / dry_run 카운트만.

## 결론

- 다음 단계 진행 가능: **yes** — Codex 검증 요청.
- 남은 위험: F-7 / F-8 자동 트리거 미구현 (헬퍼만) — 후속 세션에서 admin endpoint / cron 결합 결정.
