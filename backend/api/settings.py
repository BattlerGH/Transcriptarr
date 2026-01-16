"""Settings management API routes."""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


# === REQUEST/RESPONSE MODELS ===

class SettingResponse(BaseModel):
    """Setting response model."""
    id: int
    key: str
    value: Optional[str]
    description: Optional[str]
    category: Optional[str]
    value_type: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class SettingUpdateRequest(BaseModel):
    """Setting update request."""
    value: str = Field(..., description="New value (as string)")

    class Config:
        json_schema_extra = {
            "example": {
                "value": "true"
            }
        }


class SettingCreateRequest(BaseModel):
    """Setting create request."""
    key: str = Field(..., description="Setting key")
    value: Optional[str] = Field(None, description="Setting value")
    description: Optional[str] = Field(None, description="Description")
    category: Optional[str] = Field(None, description="Category")
    value_type: Optional[str] = Field("string", description="Value type")

    class Config:
        json_schema_extra = {
            "example": {
                "key": "custom_setting",
                "value": "value",
                "description": "Custom setting description",
                "category": "general",
                "value_type": "string"
            }
        }


class BulkUpdateRequest(BaseModel):
    """Bulk update request."""
    settings: dict = Field(..., description="Dictionary of key-value pairs")

    class Config:
        json_schema_extra = {
            "example": {
                "settings": {
                    "worker_cpu_count": "2",
                    "worker_gpu_count": "1",
                    "scanner_enabled": "true"
                }
            }
        }


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


# === ROUTES ===

@router.get("/", response_model=List[SettingResponse])
async def get_all_settings(category: Optional[str] = Query(None, description="Filter by category")):
    """
    Get all settings or filter by category.

    Args:
        category: Optional category filter (general, workers, transcription, scanner, bazarr)

    Returns:
        List of settings
    """
    from backend.core.settings_service import settings_service

    if category:
        settings = settings_service.get_by_category(category)
    else:
        settings = settings_service.get_all()

    return [SettingResponse(**s.to_dict()) for s in settings]


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str):
    """
    Get a specific setting by key.

    Args:
        key: Setting key

    Returns:
        Setting object

    Raises:
        404: Setting not found
    """
    from backend.core.database import database
    from backend.core.settings_model import SystemSettings

    with database.get_session() as session:
        setting = session.query(SystemSettings).filter(SystemSettings.key == key).first()

        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{key}' not found"
            )

        return SettingResponse(**setting.to_dict())


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(key: str, request: SettingUpdateRequest):
    """
    Update a setting value.

    Args:
        key: Setting key
        request: Update request with new value

    Returns:
        Updated setting object

    Raises:
        404: Setting not found
        400: Invalid value (e.g., GPU workers without GPU)
    """
    from backend.core.settings_service import settings_service
    from backend.core.database import database
    from backend.core.settings_model import SystemSettings
    from backend.core.system_monitor import system_monitor

    value = request.value

    # Validate GPU worker count - force to 0 if no GPU available
    if key == 'worker_gpu_count':
        gpu_count = int(value) if value else 0
        if gpu_count > 0 and system_monitor.gpu_count == 0:
            logger.warning(
                f"Attempted to set worker_gpu_count={gpu_count} but no GPU detected. "
                "Forcing to 0."
            )
            value = '0'

    success = settings_service.set(key, value)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update setting '{key}'"
        )

    # Return updated setting
    with database.get_session() as session:
        setting = session.query(SystemSettings).filter(SystemSettings.key == key).first()

        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{key}' not found"
            )

        return SettingResponse(**setting.to_dict())


@router.post("/bulk-update", response_model=MessageResponse)
async def bulk_update_settings(request: BulkUpdateRequest):
    """
    Update multiple settings at once.

    Args:
        request: Bulk update request with settings dictionary

    Returns:
        Success message
    """
    from backend.core.settings_service import settings_service
    from backend.core.system_monitor import system_monitor

    # Validate GPU worker count - force to 0 if no GPU available
    settings_to_update = request.settings.copy()
    if 'worker_gpu_count' in settings_to_update:
        gpu_count = int(settings_to_update.get('worker_gpu_count', 0))
        if gpu_count > 0 and system_monitor.gpu_count == 0:
            logger.warning(
                f"Attempted to set worker_gpu_count={gpu_count} but no GPU detected. "
                "Forcing to 0."
            )
            settings_to_update['worker_gpu_count'] = '0'

    success = settings_service.bulk_update(settings_to_update)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings"
        )

    logger.info(f"Bulk updated {len(request.settings)} settings")

    return MessageResponse(message=f"Updated {len(request.settings)} settings successfully")


@router.post("/", response_model=SettingResponse, status_code=status.HTTP_201_CREATED)
async def create_setting(request: SettingCreateRequest):
    """
    Create a new setting.

    Args:
        request: Create request with setting details

    Returns:
        Created setting object

    Raises:
        409: Setting already exists
    """
    from backend.core.settings_service import settings_service
    from backend.core.database import database
    from backend.core.settings_model import SystemSettings

    # Check if exists
    with database.get_session() as session:
        existing = session.query(SystemSettings).filter(SystemSettings.key == request.key).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Setting '{request.key}' already exists"
            )

    # Create
    success = settings_service.set(
        key=request.key,
        value=request.value,
        description=request.description,
        category=request.category,
        value_type=request.value_type
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create setting"
        )

    # Return created setting
    with database.get_session() as session:
        setting = session.query(SystemSettings).filter(SystemSettings.key == request.key).first()
        return SettingResponse(**setting.to_dict())


@router.delete("/{key}", response_model=MessageResponse)
async def delete_setting(key: str):
    """
    Delete a setting.

    Args:
        key: Setting key

    Returns:
        Success message

    Raises:
        404: Setting not found
    """
    from backend.core.settings_service import settings_service

    success = settings_service.delete(key)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found"
        )

    logger.info(f"Setting deleted: {key}")

    return MessageResponse(message=f"Setting '{key}' deleted successfully")


@router.post("/init-defaults", response_model=MessageResponse)
async def init_default_settings():
    """
    Initialize default settings.

    Creates all default settings if they don't exist.
    Safe to call multiple times (won't overwrite existing).

    Returns:
        Success message
    """
    from backend.core.settings_service import settings_service

    try:
        settings_service.init_default_settings()
        return MessageResponse(message="Default settings initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize default settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize default settings: {str(e)}"
        )

