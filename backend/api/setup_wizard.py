"""Setup wizard API endpoints."""
import logging
import secrets
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/setup", tags=["setup"])


# === REQUEST/RESPONSE MODELS ===

class SetupStatusResponse(BaseModel):
    """Setup status response."""
    is_first_run: bool
    setup_completed: bool


class WorkerConfig(BaseModel):
    """Worker configuration."""
    count: int = Field(default=1, ge=0, le=10, description="Number of workers to start")
    type: str = Field(default="cpu", description="Worker type: cpu or gpu")


class ScannerConfig(BaseModel):
    """Scanner configuration."""
    interval_minutes: int = Field(default=360, ge=1, le=10080, description="Scan interval in minutes")


class StandaloneSetupRequest(BaseModel):
    """Standalone mode setup request."""
    library_paths: List[str] = Field(..., description="Library paths to scan")
    scan_rules: List[dict] = Field(..., description="Initial scan rules")
    worker_config: Optional[WorkerConfig] = Field(default=None, description="Worker configuration")
    scanner_config: Optional[ScannerConfig] = Field(default=None, description="Scanner configuration")

    class Config:
        json_schema_extra = {
            "example": {
                "library_paths": ["/media/anime", "/media/movies"],
                "scan_rules": [
                    {
                        "name": "Japanese to Spanish",
                        "audio_language_is": "jpn",
                        "missing_external_subtitle_lang": "spa",
                        "target_language": "spa",
                        "action_type": "transcribe"
                    }
                ],
                "worker_config": {
                    "count": 1,
                    "type": "cpu"
                },
                "scanner_config": {
                    "interval_minutes": 360
                }
            }
        }


class BazarrSlaveSetupRequest(BaseModel):
    """Bazarr slave mode setup request."""
    pass  # No additional config needed


class BazarrConnectionInfo(BaseModel):
    """Bazarr connection information."""
    mode: str = "bazarr_slave"
    host: str
    port: int
    api_key: str
    provider_url: str


class SetupCompleteResponse(BaseModel):
    """Setup complete response."""
    success: bool
    message: str
    bazarr_info: Optional[BazarrConnectionInfo] = None


# === ROUTES ===

@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status():
    """
    Check if this is the first run or setup is completed.

    Returns:
        Setup status
    """
    from backend.core.settings_service import settings_service

    # Check if setup_completed setting exists
    setup_completed = settings_service.get("setup_completed", None)

    return SetupStatusResponse(
        is_first_run=setup_completed is None,
        setup_completed=setup_completed == "true" if setup_completed else False
    )


@router.post("/standalone", response_model=SetupCompleteResponse)
async def setup_standalone_mode(request: StandaloneSetupRequest):
    """
    Configure standalone mode with library paths and scan rules.

    Args:
        request: Standalone setup configuration

    Returns:
        Setup completion status
    """
    from backend.core.settings_service import settings_service
    from backend.core.database import database
    from backend.scanning.models import ScanRule

    try:
        # Set operation mode
        settings_service.set("operation_mode", "standalone",
                           description="Operation mode",
                           category="general",
                           value_type="string")

        # Set library paths
        library_paths_str = ",".join(request.library_paths)
        settings_service.set("library_paths", library_paths_str,
                           description="Library paths to scan",
                           category="general",
                           value_type="list")

        # Enable scanner by default
        settings_service.set("scanner_enabled", "true",
                           description="Enable library scanner",
                           category="scanner",
                           value_type="boolean")

        # Configure scanner interval if provided
        if request.scanner_config:
            settings_service.set("scanner_schedule_interval_minutes",
                               str(request.scanner_config.interval_minutes),
                               description="Scanner interval in minutes",
                               category="scanner",
                               value_type="integer")
        else:
            # Default: 6 hours
            settings_service.set("scanner_schedule_interval_minutes", "360",
                               description="Scanner interval in minutes",
                               category="scanner",
                               value_type="integer")

        # Configure worker auto-start if provided
        if request.worker_config:
            settings_service.set("worker_auto_start_count",
                               str(request.worker_config.count),
                               description="Number of workers to start automatically",
                               category="workers",
                               value_type="integer")
            settings_service.set("worker_auto_start_type",
                               request.worker_config.type,
                               description="Type of workers to start (cpu/gpu)",
                               category="workers",
                               value_type="string")
        else:
            # Default: 1 CPU worker
            settings_service.set("worker_auto_start_count", "1",
                               description="Number of workers to start automatically",
                               category="workers",
                               value_type="integer")
            settings_service.set("worker_auto_start_type", "cpu",
                               description="Type of workers to start (cpu/gpu)",
                               category="workers",
                               value_type="string")

        # Create scan rules
        with database.get_session() as session:
            for idx, rule_data in enumerate(request.scan_rules):
                rule = ScanRule(
                    name=rule_data.get("name", f"Rule {idx + 1}"),
                    enabled=True,
                    priority=rule_data.get("priority", 10),
                    audio_language_is=rule_data.get("audio_language_is"),
                    audio_language_not=rule_data.get("audio_language_not"),
                    audio_track_count_min=rule_data.get("audio_track_count_min"),
                    has_embedded_subtitle_lang=rule_data.get("has_embedded_subtitle_lang"),
                    missing_embedded_subtitle_lang=rule_data.get("missing_embedded_subtitle_lang"),
                    missing_external_subtitle_lang=rule_data.get("missing_external_subtitle_lang"),
                    file_extension=rule_data.get("file_extension", ".mkv,.mp4,.avi"),
                    action_type=rule_data.get("action_type", "transcribe"),
                    target_language=rule_data.get("target_language", "spa"),
                    quality_preset=rule_data.get("quality_preset", "fast"),
                    job_priority=rule_data.get("job_priority", 5)
                )
                session.add(rule)

            session.commit()

        # Mark setup as completed
        settings_service.set("setup_completed", "true",
                           description="Setup wizard completed",
                           category="general",
                           value_type="boolean")

        logger.info("Standalone mode setup completed successfully")

        return SetupCompleteResponse(
            success=True,
            message="Standalone mode configured successfully"
        )

    except Exception as e:
        logger.error(f"Failed to setup standalone mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup failed: {str(e)}"
        )


@router.post("/bazarr-slave", response_model=SetupCompleteResponse)
async def setup_bazarr_slave_mode(request: BazarrSlaveSetupRequest):
    """
    Configure Bazarr slave mode and generate API key.

    Args:
        request: Bazarr slave setup configuration

    Returns:
        Setup completion status with connection info
    """
    from backend.core.settings_service import settings_service

    try:
        # Set operation mode
        settings_service.set("operation_mode", "bazarr_slave",
                           description="Operation mode",
                           category="general",
                           value_type="string")

        # Generate API key
        api_key = secrets.token_urlsafe(32)
        settings_service.set("bazarr_api_key", api_key,
                           description="Bazarr provider API key",
                           category="bazarr",
                           value_type="string")

        # Enable Bazarr provider
        settings_service.set("bazarr_provider_enabled", "true",
                           description="Enable Bazarr provider mode",
                           category="bazarr",
                           value_type="boolean")

        # Disable scanner (not needed in slave mode)
        settings_service.set("scanner_enabled", "false",
                           description="Enable library scanner",
                           category="scanner",
                           value_type="boolean")

        # Mark setup as completed
        settings_service.set("setup_completed", "true",
                           description="Setup wizard completed",
                           category="general",
                           value_type="boolean")

        # Get host and port from settings
        host = getattr(app_settings, "API_HOST", "0.0.0.0")
        port = getattr(app_settings, "API_PORT", 8000)

        # Create connection info
        bazarr_info = BazarrConnectionInfo(
            mode="bazarr_slave",
            host=host if host != "0.0.0.0" else "127.0.0.1",
            port=port,
            api_key=api_key,
            provider_url=f"http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}"
        )

        logger.info("Bazarr slave mode setup completed successfully")

        return SetupCompleteResponse(
            success=True,
            message="Bazarr slave mode configured successfully",
            bazarr_info=bazarr_info
        )

    except Exception as e:
        logger.error(f"Failed to setup Bazarr slave mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup failed: {str(e)}"
        )


@router.post("/skip")
async def skip_setup():
    """
    Skip setup wizard (for advanced users).

    Returns:
        Success message
    """
    from backend.core.settings_service import settings_service

    settings_service.set("setup_completed", "true",
                       description="Setup wizard completed",
                       category="general",
                       value_type="boolean")

    logger.info("Setup wizard skipped")

    return {"message": "Setup wizard skipped"}

