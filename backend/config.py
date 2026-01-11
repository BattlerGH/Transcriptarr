"""Configuration management for TranscriptorIO."""
import os
from enum import Enum
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class OperationMode(str, Enum):
    """Operation modes for TranscriptorIO."""
    STANDALONE = "standalone"
    PROVIDER = "provider"
    HYBRID = "standalone,provider"


class DatabaseType(str, Enum):
    """Supported database backends."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MARIADB = "mariadb"
    MYSQL = "mysql"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # === Application Mode ===
    transcriptarr_mode: str = Field(
        default="standalone",
        description="Operation mode: standalone, provider, or standalone,provider"
    )

    # === Database Configuration ===
    database_url: str = Field(
        default="sqlite:///./transcriptarr.db",
        description="Database connection URL. Examples:\n"
                    "  SQLite: sqlite:///./transcriptarr.db\n"
                    "  PostgreSQL: postgresql://user:pass@localhost/transcriptarr\n"
                    "  MariaDB: mariadb+pymysql://user:pass@localhost/transcriptarr"
    )

    # === Worker Configuration ===
    concurrent_transcriptions: int = Field(default=2, ge=1, le=10)
    whisper_threads: int = Field(default=4, ge=1, le=32)
    transcribe_device: str = Field(default="cpu", pattern="^(cpu|gpu|cuda)$")
    clear_vram_on_complete: bool = Field(default=True)

    # === Whisper Model Configuration ===
    whisper_model: str = Field(
        default="medium",
        description="Whisper model: tiny, base, small, medium, large-v3, etc."
    )
    model_path: str = Field(default="./models")
    compute_type: str = Field(default="auto")

    # === Standalone Mode Configuration ===
    library_paths: Optional[str] = Field(
        default=None,
        description="Pipe-separated paths to scan: /media/anime|/media/movies"
    )
    auto_scan_enabled: bool = Field(default=False)
    scan_interval_minutes: int = Field(default=30, ge=1)

    required_audio_language: Optional[str] = Field(
        default=None,
        description="Only process files with this audio language (ISO 639-2)"
    )
    required_missing_subtitle: Optional[str] = Field(
        default=None,
        description="Only process if this subtitle language is missing (ISO 639-2)"
    )
    skip_if_subtitle_exists: bool = Field(default=True)

    # === Provider Mode Configuration ===
    bazarr_url: Optional[str] = Field(default=None)
    bazarr_api_key: Optional[str] = Field(default=None)
    provider_timeout_seconds: int = Field(default=600, ge=60)
    provider_callback_enabled: bool = Field(default=True)
    provider_polling_interval: int = Field(default=30, ge=10)

    # === API Configuration ===
    webhook_port: int = Field(default=9000, ge=1024, le=65535)
    api_host: str = Field(default="0.0.0.0")
    debug: bool = Field(default=True)

    # === Transcription Settings ===
    transcribe_or_translate: str = Field(
        default="transcribe",
        pattern="^(transcribe|translate)$"
    )
    subtitle_language_name: str = Field(default="")
    subtitle_language_naming_type: str = Field(
        default="ISO_639_2_B",
        description="Naming format: ISO_639_1, ISO_639_2_T, ISO_639_2_B, NAME, NATIVE"
    )
    word_level_highlight: bool = Field(default=False)
    custom_regroup: str = Field(default="cm_sl=84_sl=42++++++1")

    # === Skip Configuration ===
    skip_if_external_subtitles_exist: bool = Field(default=False)
    skip_if_target_subtitles_exist: bool = Field(default=True)
    skip_if_internal_subtitles_language: Optional[str] = Field(default="eng")
    skip_subtitle_languages: Optional[str] = Field(
        default=None,
        description="Pipe-separated language codes to skip: eng|spa"
    )
    skip_if_audio_languages: Optional[str] = Field(
        default=None,
        description="Skip if audio track is in these languages: eng|spa"
    )
    skip_unknown_language: bool = Field(default=False)
    skip_only_subgen_subtitles: bool = Field(default=False)

    # === Advanced Settings ===
    force_detected_language_to: Optional[str] = Field(default=None)
    detect_language_length: int = Field(default=30, ge=5)
    detect_language_offset: int = Field(default=0, ge=0)
    should_whisper_detect_audio_language: bool = Field(default=False)

    preferred_audio_languages: str = Field(
        default="eng",
        description="Pipe-separated list in order of preference: eng|jpn"
    )

    # === Path Mapping ===
    use_path_mapping: bool = Field(default=False)
    path_mapping_from: str = Field(default="/tv")
    path_mapping_to: str = Field(default="/Volumes/TV")

    # === Legacy SubGen Compatibility ===
    show_in_subname_subgen: bool = Field(default=True)
    show_in_subname_model: bool = Field(default=True)
    append: bool = Field(default=False)
    lrc_for_audio_files: bool = Field(default=True)

    @field_validator("transcriptarr_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Validate operation mode."""
        valid_modes = {"standalone", "provider", "standalone,provider"}
        if v not in valid_modes:
            raise ValueError(f"Invalid mode: {v}. Must be one of: {valid_modes}")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        valid_prefixes = ("sqlite://", "postgresql://", "mariadb+pymysql://", "mysql+pymysql://")
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

    @property
    def is_standalone_mode(self) -> bool:
        """Check if standalone mode is enabled."""
        return "standalone" in self.transcriptarr_mode

    @property
    def is_provider_mode(self) -> bool:
        """Check if provider mode is enabled."""
        return "provider" in self.transcriptarr_mode

    @property
    def library_paths_list(self) -> List[str]:
        """Get library paths as a list."""
        if not self.library_paths:
            return []
        return [p.strip() for p in self.library_paths.split("|") if p.strip()]

    @property
    def skip_subtitle_languages_list(self) -> List[str]:
        """Get skip subtitle languages as a list."""
        if not self.skip_subtitle_languages:
            return []
        return [lang.strip() for lang in self.skip_subtitle_languages.split("|") if lang.strip()]

    @property
    def skip_audio_languages_list(self) -> List[str]:
        """Get skip audio languages as a list."""
        if not self.skip_if_audio_languages:
            return []
        return [lang.strip() for lang in self.skip_if_audio_languages.split("|") if lang.strip()]

    @property
    def preferred_audio_languages_list(self) -> List[str]:
        """Get preferred audio languages as a list."""
        return [lang.strip() for lang in self.preferred_audio_languages.split("|") if lang.strip()]

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
