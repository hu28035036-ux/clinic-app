# 19-10 sms 분리 — 변경 요약

## 세션 이름

`19-10_sms_target_template_provider_boundary` — 문자 / SMS 도메인 후보 helper +
provider stub 분리. 라우터 본체 / 외부 발송 흐름 *완전 무수정*.

## 작업 목표 (한 문장)

`api.py` 의 SMS 핸들러 (`/sms/setting` / `/sms/templates` / `/sms/tomorrow-targets` /
`/sms/send`) 에 인라인 분산된 *대상 추출 / 본문 조립 / 비밀 마스킹 / 응답 빌드*
helper 를 `app/modules/sms/` 후보 구조에 byte-equivalent 로 분리. *외부 발송
흐름 / DB schema / API 응답 key 완전 무수정*.

## 변경 파일 목록

| 파일 | 변경 종류 | 줄 수 |
|---|---|---:|
| `app/modules/sms/__init__.py` | 신규 | 48 |
| `app/modules/sms/rules.py` | 신규 | 174 |
| `app/modules/sms/templates.py` | 신규 | 144 |
| `app/modules/sms/service.py` | 신규 | 229 |
| `app/modules/sms/provider.py` | 신규 | 225 |
| `app/modules/sms/schemas.py` | 신규 | 106 |
| `tests/test_19_10_sms.py` | 신규 (108 cases) | 881 |
| `dosu_clinic.spec` | 수정 (+9) | — |
| `tests/test_pyinstaller_hidden_imports.py` | 수정 (+7) | — |

## 파일별 변경 요약

### `app/modules/sms/__init__.py` (신규, 48줄)

패키지 docstring — 19-10 본 세션 범위 / 범위 외 / COMPAT / SAFETY / NOTE / RISK +
`TODO(19-12)` 마커 (라우터 채택 후보).

### `app/modules/sms/rules.py` (신규, 174줄)

순수 helper (DB / ORM / 외부 API 미참조).

- **전화번호 정규화** : `normalize_phone(raw)` — `api.py:_normalize_phone_for_sms`
  (line 3115) byte-equivalent.
- **형식 판정** : `is_valid_kr_mobile(digits)` — `api.py:_is_valid_kr_mobile`
  (line 3123) byte-equivalent.
- **로그 마스킹** : `mask_phone_for_log(phone)` — `api.py:_mask_phone_for_log`
  (line 3139) byte-equivalent.
- **비밀 마스킹 (echo / 예외)** : `sanitize_secrets(text, secrets)` —
  `api.py:_sms_sanitize` (line 3160) byte-equivalent (4자 미만 스킵 / None 처리).
- **응답용 비밀 마스킹** : `mask_password_for_response(value)` /
  `mask_api_key_for_response(value)` — `api.py:sms_get` (line 2932~2933) 정합.

### `app/modules/sms/templates.py` (신규, 144줄)

문자 본문 / 치료요약 빌더 (DB 미참조).

- `KOREAN_WEEKDAYS` 상수 + `korean_weekday(dt)`.
- `normalize_tx_name_for_sms(name)` — `api.py:_normalize_tx_name_for_sms` 정합
  (None 입력 → None 보존, raw 보존 정합).
- `format_tx_summary_for_sms(codes, treatments_by_code)` —
  `api.py:_format_tx_summary_for_sms` (line 2983) byte-equivalent.
- `build_tomorrow_target_body(...)` — `api.py:sms_tomorrow` body 조립 (line
  3019~3021) byte-equivalent.

### `app/modules/sms/service.py` (신규, 229줄)

응답 dict 빌더 + 누락 검사 helper.

- `serialize_sms_setting_masked(setting)` — `api.py:sms_get` (line 2929~2939)
  byte-equivalent (비밀 마스킹 적용).
- `serialize_sms_template(template)` — `api.py:_serialize_sms_template`
  (line 3036) byte-equivalent.
- `build_tomorrow_target_dict(...)` — `api.py:sms_tomorrow` 항목 dict 정합 (8키).
- `build_send_envelope(items, results)` — `api.py:sms_send` envelope (line 3442)
  정합 (sent / failed / total / results 4키).
- `build_missing_setting_message(missing)` — 한국어 사용자 노출 메시지.
- `collect_missing_setting_fields(setting)` — `api.py:sms_send` (line 3239~3244)
  누락 검사 정합.
- `should_skip_password_update(key, value)` — `api.py:sms_set` (line 2961~2966)
  비밀 보호 정책 정합 + `PASSWORD_PROTECTION_KEYS` 상수.

### `app/modules/sms/provider.py` (신규, 225줄)

외부 발송 provider 추상 인터페이스 + Fake / NotConfigured 구현.

- `ProviderResult` dataclass — 발송 결과 (5필드 + `to_dict()` 메서드).
- `SmsProvider` Protocol — 추상 인터페이스.
- `FakeSmsProvider` — 테스트 / dev 안전 fallback. *외부 호출 ⊥*. `calls` 리스트로
  호출 인자 검증.
- `NotConfiguredProvider` — SMS 설정 미완료 시 fallback. 모든 항목 `not_configured`
  거부.
- `ProviderNotConfiguredError` / `ProviderExternalCallProhibitedError` 예외.
- **외부 호출 라이브러리 미참조** — `urllib` / `requests` / `httpx` import ⊥.

### `app/modules/sms/schemas.py` (신규, 106줄)

응답 키 contract 상수 (frozenset).

- `SMS_SETTING_RESPONSE_KEYS` (7키), `SMS_SETTING_UPDATE_RESPONSE_KEYS` (1키).
- `SMS_TEMPLATE_RESPONSE_KEYS` (6키), `SMS_TEMPLATE_DELETE_RESPONSE_KEYS` (1키).
- `SMS_TOMORROW_TARGET_KEYS` (8키).
- `SMS_SEND_ENVELOPE_KEYS` (4키), `SMS_SEND_RESULT_REQUIRED_KEYS` (4키).

### `tests/test_19_10_sms.py` (신규, 881줄)

108 cases — contract 검증.

1. rules — 전화 정규화 / 형식 / 마스킹 (라우터 인라인 byte-equivalent 비교 포함).
2. templates — 본문 / 치료요약 빌더.
3. service — 응답 빌더 + 누락 검사 + 비밀 보호 정책.
4. provider — FakeSmsProvider 외부 호출 ⊥ + NotConfiguredProvider.
5. schemas — contract 회귀 보호.
6. 단방향 경계 D-4.
7. 라우터 8개 핸들러 시그니처 무수정.
8. SMS AI (sms_draft) 흐름 무수정 검증.
9. 기존 SMS API 응답 키 contract + 비밀 평문 노출 ⊥ (실제 DB 주입 후 응답 본문 검사).
10. `POST /api/sms/send` 가 빈 설정에서 외부 호출 진입 차단 (400/401/422).
11. 외부 호출 라이브러리 import 부재 검증.

### `dosu_clinic.spec` (수정, +9줄)

`hidden` 리스트에 19-10 신규 6개 모듈 등록:

```
'app.modules.sms',
'app.modules.sms.rules',
'app.modules.sms.templates',
'app.modules.sms.service',
'app.modules.sms.provider',
'app.modules.sms.schemas',
```

### `tests/test_pyinstaller_hidden_imports.py` (수정, +7줄)

`EXPECTED_19_X_MODULES_MODULES` 에 6개 모듈 추가 — spec 등록 + import 가능성 검증.

## 의도 / 이유

- **byte-equivalent 분리** : SMS 핸들러 응답 dict / 비밀 마스킹 / 본문 조립 /
  치료요약 / 누락 검사 / 비밀 보호 정책이 `api.py` 안에 인라인으로 분산되어 있음.
  19-12+ 라우터 채택 시점에 본 helper 가 채택될 후보.
- **외부 발송 차단 보장** : `FakeSmsProvider` 는 `urllib` / `requests` / `httpx`
  완전 미참조 — 본 모듈 import 만으로 외부 발송 사고 ⊥. 테스트 격리.
- **비밀 정보 보호** : `serialize_sms_setting_masked` 가 비밀번호 / API key 원문
  노출 ⊥. `sanitize_secrets` 가 외부 응답 echo / 예외 메시지에서도 평문 비밀
  마스킹.
- **계약 회귀 보호** : `schemas.py` 의 contract 상수가 응답 키 셋 *임의 변경* 검출.
  UI / SMS / 통계 의존 키 보호.
- **라우터 / 외부 발송 무수정** : `api.py:sms_send` 의 `urllib.request` 외부 호출
  본체 *완전 무수정* — 운영 발송 흐름 보존.
- **D-4 경계 보존** : `rules.py` / `templates.py` 는 ORM / DB 미참조, `service.py` /
  `provider.py` 도 `app.routers` 미참조. lazy import.

## compatibility wrapper / 라우터 무수정

- `app/routers/api.py` 본체 *완전 무수정* — 모든 SMS 핸들러 그대로 동작.
- `tests/test_19_10_sms.py` 의 8개 시그니처 테스트가 라우터 함수 서명 무수정
  검증.
- 응답 dict 키 / 타입 *완전 보존*.

## 수정 금지 범위 준수

| 금지 항목 | 준수 |
|---|---|
| 실제 외부 문자 발송 | ✅ FakeSmsProvider + urllib import 부재 |
| 문자나라 자동 발송 구현 | ✅ provider 는 stub / fallback 만 |
| 문자나라 계정/API key 원문 노출 | ✅ 마스킹 contract + 응답 본문 검사 |
| 예약 생성/수정/삭제 변경 | ✅ 라우터 무수정 |
| sms 모듈에서 예약 상태 변경 | ✅ ORM 미참조 (rules/templates), service 도 read-only |
| 예약 API 응답 key 변경 | ✅ schemas contract 보호 |
| 통계 집계 기준 변경 | ✅ 무수정 |
| 환자/치료사/휴무/치료항목 변경 | ✅ 19-3~19-9 모듈 무수정 |
| AI/RAG 변경 | ✅ sms_draft / RAG 무수정 |
| DB schema / migration | ✅ 무수정 |
| UI 디자인 | ✅ 무수정 |
| 운영 DB 접근 | ✅ 미접근 |
| 실제 외부 API 호출 | ✅ urllib/requests/httpx import 부재 |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✅ 무수정 |

## 자동 수정 루프 횟수

**2회**.
- 1회차: 108 cases → 104 passed / 4 failed.
  - `(02) 555-1234` digits 9자 (내 expected 10자 잘못).
  - `0101234567` (10자 0 시작) 는 valid (api fallback) — 내 가정 잘못.
  - `normalize_tx_name_for_sms(None)` → None 보존 (api 정합) — 내 helper 가
    빈 문자열 반환했음. helper return type `str | None` 로 보정.
  - `("munjanara_key", "ABCD****")` → False (api 의 `startswith("****")` 에 매치 ⊥) —
    내 가정 잘못.
- 2회차: 108 / 108 passed.

## 5회 실패 여부

**미해당** — 2회차 통과.

## 위반 / 우회 없음

- `pyproject.toml` per-file-ignores 무수정.
- 운영 DB 직접 open 없음.
- 외부 API 호출 없음 (FakeSmsProvider + import 부재 검증).
- 문자나라 계정 / API key / 비밀번호 원문 노출 없음 (마스킹 contract + 실제 응답 검사).
- `app.routers` 본체 무수정.
- DB schema / migration 무수정.
