# AI 코드 세션 핵심 규칙 (AI_WORKING_RULES)

> 모든 AI/RAG 코드 세션에서 **가장 먼저** 확인. 1~2페이지.
> 절차는 `docs/ai_code_session_protocol.md`, 문서 목차는 `docs/ai_docs_index.md`,
> 상세 설계는 `docs/ai_rag_*` 참조.

대상: v1.3.3 이후 모든 AI/RAG 작업 (`app/services/ai/`, `app/services/rag/`, `app/routers/ai.py`, 신규 RAG/Vector/Chunker 모듈, 관련 테스트/하네스/문서).

---

## 1. 절대 원칙

1. **기존 기능 안정성 최우선** — SMS AI / 휴무 AI / 매뉴얼 Q&A / 관리자 health, 예약·통계·권한 회귀 금지. 회귀 테스트 통과를 머지 전제로.
2. **운영 DB 접근 금지** — `%APPDATA%\도수치료예약\clinic.db`를 코드/테스트에서 직접 열지 않는다. 모든 테스트는 `tests/conftest.py` 격리 경로. `scripts/check_db_path.py` 실패 시 머지 금지.
3. **하네스/테스트 약화 금지** — 격리·시드·가드를 우회하지 않고, 실패 테스트를 `xfail`/`skip`으로 덮지 않는다(원인 수정). `pyproject.toml`의 `app/**` per-file-ignores 유지.
4. **할루시네이션 금지** — LLM 응답이 근거(인용 chunk)와 불일치하면 노출 금지. 답변에는 반드시 근거 동봉. 근거 부족 시 "정보 부족" 응답.
5. **개인정보(PII) 원문 저장/전달 금지** — 환자명/연락처/주민번호류는 LLM 입력·로그·캐시에 원문 부재. `pii.py` + sha256 해시 정책 유지/확장. 디버그·예외 메시지에도 원문 부재.
6. **API 키 로그 저장 금지** — `AiSetting.api_key`, env 키, 헤더 인증값을 어떤 로그/traceback에도 남기지 않는다. 노출 가능성 있으면 마스킹 후 기록.
7. **API 응답 구조 임의 변경 금지** — `app/routers/ai.py` 응답 스키마(필드 키/타입) 후방호환. 추가만 허용, 제거/이름 변경/타입 변경 별도 합의. 계약 테스트로 보호.

---

## 2. Local-First 원칙

> 사용자가 AI에 질문했다고 무조건 외부 API 토큰을 쓰지 않는다.

1. **내부 처리 가능하면 LLM 호출 금지** — DB 조회·고정 템플릿·규칙 매칭으로 답할 수 있는 질문은 호출 0.
2. **외부 API 토큰 최소** — 호출 전에 ① 캐시 ② 로컬 검색 ③ 근거 chunk 확보 ④ 자연어 합성 필수일 때만. 호출 시에도 `max_tokens`·재시도 정책 준수.
3. **Local Answer Composer 우선** — RAG 결과를 LLM 없이 조립해 응답. LLM은 보조.
4. **Embedding은 선택 기능** — 키워드/Local Composer만으로도 동작. 임베딩 미설치/실패에도 RAG는 degrade-gracefully.
5. **`local_only` 모드에서는 LLM/Embedding 호출 금지** — `len(provider.calls) == 0` / `len(embedding_provider.calls) == 0` 단언. 시도 시 명시적 에러 코드 (`docs/ai_rag_error_codes.md`).

---

## 3. 테스트/수정 루프

- **최대 5회**. 1회차 = 테스트 + 분석 + 수정.
- **5회 실패 시**: 부분 수정 즉시 중단 → `reports/ai_dev_loop/latest_failure_report.md` 작성 → 사용자에게 코드 재작성/설계 재검토 보고 후 승인.
- **통과 후 작성**: `latest_test_report.md` / `latest_fix_summary.md` / `latest_codex_review_request.md` + `{SESSION_NAME}_*.md` 보존본.

---

## 4. Codex 검증 게이트

- Claude Code 자체 테스트 통과는 **최종 완료가 아니다**.
- Codex가 `latest_codex_review_request.md`를 시작점으로 쓰되 실제 diff·파일·결과·로그를 **독립적으로** 확인.
- **Codex 검증 통과 전 다음 세션 진입 금지.**

---

## 5. 위반 시

깨진 규칙명을 한국어로 명시 후 사용자에게 보고. 사용자 승인 없이 임의 우회 금지. 머지/배포 중단.
