"""Individual worker for processing transcription jobs."""
import logging
import multiprocessing as mp
import time
import traceback
from datetime import datetime
from enum import Enum
from typing import Optional

from backend.core.database import Database
from backend.core.models import Job, JobStatus, JobStage
from backend.core.queue_manager import QueueManager

logger = logging.getLogger(__name__)


class WorkerType(str, Enum):
    """Worker device type."""
    CPU = "cpu"
    GPU = "gpu"


class WorkerStatus(str, Enum):
    """Worker status states."""
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class Worker:
    """
    Individual worker process for transcription.

    Each worker runs in its own process and can handle one job at a time.
    Workers communicate with the main process via multiprocessing primitives.
    """

    def __init__(
        self,
        worker_id: str,
        worker_type: WorkerType,
        device_id: Optional[int] = None
    ):
        """
        Initialize worker.

        Args:
            worker_id: Unique identifier for this worker
            worker_type: CPU or GPU
            device_id: GPU device ID (only for GPU workers)
        """
        self.worker_id = worker_id
        self.worker_type = worker_type
        self.device_id = device_id

        # Multiprocessing primitives
        self.process: Optional[mp.Process] = None
        self.stop_event = mp.Event()
        self.status = mp.Value('i', WorkerStatus.IDLE.value)  # type: ignore
        self.current_job_id = mp.Array('c', 36)  # type: ignore  # UUID string

        # Stats
        self.jobs_completed = mp.Value('i', 0)  # type: ignore
        self.jobs_failed = mp.Value('i', 0)  # type: ignore
        self.started_at: Optional[datetime] = None

    def start(self):
        """Start the worker process."""
        if self.process and self.process.is_alive():
            logger.warning(f"Worker {self.worker_id} is already running")
            return

        self.stop_event.clear()
        self.process = mp.Process(
            target=self._worker_loop,
            name=f"Worker-{self.worker_id}",
            daemon=True
        )
        self.process.start()
        self.started_at = datetime.utcnow()
        logger.info(
            f"Worker {self.worker_id} started (PID: {self.process.pid}, "
            f"Type: {self.worker_type.value})"
        )

    def stop(self, timeout: float = 30.0):
        """
        Stop the worker process gracefully.

        Args:
            timeout: Maximum time to wait for worker to stop
        """
        if not self.process or not self.process.is_alive():
            logger.warning(f"Worker {self.worker_id} is not running")
            return

        logger.info(f"Stopping worker {self.worker_id}...")
        self.stop_event.set()
        self.process.join(timeout=timeout)

        if self.process.is_alive():
            logger.warning(f"Worker {self.worker_id} did not stop gracefully, terminating...")
            self.process.terminate()
            self.process.join(timeout=5.0)

            if self.process.is_alive():
                logger.error(f"Worker {self.worker_id} did not terminate, killing...")
                self.process.kill()

        logger.info(f"Worker {self.worker_id} stopped")

    def is_alive(self) -> bool:
        """Check if worker process is alive."""
        return self.process is not None and self.process.is_alive()

    def get_status(self) -> dict:
        """Get worker status information."""
        status_value = self.status.value
        status_enum = WorkerStatus.IDLE
        for s in WorkerStatus:
            if s.value == status_value:
                status_enum = s
                break

        current_job = self.current_job_id.value.decode('utf-8').strip('\x00')

        return {
            "worker_id": self.worker_id,
            "type": self.worker_type.value,
            "device_id": self.device_id,
            "status": status_enum.value,
            "current_job_id": current_job if current_job else None,
            "jobs_completed": self.jobs_completed.value,
            "jobs_failed": self.jobs_failed.value,
            "is_alive": self.is_alive(),
            "pid": self.process.pid if self.process else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }

    def _worker_loop(self):
        """
        Main worker loop (runs in separate process).

        This is the entry point for the worker process.
        """
        # Set up logging in the worker process
        logging.basicConfig(
            level=logging.INFO,
            format=f'[Worker-{self.worker_id}] %(levelname)s: %(message)s'
        )

        logger.info(f"Worker {self.worker_id} loop started")

        # Initialize database and queue manager in worker process
        # Each process needs its own DB connection
        try:
            db = Database(auto_create_tables=False)
            queue_mgr = QueueManager()
        except Exception as e:
            logger.error(f"Failed to initialize worker: {e}")
            self._set_status(WorkerStatus.ERROR)
            return

        # Main work loop
        while not self.stop_event.is_set():
            try:
                # Try to get next job from queue
                job = queue_mgr.get_next_job(self.worker_id)

                if job is None:
                    # No jobs available, idle for a bit
                    self._set_status(WorkerStatus.IDLE)
                    time.sleep(2)
                    continue

                # Process the job
                self._set_status(WorkerStatus.BUSY)
                self._set_current_job(job.id)

                logger.info(f"Processing job {job.id}: {job.file_name}")

                try:
                    self._process_job(job, queue_mgr)
                    self.jobs_completed.value += 1
                    logger.info(f"Job {job.id} completed successfully")

                except Exception as e:
                    self.jobs_failed.value += 1
                    error_msg = f"Job processing failed: {str(e)}\n{traceback.format_exc()}"
                    logger.error(error_msg)

                    queue_mgr.mark_job_failed(job.id, error_msg)

                finally:
                    self._clear_current_job()

            except Exception as e:
                logger.error(f"Worker loop error: {e}\n{traceback.format_exc()}")
                time.sleep(5)  # Back off on errors

        self._set_status(WorkerStatus.STOPPED)
        logger.info(f"Worker {self.worker_id} loop ended")

    def _process_job(self, job: Job, queue_mgr: QueueManager):
        """
        Process a single transcription job.

        Args:
            job: Job to process
            queue_mgr: Queue manager for updating progress
        """
        # TODO: This will be implemented when we add the transcriber module
        # For now, simulate work

        # Stage 1: Detect language
        queue_mgr.update_job_progress(
            job.id,
            progress=10.0,
            stage=JobStage.DETECTING_LANGUAGE,
            eta_seconds=60
        )
        time.sleep(2)  # Simulate work

        # Stage 2: Extract audio
        queue_mgr.update_job_progress(
            job.id,
            progress=20.0,
            stage=JobStage.EXTRACTING_AUDIO,
            eta_seconds=50
        )
        time.sleep(2)

        # Stage 3: Transcribe
        queue_mgr.update_job_progress(
            job.id,
            progress=30.0,
            stage=JobStage.TRANSCRIBING,
            eta_seconds=40
        )

        # Simulate progressive transcription
        for i in range(30, 90, 10):
            time.sleep(1)
            queue_mgr.update_job_progress(
                job.id,
                progress=float(i),
                stage=JobStage.TRANSCRIBING,
                eta_seconds=int((100 - i) / 2)
            )

        # Stage 4: Finalize
        queue_mgr.update_job_progress(
            job.id,
            progress=95.0,
            stage=JobStage.FINALIZING,
            eta_seconds=5
        )
        time.sleep(1)

        # Mark as completed
        output_path = job.file_path.replace('.mkv', '.srt')
        queue_mgr.mark_job_completed(
            job.id,
            output_path=output_path,
            segments_count=100,  # Simulated
            srt_content="Simulated SRT content"
        )

    def _set_status(self, status: WorkerStatus):
        """Set worker status (thread-safe)."""
        self.status.value = status.value

    def _set_current_job(self, job_id: str):
        """Set current job ID (thread-safe)."""
        job_id_bytes = job_id.encode('utf-8')
        for i, byte in enumerate(job_id_bytes):
            if i < len(self.current_job_id):
                self.current_job_id[i] = byte

    def _clear_current_job(self):
        """Clear current job ID (thread-safe)."""
        for i in range(len(self.current_job_id)):
            self.current_job_id[i] = b'\x00'