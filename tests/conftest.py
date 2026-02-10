"""Fixtures compartilhadas para os testes do serviço de alocação."""

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import redis
import requests
from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from tenacity import retry, stop_after_delay

from allocation import config
from allocation.adapters.orm import mapper_registry, metadata, start_mappers

pytest.register_assert_rewrite("tests.e2e.api_client")


@pytest.fixture
def in_memory_sqlite_db() -> Engine:
    """Cria um banco SQLite em memória com todas as tabelas."""
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine


@pytest.fixture
def sqlite_session_factory(in_memory_sqlite_db: Engine) -> sessionmaker[Session]:
    """Retorna uma fábrica de sessões SQLite em memória."""
    yield sessionmaker(bind=in_memory_sqlite_db)


@pytest.fixture
def mappers() -> None:
    """Inicializa e limpa os mappers do ORM entre testes."""
    start_mappers()
    yield
    mapper_registry.dispose()


@retry(stop=stop_after_delay(10))
def wait_for_postgres_to_come_up(engine: Engine) -> Connection:
    """Aguarda o PostgreSQL ficar disponível."""
    return engine.connect()


@retry(stop=stop_after_delay(10))
def wait_for_webapp_to_come_up() -> requests.Response:
    """Aguarda a aplicação web ficar disponível."""
    return requests.get(config.get_api_url())


@retry(stop=stop_after_delay(10))
def wait_for_redis_to_come_up() -> bool:
    """Aguarda o Redis ficar disponível."""
    r = redis.Redis(**config.get_redis_host_and_port())  # type: ignore[arg-type]
    return r.ping()


@pytest.fixture(scope="session")
def postgres_db() -> Engine:
    """Cria e retorna a engine PostgreSQL para testes de integração."""
    engine = create_engine(config.get_postgres_uri(), isolation_level="SERIALIZABLE")
    wait_for_postgres_to_come_up(engine)
    metadata.create_all(engine)
    return engine


@pytest.fixture
def postgres_session_factory(postgres_db: Engine) -> sessionmaker[Session]:
    """Retorna uma fábrica de sessões PostgreSQL."""
    yield sessionmaker(bind=postgres_db)


@pytest.fixture
def postgres_session(postgres_session_factory: sessionmaker[Session]) -> Session:
    """Retorna uma sessão PostgreSQL."""
    return postgres_session_factory()


@pytest.fixture
def restart_api() -> None:
    """Reinicia a API tocando o arquivo de entrypoint."""
    (Path(__file__).parent / "../src/allocation/entrypoints/fastapi_app.py").touch()
    time.sleep(0.5)
    wait_for_webapp_to_come_up()


def _compose_cmd() -> list[str]:
    """Retorna o comando compose correto para o ambiente de testes."""
    compose_file = os.environ.get("COMPOSE_FILE", "docker-compose.test.yml")
    project = os.environ.get("COMPOSE_PROJECT_NAME", "cosmic-python-test")
    return ["docker", "compose", "-f", compose_file, "-p", project]


@pytest.fixture
def restart_redis_pubsub() -> None:
    """Reinicia o consumidor Redis Pub/Sub."""
    wait_for_redis_to_come_up()
    if not shutil.which("docker"):
        print("skipping restart, assumes running in container")
        return
    subprocess.run(
        [*_compose_cmd(), "restart", "-t", "0", "redis_pubsub"],
        check=True,
    )
