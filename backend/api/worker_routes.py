"""Worker pool management API endpoints."""
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.core.worker_pool import worker_pool
from backend.core.worker import WorkerType

router = APIRouter(prefix="/api/workers", tags=["workers"])


# === Request/Response Models ===


class AddWorkerRequest(BaseModel):
    """Request to add a new worker."""

    type: str = Field(..., description="Worker type: 'cpu' or 'gpu'")
    device_id: Optional[int] = Field(None, description="GPU device ID (required for GPU workers)")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "gpu",
                "device_id": 0
            }
        }


class AddWorkerResponse(BaseModel):
    """Response after adding a worker."""

    worker_id: str
    message: str


class WorkerStatusResponse(BaseModel):
    """Worker status information."""

    worker_id: str
    status: str
    worker_type: str
    device_id: Optional[int]
    current_job_id: Optional[str]
    jobs_completed: int
    jobs_failed: int
    started_at: Optional[str]


class PoolStatsResponse(BaseModel):
    """Worker pool statistics."""

    pool: dict
    jobs: dict
    queue: dict


class HealthCheckResponse(BaseModel):
    """Health check results."""

    timestamp: str
    total_workers: int
    dead_workers: list
    restarted_workers: list
    healthy: bool


# === Endpoints ===


@router.get("/", response_model=list)
async def list_workers():
    """
    List all workers with their status.

    Returns:
        List of worker status dictionaries
    """
    return worker_pool.get_all_workers_status()


@router.get("/{worker_id}", response_model=WorkerStatusResponse)
async def get_worker_status(worker_id: str):
    """
    Get status of a specific worker.

    Args:
        worker_id: Worker ID

    Returns:
        Worker status information

    Raises:
        HTTPException: If worker not found
    """
    status = worker_pool.get_worker_status(worker_id)

    if not status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found"
        )

    return status


@router.post("/", response_model=AddWorkerResponse, status_code=status.HTTP_201_CREATED)
async def add_worker(request: AddWorkerRequest):
    """
    Add a new worker to the pool.

    Args:
        request: Worker configuration

    Returns:
        Worker ID and success message

    Raises:
        HTTPException: If invalid configuration
    """
    # Validate worker type
    worker_type_str = request.type.lower()
    if worker_type_str not in ["cpu", "gpu"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Worker type must be 'cpu' or 'gpu'"
        )

    # Map to WorkerType enum
    worker_type = WorkerType.CPU if worker_type_str == "cpu" else WorkerType.GPU

    # Validate GPU device_id
    if worker_type == WorkerType.GPU:
        if request.device_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="device_id is required for GPU workers"
            )
        if request.device_id < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="device_id must be non-negative"
            )

    # Add worker
    try:
        worker_id = worker_pool.add_worker(worker_type, request.device_id)

        return AddWorkerResponse(
            worker_id=worker_id,
            message=f"Worker {worker_id} added successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add worker: {str(e)}"
        )


@router.delete("/{worker_id}")
async def remove_worker(worker_id: str, timeout: int = 30):
    """
    Remove a worker from the pool.

    Args:
        worker_id: Worker ID to remove
        timeout: Maximum time to wait for worker to stop (seconds)

    Returns:
        Success message

    Raises:
        HTTPException: If worker not found or removal fails
    """
    success = worker_pool.remove_worker(worker_id, timeout=float(timeout))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found"
        )

    return {"message": f"Worker {worker_id} removed successfully"}


@router.get("/pool/stats", response_model=PoolStatsResponse)
async def get_pool_stats():
    """
    Get overall worker pool statistics.

    Returns:
        Pool statistics including worker counts, job stats, and queue info
    """
    return worker_pool.get_pool_stats()


@router.post("/pool/start")
async def start_pool(cpu_workers: int = 0, gpu_workers: int = 0):
    """
    Start the worker pool.

    Args:
        cpu_workers: Number of CPU workers to start
        gpu_workers: Number of GPU workers to start

    Returns:
        Success message
    """
    worker_pool.start(cpu_workers=cpu_workers, gpu_workers=gpu_workers)

    return {
        "message": f"Worker pool started with {cpu_workers} CPU and {gpu_workers} GPU workers"
    }


@router.post("/pool/stop")
async def stop_pool(timeout: int = 30):
    """
    Stop the worker pool.

    Args:
        timeout: Maximum time to wait for each worker to stop (seconds)

    Returns:
        Success message
    """
    worker_pool.stop(timeout=float(timeout))

    return {"message": "Worker pool stopped successfully"}


@router.get("/pool/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Perform health check on all workers.

    Automatically restarts dead workers if configured.

    Returns:
        Health check results
    """
    return worker_pool.health_check()


@router.post("/pool/autoscale")
async def autoscale_pool(target_workers: int):
    """
    Auto-scale worker pool to target number.

    Args:
        target_workers: Target number of workers

    Returns:
        Success message

    Raises:
        HTTPException: If invalid target
    """
    if target_workers < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_workers must be non-negative"
        )

    worker_pool.auto_scale(target_workers)

    return {"message": f"Pool scaled to {target_workers} workers"}
