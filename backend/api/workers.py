
"""Worker management API routes."""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.core.worker import WorkerType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workers", tags=["workers"])


# === REQUEST/RESPONSE MODELS ===

class WorkerAddRequest(BaseModel):
    """Request to add a new worker."""
    worker_type: str = Field(..., description="Worker type: 'cpu' or 'gpu'")
    device_id: Optional[int] = Field(None, description="GPU device ID (only for GPU workers)")

    class Config:
        json_schema_extra = {
            "example": {
                "worker_type": "gpu",
                "device_id": 0
            }
        }


class WorkerStatusResponse(BaseModel):
    """Worker status response."""
    worker_id: str
    worker_type: str
    device_id: Optional[int]
    status: str
    current_job_id: Optional[str]
    jobs_completed: int
    jobs_failed: int
    uptime_seconds: float
    current_job_progress: float
    current_job_eta: Optional[int]


class WorkerPoolStatsResponse(BaseModel):
    """Worker pool statistics response."""
    total_workers: int
    cpu_workers: int
    gpu_workers: int
    idle_workers: int
    busy_workers: int
    stopped_workers: int
    error_workers: int
    total_jobs_completed: int
    total_jobs_failed: int
    uptime_seconds: Optional[float]
    is_running: bool


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


# === ROUTES ===

@router.get("/", response_model=List[WorkerStatusResponse])
async def get_all_workers():
    """
    Get status of all workers.

    Returns:
        List of worker status objects
    """
    from backend.app import worker_pool
    from datetime import datetime, timezone
    from dateutil import parser

    workers_status = worker_pool.get_all_workers_status()

    result = []
    for w in workers_status:
        # Calculate uptime
        uptime_seconds = 0.0
        if w.get("started_at"):
            try:
                started = parser.parse(w["started_at"])
                # Remove timezone info for comparison if needed
                if started.tzinfo is None:
                    from datetime import timezone
                    started = started.replace(tzinfo=timezone.utc)
                uptime_seconds = (datetime.now(timezone.utc) - started).total_seconds()
            except Exception as e:
                logger.warning(f"Failed to parse started_at: {e}")
                uptime_seconds = 0.0

        result.append(
            WorkerStatusResponse(
                worker_id=w["worker_id"],
                worker_type=w["type"],
                device_id=w.get("device_id"),
                status=w["status"],
                current_job_id=w.get("current_job_id"),
                jobs_completed=w["jobs_completed"],
                jobs_failed=w["jobs_failed"],
                uptime_seconds=uptime_seconds,
                current_job_progress=w.get("current_job_progress", 0.0),
                current_job_eta=w.get("current_job_eta"),
            )
        )

    return result


@router.get("/stats", response_model=WorkerPoolStatsResponse)
async def get_pool_stats():
    """
    Get worker pool statistics.

    Returns:
        Pool statistics object
    """
    from backend.app import worker_pool
    from datetime import datetime, timezone
    from dateutil import parser

    stats = worker_pool.get_pool_stats()
    pool_stats = stats.get('pool', {})
    jobs_stats = stats.get('jobs', {})

    # Calculate uptime
    uptime_seconds = 0.0
    if pool_stats.get('started_at'):
        try:
            started = parser.parse(pool_stats['started_at'])
            # Remove timezone info for comparison if needed
            if started.tzinfo is None:
                from datetime import timezone
                started = started.replace(tzinfo=timezone.utc)
            uptime_seconds = (datetime.now(timezone.utc) - started).total_seconds()
        except Exception as e:
            logger.warning(f"Failed to parse pool started_at: {e}")
            uptime_seconds = 0.0

    return WorkerPoolStatsResponse(
        total_workers=pool_stats.get('total_workers', 0),
        cpu_workers=pool_stats.get('cpu_workers', 0),
        gpu_workers=pool_stats.get('gpu_workers', 0),
        idle_workers=pool_stats.get('idle_workers', 0),
        busy_workers=pool_stats.get('busy_workers', 0),
        stopped_workers=pool_stats.get('stopped_workers', 0),
        error_workers=pool_stats.get('error_workers', 0),
        total_jobs_completed=jobs_stats.get('completed', 0),
        total_jobs_failed=jobs_stats.get('failed', 0),
        uptime_seconds=uptime_seconds,
        is_running=pool_stats.get('is_running', False)
    )


@router.get("/{worker_id}", response_model=WorkerStatusResponse)
async def get_worker(worker_id: str):
    """
    Get status of a specific worker.

    Args:
        worker_id: Worker ID

    Returns:
        Worker status object

    Raises:
        404: Worker not found
    """
    from backend.app import worker_pool

    status_dict = worker_pool.get_worker_status(worker_id)

    if not status_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found"
        )

    return WorkerStatusResponse(
        worker_id=status_dict["worker_id"],
        worker_type=status_dict["type"],  # Fixed: use "type" instead of "worker_type"
        device_id=status_dict.get("device_id"),
        status=status_dict["status"],
        current_job_id=status_dict.get("current_job_id"),
        jobs_completed=status_dict["jobs_completed"],
        jobs_failed=status_dict["jobs_failed"],
        uptime_seconds=status_dict.get("uptime_seconds", 0),
        current_job_progress=status_dict.get("current_job_progress", 0.0),
        current_job_eta=status_dict.get("current_job_eta"),
    )


@router.post("/", response_model=WorkerStatusResponse, status_code=status.HTTP_201_CREATED)
async def add_worker(request: WorkerAddRequest):
    """
    Add a new worker to the pool.

    Args:
        request: Worker add request

    Returns:
        Created worker status

    Raises:
        400: Invalid worker type or configuration
    """
    from backend.app import worker_pool

    # Validate worker type
    try:
        wtype = WorkerType(request.worker_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid worker type: {request.worker_type}. Must be 'cpu' or 'gpu'"
        )

    # Validate GPU worker requirements
    if wtype == WorkerType.GPU and request.device_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="device_id is required for GPU workers"
        )

    # Add worker
    worker_id = worker_pool.add_worker(wtype, request.device_id)

    # Get status
    status_dict = worker_pool.get_worker_status(worker_id)

    if not status_dict:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create worker"
        )

    logger.info(f"Worker {worker_id} added via API")

    return WorkerStatusResponse(
        worker_id=status_dict["worker_id"],
        worker_type=status_dict["type"],  # Fixed: use "type" instead of "worker_type"
        device_id=status_dict.get("device_id"),
        status=status_dict["status"],
        current_job_id=status_dict.get("current_job_id"),
        jobs_completed=status_dict["jobs_completed"],
        jobs_failed=status_dict["jobs_failed"],
        uptime_seconds=status_dict.get("uptime_seconds", 0),
        current_job_progress=status_dict.get("current_job_progress", 0.0),
        current_job_eta=status_dict.get("current_job_eta"),
    )


@router.delete("/{worker_id}", response_model=MessageResponse)
async def remove_worker(worker_id: str, timeout: float = 30.0):
    """
    Remove a worker from the pool.

    Args:
        worker_id: Worker ID to remove
        timeout: Maximum time to wait for worker to stop (seconds)

    Returns:
        Success message

    Raises:
        404: Worker not found
    """
    from backend.app import worker_pool

    success = worker_pool.remove_worker(worker_id, timeout=timeout)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found"
        )

    logger.info(f"Worker {worker_id} removed via API")

    return MessageResponse(message=f"Worker {worker_id} removed successfully")


@router.post("/pool/start", response_model=MessageResponse)
async def start_pool(cpu_workers: int = 0, gpu_workers: int = 0):
    """
    Start the worker pool.

    Args:
        cpu_workers: Number of CPU workers to start
        gpu_workers: Number of GPU workers to start

    Returns:
        Success message
    """
    from backend.app import worker_pool

    worker_pool.start(cpu_workers=cpu_workers, gpu_workers=gpu_workers)

    logger.info(f"Worker pool started via API: {cpu_workers} CPU, {gpu_workers} GPU")

    return MessageResponse(
        message=f"Worker pool started: {cpu_workers} CPU workers, {gpu_workers} GPU workers"
    )


@router.post("/pool/stop", response_model=MessageResponse)
async def stop_pool(timeout: float = 30.0):
    """
    Stop the worker pool.

    Args:
        timeout: Maximum time to wait for each worker to stop (seconds)

    Returns:
        Success message
    """
    from backend.app import worker_pool

    worker_pool.stop(timeout=timeout)

    logger.info("Worker pool stopped via API")

    return MessageResponse(message="Worker pool stopped successfully")

