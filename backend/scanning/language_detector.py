"""Language detection service using Whisper."""
import logging
from typing import Optional, Tuple
from pathlib import Path

from backend.scanning.detected_languages import DetectedLanguage
from backend.core.language_code import LanguageCode

logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    Service for detecting audio language in media files.

    Uses Whisper's language detection on a small audio sample.
    Results are cached in database to avoid re-detection.
    """

    @staticmethod
    def detect_language(file_path: str, sample_duration: int = 30) -> Tuple[Optional[LanguageCode], Optional[int]]:
        """
        Detect language of audio in a media file.

        First checks cache, then uses Whisper if needed.

        Args:
            file_path: Path to media file
            sample_duration: Seconds of audio to analyze (default: 30)

        Returns:
            Tuple of (LanguageCode, confidence_percentage) or (None, None)
        """
        # Check cache first
        cached = LanguageDetector._get_cached_language(file_path)
        if cached:
            logger.info(f"Using cached language for {Path(file_path).name}: {cached}")
            # When returning from cache, we don't have confidence stored, use 100%
            return cached, 100

        # Detect using Whisper
        try:
            detected_lang, confidence = LanguageDetector._detect_with_whisper(
                file_path, sample_duration
            )

            if detected_lang:
                # Cache the result
                LanguageDetector._cache_language(file_path, detected_lang, confidence)
                logger.info(
                    f"Detected language for {Path(file_path).name}: "
                    f"{detected_lang} (confidence: {confidence}%)"
                )
                return detected_lang, confidence

            return None, None

        except Exception as e:
            logger.error(f"Language detection failed for {file_path}: {e}")
            return None, None

    @staticmethod
    def _get_cached_language(file_path: str) -> Optional[LanguageCode]:
        """
        Get cached detected language from database.

        Args:
            file_path: Path to media file

        Returns:
            LanguageCode if cached, None otherwise
        """
        from backend.core.database import database

        with database.get_session() as session:
            cached = session.query(DetectedLanguage).filter(
                DetectedLanguage.file_path == file_path
            ).first()

            if cached:
                return LanguageCode.from_string(cached.detected_language)

            return None

    @staticmethod
    def _cache_language(
        file_path: str,
        language: LanguageCode,
        confidence: Optional[int] = None
    ):
        """
        Cache detected language in database.

        Args:
            file_path: Path to media file
            language: Detected language code
            confidence: Detection confidence (0-100)
        """
        from backend.core.database import database

        with database.get_session() as session:
            # Check if entry exists
            existing = session.query(DetectedLanguage).filter(
                DetectedLanguage.file_path == file_path
            ).first()

            lang_code = language.to_iso_639_1() if language else "und"

            if existing:
                # Update existing
                existing.detected_language = lang_code
                existing.detection_confidence = confidence
            else:
                # Create new
                detected = DetectedLanguage(
                    file_path=file_path,
                    detected_language=lang_code,
                    detection_confidence=confidence
                )
                session.add(detected)

            session.commit()
            logger.debug(f"Cached language detection: {file_path} -> {lang_code}")

    @staticmethod
    def _detect_with_whisper(
        file_path: str,
        sample_duration: int = 30
    ) -> Tuple[Optional[LanguageCode], Optional[int]]:
        """
        Detect language using Whisper model.

        Args:
            file_path: Path to media file
            sample_duration: Seconds of audio to analyze

        Returns:
            Tuple of (LanguageCode, confidence_percentage) or (None, None)
        """
        try:
            from backend.transcription.transcriber import WhisperTranscriber, WHISPER_AVAILABLE
            from backend.transcription.audio_utils import extract_audio_segment

            if not WHISPER_AVAILABLE:
                logger.error("Whisper not available - cannot detect language")
                return None, None

            # Get file duration first to extract from the middle
            import ffmpeg
            try:
                probe = ffmpeg.probe(file_path)
                duration = float(probe['format']['duration'])

                # Extract from the middle of the file for better detection
                # (beginning might have intro music, credits, etc.)
                start_time = max(0, (duration / 2) - (sample_duration / 2))

                logger.debug(
                    f"Extracting {sample_duration}s audio sample from middle of {file_path} "
                    f"(duration: {duration:.1f}s, sample start: {start_time:.1f}s)"
                )
            except Exception as e:
                logger.warning(f"Could not get file duration: {e}, using start of file")
                start_time = 0

            audio_data = extract_audio_segment(
                file_path,
                start_time=int(start_time),
                duration=sample_duration
            )

            if not audio_data:
                logger.warning(f"Failed to extract audio from {file_path}")
                return None, None

            # Save audio_data to temporary file since stable-whisper doesn't accept BytesIO
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                temp_audio.write(audio_data.read())
                temp_audio_path = temp_audio.name

            try:
                # Initialize transcriber (will use small/fast model for detection)
                transcriber = WhisperTranscriber(model_name="tiny")  # Tiny model for fast detection
                transcriber.load_model()

                # Detect language using Whisper
                logger.debug("Detecting language with Whisper...")

                # Use transcribe with language=None to trigger auto-detection
                # This is more reliable than detect_language()
                result = transcriber.model.transcribe(
                    temp_audio_path,  # Use file path instead of BytesIO
                    language=None,  # Auto-detect
                    task="transcribe",
                    vad_filter=False,  # Don't filter, just detect
                    beam_size=1,  # Faster
                    best_of=1,  # Faster
                    temperature=0.0,  # Deterministic
                    condition_on_previous_text=False,
                    initial_prompt=None,
                )

                if result:
                    # stable-whisper/faster-whisper returns language info
                    # Try different attributes that might contain the language code
                    lang_code_str = None
                    probability = 1.0

                    # Try to get language code (2-letter ISO 639-1)
                    if hasattr(result, 'language_code'):
                        lang_code_str = result.language_code
                    elif hasattr(result, 'language'):
                        # result.language might be full name like "japanese" or code like "ja"
                        lang = result.language
                        if len(lang) == 2:
                            # Already a code
                            lang_code_str = lang
                        else:
                            # Full name - need to map to code
                            # Common mappings
                            lang_map = {
                                'japanese': 'ja',
                                'english': 'en',
                                'spanish': 'es',
                                'french': 'fr',
                                'german': 'de',
                                'italian': 'it',
                                'portuguese': 'pt',
                                'russian': 'ru',
                                'chinese': 'zh',
                                'korean': 'ko',
                                'arabic': 'ar',
                                'hindi': 'hi',
                            }
                            lang_code_str = lang_map.get(lang.lower())

                    # Get language probability if available
                    if hasattr(result, 'language_probability'):
                        probability = result.language_probability

                    if lang_code_str:
                        confidence = int(probability * 100)
                        language = LanguageCode.from_iso_639_1(lang_code_str)

                        logger.info(
                            f"Whisper detected language: {lang_code_str} "
                            f"(confidence: {confidence}%)"
                        )

                        return language, confidence
                    else:
                        logger.warning(f"Could not extract language code from result: {result}")

                return None, None

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_audio_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary audio file: {e}")

        except Exception as e:
            logger.error(f"Whisper language detection error: {e}", exc_info=True)
            return None, None

    @staticmethod
    def clear_cache(file_path: Optional[str] = None):
        """
        Clear language detection cache.

        Args:
            file_path: Specific file to clear, or None to clear all
        """
        from backend.core.database import database

        with database.get_session() as session:
            if file_path:
                session.query(DetectedLanguage).filter(
                    DetectedLanguage.file_path == file_path
                ).delete()
                logger.info(f"Cleared language cache for {file_path}")
            else:
                count = session.query(DetectedLanguage).delete()
                logger.info(f"Cleared all language cache ({count} entries)")

            session.commit()


# Global instance
language_detector = LanguageDetector()

