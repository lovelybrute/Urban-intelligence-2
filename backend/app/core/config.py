"""
Urban Intelligence Platform - Core Configuration
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pydantic import ConfigDict

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_REPO_DIR = os.path.abspath(os.path.join(_BASE_DIR, ".."))
_DB_PATH = os.path.join(_BASE_DIR, "urban_intelligence.db").replace("\\", "/")


def _preferred_weight(custom_name: str, fallback_name: str) -> str:
    custom = os.path.join(_REPO_DIR, "frontend", "ml", "weights", custom_name)
    fallback = os.path.join(_REPO_DIR, "frontend", "ml", "weights", fallback_name)
    return custom if os.path.isfile(custom) else fallback


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="allow")

    # Application
    APP_NAME: str = "UrbanIntelligence"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SEED_DEMO_DATA: bool = True
    SECRET_KEY: str = "dev-secret-key-change-in-production-min-32-chars"

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_DB_PATH}"

    # JWT
    JWT_SECRET_KEY: str = "dev-jwt-secret-key-change-in-production-min-32"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,https://urban-intelligence-2.vercel.app"

    # Edge AI
    EDGE_CONFIDENCE_THRESHOLD: float = 0.5
    EDGE_UPLOAD_INTERVAL_SECONDS: int = 10
    EDGE_MAX_QUEUE_SIZE: int = 1000
    EDGE_DEDUP_RADIUS_METERS: float = 50.0
    EDGE_DEDUP_TIME_WINDOW_SECONDS: int = 3600

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # ML Models
    YOLO_MODEL_PATH: str = _preferred_weight("traffic_india.pt", "traffic_coco.pt")
    ROAD_DEFECT_MODEL_PATH: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "weights", "road_defect_best.pt")
    ANPR_MODEL_PATH: str = os.path.join(_REPO_DIR, "frontend", "ml", "weights", "anpr_plate.pt")
    INFRASTRUCTURE_MODEL_PATH: str = os.path.join(_REPO_DIR, "frontend", "ml", "weights", "infrastructure.pt")

    # Simulator
    SIMULATOR_BUS_COUNT: int = 10
    SIMULATOR_EVENT_INTERVAL_SECONDS: int = 5
    SIMULATOR_CITY: str = "hyderabad"

    # Evidence
    EVIDENCE_DIR: str = "./evidence"
    MAX_EVIDENCE_RETENTION_DAYS: int = 90

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()

