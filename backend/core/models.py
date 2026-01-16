"""Database models for Transcriptarr."""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, Boolean, Enum as SQLEnum, Index
)
from sqlalchemy.sql import func

from backend.core.database import Base


class JobType(str, Enum):
    """Job type classification."""
    TRANSCRIPTION = "transcription"      # Regular transcription/translation job
    LANGUAGE_DETECTION = "language_detection"  # Language detection only


class JobStatus(str, Enum):
    """Job status states."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStage(str, Enum):
    """Job processing stages."""
    PENDING = "pending"
    LOADING_MODEL = "loading_model"
    DETECTING_LANGUAGE = "detecting_language"
    LANGUAGE_DETECTION = "language_detection"  # Alias for backward compatibility
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    TRANSLATING = "translating"
    GENERATING_SUBTITLES = "generating_subtitles"
    POST_PROCESSING = "post_processing"
    FINALIZING = "finalizing"


class QualityPreset(str, Enum):
    """Quality presets for transcription."""
    FAST = "fast"          # ja→en→es with Helsinki-NLP (4GB VRAM)
    BALANCED = "balanced"  # ja→ja→es with M2M100 (6GB VRAM)
    BEST = "best"          # ja→es direct with SeamlessM4T (10GB+ VRAM)


class Job(Base):
    """Job model representing a transcription task."""

    __tablename__ = "jobs"

    # Primary identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_path = Column(String(1024), nullable=False, index=True)
    file_name = Column(String(512), nullable=False)

    # Job classification
    job_type = Column(
        SQLEnum(JobType),
        nullable=False,
        default=JobType.TRANSCRIPTION,
        index=True
    )

    # Job status
    status = Column(
        SQLEnum(JobStatus),
        nullable=False,
        default=JobStatus.QUEUED,
        index=True
    )
    priority = Column(Integer, nullable=False, default=0, index=True)

    # Configuration
    source_lang = Column(String(10), nullable=True)
    target_lang = Column(String(10), nullable=True)
    quality_preset = Column(
        SQLEnum(QualityPreset),
        nullable=False,
        default=QualityPreset.FAST
    )
    transcribe_or_translate = Column(String(20), nullable=False, default="transcribe")

    # Progress tracking
    progress = Column(Float, nullable=False, default=0.0)  # 0-100
    current_stage = Column(
        SQLEnum(JobStage),
        nullable=False,
        default=JobStage.PENDING
    )
    eta_seconds = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Results
    output_path = Column(String(1024), nullable=True)
    srt_content = Column(Text, nullable=True)
    segments_count = Column(Integer, nullable=True)

    # Error handling
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)

    # Worker information
    worker_id = Column(String(64), nullable=True)
    vram_used_mb = Column(Integer, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)

    # Provider mode specific
    bazarr_callback_url = Column(String(512), nullable=True)
    is_manual_request = Column(Boolean, nullable=False, default=False)

    # Additional metadata
    model_used = Column(String(64), nullable=True)
    device_used = Column(String(32), nullable=True)
    compute_type = Column(String(32), nullable=True)

    def __repr__(self):
        """String representation of Job."""
        return f"<Job {self.id[:8]}... {self.file_name} [{self.status.value}] {self.progress:.1f}%>"

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return None

    @property
    def is_terminal_state(self) -> bool:
        """Check if job is in a terminal state (completed/failed/cancelled)."""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)

    @property
    def can_retry(self) -> bool:
        """Check if job can be retried. Always allow retry for failed jobs."""
        return self.status == JobStatus.FAILED

    def to_dict(self) -> dict:
        """Convert job to dictionary for API responses."""
        def format_datetime(dt):
            """Format datetime as ISO string with UTC timezone."""
            if not dt:
                return None
            # If timezone-naive, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        return {
            "id": self.id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "job_type": self.job_type.value if self.job_type else "transcription",
            "status": self.status.value,
            "priority": self.priority,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "quality_preset": self.quality_preset.value if self.quality_preset else None,
            "transcribe_or_translate": self.transcribe_or_translate,
            "progress": self.progress,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "eta_seconds": self.eta_seconds,
            "created_at": format_datetime(self.created_at),
            "started_at": format_datetime(self.started_at),
            "completed_at": format_datetime(self.completed_at),
            "output_path": self.output_path,
            "segments_count": self.segments_count,
            "error": self.error,
            "retry_count": self.retry_count,
            "worker_id": self.worker_id,
            "vram_used_mb": self.vram_used_mb,
            "processing_time_seconds": self.processing_time_seconds,
            "model_used": self.model_used,
            "device_used": self.device_used,
        }

    def update_progress(self, progress: float, stage: JobStage, eta_seconds: Optional[int] = None):
        """Update job progress."""
        self.progress = min(100.0, max(0.0, progress))
        self.current_stage = stage
        if eta_seconds is not None:
            self.eta_seconds = eta_seconds

    def mark_started(self, worker_id: str):
        """Mark job as started."""
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.now(timezone.utc)
        self.worker_id = worker_id

    def mark_completed(self, output_path: str, segments_count: int, srt_content: Optional[str] = None):
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.output_path = output_path
        self.segments_count = segments_count
        self.srt_content = srt_content
        self.progress = 100.0
        self.current_stage = JobStage.FINALIZING

        if self.started_at:
            # Handle both timezone-aware and timezone-naive datetimes
            started = self.started_at
            if started.tzinfo is None:
                # Convert naive datetime to UTC timezone-aware
                started = started.replace(tzinfo=timezone.utc)
            self.processing_time_seconds = (self.completed_at - started).total_seconds()

    def mark_failed(self, error: str):
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error
        self.retry_count += 1

    def mark_cancelled(self):
        """Mark job as cancelled."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)


# Create indexes for common queries
Index('idx_jobs_status_priority', Job.status, Job.priority.desc(), Job.created_at)
Index('idx_jobs_created', Job.created_at.desc())
Index('idx_jobs_file_path', Job.file_path)