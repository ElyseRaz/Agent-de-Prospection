# Architecture — LeadPilot

## Vue d'ensemble

LeadPilot est un CRM de prospection B2B : l'utilisateur apporte ses
entreprises (ajout manuel ou import CSV), l'application enrichit chaque
fiche et automatise les campagnes email. Aucune collecte automatisée de
masse — c'est une contrainte de conception, pas une limitation technique
(voir README § Principe et limites assumées).

```
┌──────────────┐   ┌────────────────┐   ┌───────────────────┐
│  Prospects   │ → │ Enrichissement │ → │ Campagnes & suivi  │
│ (CRM manuel) │   │ (Trustpilot,   │   │ (email, Kanban)    │
│              │   │  analyse IA)   │   │                    │
└──────────────┘   └────────────────┘   └───────────────────┘
```

## 1. Backend (Go)

Pas de framework "batteries included" à la Django/Rails, pas d'ORM :

- **Echo** pour le routage HTTP et les middlewares.
- **pgx** comme driver PostgreSQL (pas de `database/sql` générique — pgx
  expose l'API native de Postgres, plus performante).
- **sqlc** génère le code Go typé directement depuis `backend/queries/*.sql`
  et le schéma de `backend/migrations/` : les requêtes SQL sont écrites à la
  main (pas d'ORM qui les génère), mais le mapping vers des structs Go est
  automatique et vérifié à la génération (`make sqlc`), pas à l'exécution.
  **Ne jamais éditer `internal/db/sqlc/*.go` à la main** — ces fichiers sont
  regénérés à chaque `make sqlc`.
- **golang-migrate** pour les migrations, appliquées via le service Docker
  Compose `migrate` (profil `tools`, ne démarre pas avec `docker compose up`
  seul — `make migrate` l'invoque explicitement, même principe que
  `alembic upgrade head` dans le projet précédent).
- **Asynq** (file Redis) pour les jobs asynchrones — remplace Celery.
  Utilisé à partir de la phase 3 (enrichissement) et 4 (envoi de
  campagnes) ; le worker démarre dès la phase 1 sans tâche enregistrée,
  pour valider le socle (connexion Redis, boucle de traitement).

### Authentification (`internal/auth/`)

JWT HS256, deux types de token distingués par un champ `type` dans les
claims (`access`/`refresh`) — un refresh token présenté à une route
attendant un access token est rejeté, et inversement (`ParseToken` vérifie
le type en plus de la signature et de l'expiration). Mots de passe hachés
avec bcrypt (coût par défaut).

Le pont entre `pgtype.UUID` (généré par sqlc) et `uuid.UUID` (google/uuid,
utilisé pour les claims JWT et les réponses JSON) se fait par conversion
directe de tableau de bytes (`internal/auth/uuid.go`) — les deux types
partagent le même layout mémoire `[16]byte`, pas besoin de sérialiser en
chaîne puis reparser.

### Structure

```
backend/
  cmd/api/         point d'entree HTTP
  cmd/worker/      point d'entree worker Asynq
  internal/
    auth/          password, JWT, handlers, middleware
    config/        lecture des variables d'environnement
    db/            pool pgx + code sqlc genere (internal/db/sqlc/)
    health/        /health
    httpserver/    assemblage Echo (middlewares globaux, routes)
  migrations/      *.up.sql / *.down.sql
  queries/         source de verite pour sqlc
  sqlc.yaml
```

## 2. Frontend (Next.js)

App Router, TypeScript strict. **shadcn/ui + Tailwind** plutôt que MUI — vu
comme plus idiomatique dans l'écosystème Next.js, et plus proche du style
SaaS moderne visé pour LeadPilot.

- **Validation** : Zod partout où l'utilisateur saisit des données
  (`lib/schemas.ts`), couplé à `react-hook-form` via
  `@hookform/resolvers/zod` — validation synchrone côté client avant tout
  appel réseau, mêmes règles que le backend (email valide, mot de passe
  8 caractères minimum) dupliquées consciemment (validation client = UX,
  validation serveur = source de vérité, jamais l'inverse).
- **Etat serveur** : pas de bibliothèque dédiée en phase 1 (seulement des
  appels ponctuels auth) — à réévaluer (TanStack Query probable) dès que
  les écrans prospects/campagnes arrivent en phase 2+.
- **Etat client** : Zustand avec `persist` (`store/auth-store.ts`) pour les
  tokens et l'utilisateur courant. Le flag `hasHydrated` évite de rediriger
  vers `/login` pendant le court instant où le store persisté n'est pas
  encore relu depuis `localStorage` (SSR → hydration côté client).
- **Client API** (`lib/api.ts`) : wrapper `apiFetch<T>()` unique, injection
  du Bearer token, retry unique sur 401 via refresh token (garde
  `refreshPromise` contre les rafraîchissements concurrents) — même
  pattern que le projet précédent.
- **Proxy** : `next.config.ts` réécrit `/api/*` et `/health` vers le
  service `api` interne au réseau Docker (`API_ORIGIN`, défaut
  `http://api:8000`) — le navigateur ne parle jamais directement au
  backend Go, toujours via le serveur Next.js.

## 3. Infrastructure

Docker Compose : `db` (Postgres 16 simple — pas besoin de pgvector/pg_trgm
pour ce produit, contrairement au projet précédent qui faisait de la
recherche sémantique), `redis`, `api`/`worker` (image Go multi-stage,
binaire compilé statiquement dans une image `alpine` minimale, pas de
toolchain Go dans l'image finale), `frontend` (Next.js en mode dev, hot
reload via volumes montés), `nginx` (reverse-proxy unique en développement
comme en préfiguration de la prod), `migrate` (service à profil `tools`,
invoqué à la demande).

## Choix techniques notables

- **IDs** : UUID v4 générés côté Postgres (`gen_random_uuid()`, natif depuis
  PostgreSQL 13, aucune extension requise) plutôt que côté application.
- **Migrations** : golang-migrate exclusivement, montées et descentes
  explicites pour chaque révision.
- **Pas d'ORM** : requêtes SQL écrites à la main + génération de code typé
  (sqlc) plutôt qu'un ORM qui génère le SQL — choix délibéré pour garder le
  contrôle total sur les requêtes (perf, index utilisés) tout en gardant la
  sécurité de typage.
