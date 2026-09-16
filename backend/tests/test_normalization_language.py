from app.normalization.language import detect_language


def test_detects_french():
    text = (
        "Nous recherchons un developpeur freelance experimente en Python et FastAPI "
        "pour une mission de six mois, en full remote, avec un demarrage rapide."
    )
    assert detect_language(text) == "fr"


def test_detects_english():
    text = (
        "We are looking for an experienced freelance backend engineer with strong "
        "Python and FastAPI skills for a six month fully remote contract."
    )
    assert detect_language(text) == "en"


def test_empty_text_returns_autre():
    assert detect_language("") == "autre"
    assert detect_language("   ") == "autre"


def test_short_ambiguous_text_does_not_raise():
    # Ne doit jamais lever d'exception, quel que soit le texte.
    result = detect_language("x")
    assert result in {"fr", "en", "autre"}
