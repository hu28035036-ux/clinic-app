"""modules.sms — 문자 / SMS 도메인 후보 구조 (19-10 신규).

19-10 본 세션 범위:
  - **rules.py** : 전화번호 정규화 / 한국 휴대폰 형식 판정 / 마스킹 helper.
    primitives 만 받음 — DB / ORM / 외부 API 미참조.
  - **templates.py** : 도수치료 시간 수치 제거 / 치료 코드 → 문자용 짧은 표시 /
    내일 예약 알림 body 조립. 순수 helper — DB 조회 ⊥ (caller 가 dict 주입).
  - **service.py** : SMS 설정 응답 dict 빌더 (마스킹 적용) / 템플릿 응답 dict 빌더 /
    내일 대상 dict 빌더 / 발송 응답 envelope 빌더 / secret 마스킹 helper.
  - **provider.py** : 외부 발송 provider 인터페이스 + ``FakeSmsProvider`` (테스트 /
    dev 안전 fallback) + ``NotConfiguredProvider``. *실제 외부 발송 ⊥*.
  - **schemas.py** : SMS API 응답 키 contract 상수 (frozenset).

19-10 본 세션 범위 *외* (라우터 본체 / 외부 발송 흐름 무수정):
  - ``app/routers/api.py`` 의 모든 SMS 핸들러 *완전 무수정* — 본 패키지는
    *byte-equivalent helper* 만 제공. 라우터 채택은 19-12+ 시점 점진적.
  - ``/api/sms/send`` 의 실제 ``urllib.request`` 외부 호출 *완전 무수정* —
    본 19-10 가 외부 발송 차단 / 변경 ⊥.
  - 기존 SMS AI (``app/services/ai/sms_draft.py``) 흐름 *완전 무수정* — 사용자
    명시 "기존 SMS AI 동작 변경 금지".
  - DB schema / migration *완전 무수정*.
  - UI / API URL / 응답 key *완전 무수정*.

# COMPAT: 기존 ``app/routers/api.py`` 의 모든 SMS 핸들러 (`/sms/setting` /
#         `/sms/templates` / `/sms/tomorrow-targets` / `/sms/send`) 그대로 동작.
#         본 패키지는 *helper 만* 제공 — 라우터에서 채택 ⊥. 19-10 contract 테스트가
#         라우터 인라인 동작과 본 helper 결과의 byte-equivalent 검증.

# SAFETY: ``provider.py`` 의 기본 provider 는 ``FakeSmsProvider`` — *실제 외부
#         발송 ⊥*. 운영 외부 발송은 라우터의 기존 ``urllib.request`` 흐름이
#         담당 (본 19-10 가 *대체 ⊥*). 본 모듈 import 만으로 외부 API 호출 ⊥.
#         테스트 / dev 환경에서 본 provider 채택 시 실제 발송 차단 보장.

# SAFETY: 문자나라 계정 (``munjanara_id``) / 비밀번호 (``munjanara_pw``) / API
#         인증키 (``munjanara_key``) 는 ``service.serialize_sms_setting_masked``
#         가 *마스킹된 형태로만* 노출. 응답 dict / 로그 / 캐시에 *원문 노출 ⊥*.
#         ``rules.sanitize_secrets`` 가 외부 응답 echo / 예외 메시지에 평문 비밀이
#         섞여 있을 가능성을 차단.

# RISK: 응답 dict 키 변경 ⊥ — UI 가 ``/api/sms/setting`` (8키) /
#       ``/api/sms/templates`` (6키 per item) / ``/api/sms/tomorrow-targets``
#       (8키 per item) / ``/api/sms/send`` (4키 envelope) 응답에 의존. ``schemas.py``
#       의 contract 상수와 19-10 contract 테스트가 회귀 검출.

# NOTE: 19-10 시점 *분리 만*, 라우터 채택 ⊥. 19-12+ 시점에 라우터가 본 helper 호출로
#       전환 — 그 시점에 외부 발송 흐름 (``sms_send``) 도 ``provider.SmsProvider`` 를
#       채택해 테스트 격리 + 실제 발송이 같은 인터페이스를 공유하는 구조 후보.
"""
