import importlib
import pkgutil
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from app.collectors.base import SourceConnector

log = structlog.get_logger(__name__)

_REGISTRY: dict[str, type["SourceConnector"]] = {}
_DISCOVERED = False

_NON_CONNECTOR_MODULES = {"base", "registry", "http", "robots"}


def register_connector(kind: str):
    """Decorateur a poser sur chaque classe SourceConnector : associe la
    valeur de `sources.kind` en base a l'implementation Python correspondante.
    Ajouter un connecteur = ajouter un fichier dans app/collectors/ + une ligne
    en base ; aucune modification du noyau (registre, service de collecte,
    API) n'est necessaire."""

    def _wrap(cls: type["SourceConnector"]) -> type["SourceConnector"]:
        if kind in _REGISTRY and _REGISTRY[kind] is not cls:
            raise ValueError(f"Un connecteur est deja enregistre pour kind={kind!r}")
        _REGISTRY[kind] = cls
        return cls

    return _wrap


def discover_connectors() -> None:
    """Importe tous les modules de app.collectors pour declencher leurs
    decorateurs @register_connector. Idempotent et sans effet si deja fait."""
    global _DISCOVERED
    if _DISCOVERED:
        return

    import app.collectors as collectors_package

    for module_info in pkgutil.iter_modules(collectors_package.__path__):
        if module_info.name in _NON_CONNECTOR_MODULES:
            continue
        importlib.import_module(f"app.collectors.{module_info.name}")

    _DISCOVERED = True
    log.info("connectors_discovered", kinds=sorted(_REGISTRY.keys()))


def get_connector_class(kind: str) -> type["SourceConnector"]:
    discover_connectors()
    try:
        return _REGISTRY[kind]
    except KeyError as exc:
        raise LookupError(f"Aucun connecteur enregistre pour kind={kind!r}") from exc


def available_kinds() -> list[str]:
    discover_connectors()
    return sorted(_REGISTRY.keys())
