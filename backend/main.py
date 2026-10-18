"""
VeriAttend — FastAPI Application Entry Point

AI-Powered Face Recognition Attendance Platform.

Routes:
    /api/auth         — Teacher authentication (register, login, JWT)
    /api/students     — Student registration and management
    /api/enrollment   — Student-subject enrollment
    /api/recognition  — Face detection and recognition
    /api/liveness     — Liveness verification (passive + challenge-based)
    /api/attendance   — Attendance marking pipeline
    /api/sessions     — Attendance session management
    /api/reviews      — Manual review queue
    /api/admin        — Admin dashboard and reports

API docs available at /docs (Swagger) and /redoc (ReDoc).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config import settings
from models.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──
@asynccontextmanager
async def lifespan(app):
    """Initialize database tables and load ML models on startup."""
    logger.info("Initializing VeriAttend...")
    init_db()
    logger.info("Database tables created/verified.")

    # Pre-load dlib models (takes a few seconds)
    try:
        from services.face_detection import _load_models
        _load_models()
        logger.info("Face detection models loaded.")
    except Exception as e:
        logger.error(f"Failed to load face detection models: {e}")
        logger.warning("Face recognition features will not be available.")

    yield  # Application runs here


# ── Create FastAPI App ──
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "VeriAttend is an AI-powered face recognition attendance platform. "
        "It provides contactless attendance verification through face detection, "
        "liveness verification, and identity recognition with configurable "
        "confidence thresholds and manual review capabilities."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register Routers ──
from routers.auth import router as auth_router
from routers.students import router as students_router
from routers.enrollment import router as enrollment_router
from routers.attendance import router as attendance_router
from routers.sessions import router as sessions_router
from routers.admin import router as admin_router
from routers.liveness import router as liveness_router

app.include_router(auth_router)
app.include_router(students_router)
app.include_router(enrollment_router)
app.include_router(attendance_router)
app.include_router(sessions_router)
app.include_router(admin_router)
app.include_router(liveness_router)


# ── Health Check ──
@app.get("/", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/api/config", tags=["Config"])
def get_public_config():
    """
    Get public configuration values for the frontend.

    Only exposes non-sensitive configuration. Never returns
    JWT secrets, database URLs, or biometric data.
    """
    return {
        "camera_sample_interval_ms": settings.CAMERA_SAMPLE_INTERVAL_MS,
        "liveness_challenge_timeout": settings.LIVENESS_CHALLENGE_TIMEOUT,
        "app_name": settings.APP_NAME,
    }
