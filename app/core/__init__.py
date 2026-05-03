"""19-1 단위화 리팩토링 — core 공통 유틸 패키지.

19-P-2 §2-1 V2 트리의 ``app/core/`` 자리. modules 가 공통 참조하는 경계.

NOTE: core 는 modules 를 import 하지 않는다 (D-4 정합 — 단방향 경계).
이 패키지는 19-1 시점에 빈 facade 로 신설된다 — 실제 로직은 ``app/config.py`` /
``app/database.py`` / ``app/services/auth.py`` 에 그대로 두고, core/* 는 re-export
wrapper 와 신규 helper (errors / responses / time_utils / feature_flags) 만 제공.

향후 19-x 코드 세션이 core/ 안 helper 를 사용하기 시작하면 점진적으로 본체를
core 로 이동한다 (TODO(19-x)).
"""
