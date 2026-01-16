"""Queue manager for persistent job queuing."""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from backend.core.database import database
from backend.core.models import Job, JobStatus, JobStage, QualityPreset

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Persistent queue manager for transcription jobs.

    Replaces the old DeduplicatedQueue with a database-backed solution that:
    - Persists jobs across restarts
    - Supports priority queuing
    - Prevents duplicate jobs
    - Provides visibility into queue state
    - Thread-safe operations
    """

    def __init__(self):
        """Initialize queue manager."""
        self.db = database
        logger.info("QueueManager initialized")

    def add_job(
        self,
        file_path: str,
        file_name: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        quality_preset: QualityPreset = QualityPreset.FAST,
        transcribe_or_translate: str = "transcribe",
        priority: int = 0,
        bazarr_callback_url: Optional[str] = None,
        is_manual_request: bool = False,
        job_type: Optional['JobType'] = None,
    ) -> Optional[Job]:
        """
        Add a new job to the queue.

        Args:
            file_path: Full path to the media file
            file_name: Name of the file
            source_lang: Source language code (ISO 639-2)
            target_lang: Target language code (ISO 639-2)
            quality_preset: Quality preset (fast/balanced/best)
            transcribe_or_translate: Operation type
            priority: Job priority (higher = processed first)
            bazarr_callback_url: Callback URL for Bazarr provider mode
            is_manual_request: Whether this is a manual request (higher priority)
            job_type: Type of job (transcription or language_detection)

        Returns:
            Job object if created, None if duplicate exists
        """
        from backend.core.models import JobType

        if job_type is None:
            job_type = JobType.TRANSCRIPTION
        with self.db.get_session() as session:
            # Check for existing job
            existing = self._find_existing_job(session, file_path, target_lang)

            if existing:
                logger.warning(
                    f"Duplicate job detected for {file_name}: "
                    f"Existing job {existing.id} [{existing.status.value}] "
                    f"target={target_lang}, path={file_path}"
                )

                # If existing job failed and can retry, reset it
                if existing.can_retry:
                    logger.info(f"Auto-retrying failed job {existing.id}")
                    existing.status = JobStatus.QUEUED
                    existing.error = None
                    existing.current_stage = JobStage.PENDING
                    existing.progress = 0.0
                    session.commit()
                    return existing

                logger.info(f"Job {existing.id} cannot be auto-retried (status: {existing.status.value})")
                return None

            # Create new job
            job = Job(
                file_path=file_path,
                file_name=file_name,
                job_type=job_type,
                source_lang=source_lang,
                target_lang=target_lang,
                quality_preset=quality_preset,
                transcribe_or_translate=transcribe_or_translate,
                priority=priority + (10 if is_manual_request else 0),  # Boost manual requests
                bazarr_callback_url=bazarr_callback_url,
                is_manual_request=is_manual_request,
            )

            session.add(job)
            session.commit()

            # Access all attributes before session closes to ensure they're loaded
            job_id = job.id
            job_status = job.status

            logger.info(
                f"Job {job_id} added to queue: {file_name} "
                f"[{quality_preset.value}] priority={job.priority}"
            )

        # Re-query the job in a new session to return a fresh copy
        with self.db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if job:
                session.expunge(job)  # Remove from session so it doesn't expire
            return job

    def get_next_job(self, worker_id: str) -> Optional[Job]:
        """
        Get the next job from the queue for processing.

        Jobs are selected based on:
        1. Status = QUEUED
        2. Priority (DESC)
        3. Created time (ASC) - FIFO within same priority

        Args:
            worker_id: ID of the worker requesting the job

        Returns:
            Job object or None if queue is empty
        """
        with self.db.get_session() as session:
            job = (
                session.query(Job)
                .filter(Job.status == JobStatus.QUEUED)
                .order_by(
                    Job.priority.desc(),
                    Job.created_at.asc()
                )
                .with_for_update(skip_locked=True)  # Skip locked rows (concurrent workers)
                .first()
            )

            if job:
                job_id = job.id
                job.mark_started(worker_id)
                session.commit()
                logger.info(f"Job {job_id} assigned to worker {worker_id}")

        # Re-query the job if found
        if job:
            with self.db.get_session() as session:
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    session.expunge(job)  # Remove from session so it doesn't expire
                return job

        return None

    def get_job_by_id(self, job_id: str) -> Optional[Job]:
        """Get a specific job by ID."""
        with self.db.get_session() as session:
            return session.query(Job).filter(Job.id == job_id).first()

    def update_job_progress(
        self,
        job_id: str,
        progress: float,
        stage: JobStage,
        eta_seconds: Optional[int] = None
    ) -> bool:
        """
        Update job progress.

        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
            stage: Current processing stage
            eta_seconds: Estimated time to completion

        Returns:
            True if updated successfully, False otherwise
        """
        with self.db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()

            if not job:
                logger.warning(f"Job {job_id} not found for progress update")
                return False

            job.update_progress(progress, stage, eta_seconds)
            session.commit()

            logger.debug(
                f"Job {job_id} progress: {progress:.1f}% [{stage.value}] ETA: {eta_seconds}s"
            )
            return True

    def mark_job_completed(
        self,
        job_id: str,
        output_path: str,
        segments_count: int,
        srt_content: Optional[str] = None,
        model_used: Optional[str] = None,
        device_used: Optional[str] = None,
        processing_time_seconds: Optional[float] = None,
        detected_language: Optional[str] = None
    ) -> bool:
        """Mark a job as completed."""
        with self.db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()

            if not job:
                logger.warning(f"Job {job_id} not found for completion")
                return False

            job.mark_completed(output_path, segments_count, srt_content)

            # Set optional metadata if provided
            if model_used:
                job.model_used = model_used
            if device_used:
                job.device_used = device_used
            if processing_time_seconds is not None:
                job.processing_time_seconds = processing_time_seconds
            if detected_language:
                job.source_lang = detected_language

            session.commit()

            logger.info(
                f"Job {job_id} completed: {output_path} "
                f"({segments_count} segments, {job.processing_time_seconds:.1f}s)"
            )
            return True

    def mark_job_failed(self, job_id: str, error: str) -> bool:
        """Mark a job as failed."""
        with self.db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()

            if not job:
                logger.warning(f"Job {job_id} not found for failure marking")
                return False

            job.mark_failed(error)
            session.commit()

            logger.error(
                f"Job {job_id} failed (attempt #{job.retry_count}): {error}"
            )
            return True

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued or processing job."""
        with self.db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()

            if not job:
                logger.warning(f"Job {job_id} not found for cancellation")
                return False

            if job.is_terminal_state:
                logger.warning(f"Job {job_id} is already in terminal state: {job.status.value}")
                return False

            job.mark_cancelled()
            session.commit()

            logger.info(f"Job {job_id} cancelled")
            return True

    def get_queue_stats(self) -> Dict:
        """Get queue statistics."""
        with self.db.get_session() as session:
            total = session.query(Job).count()
            queued = session.query(Job).filter(Job.status == JobStatus.QUEUED).count()
            processing = session.query(Job).filter(Job.status == JobStatus.PROCESSING).count()
            completed = session.query(Job).filter(Job.status == JobStatus.COMPLETED).count()
            failed = session.query(Job).filter(Job.status == JobStatus.FAILED).count()

            # Get today's stats
            today = datetime.now(timezone.utc).date()
            completed_today = (
                session.query(Job)
                .filter(
                    Job.status == JobStatus.COMPLETED,
                    Job.completed_at >= today
                )
                .count()
            )
            failed_today = (
                session.query(Job)
                .filter(
                    Job.status == JobStatus.FAILED,
                    Job.completed_at >= today
                )
                .count()
            )

            return {
                "total": total,
                "queued": queued,
                "processing": processing,
                "completed": completed,
                "failed": failed,
                "completed_today": completed_today,
                "failed_today": failed_today,
            }

    def get_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Job]:
        """
        Get jobs with optional filtering.

        Args:
            status: Filter by status
            limit: Maximum number of jobs to return
            offset: Offset for pagination

        Returns:
            List of Job objects
        """
        with self.db.get_session() as session:
            query = session.query(Job)

            if status:
                query = query.filter(Job.status == status)

            jobs = (
                query
                .order_by(Job.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return jobs

    def get_all_jobs(
        self,
        status_filter: Optional[JobStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Job]:
        """
        Get all jobs with optional filtering.

        Args:
            status_filter: Filter by status
            limit: Maximum number of jobs to return
            offset: Offset for pagination

        Returns:
            List of Job objects (detached from session)
        """
        with self.db.get_session() as session:
            query = session.query(Job)

            if status_filter:
                query = query.filter(Job.status == status_filter)

            jobs = (
                query
                .order_by(Job.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            # Expunge all jobs from session so they don't expire
            for job in jobs:
                session.expunge(job)

            return jobs

    def count_jobs(self, status_filter: Optional[JobStatus] = None) -> int:
        """
        Count jobs with optional filtering.

        Args:
            status_filter: Filter by status

        Returns:
            Number of jobs
        """
        with self.db.get_session() as session:
            query = session.query(Job)

            if status_filter:
                query = query.filter(Job.status == status_filter)

            return query.count()

    def retry_job(self, job_id: str) -> bool:
        """
        Retry a failed job.

        Args:
            job_id: Job ID to retry

        Returns:
            True if job was reset to queued, False otherwise
        """
        with self.db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()

            if not job:
                logger.warning(f"Job {job_id} not found for retry")
                return False

            if not job.can_retry:
                logger.warning(f"Job {job_id} cannot be retried")
                return False

            # Reset job to queued
            job.status = JobStatus.QUEUED
            job.error = None
            job.current_stage = JobStage.PENDING
            job.progress = 0.0
            job.worker_id = None
            job.retry_count += 1  # Increment retry count for tracking
            session.commit()

            logger.info(f"Job {job_id} reset for retry (attempt #{job.retry_count})")
            return True

    def clear_completed_jobs(self) -> int:
        """
        Clear all completed jobs.

        Returns:
            Number of jobs cleared
        """
        with self.db.get_session() as session:
            deleted = (
                session.query(Job)
                .filter(Job.status == JobStatus.COMPLETED)
                .delete()
            )

            session.commit()

            if deleted > 0:
                logger.info(f"Cleared {deleted} completed jobs")

            return deleted

    def get_processing_jobs(self) -> List[Job]:
        """Get all currently processing jobs."""
        return self.get_jobs(status=JobStatus.PROCESSING)

    def get_queued_jobs(self) -> List[Job]:
        """Get all queued jobs."""
        return self.get_jobs(status=JobStatus.QUEUED)

    def is_queue_empty(self) -> bool:
        """Check if queue has any pending jobs."""
        with self.db.get_session() as session:
            count = (
                session.query(Job)
                .filter(Job.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING]))
                .count()
            )
            return count == 0

    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Delete completed/failed jobs older than specified days.

        Args:
            days: Number of days to keep jobs

        Returns:
            Number of jobs deleted
        """
        with self.db.get_session() as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            deleted = (
                session.query(Job)
                .filter(
                    Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]),
                    Job.completed_at < cutoff_date
                )
                .delete()
            )

            session.commit()

            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old jobs (older than {days} days)")

            return deleted

    def _find_existing_job(
        self,
        session: Session,
        file_path: str,
        target_lang: Optional[str]
    ) -> Optional[Job]:
        """
        Find existing job for the same file and target language.

        Ignores completed jobs - allows re-transcription.
        """
        query = session.query(Job).filter(
            Job.file_path == file_path,
            Job.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING])
        )

        if target_lang:
            query = query.filter(Job.target_lang == target_lang)

        return query.first()

    def cleanup_orphaned_jobs(self) -> int:
        """
        Clean up orphaned jobs after server restart.

        Jobs stuck in 'processing' state with no active worker are marked as failed.
        This prevents jobs from being stuck forever after a restart.

        Returns:
            Number of jobs cleaned up
        """
        from datetime import datetime

        with self.db.get_session() as session:
            # Find all jobs in processing state
            orphaned_jobs = session.query(Job).filter(
                Job.status == JobStatus.PROCESSING
            ).all()

            cleaned_count = 0
            for job in orphaned_jobs:
                # Mark as failed with appropriate error message
                job.status = JobStatus.FAILED
                job.error = "Job interrupted by server restart"
                job.completed_at = datetime.now(timezone.utc)
                job.progress = 0.0
                job.current_stage = JobStage.PENDING
                job.worker_id = None

                logger.warning(
                    f"Cleaned up orphaned job {job.id} ({job.file_name}) - "
                    f"was stuck in processing state"
                )
                cleaned_count += 1

            session.commit()

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} orphaned job(s) after restart")

            return cleaned_count


# Global queue manager instance
queue_manager = QueueManager()

