"""Individual worker for processing transcription jobs."""
import logging
import multiprocessing as mp
import os
import time
import traceback
from datetime import datetime, timezone
from enum import IntEnum, Enum
from typing import Optional

from backend.core.database import Database
from backend.core.models import Job, JobStatus, JobStage
from backend.core.queue_manager import QueueManager

logger = logging.getLogger(__name__)


class WorkerType(str, Enum):
    """Worker device type."""
    CPU = "cpu"
    GPU = "gpu"


class WorkerStatus(IntEnum):
    """Worker status states."""
    IDLE = 0
    BUSY = 1
    STOPPING = 2
    STOPPED = 3
    ERROR = 4

    def to_string(self) -> str:
        """Convert to string representation."""
        return {
            0: "idle",
            1: "busy",
            2: "stopping",
            3: "stopped",
            4: "error"
        }.get(self.value, "unknown")


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
        self.started_at = datetime.now(timezone.utc)
        logger.info(
            f"Worker {self.worker_id} started (PID: {self.process.pid}, "
            f"Type: {self.worker_type.value})"
        )

    def stop(self, timeout: float = 5.0):
        """
        Stop the worker process gracefully.

        Args:
            timeout: Maximum time to wait for worker to stop
        """
        if not self.process or not self.process.is_alive():
            logger.debug(f"Worker {self.worker_id} is not running")
            return

        logger.info(f"Stopping worker {self.worker_id}...")
        self.stop_event.set()
        self.process.join(timeout=timeout)

        if self.process.is_alive():
            logger.warning(f"Worker {self.worker_id} did not stop gracefully, terminating...")
            self.process.terminate()
            self.process.join(timeout=2.0)

            if self.process.is_alive():
                logger.error(f"Worker {self.worker_id} did not terminate, killing...")
                self.process.kill()
                self.process.join(timeout=1.0)

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
            "status": status_enum.to_string(),  # Convert to string
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
        Process a job (transcription or language detection).

        Args:
            job: Job to process
            queue_mgr: Queue manager for updating progress
        """
        from backend.core.models import JobType

        # Route to appropriate handler based on job type
        if job.job_type == JobType.LANGUAGE_DETECTION:
            self._process_language_detection(job, queue_mgr)
        else:
            self._process_transcription(job, queue_mgr)

    def _process_language_detection(self, job: Job, queue_mgr: QueueManager):
        """
        Process a language detection job using fast Whisper model.

        Args:
            job: Language detection job
            queue_mgr: Queue manager for updating progress
        """
        start_time = time.time()

        try:
            logger.info(f"Worker {self.worker_id} processing LANGUAGE DETECTION job {job.id}: {job.file_name}")

            # Stage 1: Detecting language (20% progress)
            queue_mgr.update_job_progress(
                job.id, progress=20.0, stage=JobStage.DETECTING_LANGUAGE, eta_seconds=10
            )

            # Use language detector with tiny model
            from backend.scanning.language_detector import LanguageDetector

            language, confidence = LanguageDetector.detect_language(
                file_path=job.file_path,
                sample_duration=30
            )

            # Stage 2: Finalizing (80% progress)
            queue_mgr.update_job_progress(
                job.id, progress=80.0, stage=JobStage.FINALIZING, eta_seconds=2
            )

            if language:
                # Calculate processing time
                processing_time = time.time() - start_time

                # Use ISO 639-1 format (ja, en, es) throughout the system
                lang_code = language.value[0] if language else "unknown"

                result_text = f"Language detected: {lang_code} ({language.name.title() if language else 'Unknown'})\nConfidence: {confidence}%"

                # Store in ISO 639-1 format (ja, en, es) for consistency
                queue_mgr.mark_job_completed(
                    job.id,
                    output_path=None,
                    segments_count=0,
                    srt_content=result_text,
                    detected_language=lang_code  # Use ISO 639-1 (ja, en, es)
                )

                logger.info(
                    f"Worker {self.worker_id} completed detection job {job.id}: "
                    f"{lang_code} (confidence: {confidence}%) in {processing_time:.1f}s"
                )

                # Check if file matches any scan rules and queue transcription job
                self._check_and_queue_transcription(job, lang_code)
            else:
                # Detection failed
                queue_mgr.mark_job_failed(job.id, "Language detection failed - could not detect language")
                logger.error(f"Worker {self.worker_id} failed detection job {job.id}: No language detected")

        except Exception as e:
            logger.error(f"Worker {self.worker_id} failed detection job {job.id}: {e}", exc_info=True)
            queue_mgr.mark_job_failed(job.id, str(e))

    def _process_transcription(self, job: Job, queue_mgr: QueueManager):
        """
        Process a transcription/translation job using Whisper.

        Args:
            job: Transcription job
            queue_mgr: Queue manager for updating progress
        """
        from backend.transcription import WhisperTranscriber
        from backend.transcription.audio_utils import handle_multiple_audio_tracks
        from backend.core.language_code import LanguageCode

        transcriber = None
        start_time = time.time()

        try:
            logger.info(f"Worker {self.worker_id} processing TRANSCRIPTION job {job.id}: {job.file_name}")

            # Stage 1: Loading model
            queue_mgr.update_job_progress(
                job.id, progress=5.0, stage=JobStage.LOADING_MODEL, eta_seconds=None
            )

            # Determine device for transcriber
            if self.worker_type == WorkerType.GPU:
                device = f"cuda:{self.device_id}" if self.device_id is not None else "cuda"
            else:
                device = "cpu"

            transcriber = WhisperTranscriber(device=device)
            transcriber.load_model()

            # Stage 2: Preparing audio
            queue_mgr.update_job_progress(
                job.id, progress=10.0, stage=JobStage.EXTRACTING_AUDIO, eta_seconds=None
            )

            # Handle multiple audio tracks if needed
            source_lang = (
                LanguageCode.from_string(job.source_lang) if job.source_lang else None
            )
            audio_data = handle_multiple_audio_tracks(job.file_path, source_lang)

            # Stage 3: Transcribing
            queue_mgr.update_job_progress(
                job.id, progress=15.0, stage=JobStage.TRANSCRIBING, eta_seconds=None
            )

            # Progress callback for real-time updates
            def progress_callback(seek, total):
                # Reserve 15%-75% for Whisper (60% range)
                # If translate mode, reserve 75%-90% for translation (15% range)
                whisper_progress = 15.0 + (seek / total) * 60.0
                queue_mgr.update_job_progress(job.id, progress=whisper_progress, stage=JobStage.TRANSCRIBING)

            # Stage 3A: Whisper transcription to English
            # IMPORTANT: Both 'transcribe' and 'translate' modes use task='translate' here
            # to convert audio to English subtitles
            logger.info(f"Running Whisper with task='translate' to convert audio to English")

            # job.source_lang is already in ISO 639-1 format (ja, en, es)
            # Whisper accepts ISO 639-1, so we can use it directly
            if audio_data:
                result = transcriber.transcribe_audio_data(
                    audio_data=audio_data.read(),
                    language=job.source_lang,  # Already ISO 639-1 (ja, en, es)
                    task="translate",  # ALWAYS translate to English first
                    progress_callback=progress_callback,
                )
            else:
                result = transcriber.transcribe_file(
                    file_path=job.file_path,
                    language=job.source_lang,  # Already ISO 639-1 (ja, en, es)
                    task="translate",  # ALWAYS translate to English first
                    progress_callback=progress_callback,
                )

            # Generate English SRT filename
            file_base = os.path.splitext(job.file_path)[0]
            english_srt_path = f"{file_base}.eng.srt"

            # Save English SRT
            result.to_srt(english_srt_path, word_level=False)
            logger.info(f"English subtitles saved to {english_srt_path}")

            # Stage 3B: Optional translation to target language
            if job.transcribe_or_translate == "translate" and job.target_lang and job.target_lang.lower() != "eng":
                queue_mgr.update_job_progress(
                    job.id, progress=75.0, stage=JobStage.FINALIZING, eta_seconds=10
                )

                logger.info(f"Translating English subtitles to {job.target_lang}")

                from backend.transcription import translate_srt_file

                # Generate target language SRT filename
                target_srt_path = f"{file_base}.{job.target_lang}.srt"

                # Translate English SRT to target language
                success = translate_srt_file(
                    input_path=english_srt_path,
                    output_path=target_srt_path,
                    target_language=job.target_lang
                )

                if success:
                    logger.info(f"Translated subtitles saved to {target_srt_path}")
                    output_path = target_srt_path
                else:
                    logger.warning(f"Translation failed, keeping English subtitles only")
                    output_path = english_srt_path
            else:
                # For 'transcribe' mode or if target is English, use English SRT
                output_path = english_srt_path

            # Stage 4: Finalize
            queue_mgr.update_job_progress(
                job.id, progress=90.0, stage=JobStage.FINALIZING, eta_seconds=5
            )

            # Calculate processing time
            processing_time = time.time() - start_time

            # Get SRT content for storage
            srt_content = result.get_srt_content()

            # Mark job as completed
            queue_mgr.mark_job_completed(
                job.id,
                output_path=output_path,
                segments_count=result.segments_count,
                srt_content=srt_content,
                model_used=transcriber.model_name,
                device_used=transcriber.device,
                processing_time_seconds=processing_time,
            )

            logger.info(
                f"Worker {self.worker_id} completed job {job.id}: "
                f"{result.segments_count} segments in {processing_time:.1f}s"
            )

        except Exception as e:
            logger.error(f"Worker {self.worker_id} failed job {job.id}: {e}", exc_info=True)
            queue_mgr.mark_job_failed(job.id, str(e))
        finally:
            # Always unload model after job
            if transcriber:
                try:
                    transcriber.unload_model()
                except Exception as e:
                    logger.error(f"Error unloading model: {e}")

    def _set_status(self, status: WorkerStatus):
        """Set worker status (thread-safe)."""
        self.status.value = status.value

    def _set_current_job(self, job_id: str):
        """Set the current job ID (thread-safe)."""
        job_id_bytes = job_id.encode('utf-8')
        for i, byte in enumerate(job_id_bytes):
            if i < len(self.current_job_id):
                self.current_job_id[i] = byte

    def _clear_current_job(self):
        """Clear current job ID (thread-safe)."""
        for i in range(len(self.current_job_id)):
            self.current_job_id[i] = b'\x00'

    def _check_and_queue_transcription(self, job: Job, detected_lang_code: str):
        """
        Check if detected language matches any scan rules and queue transcription job.

        Args:
            job: Completed language detection job
            detected_lang_code: Detected language code (ISO 639-1, e.g., 'ja', 'en')
        """
        try:
            from backend.scanning.library_scanner import library_scanner

            logger.info(
                f"Language detection completed for {job.file_path}: {detected_lang_code}. "
                f"Checking scan rules..."
            )

            # Use the scanner's method to check rules and queue transcription
            library_scanner._check_and_queue_transcription_for_file(
                job.file_path, detected_lang_code
            )

        except Exception as e:
            logger.error(
                f"Error checking scan rules for {job.file_path}: {e}",
                exc_info=True
            )
