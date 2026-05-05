# CLEANUP_LOG

병원예약관리 (도수치료예약, v1.3.4) 프로젝트 폴더 정리 기록.

- 정리 일자: **2026-05-05**
- 정리 사유: 사용자 요청 ("지금까지 만든 프로그램폴더 안에서 사용하지 않는코드, 문서, 정리한번하자. 삭제한 코드,문서는 최상위메인폴더에 문서로 기록한다")
- 정리 범위: 사용자 추가 지시 ("모든내용포함") 에 따라 식별된 모든 후보 삭제 (Tier 1 + Tier 2)
- 회귀 가드: 삭제 항목 모두 `.gitignore` 에 등재 (= git 추적 외부 / 재생성 가능)
- 절대 손대지 않은 영역: `app/`, `tests/`, `docs/`, `tools/`, `knowledge/`, `reports/`, `.git/`, `.github/`, `versions/INDEX.txt`, root 의 `.md` / `.txt` / `.py` / `.bat` / `.json` / `.toml` / `.ini` / `.cfg`, 사용자 데이터 파일 (`*.xlsx`)

---

## 1. 삭제된 항목 전체 목록

### 1.1 가상환경 (broken venv 백업)

| 경로 | 크기 | 사유 |
|---|---|---|
| `venv_broken/` | 151 MB | 폴더명에 "broken" 명시. `.gitignore` 의 `venv_broken*/` 패턴 등재. 운영 venv 는 `venv/` 로 별도 존재. |
| `venv_broken_20260502_111037/` | 151 MB | 2026-05-02 자 broken venv 백업. `.gitignore` 등재. 운영 venv 와 무관. |

### 1.2 빌드 산출물 (PyInstaller)

| 경로 | 크기 | 사유 |
|---|---|---|
| `build/` | 53 MB | PyInstaller 중간 산출. `.gitignore` 의 `build/` 등재. `pyinstaller dosu_clinic.spec` 으로 재생성. |
| `dist/` | 105 MB | PyInstaller 최종 산출 (`dist/도수치료예약/`). `.gitignore` 의 `dist/` 등재. 사용자 동의 후 재빌드 시 다시 생성. GitHub Releases 에 동일 산출 보존. |

### 1.3 과거 버전 백업 폴더

| 경로 | 갯수 | 사유 |
|---|---|---|
| `versions/v1.1.0`, `v1.2.0` ~ `v1.2.18`, `v1.3.1`, `v1.3.2`, `v1.3.3` | 24 폴더 | `.gitignore` 의 `versions/v*/` 등재. GitHub Releases (`hu28035036-ux/clinic-updates`) 에 동일 산출 영구 보존. `versions/INDEX.txt` 는 *보존* 했음 (히스토리 텍스트 인덱스). |

### 1.4 디자인 / 디버그 산출물

| 경로 | 갯수 | 사유 |
|---|---|---|
| `screenshots/addr_chip.png`, `addr_final.png`, `addr_final2.png`, `closing_row.png`, `design_v1.png`, `design_v2.png`, `fix_main.png`, `fix_mobile.png`, `subhead_v1.png`, `subhead_v2.png` | 10 PNG | 디자인 이력 스크린샷. 코드 / 문서 어디서도 참조되지 않음 (`screenshots` 키워드 grep 0건). `.gitignore` 미등재이지만 의미상 작업물. |
| `scripts/debug_ai_helper_user_db.py` | 1 | AI 예약 도우미 흐름 디버깅 (사용자 dev DB). 자기 자신 외 참조 0건. 일회성 디버그 스크립트. |
| `scripts/debug_alias_match.py` | 1 | alias 시드 + 매칭 디버그. 참조 0건. 일회성. |
| `scripts/debug_parse_full_flow.py` | 1 | `commands/parse` 전체 흐름 재현. 참조 0건. 일회성. |

### 1.5 캐시 / 임시 폴더

| 경로 | 사유 |
|---|---|
| `__pycache__/` (root + 하위 40개 디렉토리) | Python 바이트코드 캐시. `.gitignore` 등재. import 시 자동 재생성. `venv/`, `.claude/` 하위는 보존. |
| `.test-build-tmp/` | 빈 폴더. PyInstaller 테스트 빌드 임시. |
| `.tmp.drivedownload/` | 빈 폴더. Google Drive sync 임시. `.gitignore` 등재. |

### 1.6 Claude Code worktree 산출물

| 경로 | 갯수 | 사유 |
|---|---|---|
| `.claude/worktrees/affectionate-wright-2bf4e6`, `amazing-hermann-044fe4`, `gifted-ramanujan-fb28ca`, `happy-diffie-6e3501`, `practical-lalande-0042cc`, `thirsty-joliot-b18f18`, `upbeat-gauss-976297` | 7 worktree | 과거 Claude Code 세션의 worktree 산출 (각 워크트리는 프로젝트 전체 사본 포함, 합계 17 MB). `.gitignore` 의 `.claude/` 등재. 활성 worktree 아님 (모두 git status 와 무관). |

---

## 2. 보류된 항목 → 후속 처리 결과

### 2.1 `.tmp.driveupload/` (재검토 후 삭제 완료)

- 1차 분류: 보류 (활성 Google Drive sync 가능성)
- 재검토 결과: 폴더 mtime 은 갱신됐으나 **내부 파일 2,447개 모두 mtime 이 2026-05-02** — 3일째 stuck 한 업로드 큐로 판정.
- 사용자 "순서대로 진행해" 지시에 따라 삭제 완료 (2026-05-05).
- 회수 디스크: 약 **76 MB**.
- 부작용 가능성: 향후 Google Drive 가 다시 큐를 만들 경우 자동 재생성. 사용자 측에서 Drive sync 클라이언트 재시작 권장.

---

## 3. 절대 손대지 않은 영역 (정리 대상 아님)

다음 항목은 *명백히 활성* 또는 *반드시 보존* 이라 정리 후보에서 제외했습니다:

- `app/` — 운영 코드
- `tests/` — 회귀 테스트 (1955~2142 케이스)
- `docs/` — 활성 문서 (specs, AI, refactor, agent, harnesses, releases, checklists)
- `docs/agent/` — 본 세션에서 신규 작성한 12개 Agent 문서
- `tools/` — 사용자 환경 동봉 도구 (`백업하기.bat`, `복원하기.bat`, `db점검.bat`)
- `knowledge/` — RAG manuals / sms_guides / `_index.json`
- `reports/ai_dev_loop/`, `reports/refactor/` — 과거 Codex review / fix summary / test report 이력 (114개 docs 가 활성 참조)
- `.git/`, `.github/` — 버전 관리 / CI
- `versions/INDEX.txt` — 버전 히스토리 텍스트 인덱스
- `app/migrations/m001` ~ `m020` — DB 마이그레이션 (운영 DB 적용본, 절대 삭제 ❌)
- 모든 root 문서 (`README.md`, `CHANGELOG.txt`, `VERSION.txt`, `BUILD_README.txt`, `CLAUDE.md`, `dosu_clinic.spec`, `pyproject.toml`, `pytest.ini`, `requirements*.txt`, `run.py`, `*.bat`, `자동 업데이트 배포 가이드.txt`, `배포용 사용법 및 안내사항.txt`, `기존 설치 컴퓨터 업데이트 방법.txt`, `⚠ 데이터 안전 안내.txt`)
- 사용자 데이터 (`비트U차트_환자목록_테스트용_80000명.xlsx`)
- `.pytest_cache/`, `.ruff_cache/` — pytest / ruff 캐시 (다음 실행 시 무관)
- `.gitignore`, `.gitattributes`
- `venv/` — 활성 운영 venv

---

## 4. 회귀 안전성

본 정리는 *모두* `.gitignore` 등재 항목 + `versions/v*/` (GitHub Releases 에 동일 보존) + 디자인 이력 + 일회성 디버그 스크립트로 한정. 따라서:

- **소스 코드 변경 ⊥** — `app/`, `tests/`, `docs/`, `scripts/{check_db_path,pytest_loop_10,runtime_verify_live,dummy_seed_and_live_test,seed_dev_dummy,ui_integration_check}.py` 무수정.
- **DB 변경 ⊥** — 운영 DB 미접근. 마이그레이션 무수정.
- **문서 변경 ⊥** — `docs/` 무수정. CHANGELOG / VERSION / INDEX / spec 무수정.
- **빌드 가능성 ⊥** — `dosu_clinic.spec` 무수정. PyInstaller 재실행으로 `dist/` / `build/` 즉시 재생성.
- **테스트 가능성 ⊥** — `tests/conftest.py` 가 `tests/temp/` 격리 폴더만 사용. 캐시 삭제로 인한 영향 ⊥.

---

## 5. 회수 (Recovery)

| 항목 | 회수 방법 |
|---|---|
| `dist/`, `build/` | `venv/Scripts/pyinstaller.exe --noconfirm dosu_clinic.spec` 재실행 |
| `versions/v1.X.Y/` | GitHub Releases (`hu28035036-ux/clinic-updates`) 에서 다운로드 |
| `__pycache__/` | Python import 시 자동 재생성 |
| `screenshots/` | 회수 불가 (디자인 이력) — 다만 코드 / 문서 어디서도 참조되지 않아 영향 없음 |
| `scripts/debug_*.py` | 회수 불가 — 다만 일회성 디버그 스크립트로 동일 기능 필요 시 재작성 가능 |
| `venv_broken*/` | 회수 불필요 (broken 표기) |
| `.claude/worktrees/` | Claude Code 가 새 worktree 필요 시 자동 재생성 |
| `.tmp.drivedownload/`, `.test-build-tmp/` | 회수 불필요 (임시) |

---

## 6. 디스크 회수량 추정

| 항목 | 회수 |
|---|---|
| `venv_broken/` + `venv_broken_20260502_111037/` | ~302 MB |
| `dist/` | ~105 MB |
| `build/` | ~53 MB |
| `.claude/worktrees/` | ~17 MB |
| `versions/v1.X.Y/` × 24 | (개별 크기 미측정 — 각 버전당 수십 MB 규모로 추정) |
| `__pycache__/` × 40+ 디렉토리 | 소량 (~수 MB) |
| `screenshots/` 10 PNG | 소량 |
| `scripts/debug_*.py` 3 파일 | < 100 KB |
| `.tmp.driveupload/` (2,447 stuck 파일) | ~76 MB |
| **합계 (보수 추정)** | **약 580 MB+** |
