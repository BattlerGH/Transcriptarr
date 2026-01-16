"""System resources monitoring API."""
import logging
import psutil
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])


# === RESPONSE MODELS ===

class CPUInfo(BaseModel):
    """CPU information."""
    usage_percent: float
    count_logical: int
    count_physical: int
    frequency_mhz: Optional[float] = None


class MemoryInfo(BaseModel):
    """Memory information."""
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float


class GPUInfo(BaseModel):
    """GPU information."""
    id: int
    name: str
    memory_total_mb: Optional[int] = None
    memory_used_mb: Optional[int] = None
    memory_free_mb: Optional[int] = None
    utilization_percent: Optional[int] = None


class SystemResourcesResponse(BaseModel):
    """System resources response."""
    cpu: CPUInfo
    memory: MemoryInfo
    gpus: List[GPUInfo]


# === ROUTES ===

@router.get("/resources", response_model=SystemResourcesResponse)
async def get_system_resources():
    """
    Get current system resources (CPU, RAM, GPU).

    Returns:
        System resources information
    """
    # CPU info
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count_logical = psutil.cpu_count(logical=True)
    cpu_count_physical = psutil.cpu_count(logical=False)
    cpu_freq = psutil.cpu_freq()

    cpu_info = CPUInfo(
        usage_percent=cpu_percent,
        count_logical=cpu_count_logical or 0,
        count_physical=cpu_count_physical or 0,
        frequency_mhz=cpu_freq.current if cpu_freq else 0
    )

    # Memory info
    mem = psutil.virtual_memory()
    memory_info = MemoryInfo(
        total_gb=round(mem.total / (1024**3), 2),
        used_gb=round(mem.used / (1024**3), 2),
        free_gb=round(mem.available / (1024**3), 2),
        usage_percent=round(mem.percent, 1)
    )

    # GPU info - try to detect NVIDIA GPUs
    gpus = []
    try:
        import pynvml
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()

        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            memory_info_gpu = pynvml.nvmlDeviceGetMemoryInfo(handle)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)

            gpus.append(GPUInfo(
                id=i,
                name=name if isinstance(name, str) else name.decode('utf-8'),
                memory_total_mb=memory_info_gpu.total // (1024**2),
                memory_used_mb=memory_info_gpu.used // (1024**2),
                memory_free_mb=memory_info_gpu.free // (1024**2),
                utilization_percent=utilization.gpu
            ))

        pynvml.nvmlShutdown()
    except Exception as e:
        logger.debug(f"Could not get GPU info: {e}")
        # No GPUs or pynvml not available
        pass

    return SystemResourcesResponse(
        cpu=cpu_info,
        memory=memory_info,
        gpus=gpus
    )


@router.get("/cpu", response_model=CPUInfo)
async def get_cpu_info():
    """Get CPU information."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count_logical = psutil.cpu_count(logical=True)
    cpu_count_physical = psutil.cpu_count(logical=False)
    cpu_freq = psutil.cpu_freq()

    return CPUInfo(
        usage_percent=cpu_percent,
        count_logical=cpu_count_logical or 0,
        count_physical=cpu_count_physical or 0,
        frequency_mhz=cpu_freq.current if cpu_freq else 0
    )


@router.get("/memory", response_model=MemoryInfo)
async def get_memory_info():
    """Get memory information."""
    mem = psutil.virtual_memory()

    return MemoryInfo(
        total_gb=round(mem.total / (1024**3), 2),
        used_gb=round(mem.used / (1024**3), 2),
        free_gb=round(mem.available / (1024**3), 2),
        usage_percent=round(mem.percent, 1)
    )


@router.get("/gpus", response_model=List[GPUInfo])
async def get_gpus_info():
    """Get all GPUs information."""
    gpus = []
    try:
        import pynvml
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()

        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            memory_info_gpu = pynvml.nvmlDeviceGetMemoryInfo(handle)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)

            gpus.append(GPUInfo(
                id=i,
                name=name if isinstance(name, str) else name.decode('utf-8'),
                memory_total_mb=memory_info_gpu.total // (1024**2),
                memory_used_mb=memory_info_gpu.used // (1024**2),
                memory_free_mb=memory_info_gpu.free // (1024**2),
                utilization_percent=utilization.gpu
            ))

        pynvml.nvmlShutdown()
    except Exception as e:
        logger.debug(f"Could not get GPU info: {e}")

    return gpus


@router.get("/gpu/{device_id}", response_model=GPUInfo)
async def get_gpu_info(device_id: int):
    """Get specific GPU information."""
    try:
        import pynvml
        pynvml.nvmlInit()

        handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)
        name = pynvml.nvmlDeviceGetName(handle)
        memory_info_gpu = pynvml.nvmlDeviceGetMemoryInfo(handle)
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)

        gpu = GPUInfo(
            id=device_id,
            name=name if isinstance(name, str) else name.decode('utf-8'),
            memory_total_mb=memory_info_gpu.total // (1024**2),
            memory_used_mb=memory_info_gpu.used // (1024**2),
            memory_free_mb=memory_info_gpu.free // (1024**2),
            utilization_percent=utilization.gpu
        )

        pynvml.nvmlShutdown()
        return gpu

    except Exception as e:
        logger.error(f"Could not get GPU {device_id} info: {e}")
        # Return basic info if can't get details
        return GPUInfo(
            id=device_id,
            name=f"GPU {device_id}",
            memory_total_mb=None,
            memory_used_mb=None,
            memory_free_mb=None,
            utilization_percent=None
        )

