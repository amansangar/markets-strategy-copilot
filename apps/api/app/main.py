from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import get_settings
from app.db import get_session, init_db
from app.demo_store import seed_demo_database
from app.models import Symbol
from app.routers.api import dashboard, router, stream_dashboard_snapshot


def _warm_default_dashboard_cache() -> None:
    session = next(get_session())
    try:
        dashboard(mode="demo", symbol="SPY", session=session)
        dashboard(mode="live", symbol="SPY", session=session)
    except Exception:
        # Cache warming must never stop the local API from starting.
        pass
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    session = next(get_session())
    try:
        has_seed_data = session.scalar(select(Symbol.symbol).limit(1)) is not None
        if not has_seed_data:
            seed_demo_database(session)
    finally:
        session.close()
    asyncio.create_task(asyncio.to_thread(_warm_default_dashboard_cache))
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"name": settings.app_name, "docs": "/docs"}


@app.websocket("/ws/market")
async def market_stream(websocket: WebSocket):
    await stream_dashboard_snapshot(websocket)
