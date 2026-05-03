# 18-7 체크리스트 — 라우터/UI 통합 + API 계약 테스트

> 이 문서는 해당 세션에서 반드시 확인해야 하는 실행 체크리스트다.
> 공통 규칙은 `docs/AI_WORKING_RULES.md`와 `docs/ai_code_session_protocol.md`를 먼저 확인한다.
> 상세 설계는 관련 ai_rag 문서를 참조한다.

**메타**: 목적=18-7 실행 가이드 · 시점=18-7 시작 시 · 독자=Claude Code/Codex/사용자 · 관련=`ai_rag_rollout_plan.md` §7 §8, `harnesses/rag_harness_plan.md`, `ai_rag_test_plan.md` · 결정=라우터 pipeline 통합과 관리자 UI 노출 · 비결정=PyInstaller 빌드(18-8).

## 세션 목표
신규 RAG pipeline을 라우터에 통합. `/api/ai/status` 확장(chunk/vector 카운트, 검색 모드, AI 모드, flag, 최근 로그). 관리자 UI에 모든 상태/토글/Reindex 노출. 응답 키 9개 보존 + 신규 optional 키 5개 추가.

## 수정 가능 범위
`app/routers/ai.py` (pipeline 통합·`/status`·`/reindex`) · `app/templates/main.html` 관리자 탭 · `app/static/css/app.css` · `app/services/ai/health.py` · 신규 테스트 (`test_ai_contract_manual`, `test_ai_health_status`, `test_admin_ui_smoke`) · (필요 시) m015 — AiSetting 신규 컬럼.

## 수정 금지 범위
응답 9개 키 변경(추가만 허용·이름/타입/제거 금지) · 일반 직원에 admin 화면 노출 · API key 화면 표시(등록 여부만) · AI 로그 원문 PII 표시 · 기존 마이그레이션 수정 · requirements.txt.

## 반드시 지킬 안전 원칙
계약 테스트로 응답 키 회귀 0 · admin 권한 강제(`/reindex`, `/status` 상세) · API key/원문 PII 화면·로그 부재 · pipeline 통합 후에도 v1.3.3 동작 100% 유지 · `local_only` 모드 노출 + 동작.

## 외부 API 호출 가능/불가능 여부
**테스트에서 불가능.** 운영에서는 사용자 토글에 따라.

## FakeProvider / FakeEmbeddingProvider 필요 여부
**둘 다 필수.** 모든 분기(success/no_result/safety/error) 시뮬레이션.

## 반드시 실행할 테스트
```
run_check.bat
venv\Scripts\python.exe -m pytest tests/test_ai_contract_manual.py tests/test_ai_health_status.py tests/test_admin_ui_smoke.py tests/test_full_harness.py -v
```
+ 관리자 UI 수동 확인(preview)

## 완료 조건
- [ ] `run_check.bat` 통과 · 기존 모든 테스트 100% 통과
- [ ] 응답 키 9개 보존 + 신규 optional 키 5개(`reason_code`/`llm_called`/`embedding_called`/`ai_mode`/`prompt_version`)
- [ ] `/api/ai/reindex` 일반 403, admin 200
- [ ] 관리자 UI에 chunk/vector 카운트·마지막 reindex·실패 목록·AI 모드·flag·최근 로그·Reindex 버튼·prompt_version 노출
- [ ] AI 로그에 원문 PII 부재(수동 확인) · API key 미노출
- [ ] 5회 이내 통과 · `latest_*_report.md` 3종 작성

## Codex 검증 요청 문서에 꼭 적을 내용
계약 테스트 위치 + 단언 항목, 신규 optional 키 모두 optional 입증, admin 권한 체크 위치, 관리자 UI 표시 항목 vs `rollout_plan §7` 매핑, API key/PII 미노출 입증, pipeline 통합 후 v1.3.3 동작 동등 입증, m015 idempotent(있다면), 다음 세션(18-8) 진입 yes/no.

## 참조해야 할 상세 문서 목록
**공통 베이스 5개**(`AI_WORKING_RULES`, `ai_code_session_protocol`, `ai_docs_index`, `ai_rag_current_state`, 본 체크리스트).
**18-7 추가 참조**: `docs/ai_rag_architecture_plan.md` §5 · `docs/ai_rag_test_plan.md` §4-3 · `docs/ai_rag_rollout_plan.md` §7 §8 · `docs/ai_rag_error_codes.md` §6 · `docs/harnesses/rag_harness_plan.md`.
