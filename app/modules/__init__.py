"""19-2 단위화 리팩토링 — modules 패키지 (도메인별 분리 후보).

19-P-2 §2-1 V2 트리의 ``app/modules/`` 자리. 각 도메인 (settings / health /
appointments / leaves / treatments / patients / staff / sms / stats / admin /
backup / audit / ai / export_import) 의 후보 폴더가 19-x 세션에서 점진적으로
신설된다.

NOTE: modules 는 core 만 참조한다 (D-4 정합 — 단방향 경계 modules → core).
modules 끼리는 *직접 import 금지* — 공통 유틸은 core 에 두고 양쪽이 core 를 참조.

이 패키지는 19-2 시점에 ``settings/`` 와 ``health/`` 후보 구조 만 신설된 상태로
시작한다. 다른 모듈 폴더는 해당 19-x 세션 (19-5 leaves / 19-6 treatments /
19-9 appointments / ...) 에서 신설.
"""
