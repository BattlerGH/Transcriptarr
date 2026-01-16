"""File analyzer using ffprobe for media file inspection."""
import logging
import os
from typing import Optional, List, Dict
from dataclasses import dataclass

from backend.transcription.audio_utils import (
    get_audio_tracks,
    get_audio_languages,
    get_subtitle_languages,
    has_audio,
    has_subtitle_of_language_in_folder,
)
from backend.core.language_code import LanguageCode

logger = logging.getLogger(__name__)


@dataclass
class AudioTrackInfo:
    """Information about an audio track."""

    index: int
    language: LanguageCode
    codec: str
    channels: int
    is_default: bool
    title: Optional[str] = None


@dataclass
class SubtitleTrackInfo:
    """Information about a subtitle track."""

    language: LanguageCode
    is_embedded: bool
    is_external: bool
    file_path: Optional[str] = None


@dataclass
class FileAnalysis:
    """Complete analysis of a media file."""

    file_path: str
    file_name: str
    file_extension: str
    has_audio: bool
    audio_tracks: List[AudioTrackInfo]
    embedded_subtitles: List[LanguageCode]
    external_subtitles: List[SubtitleTrackInfo]

    @property
    def audio_languages(self) -> List[LanguageCode]:
        """Get list of audio languages."""
        return [track.language for track in self.audio_tracks]

    @property
    def all_subtitle_languages(self) -> List[LanguageCode]:
        """Get all subtitle languages (embedded + external)."""
        languages = self.embedded_subtitles.copy()
        for sub in self.external_subtitles:
            if sub.language not in languages:
                languages.append(sub.language)
        return languages

    @property
    def default_audio_language(self) -> Optional[LanguageCode]:
        """Get default audio track language."""
        for track in self.audio_tracks:
            if track.is_default:
                return track.language
        # Fallback to first track
        return self.audio_tracks[0].language if self.audio_tracks else None

    def has_subtitle_language(self, language: LanguageCode) -> bool:
        """Check if file has subtitles in given language (embedded or external)."""
        return language in self.all_subtitle_languages

    def has_embedded_subtitle_language(self, language: LanguageCode) -> bool:
        """Check if file has embedded subtitles in given language."""
        return language in self.embedded_subtitles

    def has_external_subtitle_language(self, language: LanguageCode) -> bool:
        """Check if file has external subtitles in given language."""
        return any(sub.language == language for sub in self.external_subtitles)


class FileAnalyzer:
    """Analyzer for media files using ffprobe."""

    # Supported video extensions
    VIDEO_EXTENSIONS = (
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".mpg",
        ".mpeg",
        ".3gp",
        ".ogv",
        ".vob",
        ".rm",
        ".rmvb",
        ".ts",
        ".m4v",
        ".f4v",
        ".svq3",
        ".asf",
        ".m2ts",
        ".divx",
        ".xvid",
    )

    # Subtitle file extensions
    SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".sub", ".ass", ".ssa", ".idx", ".sbv"}

    @staticmethod
    def is_video_file(file_path: str) -> bool:
        """
        Check if file is a video file by extension.

        Args:
            file_path: Path to file

        Returns:
            True if video file
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in FileAnalyzer.VIDEO_EXTENSIONS

    @staticmethod
    def analyze_file(file_path: str) -> Optional[FileAnalysis]:
        """
        Analyze a media file completely.

        Args:
            file_path: Path to media file

        Returns:
            FileAnalysis object or None if analysis fails
        """
        try:
            # Basic file info
            file_name = os.path.basename(file_path)
            _, file_extension = os.path.splitext(file_path)

            # Check if file is video
            if not FileAnalyzer.is_video_file(file_path):
                logger.debug(f"Skipping non-video file: {file_name}")
                return None

            # Check if file exists and has audio
            if not os.path.isfile(file_path):
                logger.warning(f"File not found: {file_path}")
                return None

            file_has_audio = has_audio(file_path)
            if not file_has_audio:
                logger.debug(f"File has no audio, skipping: {file_name}")
                return None

            # Get audio tracks
            audio_tracks_raw = get_audio_tracks(file_path)
            audio_tracks = [
                AudioTrackInfo(
                    index=track["index"],
                    language=track["language"],
                    codec=track["codec"],
                    channels=track["channels"],
                    is_default=track["default"],
                    title=track.get("title"),
                )
                for track in audio_tracks_raw
            ]

            # Get embedded subtitles
            embedded_subtitles = get_subtitle_languages(file_path)

            # Find external subtitles
            external_subtitles = FileAnalyzer._find_external_subtitles(file_path)

            return FileAnalysis(
                file_path=file_path,
                file_name=file_name,
                file_extension=file_extension.lower(),
                has_audio=file_has_audio,
                audio_tracks=audio_tracks,
                embedded_subtitles=embedded_subtitles,
                external_subtitles=external_subtitles,
            )

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return None

    @staticmethod
    def _find_external_subtitles(video_file: str) -> List[SubtitleTrackInfo]:
        """
        Find external subtitle files for a video.

        Args:
            video_file: Path to video file

        Returns:
            List of SubtitleTrackInfo for external subtitles
        """
        external_subs = []
        video_folder = os.path.dirname(video_file)
        video_name = os.path.splitext(os.path.basename(video_file))[0]

        try:
            for file_name in os.listdir(video_folder):
                # Check if it's a subtitle file
                if not any(file_name.endswith(ext) for ext in FileAnalyzer.SUBTITLE_EXTENSIONS):
                    continue

                subtitle_path = os.path.join(video_folder, file_name)
                subtitle_name, _ = os.path.splitext(file_name)

                # Check if subtitle belongs to this video
                if not subtitle_name.startswith(video_name):
                    continue

                # Extract language from filename
                # Format: video_name.lang.srt or video_name.subgen.medium.lang.srt
                parts = subtitle_name[len(video_name) :].lstrip(".").split(".")

                # Try to find language code in parts
                detected_language = None
                for part in parts:
                    lang = LanguageCode.from_string(part)
                    if lang != LanguageCode.NONE:
                        detected_language = lang
                        break

                if detected_language:
                    external_subs.append(
                        SubtitleTrackInfo(
                            language=detected_language,
                            is_embedded=False,
                            is_external=True,
                            file_path=subtitle_path,
                        )
                    )

        except Exception as e:
            logger.error(f"Error finding external subtitles for {video_file}: {e}")

        return external_subs
