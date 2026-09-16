from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RawText:
    """Texte brut normalise a partir du `raw_payload` d'un connecteur, avant
    nettoyage HTML et extraction LLM. Un extracteur par `sources.kind`."""

    title: str | None
    company_name: str | None
    description_html: str | None
    context_lines: list[str] = field(default_factory=list)
