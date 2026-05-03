"""modules.patients — 환자 도메인 후보 구조 (19-7 신규).

19-7 본 세션 범위:
  - **rules.py** : 환자 도메인 규칙 (중복 검사 / 신환 체크 / PII 마스킹 정책 상수).
  - **repository.py** : 환자 row read-only 조회 (DB 호출자 주입, lazy import).
  - **service.py** : ``_patient_to_dict`` / ``_patient_counts_dict`` /
    ``_serialize_patients_bulk`` / ``_apply_patient_counts`` 동등 helper +
    PII 마스킹 helper.

19-7 본 세션 범위 *외* (라우터 / 서비스 본체 무수정):
  - ``app/routers/api.py`` 의 모든 환자 / 예약 / 통계 핸들러 무수정.
  - ``data-convert`` 흐름 (``/api/data-convert/preview`` / ``/apply``) 무수정 — 19-12
    시점 채택 후보 (export_import 분리).
  - AI / RAG / SMS 흐름 무수정.

# COMPAT: 기존 ``app/routers/api.py`` 의 모든 환자 / 메모 흐름 그대로 동작. 본
#         패키지는 *helper 만* 제공 — 라우터에서 채택 ⊥.

# SAFETY: 환자 PII (name / phone / birth_date / chart_no / memo) 는 응답 / 로그 /
#         audit_log / AI prompt / sync payload 에 *원문 노출 ⊥*. 본 패키지의 마스킹
#         helper 는 *로그 / AI prompt / 진단 출력* 용. 운영 응답 dict 는 *기존 구조
#         그대로* (라우터 무수정) — 환자 모달 / 검색 결과는 평문 PII 가 필요한 흐름.

# NOTE: 현재 *환자 PII 평문* 이 응답에 포함되는 흐름은 *기존 동작* (UI 가 환자 정보
#       조회 / 편집 / SMS 발송 대상 추출에 사용). 본 19-7 이 마스킹 정책 변경 ⊥ —
#       마스킹 helper 는 *로그 / AI / 진단* 경계 한정.

# RISK: 환자 PII 가 ``audit_log`` 에 원문으로 들어가면 GDPR / 의료법 위반 위험 —
#       기존 정책 (audit() 시그니처에 환자명만 또는 ID 만 노출) 보존.
"""
