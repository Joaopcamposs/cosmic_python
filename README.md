# Cosmic Python — Architecture Patterns with Python

Implementação dos padrões de arquitetura do livro **"Architecture Patterns with Python"**
usando **FastAPI**, **SQLAlchemy 2.0** e **Python 3.11**.

## Stack

- **Python 3.11** com tipagem completa e docstrings
- **FastAPI** + **Pydantic v2** para a API REST
- **SQLAlchemy 2.0** com mapeamento imperativo (`registry.map_imperatively`)
- **PostgreSQL 16** para persistência
- **Redis 7** para Pub/Sub de eventos
- **Docker Compose** para orquestração de serviços
- **pytest** para testes unitários, integração e e2e

## Requisitos

- Docker com Docker Compose v2
- (Opcional) Python 3.11 local com `uv` para desenvolvimento

## Build e execução

```sh
make build
make up
# ou
make all  # build, up, test
```

## Desenvolvimento local (opcional)

```sh
uv sync --all-extras
PYTHONPATH=src .venv/bin/python -m pytest tests/unit
```

## Testes

```sh
make test               # todos os testes (via Docker)
make unit-tests         # apenas unitários
make integration-tests  # apenas integração
make e2e-tests          # apenas e2e
```

## Makefile

Veja o `Makefile` para mais comandos úteis.

