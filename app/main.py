"""FastAPI 앱"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import resource_path
from .database import init_db
from .modules.appointment_series import router as appointment_series_router
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


def create_app() -> FastAPI:
    app = FastAPI(title="도수치료 예약 관리")
    init_db()  # 스키마 버전 체크 + 시드 (seed_defaults)
    app.mount("/static",
              StaticFiles(directory=str(resource_path("app/static"))),
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
    app.include_router(revenue_router)     # daily revenue records and statistics
    set_startup_time()                     # 20-2 F-13: uptime 기준점
    start_sync_worker()
    start_auto_backup()   # 단계 G #18: 시작 시 1회 + 타이머
    return app


app = create_app()
