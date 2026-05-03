# 18-1 체크리스트 — RAG/Knowledge/Vector 폴더 구조 생성

> 이 문서는 해당 세션에서 반드시 확인해야 하는 실행 체크리스트다.
> 공통 규칙은 `docs/AI_WORKING_RULES.md`와 `docs/ai_code_session_protocol.md`를 먼저 확인한다.
> 상세 설계는 관련 ai_rag 문서를 참조한다.

**메타**: 목적=18-1 실행 가이드 · 시점=18-1 시작 시 · 독자=Claude Code/Codex/사용자 · 관련=`ai_rag_architecture_plan.md`, `ai_rag_decision_record.md`, `harnesses/component_harness_matrix.md` · 결정=신규 폴더/모듈 골격과 등록 범위 · 비결정=각 모듈 내부 로직(18-2 이후).

## 세션 목표
`app/services/ai/{rag,knowledge,vector}/` 빈 폴더 골격을 만든다. schemas / source_builder / query_normalizer / query_parser / intent_router / safety / prompts의 **인터페이스만** 도입. 실제 동작 변경 0.

## 수정 가능 범위
신규 모듈 stub 생성 · `dosu_clinic.spec` hidden import 등록 · `tests/test_rag_intent_router.py`·`test_rag_query_normalizer.py` 신규.

## 수정 금지 범위
기존 `app/services/ai/manual_qa.py`/`provider.py`/`pii.py`/`rag/search.py` 수정 · 라우터 · DB 마이그레이션 · requirements.txt · 응답 키.

## 반드시 지킬 안전 원칙
신규 stub은 외부 호출 0. `Source` dataclass 키가 v1.3.3 응답 (`title/path/snippet`)과 1:1 매핑. PyInstaller hidden import 누락 금지. 운영 DB 미접근.

## 외부 API 호출 가능/불가능 여부
**불가능.** 모든 신규 모듈은 외부 호출 0.

## FakeProvider / FakeEmbeddingProvider 필요 여부
**불필요(검증용 conftest 시드는 유지).** 18-1은 외부 호출 경로를 만들지 않는다. 호출되면 fail하도록 conftest 기본 시드로만 보호.

## 반드시 실행할 테스트
```
run_check.bat
venv\Scripts\python.exe -m pytest tests/test_rag_intent_router.py tests/test_rag_query_normalizer.py tests/test_full_harness.py tests/test_ai_manual_qa.py -v
```

## 완료 조건
- [ ] `run_check.bat` 통과
- [ ] 기존 모든 테스트 100% 통과 (회귀 0)
- [ ] 신규 stub 모듈 모두 import 성공
- [ ] `dosu_clinic.spec` hiddenimports에 신규 15+ 항목 등록
- [ ] `Source`/`Answer` dataclass가 v1.3.3 응답 키를 보존
- [ ] 5회 이내 통과
- [ ] `latest_*_report.md` 3종 작성

## Codex 검증 요청 문서에 꼭 적을 내용
신규 모듈 목록 + 라인 수, hiddenimports 추가 항목 diff, Source/Answer dataclass 필드, intent_router 6개 분기 정의 위치, 기존 코드 0 diff 입증, 다음 세션(18-2) 진입 yes/no.

## 참조해야 할 상세 문서 목록
**공통 베이스 5개**(`AI_WORKING_RULES`, `ai_code_session_protocol`, `ai_docs_index`, `ai_rag_current_state`, 본 체크리스트).
**18-1 추가 참조**: `docs/ai_rag_architecture_plan.md` §2 §3 · `docs/ai_rag_error_codes.md` · `docs/ai_rag_decision_record.md` · `docs/harnesses/component_harness_matrix.md`.
