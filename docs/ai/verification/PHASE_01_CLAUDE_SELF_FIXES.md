# PHASE_01_CLAUDE_SELF_FIXES.md

Phase 1 자체 검증 / 작업 중 발견·수정한 내용.

## 수정 1: 테스트 assertion 너무 strict

- **문제**: `test_app_ai_does_not_import_app_services_ai` 가 docstring 텍스트까지 검사하여 `__init__.py` 의 "기존 `app.services.ai` 와 분리" 라는 설명 텍스트에 매칭 → 1 fail.
- **수정**: 정규식으로 `^\s*(from|import)\s+app\.services\.ai` 만 검사하도록 변경 — docstring 언급은 허용.
- **재테스트**: 20/20 통과.

## 수정 2: Ruff `I001` (import 정렬)

- **문제**: `tests/test_phase01_ai_command.py` 의 `from app.ai import ...` 항목이 알파벳 정렬 안 됨 (`AIProvider` 가 `AiCommandStatus` 보다 뒤에 있어야 ruff 가 권장).
- **수정**: `ruff check --fix` 로 자동 정렬.
- **재테스트**: ruff 0 error / pytest 20/20 통과.

## 수정 3 (사전 인지): `MockProvider` Phase 1 동작 범위

- **결정**: Phase 1 의 `MockProvider.parse_command()` 는 단순히 `ParsedCommand(raw_text=raw_text)` 만 반환. 실제 자연어 → JSON 추출은 Phase 2 의 `ai_parser` 가 담당.
- **이유**: Phase 1 범위 (스키마 + provider 추상화 + audit) 만 명확히 분리. Phase 2 가 진짜 parser 구현 시 본 인터페이스 재사용.

## 수정 4 (사전 인지): `ai_audit` 가 sqlite3 직접 받음

- **결정**: Phase 1 의 `write_log` / `update_log` / `get_log` 는 `sqlite3.Connection` 인자를 직접 받음. ORM 또는 service 패턴 미사용.
- **이유**: Phase 1 은 audit 의 최소 동작만 구현. Phase 5 에서 executor 가 호출 시 도메인 service 패턴으로 wrapping 가능.
- **주의**: Phase 5 진입 시 본 인터페이스의 호출 위치 (router / executor) 명확화 필요.

## 미수정 / 향후 점검 (자만 없는 판단)

1. **PyInstaller 빌드 미수행** — `dosu_clinic.spec` 갱신은 빌드 시점에 검증. 사용자 승인 후 빌드로 확인.
2. **운영 DB 마이그레이션 미수행** — m019 / m020 은 in-memory + 단위 테스트만 검증. 운영 DB 마이그레이션은 사용자 환경에서만 동작 (CLAUDE.md 의 "운영 DB 사용 금지" 원칙 따름).
3. **실제 외부 AI API 호출 미검증** — `MockProvider` 만 사용. Anthropic / OpenAI provider 는 Phase 2 에서 실 구현 + 실패 시나리오 테스트.

## 결론

- Phase 1 작업 중 발견된 모든 문제 (수정 1, 2) 는 보완 완료.
- 사전 인지 / 향후 점검 대상 (수정 3, 4 / 미수정 1, 2, 3) 은 Phase 2~5 에서 처리.
- **Phase 2 자동 진행 가능** (자동 진행 조건 만족).
