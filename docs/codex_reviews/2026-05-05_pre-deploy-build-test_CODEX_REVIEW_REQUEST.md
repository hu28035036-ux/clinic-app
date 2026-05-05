# CODEX_REVIEW_REQUEST — pre-deploy-build-test (2026-05-05)

## 1. 사용자 원래 요청

```
배포 전 빌드테스트 및 실행검증을 진행해줘.
목표: 배포 대상 컴퓨터에서 실행되지 않을 수 있는 요소를 사전에 찾아내고
설치/실행/DB/정적파일/AI 기능/백업/권한/포트/브라우저 접속까지 전체 검증.
중요: 기능 추가 ❌, 기능 변경 ❌, 운영 DB 직접 수정 ❌, 수정 전 보고.
```

## 2. Claude Code 작업 요약

배포 전 *검증만 진행* (코드 수정 ❌). 11 영역 전수 검사:
- 실행 환경 (Python 3.12.10 / pip 26.1 / venv) ✅
- 서버 부팅 + 정적파일 + API endpoint ✅
- DB 스키마 (26 테이블 / m001~m020) + therapists.birth_date/phone 회귀 ✅
- 도메인 정책 (manual60=1, 노쇼 3/4키 contract) ✅
- 모든 회귀 / lint / DB 안전 / AI 안전 통과 ✅

결과: **조건부 배포 가능** — 코드 정상, 단 4점 버전 정합 누락 (CHANGELOG / VERSION / INDEX 미갱신).

## 3. 사용한 내부 Agent 목록

01 Brainstorming → 03 Architecture (모듈 / spec) → 05 Test/Harness → 11 Release Check → 10 Docs

## 4. 수정한 파일 목록

| 파일 | 변경 |
|---|---|
| (없음 — 검증만) | — |

## 5. 새로 만든 파일 목록

- `docs/DEPLOYMENT_CHECKLIST.md` (12 섹션 빌드테스트 단일 원천)
- `docs/codex_reviews/2026-05-05_pre-deploy-build-test_CODEX_REVIEW_REQUEST.md` (본 파일)

## 6. 실행한 테스트 명령

```powershell
venv\Scripts\python.exe --version
venv\Scripts\python.exe -m pip list
venv\Scripts\python.exe -m pytest tests -q
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts\check_db_path.py
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py tests/test_migration_spec_discovery.py -q
venv\Scripts\python.exe -m pytest tests/test_phase06_ai_safety.py tests/test_ai_safety_harness.py tests/test_ai_hallucination.py tests/test_ai_full_harness.py tests/test_local_only_mode.py -q
# 추가: TestClient 로 / + /static/* + /api/* 응답 검사
```

## 7. 테스트 결과

- pytest 전체: **2143 passed / 1 skipped / 10 xfailed / 0 failed (20.19s)**
- ruff: **All checks passed!**
- DB safety: **OK** (운영 경로 단독 실행 정상 출력)
- PyInstaller hidden imports: **239 passed (0.67s)**
- AI safety 풀세트: **45 passed (0.29s)**
- TestClient endpoint: **/ + 4 static + /api/health + /api/about + /api/ai/health/public 모두 200**

## 8. 영향 범위

| 영역 | 결과 |
|---|---|
| 화면 | 6 탭 (예약/환자/직원/문자/관리자) — AI 도우미 탭 v1.3.5+ UI 제거 |
| API | 127 라우트 등록, 주요 endpoint 200 |
| DB | 26 테이블, 마이그레이션 1~20 모두 적용, employees.birth_date/phone 보존 |
| 테스트 | 2143 passed / 0 failed |
| AI 기능 | preview→approve / Privacy / Hallucination / local-only 모두 회귀 통과 |
| 정적파일 | app.css 130KB / _ai_helper.css 10KB / ai_helper.js 7KB / ai_leave_helper.js 6KB |
| 빌드 spec | hidden imports + datas + 마이그레이션 자동 글롭 정합 |

## 9. Codex 가 검증해야 할 체크리스트

- [ ] **빌드 가능성** — `dosu_clinic.spec` 의 hidden imports / datas / openai+anthropic SDK collect 가 모든 모듈 포함하는지
- [ ] **운영 DB 미접근** — TestClient 검증이 격리 DB (tests/temp/) 만 사용했는지 확인
- [ ] **마이그레이션 안전성** — 신규 사용자 DB / 기존 사용자 DB 모두 m001~m020 적용 안전한지
- [ ] **`employees.birth_date / phone` 회귀 가드** — 과거 누락 컬럼 사고 재발 가능성
- [ ] **manual60=1 / 노쇼 3·4키 contract** — 도메인 정책 보존
- [ ] **AI 안전 정책 (preview→approve, 단정 표현 ❌, Privacy)** — 회귀
- [ ] **CLAUDE.md 절대 금지 11 항목** — 모든 보존 확인
- [ ] **사용자 배포 PC 실행 위험** — 한글/공백 경로 / 포트 / 방화벽 / AppData 권한 / DB 스키마 충돌
- [ ] **4점 버전 정합 누락** (§ 9.2 권장 수정) — VERSION.txt v1.3.3 헤더가 config.py v1.3.4 와 불일치
- [ ] **`dist/` 가 cleanup 으로 제거됨** — 다음 빌드 시 PyInstaller 가 자동 재생성하나, 현재 배포 산출물 ❌

## 10. Codex 금지사항

- 코드 직접 수정 ❌
- 운영 DB (`%APPDATA%\도수치료예약\clinic.db`) 직접 수정 ❌
- 기존 탭 이름 변경 ❌
- 사용자 미요청 새 탭 추가 ❌
- AI preview → approve 구조 변경 ❌
- 환자 개인정보 외부 전송 ❌
- 문자 자동 발송 구조 변경 ❌
- Claude Code 설명 그대로 신뢰 ❌ — 실제 파일 (`app/`, `tests/`, `dosu_clinic.spec`, `docs/DEPLOYMENT_CHECKLIST.md`) 기준으로 검증

## 11. Codex 보고 형식 (9 항목)

1. 전체 판정 (승인 / 조건부 승인 / 반려)
2. 잘 된 부분
3. 문제점
4. 위험한 변경 / 위험 요소
5. 누락된 테스트
6. 추가 테스트 제안
7. 수정 제안 (파일:라인)
8. 반드시 수동 확인할 화면 / 절차
9. 최종 의견 (배포 가능 / 조건부 / 반려)
