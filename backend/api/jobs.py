"""Job management API routes."""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.core.models import JobStatus, QualityPreset

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# === REQUEST/RESPONSE MODELS ===

class JobCreateRequest(BaseModel):
    """Request to create a new job."""
    file_path: str = Field(..., description="Full path to the media file")
    file_name: str = Field(..., description="Name of the file")
    source_lang: Optional[str] = Field(None, description="Source language (ISO 639-2)")
    target_lang: str = Field(..., description="Target subtitle language (ISO 639-2)")
    quality_preset: str = Field("fast", description="Quality preset: fast, balanced, best")
    transcribe_or_translate: str = Field("transcribe", description="Operation: transcribe or translate")
    priority: int = Field(0, description="Job priority (higher = processed first)")
    is_manual_request: bool = Field(True, description="Whether this is a manual request")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "/media/anime/Attack on Titan S04E01.mkv",
                "file_name": "Attack on Titan S04E01.mkv",
                "source_lang": "jpn",
                "target_lang": "spa",
                "quality_preset": "fast",
                "transcribe_or_translate": "transcribe",
                "priority": 10
            }
        }


class JobResponse(BaseModel):
    """Job response model."""
    id: str
    file_path: str
    file_name: str
    job_type: str = "transcription"  # Default to transcription for backward compatibility
    status: str
    priority: int
    source_lang: Optional[str]
    target_lang: Optional[str]
    quality_preset: Optional[str]
    transcribe_or_translate: str
    progress: float
    current_stage: Optional[str]
    eta_seconds: Optional[int]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    output_path: Optional[str]
    segments_count: Optional[int]
    error: Optional[str]
    retry_count: int
    worker_id: Optional[str]
    vram_used_mb: Optional[int]
    processing_time_seconds: Optional[float]
    model_used: Optional[str]
    device_used: Optional[str]


class JobListResponse(BaseModel):
    """Job list response with pagination."""
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int


class QueueStatsResponse(BaseModel):
    """Queue statistics response."""
    total_jobs: int
    queued: int
    processing: int
    completed: int
    failed: int
    cancelled: int


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


# === ROUTES ===

@router.get("/", response_model=JobListResponse)
async def get_jobs(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
):
    """
    Get list of jobs with optional filtering and pagination.

    Args:
        status_filter: Filter by job status (queued/processing/completed/failed/cancelled)
        page: Page number (1-based)
        page_size: Number of items per page

    Returns:
        Paginated list of jobs
    """
    from backend.core.queue_manager import queue_manager

    # Validate status filter
    status_enum = None
    if status_filter:
        try:
            status_enum = JobStatus(status_filter.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    # Get jobs
    jobs = queue_manager.get_all_jobs(
        status_filter=status_enum,
        limit=page_size,
        offset=(page - 1) * page_size
    )

    # Get total count
    total = queue_manager.count_jobs(status_filter=status_enum)

    return JobListResponse(
        jobs=[JobResponse(**job.to_dict()) for job in jobs],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/stats", response_model=QueueStatsResponse)
async def get_queue_stats():
    """
    Get queue statistics.

    Returns:
        Queue statistics
    """
    from backend.core.queue_manager import queue_manager

    stats = queue_manager.get_queue_stats()

    return QueueStatsResponse(**stats)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Get a specific job by ID.

    Args:
        job_id: Job ID

    Returns:
        Job object

    Raises:
        404: Job not found
    """
    from backend.core.database import database
    from backend.core.models import Job

    with database.get_session() as session:
        job = session.query(Job).filter(Job.id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        job_dict = job.to_dict()

    return JobResponse(**job_dict)


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(request: JobCreateRequest):
    """
    Create a new transcription job.

    Args:
        request: Job creation request

    Returns:
        Created job object

    Raises:
        400: Invalid quality preset
        409: Job already exists for this file
    """
    from backend.core.queue_manager import queue_manager

    # Validate quality preset
    try:
        quality = QualityPreset(request.quality_preset.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid quality preset: {request.quality_preset}"
        )

    # Create job
    job = queue_manager.add_job(
        file_path=request.file_path,
        file_name=request.file_name,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        quality_preset=quality,
        transcribe_or_translate=request.transcribe_or_translate,
        priority=request.priority,
        is_manual_request=request.is_manual_request,
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job already exists for {request.file_name}"
        )

    logger.info(f"Job {job.id} created via API for {request.file_name}")

    return JobResponse(**job.to_dict())


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(job_id: str):
    """
    Retry a failed job.

    Args:
        job_id: Job ID to retry

    Returns:
        Updated job object

    Raises:
        404: Job not found
        400: Job cannot be retried
    """
    from backend.core.queue_manager import queue_manager
    from backend.core.database import database
    from backend.core.models import Job, JobStatus

    # Check if job exists and can be retried (within session)
    with database.get_session() as session:
        job = session.query(Job).filter(Job.id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # Access attributes while session is active
        can_retry = job.status == JobStatus.FAILED
        current_status = job.status.value

        if not can_retry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} cannot be retried (status={current_status})"
            )

    # Reset job to queued
    success = queue_manager.retry_job(job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry job {job_id}"
        )

    # Get updated job and return
    with database.get_session() as session:
        job = session.query(Job).filter(Job.id == job_id).first()
        job_dict = job.to_dict() if job else {}

    logger.info(f"Job {job_id} retried via API")

    return JobResponse(**job_dict)


@router.delete("/{job_id}", response_model=MessageResponse)
async def cancel_job(job_id: str):
    """
    Cancel a job.

    Args:
        job_id: Job ID to cancel

    Returns:
        Success message

    Raises:
        404: Job not found
        400: Job already completed
    """
    from backend.core.queue_manager import queue_manager
    from backend.core.database import database
    from backend.core.models import Job, JobStatus

    # Check if job exists and can be cancelled (within session)
    with database.get_session() as session:
        job = session.query(Job).filter(Job.id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # Access attributes while session is active
        is_terminal = job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
        current_status = job.status.value

        if is_terminal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} is already in terminal state: {current_status}"
            )

    # Cancel job
    success = queue_manager.cancel_job(job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job {job_id}"
        )

    logger.info(f"Job {job_id} cancelled via API")

    return MessageResponse(message=f"Job {job_id} cancelled successfully")


@router.post("/{job_id}/cancel", response_model=MessageResponse)
async def cancel_job_post(job_id: str):
    """
    Cancel a job (POST alias).

    Args:
        job_id: Job ID to cancel

    Returns:
        Success message
    """
    # Reuse the delete endpoint logic
    return await cancel_job(job_id)


@router.post("/queue/clear", response_model=MessageResponse)
async def clear_completed_jobs():
    """
    Clear all completed jobs from the queue.

    Returns:
        Success message with count of cleared jobs
    """
    from backend.core.queue_manager import queue_manager

    count = queue_manager.clear_completed_jobs()

    logger.info(f"Cleared {count} completed jobs via API")

    return MessageResponse(message=f"Cleared {count} completed jobs")

