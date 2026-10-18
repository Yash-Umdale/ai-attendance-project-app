"""
VeriAttend — Centralized Configuration

All configurable thresholds, paths, and secrets are managed here
via environment variables (loaded from .env file).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ── Application ──
    APP_NAME: str = "VeriAttend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── Database ──
    # Default: SQLite in the backend directory
    # For PostgreSQL: postgresql://user:pass@host:port/dbname
    DATABASE_URL: str = "sqlite:///./veriattend.db"

    # ── Authentication ──
    JWT_SECRET_KEY: str = "veriattend-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # ── CORS ──
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Face Recognition ──
    # Euclidean distance threshold for face recognition.
    # Lower = stricter matching. dlib 128D embeddings typically use 0.6.
    RECOGNITION_THRESHOLD: float = 0.6

    # Confidence threshold for attendance decisions.
    # Confidence is calculated as: 1.0 - (distance / RECOGNITION_THRESHOLD)
    # At or above 40%, attendance is auto-approved; lower recognized matches
    # are sent to manual review rather than rejected.
    # Scores are still calculated from the actual face-embedding distance;
    # this setting never increases or fabricates a recognition score.
    CONFIDENCE_HIGH_THRESHOLD: float = 0.40
    # Retained so older .env files continue to load; low recognized matches
    # are all sent to manual review, so this secondary threshold is unused.
    CONFIDENCE_BORDERLINE_THRESHOLD: float = 0.40

    # ── Liveness Verification ──
    # Eye Aspect Ratio threshold for blink detection
    LIVENESS_EAR_THRESHOLD: float = 0.21
    # Minimum consecutive frames with closed eyes to count as blink
    # One closed-eye sample is sufficient because the challenge also requires
    # open eyes before and after closure across separate live camera frames.
    LIVENESS_BLINK_CONSEC_FRAMES: int = 1
    # Head pose yaw angle threshold (degrees) for turn detection
    LIVENESS_HEAD_TURN_THRESHOLD: float = 15.0
    # Liveness challenge timeout in seconds
    LIVENESS_CHALLENGE_TIMEOUT: int = 30
    # Minimum texture variance (Laplacian) to detect printed photos
    LIVENESS_TEXTURE_THRESHOLD: float = 50.0

    # ── Camera / Frame Capture ──
    # Milliseconds between frame captures sent to backend
    CAMERA_SAMPLE_INTERVAL_MS: int = 1500

    # ── Attendance ──
    # If True, prevents marking attendance twice for same student in same session
    PREVENT_DUPLICATE_ATTENDANCE: bool = True

    # ── Model Paths (relative to backend/) ──
    # dlib models are loaded from face_recognition_models package by default
    # Override these only if using custom model files
    DLIB_SHAPE_PREDICTOR_PATH: str = ""
    DLIB_FACE_RECOGNITION_MODEL_PATH: str = ""





# Singleton settings instance
settings = Settings()
