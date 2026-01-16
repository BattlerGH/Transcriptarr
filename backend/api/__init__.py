"""API module for TranscriptorIO backend."""
from backend.api.workers import router as workers_router
from backend.api.jobs import router as jobs_router
from backend.api.scan_rules import router as scan_rules_router
from backend.api.scanner import router as scanner_router
from backend.api.settings import router as settings_router
from backend.api.setup_wizard import router as setup_router

__all__ = [
    "workers_router",
    "jobs_router",
    "scan_rules_router",
    "scanner_router",
    "settings_router",
    "setup_router",
]

