"""Model for storing detected audio languages."""
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.sql import func

from backend.core.database import Base


class DetectedLanguage(Base):
    """
    Stores detected audio languages for files where metadata is undefined.

    This cache prevents re-detecting the same file multiple times.
    """

    __tablename__ = "detected_languages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String(1024), nullable=False, unique=True, index=True)
    detected_language = Column(String(10), nullable=False)  # ISO 639-1 code
    detection_confidence = Column(Integer, nullable=True)  # 0-100
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_detected_lang_path', 'file_path'),
        Index('idx_detected_lang_language', 'detected_language'),
    )

    def __repr__(self):
        return f"<DetectedLanguage {self.file_path}: {self.detected_language}>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "detected_language": self.detected_language,
            "detection_confidence": self.detection_confidence,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
        }

