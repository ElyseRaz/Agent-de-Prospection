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


def build_profile_embedding_text(*, name: str, skill_labels: list[str]) -> str:
    """Meme principe que build_embedding_text, cote profil freelance : nom du
    profil + competences declarees, pour comparer semantiquement au meme
    espace vectoriel que les offres (meme modele d'embedding)."""

    parts: list[str] = [name]
    if skill_labels:
        parts.append("Competences : " + ", ".join(skill_labels))
    return "\n".join(parts)
