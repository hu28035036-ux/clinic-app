# 18-8 체크리스트 — 회귀 + PyInstaller 검증 + 배포

> 이 문서는 해당 세션에서 반드시 확인해야 하는 실행 체크리스트다.
> 공통 규칙은 `docs/AI_WORKING_RULES.md`와 `docs/ai_code_session_protocol.md`를 먼저 확인한다.
> 상세 설계는 관련 ai_rag 문서를 참조한다.

**메타**: 목적=18-8 실행 가이드 · 시점=18-8 시작 시 · 독자=Claude Code/Codex/사용자 · 관련=`harnesses/full_harness_plan.md`, `ai_rag_migration_plan.md` §12, `ai_rag_rollout_plan.md` §5, `CLAUDE.md` 배포 규칙 · 결정=릴리스 진입 가능 여부와 빌드/배포 절차 · 비결정=v1.4.x 후속 패치(별도 세션).

## 세션 목표
PyInstaller 빌드 깨짐 없음(hidden import/데이터 동봉/마이그레이션 import) 확인 + 전체 회귀 + 최종 eval. 사용자 명시 승인 후만 빌드/ZIP/Release/manifest.

## 수정 가능 범위
`tests/test_pyinstaller_hidden_imports.py` 신규 · `tests/test_full_harness.py` 보강 · 사용자 승인 후 `app/config.py`(APP_VERSION/BUILD_DATE)·`CHANGELOG.txt`·`VERSION.txt`·`versions/INDEX.txt` · 사용자 승인 후 빌드/ZIP/Release/manifest.

## 수정 금지 범위
`app/services/ai/**`·`app/routers/ai.py` 코드 수정 · DB 마이그레이션 추가 · requirements.txt 변경 · `dosu_clinic.spec` 구조 변경(오타/누락만 허용) · **사용자 승인 없는 빌드/배포**(`CLAUDE.md` 배포 규칙).

## 반드시 지킬 안전 원칙
spec hiddenimports 모두 import 가능(누락 시 런타임 ImportError) · knowledge/ 동봉 확인 · 모든 마이그레이션 idempotent + import 가능 · 운영 DB 미접근 · 사용자 승인 후만 빌드/배포 · ZIP/manifest sha256 일관.

## 외부 API 호출 가능/불가능 여부
**테스트에서 불가능.** 빌드 후 운영 환경 smoke는 별도(사용자 환경).

## FakeProvider / FakeEmbeddingProvider 필요 여부
**둘 다 필수**(전체 회귀 재실행).

## 반드시 실행할 테스트
```
run_check.bat
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py tests/test_full_harness.py -v
venv\Scripts\python.exe -m pytest tests -v
```
+ 최종 eval (`docs/ai_rag_quality_eval_plan.md` §5 합격 기준)

## 완료 조건
- [ ] `run_check.bat` 통과 · 전체 pytest 100% 통과
- [ ] `test_pyinstaller_hidden_imports.py` 통과(spec 모든 hiddenimports import 가능)
- [ ] knowledge/ 동봉 + `collect_data_files('openai')` 정상
- [ ] 마이그레이션 m012/m013/(m014/m015) idempotent + import 가능
- [ ] 최종 eval 합격 · PII 노출 0
- [ ] **사용자 명시 승인 받음**
- [ ] APP_VERSION/CHANGELOG/VERSION/INDEX 갱신
- [ ] PyInstaller 빌드 성공 · ZIP 동봉 파일 모두 포함
- [ ] `gh release create` 성공 · manifest 푸시 + URL 응답 확인
- [ ] `versions/v1.X.Y/` 백업 폴더 생성
- [ ] 5회 이내 통과 · `latest_*_report.md` 3종 작성

## Codex 검증 요청 문서에 꼭 적을 내용
spec hiddenimports 추가 항목 diff, knowledge/ 동봉 경로 = `_MEIPASS/knowledge/` 일치, 마이그레이션 m012~ idempotent + 기존 m001~m011 diff 0, requirements.txt 변경(있다면)과 빌드 영향, ZIP/CHANGELOG/VERSION/manifest sha256 일관, 사용자 승인 시점, 운영 DB 미접근 입증, 후속 세션 권고(있으면).

## 참조해야 할 상세 문서 목록
**공통 베이스 5개**(`AI_WORKING_RULES`, `ai_code_session_protocol`, `ai_docs_index`, `ai_rag_current_state`, 본 체크리스트).
**18-8 추가 참조**: `docs/ai_rag_test_plan.md` 전체 · `docs/ai_rag_migration_plan.md` §12 · `docs/ai_rag_rollout_plan.md` §5 · `docs/ai_rag_quality_eval_plan.md` §5 · `docs/harnesses/full_harness_plan.md` · `CLAUDE.md` (배포 규칙).
