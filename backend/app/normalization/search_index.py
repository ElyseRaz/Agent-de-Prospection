from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement


def search_tsv_expression(title: str | None, description_clean: str | None) -> ColumnElement:
    """Expression SQL `to_tsvector` utilisee pour tenir `jobs.search_tsv` a
    jour. Config 'simple' + `unaccent` (deja active) plutot que des configs
    francais/anglais distinctes : fonctionne pour les deux langues sans avoir
    a maintenir deux colonnes, au prix du stemming (limitation assumee)."""

    combined = f"{title or ''} {description_clean or ''}".strip()
    return func.to_tsvector("simple", func.unaccent(combined))
