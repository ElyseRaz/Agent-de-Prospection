# Architecture — RemoteRadar

## Vue d'ensemble

RemoteRadar suit une architecture hexagonale en 4 couches, pensée pour qu'ajouter une
source de données ou un canal de notification ne demande jamais de modifier le noyau.

```
┌─────────────┐   ┌────────────────┐   ┌───────────────────────┐   ┌──────────────┐
│  Collecte   │ → │ Normalisation  │ → │ Enrichissement/scoring │ → │  Exposition  │
│ (connecteurs)│   │ (LLM + regles) │   │ (dedup, reputation)   │   │ (REST + SSE) │
└─────────────┘   └────────────────┘   └───────────────────────┘   └──────────────┘
```

### 1. Collecte

Chaque source implémente l'interface `SourceConnector` (`backend/app/collectors/base.py`) :

```python
class SourceConnector(abc.ABC):
    metadata: ClassVar[ConnectorMetadata]  # access_type, quotas, cron par defaut, compliance_note

    def __init__(self, *, base_url, config, http_client, circuit_breaker) -> None: ...

    @abc.abstractmethod
    def fetch(self, *, since: datetime | None = None) -> AsyncIterator[RawDocumentPayload]: ...
```

Les connecteurs sont enregistrés en base (table `sources`) avec leur type d'accès
(`api` / `rss` / `html_public`), leurs quotas, leur fréquence (cron Celery Beat) et une
`compliance_note` obligatoire, affichée via `GET /api/v1/sources`. Le noyau (le registre
`app/collectors/registry.py` et le service `app/services/collection.py`) ne référence
jamais un connecteur par son nom en dur : `discover_connectors()` importe dynamiquement
tous les modules de `app/collectors/`, ce qui déclenche leurs décorateurs
`@register_connector("<kind>")`. **Ajouter une source = ajouter un fichier connecteur +
une ligne en base (`sources.kind` = la clé du décorateur), sans toucher au reste du
système.**

Le noyau assure trois garanties transverses, indépendamment du connecteur :
- **Retry/backoff** (`app/collectors/http.py`) : backoff exponentiel, respect du header
  `Retry-After`, et un **circuit breaker par domaine** (compteur Redis partagé entre
  workers, ouverture après N échecs consécutifs, fermeture après un délai de
  refroidissement).
- **robots.txt** (`app/collectors/robots.py`) : vérifié à l'exécution pour les
  connecteurs `html_public`/`rss` (repli permissif si inaccessible, toujours tracé) ;
  non applicable aux API dédiées comme Remotive (endpoint documenté pour un usage
  programmatique, pas une page web crawlée).
- **Idempotence** (`app/services/collection.py`) : chaque document brut est upserté sur
  la clé naturelle `(source_id, external_id)` ; le `content_hash` (sha256 du payload
  canonique) permet de détecter un contenu inchangé (aucune écriture) vs modifié
  (mise à jour, `processing_status` remis à `pending` pour re-normalisation en phase 3).
  Rejouer une collecte ne crée donc jamais de doublon.

Le mode `dry_run=True` (via l'API ou la tâche Celery) exécute le connecteur et retourne
un échantillon des documents récupérés **sans aucune écriture en base**, ni `scrape_run`
ni `raw_document` — utile pour tester un connecteur avant de l'activer.

### 2. Normalisation

Pipeline déterministe (`app/services/normalization.py`) : extraction de texte brut par
`kind` de source (registre dynamique, même principe que les connecteurs :
`app/normalization/raw_text/`) → nettoyage HTML (`selectolax`) → détection de langue
(`langdetect`) → extraction structurée par LLM avec sortie validée par un schéma
Pydantic strict (`app/normalization/schema.py`, Structured Outputs de l'API Claude via
`client.messages.parse(output_format=...)`), retry automatique (3 tentatives) en cas de
sortie invalide.

**Cache et coût LLM** (`app/normalization/llm_extraction.py`) : chaque extraction est
mise en cache par `content_hash + prompt_version + purpose` (`llm_extraction_cache`) —
un repost identique ou un rejeu de collecte ne paie jamais deux fois la même extraction.
Chaque tentative (hit de cache ou appel reel) est journalisée dans `llm_calls` avec le
nombre de tokens et le coût réel calculé depuis une table de tarification par modèle.
Le backend d'appel LLM est injecté via un `Protocol` (`JobExtractionBackend`), ce qui
permet de tester tout le pipeline (cache, retry, upsert idempotent) sans réseau ni clé
API — seule l'implémentation `AnthropicJobExtractionBackend` parle réellement au SDK.

Chaque offre conserve la version du prompt qui l'a produite (`prompts/extract_job_vN.md`),
pour permettre de rejouer l'extraction sans re-crawler (le `raw_document` brut est
conservé) — via `POST /api/v1/raw-documents/{id}/reprocess`.

**Normalisations additionnelles** : devises vers EUR (API Frankfurter, taux du jour,
cache 24h, repli statique si injoignable — `app/services/currency.py`) ; résolution
entreprise minimale par nom normalisé (`app/normalization/company.py` — la résolution
avancée par domaine/dédup fuzzy est explicitement phase 5) ; compétences vers un
référentiel « maison » par slug + table d'alias (`app/normalization/skills.py` — une
intégration ESCO complète est hors scope) ; score de qualité déterministe 0-100 basé sur
la complétude des champs extraits (`app/normalization/quality.py`).

### 3. Enrichissement & scoring

Déduplication multi-niveaux (hash exact → trigramme → cosinus sur embeddings),
résolution d'entreprise, récupération de réputation (Trustpilot), détection
heuristique + LLM des signaux d'arnaque, et calcul du score de compatibilité au profil
utilisateur.

### 4. Exposition

API REST documentée en OpenAPI (FastAPI génère `/docs` et `/openapi.json`
automatiquement) + flux SSE pour le temps réel, consommés par le frontend React.

## Choix techniques notables (Phase 1)

- **IDs** : UUID v4 générés côté application pour toutes les entités, pour éviter
  l'exposition de séquences et faciliter la fusion de données multi-sources.
- **Migrations** : Alembic exclusivement. `Base.metadata.create_all` n'est utilisé que
  dans les fixtures de test (base éphémère), jamais en développement ou production.
- **Auth** : JWT stateless (access courte durée + refresh rotatif), hachage Argon2,
  2FA TOTP optionnelle activable par l'utilisateur (`/auth/2fa/setup` puis
  `/auth/2fa/verify`).
- **Config** : `pydantic-settings`, aucune valeur sensible en dur — tout provient de
  variables d'environnement (voir `.env.example`).
