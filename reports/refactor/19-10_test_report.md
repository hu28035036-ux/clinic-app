# 19-10 sms 분리 — 테스트 리포트

## 환경

- 작업 디렉토리: `C:\Users\user\Desktop\새 폴더\병원예약관리\병원예약관리`
- 브랜치: `ai-rag-v1-integration`
- Python: `venv\Scripts\python.exe` (3.12.10)
- pytest: 8.4.2
- ruff: 프로젝트 설정 (`pyproject.toml` 의 `app/**` per-file-ignores 유지)
- DB: 격리된 `.test-tmp/` 경로 (운영 DB 미참조).

## 실행한 명령

| 명령 | 결과 |
|---|---|
| `venv/Scripts/python.exe -m pytest tests/test_19_10_sms.py -q` | **108 passed** |
| `venv/Scripts/python.exe -m pytest tests -q` | **1233 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **143 passed** |
| `venv/Scripts/python.exe -m pytest tests -k "ai_sms or ai_leave or rag or safety or contract" -q` | **130 passed, 1111 deselected, 21 warnings** |
| `venv/Scripts/python.exe -m ruff check app tests scripts` | **All checks passed!** |
| `venv/Scripts/python.exe scripts/check_db_path.py` | exit 0 |

## 테스트 통과 카운트

- 19-10 전용 contract: **108 passed** (수정 루프 2회).
- 전체 회귀: **1233 passed, 1 skipped, 7 xfailed**. (19-9 통과 시점 1113 → 19-10
  추가 108 + 신규 spec 8 + 신규 19-10 spec 12 = 1233).
- PyInstaller 스펙: **143 passed** (19-10 신규 6개 모듈 등록 검증 12건 추가).
- AI 회귀 (SMS / Leave / RAG / Safety / contract): **130 passed**.

## 자동 수정 루프

- **1회차** : 108 cases 작성 → 104 passed / 4 failed.
  - `test_normalize_phone_byte_equivalent_with_api[(02) 555-1234-0255551234]` :
    내 expected 가 10자 (`0255551234`) 였으나 실제는 9자 (`025551234`). 단순 산수
    오류.
  - `test_is_valid_kr_mobile_byte_equivalent_with_api[0101234567-False]` : api 의
    fallback (`len in (10,11) and digits[0]=="0"` line 3134) 으로 valid — 내 가정
    잘못. 테스트 데이터 보정.
  - `test_normalize_tx_name_for_sms_byte_equivalent_with_api[None-]` : api 가 raw
    name 보존 (`return name` for `not name`) — None 입력에 None 반환. 내 helper 가
    빈 문자열 강제 반환했음. helper 수정 (return type 을 ``str | None`` 로) + 테스트
    expected 도 None 으로 보정.
  - `test_should_skip_password_update[munjanara_key-ABCD****-True]` : api 의
    `startswith("****")` 검사가 `"ABCD****"` 에는 매치 ⊥ — 내 가정 잘못. 테스트
    expected 를 False 로 보정 + NOTE 주석 추가 (api 의 알려진 edge case 명시).
- **2회차** : 108 / 108 passed.

## 핵심 신규 테스트 (108 cases)

### 1. rules — 전화번호 정규화 / 형식 / 마스킹 (32 cases)
- `normalize_phone` 8 parametrize + 라우터 인라인 byte-equivalent 비교.
- `is_valid_kr_mobile` 11 parametrize + 라우터 인라인 비교.
- `mask_phone_for_log` 6 parametrize + 라우터 인라인 비교.
- `sanitize_secrets` 4 케이스 (long secrets / short skip / None handling /
  byte-equivalent).
- `mask_password_for_response` 4 parametrize.
- `mask_api_key_for_response` 4 parametrize.

### 2. templates — 본문 / 치료요약 (15 cases)
- `normalize_tx_name_for_sms` 9 parametrize (None → None 보존, "" → ""
  보존, 도수치료30분 → 도수치료, etc.) + 라우터 인라인 byte-equivalent 비교.
- `format_tx_summary_for_sms` 4 케이스 (정규화 후 중복 제거 / 두 항목 결합 /
  알 수 없는 코드 스킵 / 빈 리스트).
- `build_tomorrow_target_body` 2 케이스 (정상 포맷 + 빈 tx_summary).
- `korean_weekday` 2 케이스 (월요일 / 일요일).

### 3. service — 응답 빌더 (12 cases)
- `serialize_sms_setting_masked` byte-equivalent + 비밀 마스킹 + 빈 비밀 처리.
- `serialize_sms_template` byte-equivalent.
- `build_tomorrow_target_dict` 키 contract + chart_no fallback.
- `build_send_envelope` 키 contract + 전부 성공 / 빈 케이스.
- `collect_missing_setting_fields` 모두 누락 / 모두 채움 / pw 만 비어있음.
- `build_missing_setting_message` 포맷 검증.
- `should_skip_password_update` 11 parametrize.

### 4. provider — FakeSmsProvider 외부 호출 ⊥ (10 cases)
- `FakeSmsProvider` 기록만 하고 합성 성공 반환.
- `FakeSmsProvider.send` 본체에 urllib / requests / httpx 미참조.
- provider.py 모듈 전체 외부 호출 라이브러리 미import.
- 빈 items 처리.
- `ProviderResult.to_dict` 정상 / status_code=None 제외.
- `NotConfiguredProvider` 모든 항목 거부 + 빈 missing 처리.

### 5. schemas — contract 회귀 보호 (4 cases)
- `SMS_SETTING_RESPONSE_KEYS` (7키) / `SMS_TEMPLATE_RESPONSE_KEYS` (6키) /
  `SMS_TOMORROW_TARGET_KEYS` (8키) / `SMS_SEND_ENVELOPE_KEYS` (4키).

### 6. 단방향 경계 D-4 (8 cases)
- `rules.py` / `templates.py` / `service.py` / `provider.py` / `schemas.py`
  가 `app.routers` 미참조.
- `rules.py` / `templates.py` 가 ORM / DB / `sqlalchemy` 미참조.
- `app.modules.sms` 6개 import 가능.

### 7. 라우터 시그니처 무수정 (8 cases)
- `sms_get` / `sms_set` / `sms_tomorrow` / `sms_send` /
  `list_sms_templates` / `create_sms_template` / `update_sms_template` /
  `delete_sms_template` 시그니처 보존.

### 8. SMS AI 흐름 무수정 (1 case)
- `app.services.ai.sms_draft.DraftContext` 존재 검증.

### 9. 기존 SMS API 흐름 영향 없음 (4 cases)
- `GET /api/sms/setting` 응답 키 contract.
- `GET /api/sms/setting` 비밀 / API key 평문 노출 ⊥ (실제 DB 에 secret 주입 후
  응답 본문 검사).
- `GET /api/sms/templates` 항목 키 contract.
- `GET /api/sms/tomorrow-targets` 항목 키 contract.

### 10. SMS send 외부 호출 차단 검증 (1 case)
- `POST /api/sms/send` 가 빈 SMS 설정에서 400 / 401 / 422 (외부 호출 진입 ⊥).

### 11. 외부 호출 라이브러리 미import 검증 (1 case)
- 6개 sms 모듈 파일 모두 `urllib.request` / `requests` / `httpx` import 라인 부재.

## 운영 DB 보호 검사 결과

`scripts/check_db_path.py` exit 0 — 운영 DB 경로 출력만, 실제 접근 ⊥.

## 외부 API 호출 차단 검증

- 본 19-10 신규 모듈 (`rules.py` / `templates.py` / `service.py` / `provider.py` /
  `schemas.py`) 어디에도 `urllib.request` / `requests` / `httpx` import 부재 —
  `test_no_module_imports_urllib_request` 가 검증.
- `FakeSmsProvider` 가 외부 호출 ⊥ (테스트 검증).
- 라우터의 `sms_send` 본체 (외부 호출 포함) 는 *완전 무수정* — 본 19-10 가
  대체 ⊥. 운영 흐름 보존.
- 테스트 중 `POST /api/sms/send` 호출은 시드 SMS 설정 부재로 400 응답 (외부 호출
  진입 전 차단).

## RAG / SMS AI / Leave AI / Safety 회귀

| 테스트 묶음 | 결과 |
|---|---|
| `tests -k "ai_sms"` | 통과 (130 passed 안에 포함) |
| `tests -k "ai_leave"` | 통과 |
| `tests -k "rag or safety"` (RAG 하네스) | 통과 |
| `tests -k "contract"` | 통과 |
| 종합 | **130 passed** |

## 주요 로그 발췌

```
============================= 108 passed in 0.43s =============================
========== 1233 passed, 1 skipped, 7 xfailed, 27 warnings in 12.87s ===========
============================= 143 passed in 0.56s =============================
============== 130 passed, 1111 deselected, 21 warnings in 2.18s ==============
All checks passed!
```

## 결론

- 19-10 신규 contract 108 cases 모두 통과 (수정 루프 2회).
- 전체 회귀 1233 passed.
- ruff / DB 경로 / 기존 SMS AI / 휴무 AI / RAG / 계약 테스트 모두 통과.
- 외부 API 호출 / 문자나라 발송 *없음* — `FakeSmsProvider` + 라우터 본체 무수정.
- 비밀번호 / API key 원문 노출 *없음* — 마스킹 contract 검증 + 실제 응답 본문 검사.
- **19-10 → 19-11 진입 후보** (Codex 검증 후 최종 결정).
