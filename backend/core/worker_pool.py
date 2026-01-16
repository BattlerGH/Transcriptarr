"""Worker pool orchestrator for managing transcription workers."""
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timezone

from backend.core.worker import Worker, WorkerType, WorkerStatus
from backend.core.queue_manager import queue_manager

logger = logging.getLogger(__name__)


class WorkerPool:
    """
    Orchestrator for managing a pool of transcription workers.

    Similar to Tdarr's worker management system, this class handles:
    - Dynamic worker creation/removal (CPU and GPU)
    - Worker health monitoring
    - Load balancing via the queue
    - Worker statistics and reporting
    - Graceful shutdown

    Workers are managed as separate processes that pull jobs from the
    persistent queue. The pool can be controlled via WebUI to add/remove
    workers on-demand.
    """

    def __init__(self):
        """Initialize worker pool."""
        self.workers: Dict[str, Worker] = {}
        self.is_running = False
        self.started_at: Optional[datetime] = None

        logger.info("WorkerPool initialized")

    def start(self, cpu_workers: int = 0, gpu_workers: int = 0):
        """
        Start the worker pool with specified number of workers.

        Args:
            cpu_workers: Number of CPU workers to start
            gpu_workers: Number of GPU workers to start
        """
        if self.is_running:
            logger.warning("WorkerPool is already running")
            return

        self.is_running = True
        self.started_at = datetime.now(timezone.utc)

        # Start CPU workers
        for i in range(cpu_workers):
            self.add_worker(WorkerType.CPU)

        # Start GPU workers
        for i in range(gpu_workers):
            self.add_worker(WorkerType.GPU, device_id=i % self._get_gpu_count())

        logger.info(
            f"WorkerPool started: {cpu_workers} CPU workers, {gpu_workers} GPU workers"
        )

    def stop(self, timeout: float = 30.0):
        """
        Stop all workers gracefully.

        Args:
            timeout: Maximum time to wait for each worker to stop
        """
        if not self.is_running:
            logger.warning("WorkerPool is not running")
            return

        logger.info(f"Stopping WorkerPool with {len(self.workers)} workers...")

        # Stop all workers
        for worker_id, worker in list(self.workers.items()):
            logger.info(f"Stopping worker {worker_id}")
            worker.stop(timeout=timeout)

        self.workers.clear()
        self.is_running = False

        logger.info("WorkerPool stopped")

    def add_worker(
        self,
        worker_type: WorkerType,
        device_id: Optional[int] = None
    ) -> str:
        """
        Add a new worker to the pool.

        Args:
            worker_type: CPU or GPU
            device_id: GPU device ID (only for GPU workers)

        Returns:
            Worker ID
        """
        # Generate unique worker ID
        worker_id = self._generate_worker_id(worker_type, device_id)

        if worker_id in self.workers:
            logger.warning(f"Worker {worker_id} already exists")
            return worker_id

        # Create and start worker
        worker = Worker(worker_id, worker_type, device_id)
        worker.start()

        self.workers[worker_id] = worker

        logger.info(f"Added worker {worker_id} ({worker_type.value})")
        return worker_id

    def remove_worker(self, worker_id: str, timeout: float = 30.0) -> bool:
        """
        Remove a worker from the pool.

        Args:
            worker_id: Worker ID to remove
            timeout: Maximum time to wait for worker to stop

        Returns:
            True if worker was removed, False otherwise
        """
        worker = self.workers.get(worker_id)

        if not worker:
            logger.warning(f"Worker {worker_id} not found")
            return False

        logger.info(f"Removing worker {worker_id}")
        worker.stop(timeout=timeout)

        del self.workers[worker_id]

        logger.info(f"Worker {worker_id} removed")
        return True

    def get_worker_status(self, worker_id: str) -> Optional[dict]:
        """
        Get status of a specific worker.

        Args:
            worker_id: Worker ID

        Returns:
            Worker status dict or None if not found
        """
        worker = self.workers.get(worker_id)
        if not worker:
            return None

        return worker.get_status()

    def get_all_workers_status(self) -> List[dict]:
        """
        Get status of all workers.

        Returns:
            List of worker status dicts
        """
        return [worker.get_status() for worker in self.workers.values()]

    def get_pool_stats(self) -> dict:
        """
        Get overall pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        total_workers = len(self.workers)
        cpu_workers = sum(1 for w in self.workers.values() if w.worker_type == WorkerType.CPU)
        gpu_workers = sum(1 for w in self.workers.values() if w.worker_type == WorkerType.GPU)

        # Count workers by status
        idle_workers = 0
        busy_workers = 0
        stopped_workers = 0
        error_workers = 0

        for worker in self.workers.values():
            status_dict = worker.get_status()
            status = status_dict["status"]  # This is a string like "idle", "busy", etc.

            if status == "idle":
                idle_workers += 1
            elif status == "busy":
                busy_workers += 1
            elif status == "stopped":
                stopped_workers += 1
            elif status == "error":
                error_workers += 1

        # Get total jobs processed
        total_completed = sum(w.jobs_completed.value for w in self.workers.values())
        total_failed = sum(w.jobs_failed.value for w in self.workers.values())

        # Get queue stats
        queue_stats = queue_manager.get_queue_stats()

        return {
            "pool": {
                "is_running": self.is_running,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "total_workers": total_workers,
                "cpu_workers": cpu_workers,
                "gpu_workers": gpu_workers,
                "idle_workers": idle_workers,
                "busy_workers": busy_workers,
                "stopped_workers": stopped_workers,
                "error_workers": error_workers,
            },
            "jobs": {
                "completed": total_completed,
                "failed": total_failed,
                "success_rate": (
                    total_completed / (total_completed + total_failed) * 100
                    if (total_completed + total_failed) > 0
                    else 0
                ),
            },
            "queue": queue_stats,
        }

    def health_check(self) -> dict:
        """
        Perform health check on all workers.

        Restarts dead workers automatically.

        Returns:
            Health check results
        """
        dead_workers = []
        restarted_workers = []

        for worker_id, worker in list(self.workers.items()):
            if not worker.is_alive():
                logger.warning(f"Worker {worker_id} is dead, restarting...")
                dead_workers.append(worker_id)

                # Try to restart
                try:
                    worker.start()
                    restarted_workers.append(worker_id)
                    logger.info(f"Worker {worker_id} restarted successfully")
                except Exception as e:
                    logger.error(f"Failed to restart worker {worker_id}: {e}")

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_workers": len(self.workers),
            "dead_workers": dead_workers,
            "restarted_workers": restarted_workers,
            "healthy": len(dead_workers) == 0,
        }

    def auto_scale(self, target_workers: int):
        """
        Auto-scale workers based on queue size.

        This is a placeholder for future auto-scaling logic.

        Args:
            target_workers: Target number of workers
        """
        current_workers = len(self.workers)

        if current_workers < target_workers:
            # Add workers
            workers_to_add = target_workers - current_workers
            logger.info(f"Auto-scaling: adding {workers_to_add} workers")

            for _ in range(workers_to_add):
                # Default to CPU workers for auto-scaling
                self.add_worker(WorkerType.CPU)

        elif current_workers > target_workers:
            # Remove idle workers
            workers_to_remove = current_workers - target_workers
            logger.info(f"Auto-scaling: removing {workers_to_remove} workers")

            # Find idle workers to remove
            idle_workers = [
                worker_id for worker_id, worker in self.workers.items()
                if worker.get_status()["status"] == WorkerStatus.IDLE.value
            ]

            for worker_id in idle_workers[:workers_to_remove]:
                self.remove_worker(worker_id)

    def _generate_worker_id(
        self,
        worker_type: WorkerType,
        device_id: Optional[int] = None
    ) -> str:
        """
        Generate unique worker ID.

        Args:
            worker_type: CPU or GPU
            device_id: GPU device ID

        Returns:
            Worker ID string
        """
        prefix = "cpu" if worker_type == WorkerType.CPU else f"gpu{device_id}"

        # Count existing workers of this type
        existing_count = sum(
            1 for wid in self.workers.keys()
            if wid.startswith(prefix)
        )

        return f"{prefix}-{existing_count + 1}"

    def _get_gpu_count(self) -> int:
        """
        Get number of available GPUs.

        Returns:
            Number of GPUs (defaults to 1 if detection fails)
        """
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.device_count()
        except ImportError:
            pass

        return 1  # Default to 1 GPU


# Global worker pool instance
worker_pool = WorkerPool()