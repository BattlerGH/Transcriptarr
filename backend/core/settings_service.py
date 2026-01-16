"""Settings service for database-backed configuration."""
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.exc import IntegrityError

from backend.core.database import database
from backend.core.settings_model import SystemSettings

logger = logging.getLogger(__name__)


class SettingsService:
    """
    Service for managing system settings in database.

    Provides caching and type-safe access to settings.
    Settings are organized by category: general, workers, transcription, scanner, bazarr
    """

    def __init__(self):
        """Initialize settings service."""
        self._cache: Dict[str, Any] = {}
        self._cache_valid = False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value by key.

        Args:
            key: Setting key
            default: Default value if not found

        Returns:
            Parsed setting value or default
        """
        # Refresh cache if needed
        if not self._cache_valid:
            self._load_cache()

        return self._cache.get(key, default)

    def set(self, key: str, value: Any, description: str = None, category: str = None, value_type: str = None) -> bool:
        """
        Set setting value.

        Args:
            key: Setting key
            value: Setting value (will be converted to string)
            description: Optional description
            category: Optional category
            value_type: Optional type (string, integer, boolean, float, list)

        Returns:
            True if successful
        """
        with database.get_session() as session:
            setting = session.query(SystemSettings).filter(SystemSettings.key == key).first()

            if setting:
                # Update existing
                setting.value = str(value) if value is not None else None
                if description:
                    setting.description = description
                if category:
                    setting.category = category
                if value_type:
                    setting.value_type = value_type
            else:
                # Create new
                setting = SystemSettings(
                    key=key,
                    value=str(value) if value is not None else None,
                    description=description,
                    category=category,
                    value_type=value_type or "string"
                )
                session.add(setting)

            session.commit()

            # Invalidate cache
            self._cache_valid = False

            logger.info(f"Setting updated: {key}={value}")
            return True

    def get_by_category(self, category: str) -> List[SystemSettings]:
        """
        Get all settings in a category.

        Args:
            category: Category name

        Returns:
            List of SystemSettings objects
        """
        with database.get_session() as session:
            settings = session.query(SystemSettings).filter(
                SystemSettings.category == category
            ).all()

            # Detach from session
            for setting in settings:
                session.expunge(setting)

            return settings

    def get_all(self) -> List[SystemSettings]:
        """
        Get all settings.

        Returns:
            List of SystemSettings objects
        """
        with database.get_session() as session:
            settings = session.query(SystemSettings).all()

            # Detach from session
            for setting in settings:
                session.expunge(setting)

            return settings

    def delete(self, key: str) -> bool:
        """
        Delete a setting.

        Args:
            key: Setting key

        Returns:
            True if deleted, False if not found
        """
        with database.get_session() as session:
            setting = session.query(SystemSettings).filter(SystemSettings.key == key).first()

            if not setting:
                return False

            session.delete(setting)
            session.commit()

            # Invalidate cache
            self._cache_valid = False

            logger.info(f"Setting deleted: {key}")
            return True

    def bulk_update(self, settings: Dict[str, Any]) -> bool:
        """
        Update multiple settings at once.

        Args:
            settings: Dictionary of key-value pairs

        Returns:
            True if successful
        """
        with database.get_session() as session:
            for key, value in settings.items():
                setting = session.query(SystemSettings).filter(SystemSettings.key == key).first()

                if setting:
                    setting.value = str(value) if value is not None else None
                else:
                    logger.warning(f"Setting not found for bulk update: {key}")

            session.commit()

            # Invalidate cache
            self._cache_valid = False

            logger.info(f"Bulk updated {len(settings)} settings")
            return True

    def init_default_settings(self):
        """
        Initialize default settings if they don't exist.
        Called on first run or after database reset.
        """
        defaults = self._get_default_settings()

        with database.get_session() as session:
            for key, config in defaults.items():
                existing = session.query(SystemSettings).filter(SystemSettings.key == key).first()

                if not existing:
                    setting = SystemSettings(
                        key=key,
                        value=str(config["value"]) if config["value"] is not None else None,
                        description=config.get("description"),
                        category=config.get("category"),
                        value_type=config.get("value_type", "string")
                    )
                    session.add(setting)
                    logger.info(f"Created default setting: {key}")

            session.commit()

        # Invalidate cache
        self._cache_valid = False

        logger.info("Default settings initialized")

    def _load_cache(self):
        """Load all settings into cache."""
        with database.get_session() as session:
            settings = session.query(SystemSettings).all()

            self._cache = {}
            for setting in settings:
                self._cache[setting.key] = setting.get_parsed_value()

            self._cache_valid = True

    def _get_default_settings(self) -> Dict[str, Dict]:
        """
        Get default settings configuration.

        All settings have sensible defaults. Configuration is managed
        through the Web UI Settings page or the Settings API.

        Returns:
            Dictionary of setting configurations
        """
        return {
            # === General ===
            "operation_mode": {
                "value": "standalone",
                "description": "Operation mode: standalone, provider, or standalone,provider",
                "category": "general",
                "value_type": "string"
            },
            "library_paths": {
                "value": "",
                "description": "Comma-separated library paths to scan",
                "category": "general",
                "value_type": "list"
            },
            "api_host": {
                "value": "0.0.0.0",
                "description": "API server host",
                "category": "general",
                "value_type": "string"
            },
            "api_port": {
                "value": "8000",
                "description": "API server port",
                "category": "general",
                "value_type": "integer"
            },
            "debug": {
                "value": "false",
                "description": "Enable debug mode",
                "category": "general",
                "value_type": "boolean"
            },
            "setup_completed": {
                "value": "false",
                "description": "Whether setup wizard has been completed",
                "category": "general",
                "value_type": "boolean"
            },

            # === Workers ===
            "worker_cpu_count": {
                "value": "0",
                "description": "Number of CPU workers to start on boot",
                "category": "workers",
                "value_type": "integer"
            },
            "worker_gpu_count": {
                "value": "0",
                "description": "Number of GPU workers to start on boot",
                "category": "workers",
                "value_type": "integer"
            },
            "concurrent_transcriptions": {
                "value": "2",
                "description": "Maximum concurrent transcriptions",
                "category": "workers",
                "value_type": "integer"
            },
            "worker_healthcheck_interval": {
                "value": "60",
                "description": "Worker health check interval (seconds)",
                "category": "workers",
                "value_type": "integer"
            },
            "worker_auto_restart": {
                "value": "true",
                "description": "Auto-restart failed workers",
                "category": "workers",
                "value_type": "boolean"
            },
            "clear_vram_on_complete": {
                "value": "true",
                "description": "Clear VRAM after job completion",
                "category": "workers",
                "value_type": "boolean"
            },

            # === Whisper/Transcription ===
            "whisper_model": {
                "value": "medium",
                "description": "Whisper model: tiny, base, small, medium, large-v3, large-v3-turbo",
                "category": "transcription",
                "value_type": "string"
            },
            "model_path": {
                "value": "./models",
                "description": "Path to store Whisper models",
                "category": "transcription",
                "value_type": "string"
            },
            "transcribe_device": {
                "value": "cpu",
                "description": "Device for transcription (cpu, cuda, gpu)",
                "category": "transcription",
                "value_type": "string"
            },
            "cpu_compute_type": {
                "value": "auto",
                "description": "CPU compute type (auto, int8, float32)",
                "category": "transcription",
                "value_type": "string"
            },
            "gpu_compute_type": {
                "value": "auto",
                "description": "GPU compute type (auto, float16, float32, int8_float16, int8)",
                "category": "transcription",
                "value_type": "string"
            },
            "whisper_threads": {
                "value": "4",
                "description": "Number of CPU threads for Whisper",
                "category": "transcription",
                "value_type": "integer"
            },
            "transcribe_or_translate": {
                "value": "transcribe",
                "description": "Default mode: transcribe or translate",
                "category": "transcription",
                "value_type": "string"
            },
            "word_level_highlight": {
                "value": "false",
                "description": "Enable word-level highlighting in subtitles",
                "category": "transcription",
                "value_type": "boolean"
            },
            "detect_language_length": {
                "value": "30",
                "description": "Seconds of audio to use for language detection",
                "category": "transcription",
                "value_type": "integer"
            },
            "detect_language_offset": {
                "value": "0",
                "description": "Offset in seconds for language detection sample",
                "category": "transcription",
                "value_type": "integer"
            },

            # === Subtitle Settings ===
            "subtitle_language_name": {
                "value": "",
                "description": "Custom subtitle language name",
                "category": "subtitles",
                "value_type": "string"
            },
            "subtitle_language_naming_type": {
                "value": "ISO_639_2_B",
                "description": "Language naming: ISO_639_1, ISO_639_2_T, ISO_639_2_B, NAME, NATIVE",
                "category": "subtitles",
                "value_type": "string"
            },
            "custom_regroup": {
                "value": "cm_sl=84_sl=42++++++1",
                "description": "Custom regrouping algorithm for subtitles",
                "category": "subtitles",
                "value_type": "string"
            },

            # === Skip Configuration ===
            "skip_if_external_subtitles_exist": {
                "value": "false",
                "description": "Skip if any external subtitle exists",
                "category": "skip",
                "value_type": "boolean"
            },
            "skip_if_target_subtitles_exist": {
                "value": "true",
                "description": "Skip if target language subtitle already exists",
                "category": "skip",
                "value_type": "boolean"
            },
            "skip_if_internal_subtitles_language": {
                "value": "",
                "description": "Skip if internal subtitle in this language exists",
                "category": "skip",
                "value_type": "string"
            },
            "skip_subtitle_languages": {
                "value": "",
                "description": "Pipe-separated language codes to skip",
                "category": "skip",
                "value_type": "list"
            },
            "skip_if_audio_languages": {
                "value": "",
                "description": "Skip if audio track is in these languages",
                "category": "skip",
                "value_type": "list"
            },
            "skip_unknown_language": {
                "value": "false",
                "description": "Skip files with unknown audio language",
                "category": "skip",
                "value_type": "boolean"
            },
            "skip_only_subgen_subtitles": {
                "value": "false",
                "description": "Only skip SubGen-generated subtitles",
                "category": "skip",
                "value_type": "boolean"
            },

            # === Scanner ===
            "scanner_enabled": {
                "value": "true",
                "description": "Enable library scanner",
                "category": "scanner",
                "value_type": "boolean"
            },
            "scanner_cron": {
                "value": "0 2 * * *",
                "description": "Cron expression for scheduled scans",
                "category": "scanner",
                "value_type": "string"
            },
            "watcher_enabled": {
                "value": "false",
                "description": "Enable real-time file watcher",
                "category": "scanner",
                "value_type": "boolean"
            },
            "auto_scan_enabled": {
                "value": "false",
                "description": "Enable automatic scheduled scanning",
                "category": "scanner",
                "value_type": "boolean"
            },
            "scan_interval_minutes": {
                "value": "30",
                "description": "Scan interval in minutes",
                "category": "scanner",
                "value_type": "integer"
            },

            # === Bazarr Provider ===
            "bazarr_provider_enabled": {
                "value": "false",
                "description": "Enable Bazarr provider mode",
                "category": "bazarr",
                "value_type": "boolean"
            },
            "bazarr_url": {
                "value": "http://bazarr:6767",
                "description": "Bazarr server URL",
                "category": "bazarr",
                "value_type": "string"
            },
            "bazarr_api_key": {
                "value": "",
                "description": "Bazarr API key",
                "category": "bazarr",
                "value_type": "string"
            },
            "provider_timeout_seconds": {
                "value": "600",
                "description": "Provider request timeout in seconds",
                "category": "bazarr",
                "value_type": "integer"
            },
            "provider_callback_enabled": {
                "value": "true",
                "description": "Enable callback to Bazarr on completion",
                "category": "bazarr",
                "value_type": "boolean"
            },
            "provider_polling_interval": {
                "value": "30",
                "description": "Polling interval for Bazarr jobs",
                "category": "bazarr",
                "value_type": "integer"
            },

            # === Advanced ===
            "force_detected_language_to": {
                "value": "",
                "description": "Force detected language to specific code",
                "category": "advanced",
                "value_type": "string"
            },
            "preferred_audio_languages": {
                "value": "eng",
                "description": "Pipe-separated preferred audio languages",
                "category": "advanced",
                "value_type": "list"
            },
            "use_path_mapping": {
                "value": "false",
                "description": "Enable path mapping for network shares",
                "category": "advanced",
                "value_type": "boolean"
            },
            "path_mapping_from": {
                "value": "/tv",
                "description": "Path mapping source",
                "category": "advanced",
                "value_type": "string"
            },
            "path_mapping_to": {
                "value": "/Volumes/TV",
                "description": "Path mapping destination",
                "category": "advanced",
                "value_type": "string"
            },
            "lrc_for_audio_files": {
                "value": "true",
                "description": "Generate LRC files for audio-only files",
                "category": "advanced",
                "value_type": "boolean"
            },
        }


# Global settings service instance
settings_service = SettingsService()

