"""Scan rules management API routes."""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scan-rules", tags=["scan-rules"])


# === REQUEST/RESPONSE MODELS ===

class ScanRuleConditions(BaseModel):
    """Scan rule conditions."""
    audio_language_is: Optional[str] = Field(None, description="Audio language must be (ISO 639-2)")
    audio_language_not: Optional[str] = Field(None, description="Audio language must NOT be (comma-separated)")
    audio_track_count_min: Optional[int] = Field(None, description="Minimum number of audio tracks")
    has_embedded_subtitle_lang: Optional[str] = Field(None, description="Must have embedded subtitle in language")
    missing_embedded_subtitle_lang: Optional[str] = Field(None, description="Must NOT have embedded subtitle")
    missing_external_subtitle_lang: Optional[str] = Field(None, description="Must NOT have external .srt file")
    file_extension: Optional[str] = Field(None, description="File extensions filter (comma-separated)")


class ScanRuleAction(BaseModel):
    """Scan rule action."""
    action_type: str = Field("transcribe", description="Action type: transcribe or translate")
    target_language: str = Field(..., description="Target subtitle language (ISO 639-2)")
    quality_preset: str = Field("fast", description="Quality preset: fast, balanced, best")
    job_priority: int = Field(0, description="Priority for created jobs")


class ScanRuleCreateRequest(BaseModel):
    """Request to create a scan rule."""
    name: str = Field(..., description="Rule name")
    enabled: bool = Field(True, description="Whether rule is enabled")
    priority: int = Field(0, description="Rule priority (higher = evaluated first)")
    conditions: ScanRuleConditions
    action: ScanRuleAction

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Japanese anime without Spanish subs",
                "enabled": True,
                "priority": 10,
                "conditions": {
                    "audio_language_is": "jpn",
                    "missing_embedded_subtitle_lang": "spa",
                    "missing_external_subtitle_lang": "spa",
                    "file_extension": ".mkv,.mp4"
                },
                "action": {
                    "action_type": "transcribe",
                    "target_language": "spa",
                    "quality_preset": "fast",
                    "job_priority": 5
                }
            }
        }


class ScanRuleUpdateRequest(BaseModel):
    """Request to update a scan rule."""
    name: Optional[str] = Field(None, description="Rule name")
    enabled: Optional[bool] = Field(None, description="Whether rule is enabled")
    priority: Optional[int] = Field(None, description="Rule priority")
    conditions: Optional[ScanRuleConditions] = None
    action: Optional[ScanRuleAction] = None


class ScanRuleResponse(BaseModel):
    """Scan rule response."""
    id: int
    name: str
    enabled: bool
    priority: int
    conditions: dict
    action: dict
    created_at: Optional[str]
    updated_at: Optional[str]


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


# === ROUTES ===

@router.get("/", response_model=List[ScanRuleResponse])
async def get_all_rules(enabled_only: bool = False):
    """
    Get all scan rules.

    Args:
        enabled_only: Only return enabled rules

    Returns:
        List of scan rules (ordered by priority DESC)
    """
    from backend.core.database import database
    from backend.scanning.models import ScanRule

    with database.get_session() as session:
        query = session.query(ScanRule)

        if enabled_only:
            query = query.filter(ScanRule.enabled == True)

        rules = query.order_by(ScanRule.priority.desc()).all()

        return [ScanRuleResponse(**rule.to_dict()) for rule in rules]


@router.get("/{rule_id}", response_model=ScanRuleResponse)
async def get_rule(rule_id: int):
    """
    Get a specific scan rule.

    Args:
        rule_id: Rule ID

    Returns:
        Scan rule object

    Raises:
        404: Rule not found
    """
    from backend.core.database import database
    from backend.scanning.models import ScanRule

    with database.get_session() as session:
        rule = session.query(ScanRule).filter(ScanRule.id == rule_id).first()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scan rule {rule_id} not found"
            )

        return ScanRuleResponse(**rule.to_dict())


@router.post("/", response_model=ScanRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(request: ScanRuleCreateRequest):
    """
    Create a new scan rule.

    Args:
        request: Rule creation request

    Returns:
        Created rule object

    Raises:
        400: Invalid data
        409: Rule with same name already exists
    """
    from backend.core.database import database
    from backend.scanning.models import ScanRule

    with database.get_session() as session:
        # Check for duplicate name
        existing = session.query(ScanRule).filter(ScanRule.name == request.name).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Scan rule with name '{request.name}' already exists"
            )

        # Create rule
        rule = ScanRule(
            name=request.name,
            enabled=request.enabled,
            priority=request.priority,
            # Conditions
            audio_language_is=request.conditions.audio_language_is,
            audio_language_not=request.conditions.audio_language_not,
            audio_track_count_min=request.conditions.audio_track_count_min,
            has_embedded_subtitle_lang=request.conditions.has_embedded_subtitle_lang,
            missing_embedded_subtitle_lang=request.conditions.missing_embedded_subtitle_lang,
            missing_external_subtitle_lang=request.conditions.missing_external_subtitle_lang,
            file_extension=request.conditions.file_extension,
            # Action
            action_type=request.action.action_type,
            target_language=request.action.target_language,
            quality_preset=request.action.quality_preset,
            job_priority=request.action.job_priority,
        )

        session.add(rule)
        session.commit()
        session.refresh(rule)

        logger.info(f"Scan rule created via API: {rule.name} (ID: {rule.id})")

        return ScanRuleResponse(**rule.to_dict())


@router.put("/{rule_id}", response_model=ScanRuleResponse)
async def update_rule(rule_id: int, request: ScanRuleUpdateRequest):
    """
    Update a scan rule.

    Args:
        rule_id: Rule ID to update
        request: Rule update request

    Returns:
        Updated rule object

    Raises:
        404: Rule not found
        409: Name already exists
    """
    from backend.core.database import database
    from backend.scanning.models import ScanRule

    with database.get_session() as session:
        rule = session.query(ScanRule).filter(ScanRule.id == rule_id).first()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scan rule {rule_id} not found"
            )

        # Check for duplicate name
        if request.name and request.name != rule.name:
            existing = session.query(ScanRule).filter(ScanRule.name == request.name).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Scan rule with name '{request.name}' already exists"
                )

        # Update fields
        if request.name is not None:
            rule.name = request.name
        if request.enabled is not None:
            rule.enabled = request.enabled
        if request.priority is not None:
            rule.priority = request.priority

        # Update conditions
        if request.conditions:
            if request.conditions.audio_language_is is not None:
                rule.audio_language_is = request.conditions.audio_language_is
            if request.conditions.audio_language_not is not None:
                rule.audio_language_not = request.conditions.audio_language_not
            if request.conditions.audio_track_count_min is not None:
                rule.audio_track_count_min = request.conditions.audio_track_count_min
            if request.conditions.has_embedded_subtitle_lang is not None:
                rule.has_embedded_subtitle_lang = request.conditions.has_embedded_subtitle_lang
            if request.conditions.missing_embedded_subtitle_lang is not None:
                rule.missing_embedded_subtitle_lang = request.conditions.missing_embedded_subtitle_lang
            if request.conditions.missing_external_subtitle_lang is not None:
                rule.missing_external_subtitle_lang = request.conditions.missing_external_subtitle_lang
            if request.conditions.file_extension is not None:
                rule.file_extension = request.conditions.file_extension

        # Update action
        if request.action:
            if request.action.action_type is not None:
                rule.action_type = request.action.action_type
            if request.action.target_language is not None:
                rule.target_language = request.action.target_language
            if request.action.quality_preset is not None:
                rule.quality_preset = request.action.quality_preset
            if request.action.job_priority is not None:
                rule.job_priority = request.action.job_priority

        session.commit()
        session.refresh(rule)

        logger.info(f"Scan rule updated via API: {rule.name} (ID: {rule.id})")

        return ScanRuleResponse(**rule.to_dict())


@router.delete("/{rule_id}", response_model=MessageResponse)
async def delete_rule(rule_id: int):
    """
    Delete a scan rule.

    Args:
        rule_id: Rule ID to delete

    Returns:
        Success message

    Raises:
        404: Rule not found
    """
    from backend.core.database import database
    from backend.scanning.models import ScanRule

    with database.get_session() as session:
        rule = session.query(ScanRule).filter(ScanRule.id == rule_id).first()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scan rule {rule_id} not found"
            )

        rule_name = rule.name
        session.delete(rule)
        session.commit()

        logger.info(f"Scan rule deleted via API: {rule_name} (ID: {rule_id})")

        return MessageResponse(message=f"Scan rule {rule_id} deleted successfully")


@router.post("/{rule_id}/toggle", response_model=ScanRuleResponse)
async def toggle_rule(rule_id: int):
    """
    Toggle a scan rule enabled/disabled.

    Args:
        rule_id: Rule ID to toggle

    Returns:
        Updated rule object

    Raises:
        404: Rule not found
    """
    from backend.core.database import database
    from backend.scanning.models import ScanRule

    with database.get_session() as session:
        rule = session.query(ScanRule).filter(ScanRule.id == rule_id).first()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scan rule {rule_id} not found"
            )

        rule.enabled = not rule.enabled
        session.commit()
        session.refresh(rule)

        logger.info(f"Scan rule toggled via API: {rule.name} -> {'enabled' if rule.enabled else 'disabled'}")

        return ScanRuleResponse(**rule.to_dict())

