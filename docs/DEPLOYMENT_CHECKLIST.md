# DEPLOYMENT_CHECKLIST

병원예약관리 (도수치료예약, v1.3.4 / 차기 v1.3.5) 배포 전 빌드테스트 + 실행검증 절차 + 위험 요소 단일 원천.

- 작성: 2026-05-05
- 검증 기준 환경: Windows 11 + Python 3.12.10 + venv
- 적용 대상: 사용자 배포 PC (병원 PC) — 단독 실행형 PyInstaller 산출물

> 본 문서는 *코드 수정 ❌ 검증만* 의 결과 단일 원천. 수정이 필요한 항목은 § 9 에 *권고* 로 기록 — 사용자 동의 후 별도 작업.

---

## 1. 현재 실행 환경

| 항목 | 값 |
|---|---|
| Python 버전 | 3.12.10 |
| pip 버전 | 26.1 |
| OS | Windows 11 (10.0.26200) |
| 프로젝트 경로 | `C:\Users\user\Desktop\새 폴더\병원예약관리\병원예약관리` (한글 + 공백 포함) |
| 실행 명령 | `venv\Scripts\python.exe run.py` (개발) / `dist\도수치료예약\도수치료예약.exe` (배포) |
| 운영 DB | `%APPDATA%\도수치료예약\clinic.db` |
| 격리 DB (dev) | `tests\temp\dev_clinic.db` |

## 2. 빌드 / 실행 결과

| 항목 | 결과 |
|---|---|
| `run.py` 모듈 import | ✅ 성공 |
| FastAPI app 부팅 | ✅ 127 라우트 등록 |
| 마이그레이션 자동 | ✅ m001~m020 적용 (20개) |
| 정적파일 / | ✅ 200 (3KB) |
| 정적파일 `/static/css/app.css` | ✅ 200 (130KB) |
| 정적파일 `/static/css/_ai_helper.css` | ✅ 200 (10KB) |
| 정적파일 `/static/js/ai_helper.js` | ✅ 200 (7KB) |
| 정적파일 `/static/js/ai_leave_helper.js` | ✅ 200 (6KB) |
| `/api/health` | ✅ 200 |
| `/api/about` | ✅ 200 |
| `/api/ai/health/public` | ✅ 200 |
| 포트 8000 | ✅ free (현재 사용 ❌) |
| host 바인딩 | `0.0.0.0:8000` (LAN 접속 가능) |

## 3. DB 검증 결과

| 항목 | 결과 |
|---|---|
| DB 경로 (운영) | `%APPDATA%\도수치료예약\clinic.db` |
| DB 경로 (dev) | `tests\temp\dev_clinic.db` (격리) |
| 신규 DB 생성 | ✅ AppData / 격리 모두 가능 |
| 기존 DB 호환 | ✅ 마이그레이션 자동 적용 (`init_db()`) |
| 스키마 불일치 | ❌ 없음 |
| `employees.birth_date` / `phone` 회귀 | ✅ 보존 (m002 / m003 / m010 적용) |
| 26 테이블 모두 정상 생성 | ✅ |
| `manual60 = 1` 카운트 정책 | ✅ `app/modules/treatments/rules.py:174` 보존 |
| 노쇼 (F-10) CANCEL 3키 / MARK_NO_SHOW 4키 | ✅ `app/modules/appointments/schemas.py:65~127` |

## 4. 화면 검증 결과

`/` 응답 + `app/templates/main.html` 의 6 탭 구조 확인:

| 탭 | 상태 |
|---|---|
| ▦ 예약 (`tab-reserve`) | ✅ 정상 (AI 예약 도우미 카드 포함) |
| ◎ 환자 (`tab-patients`) | ✅ 정상 |
| ◇ 직원 (`tab-therapists`) | ✅ 정상 (직원 관리 / 휴무일 관리 서브탭 — AI 휴무 도우미 포함) |
| ✉ 예약 문자 (`tab-sms`) | ✅ 정상 (개별 / 일괄 안내) |
| ≡ 관리자 (`tab-admin`) | ✅ 정상 (메인 모드 only) |

> v1.3.5+: `tab-ai-manual` (RAG 매뉴얼 Q&A) UI 제거 완료. 백엔드 보존.

수동 시각 확인 권장 (사용자):
- 모든 탭 헤더 텍스트 가독성 (Phase M 적용)
- AI 도우미 카드 색상 (블루 톤, Phase E 적용)
- 비밀번호 변경 권장 알림 — 로그인 시 1회만 (직전 fix)

## 5. 핵심 기능 검증 결과

| 기능 | 회귀 테스트 | 결과 |
|---|---|---|
| 예약 등록/수정/취소/완료 | `test_appointment_rules` / `test_19_9_appointments` | ✅ |
| 노쇼 (F-10) | `test_20_3_1_no_show` | ✅ |
| 시리즈 (반복 예약) | `test_20_3_4_appointment_series` | ✅ |
| 자원 (치료실) | `test_20_3_5_resources` | ✅ |
| 환자 검색/등록 | `test_19_7_patients_notes` | ✅ |
| 치료사/의사 관리 | `test_19_8_therapists` / `test_20_3_3_doctors` | ✅ |
| 휴무 (종일/오전/오후 / UNIQUE) | `test_19_5_leaves` / `test_employee_leave_*` | ✅ |
| 치료항목 (alias / manual60=1) | `test_19_6_treatments` | ✅ |
| 예약 문자 (수동 발송 흐름) | `test_19_10_sms` / `test_ai_sms_validate` | ✅ |
| 통계 (manual30=1 / manual60=1) | `test_19_11_stats` / `test_stats_counts` | ✅ |
| 백업 / 복원 | `test_db_restore_safety` / `test_19_12_admin` | ✅ |
| 권한 (admin / 직원) | `test_admin_auth_required` / `test_20_3_2_permission_level` | ✅ |

문자 자동 발송 ❌ — `app/modules/sms/provider.py:FakeSmsProvider` (외부 호출 ⊥) 보존.

## 6. AI 기능 검증 결과

| 항목 | 결과 |
|---|---|
| AI 예약 도우미 카드 (예약 화면 *내부*) | ✅ 보존 (`_ai_appointment_helper.html`, `x-data="aiHelper"`) |
| AI 휴무 도우미 카드 (휴무 서브탭 *내부*) | ✅ 보존 (`_ai_leave_helper.html`) |
| preview → approve 구조 (Gate 1 + Gate 2) | ✅ `app/ai/ai_executor.py` |
| 단정 표현 ❌ ("예약 완료" 등) | ✅ `tests/test_ai_hallucination.py` 통과 |
| Privacy (외부 AI API 페이로드 PII 차단) | ✅ `app/ai/ai_safety.py:PRIVACY_FORBIDDEN_KEYS` 12 키 |
| 환자 개인정보 외부 전송 ❌ | ✅ `tests/test_ai_safety_harness.py` 통과 |
| Local-only mode (외부 LLM 키 없이 동작) | ✅ `tests/test_local_only_mode.py` 통과 |
| AI 명령 audit log | ✅ `ai_command_logs` 테이블 (m019) |
| 인증 정책 (선택적 admin 토큰) | ✅ v1.3.5+ get_actor_user_id |

## 7. 테스트 결과

| 명령 | 결과 |
|---|---|
| `pytest tests -q` | **2143 passed / 1 skipped / 10 xfailed / 0 failed (20.19s)** |
| `ruff check app tests scripts` | **All checks passed!** |
| `scripts/check_db_path.py` | ✅ (운영 DB 경로 정상 출력) |
| `pytest tests/test_pyinstaller_hidden_imports.py tests/test_migration_spec_discovery.py` | **239 passed (0.67s)** |
| `pytest tests/test_phase06_ai_safety.py + test_ai_safety_harness + test_ai_hallucination + test_ai_full_harness + test_local_only_mode` | **45 passed (0.29s)** |

실패 / 누락 / 건너뛴 테스트:
- skipped 1 / xfailed 10: 모두 *spec 정의됐으나 백엔드 미구현* (의도된 xfail) — 회귀 ❌
- 실패 0

## 8. 배포 컴퓨터에서 실행 안 될 가능성

### 8.1 위험도 높음 (사전 확인 필수)

| 위험 | 영향 | 완화 |
|---|---|---|
| Python 미설치 | exe 빌드본은 영향 ⊥ (PyInstaller onedir 자체 포함). dev 모드 ❌ | 배포본은 PyInstaller 산출물로 배포 — 사용자 PC Python 의존 ⊥ |
| AppData 쓰기 권한 ❌ | clinic.db / config.json 생성 실패 → 첫 실행 ❌ | 일반 사용자 권한으로도 `%APPDATA%` 쓰기 가능 (Windows 표준) — 단 회사 PC 보안 정책 차단 시 ❌ |
| 포트 8000 충돌 | 다른 앱 사용 시 서버 시작 실패 | `app/config.py:port` 변경 가능 (`config.json`) — 사용자 안내 |
| 한글/공백 경로 | 빌드본 내부 경로 처리 (`config.py:resource_path` + PyInstaller `_MEIPASS`) — 검증됨 ✅ | 운영 PC 의 사용자 폴더명에 한글 있어도 동작 (검증) |

### 8.2 위험도 중간

| 위험 | 영향 | 완화 |
|---|---|---|
| 방화벽 차단 | LAN 의 다른 PC / 휴대폰 접속 ❌ | Windows Defender 첫 실행 시 *허용* 필요 (사용자 안내) |
| 백업 폴더 권한 | `%APPDATA%\도수치료예약\backups\` 쓰기 ❌ | AppData 권한과 동일 — 보통 OK |
| 브라우저 캐시 | 업데이트 후 옛 JS/CSS 사용 → UI 깨짐 | `?v=APP_VERSION` 자동 무효화 + `Ctrl+Shift+R` 안내 |
| AI API Key 누락 | AI 도우미 외부 LLM 호출 시 503 + 안내 | local-only 모드 (정규식) 로 동작. RAG 매뉴얼 Q&A 만 키 필요 (현재 UI 제거) |

### 8.3 위험도 낮음

| 위험 | 영향 |
|---|---|
| Windows 실행정책 (.ps1) | `dev_run.ps1` 만 영향. `dev_run.bat` 또는 운영 빌드본은 무관 |
| pip 의존성 설치 실패 | 운영 빌드본에서 영향 ⊥ (이미 번들). 개발 PC 만 영향 |
| 환경설정 파일 누락 | `config.json` 미존재 시 첫 실행에서 자동 생성 (`load_config`) |
| 정적파일 누락 | PyInstaller `datas` 자동 포함 — 빠지면 `tests/test_pyinstaller_hidden_imports` 실패 (회귀 가드) |
| 문자나라 설정 누락 | SMS 발송 ❌, 다른 기능 무관. 관리자 → 문자 설정에서 입력 |

## 9. 수정 필요 사항 (수정 ❌ — 보고만)

### 9.1 반드시 수정 (현재 없음)

코드 / 데이터 / 빌드 진입점 / 회귀 가드 모두 정상. 즉시 빌드 가능 상태.

### 9.2 권장 수정 (사용자 동의 시 별도 작업)

1. **`VERSION.txt` 헤더 v1.3.3 → v1.3.4 (또는 v1.3.5) 갱신** — `app/config.py:APP_VERSION = "1.3.4"` 와 4점 정합 ❌ (10 Docs Agent § 6 정합 검사).
2. **`versions/INDEX.txt` 의 최상단 헤드 블록 검증** — Phase A~M + AI 인증 정책 + 도우미 탭 제거 + dev_run.bat / .ps1 추가 등 v1.3.5 변경 사항 미반영 가능성.
3. **CHANGELOG.txt 의 v1.3.5 블록 추가** — 이번 세션 변경 사항 일괄 정리:
   - Phase A~M 디자인 토큰 + 가독성 (`docs/ui/UI_DESIGN_TOKENS.md`)
   - AI 인증 정책 변경 (선택적 admin 토큰)
   - AI 도우미 탭 (RAG Q&A) UI 제거
   - dev_run.bat / .ps1 + run.py `--dev` 자동 시드
   - 비밀번호 변경 권장 알림 fix
   - Codex 외부 검증 워크플로우 + 정리 (CLEANUP_LOG)

### 9.3 나중에 개선

1. AI 도우미 탭 백엔드 (RAG / manual_qa / m012/m013 / knowledge/) 완전 제거 여부 — 사용자 결정
2. `app.css` 4,500줄 다중 정의 정리 (Phase G+ 후속)
3. Codex 호출 시 PowerShell stdin 인코딩 (cp949) — `Get-Content -Encoding UTF8` 명시 권장
4. `docs/agent/` 12 + 인덱스 의 모델 정책 표 갱신 (사용자 정책 통합 후)

## 10. 최종 판정

**판정: 조건부 배포 가능**

이유:
- 코드 / 테스트 / DB / 정적파일 / AI 안전 / 회귀 가드 *모두 통과* — 기능적으로 즉시 빌드 가능
- 단, **§ 9.2 권장 수정** (CHANGELOG / VERSION / INDEX 갱신) 이 4점 버전 정합 누락 — 사용자 측 자동 업데이트 클라이언트가 새 버전 인식 못 할 가능성
- PyInstaller 빌드 / `gh release create` / `clinic-updates` 푸시는 *사용자 명시 동의* 후 (CLAUDE.md 배포 규칙)

---

## 11. 사용자 배포 PC 실행 절차 (최종 사용자용)

> 사용자에게 안내할 *최종 사용자 / 다른 PC 운영자* 용 절차.

### 11.1 PyInstaller 배포본 (도수치료예약.exe 더블클릭)

1. ZIP 다운로드 → 압축 해제 (한글/공백 폴더 OK)
2. `도수치료예약.exe` 더블클릭
3. 첫 실행 시:
   - `%APPDATA%\도수치료예약\` 자동 생성 (clinic.db / config.json)
   - 자동으로 메인 모드 설정
   - 브라우저 자동 열림 (`http://127.0.0.1:8000/`)
   - 바탕화면 바로가기 (`병원 예약 관리.url`) 자동 생성
4. Windows Defender 방화벽 *허용* 클릭 (LAN 접속 시)

### 11.2 접속 주소

- 이 PC: `http://127.0.0.1:8000/`
- 다른 PC / 휴대폰: `http://<LAN-IP>:8000/` (콘솔에 표시)
- 관리자 비번 첫 실행: `admin1234` (즉시 변경 권장)

### 11.3 백업 / DB 위치

- DB: `%APPDATA%\도수치료예약\clinic.db`
- 자동 백업: `%APPDATA%\도수치료예약\backups\`
- 동봉 도구: `tools\백업하기.bat` / `복원하기.bat` / `db점검.bat`

### 11.4 오류 발생 시

| 증상 | 확인 |
|---|---|
| 실행 즉시 종료 | `%TEMP%\도수치료예약_DB점검_log.txt` 확인 |
| 포트 8000 사용 중 | `config.json` 의 `port` 다른 값 (예: 8080) 으로 변경 |
| 다른 PC 접속 ❌ | Windows Defender 방화벽 → "병원 예약 관리" 허용 |
| UI 깨짐 / 옛 화면 | 브라우저에서 `Ctrl+Shift+R` (강력 새로고침) |
| DB 점검 필요 | `tools\db점검.bat` 더블클릭 |

### 11.5 자동 업데이트

- `config.json` 의 `update_manifest_url` 설정 시 `clinic-updates` 매니페스트 자동 체크
- 새 버전 시 ZIP 자동 다운로드 + SHA256 검증 + `updater.bat` 가 본체 교체
- 업데이트 직전 DB 자동 백업 (`clinic_before_update_v*.db`)

---

## 12. Codex 외부 검증

배포 직전 (사용자 명시 시) `docs/codex_reviews/CODEX_REVIEW_GUIDE.md` 절차 따라 Codex 호출.

```powershell
codex.cmd --help    # 사전 확인
Get-Content -Raw "docs\codex_reviews\<TASK>_REQUEST.md" | codex.cmd exec --sandbox read-only --ephemeral --output-last-message "docs\codex_reviews\<TASK>_RESULT.md" -
```

본 빌드테스트 결과는 별도 Codex REQUEST 작성 시 § 7 / § 8 / § 9 를 그대로 인용.
