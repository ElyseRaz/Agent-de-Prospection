.PHONY: up down build logs migrate makemigration test lint shell-api shell-db ps clean

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
	docker compose exec api alembic upgrade head

makemigration: $(ENV_FILE)
	docker compose exec api alembic revision --autogenerate -m "$(m)"

test:
	docker compose exec api pytest --cov=app --cov-report=term-missing

lint:
	docker compose exec api ruff check app tests

shell-api:
	docker compose exec api bash

shell-db:
	docker compose exec db psql -U $${POSTGRES_USER:-remoteradar} -d $${POSTGRES_DB:-remoteradar}

clean:
	docker compose down -v
