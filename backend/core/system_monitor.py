"""System resource monitoring service."""
import logging
import platform
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import psutil (CPU/RAM monitoring)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not installed. CPU/RAM monitoring will be unavailable.")

# Try to import pynvml (NVIDIA GPU monitoring)
try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except Exception as e:
    NVML_AVAILABLE = False
    logger.debug(f"pynvml not available: {e}. GPU monitoring will be unavailable.")


class SystemMonitor:
    """Monitor system resources: CPU, RAM, GPU, VRAM."""

    def __init__(self):
        """Initialize system monitor."""
        self.gpu_count = 0

        if NVML_AVAILABLE:
            try:
                self.gpu_count = pynvml.nvmlDeviceGetCount()
                logger.info(f"Detected {self.gpu_count} NVIDIA GPU(s)")
            except Exception as e:
                logger.warning(f"Could not get GPU count: {e}")
                self.gpu_count = 0

    def get_cpu_info(self) -> Dict[str, any]:
        """
        Get CPU usage information.

        Returns:
            Dictionary with CPU stats
        """
        if not PSUTIL_AVAILABLE:
            return {
                "available": False,
                "error": "psutil not installed"
            }

        try:
            cpu_percent = psutil.cpu_percent(interval=0.1, percpu=False)
            cpu_count = psutil.cpu_count(logical=True)
            cpu_count_physical = psutil.cpu_count(logical=False)

            # Get per-core usage
            cpu_percent_per_core = psutil.cpu_percent(interval=0.1, percpu=True)

            # Get CPU frequency
            cpu_freq = psutil.cpu_freq()
            freq_current = cpu_freq.current if cpu_freq else None
            freq_max = cpu_freq.max if cpu_freq else None

            return {
                "available": True,
                "usage_percent": round(cpu_percent, 1),
                "count_logical": cpu_count,
                "count_physical": cpu_count_physical,
                "per_core_usage": [round(p, 1) for p in cpu_percent_per_core],
                "frequency_mhz": round(freq_current, 0) if freq_current else None,
                "frequency_max_mhz": round(freq_max, 0) if freq_max else None,
            }
        except Exception as e:
            logger.error(f"Error getting CPU info: {e}")
            return {
                "available": False,
                "error": str(e)
            }

    def get_memory_info(self) -> Dict[str, any]:
        """
        Get RAM usage information.

        Returns:
            Dictionary with memory stats
        """
        if not PSUTIL_AVAILABLE:
            return {
                "available": False,
                "error": "psutil not installed"
            }

        try:
            mem = psutil.virtual_memory()

            return {
                "available": True,
                "total_gb": round(mem.total / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "free_gb": round(mem.available / (1024**3), 2),
                "usage_percent": round(mem.percent, 1),
                "total_bytes": mem.total,
                "used_bytes": mem.used,
                "available_bytes": mem.available,
            }
        except Exception as e:
            logger.error(f"Error getting memory info: {e}")
            return {
                "available": False,
                "error": str(e)
            }

    def get_swap_info(self) -> Dict[str, any]:
        """
        Get swap memory information.

        Returns:
            Dictionary with swap stats
        """
        if not PSUTIL_AVAILABLE:
            return {
                "available": False,
                "error": "psutil not installed"
            }

        try:
            swap = psutil.swap_memory()

            return {
                "available": True,
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "free_gb": round(swap.free / (1024**3), 2),
                "usage_percent": round(swap.percent, 1),
                "total_bytes": swap.total,
                "used_bytes": swap.used,
                "free_bytes": swap.free,
            }
        except Exception as e:
            logger.error(f"Error getting swap info: {e}")
            return {
                "available": False,
                "error": str(e)
            }

    def get_gpu_info(self, device_id: int = 0) -> Dict[str, any]:
        """
        Get GPU information for a specific device.

        Args:
            device_id: GPU device ID (default: 0)

        Returns:
            Dictionary with GPU stats
        """
        if not NVML_AVAILABLE:
            return {
                "available": False,
                "device_id": device_id,
                "error": "pynvml not available or no NVIDIA GPUs detected"
            }

        if device_id >= self.gpu_count:
            return {
                "available": False,
                "device_id": device_id,
                "error": f"GPU device {device_id} not found. Only {self.gpu_count} GPU(s) available."
            }

        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)

            # Get GPU name
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')

            # Get memory info
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

            # Get utilization
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)

            # Get temperature
            try:
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            except Exception:
                temp = None

            # Get power usage
            try:
                power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert mW to W
                power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
            except Exception:
                power_usage = None
                power_limit = None

            # Get fan speed
            try:
                fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)
            except Exception:
                fan_speed = None

            return {
                "available": True,
                "device_id": device_id,
                "name": name,
                "memory": {
                    "total_gb": round(mem_info.total / (1024**3), 2),
                    "used_gb": round(mem_info.used / (1024**3), 2),
                    "free_gb": round(mem_info.free / (1024**3), 2),
                    "usage_percent": round((mem_info.used / mem_info.total) * 100, 1),
                    "total_bytes": mem_info.total,
                    "used_bytes": mem_info.used,
                    "free_bytes": mem_info.free,
                },
                "utilization": {
                    "gpu_percent": util.gpu,
                    "memory_percent": util.memory,
                },
                "temperature_c": temp,
                "power": {
                    "usage_watts": round(power_usage, 1) if power_usage else None,
                    "limit_watts": round(power_limit, 1) if power_limit else None,
                    "usage_percent": round((power_usage / power_limit) * 100, 1) if (power_usage and power_limit) else None,
                },
                "fan_speed_percent": fan_speed,
            }
        except Exception as e:
            logger.error(f"Error getting GPU {device_id} info: {e}")
            return {
                "available": False,
                "device_id": device_id,
                "error": str(e)
            }

    def get_all_gpus_info(self) -> List[Dict[str, any]]:
        """
        Get information for all available GPUs.

        Returns:
            List of GPU info dictionaries
        """
        if not NVML_AVAILABLE or self.gpu_count == 0:
            return []

        return [self.get_gpu_info(i) for i in range(self.gpu_count)]

    def get_system_info(self) -> Dict[str, any]:
        """
        Get general system information.

        Returns:
            Dictionary with system info
        """
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }

    def get_all_resources(self) -> Dict[str, any]:
        """
        Get all system resources in a single call.

        Returns:
            Comprehensive system resource dictionary
        """
        return {
            "system": self.get_system_info(),
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "swap": self.get_swap_info(),
            "gpus": self.get_all_gpus_info(),
            "gpu_count": self.gpu_count,
        }

    def __del__(self):
        """Cleanup NVML on destruction."""
        if NVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass


# Global system monitor instance
system_monitor = SystemMonitor()
