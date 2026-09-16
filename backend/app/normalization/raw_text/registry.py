import importlib
import pkgutil
from collections.abc import Callable

import structlog

from app.normalization.raw_text.base import RawText

log = structlog.get_logger(__name__)

RawTextExtractor = Callable[[dict], RawText]

_REGISTRY: dict[str, RawTextExtractor] = {}
_DISCOVERED = False
_NON_EXTRACTOR_MODULES = {"base", "registry"}


def register_raw_text_extractor(kind: str):
    """Decorateur a poser sur la fonction d'extraction de texte brut d'un
    connecteur. Meme principe que app.collectors.registry : ajouter un
    extracteur = ajouter un fichier, aucune modification du noyau."""

    def _wrap(fn: RawTextExtractor) -> RawTextExtractor:
        if kind in _REGISTRY and _REGISTRY[kind] is not fn:
            raise ValueError(f"Un extracteur est deja enregistre pour kind={kind!r}")
        _REGISTRY[kind] = fn
        return fn

    return _wrap


def discover_raw_text_extractors() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return

    import app.normalization.raw_text as package

    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name in _NON_EXTRACTOR_MODULES:
            continue
        importlib.import_module(f"app.normalization.raw_text.{module_info.name}")

    _DISCOVERED = True
    log.info("raw_text_extractors_discovered", kinds=sorted(_REGISTRY.keys()))


def get_raw_text_extractor(kind: str) -> RawTextExtractor:
    discover_raw_text_extractors()
    try:
        return _REGISTRY[kind]
    except KeyError as exc:
        raise LookupError(f"Aucun extracteur de texte brut pour kind={kind!r}") from exc
