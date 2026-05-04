# 19-10 sms 분리 — Codex 검증 요청

## 1. 세션 이름

`19-10_sms_target_template_provider_boundary` — 문자 / SMS 도메인 후보 helper +
provider stub 분리.

## 2. 작업 목표

`api.py` 의 SMS 핸들러 (`/sms/setting` / `/sms/templates` / `/sms/tomorrow-targets` /
`/sms/send`) 에 인라인 분산된 *대상 추출 / 본문 조립 / 비밀 마스킹 / 응답 빌드*
helper 를 `app/modules/sms/` 후보 구조에 byte-equivalent 로 분리. *외부 발송
흐름 / DB schema / API 응답 key 완전 무수정*. **실제 외부 문자 발송 / 문자나라
자동 발송 구현 ⊥**.

## 3. 변경 파일 목록

신규:
- `app/modules/sms/__init__.py` (48줄)
- `app/modules/sms/rules.py` (174줄)
- `app/modules/sms/templates.py` (144줄)
- `app/modules/sms/service.py` (229줄)
- `app/modules/sms/provider.py` (225줄)
- `app/modules/sms/schemas.py` (106줄)
- `tests/test_19_10_sms.py` (881줄, 108 cases)

수정:
- `dosu_clinic.spec` (+9, hidden imports 6개 모듈 등록)
- `tests/test_pyinstaller_hidden_imports.py` (+7, EXPECTED tuple 6개 추가)

라우터 / DB schema / migration / `app/routers/` 본체 / `app/services/ai/sms_draft.py` —
*무수정*.

## 4. 실제 이동 / 분리한 문자 대상 추출 로직

| api.py 위치 | 본 19-10 helper | byte-equivalent 검증 |
|---|---|---|
| `_get_sms_setting` 본체 | (라우터 inline 그대로 — 본 19-10 분리 ⊥) | — |
| `sms_get` 응답 dict (line 2929~2939) | `service.serialize_sms_setting_masked` | `test_serialize_sms_setting_masked_byte_equivalent_with_api` |
| `sms_set` 비밀 보호 정책 (line 2961~2966) | `service.should_skip_password_update` + `PASSWORD_PROTECTION_KEYS` | `test_should_skip_password_update[*]` |
| `_normalize_phone_for_sms` (line 3115) | `rules.normalize_phone` | `test_normalize_phone_byte_equivalent_with_api[*]` |
| `_is_valid_kr_mobile` (line 3123) | `rules.is_valid_kr_mobile` | `test_is_valid_kr_mobile_byte_equivalent_with_api[*]` |
| `_mask_phone_for_log` (line 3139) | `rules.mask_phone_for_log` | `test_mask_phone_for_log_byte_equivalent_with_api[*]` |
| `_sms_sanitize` (line 3160) | `rules.sanitize_secrets` | `test_sanitize_secrets_byte_equivalent_with_api` |
| `sms_get` 비밀 마스킹 inline (line 2932~2933) | `rules.mask_password_for_response` / `mask_api_key_for_response` | 4 + 4 parametrize |
| `sms_tomorrow` 응답 dict (line 3022~3029) | `service.build_tomorrow_target_dict` (8키) | `test_build_tomorrow_target_dict_keys` |
| `sms_send` 누락 검사 (line 3239~3244) | `service.collect_missing_setting_fields` | `test_collect_missing_setting_fields` |
| `sms_send` 누락 메시지 (line 3247~3248) | `service.build_missing_setting_message` | `test_build_missing_setting_message_format` |
| `sms_send` envelope (line 3442~3445) | `service.build_send_envelope` | `test_build_send_envelope_*` |

## 5. 실제 이동 / 분리한 문자 템플릿 로직

| api.py 위치 | 본 19-10 helper | 검증 |
|---|---|---|
| `_normalize_tx_name_for_sms` (line 2973) | `templates.normalize_tx_name_for_sms` | `test_normalize_tx_name_for_sms_byte_equivalent_with_api[*]` (None 보존 정합 포함) |
| `_format_tx_summary_for_sms` (line 2983) | `templates.format_tx_summary_for_sms` | `test_format_tx_summary_for_sms_basic` |
| `sms_tomorrow` body 조립 (line 3019~3021) | `templates.build_tomorrow_target_body` | `test_build_tomorrow_target_body_format` + 빈 tx_summary |
| `sms_tomorrow` weekdays (line 3008) | `templates.KOREAN_WEEKDAYS` + `korean_weekday(dt)` | `test_korean_weekday` |
| `_serialize_sms_template` (line 3036) | `service.serialize_sms_template` | `test_serialize_sms_template_byte_equivalent_with_api` |

## 6. provider 경계 정리 방식

본 19-10 시점에는 *외부 발송 미구현* — `provider.py` 는 인터페이스 + 안전 fallback
만 정의:

- `SmsProvider` Protocol — caller 가 의존하는 추상 인터페이스 (typing.Protocol).
- `FakeSmsProvider` — 테스트 / dev 안전 fallback. **`urllib` / `requests` /
  `httpx` 미참조** (테스트가 검증). 호출 시 `calls` 에 기록만 + 합성 성공 결과 반환.
- `NotConfiguredProvider` — SMS 설정 미완료 시 명시적 거부 fallback. 모든 항목
  `not_configured` 로 fail.
- `ProviderResult` dataclass — 결과 컨테이너 + `to_dict()` (응답 변환).

운영 외부 발송 (문자나라 호출) 은 `api.py:sms_send` 의 *기존 inline `urllib.request`
흐름이 그대로 담당* — 본 19-10 가 *대체 ⊥*. 19-12+ 시점에 라우터가 본 인터페이스
를 채택할 후보 (TODO 마커).

## 7. compatibility wrapper / 라우터 무수정

- `app/routers/api.py` 본체 *완전 무수정* — 8개 SMS 핸들러 그대로 동작.
- `tests/test_19_10_sms.py` 의 8개 시그니처 테스트가 라우터 함수 서명 무수정 검증.
- 응답 dict 키 / 타입 *완전 보존* — `schemas.py` contract 상수 + 실제 응답 본문
  검사 테스트로 회귀 보호.

## 8. 수정 금지 범위 준수 여부

| 금지 항목 | 준수 |
|---|---|
| 실제 외부 문자 발송 | ✅ FakeSmsProvider + 외부 호출 라이브러리 import 부재 검증 |
| 문자나라 자동 발송 구현 | ✅ provider 는 stub 만 |
| 문자나라 계정/API key 원문 노출 | ✅ 마스킹 contract + 응답 본문 검사 통과 |
| 예약 생성/수정/삭제 변경 | ✅ 19-9 + api.py 본체 무수정 |
| sms 모듈에서 예약 상태 변경 | ✅ ORM 미참조 |
| 예약 API 응답 key 변경 | ✅ contract 검증 통과 |
| 통계 집계 기준 변경 | ✅ 무수정 |
| 환자/치료사/휴무/치료항목 변경 | ✅ 19-3~19-9 모듈 무수정 |
| AI/RAG 변경 | ✅ sms_draft / RAG 무수정 |
| DB schema / migration | ✅ 무수정 |
| UI 디자인 | ✅ 무수정 |
| 운영 DB 접근 | ✅ 미접근 (check_db_path exit 0) |
| 실제 외부 API 호출 | ✅ import 부재 검증 |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✅ 무수정 |

## 9. 기존 API 응답 key 유지 여부

| 응답 | contract 상수 | 검증 |
|---|---|---|
| `GET /api/sms/setting` | `SMS_SETTING_RESPONSE_KEYS` (7키) | `test_sms_get_endpoint_keys_match_contract` |
| `POST /api/sms/setting` | `SMS_SETTING_UPDATE_RESPONSE_KEYS` (1키) | (라우터 무수정) |
| `GET /api/sms/templates` | `SMS_TEMPLATE_RESPONSE_KEYS` (6키) | `test_sms_templates_endpoint_keys_match_contract` |
| `GET /api/sms/tomorrow-targets` | `SMS_TOMORROW_TARGET_KEYS` (8키) | `test_sms_tomorrow_endpoint_no_external_calls` |
| `POST /api/sms/send` | `SMS_SEND_ENVELOPE_KEYS` (4키) | (라우터 무수정 + 외부 호출 차단 검증) |

## 10. 실제 외부 문자 발송 여부

**없음**. 검증:
- `test_no_module_imports_urllib_request` : 6개 sms 모듈 어느 파일도 `urllib.request`
  / `requests` / `httpx` import ⊥.
- `test_fake_provider_no_urllib_used` : `FakeSmsProvider.send` 본체에 외부 호출
  미참조.
- `test_provider_module_top_level_no_external_libs` : `provider.py` 모듈 top-level
  외부 호출 미import.
- `test_sms_send_with_empty_settings_returns_400` : `POST /api/sms/send` 가 빈
  설정에서 400/401/422 응답 — 외부 호출 진입 *전* 차단.

## 11. 문자나라 계정 / API key 원문 노출 여부

**없음**. 검증:
- `test_serialize_sms_setting_masks_password` : ORM 객체에 `supersecret_pw_value` /
  `supersecret_api_key` 주입 후 응답 dict 어디에도 평문 노출 ⊥.
- `test_sms_get_endpoint_does_not_expose_secrets` : 실제 DB 에 `secret_pw_value_19_10` /
  `secret_key_value_19_10` 주입 후 `GET /api/sms/setting` 응답 본문 (text) 에 평문
  노출 ⊥.
- `rules.mask_password_for_response` : ``"****"`` 또는 빈 문자열만 반환.
- `rules.mask_api_key_for_response` : 앞 4자 + ``"****"`` 만 반환.
- `rules.sanitize_secrets` : 외부 응답 / 예외 메시지에서도 4자 이상 비밀 평문
  치환.

## 12. 환자 개인정보 로그 / 응답 노출 여부

- 환자 PII (이름 / 전화 / 차트번호) 응답 dict 는 *기존 동작* 그대로 평문 — UI /
  SMS 발송 흐름 정합. 본 19-10 가 마스킹 정책 변경 ⊥.
- 로그용 마스킹 (`mask_phone_for_log`) 은 별도 helper 로 *로그 / audit 용* —
  운영 응답에 사용 ⊥ (api.py 정합).
- 본 19-10 모듈은 *추가 로깅 ⊥* — 환자 PII 가 신규로 log 에 노출되는 경로 부재.

## 13. 기존 예약 / 통계 / 관리자 영향 여부

- 19-3~19-9 모듈 *무수정*. 예약 / 휴무 / 치료항목 / 환자 / 치료사 흐름 *무수정*.
- 통계 핸들러 *무수정*.
- 관리자 SMS 설정 (`POST /api/sms/setting`) 라우터 본체 *무수정* — 비밀 보호 정책
  helper (`should_skip_password_update`) 만 추가 (라우터 채택 ⊥).

## 14. 운영 DB 보호 여부

`scripts/check_db_path.py` exit 0. 테스트 fixture (`tests/conftest.py`) 가 격리
경로 강제. 본 19-10 모듈은 ORM lazy import 도 *부재* (`templates.py` / `rules.py` /
`schemas.py` 가 ORM 미참조 — 순수 helper).

## 15. 외부 API 호출 여부

**없음**. `urllib.request` / `requests` / `httpx` 어느 모듈도 미import — 단위
테스트가 검증.

## 16. 순환참조 위험 여부

- `rules.py` ORM / DB / 웹 프레임워크 미참조.
- `templates.py` ORM / DB 미참조.
- `service.py` `app.modules.sms.rules` 만 참조.
- `provider.py` `app.modules.sms.service` 함수 안 lazy import (NotConfiguredProvider
  의 build_missing_setting_message 호출).
- `schemas.py` 외부 의존 ⊥ (Final / frozenset 만).
- `app.routers` 미참조 (5개 모듈 모두).

## 17. 주석/문서화 기준 적용 여부

- 6개 신규 파일 모두 docstring (COMPAT / SAFETY / NOTE / RISK 섹션).
- 외부 발송 차단 / 비밀 비노출 / 환자 PII 보호 부분에 SAFETY 주석.
- 문자 대상 추출 / 템플릿 조립 기준에 NOTE 주석.
- FakeSmsProvider / NotConfiguredProvider 에 NOTE.
- `TODO(19-12)` 마커로 향후 라우터 채택 후보 명시.

## 18. 실행한 테스트와 결과

| 명령 | 결과 |
|---|---|
| 19-10 contract | **108 passed** |
| 전체 회귀 | **1233 passed, 1 skipped, 7 xfailed, 27 warnings** |
| PyInstaller 스펙 | **143 passed** |
| AI 회귀 (sms / leave / rag / safety / contract) | **130 passed, 1111 deselected** |
| ruff | **All checks passed!** |
| check_db_path | exit 0 |

## 19. 자동 수정 루프 횟수

**2회**.
- 1회차: 108 cases → 104 passed / 4 failed.
  - 3건 테스트 데이터 보정 (digit count / api fallback / api masking edge case).
  - 1건 helper return type 보정 (None 입력 → None 보존, api 정합).
- 2회차: 108 / 108 passed.

## 20. 다음 세션으로 넘어가도 되는지에 대한 Claude Code 의 자체 판단

**yes**. 근거:

1. 19-10 신규 contract 108 cases 모두 통과 (수정 루프 2회 — 5회 미만).
2. 전체 회귀 1233 passed (19-9 통과 시점 1113 + 19-10 신규 108 + 신규 spec 12 = 1233).
3. ruff / DB 경로 / SMS AI / 휴무 AI / RAG / 계약 회귀 모두 통과.
4. **외부 문자 발송 / 외부 API 호출 부재** — `urllib.request` / `requests` /
   `httpx` import 부재 단위 테스트 + provider stub 검증.
5. **문자나라 계정 / 비밀 / API key 원문 노출 부재** — 마스킹 contract + 실제 응답
   본문 검사 (DB 에 secret 주입 후 응답에 평문 미포함 검증).
6. 라우터 / DB schema / migration / API 응답 key *완전 무수정* (8개 시그니처 +
   응답 키 contract 검증).
7. 19-3 ~ 19-9 모듈 *완전 무수정*.
8. 단방향 경계 (D-4) 보존.
9. 19-11 (stats 통계 집계 분리) 진입 후보.

다만 **Codex 독립 검증 통과** 가 19-11 진입의 필수 게이트.
