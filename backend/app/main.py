"""CarSoul Guardian - FastAPI application entrypoint.

Run locally:
    cd backend
    uvicorn app.main:app --reload --port 8000

The app boots even without PostgreSQL (SQLite dev fallback) and without an
LLM key (agent service degrades to a rule-based responder).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Bootstrap paths + logging as early as possible.
import app  # noqa: F401  (ensures ai-agent path is on sys.path)
from app.api import api_router
from app.core.config import settings
from app.database import init_db
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting CarSoul Guardian backend [{}]", settings.ENVIRONMENT)
    logger.info("Effective DB: {}", settings.effective_database_url)
    try:
        init_db()
        logger.info("Database initialised (tables created if missing).")
    except Exception as exc:  # noqa: BLE001
        logger.warning("init_db skipped (DB unavailable): {}", exc)
    # 主动巡检调度器：让"主动守护"名副其实。
    # APScheduler 未安装时优雅降级为手动巡检，不阻塞启动。
    from app.services.scheduler import init_scheduler
    try:
        init_scheduler()
    except Exception as exc:  # noqa: BLE001
        logger.warning("主动巡检调度器初始化跳过: {}", exc)
    yield
    # 应用退出时关闭调度器，避免后台线程泄漏。
    from app.services.scheduler import shutdown_scheduler
    try:
        shutdown_scheduler()
    except Exception as exc:  # noqa: BLE001
        logger.debug("调度器关闭异常: {}", exc)
    logger.info("CarSoul Guardian backend shutting down.")


app = FastAPI(
    title="CarSoul Guardian API",
    description=(
        "基于 AI Agent 的智能汽车生命周期守护系统 — 后端接口。\n\n"
        "AI 汽车私人管家 + 车辆数字生命档案 + 主动式汽车健康管理系统。"
    ),
    version="0.6.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "CarSoul Guardian",
        "version": "0.6.0",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "healthy", "service": "carsoul-guardian-backend"}
