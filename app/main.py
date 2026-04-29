"""FastAPI 앱"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import resource_path
from .database import init_db
from .routers import pages, api, ai as ai_router
from .services.sync import start_sync_worker
from .services.backup import start_auto_backup


def create_app() -> FastAPI:
    app = FastAPI(title="도수치료 예약 관리")
    init_db()  # 스키마 버전 체크 + 시드 (seed_defaults)
    app.mount("/static",
              StaticFiles(directory=str(resource_path("app/static"))),
              name="static")
    app.include_router(pages.router)
    app.include_router(api.router)
    app.include_router(ai_router.router)   # v1.3: AI/RAG 라우터 (/api/ai/*)
    start_sync_worker()
    start_auto_backup()   # 단계 G #18: 시작 시 1회 + 타이머
    return app


app = create_app()
