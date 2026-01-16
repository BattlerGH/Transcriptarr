"""Configuration management for TranscriptorIO.

Most configuration is now stored in the database and managed through the
Settings service. Only DATABASE_URL is loaded from environment variables.

For runtime configuration, use:
    from backend.core.settings_service import settings_service
    value = settings_service.get("setting_key", default_value)
"""
from enum import Enum
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class DatabaseType(str, Enum):
    """Supported database backends."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MARIADB = "mariadb"
    MYSQL = "mysql"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Only DATABASE_URL is required. All other configuration is stored
    in the database and managed through the Settings API/UI.
    """

    # === Database Configuration (REQUIRED) ===
    database_url: str = Field(
        default="sqlite:///./transcriptarr.db",
        description="Database connection URL"
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        valid_prefixes = (
            "sqlite://",
            "postgresql://",
            "mariadb+pymysql://",
            "mysql+pymysql://"
        )
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(
                f"Invalid database URL. Must start with one of: {valid_prefixes}"
            )
        return v

    @property
    def database_type(self) -> DatabaseType:
        """Get the database type from the URL."""
        if self.database_url.startswith("sqlite"):
            return DatabaseType.SQLITE
        elif self.database_url.startswith("postgresql"):
            return DatabaseType.POSTGRESQL
        elif "mariadb" in self.database_url:
            return DatabaseType.MARIADB
        elif "mysql" in self.database_url:
            return DatabaseType.MYSQL
        else:
            raise ValueError(f"Unknown database type in URL: {self.database_url}")

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
