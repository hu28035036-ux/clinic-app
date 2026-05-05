# 11_RELEASE_CHECK_AGENT

빌드 가능성 / spec 일관성 / 배포 게이트 검사. *실제 빌드와 배포는 사용자 명시 동의 후* 04/10 Agent 와 협력하여 수행.

---

## 0. 기본 모델 정책

- **기본 모델: sonnet**
- 상위 모델 조건: 배포 전 전체 위험 검토 / 운영 DB · 백업 · AI 안전 포함 최종 판단 → `opusplan` 또는 `opus` 가능.
- haiku 사용: 단순 체크리스트 확인 / spec hidden imports 누락 카운트 정도에만 가능. 빌드 / 배포 결정 자체는 sonnet 이상.

---

## 1. Agent 목적

- 사용자가 "배포해도 돼?" / "빌드 깨질 위험 있어?" / "지금 릴리즈 가능한 상태야?" 라고 물을 때 *반드시 통과해야 할 게이트* 를 자동 점검.
- PyInstaller spec / hidden imports / 마이그레이션 / 백업 / 안전 정책 / 테스트 통과 여부를 종합.
- 사용자 미승인 상태에서 **빌드 / ZIP / Release 생성 / 외부 레포 푸시 금지**.

## 2. 담당 범위

- `dosu_clinic.spec` (PyInstaller 단일 원천)
- `app/config.py:APP_VERSION` ↔ `CHANGELOG.txt` ↔ `VERSION.txt` ↔ `versions/INDEX.txt` 4점 일치
- `tools/백업하기.bat`, `tools/복원하기.bat`, `tools/db점검.bat` (사용자 환경 도구)
- `updater.bat` (자동 업데이트 시 본체 종료 후 파일 교체)
- 외부 레포 게이트 (`hu28035036-ux/clinic-updates`)

## 3. 실제 확인한 관련 파일/모듈

### 3.1 빌드 단일 원천
- `dosu_clinic.spec`:
  - `hiddenimports` = `app.main` / 라우터 / 모든 `app.modules.*` / 모든 `app.services.ai.*` / 모든 `app.ai.*` / 마이그레이션 자동 글롭
  - `_ai_sdk_modules` = openai + anthropic 자동 collect (실패 시 빌드 중단 — v1.3.2 누락 사고 회귀 가드)
  - `excludes` = `tkinter, matplotlib, numpy, pandas, PyQt5, PyQt6` (불필요한 dep 제외)
  - `datas` = `app/templates`, `app/static`, `knowledge/`, `updater.bat`
  - `console=False`, `upx=False` (백신 오탐 방지)
  - 빌드 후처리: `_internal/updater.bat` → 배포 루트 복사
- 빌드 명령:
  ```
  rm -rf build dist/도수치료예약 dist/dosu_clinic_v*.zip
  venv/Scripts/pyinstaller.exe --noconfirm dosu_clinic.spec
  ```
- 결과물: `dist/도수치료예약/도수치료예약.exe` + `_internal/`

### 3.2 사용자 도구 (배포 동봉)
- `tools/백업하기.bat`
- `tools/복원하기.bat`
- `tools/db점검.bat`
- `updater.bat`

### 3.3 외부 자동 업데이트
- 매니페스트 URL: `https://hu28035036-ux.github.io/clinic-updates/manifest.json`
- 배포 레포: `hu28035036-ux/clinic-updates`
- `app/config.py` 의 `update_manifest_url` (사용자 환경 설정)
- `app/services/sync.py` 와 별개 — 본체 업데이트는 `updater.bat` 흐름

### 3.4 회귀 테스트
- `tests/test_pyinstaller_hidden_imports.py` — spec 누락 검사
- `tests/test_migration_spec_discovery.py` — 마이그레이션 자동 글롭
- `tests/test_updater_invocation.py` — updater 호출
- `tests/test_update_log.py` — 업데이트 로그
- `tests/test_db_restore_safety.py` — 복원 안전망
- `tests/test_graceful_shutdown.py` — 정상 종료

## 4. 작업 전 확인사항

1. **사용자 동의 필수** — CLAUDE.md 배포 규칙: PyInstaller 빌드 / ZIP / `gh release create` / `clinic-updates` 푸시 / `versions/v1.2.X/` 백업 폴더 생성 모두 미승인 ❌.
2. `run_check.bat` 통과 여부 (pytest + ruff + DB 안전 검사).
3. § 3.1 / § 3.2 의 단일 원천 4점 일치 (10 Agent § 6 정합).
4. 새 마이그레이션이 spec hidden imports 에 등록 (자동 글롭 + 명시) — `tests/test_pyinstaller_hidden_imports.py` 통과.
5. AI 안전 회귀 (`tests/test_phase06_ai_safety.py`, `tests/test_ai_safety_harness.py`) 통과.
6. 새로 추가된 vendor JS / CSS / data file 이 spec `datas` 에 등록되었는지.
7. **Codex 외부 검증** (배포 직전 필수 — `docs/codex_reviews/CODEX_REVIEW_GUIDE.md`):
   - REQUEST.md 작성 (11 항목) → `codex.cmd exec --sandbox read-only --ephemeral`
   - RESULT.md 9 항목 (판정 / 잘된부분 / 문제점 / 위험변경 / 누락테스트 / 추가제안 / 수정제안 / 수동확인 / 최종의견)
   - Claude 독립 재검토 → 반영 / 미반영 / 보류 분류 → CHANGELOG 기록
   - "반려" / "조건부 승인" 시 빌드 진행 ❌

## 5. 작업 중 금지사항

- 사용자 미동의 상태에서 `pyinstaller` 실행 ❌ (시간 걸리는 작업이고 dist 가 변경됨).
- `gh release create` / `gh release upload` ❌ (사용자 동의 후만).
- 외부 레포 푸시 (manifest.json, README.md) ❌.
- spec 의 `excludes` 에 추가하여 *번들 슬림화* 시도 ❌ — v1.3.2 누락 사고 회귀 위험.
- `console=False` / `upx=False` 변경 ❌ (백신 오탐 회귀).
- AI SDK (openai / anthropic) collect 실패 시 *try/except 로 삼키기* ❌ (spec 주석 단일 원천: 실패 시 즉시 빌드 중단).

## 6. 작업 후 테스트 항목

```
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py tests/test_migration_spec_discovery.py tests/test_updater_invocation.py tests/test_db_restore_safety.py tests/test_graceful_shutdown.py tests/test_update_log.py -v
```

전체 회귀: `run_check.bat`

배포 게이트 (사용자 동의 후만):
- `pyinstaller --noconfirm dosu_clinic.spec` 실행 → `dist/도수치료예약/` 검사
- ZIP 패키징 → SHA256 산출
- `gh release create` (사용자 동의)
- `clinic-updates` 푸시 (사용자 동의)
- `versions/vX.Y.Z/` 백업 폴더 생성 (사용자 동의)

## 7. 보고 형식

```
[릴리즈 게이트]
  ✅ run_check.bat 통과 (또는 실패 사유)
  ✅ APP_VERSION ↔ CHANGELOG ↔ VERSION ↔ versions/INDEX 일치 (또는 불일치 사유)
  ✅ tests/test_pyinstaller_hidden_imports.py 통과
  ✅ tests/test_migration_spec_discovery.py 통과
  ✅ AI 안전 회귀 통과
  ✅ updater.bat / 사용자 도구 동봉 확인
[빌드] (실행 안 함 — 사용자 동의 대기)
[배포] (실행 안 함 — 사용자 동의 대기)
[Open] 사용자 동의 필요 항목 / 누락 게이트
```

## 8. 이 프로젝트에서 특히 주의할 점

- 배포 게이트 우회 절대 금지 — CLAUDE.md "배포 규칙" 단일 원천.
- *여러 fix 를 모아서 한 번에 배포* 가 권장 흐름 (CLAUDE.md). 사소한 수정마다 배포 ❌.
- `dist/도수치료예약/` 경로명에 한글 포함 — Windows 경로 안전성 확인된 상태. 변경 시 재테스트.
- `updater.bat` 위치는 `_internal/` 안이 아니라 *배포 루트* (도수치료예약.exe 와 같은 폴더) 여야 `%~dp0` 경로가 맞음 — spec 후처리가 자동 복사.
- `clinic-updates` 외부 레포는 배포처 — `manifest.json` 의 sha256 / version / notes 가 클라이언트 자동 업데이트의 단일 원천.
- v1.3.2 에서 openai / anthropic SDK 번들 누락 사고 발생 → spec 의 `_ai_sdk_modules` 루프가 회귀 가드. 변경 ❌.
- 사용자 환경에서 *업데이트 적용 시* `%APPDATA%\도수치료예약\` 은 절대 안 건드림 — 본체 폴더 + `_internal/` 만 교체. 회귀 ❌.
