"""FastAPI 앱"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from .config import IS_FROZEN, resource_path
from .database import init_db
from .modules.appointment_series import router as appointment_series_router
from .modules.charts import router as charts_router
from .modules.doctors import router as doctors_router
from .modules.health import router as health_router, set_startup_time
from .modules.inventory import router as inventory_router
from .modules.records import router as records_router
from .modules.revenue import router as revenue_router
from .modules.resources import router as resources_router
from .modules.settlement import router as settlement_router
from .routers import ai as ai_router
from .routers import ai_commands_router
from .routers import ai_harness_router
from .routers import api, pages
from .services.backup import start_auto_backup
from .services.sync import start_sync_worker


class CachedStaticFiles(StaticFiles):
    """정적 자산에 Cache-Control 을 붙이는 StaticFiles.

    배포 환경(IS_FROZEN)에서 ``?v=<버전>`` 쿼리가 붙은 요청은 버전이 바뀌면
    URL 자체가 달라지므로 영구 캐시(immutable)해도 항상 정확하다 → 서브 PC
    로딩이 빨라지고, 업데이트 시엔 새 URL 이라 자동으로 새로 받는다.
    버전 쿼리 없는 자산(favicon 등)이나 dev 실행본은 no-cache 로 둬 항상 최신
    파일을 받게 한다(편집 즉시 반영).
    """

    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        qs = scope.get("query_string", b"")
        has_version = qs.startswith(b"v=") or b"&v=" in qs
        if IS_FROZEN and has_version:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-cache"
        return response


def create_app() -> FastAPI:
    app = FastAPI(title="도수치료 예약 관리")
    init_db()  # 스키마 버전 체크 + 시드 (seed_defaults)
    app.mount("/static",
              CachedStaticFiles(directory=str(resource_path("app/static"))),
              name="static")
    app.include_router(pages.router)
    app.include_router(api.router)
    app.include_router(ai_router.router)   # v1.3: AI/RAG 라우터 (/api/ai/*)
    app.include_router(ai_harness_router.router)   # Phase 6: AI 명령 하네스 (/api/ai/harness/*)
    app.include_router(ai_commands_router.router)  # Post-Phase 11: SSOT § 11 commands (/api/ai/commands/*)
    app.include_router(health_router)      # 20-2 F-13: /api/health (post-19-P)
    app.include_router(doctors_router)     # 20-3-3 F-1 (c): /api/doctors (post-19-P)
    app.include_router(appointment_series_router)  # 20-3-4 F-2: /api/appointment-series
    app.include_router(resources_router)   # 20-3-5 F-3: /api/resources
    app.include_router(settlement_router)  # settlement snapshots and reports
    app.include_router(inventory_router)   # inventory by employee category
    app.include_router(records_router)     # chart/name/employee record tabs
    app.include_router(charts_router)      # 환자 차팅(SOAP 진료기록) /api/charts/*
    app.include_router(revenue_router)     # daily revenue records and statistics
    set_startup_time()                     # 20-2 F-13: uptime 기준점
    start_sync_worker()
    start_auto_backup()   # 단계 G #18: 시작 시 1회 + 타이머
    return app


app = create_app()
