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

Les sous-sections ci-dessous détaillent ces 4 couches (1 à 3, puis 6 pour l'exposition,
qui inclut désormais le pipeline de candidatures) ; 4 sujets transverses y sont
documentés à part faute de mieux s'insérer dans le schéma d'origine : le choix du
fournisseur LLM (section 4, détail technique traversant les couches Normalisation et
Enrichissement), les profils/matching (section 5, une extension du modèle à 4 couches
plutôt qu'une 5e couche à proprement parler), le frontend (section 7, consommateur de
la couche Exposition) et les alertes/admin/observabilité/durcissement (section 8, ajoutés
en phase 8 par-dessus les couches existantes plutôt qu'une 5e couche).

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
automatiquement) + flux SSE (`GET /notifications/stream`, phase 8) pour le temps réel,
consommés par le frontend React.

**Pipeline de candidatures** (`app/models/application.py`, `app/services/applications.py`,
`app/api/routes/applications.py`) : une ligne `Application` par couple `(profile_id,
job_id)` (contrainte unique `uq_applications_profile_job`, création idempotente via
`ON CONFLICT DO NOTHING`), avec 7 étapes (`spotted -> to_apply -> applied -> in_discussion
-> proposal -> won/lost`). Chaque changement d'étape ou de note génère un
`ApplicationEvent` horodaté (`payload` JSONB), formant un historique consultable sans
table de log séparée. `applied_at`/`last_contact_at` sont dérivés automatiquement du
changement d'étape plutôt que saisis manuellement, pour éviter l'incohérence entre le
statut affiché et ces dates. Propriété stricte par profil (403 si le profil demandé
n'appartient pas à l'utilisateur courant, vérifié à chaque route via
`_get_owned_profile`/`_get_owned_application`).

### 7. Frontend

React 18 + TypeScript (strict) + Vite. **MUI (Material-UI)** pour l'ensemble des
composants visuels — remplace Tailwind/shadcn-ui prévu dans le cahier des charges
d'origine, à la demande explicite en cours de phase 7. TanStack Table reste utilisé en
sous-couche pour la logique de tableau (colonnes, tri) et la virtualisation
(`@tanstack/react-virtual`), rendu via des composants MUI plutôt que du HTML brut.

- **Etat serveur** : TanStack Query exclusivement (`src/hooks/`) — aucun composant
  n'appelle `fetch`/`apiFetch` directement, ce qui centralise le cache, l'invalidation et
  les états loading/error.
- **Etat client** : Zustand (`src/store/authStore.ts`, avec `persist`) pour les tokens
  d'authentification et le profil actif sélectionné — seul état qui doit survivre à un
  rechargement de page sans dépendre du serveur.
- **Client API** (`src/api/client.ts`) : wrapper `apiFetch<T>()` unique, injection du
  Bearer token, **un seul retry automatique sur 401** via le refresh token (garde
  `refreshPromise` contre les rafraîchissements concurrents), erreurs typées (`ApiError`).
- **Rendu conditionnel** systématique : chaque écran gère explicitement les états
  chargement / vide / erreur (`components/common/{Loading,Empty,Error}State.tsx`) plutôt
  que de supposer les données toujours présentes.
- **Kanban** : transition d'étape par menu contextuel (pas de glisser-déposer, hors scope
  phase 7) — `components/kanban/`.
- **Décimaux** : Pydantic v2 sérialise les champs `Decimal` (TJM, `expected_value`, etc.)
  en `string` JSON, jamais en `number` — reflété dans `src/api/types.ts`
  (`string | null`), pour ne pas perdre de précision ni introduire d'arrondi flottant côté
  client.

### 8. Alertes, admin, observabilité, durcissement

**Recherches sauvegardées** (`app/models/alert.py`, `app/services/alerts.py`) : une
`SavedSearch` stocke les mêmes filtres que `GET /jobs/search` (JSONB, reconstruits en
`JobSearchFilters` à chaque évaluation via `_filters_from_json` — même dataclass que la
recherche interactive, aucune logique de filtrage dupliquée) plus une liste de canaux et
une fréquence (`instant`/`daily`). `evaluate_saved_search` réutilise `hybrid_search_jobs`
(phase 4) trié par fraîcheur, ne retient que les offres détectées depuis le dernier
passage, et n'envoie jamais deux fois la même offre pour la même recherche (contrainte
unique `uq_alert_notifications_search_job`, vérifiée avant l'envoi). Une panne d'un canal
(`NotificationError`) n'empêche ni les autres canaux ni les autres offres d'être traités —
capturée et journalisée, jamais propagée. `evaluate_due_saved_searches` (tâche Celery Beat
`alerts.evaluate_due_saved_searches`, toutes les 15 min) n'évalue que les recherches dues :
`instant` l'est à chaque passage, `daily` seulement après 24h depuis `last_run_at`.

**Canaux de notification** (`app/notifications/`) : interface `NotificationChannel`
commune (email SMTP via `smtplib` déporté dans un thread, Slack/Discord en webhook HTTP,
Telegram via l'API bot `sendMessage`), chacun construit seulement si ses variables
d'environnement sont présentes (`build_notification_channels`, même principe que
Trustpilot phase 5 : fonctionnalité optionnelle, jamais d'erreur au démarrage). Un canal,
un bot ou un webhook sont configurés **une fois pour toute l'instance**, pas par
utilisateur — cohérent avec les variables d'environnement déjà réservées en phase 1
(`SLACK_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, etc., toutes à valeur unique).

**Flux temps réel** (`GET /notifications/stream`) : plutôt que d'introduire un bus
d'événements (Redis Pub/Sub) pour un unique flux, l'endpoint interroge périodiquement
`alert_notifications` (qui sert déjà d'idempotence) et ne renvoie que les lignes pas
encore vues par cette connexion. La génératrice (`_stream_notifications`) est testée
directement, sans passer par `StreamingResponse` ni un serveur réel, via un paramètre
`max_polls` qui la rend déterministe en test. L'API `EventSource` du navigateur ne
permettant pas d'en-têtes personnalisés, le token peut être passé en paramètre de requête
(`?access_token=...`, `get_current_user_sse`) — exception documentée à la règle « JWT
toujours en en-tête Bearer » appliquée partout ailleurs.

**Admin** (`app/services/admin.py`, `app/api/routes/admin.py`) : agrégation de `llm_calls`
par jour/purpose/modèle (consommation déjà journalisée depuis la phase 3, aucune nouvelle
collecte de données), gestion des utilisateurs (rôle, activation), compteurs globaux.
Garde-fou : un administrateur ne peut ni se retirer ses propres droits admin ni se
désactiver lui-même via cette API (éviterait un lockout total du système).

**Rate limiting** (`app/core/rate_limit.py`) : `RateLimiter` à fenêtre fixe, construit sur
le même `CounterStore` Protocol que le circuit breaker des collecteurs (phase 2) —
`incr`/`expire` sur une clé Redis, aucune dépendance nouvelle. Appliqué par IP cliente sur
`/auth/login` et `/auth/register` via une factory de dépendance FastAPI
(`rate_limit(prefix, max_requests, window_seconds)`), `429` au-delà. Comme pour le
circuit breaker, le store est injectable (`get_rate_limit_store`), ce qui permet aux
tests d'utiliser un `InMemoryCounterStore` sans Redis réel.

**Observabilité** : middleware d'ID de requête (`RequestIDMiddleware`) qui génère ou
reprend `X-Request-ID`, le lie aux logs `structlog` le temps de la requête (contextvars)
et le renvoie en en-tête — permet de corréler un rapport utilisateur aux logs serveur.
Sentry (`sentry-sdk`) initialisé seulement si `SENTRY_DSN` est présent.

**Durcissement** : `SecurityHeadersMiddleware` ajoute `X-Content-Type-Options`,
`X-Frame-Options` et `Referrer-Policy` à chaque réponse. Pas de CSP complète : cette API
ne sert aucun contenu HTML consommé par un navigateur en dehors du frontend React
(origine distincte, déjà couverte par CORS).

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
