"""Audio processing utilities extracted from transcriptarr.py."""
import logging
import os
from io import BytesIO
from typing import List, Dict, Optional

import ffmpeg

# Optional import - graceful degradation if not available
try:
    import av
    AV_AVAILABLE = True
except ImportError:
    av = None
    AV_AVAILABLE = False
    logging.warning("av (PyAV) not available. Some audio features may not work.")

from backend.core.language_code import LanguageCode

logger = logging.getLogger(__name__)


def extract_audio_segment(
    input_file: str,
    start_time: int,
    duration: int,
) -> BytesIO:
    """
    Extract a segment of audio from a file to memory.

    Args:
        input_file: Path to input media file
        start_time: Start time in seconds
        duration: Duration in seconds

    Returns:
        BytesIO object containing audio segment
    """
    try:
        logger.debug(f"Extracting audio: {input_file}, start={start_time}s, duration={duration}s")

        out, _ = (
            ffmpeg.input(input_file, ss=start_time, t=duration)
            .output("pipe:1", format="wav", acodec="pcm_s16le", ar=16000)
            .run(capture_stdout=True, capture_stderr=True)
        )

        if not out:
            raise ValueError("FFmpeg output is empty")

        return BytesIO(out)

    except ffmpeg.Error as e:
        logger.error(f"FFmpeg error: {e.stderr.decode()}")
        raise
    except Exception as e:
        logger.error(f"Error extracting audio: {e}")
        raise


def get_audio_tracks(video_file: str) -> List[Dict]:
    """
    Get information about audio tracks in a media file.

    Args:
        video_file: Path to media file

    Returns:
        List of dicts with audio track information
    """
    try:
        probe = ffmpeg.probe(video_file, select_streams="a")
        audio_streams = probe.get("streams", [])

        audio_tracks = []
        for stream in audio_streams:
            # Get all possible language tags - check multiple locations
            tags = stream.get("tags", {})

            # Try different common tag names (MKV uses different conventions)
            lang_tag = (
                tags.get("language") or           # Standard location
                tags.get("LANGUAGE") or           # Uppercase variant
                tags.get("lang") or               # Short form
                stream.get("language") or         # Sometimes at stream level
                "und"                             # Default: undefined
            )

            # Log ALL tags for debugging
            logger.debug(
                f"Audio track {stream.get('index')}: "
                f"codec={stream.get('codec_name')}, "
                f"lang_tag='{lang_tag}', "
                f"all_tags={tags}"
            )

            language = LanguageCode.from_iso_639_2(lang_tag)

            # Log when language is undefined
            if lang_tag == "und" or language is None:
                logger.warning(
                    f"Audio track {stream.get('index')} in {video_file}: "
                    f"Language undefined (tag='{lang_tag}'). "
                    f"Available tags: {list(tags.keys())}"
                )

            audio_track = {
                "index": int(stream.get("index", 0)),
                "codec": stream.get("codec_name", "unknown"),
                "channels": int(stream.get("channels", 0)),
                "language": language,
                "title": tags.get("title", ""),
                "default": stream.get("disposition", {}).get("default", 0) == 1,
                "forced": stream.get("disposition", {}).get("forced", 0) == 1,
                "original": stream.get("disposition", {}).get("original", 0) == 1,
                "commentary": "commentary" in tags.get("title", "").lower(),
            }
            audio_tracks.append(audio_track)

        return audio_tracks

    except ffmpeg.Error as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        return []
    except Exception as e:
        logger.error(f"Error reading audio tracks: {e}")
        return []


def extract_audio_track_to_memory(
    input_video_path: str, track_index: int
) -> Optional[BytesIO]:
    """
    Extract a specific audio track to memory.

    Args:
        input_video_path: Path to video file
        track_index: Audio track index

    Returns:
        BytesIO with audio data or None
    """
    if track_index is None:
        logger.warning(f"Skipping audio track extraction for {input_video_path}")
        return None

    try:
        out, _ = (
            ffmpeg.input(input_video_path)
            .output(
                "pipe:",
                map=f"0:{track_index}",
                format="wav",
                ac=1,
                ar=16000,
                loglevel="quiet",
            )
            .run(capture_stdout=True, capture_stderr=True)
        )
        return BytesIO(out)

    except ffmpeg.Error as e:
        logger.error(f"FFmpeg error extracting track: {e.stderr.decode()}")
        return None


def get_audio_languages(video_path: str) -> List[LanguageCode]:
    """
    Extract language codes from audio streams.

    Args:
        video_path: Path to video file

    Returns:
        List of LanguageCode objects
    """
    audio_tracks = get_audio_tracks(video_path)
    return [track["language"] for track in audio_tracks]


def get_subtitle_languages(video_path: str) -> List[LanguageCode]:
    """
    Extract language codes from subtitle streams.

    Args:
        video_path: Path to video file

    Returns:
        List of LanguageCode objects
    """
    languages = []

    try:
        with av.open(video_path) as container:
            for stream in container.streams.subtitles:
                lang_code = stream.metadata.get("language")
                if lang_code:
                    languages.append(LanguageCode.from_iso_639_2(lang_code))
                else:
                    languages.append(LanguageCode.NONE)
    except Exception as e:
        logger.error(f"Error reading subtitle languages: {e}")

    return languages


def has_audio(file_path: str) -> bool:
    """
    Check if a file has valid audio streams.

    Args:
        file_path: Path to media file

    Returns:
        True if file has audio, False otherwise
    """
    if not AV_AVAILABLE or av is None:
        logger.warning(f"av (PyAV) not available, cannot check audio for {file_path}")
        # Assume file has audio if we can't check
        return True

    try:
        if not os.path.isfile(file_path):
            return False

        with av.open(file_path) as container:
            for stream in container.streams:
                if stream.type == "audio":
                    if stream.codec_context and stream.codec_context.name != "none":
                        return True
        return False

    except Exception as e:
        # Catch all exceptions since av.FFmpegError might not exist if av is None
        logger.debug(f"Error checking audio in {file_path}: {e}")
        return False


def has_subtitle_language_in_file(
    video_file: str, target_language: LanguageCode
) -> bool:
    """
    Check if video has embedded subtitles in target language.

    Args:
        video_file: Path to video file
        target_language: Language to check for

    Returns:
        True if subtitles exist in target language
    """
    if not AV_AVAILABLE or av is None:
        logger.warning(f"av (PyAV) not available, cannot check subtitles for {video_file}")
        return False

    try:
        with av.open(video_file) as container:
            subtitle_streams = [
                stream
                for stream in container.streams
                if stream.type == "subtitle" and "language" in stream.metadata
            ]

            for stream in subtitle_streams:
                stream_language = LanguageCode.from_string(
                    stream.metadata.get("language", "").lower()
                )
                if stream_language == target_language:
                    logger.debug(f"Found subtitles in '{target_language}' in video")
                    return True

        return False

    except Exception as e:
        logger.error(f"Error checking subtitles: {e}")
        return False


def has_subtitle_of_language_in_folder(
    video_file: str, target_language: LanguageCode
) -> bool:
    """
    Check if external subtitle file exists for video.

    Args:
        video_file: Path to video file
        target_language: Language to check for

    Returns:
        True if external subtitle exists
    """
    subtitle_extensions = {".srt", ".vtt", ".sub", ".ass", ".ssa"}

    video_folder = os.path.dirname(video_file)
    video_name = os.path.splitext(os.path.basename(video_file))[0]

    try:
        for file_name in os.listdir(video_folder):
            if not any(file_name.endswith(ext) for ext in subtitle_extensions):
                continue

            subtitle_name, _ = os.path.splitext(file_name)

            if not subtitle_name.startswith(video_name):
                continue

            # Extract language from filename
            parts = subtitle_name[len(video_name) :].lstrip(".").split(".")

            for part in parts:
                if LanguageCode.from_string(part) == target_language:
                    logger.debug(f"Found external subtitle: {file_name}")
                    return True

        return False

    except Exception as e:
        logger.error(f"Error checking external subtitles: {e}")
        return False


def handle_multiple_audio_tracks(
    file_path: str, language: Optional[LanguageCode] = None
) -> Optional[BytesIO]:
    """
    Handle files with multiple audio tracks.

    Args:
        file_path: Path to media file
        language: Preferred language

    Returns:
        BytesIO with extracted audio or None
    """
    audio_tracks = get_audio_tracks(file_path)

    if len(audio_tracks) <= 1:
        return None

    logger.debug(f"Handling {len(audio_tracks)} audio tracks")

    # Find track by language
    audio_track = None
    if language:
        for track in audio_tracks:
            if track["language"] == language:
                audio_track = track
                break

    # Fallback to first track
    if not audio_track:
        audio_track = audio_tracks[0]

    return extract_audio_track_to_memory(file_path, audio_track["index"])
