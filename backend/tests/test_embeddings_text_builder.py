from app.embeddings.text_builder import build_embedding_text


def test_build_embedding_text_combines_title_stack_and_description():
    text = build_embedding_text(
        title="Ingenieur Backend Python",
        description_clean="Nous cherchons un developpeur experimente.",
        tech_stack=["Python", "FastAPI"],
    )

    assert "Ingenieur Backend Python" in text
    assert "Python, FastAPI" in text
    assert "developpeur experimente" in text


def test_build_embedding_text_truncates_long_description():
    long_description = "x" * 5000
    text = build_embedding_text(title="Titre", description_clean=long_description, tech_stack=[])

    assert len(text) < 5000 + len("Titre") + 10


def test_build_embedding_text_handles_missing_fields():
    text = build_embedding_text(title=None, description_clean=None, tech_stack=[])
    assert text == ""
