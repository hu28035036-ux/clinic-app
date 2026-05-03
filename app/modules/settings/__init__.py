"""modules.settings — 관리자 설정 / SMS 설정 / AI 설정 직렬화 helper (19-2 후보 구조).

본 패키지는 19-2 시점에 *신설* 되며, 19-12 admin/settings 분리 세션에서 본격적으로
``app/routers/api.py`` 의 ``/api/system-settings`` / ``/api/sms/setting`` 핸들러와
``app/routers/ai.py`` 의 ``/api/ai/settings`` 핸들러를 위임받을 facade 자리다.

19-2 본 세션 범위:
  - **신규 저장소 / 신규 router 추가 ⊥** — 기존 ``api.py`` / ``ai.py`` 핸들러 무수정.
  - 직렬화 helper (``serializers``) 만 신설 — 향후 modules 가 채택할 *순수 함수*.
  - 기존 응답 dict 의 *키 / 타입 / 값 / 마스킹 정책* 100% 보존.

NOTE: ``SystemSetting`` (관리자 시스템 탭) / ``SmsSetting`` (문자나라) /
``AiSetting`` (AI / RAG) 는 모두 *별개의 ORM* 이며 각각의 router 가 별도로 관리.
본 모듈은 이 셋의 직렬화 정책 (마스킹 / boolean 변환 / 기본값) 을 공통 진입점
으로 제공해 19-12 / 19-13 세션이 위임받기 쉽게 한다.

# COMPAT: 19-P-1 §21 의 33+ 응답 키 셋 (DEC-C 절대 원칙) 100% 보존.
#         본 helper 는 *추가만* — 기존 응답 dict 빌드 위치를 *대체* 하지 않는다.

# SAFETY: ``api_key`` / ``munjanara_pw`` / ``munjanara_key`` 원문은 어떤 응답에도
#         포함 ⊥ — 마스킹 helper (``mask_api_key``) 또는 ``api_key_set`` boolean 만.
"""
