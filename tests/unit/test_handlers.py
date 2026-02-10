"""Testes unitários para os handlers de comandos e eventos."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

import pytest

from allocation import bootstrap
from allocation.adapters import notifications, repository
from allocation.domain import commands
from allocation.domain.model import Product
from allocation.service_layer import handlers, unit_of_work
from allocation.service_layer.messagebus import MessageBus


class FakeRepository(repository.AbstractRepository):
    """Repositório em memória para testes unitários."""

    def __init__(self, products: list[Product]) -> None:
        super().__init__()
        self._products = set(products)

    def _add(self, product: Product) -> None:
        self._products.add(product)

    def _get(self, sku: str) -> Product | None:
        return next((p for p in self._products if p.sku == sku), None)

    def _get_by_batchref(self, batchref: str) -> Product | None:
        return next(
            (p for p in self._products for b in p.batches if b.reference == batchref),
            None,
        )


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    """Unit of Work em memória para testes unitários."""

    def __init__(self) -> None:
        self.products = FakeRepository([])
        self.committed = False

    def _commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


class FakeNotifications(notifications.AbstractNotifications):
    """Notificações fake que registra mensagens enviadas."""

    def __init__(self) -> None:
        self.sent: defaultdict[str, list[str]] = defaultdict(list)

    def send(self, destination: str, message: str) -> None:
        self.sent[destination].append(message)


def bootstrap_test_app() -> MessageBus:
    """Cria um MessageBus com fakes para testes unitários."""
    return bootstrap.bootstrap(
        start_orm=False,
        uow=FakeUnitOfWork(),
        notifications=FakeNotifications(),
        publish=lambda *args: None,
    )


class TestAddBatch:
    """Testes para o handler de criação de lotes."""

    def test_for_new_product(self) -> None:
        """Testa criação de lote para um produto novo."""
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "CRUNCHY-ARMCHAIR", 100, None))
        assert bus.uow.products.get("CRUNCHY-ARMCHAIR") is not None
        assert bus.uow.committed

    def test_for_existing_product(self) -> None:
        """Testa adição de lote a um produto existente."""
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "GARISH-RUG", 100, None))
        bus.handle(commands.CreateBatch("b2", "GARISH-RUG", 99, None))
        assert "b2" in [b.reference for b in bus.uow.products.get("GARISH-RUG").batches]


class TestAllocate:
    """Testes para o handler de alocação."""

    def test_allocates(self) -> None:
        """Testa alocação bem-sucedida."""
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("batch1", "COMPLICATED-LAMP", 100, None))
        bus.handle(commands.Allocate("o1", "COMPLICATED-LAMP", 10))
        [batch] = bus.uow.products.get("COMPLICATED-LAMP").batches
        assert batch.available_quantity == 90

    def test_errors_for_invalid_sku(self) -> None:
        """Testa que alocação com SKU inválido lança exceção."""
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "AREALSKU", 100, None))

        with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
            bus.handle(commands.Allocate("o1", "NONEXISTENTSKU", 10))

    def test_commits(self) -> None:
        """Testa que a alocação faz commit."""
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "OMINOUS-MIRROR", 100, None))
        bus.handle(commands.Allocate("o1", "OMINOUS-MIRROR", 10))
        assert bus.uow.committed

    def test_sends_email_on_out_of_stock_error(self) -> None:
        """Testa que um e-mail é enviado quando não há estoque."""
        fake_notifs = FakeNotifications()
        bus = bootstrap.bootstrap(
            start_orm=False,
            uow=FakeUnitOfWork(),
            notifications=fake_notifs,
            publish=lambda *args: None,
        )
        bus.handle(commands.CreateBatch("b1", "POPULAR-CURTAINS", 9, None))
        bus.handle(commands.Allocate("o1", "POPULAR-CURTAINS", 10))
        assert fake_notifs.sent["stock@made.com"] == [
            "Out of stock for POPULAR-CURTAINS",
        ]


class TestChangeBatchQuantity:
    """Testes para o handler de alteração de quantidade de lote."""

    def test_changes_available_quantity(self) -> None:
        """Testa alteração simples de quantidade."""
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("batch1", "ADORABLE-SETTEE", 100, None))
        [batch] = bus.uow.products.get(sku="ADORABLE-SETTEE").batches
        assert batch.available_quantity == 100

        bus.handle(commands.ChangeBatchQuantity("batch1", 50))
        assert batch.available_quantity == 50

    def test_reallocates_if_necessary(self) -> None:
        """Testa que reduzir a quantidade causa realocação automática."""
        bus = bootstrap_test_app()
        history = [
            commands.CreateBatch("batch1", "INDIFFERENT-TABLE", 50, None),
            commands.CreateBatch("batch2", "INDIFFERENT-TABLE", 50, date.today()),
            commands.Allocate("order1", "INDIFFERENT-TABLE", 20),
            commands.Allocate("order2", "INDIFFERENT-TABLE", 20),
        ]
        for msg in history:
            bus.handle(msg)
        [batch1, batch2] = bus.uow.products.get(sku="INDIFFERENT-TABLE").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        bus.handle(commands.ChangeBatchQuantity("batch1", 25))

        # order1 or order2 will be deallocated, so we'll have 25 - 20
        assert batch1.available_quantity == 5
        # and 20 will be reallocated to the next batch
        assert batch2.available_quantity == 30
