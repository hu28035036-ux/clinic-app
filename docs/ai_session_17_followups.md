# 세션 17 — AI/RAG v1 후속 보강 작업 노트

작업일: 2026-04-30
범위: 16 세션 (AI Action Leave v1) 후속 보강 항목 #2, #3, #4
브랜치: ai-rag-v1-integration

## 적용 변경 요약

| ID | 항목 | 우선순위 | 결과 |
|---|---|---|---|
| #3 | EmployeeLeave (employee_id, leave_date) UNIQUE 제약 | Medium | ✅ m011 마이그레이션 + 모델 + 테스트 3건 |
| #4 | AiUsageLog.outcome 길이 확장 (20→50) | Low | ✅ Python only (모델 + ai_logging) + 회귀 테스트 1건 |
| #2 | /api/ai/health/public 엔드포인트 분리 | Medium | ✅ admin/public 라우트 + 프론트 + 테스트 3건 |

테스트 결과: 175 → **182 passed** · ruff 0 errors · 운영 DB 마이그레이션 검증 완료

## ⚠️ m011 운영자 안내 (배포 시점)

m011 은 **파괴적 마이그레이션** 이다. 본 프로젝트의 표준 원칙 (DROP/DELETE 금지) 의
**의도적 정책 예외** 이며, 다음을 충족할 때만 row 를 삭제한다:

- 동일 `(employee_id, leave_date)` 그룹 내 row 가 2건 이상 존재
- 그룹 내에서 `(created_at DESC, id DESC)` 최상위 1건만 보존, 나머지 삭제

### 배포 전 운영자 안내 (CHANGELOG / 업데이트 노트에 명시 필요)

> **v1.3.3 업데이트 시 주의사항 (m011)**:
> 같은 직원·같은 날짜에 휴무가 중복 등록된 경우, 가장 최근 등록 1건만 남기고
> 나머지가 자동 정리됩니다. 정상적으로 운영 중이라면 중복은 없을 것이지만,
> 안전을 위해 업데이트 적용 전 `%APPDATA%\도수치료예약\clinic.db` 를 별도
> 위치로 백업해 두는 것을 권장합니다. (프로그램 자동 백업은 매일 1회
> `backups/` 에 보관됨)

### 사후 추적 (지원 문의 시 참고)

m011 은 다음 정보를 stderr 로 로깅한다 (uvicorn / PyInstaller exe 콘솔):
1. `중복 그룹 N개 발견` — 사전 카운트
2. `삭제 대상 K건 (id, employee_id, leave_date, created_at):` — 삭제될 row 의 풀
   레코드 (id 포함) 가 stderr 에 한 줄씩 출력됨. 사후에 어떤 row 가 사라졌는지
   100% 식별 가능.
3. `정리 후에도 중복 그룹 N개 잔존 — 인덱스 생성 실패 예상` — 정상 흐름이면
   이 라인은 없음. 있다면 정리 SQL 의 가정 위반 신호.

## #4 outcome 길이 — 스키마 정합성 노트

m008 마이그레이션이 `outcome VARCHAR(20)` 으로 컬럼을 생성했고, v1.3.3 부터
모델은 `String(50)` 으로 선언된다. **m008 자체는 수정하지 않는다** (한 번
배포된 마이그레이션 수정 금지 원칙).

근거:
- SQLite 의 `VARCHAR(N)` 은 길이를 강제하지 않으며 내부적으로 TEXT 로 저장됨
- 실제 truncate 는 `app/services/ai/ai_logging.py:107` 의 Python 슬라이스
  `(outcome or "")[:50]` 에서만 발생
- 따라서 모델 선언과 m008 의 VARCHAR(20) 이 표면적으로 다르더라도, 실 DB 동작은
  String(50) 정책과 일치한다

PostgreSQL 등 길이를 강제하는 RDBMS 로 이전하게 되는 시점에는 별도 m012 (또는
당시 다음 ID) 마이그레이션으로 ALTER COLUMN ... TYPE VARCHAR(50) 적용이 필요하다.
현 시점에서는 모델 코멘트로만 정합성 의도를 명시한다 (`app/models/models.py:328` 근처).

## venv 진단 결과 (외부 리뷰 #2)

외부 리뷰에서 `.\venv\Scripts\python.exe --version` 실행 실패가 보고되었으나,
본 작업 환경 (Git Bash) 에서는 정상 동작 확인:
- Python 3.12.10
- pytest 8.4.2
- 마이그레이션 자동 발견 + 적용 정상 (m001~m011)

원인 정리: PowerShell/cmd 환경의 cp949 콘솔 인코딩 + 한글 경로 (`병원예약관리`)
조합 이슈로, venv 자체의 깨짐 아님. **사용자 결정 (2026-05-01): 외부 리뷰어
환경의 인코딩 이슈로 정리하고 venv 재생성하지 않음.** 향후 동일 보고가 재차
들어오면 그때 재생성 검토.

## 미진행 (다음 세션 또는 배포 단계)

### v1.3.3 배포 체크리스트 (사용자 승인 시 순서대로 실행)

> **외부 리뷰 (Medium #1) 재확인:** m011 은 파괴적 마이그레이션이므로 운영
> 적용 전 백업이 필수. 아래 Step 0 (백업) 을 건너뛰지 말 것.

0. **[필수] 운영 DB 사전 백업**
   - `%APPDATA%\도수치료예약\clinic.db` 를 별도 위치로 수동 복사
     (예: `Desktop\backup_v1.3.2_pre_m011_YYYYMMDD.db`).
   - 자동 백업(`%APPDATA%\도수치료예약\backups\`) 은 매일 1회 도므로 직전
     24h 백업이 이미 있지만, 추가로 수동 백업 1부를 별도 위치에 보관.
   - 운영 노트에 백업 파일명·일시·해시를 기록.
1. **spec hiddenimports 보강**: `dosu_clinic.spec` 에
   `app.services.ai.action_leave`, `app.services.ai.date_resolver` 추가
   (글롭에 미포함된 모듈).
2. **버전 갱신**:
   - `app/config.py` APP_VERSION 1.3.2 → 1.3.3
   - CHANGELOG.txt / VERSION.txt / versions/INDEX.txt 에 v1.3.3 블록 추가
     (변경사항: m011 UNIQUE 제약 + outcome 50자 + /health/public)
3. **빌드**: PyInstaller `dosu_clinic.spec` → `dist/도수치료예약/`
4. **패키징**: ZIP 생성
5. **릴리스**: `gh release create` 로 GitHub Release 생성
6. **매니페스트 push**: `clinic-updates/manifest.json` (version/sha256/notes)
   + `clinic-updates/README.md` 에 "v1.3.3 업데이트 시 주의사항" 추가
   - 운영자가 업데이트 적용 전 위 Step 0 (백업) 을 수행하도록 README 에 명시
7. **사후 점검**: 첫 사용자가 업데이트 적용 후 stderr 로그 (uvicorn / exe
   콘솔) 확인 — `[MIGRATE m011] 중복 그룹 N개 발견` 이 보이면 삭제 대상
   id 목록도 함께 출력됨. 정상 환경이면 이 로그 없음.

### 영구 보류 또는 다음 세션 이월

- **#1 / #5 항목** (rate limit, 동명이인 라디오 선택 UI, 토큰 만료 카운트다운):
  영향 매우 낮음, 다음 세션 이월
