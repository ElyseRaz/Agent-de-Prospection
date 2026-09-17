# LeadPilot

CRM de prospection commerciale B2B enrichi par IA : tu ajoutes tes entreprises
(pas de scraping de masse), l'app enrichit chaque fiche (Trustpilot, analyse
IA du site) et automatise les campagnes email de proposition de services.

## Principe et limites assumées

- **Aucune collecte de masse.** Les entreprises sont ajoutées une à une ou
  par import CSV, par la personne qui utilise l'app — jamais aspirées
  automatiquement depuis un annuaire ou un site tiers.
- **Traçabilité obligatoire.** Chaque contact porte un `source_note` :
  d'où vient ce contact (page "Contact" publique, réseau, salon pro...),
  pour garder une base légale de prospection.
- **Trustpilot en enrichissement, jamais en source.** L'API publique
  Trustpilot ne permet qu'une recherche par domaine déjà connu — utilisée
  pour enrichir une fiche entreprise existante, pas pour construire une
  liste.
- **Emailing avec désinscription obligatoire** et limite d'envoi quotidien.

## Etat du projet

**Phase 1 — Socle** : API Go (Echo), authentification JWT (access/refresh),
base PostgreSQL (migrations via golang-migrate, requêtes typées générées par
sqlc), worker Asynq (Redis) démarré sans tâche métier, frontend Next.js
(App Router, TypeScript, Tailwind + shadcn/ui, validation Zod), reverse-proxy
Nginx, CI GitHub Actions.

Les phases suivantes (CRM prospects, enrichissement Trustpilot/Groq,
campagnes email, suivi Kanban) ne sont pas encore implémentées.

## Stack

| Composant | Choix |
|---|---|
| Backend | Go 1.23, Echo, pgx, sqlc (SQL typé généré, pas d'ORM) |
| Migrations | golang-migrate |
| Jobs asynchrones | Asynq (Redis) |
| Frontend | Next.js (App Router), TypeScript, Tailwind, shadcn/ui |
| Formulaires | react-hook-form + Zod |
| Etat client | Zustand (persist) |
| Base de données | PostgreSQL 16 |
| Infra | Docker Compose, Nginx, GitHub Actions CI |

## Démarrage en une commande

Prérequis : Docker + Docker Compose.

```bash
make up
```

Cette commande crée `.env` depuis `.env.example` si besoin, puis build et
démarre tous les services (`db`, `redis`, `api`, `worker`, `frontend`,
`nginx`).

Avant la première utilisation, applique les migrations :

```bash
make migrate
```

### Vérifier que tout fonctionne

- API : http://localhost:8000/health → `{"status":"ok","db":"ok"}`
- Frontend : http://localhost:3000
- Via le reverse-proxy Nginx : http://localhost/ (frontend), http://localhost/api,
  http://localhost/health

### Commandes utiles (Makefile)

| Commande | Effet |
|---|---|
| `make up` | build + démarre tous les services |
| `make down` | arrête les services |
| `make migrate` | applique les migrations golang-migrate |
| `make sqlc` | régénère le code Go typé depuis `backend/queries/*.sql` |
| `make test` | lance `go test ./...` dans un conteneur Go |
| `make lint` | lance golangci-lint |
| `make logs` | suit les logs de tous les services |
| `make shell-api` | shell dans le conteneur API |
| `make shell-db` | psql dans le conteneur Postgres |
| `make clean` | arrête les services et supprime les volumes (⚠️ supprime les données) |

## Configuration

Toutes les variables sont documentées dans [.env.example](.env.example).
Aucun secret en dur dans le code : tout passe par variables d'environnement
(`backend/internal/config/config.go`).

## Architecture backend

```
backend/
  cmd/
    api/        point d'entree du serveur HTTP (Echo)
    worker/     point d'entree du worker de jobs asynchrones (Asynq)
  internal/
    auth/       hash de mot de passe, JWT, handlers et middleware d'authentification
    config/     lecture de la configuration depuis les variables d'environnement
    db/         pool de connexions pgx + code genere par sqlc (internal/db/sqlc)
    health/     endpoint /health
    httpserver/ assemblage de l'application Echo (middlewares, routes)
  migrations/   migrations SQL (golang-migrate, montees/descentes explicites)
  queries/      requetes SQL source de verite pour sqlc (make sqlc regenere le code)
```

Aucun ORM : sqlc génère du code Go typé directement depuis les requêtes SQL
écrites à la main (`backend/queries/*.sql`) et le schéma des migrations —
les erreurs de type entre le SQL et le Go sont détectées à la génération,
pas à l'exécution.

## Architecture frontend

```
frontend/
  app/                 routes (App Router) : /, /login, /register, /prospects,
                       /campaigns, /settings
  components/
    auth/              garde d'authentification cote client
    layout/            structure de l'application (sidebar, topbar)
    ui/                composants shadcn/ui
  lib/
    api.ts             client fetch type, injection du token, retry sur 401
    auth-api.ts         wrappers types pour les endpoints d'authentification
    schemas.ts          schemas Zod (validation des formulaires)
  store/
    auth-store.ts        etat d'authentification (Zustand, persist)
```

Le frontend ne parle jamais directement à l'API Go depuis le navigateur :
`next.config.ts` proxie `/api/*` et `/health` vers le service `api` interne
au réseau Docker (`rewrites`), même principe que le proxy Vite du projet
précédent.

## Sécurité

- Mots de passe hachés avec bcrypt.
- JWT access (courte durée) + refresh, type de token vérifié à la relecture
  (un refresh token ne peut jamais servir d'access token).
- En-têtes de sécurité de base (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`) sur toutes les réponses.
- Aucun identifiant en dur : tout passe par variables d'environnement.

## Roadmap

| Phase | Contenu | Statut |
|---|---|---|
| 1 | Socle : Go/Echo, Next.js, auth JWT, Docker Compose, CI | ✅ |
| 2 | CRM prospects (ajout manuel/CSV, `source_note`, fiche entreprise) | ✅ |
| 3 | Enrichissement (Trustpilot par domaine, analyse IA du site via Groq) | ✅ |
| 4 | Campagnes email (éditeur de template, envoi SMTP, désinscription, limite quotidienne) | ✅ |
| 5 | Suivi (Kanban contacté/répondu/converti) | ⏳ |
