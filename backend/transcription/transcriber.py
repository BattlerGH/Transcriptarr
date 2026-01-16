"""Whisper transcription wrapper for worker processes."""
import logging
import os
import gc
import ctypes
import ctypes.util
from typing import Optional, Callable
from io import BytesIO

import numpy as np

# Optional imports - graceful degradation if not available
try:
    import stable_whisper
    import torch
    WHISPER_AVAILABLE = True
except ImportError:
    stable_whisper = None
    torch = None
    WHISPER_AVAILABLE = False
    logging.warning("stable_whisper or torch not available. Transcription will not work.")

logger = logging.getLogger(__name__)


class TranscriptionResult:
    """Result of a transcription operation."""

    def __init__(self, result, language: str, segments_count: int):
        """
        Initialize transcription result.

        Args:
            result: stable-ts result object
            language: Detected or forced language
            segments_count: Number of subtitle segments
        """
        self.result = result
        self.language = language
        self.segments_count = segments_count

    def to_srt(self, output_path: str, word_level: bool = False) -> str:
        """
        Save result as SRT file.

        Args:
            output_path: Path to save SRT file
            word_level: Enable word-level timestamps

        Returns:
            Path to saved file
        """
        self.result.to_srt_vtt(output_path, word_level=word_level)
        return output_path

    def get_srt_content(self, word_level: bool = False) -> str:
        """
        Get SRT content as string.

        Args:
            word_level: Enable word-level timestamps

        Returns:
            SRT content
        """
        return "".join(self.result.to_srt_vtt(filepath=None, word_level=word_level))


class WhisperTranscriber:
    """
    Whisper transcription engine wrapper.

    Manages Whisper model loading/unloading and transcription operations.
    Designed to run in worker processes with isolated model instances.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        model_path: Optional[str] = None,
        compute_type: Optional[str] = None,
        threads: Optional[int] = None,
    ):
        """
        Initialize transcriber.

        Args:
            model_name: Whisper model name (tiny, base, small, medium, large, etc.)
            device: Device to use (cpu, cuda, gpu)
            model_path: Path to store/load models
            compute_type: Compute type (auto, int8, float16, etc.)
            threads: Number of CPU threads
        """
        # Import settings_service here to avoid circular imports
        from backend.core.settings_service import settings_service

        # Load from database settings with sensible defaults
        self.model_name = model_name or settings_service.get('whisper_model', 'medium')
        self.device = (device or settings_service.get('transcribe_device', 'cpu')).lower()
        if self.device == "gpu":
            self.device = "cuda"
        self.model_path = model_path or settings_service.get('model_path', './models')

        # Get compute_type from settings based on device type
        if compute_type:
            requested_compute_type = compute_type
        elif self.device == "cpu":
            requested_compute_type = settings_service.get('cpu_compute_type', 'auto')
        else:
            requested_compute_type = settings_service.get('gpu_compute_type', 'auto')

        # Auto-detect compatible compute_type based on device
        self.compute_type = self._get_compatible_compute_type(self.device, requested_compute_type)

        self.threads = threads or int(settings_service.get('whisper_threads', 4))

        self.model = None
        self.is_loaded = False

        if self.compute_type != requested_compute_type:
            logger.warning(
                f"Requested compute_type '{requested_compute_type}' is not compatible with device '{self.device}'. "
                f"Using '{self.compute_type}' instead."
            )

        logger.info(
            f"WhisperTranscriber initialized: model={self.model_name}, "
            f"device={self.device}, compute_type={self.compute_type}"
        )

    def _get_compatible_compute_type(self, device: str, requested: str) -> str:
        """
        Get compatible compute type for the device.

        CPU: Only supports int8 and float32
        GPU: Supports float16, float32, int8, int8_float16

        Args:
            device: Device type (cpu, cuda)
            requested: Requested compute type

        Returns:
            Compatible compute type
        """
        if device == "cpu":
            # CPU only supports int8 and float32
            if requested == "auto":
                return "int8"  # int8 is faster on CPU
            elif requested in ("float16", "int8_float16"):
                logger.warning(f"CPU doesn't support {requested}, falling back to int8")
                return "int8"
            elif requested in ("int8", "float32"):
                return requested
            else:
                logger.warning(f"Unknown compute type {requested}, using int8")
                return "int8"
        else:
            # CUDA/GPU supports all types
            if requested == "auto":
                return "float16"  # float16 is recommended for GPU
            elif requested in ("float16", "float32", "int8", "int8_float16"):
                return requested
            else:
                logger.warning(f"Unknown compute type {requested}, using float16")
                return "float16"
    def load_model(self):
        """Load Whisper model into memory."""
        if not WHISPER_AVAILABLE:
            raise RuntimeError(
                "Whisper is not available. Install with: pip install stable-ts faster-whisper"
            )

        if self.is_loaded and self.model is not None:
            logger.debug("Model already loaded")
            return

        try:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = stable_whisper.load_faster_whisper(
                self.model_name,
                download_root=self.model_path,
                device=self.device,
                cpu_threads=self.threads,
                num_workers=1,  # Each worker has own model
                compute_type=self.compute_type if self.device == "gpu" or self.device == "cuda" else "float32",
            )
            self.is_loaded = True
            logger.info(f"Model {self.model_name} loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise

    def unload_model(self):
        """Unload model from memory and clear cache."""
        if not self.is_loaded or self.model is None:
            logger.debug("Model not loaded, nothing to unload")
            return

        try:
            logger.info("Unloading Whisper model")

            # Unload the model
            if hasattr(self.model, "model") and hasattr(self.model.model, "unload_model"):
                self.model.model.unload_model()

            del self.model
            self.model = None
            self.is_loaded = False

            # Clear CUDA cache if using GPU
            if self.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.debug("CUDA cache cleared")

            # Garbage collection
            if os.name != "nt":  # Don't run on Windows
                gc.collect()
                try:
                    ctypes.CDLL(ctypes.util.find_library("c")).malloc_trim(0)
                except Exception:
                    pass

            logger.info("Model unloaded successfully")

        except Exception as e:
            logger.error(f"Error unloading model: {e}")

    def transcribe_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        progress_callback: Optional[Callable] = None,
    ) -> TranscriptionResult:
        """
        Transcribe a media file.

        Args:
            file_path: Path to media file
            language: Language code (ISO 639-1) or None for auto-detect
            task: 'transcribe' or 'translate'
            progress_callback: Optional callback for progress updates

        Returns:
            TranscriptionResult object

        Raises:
            Exception: If transcription fails
        """
        # Ensure model is loaded
        if not self.is_loaded:
            self.load_model()

        try:
            logger.info(f"Transcribing file: {file_path} (language={language}, task={task})")

            # Prepare transcription arguments
            args = {}
            if progress_callback:
                args["progress_callback"] = progress_callback

            # Add custom regroup if configured
            from backend.core.settings_service import settings_service
            custom_regroup = settings_service.get('custom_regroup', 'cm_sl=84_sl=42++++++1')
            if custom_regroup:
                args["regroup"] = custom_regroup

            # Perform transcription
            result = self.model.transcribe(
                file_path,
                language=language,
                task=task,
                **args,
            )

            segments_count = len(result.segments) if hasattr(result, "segments") else 0
            detected_language = result.language if hasattr(result, "language") else language or "unknown"

            logger.info(
                f"Transcription completed: {segments_count} segments, "
                f"language={detected_language}"
            )

            return TranscriptionResult(
                result=result,
                language=detected_language,
                segments_count=segments_count,
            )

        except Exception as e:
            logger.error(f"Transcription failed for {file_path}: {e}")
            raise

    def transcribe_audio_data(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        task: str = "transcribe",
        sample_rate: int = 16000,
        progress_callback: Optional[Callable] = None,
    ) -> TranscriptionResult:
        """
        Transcribe raw audio data (for Bazarr provider mode).

        Args:
            audio_data: Raw audio bytes
            language: Language code or None
            task: 'transcribe' or 'translate'
            sample_rate: Audio sample rate
            progress_callback: Optional progress callback

        Returns:
            TranscriptionResult object
        """
        if not self.is_loaded:
            self.load_model()

        try:
            logger.info(f"Transcribing audio data (size={len(audio_data)} bytes)")

            args = {
                "audio": audio_data,
                "input_sr": sample_rate,
            }

            if progress_callback:
                args["progress_callback"] = progress_callback

            from backend.core.settings_service import settings_service
            custom_regroup = settings_service.get('custom_regroup', 'cm_sl=84_sl=42++++++1')
            if custom_regroup:
                args["regroup"] = custom_regroup

            result = self.model.transcribe(task=task, language=language, **args)

            segments_count = len(result.segments) if hasattr(result, "segments") else 0
            detected_language = result.language if hasattr(result, "language") else language or "unknown"

            logger.info(f"Audio transcription completed: {segments_count} segments")

            return TranscriptionResult(
                result=result,
                language=detected_language,
                segments_count=segments_count,
            )

        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            raise

    def detect_language(
        self,
        file_path: str,
        offset: int = 0,
        length: int = 30,
    ) -> str:
        """
        Detect language of a media file.

        Args:
            file_path: Path to media file
            offset: Start offset in seconds
            length: Duration to analyze in seconds

        Returns:
            Language code (ISO 639-1)
        """
        if not self.is_loaded:
            self.load_model()

        try:
            logger.info(f"Detecting language for: {file_path} (offset={offset}s, length={length}s)")

            # Extract audio segment for analysis
            from backend.transcription.audio_utils import extract_audio_segment

            audio_segment = extract_audio_segment(file_path, offset, length)

            result = self.model.transcribe(audio_segment.read())
            detected_language = result.language if hasattr(result, "language") else "unknown"

            logger.info(f"Detected language: {detected_language}")
            return detected_language

        except Exception as e:
            logger.error(f"Language detection failed for {file_path}: {e}")
            return "unknown"

    def __enter__(self):
        """Context manager entry."""
        self.load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        from backend.core.settings_service import settings_service
        if settings_service.get('clear_vram_on_complete', True) in (True, 'true', 'True', '1', 1):
            self.unload_model()

    def __del__(self):
        """Destructor - ensure model is unloaded."""
        try:
            if self.is_loaded:
                self.unload_model()
        except Exception:
            pass
