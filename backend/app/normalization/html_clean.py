from selectolax.parser import HTMLParser


def clean_html(html: str | None) -> str:
    """Supprime les balises HTML et le boilerplate, conserve un texte lisible
    avec un saut de ligne par bloc."""

    if not html or not html.strip():
        return ""

    tree = HTMLParser(html)
    for tag in tree.css("script, style, noscript"):
        tag.decompose()

    text = tree.text(separator="\n", deep=True)
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)
