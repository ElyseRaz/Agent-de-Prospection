.PHONY: up down build logs migrate makemigration sqlc test lint shell-api shell-db ps clean

ENV_FILE := .env

$(ENV_FILE):
	cp .env.example $(ENV_FILE)
	@echo ">> .env cree a partir de .env.example — pense a changer SECRET_KEY/POSTGRES_PASSWORD."

up: $(ENV_FILE)
	docker compose up --build -d
	@echo ">> Services demarres. Lance 'make migrate' avant la premiere utilisation."

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

migrate: $(ENV_FILE)
	docker compose run --rm migrate

sqlc:
	docker run --rm -v "$(CURDIR)/backend:/src" -w /src sqlc/sqlc generate

test:
	docker run --rm -v "$(CURDIR)/backend:/src" -w /src golang:1.25-alpine go test ./...

lint:
	docker run --rm -v "$(CURDIR)/backend:/src" -w /src golangci/golangci-lint:latest golangci-lint run

shell-api:
	docker compose exec api sh

shell-db:
	docker compose exec db psql -U $${POSTGRES_USER:-leadpilot} -d $${POSTGRES_DB:-leadpilot}

clean:
	docker compose down -v
