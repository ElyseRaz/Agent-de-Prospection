from app.normalization.html_clean import clean_html


def test_clean_html_strips_tags_and_collapses_whitespace():
    html = "<p>Hello <b>World</b></p>\n<ul><li>Python</li><li>FastAPI</li></ul>"
    result = clean_html(html)

    assert "Hello" in result
    assert "World" in result
    assert "Python" in result
    assert "<" not in result


def test_clean_html_removes_script_and_style():
    html = "<div>Contenu</div><script>alert('x')</script><style>.a{}</style>"
    result = clean_html(html)

    assert "Contenu" in result
    assert "alert" not in result


def test_clean_html_handles_empty_input():
    assert clean_html(None) == ""
    assert clean_html("") == ""
    assert clean_html("   ") == ""
