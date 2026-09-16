from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0  # resultats reproductibles

SUPPORTED_LANGUAGES = {"fr", "en"}


def detect_language(text: str) -> str:
    """Retourne 'fr', 'en', ou 'autre'. Jamais d'exception : un texte trop
    court ou ambigu retombe sur 'autre'."""

    if not text or not text.strip():
        return "autre"

    try:
        code = detect(text)
    except LangDetectException:
        return "autre"

    return code if code in SUPPORTED_LANGUAGES else "autre"
