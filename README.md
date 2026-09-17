# RemoteRadar

Agent IA qui agrège, normalise, enrichit et score des offres de mission freelance en
remote, avec suivi de candidatures.

## Etat du projet

**Phase 1 — Socle** : API FastAPI, authentification JWT (access/refresh + 2FA TOTP
optionnelle), base PostgreSQL 16 (pgvector/pg_trgm/unaccent), Celery/Redis (worker +
beat déclarés, sans tâche métier), frontend Vite/React squelette, reverse-proxy Nginx,
CI GitHub Actions.

**Phase 2 — Collecte** : interface `SourceConnector` (registre chargé dynamiquement
depuis `app/collectors/`, aucune modification du noyau pour ajouter une source),
connecteur Remotive (API JSON publique), client HTTP avec backoff exponentiel +
respect de `Retry-After` + circuit breaker par domaine (Redis), vérificateur
`robots.txt`, service de collecte idempotent (`raw_documents`, clé naturelle
`source_id + external_id`), endpoints `GET /sources`, `GET /sources/{slug}`,
`POST /sources/{slug}/collect` (dry-run ou réel, admin uniquement), tâche Celery
`collection.collect_source`.

**Phase 3 — Normalisation LLM** : pipeline `raw_document -> Job canonique` (nettoyage
HTML via `selectolax`, détection de langue via `langdetect`, extraction structurée par
LLM — Claude Sonnet 5 par défaut, configurable via `LLM_MODEL` — avec sortie validée par
schéma Pydantic et retry automatique), cache des extractions par `content_hash +
prompt_version` (`llm_extraction_cache`), journal d'audit coût/tokens (`llm_calls`),
normalisation des devises vers l'EUR (API Frankfurter, taux du jour, repli statique),
résolution entreprise minimale, normalisation des compétences vers un référentiel
« maison » (`skills`/`job_skills`), score de qualité déterministe, endpoints admin
`POST /normalization/run` et `POST /raw-documents/{id}/reprocess`, tâche Celery
`normalization.normalize_pending`. Prompt versionné dans
`backend/app/prompts/extract_job_v1.md`.

**Phase 4 — Embeddings, déduplication, recherche hybride** : embeddings locaux
(`sentence-transformers`, modèle `paraphrase-multilingual-mpnet-base-v2`, 768 dim,
aucune clé API, poids pré-téléchargés au build Docker), recherche plein texte
(`search_tsv`, config `simple` + `unaccent`, GIN) et recherche hybride (fusion
texte + cosinus pgvector/HNSW, `GET /jobs/search` avec filtres TJM/stack/séniorité/etc.
et tri), déduplication multi-niveaux (hash exact → trigramme pg_trgm → cosinus,
fusion via `canonical_id` + `job_duplicate_links`), détection d'expiration basique
(`last_seen_at`), endpoints `POST /jobs/backfill-embeddings` (ré-embedde sans
réappeler le LLM) et `POST /jobs/mark-expired`.

**Phase 5 — Réputation, score de risque, liste noire** : réputation Trustpilot (API
Business Units **publique**, résolution par domaine uniquement — voir limitation
ci-dessous), score de risque 0-100 avec raisons lisibles combinant signaux déterministes
(TJM vs médiane du marché par séniorité, réputation, doublons multi-entreprises via la
phase 4) et jugement LLM sur le texte (codes `NO_BUDGET`, `UNDERPAID`, `UPFRONT_PAYMENT`,
`UNPAID_TEST`, `PERSONAL_CONTACT_ONLY`, `VAGUE_SCOPE`, `COMPANY_NOT_FOUND`,
`BAD_REPUTATION`, `DUPLICATE_SPAM`), liste noire d'entreprises/recruteurs (entrées
partagées ou personnelles), endpoints `POST /jobs/assess-risk` (admin) et
`GET/POST /blacklist`. Prompt versionné `detect_scam_v1.md`.

**Limitation assumée (Trustpilot)** : l'API publique ne propose pas de recherche par nom
d'entreprise en texte libre, seulement par domaine exact (`GET /business-units/find?name=
<domaine>`). Le domaine n'est connu que si le LLM le détecte explicitement dans le texte
de l'annonce (rare) — la couverture réelle de la vérification de réputation sera donc
faible en pratique. Le score de risque reste utile sans elle (TJM, doublons, signaux
textuels).

**Phase 6 — Profils, matching, explication du score** : profils freelance multi-profils
par utilisateur (`profiles`/`profile_skills`, TJM cible/plancher, fuseau, langues,
compétences avec niveau), moteur de score de compatibilité 0-100 sur 5 critères pondérés
(similarité sémantique, couverture des compétences requises, TJM vs cible/plancher,
fuseau horaire, fiabilité via `risk_score`), explication lisible par critère
(`{criterion, points, label}`), mise en cache dans `matches`, apprentissage implicite des
poids à partir des offres sauvegardées/rejetées (`match_feedback`, dès 3 signaux de
chaque côté). Endpoints CRUD `/profiles`, `PUT /profiles/{id}/skills`,
`GET /profiles/{id}/matches`, `POST /profiles/{id}/matches/{job_id}/feedback`.

**Fournisseur LLM configurable** (ajouté en cours de phase 6, à la demande) : extraction
(phase 3) et score de risque (phase 5) peuvent basculer d'Anthropic vers une passerelle
tierce compatible OpenAI (`LLM_PROVIDER=openai_compatible`, appelée en HTTP direct — voir
§ IA & coûts). Anthropic reste le défaut, rien ne change sans action explicite.

**Phase 7 — Frontend complet & pipeline de candidatures (Kanban)** : côté backend, suivi
de candidatures type CRM (`applications`/`application_events`, étapes `spotted -> to_apply
-> applied -> in_discussion -> proposal -> won/lost`, historique d'événements horodaté),
endpoints CRUD `/profiles/{id}/applications` avec propriété stricte (403 si le profil
n'appartient pas à l'utilisateur), création idempotente (contrainte unique
`profile_id + job_id`). Côté frontend, application React complète : authentification
(login/register, refresh automatique sur 401), sélecteur de profil actif persistant
(Zustand), recherche d'offres (filtres TJM/séniorité/remote/contrat, tri, vue tableau
virtualisée `@tanstack/react-virtual` pour 10k+ lignes et vue cartes), fiche offre
détaillée (risque, ajout au pipeline, feedback de matching), pipeline Kanban (transition
d'étape par menu, pas de glisser-déposer), tableau de bord (statistiques + graphiques
Recharts), gestion de profils et compétences. **Design UI/UX en MUI (Material-UI)**, à la
demande explicite — remplace Tailwind/shadcn-ui prévu initialement dans le cahier des
charges.

**Phase 8 — Alertes, admin, observabilité, CI, durcissement** : recherches sauvegardées
(`saved_searches`, mêmes filtres que `GET /jobs/search`, fréquence `instant`/`daily`) avec
notifications multi-canal (email SMTP, Slack, Telegram, Discord — chaque canal optionnel
indépendamment, voir `app/notifications/`), idempotence par offre déjà notifiée
(`alert_notifications`), évaluation périodique via Celery Beat (`alerts.evaluate_due_saved_searches`,
toutes les 15 min) et endpoint `POST /saved-searches/{id}/run` pour un déclenchement manuel ;
flux temps réel `GET /notifications/stream` (SSE, basé sur un polling de la table
d'idempotence plutôt qu'un bus dédié). Écran admin (API) : `GET /admin/llm-usage`
(consommation LLM agrégée par jour/purpose/modèle), `GET/PATCH /admin/users`
(rôle, activation), `GET /admin/stats`. Observabilité : intégration Sentry optionnelle
(`SENTRY_DSN`), middleware d'ID de requête corrélé aux logs structurés. Durcissement :
en-têtes de sécurité de base, rate limiting Redis sur `/auth/login` et `/auth/register`
(réutilise le `CounterStore` du circuit breaker phase 2). CI GitHub Actions déjà en place
depuis la phase 1, complétée : seuil de couverture 70 % sur normalisation/scoring, lint
frontend en plus du build.

Toutes les phases du cahier des charges initial sont maintenant implémentées — voir la
section Roadmap pour le détail phase par phase.

## Démarrage en une commande

Prérequis : Docker + Docker Compose.

```bash
make up
```

Cette commande :
1. crée `.env` à partir de `.env.example` s'il n'existe pas encore ;
2. build et démarre tous les services (`db`, `redis`, `api`, `worker`, `beat`,
   `frontend`, `nginx`).

Puis, avant la première utilisation, applique les migrations :

```bash
make migrate
```

### Vérifier que tout fonctionne

- API : http://localhost:8000/health → `{"status": "ok", "db": "ok"}`
- Documentation OpenAPI : http://localhost:8000/docs
- Frontend : http://localhost:5173 (affiche le statut de connexion à l'API)
- Via le reverse-proxy Nginx : http://localhost/ (frontend), http://localhost/docs
  (API docs), http://localhost/health

### Commandes utiles (Makefile)

| Commande | Effet |
|---|---|
| `make up` | build + démarre tous les services |
| `make down` | arrête les services |
| `make migrate` | applique les migrations Alembic |
| `make makemigration m="message"` | génère une migration autogenerate |
| `make test` | lance la suite pytest avec couverture dans le conteneur `api` |
| `make lint` | lance ruff dans le conteneur `api` |
| `make logs` | suit les logs de tous les services |
| `make shell-api` | shell dans le conteneur API |
| `make shell-db` | psql dans le conteneur Postgres |
| `make clean` | arrête les services et supprime les volumes (⚠️ supprime les données) |

## Configuration

Toutes les variables sont documentées dans [.env.example](.env.example). Aucun secret
n'est en dur dans le code : tout passe par variables d'environnement (voir
`backend/app/core/config.py`).

## Tests

```bash
make up
make migrate
make test
```

Les tests d'authentification (`backend/tests/test_auth.py`) couvrent : inscription,
doublon d'email, login (succès/échec), `/auth/me`, refresh token, activation et
vérification 2FA TOTP, et RBAC (route admin refusée à un utilisateur simple, autorisée
à un admin).

Les tests de collecte couvrent :
- `test_collectors_remotive.py` — parsing des offres, filtre `since`, filtres de config ;
- `test_collectors_http.py` — retry/backoff, respect de `Retry-After`, ouverture et
  réinitialisation du circuit breaker ;
- `test_collectors_robots.py` — respect de `robots.txt`, repli permissif si inaccessible ;
- `test_collection_service.py` — insertion, **idempotence sur rejeu** (aucun doublon),
  mise à jour d'un contenu modifié, dry-run sans écriture en base ;
- `test_sources_api.py` — RBAC sur `/sources/*`, dry-run vs collecte réelle via l'API.

Toutes les réponses HTTP externes sont mockées via `httpx.MockTransport` à partir d'une
fixture figée (`backend/tests/fixtures/remotive_response.json`) : aucun test n'effectue
d'appel réseau réel.

Les tests de normalisation couvrent :
- `test_normalization_html_clean.py`, `test_normalization_language.py` — nettoyage HTML,
  détection de langue ;
- `test_llm_extraction.py` — **cache par content_hash** (un 2e appel ne recontacte jamais
  le LLM), retry automatique sur sortie invalide, échec après épuisement des tentatives ;
- `test_normalization_company.py`, `test_normalization_skills.py` — résolution
  entreprise, normalisation et déduplication des compétences ;
- `test_currency.py` — conversion EUR via Frankfurter (mocké), repli statique si
  injoignable ;
- `test_normalization_service.py` — pipeline complet `raw_document -> Job`, idempotence,
  `force=True` pour rejouer, échec marquant le document `FAILED` ;
- `test_normalization_api.py` — RBAC sur `/normalization/run` et `/raw-documents/{id}/reprocess`.

L'extraction LLM est testée via un backend injectable (`JobExtractionBackend` Protocol) :
aucun test n'appelle l'API Anthropic réelle, aucune clé API n'est nécessaire pour lancer
la suite.

Les tests d'embeddings/déduplication/recherche couvrent :
- `test_embeddings_text_builder.py` — construction du texte source de l'embedding ;
- `test_deduplication.py` — les **3 niveaux** (hash exact, trigramme avec contrainte
  même entreprise, cosinus au-dessus du seuil), non-détection de jobs réellement
  différents, upsert idempotent de `job_duplicate_links` ;
- `test_expiry.py` — passage `EXPIRED` des jobs non reconfirmés, jobs déjà expirés
  ignorés ;
- `test_search_service.py` — recherche sans requête (filtres + tri), plein texte,
  vectoriel seul, exclusion des doublons/jobs non actifs, filtre TJM ;
- `test_jobs_api.py` — authentification requise sur `/jobs/search`, RBAC sur
  `/jobs/backfill-embeddings` et `/jobs/mark-expired`, URLs des doublons sur
  `GET /jobs/{id}`.

Comme pour le LLM, l'embedding est testé via un backend injectable
(`EmbeddingBackend` Protocol, `FakeEmbeddingBackend` dans `conftest.py`) : aucun test
ne charge le modèle `sentence-transformers` réel.

Les tests de réputation/risque/liste noire couvrent :
- `test_reputation.py` — parsing des champs Trustpilot confirmés (`score.trustScore`,
  `numberOfReviews.total`), repli sur l'endpoint détail si absents de `/find`, 404 →
  `None`, erreur serveur → `ReputationLookupError` (jamais confondue avec "non trouvé"),
  **cache 30 jours** (pas de second appel avant expiration), ancienne valeur conservée
  en cas de panne transitoire ;
- `test_risk_service.py` — signaux déterministes (médiane de TJM par séniorité, comptage
  d'entreprises distinctes dans un cluster de doublons, détection blacklist), **court-
  circuit sur liste noire** (aucun appel LLM), appel LLM + cache sur le chemin normal,
  traitement par lot ne réévaluant pas deux fois le même job ;
- `test_blacklist.py` — normalisation des valeurs (cohérente avec la résolution
  d'entreprise), entrées personnelles invisibles des autres utilisateurs, RBAC sur les
  entrées partagées (admin uniquement).

Le backend Trustpilot et le backend LLM de risque sont tous deux injectables : aucun
test n'appelle Trustpilot ni Anthropic réellement.

Les tests de matching couvrent :
- `test_matching_service.py` — chaque axe de score isolément (sémantique via vecteurs de
  test à similarité cosinus contrôlée, couverture de compétences, TJM au-dessus/dans la
  fourchette/**sous le plancher négatif**, fuseau avec/sans contrainte, fiabilité selon
  le risque), scoring bout-en-bout avec persistance dans `matches`, **apprentissage des
  poids** déclenché seulement au-dessus du seuil d'échantillon (3+3) et pas avant,
  poids toujours renormalisés à 100 ;
- `test_profiles_api.py` — CRUD avec propriété (un utilisateur ne voit/modifie jamais le
  profil d'un autre), recalcul de l'embedding à la mise à jour des compétences, endpoint
  matches, feedback.

Les tests du fournisseur LLM alternatif couvrent :
- `test_openai_compatible.py` — parsing réel via `httpx.MockTransport` (contrat REST
  "chat completions" standard), erreurs HTTP/JSON invalide/schéma incompatible, coût à
  0$ quand aucun tarif n'est connu pour le modèle.

Les tests du pipeline de candidatures couvrent :
- `test_applications_api.py` — création + liste, **idempotence** (rejouer la création ne
  duplique jamais), changement d'étape journalisé (`ApplicationEvent`) et positionnement
  automatique de `applied_at`, mise à jour des notes, invisibilité d'une candidature pour
  un autre utilisateur (403), suppression, authentification requise (401).

Les tests d'alertes/admin/durcissement (phase 8) couvrent :
- `test_alerts_service.py` — notification d'une offre nouvelle, **idempotence** (jamais
  renotifiée), panne d'un canal sans bloquer les autres (`NotificationError` capturée),
  canal demandé mais non configuré simplement ignoré, planification `instant` (toujours
  due) vs `daily` (due seulement après 24h), recherches inactives ignorées ;
- `test_saved_searches_api.py` — CRUD avec propriété, rejet d'un canal inconnu (422),
  déclenchement manuel (`POST /saved-searches/{id}/run`) ;
- `test_notification_channels.py` — Slack/Discord/Telegram via `httpx.MockTransport`
  (aucun appel réseau réel), email via un double de `smtplib.SMTP` (aucun socket ouvert) ;
- `test_notifications_stream.py` — le flux SSE (fonction génératrice testée directement,
  sans passer par `StreamingResponse`) ne fuite jamais les notifications d'un autre
  utilisateur, ne répète jamais un événement déjà vu entre deux passages ;
- `test_admin_api.py` — RBAC admin sur les 3 endpoints, agrégation de `llm_calls`,
  **un admin ne peut pas se retirer ses propres droits ni se désactiver** ;
- `test_rate_limit.py` — `/auth/login` et `/auth/register` renvoient 429 au-delà du seuil
  configuré, avec un `CounterStore` partagé injecté pour un test déterministe.

### Frontend

```bash
cd frontend
npm install
npm run lint     # ESLint (flat config, TypeScript + react-hooks)
npm run build    # tsc -b && vite build
```

Le client API (`src/api/client.ts`) centralise l'injection du token, le retry automatique
sur 401 (un seul essai de refresh, garde anti-concurrence), et le typage des erreurs. Les
hooks TanStack Query (`src/hooks/`) encapsulent tous les appels réseau ; aucun composant
n'appelle `fetch` directement. Le tableau d'offres (`JobTable`) est virtualisé
(`@tanstack/react-virtual`) pour rester fluide avec un grand volume de résultats.

## Architecture (cible, voir Roadmap pour l'état d'implémentation)

Architecture hexagonale en 4 couches :

1. **Collecte** — connecteurs de sources (`SourceConnector.fetch() -> Iterable[RawDocument]`),
   chargés dynamiquement depuis un registre en base.
2. **Normalisation** — nettoyage HTML, détection de langue, extraction structurée par
   LLM validée par schéma Pydantic.
3. **Enrichissement & scoring** — déduplication, réputation entreprise, détection
   d'arnaque, score de compatibilité au profil utilisateur.
4. **Exposition** — API REST (OpenAPI) + SSE, consommée par le frontend React.

## Arborescence

```
/backend    API FastAPI, modèles SQLAlchemy, migrations Alembic, worker Celery, tests
/frontend   React 18 + TypeScript + Vite
/infra      Nginx, scripts d'initialisation Postgres
/docs       Documentation complémentaire (ajoutée au fil des phases)
```

## Roadmap

| Phase | Contenu | Statut |
|---|---|---|
| 1 | Socle : Docker Compose, FastAPI, Alembic, modèles, auth JWT | ✅ |
| 2 | `SourceConnector` + connecteur Remotive + `raw_documents` | ✅ |
| 3 | Pipeline de normalisation LLM + validation Pydantic + cache | ✅ |
| 4 | Embeddings, déduplication, recherche hybride | ✅ |
| 5 | Enrichissement entreprise + Trustpilot + score de risque | ✅ |
| 6 | Profils, moteur de matching, explication du score | ✅ |
| 7 | Frontend React complet (dashboard, liste, fiche, kanban, analytics) | ✅ |
| 8 | Alertes, notifications, admin, observabilité, CI, durcissement | ✅ |

## IA & coûts

- Modèle par défaut : `claude-sonnet-5` (configurable via `LLM_MODEL`), choisi pour
  l'extraction structurée à fort volume (tâche fermée, pas de raisonnement complexe).
- Sortie contrainte par schéma Pydantic (Structured Outputs de l'API Claude), avec
  retry automatique (3 tentatives) en cas de sortie invalide.
- Cache par `content_hash + prompt_version + purpose` (`llm_extraction_cache`) : une
  même extraction n'est jamais payée deux fois, y compris en cas de repost identique
  sur une autre offre.
- Chaque appel (hit de cache inclus) est journalisé dans `llm_calls` avec le nombre de
  tokens et le coût réel en dollars.
- Prompts versionnés dans `backend/app/prompts/` — chaque `Job` conserve la version qui
  l'a produit, pour permettre de rejouer l'extraction sans re-crawler.
- Embeddings : modèle local `sentence-transformers` (`paraphrase-multilingual-mpnet-base-v2`,
  768 dimensions), pré-téléchargé au build de l'image Docker (`backend/Dockerfile`) —
  aucune clé API, aucun coût récurrent, aucun appel réseau à l'exécution. Contrepartie
  assumée : image `api`/`worker` plus lourde (~1-2 Go de plus) et build plus long.
- Score de risque (phase 5) : **2e appel LLM payant**, distinct de l'extraction (phase 3).
  Jamais déclenché automatiquement par la normalisation — action explicite
  (`POST /jobs/assess-risk` ou tâche Celery `risk.assess_pending`) pour garder le
  contrôle du coût. Même mécanisme de cache/retry/journalisation que l'extraction
  (`purpose="detect_scam"` dans `llm_calls`/`llm_extraction_cache`).
- **Fournisseur LLM alternatif** (`LLM_PROVIDER=openai_compatible`) : passerelle tierce
  compatible OpenAI (ex: `opencode.ai`), appelée en HTTP direct (`POST {base}/chat/completions`,
  mode JSON) plutôt que via un SDK tiers — même raisonnement que pour Frankfurter/Trustpilot :
  s'appuyer sur le contrat REST documenté plutôt que sur les internals non vérifiés d'un
  SDK. **Aucun tarif public connu** pour un modèle exposé par une passerelle tierce
  personnalisée (ex. un alias propre à cette passerelle) : le coût journalisé sera **0$**
  tant que `PRICING_USD_PER_MTOK` (`backend/app/normalization/llm_common.py`) n'est pas
  complété manuellement avec le tarif réel. Le score de compatibilité structurée
  (schéma respecté) n'a pas la même garantie native que Structured Outputs côté
  Anthropic — repose sur le mode JSON générique + validation Pydantic + retry déjà en
  place. Défaut inchangé (`anthropic`) : bascule uniquement sur action explicite.

## Sécurité et conformité

- Mots de passe hachés avec Argon2 (`argon2-cffi`).
- JWT access (courte durée) + refresh (longue durée), 2FA TOTP optionnelle.
- RBAC par dépendance FastAPI (`require_role`).
- Aucun identifiant en dur : tout passe par variables d'environnement.
- Chaque connecteur respecte `robots.txt` (quand applicable) et les en-têtes
  `Retry-After`, et porte un champ `compliance_note` documentant sa légalité
  (visible via `GET /api/v1/sources`).
- Circuit breaker par domaine (Redis) après échecs consécutifs, backoff exponentiel.
- Idempotence garantie par clé naturelle `source_id + external_id` sur `raw_documents` :
  rejouer une collecte ne crée jamais de doublon.
- **Rate limiting** (phase 8) sur `/auth/login` (10 req / 5 min) et `/auth/register`
  (5 req / heure), par IP cliente, `429` au-delà — réutilise le `CounterStore` du circuit
  breaker (`app/core/rate_limit.py`), aucune dépendance nouvelle.
- **En-têtes de sécurité** (phase 8) : `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy` sur toutes les réponses (`app/core/middleware.py`).
- **Observabilité** (phase 8) : ID de requête généré/repris (`X-Request-ID`) et lié aux
  logs structurés le temps de la requête ; Sentry optionnel (`SENTRY_DSN`, non initialisé
  si absent).
- Un administrateur ne peut ni se retirer ses propres droits admin ni se désactiver via
  `PATCH /admin/users/{id}` (garde-fou anti-lockout).
