"""Testes de integração para as views de leitura."""

from datetime import date
from unittest import mock

import pytest
from sqlalchemy.orm import Session, sessionmaker

from allocation import bootstrap, views
from allocation.adapters.orm import mapper_registry
from allocation.domain import commands
from allocation.service_layer import unit_of_work
from allocation.service_layer.messagebus import MessageBus

today = date.today()


@pytest.fixture
def sqlite_bus(sqlite_session_factory: sessionmaker[Session]) -> MessageBus:
    """Cria um MessageBus com SQLite em memória para testes de views."""
    bus = bootstrap.bootstrap(
        start_orm=True,
        uow=unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory),
        notifications=mock.Mock(),
        publish=lambda *args: None,
    )
    yield bus
    mapper_registry.dispose()


def test_allocations_view(sqlite_bus: MessageBus) -> None:
    """Testa que a view de alocações retorna os dados corretos."""
    sqlite_bus.handle(commands.CreateBatch("sku1batch", "sku1", 50, None))
    sqlite_bus.handle(commands.CreateBatch("sku2batch", "sku2", 50, today))
    sqlite_bus.handle(commands.Allocate("order1", "sku1", 20))
    sqlite_bus.handle(commands.Allocate("order1", "sku2", 20))
    # add a spurious batch and order to make sure we're getting the right ones
    sqlite_bus.handle(commands.CreateBatch("sku1batch-later", "sku1", 50, today))
    sqlite_bus.handle(commands.Allocate("otherorder", "sku1", 30))
    sqlite_bus.handle(commands.Allocate("otherorder", "sku2", 10))

    assert views.allocations("order1", sqlite_bus.uow) == [
        {"sku": "sku1", "batchref": "sku1batch"},
        {"sku": "sku2", "batchref": "sku2batch"},
    ]


def test_deallocation(sqlite_bus: MessageBus) -> None:
    """Testa que a desalocação e realocação atualizam a view corretamente."""
    sqlite_bus.handle(commands.CreateBatch("b1", "sku1", 50, None))
    sqlite_bus.handle(commands.CreateBatch("b2", "sku1", 50, today))
    sqlite_bus.handle(commands.Allocate("o1", "sku1", 40))
    sqlite_bus.handle(commands.ChangeBatchQuantity("b1", 10))

    assert views.allocations("o1", sqlite_bus.uow) == [
        {"sku": "sku1", "batchref": "b2"},
    ]


def test_allocations_view_returns_empty_for_unknown_order(
    sqlite_bus: MessageBus,
) -> None:
    """Testa que a view retorna lista vazia para pedido inexistente."""
    assert views.allocations("NONEXISTENT", sqlite_bus.uow) == []


def test_allocations_view_after_multiple_batches_same_sku(
    sqlite_bus: MessageBus,
) -> None:
    """Testa que alocação escolhe o lote correto e a view reflete isso."""
    sqlite_bus.handle(commands.CreateBatch("later-batch", "LAMP", 50, today))
    sqlite_bus.handle(commands.CreateBatch("warehouse-batch", "LAMP", 50, None))
    sqlite_bus.handle(commands.Allocate("order1", "LAMP", 10))

    result = views.allocations("order1", sqlite_bus.uow)
    assert len(result) == 1
    assert result[0]["batchref"] == "warehouse-batch"
