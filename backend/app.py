"""Main FastAPI application for TranscriptorIO backend."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.core.database import database
from backend.core.worker_pool import WorkerPool
from backend.core.queue_manager import queue_manager
from backend.scanning.library_scanner import library_scanner

# Import API routers
from backend.api.workers import router as workers_router
from backend.api.jobs import router as jobs_router
from backend.api.scan_rules import router as scan_rules_router
from backend.api.scanner import router as scanner_router
from backend.api.settings import router as settings_router
from backend.api.setup_wizard import router as setup_router
from backend.api.system import router as system_router
from backend.api.filesystem import router as filesystem_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global worker pool instance
worker_pool = WorkerPool()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown tasks:
    - Database initialization
    - Worker pool startup (if configured)
    - Library scanner startup (if configured)
    - Graceful shutdown
    """
    # === STARTUP ===
    logger.info("=== TranscriptorIO Backend Starting ===")

    # Initialize database
    logger.info("Initializing database...")
    database.init_db()
    logger.info("Database initialized")

    # Clean up orphaned jobs from previous session
    from backend.core.queue_manager import queue_manager
    try:
        cleaned = queue_manager.cleanup_orphaned_jobs()
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} orphaned job(s) from previous session")
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned jobs: {e}")

    # Initialize default settings if needed
    from backend.core.settings_service import settings_service
    try:
        settings_service.init_default_settings()
        logger.info("Settings initialized")
    except Exception as e:
        logger.warning(f"Could not initialize settings: {e}")

    # Initialize scanner stats from existing jobs if not already set
    try:
        from backend.core.models import Job, JobStatus
        scan_count = settings_service.get('scanner_scan_count')
        if scan_count is None or scan_count == 0:
            # Count completed jobs as an approximation of files scanned
            with database.get_session() as session:
                completed_count = session.query(Job).filter(
                    Job.status == JobStatus.COMPLETED
                ).count()
                if completed_count > 0:
                    settings_service.set('scanner_total_files_scanned', str(completed_count), category='scanner')
                    settings_service.set('scanner_scan_count', '1', category='scanner')  # At least 1 scan happened
                    logger.info(f"Initialized scanner stats from existing jobs: {completed_count} files")
    except Exception as e:
        logger.warning(f"Could not initialize scanner stats: {e}")

    # Start worker pool if configured (and Whisper is available)
    from backend.transcription.transcriber import WHISPER_AVAILABLE
    from backend.core.system_monitor import system_monitor

    cpu_workers = int(settings_service.get("worker_cpu_count", 0))
    gpu_workers = int(settings_service.get("worker_gpu_count", 0))

    # Validate GPU workers - force to 0 if no GPU available
    if gpu_workers > 0 and system_monitor.gpu_count == 0:
        logger.warning(
            f"GPU workers configured ({gpu_workers}) but no GPU detected. "
            "GPU workers will NOT be started. Setting gpu_workers=0."
        )
        gpu_workers = 0
        # Also update the setting to prevent confusion
        settings_service.set("worker_gpu_count", "0")

    if not WHISPER_AVAILABLE:
        if cpu_workers > 0 or gpu_workers > 0:
            logger.warning(
                "Whisper is not installed but workers are configured. "
                "Workers will NOT be started. Install stable-ts or faster-whisper to enable transcription."
            )
    elif cpu_workers > 0 or gpu_workers > 0:
        logger.info(f"Starting worker pool: {cpu_workers} CPU, {gpu_workers} GPU")
        worker_pool.start(cpu_workers=cpu_workers, gpu_workers=gpu_workers)
    else:
        logger.info("No workers configured to start automatically")

    # Start library scanner scheduler (enabled by default)
    scanner_enabled = settings_service.get("scanner_enabled", True)
    if scanner_enabled in (True, "true", "True", "1", 1):
        # Get library paths from settings
        library_paths = settings_service.get("library_paths", "")
        if isinstance(library_paths, list):
            paths = [p.strip() for p in library_paths if p and p.strip()]
        elif isinstance(library_paths, str) and library_paths:
            paths = [p.strip() for p in library_paths.split(",") if p.strip()]
        else:
            paths = []

        if paths:
            interval_minutes = int(settings_service.get("scanner_schedule_interval_minutes", 360))
            logger.info(f"Starting library scanner scheduler (every {interval_minutes} minutes)")
            library_scanner.start_scheduler(interval_minutes=interval_minutes)
        else:
            logger.info("Scanner enabled but no library paths configured - scheduler not started")
    else:
        logger.info("Library scanner scheduler disabled in settings")

    # Start file watcher if configured
    watcher_enabled = settings_service.get("watcher_enabled", False)
    if watcher_enabled in (True, "true", "True", "1", 1):
        library_paths = settings_service.get("library_paths", "")
        if isinstance(library_paths, list):
            watcher_paths = [p.strip() for p in library_paths if p and p.strip()]
        elif isinstance(library_paths, str) and library_paths:
            watcher_paths = [p.strip() for p in library_paths.split(",") if p.strip()]
        else:
            watcher_paths = []

        if watcher_paths:
            logger.info(f"Starting file watcher: {watcher_paths}")
            library_scanner.start_file_watcher(
                paths=watcher_paths,
                recursive=True
            )
        else:
            logger.info("File watcher enabled but no library paths configured")

    logger.info("=== TranscriptorIO Backend Started ===")

    yield

    # === SHUTDOWN ===
    logger.info("=== TranscriptorIO Backend Shutting Down ===")

    # Stop library scanner first (quick operations)
    logger.info("Stopping library scanner...")
    try:
        library_scanner.stop_scheduler()
        library_scanner.stop_file_watcher()
    except Exception as e:
        logger.warning(f"Error stopping scanner: {e}")

    # Stop worker pool with shorter timeout
    logger.info("Stopping worker pool...")
    try:
        worker_pool.stop(timeout=5.0)
    except Exception as e:
        logger.warning(f"Error stopping worker pool: {e}")

    logger.info("=== TranscriptorIO Backend Stopped ===")


# Create FastAPI app
app = FastAPI(
    title="TranscriptorIO API",
    description="AI-powered subtitle transcription service",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure this properly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(workers_router)
app.include_router(jobs_router)
app.include_router(scan_rules_router)
app.include_router(scanner_router)
app.include_router(settings_router)
app.include_router(setup_router)
app.include_router(system_router)
app.include_router(filesystem_router)


# === ROOT ENDPOINTS ===

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
        "workers": len(worker_pool.workers),
        "queue_size": len(queue_manager.get_queued_jobs())
    }


@app.get("/api/status")
async def get_status():
    """
    Get overall system status.

    Returns comprehensive system status including:
    - Worker pool status
    - Queue statistics
    - Scanner status
    """
    pool_stats = worker_pool.get_pool_stats()
    queue_stats = queue_manager.get_queue_stats()
    scanner_status = library_scanner.get_status()

    return {
        "system": {
            "status": "running",
            "uptime_seconds": pool_stats.get("uptime_seconds"),
        },
        "workers": pool_stats,
        "queue": queue_stats,
        "scanner": scanner_status,
    }


# === FRONTEND STATIC FILES ===

# Check if frontend build exists
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"

if frontend_path.exists() and frontend_path.is_dir():
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")

    # Serve index.html for all frontend routes
    @app.get("/")
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str = ""):
        """Serve frontend application."""
        # Don't serve frontend for API routes
        if full_path.startswith("api/") or full_path.startswith("health") or full_path.startswith("docs") or full_path.startswith("redoc") or full_path.startswith("openapi.json"):
            return {"error": "Not found"}

        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))

        return {"error": "Frontend not built. Run: cd frontend && npm run build"}
else:
    # No frontend build - serve API info
    @app.get("/")
    async def root():
        """Root endpoint - API info."""
        return {
            "name": "TranscriptorIO API",
            "version": "1.0.0",
            "status": "running",
            "message": "Frontend not built. Access API docs at /docs"
        }


# Export worker_pool for API access
__all__ = ["app", "worker_pool"]

