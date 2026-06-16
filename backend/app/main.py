"""FastAPI 应用入口。同时托管后端 API 与前端静态页面。"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import moderation, posts, publish, rewrite, schedule
from .scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="公众号写作助手", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts.router)
app.include_router(rewrite.router)
app.include_router(publish.router)
app.include_router(moderation.router)
app.include_router(schedule.router)


@app.on_event("startup")
def _startup():
    init_db()
    start_scheduler()


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---- 前端静态托管 ----
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
