import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

class LanguageDetector:
    """Wrapper for fast, offline language detection using lingua-language-detector."""
    
    def __init__(self):
        self._detector = None
        
    @property
    def detector(self):
        if self._detector is None:
            from lingua import Language, LanguageDetectorBuilder
            self._detector = LanguageDetectorBuilder.from_all_languages().build()
        return self._detector
        
    def detect_language(self, text: str) -> Optional[str]:
        """
        Detects the language of the provided text.
        Returns the ISO 639-1 language code (e.g., 'en', 'es', 'fr') or None if undetected.
        """
        if not text or not text.strip():
            return None
            
        try:
            language = self.detector.detect_language_of(text)
            if language:
                return language.iso_code_639_1.name.lower()
            return None
        except Exception as e:
            logger.warning("Language detection failed", error=str(e)[:200])
            return None

# Singleton instance for easy import
language_detector = LanguageDetector()
