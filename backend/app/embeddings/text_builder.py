def build_embedding_text(
    *, title: str | None, description_clean: str | None, tech_stack: list[str]
) -> str:
    """Construit le texte source de l'embedding d'une offre : titre +
    competences + debut de description (suffisant pour la similarite
    semantique, evite d'embarquer des descriptions tres longues)."""

    parts: list[str] = []
    if title:
        parts.append(title)
    if tech_stack:
        parts.append("Competences : " + ", ".join(tech_stack))
    if description_clean:
        parts.append(description_clean[:2000])
    return "\n".join(parts)
