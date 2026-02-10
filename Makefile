export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1

TEST_COMPOSE = docker compose -f docker-compose.test.yml -p cosmic-python-test

# ── Produção / Dev ──────────────────────────────────────────────

all: down build up

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down --remove-orphans

logs:
	docker compose logs --tail=25 api redis_pubsub

# ── Testes (compose separado) ───────────────────────────────────

test-build:
	$(TEST_COMPOSE) build

test-up: test-build
	$(TEST_COMPOSE) up -d

test-down:
	$(TEST_COMPOSE) down --remove-orphans

test: test-up
	$(TEST_COMPOSE) run --rm --no-deps --entrypoint=pytest api /tests/unit /tests/integration /tests/e2e

unit-tests: test-build
	$(TEST_COMPOSE) run --rm --no-deps --entrypoint=pytest api /tests/unit

integration-tests: test-up
	$(TEST_COMPOSE) run --rm --no-deps --entrypoint=pytest api /tests/integration

e2e-tests: test-up
	$(TEST_COMPOSE) run --rm --no-deps --entrypoint=pytest api /tests/e2e

test-logs:
	$(TEST_COMPOSE) logs --tail=25 api redis_pubsub

# ── Linting ─────────────────────────────────────────────────────

ruff:
	ruff format . && ruff check . --fix
