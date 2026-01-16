"""Database model for system settings."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from backend.core.database import Base


class SystemSettings(Base):
    """
    System settings stored in database.

    Replaces .env configuration for dynamic settings management through WebUI.
    Settings are organized by category and support different value types.
    """

    __tablename__ = "system_settings"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Setting identification
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=True)  # Store as string, parse based on value_type

    # Metadata
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)  # general, workers, transcription, scanner, bazarr
    value_type = Column(String(50), nullable=True)  # string, integer, boolean, float, list

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        """String representation."""
        return f"<SystemSettings {self.key}={self.value}>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "category": self.category,
            "value_type": self.value_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_parsed_value(self):
        """
        Parse value based on value_type.

        Returns:
            Parsed value in appropriate Python type
        """
        if self.value is None:
            return None

        if self.value_type == "boolean":
            return self.value.lower() in ("true", "1", "yes", "on")
        elif self.value_type == "integer":
            return int(self.value)
        elif self.value_type == "float":
            return float(self.value)
        elif self.value_type == "list":
            # Comma-separated values
            return [v.strip() for v in self.value.split(",") if v.strip()]
        else:  # string or unknown
            return self.value


