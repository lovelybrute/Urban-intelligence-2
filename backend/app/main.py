"""
Urban Intelligence Platform - FastAPI Application Entry Point

AI-powered edge + cloud platform that transforms public transport buses
into mobile urban sensing units for smart city intelligence.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
import os

from app.core.config import settings
from app.core.security import get_current_user, require_write
from app.db.session import init_db, close_db, async_session
from app.db.seed import seed_database
from app.api.routes.auth import router as auth_router
from app.api.routes.buses import router as buses_router
from app.api.routes.events import router as events_router
from app.api.routes.traffic import router as traffic_router
from app.api.routes.analytics import (
    alerts_router, roads_router, analytics_router,
    routes_router, system_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle - startup and shutdown."""
    # Startup
    logger.info("🚌 Urban Intelligence Platform starting...")
    await init_db()
    logger.info("✅ Database initialized")

    if settings.APP_ENV == "production":
        if settings.SEED_DEMO_DATA or "dev-" in settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY) < 32:
            raise RuntimeError("Production requires SEED_DEMO_DATA=false and a strong JWT_SECRET_KEY")
    if settings.SEED_DEMO_DATA:
        async with async_session() as session:
            await seed_database(session)

    # Create evidence directory
    os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)

    logger.info(f"🚀 Urban Intelligence Platform ready on port {settings.API_PORT}")

    yield

    # Shutdown
    await close_db()
    logger.info("👋 Urban Intelligence Platform stopped")


# Create FastAPI app
app = FastAPI(
    title="Urban Intelligence Platform",
    description=(
        "AI-powered mobile urban sensing platform that transforms public transport "
        "buses into intelligent city monitoring units. Detects road defects, traffic "
        "congestion, safety incidents, and infrastructure deficiencies."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(buses_router, dependencies=[Depends(get_current_user), Depends(require_write)])
app.include_router(events_router, dependencies=[Depends(get_current_user), Depends(require_write)])
app.include_router(traffic_router, dependencies=[Depends(get_current_user), Depends(require_write)])
app.include_router(alerts_router, dependencies=[Depends(get_current_user), Depends(require_write)])
app.include_router(roads_router, dependencies=[Depends(get_current_user), Depends(require_write)])
app.include_router(analytics_router, dependencies=[Depends(get_current_user), Depends(require_write)])
app.include_router(routes_router, dependencies=[Depends(get_current_user), Depends(require_write)])
app.include_router(system_router, dependencies=[Depends(get_current_user), Depends(require_write)])


@app.get("/", tags=["Root"])
async def root():
    """API root - platform information."""
    return {
        "platform": "Urban Intelligence Platform",
        "version": "1.0.0",
        "description": "AI-powered mobile urban sensing using public transport buses",
        "docs": "/docs",
        "health": "/api/system/health",
    }

from app.api.routes.evidence import router as evidence_router
app.include_router(evidence_router, dependencies=[Depends(get_current_user), Depends(require_write)])
