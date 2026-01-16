"""Library scanner API routes."""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scanner", tags=["scanner"])


# === REQUEST/RESPONSE MODELS ===

class ScanRequest(BaseModel):
    """Request to scan paths."""
    paths: List[str] = Field(..., description="Paths to scan")
    recursive: bool = Field(True, description="Scan subdirectories")

    class Config:
        json_schema_extra = {
            "example": {
                "paths": ["/media/anime", "/media/movies"],
                "recursive": True
            }
        }


class ScanResult(BaseModel):
    """Scan result summary."""
    scanned_files: int
    matched_files: int
    jobs_created: int
    skipped_files: int
    paths_scanned: List[str]


class ScheduleConfig(BaseModel):
    """Scanner schedule configuration."""
    enabled: bool = Field(..., description="Enable scheduled scanning")
    cron_expression: str = Field(..., description="Cron expression for schedule")
    paths: List[str] = Field(..., description="Paths to scan")
    recursive: bool = Field(True, description="Scan subdirectories")

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "cron_expression": "0 2 * * *",  # Daily at 2 AM
                "paths": ["/media/anime", "/media/movies"],
                "recursive": True
            }
        }


class WatcherConfig(BaseModel):
    """File watcher configuration."""
    enabled: bool = Field(..., description="Enable file watcher")
    paths: List[str] = Field(..., description="Paths to watch")
    recursive: bool = Field(True, description="Watch subdirectories")

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "paths": ["/media/anime", "/media/movies"],
                "recursive": True
            }
        }


class ScannerStatus(BaseModel):
    """Scanner status response."""
    scheduler_enabled: bool
    scheduler_running: bool
    next_scan_time: Optional[str]
    watcher_enabled: bool
    watcher_running: bool
    watched_paths: List[str]
    last_scan_time: Optional[str]
    total_scans: int


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


# === ROUTES ===

@router.get("/status", response_model=ScannerStatus)
async def get_scanner_status():
    """
    Get library scanner status.

    Returns:
        Scanner status information
    """
    from backend.scanning.library_scanner import library_scanner

    status_dict = library_scanner.get_status()

    return ScannerStatus(**status_dict)


@router.post("/scan", response_model=ScanResult)
async def scan_paths(request: Optional[ScanRequest] = None):
    """
    Manually trigger a library scan.

    Args:
        request: Optional scan request with paths. If not provided, uses library_paths from settings.

    Returns:
        Scan result summary
    """
    from backend.scanning.library_scanner import library_scanner
    from backend.core.settings_service import settings_service

    # Use request paths or load from settings
    if request is None:
        library_paths = settings_service.get('library_paths', '')
        # Handle both string (comma-separated) and list types
        if isinstance(library_paths, list):
            paths = [p.strip() for p in library_paths if p and p.strip()]
        elif isinstance(library_paths, str) and library_paths:
            paths = [p.strip() for p in library_paths.split(',') if p.strip()]
        else:
            paths = []
        recursive = True
    else:
        paths = request.paths
        recursive = request.recursive

    if not paths:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No library paths configured. Please configure library_paths in settings."
        )

    logger.info(f"Manual scan triggered via API: {paths}")

    result = library_scanner.scan_paths(
        paths=paths,
        recursive=recursive
    )

    return ScanResult(**result)


@router.post("/scheduler/start", response_model=MessageResponse)
async def start_scheduler(config: Optional[ScheduleConfig] = None):
    """
    Start scheduled scanning.

    Args:
        config: Optional scheduler configuration. If not provided, uses settings from database.

    Returns:
        Success message
    """
    from backend.scanning.library_scanner import library_scanner
    from backend.core.settings_service import settings_service

    try:
        # Use config from request or load from settings
        if config is None:
            # Load interval from database settings (in minutes)
            interval_minutes = settings_service.get('scanner_schedule_interval_minutes', 360)  # Default: 6 hours
            interval_minutes = int(interval_minutes) if interval_minutes else 360
        else:
            # Convert cron to interval (simplified - just use 360 minutes for now)
            interval_minutes = 360

        if interval_minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid scanner interval. Must be greater than 0 minutes."
            )

        library_scanner.start_scheduler(interval_minutes=interval_minutes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    logger.info(f"Scheduler started via API with interval: {interval_minutes} minutes")

    return MessageResponse(message=f"Scheduler started successfully (every {interval_minutes} minutes)")


@router.post("/scheduler/stop", response_model=MessageResponse)
async def stop_scheduler():
    """
    Stop scheduled scanning.

    Returns:
        Success message
    """
    from backend.scanning.library_scanner import library_scanner

    library_scanner.stop_scheduler()

    logger.info("Scheduler stopped via API")

    return MessageResponse(message="Scheduler stopped successfully")


@router.post("/watcher/start", response_model=MessageResponse)
async def start_watcher(config: Optional[WatcherConfig] = None):
    """
    Start file watcher.

    Args:
        config: Optional watcher configuration. If not provided, uses settings from database.

    Returns:
        Success message
    """
    from backend.scanning.library_scanner import library_scanner
    from backend.core.settings_service import settings_service

    # Use config from request or load from settings
    if config is None:
        library_paths = settings_service.get('library_paths', '')
        # Handle both string (comma-separated) and list types
        if isinstance(library_paths, list):
            paths = [p.strip() for p in library_paths if p and p.strip()]
        elif isinstance(library_paths, str) and library_paths:
            paths = [p.strip() for p in library_paths.split(',') if p.strip()]
        else:
            paths = []
        recursive = True
    else:
        paths = config.paths
        recursive = config.recursive

    if not paths:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No library paths configured. Please configure library_paths in settings."
        )

    library_scanner.start_file_watcher(
        paths=paths,
        recursive=recursive
    )

    logger.info(f"File watcher started via API: {paths}")

    return MessageResponse(message="File watcher started successfully")


@router.post("/watcher/stop", response_model=MessageResponse)
async def stop_watcher():
    """
    Stop file watcher.

    Returns:
        Success message
    """
    from backend.scanning.library_scanner import library_scanner

    library_scanner.stop_file_watcher()

    logger.info("File watcher stopped via API")

    return MessageResponse(message="File watcher stopped successfully")


@router.post("/analyze", response_model=dict)
async def analyze_file(file_path: str):
    """
    Analyze a single file.

    Args:
        file_path: Path to file to analyze

    Returns:
        File analysis result

    Raises:
        400: Invalid file path
        404: File not found
    """
    from backend.scanning.file_analyzer import FileAnalyzer
    import os

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}"
        )

    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path is not a file: {file_path}"
        )

    analyzer = FileAnalyzer()

    try:
        analysis = analyzer.analyze(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze file: {str(e)}"
        )

    return analysis.to_dict()

