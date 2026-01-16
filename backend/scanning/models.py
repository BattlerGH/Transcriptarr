"""Database models for library scanning rules."""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index
from sqlalchemy.sql import func

from backend.core.database import Base


class ScanRule(Base):
    """
    Scan rule for filtering media files in standalone mode.

    Rules define conditions that files must match and actions to take when matched.
    Example: "All Japanese audio without Spanish subtitles should be transcribed to Spanish"
    """

    __tablename__ = "scan_rules"

    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False, unique=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    priority = Column(Integer, nullable=False, default=0, index=True)

    # === CONDITION FILTERS (all must match for rule to apply) ===

    # Audio language filters
    audio_language_is = Column(String(10), nullable=True)
    """Audio track language must be this (ISO 639-1). Example: 'ja'"""

    audio_language_not = Column(String(64), nullable=True)
    """Audio track language must NOT be any of these (comma-separated). Example: 'en,es'"""

    audio_track_count_min = Column(Integer, nullable=True)
    """Minimum number of audio tracks required"""

    # Subtitle filters
    has_embedded_subtitle_lang = Column(String(10), nullable=True)
    """Must have embedded subtitle in this language. Example: 'en'"""

    missing_embedded_subtitle_lang = Column(String(10), nullable=True)
    """Must NOT have embedded subtitle in this language. Example: 'es'"""

    missing_external_subtitle_lang = Column(String(10), nullable=True)
    """Must NOT have external .srt file in this language. Example: 'es'"""

    # File format filters
    file_extension = Column(String(64), nullable=True)
    """File extension filter (comma-separated). Example: '.mkv,.mp4'"""

    # === ACTION (what to do when rule matches) ===

    action_type = Column(String(20), nullable=False, default="transcribe")
    """Action: 'transcribe' or 'translate'"""

    target_language = Column(String(10), nullable=False)
    """Target subtitle language (ISO 639-1). Example: 'es'"""

    quality_preset = Column(String(20), nullable=False, default="fast")
    """Quality preset: 'fast', 'balanced', or 'best'"""

    job_priority = Column(Integer, nullable=False, default=0)
    """Priority for jobs created by this rule (higher = processed first)"""

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        """String representation."""
        return f"<ScanRule {self.id}: {self.name} [{'enabled' if self.enabled else 'disabled'}]>"

    def to_dict(self) -> dict:
        """Convert rule to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "priority": self.priority,
            "conditions": {
                "audio_language_is": self.audio_language_is,
                "audio_language_not": self.audio_language_not,
                "audio_track_count_min": self.audio_track_count_min,
                "has_embedded_subtitle_lang": self.has_embedded_subtitle_lang,
                "missing_embedded_subtitle_lang": self.missing_embedded_subtitle_lang,
                "missing_external_subtitle_lang": self.missing_external_subtitle_lang,
                "file_extension": self.file_extension,
            },
            "action": {
                "action_type": self.action_type,
                "target_language": self.target_language,
                "quality_preset": self.quality_preset,
                "job_priority": self.job_priority,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def audio_language_not_list(self) -> List[str]:
        """Get audio_language_not as a list."""
        if not self.audio_language_not:
            return []
        return [lang.strip() for lang in self.audio_language_not.split(",") if lang.strip()]

    @property
    def file_extension_list(self) -> List[str]:
        """Get file_extension as a list."""
        if not self.file_extension:
            return []
        return [ext.strip() for ext in self.file_extension.split(",") if ext.strip()]


# Create indexes for common queries
Index('idx_scan_rules_enabled_priority', ScanRule.enabled, ScanRule.priority.desc())
Index('idx_scan_rules_name', ScanRule.name)
