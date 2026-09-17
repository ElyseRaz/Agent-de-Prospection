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

Les sous-sections ci-dessous détaillent ces 4 couches (1 à 3, puis 6 pour l'exposition) ;
2 sujets transverses y sont documentés à part faute de mieux s'insérer dans le schéma
d'origine : le choix du fournisseur LLM (section 4, détail technique traversant les
couches Normalisation et Enrichissement) et les profils/matching (section 5, une
extension du modèle à 4 couches plutôt qu'une 5e couche à proprement parler).

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

**Embeddings et indexation** (fin de `normalize_raw_document`, avant le commit) :
génération d'un embedding local (`sentence-transformers`, `app/embeddings/`, aucune clé
API — voir README § IA & coûts) et mise a jour de `search_tsv` (`to_tsvector('simple',
unaccent(...))`, `app/normalization/search_index.py`), puis appel immediat de la
deduplication (voir section 3). Embeddings et recherche sont ainsi toujours a jour a
l'issue d'une normalisation, sans etape batch separee. `POST /api/v1/jobs/backfill-embeddings`
complete a posteriori les jobs normalises avant l'existence de cette logique, sans
reappeler le LLM (aucun cout d'extraction).

### 3. Enrichissement & scoring

**Déduplication multi-niveaux** (`app/services/deduplication.py`, implémentée) : hash
exact (`dedup_hash`, titre+entreprise+début de description normalisés) → similarité
trigramme `pg_trgm` sur le titre (contrainte : même `company_id`, pour éviter les faux
positifs entre entreprises différentes) → similarité cosinus sur l'embedding (pgvector,
index HNSW). Le premier job détecté reste canonique ; les suivants pointent vers lui via
`canonical_id`, tracé dans `job_duplicate_links`. Aucune table d'URLs séparée : chaque
job dupliqué garde sa propre `url`, récupérable via `WHERE canonical_id = X OR id = X`.
Une repost à plusieurs semaines d'écart est détectée par ce même mécanisme, sans logique
dédiée. Détection d'expiration minimale par ancienneté de `last_seen_at`
(`app/services/expiry.py`) — un contrôle HTTP réel (404) reste à faire.

**Réputation entreprise** (`app/reputation/`, `app/services/reputation.py`) : API
Business Units **publique** de Trustpilot (authentification `apikey`, endpoints
confirmés via la doc officielle — `GET /business-units/find?name=<domaine>` puis
`GET /business-units/{id}` pour `score.trustScore`/`numberOfReviews.total`). Limitation
structurelle : cette API ne recherche que par domaine exact, jamais par nom en texte
libre — la réputation n'est donc vérifiée que si le LLM a détecté un `company_domain`
explicite dans l'annonce (champ ajouté au schéma d'extraction phase 3), ce qui reste
rare en pratique. Cache 30 jours par entreprise (`company_reputation`, `UNIQUE(company_id,
provider)`) ; une ligne avec `rating=NULL` signifie "vérifié, absent de Trustpilot"
(signal `COMPANY_NOT_FOUND` légitime), à ne jamais confondre avec "jamais vérifié"
(aucune ligne). Une panne Trustpilot (`ReputationLookupError`) ne produit jamais de faux
signal : l'ancienne valeur en cache est conservée.

**Score de risque** (`app/services/risk.py`, `app/normalization/risk_extraction.py`,
prompt `detect_scam_v1.md`) : signaux déterministes calculés en Python (budget déclaré,
TJM vs médiane du marché pour la même séniorité via `percentile_cont`, réputation
Trustpilot si connue, nombre d'entreprises distinctes dans un cluster de doublons phase 4,
présence en liste noire partagée) transmis en contexte à un second appel LLM (même
mécanisme cache/retry/coût que l'extraction phase 3, `purpose="detect_scam"`) qui
synthétise `{risk_score, reasons}` et détecte en plus les signaux non structurés
(test non payé, contact personnel uniquement, périmètre flou, paiement demandé en amont).
Une entrée de liste noire **partagée** court-circuite entièrement l'appel LLM
(`risk_score=100`, code `BLACKLISTED` — jamais généré par le LLM). Déclenché
explicitement (`POST /api/v1/jobs/assess-risk`, tâche Celery `risk.assess_pending`),
jamais automatiquement à la normalisation, pour garder le contrôle du coût (2e appel LLM
payant par offre).

**Liste noire** (`app/models/blacklist.py`, `app/services/blacklist.py`) : entrées
partagées (`user_id=NULL`, visibles de tous, seules à influencer le `risk_score` public)
ou personnelles (visibles de leur auteur uniquement). Valeurs normalisées de la même
façon que la résolution d'entreprise, pour garantir la correspondance lors de la
vérification.

### 4. Fournisseur LLM configurable

`app/normalization/llm_common.py` et `app/normalization/openai_compatible.py` :
`extract_job_structured` (phase 3) et `assess_risk_structured` (phase 5) restent
inchangés — seul le *backend* injecté change.
`build_job_extraction_backend`/`build_risk_assessment_backend` lisent
`settings.llm_provider` (`anthropic` par défaut, jamais changé automatiquement) et
construisent soit le backend Claude existant, soit `OpenAICompatible*Backend`, qui parle
en HTTP direct (pas de SDK tiers) au contrat REST "chat completions" (`response_format:
json_object`) que toute passerelle "OpenAI-compatible" s'engage à respecter — même choix
que pour Frankfurter/Trustpilot : s'appuyer sur un contrat REST documenté plutôt que sur
les internals non vérifiés d'un SDK tiers. `PRICING_USD_PER_MTOK` n'a de tarif que pour
les modèles Claude ; un modèle inconnu (ex. exposé par une passerelle tierce) journalise
un coût de 0$ jusqu'à complétion manuelle de cette table.

### 5. Profils & matching

**Profils freelance** (`app/models/profile.py`) : multi-profils par utilisateur
(`user_id` FK sans contrainte d'unicité), compétences avec niveau/années/`is_required`
(`profile_skills`, référentiel `skills` partagé avec les offres), embedding calculé sur
nom + compétences (même modèle que les offres, même espace vectoriel).

**Score de compatibilité** (`app/services/matching.py`) : 5 critères pondérés
(`profiles.weights`, défaut `{semantic:25, skills:30, rate:25, timezone:10,
reliability:10}`), chacun retournant une contribution en points et un libellé lisible :
- *Sémantique* et *compétences* : contribution 0→poids (pas de pénalité, une similarité
  ou une couverture faible ne fait que rapporter peu de points).
- *TJM* : seul critère franchement bipolaire — plein poids au-dessus de la cible,
  interpolation entre plancher et cible, **négatif sous le plancher** (reproduit
  l'exemple `−25 : TJM 250€ sous votre plancher de 400€` de la spec).
- *Fuseau horaire* : heuristique texte (nom de la région du fuseau du profil recherché
  dans `timezone_constraint`) — **pas un parseur de plages UTC**, limitation assumée.
- *Fiabilité* : signée autour de `risk_score=50` (neutre), négative au-delà.

Candidats récupérés par ANN pgvector (embedding du profil) ou par fraîcheur si le profil
n'a pas encore d'embedding, scorés en Python, mis en cache dans `matches` (upsert).

**Apprentissage implicite** (`match_feedback`) : à partir de 3 offres sauvegardées et 3
rejetées pour un profil, compare la contribution moyenne de chaque critère entre les deux
groupes (déjà stockée dans `matches.breakdown`) et ajuste les poids en conséquence (taux
d'apprentissage faible, poids bornés `[5, 50]`, renormalisés à 100). Heuristique simple
et testable, pas un modèle entraîné — cohérent avec l'absence d'infrastructure ML dans le
projet. Sous le seuil de 3+3, aucun ajustement (évite de sur-réagir à un seul clic).

`excluded_industries`/`desired_contract_types` sont stockés sur le profil mais **non
exploités dans le score** : ni `jobs` ni `companies` n'ont de champ secteur (décision
prise en phase 5, aucune source de données assignée) — champs réservés pour une extension
future, pas des signaux fabriqués.

### 6. Exposition

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
