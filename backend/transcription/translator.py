"""SRT translation service using Google Translate or DeepL."""
import logging
from typing import Optional
import re

logger = logging.getLogger(__name__)

# Check for translation library availability
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    GoogleTranslator = None
    TRANSLATOR_AVAILABLE = False


class SRTTranslator:
    """
    Translate SRT subtitle files from English to target language.

    Uses deep-translator library with Google Translate as backend.
    Falls back gracefully if library not installed.
    """

    def __init__(self, target_language: str):
        """
        Initialize translator.

        Args:
            target_language: ISO 639-1 code (e.g., 'es', 'fr', 'ja')
        """
        if not TRANSLATOR_AVAILABLE:
            raise RuntimeError(
                "Translation library not available. Install with: pip install deep-translator"
            )

        # Google Translate accepts ISO 639-1 codes directly
        self.target_language = target_language
        logger.info(f"Initializing translator for language: {target_language}")

        self.translator = None

    def _get_translator(self):
        """Lazy load translator."""
        if self.translator is None:
            self.translator = GoogleTranslator(source='en', target=self.target_language)
        return self.translator

    def translate_srt_content(self, srt_content: str) -> str:
        """
        Translate SRT content from English to target language.

        Args:
            srt_content: SRT formatted string in English

        Returns:
            SRT formatted string in target language

        Raises:
            Exception: If translation fails
        """
        if not srt_content or not srt_content.strip():
            logger.warning("Empty SRT content, nothing to translate")
            return srt_content

        try:
            logger.info(f"Translating SRT content to {self.target_language}")

            # Parse SRT into blocks
            blocks = self._parse_srt(srt_content)

            if not blocks:
                logger.warning("No subtitle blocks found in SRT")
                return srt_content

            # Translate each text block
            translator = self._get_translator()
            translated_blocks = []

            for block in blocks:
                try:
                    # Only translate the text, keep index and timestamps
                    translated_text = translator.translate(block['text'])
                    translated_blocks.append({
                        'index': block['index'],
                        'timestamp': block['timestamp'],
                        'text': translated_text
                    })

                except Exception as e:
                    logger.error(f"Failed to translate block {block['index']}: {e}")
                    # Keep original text on error
                    translated_blocks.append(block)

            # Reconstruct SRT
            result = self._reconstruct_srt(translated_blocks)

            logger.info(f"Successfully translated {len(translated_blocks)} subtitle blocks")
            return result

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise

    def _parse_srt(self, srt_content: str) -> list:
        """
        Parse SRT content into structured blocks.

        Args:
            srt_content: Raw SRT string

        Returns:
            List of dicts with 'index', 'timestamp', 'text'
        """
        blocks = []

        # Split by double newline (subtitle blocks separator)
        raw_blocks = re.split(r'\n\s*\n', srt_content.strip())

        for raw_block in raw_blocks:
            lines = raw_block.strip().split('\n')

            if len(lines) < 3:
                continue  # Invalid block

            try:
                index = lines[0].strip()
                timestamp = lines[1].strip()
                text = '\n'.join(lines[2:])  # Join remaining lines as text

                blocks.append({
                    'index': index,
                    'timestamp': timestamp,
                    'text': text
                })

            except Exception as e:
                logger.warning(f"Failed to parse SRT block: {e}")
                continue

        return blocks

    def _reconstruct_srt(self, blocks: list) -> str:
        """
        Reconstruct SRT content from structured blocks.

        Args:
            blocks: List of dicts with 'index', 'timestamp', 'text'

        Returns:
            SRT formatted string
        """
        srt_lines = []

        for block in blocks:
            srt_lines.append(block['index'])
            srt_lines.append(block['timestamp'])
            srt_lines.append(block['text'])
            srt_lines.append('')  # Empty line separator

        return '\n'.join(srt_lines)


def translate_srt_file(
    input_path: str,
    output_path: str,
    target_language: str
) -> bool:
    """
    Translate an SRT file from English to target language.

    Args:
        input_path: Path to input SRT file (English)
        output_path: Path to output SRT file (target language)
        target_language: ISO 639-1 code

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read input SRT
        with open(input_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()

        # Translate
        translator = SRTTranslator(target_language=target_language)
        translated_content = translator.translate_srt_content(srt_content)

        # Write output SRT
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(translated_content)

        logger.info(f"Translated SRT saved to {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to translate SRT file: {e}")
        return False
