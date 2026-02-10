"""Testes de integração para notificações por e-mail."""

import pytest
import requests
from sqlalchemy.orm import Session, sessionmaker

from allocation import bootstrap, config
from allocation.adapters import notifications
from allocation.adapters.orm import mapper_registry
from allocation.domain import commands
from allocation.service_layer import unit_of_work
from allocation.service_layer.messagebus import MessageBus
from ..random_refs import random_sku


@pytest.fixture
def bus(sqlite_session_factory: sessionmaker[Session]) -> MessageBus:
    """Cria um MessageBus com notificações reais via SMTP para testes de e-mail."""
    bus = bootstrap.bootstrap(
        start_orm=True,
        uow=unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory),
        notifications=notifications.EmailNotifications(),
        publish=lambda *args: None,
    )
    yield bus
    mapper_registry.dispose()


def get_email_from_mailhog(sku: str) -> dict[str, object]:
    """Busca um e-mail no MailHog filtrando pelo SKU."""
    host, port = map(config.get_email_host_and_port().get, ["host", "http_port"])
    all_emails = requests.get(f"http://{host}:{port}/api/v2/messages").json()
    return next(m for m in all_emails["items"] if sku in str(m))


def test_out_of_stock_email(bus: MessageBus) -> None:
    """Testa que um e-mail de falta de estoque é enviado corretamente."""
    sku = random_sku()
    bus.handle(commands.CreateBatch("batch1", sku, 9, None))
    bus.handle(commands.Allocate("order1", sku, 10))
    email = get_email_from_mailhog(sku)
    assert email["Raw"]["From"] == "allocations@example.com"
    assert email["Raw"]["To"] == ["stock@made.com"]
    assert f"Out of stock for {sku}" in email["Raw"]["Data"]
