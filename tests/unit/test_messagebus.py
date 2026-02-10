"""Testes unitários para o barramento de mensagens."""

from __future__ import annotations

import pytest
from unittest import mock

from allocation.domain import commands, events
from allocation.service_layer import messagebus, unit_of_work
from allocation.adapters import repository
from allocation.domain.model import Product


class FakeRepository(repository.AbstractRepository):
    """Repositório fake para testes do MessageBus."""

    def __init__(self) -> None:
        super().__init__()
        self._products: set[Product] = set()

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
    """Unit of Work fake para testes do MessageBus."""

    def __init__(self) -> None:
        self.products = FakeRepository()
        self.committed = False

    def _commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


class TestMessageBusHandleCommand:
    """Testes de processamento de comandos no MessageBus."""

    def test_command_handler_is_called(self) -> None:
        """Testa que o handler do comando é invocado."""
        handler = mock.Mock()
        bus = messagebus.MessageBus(
            uow=FakeUnitOfWork(),
            event_handlers={},
            command_handlers={commands.CreateBatch: handler},
        )
        cmd = commands.CreateBatch("b1", "SKU", 100, None)
        bus.handle(cmd)
        handler.assert_called_once_with(cmd)

    def test_command_exception_is_propagated(self) -> None:
        """Testa que exceção no handler de comando é re-lançada."""

        def failing_handler(cmd: commands.Allocate) -> None:
            raise ValueError("boom")

        bus = messagebus.MessageBus(
            uow=FakeUnitOfWork(),
            event_handlers={},
            command_handlers={commands.Allocate: failing_handler},
        )
        with pytest.raises(ValueError, match="boom"):
            bus.handle(commands.Allocate("o1", "SKU", 10))


class TestMessageBusHandleEvent:
    """Testes de processamento de eventos no MessageBus."""

    def test_event_handlers_are_called(self) -> None:
        """Testa que todos os handlers de um evento são invocados."""
        handler1 = mock.Mock()
        handler2 = mock.Mock()
        bus = messagebus.MessageBus(
            uow=FakeUnitOfWork(),
            event_handlers={events.OutOfStock: [handler1, handler2]},
            command_handlers={},
        )
        event = events.OutOfStock(sku="SKU")
        bus.handle(event)
        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)

    def test_event_handler_exception_does_not_stop_other_handlers(self) -> None:
        """Testa que falha em um handler de evento não impede os demais."""
        handler1 = mock.Mock(side_effect=RuntimeError("fail"))
        handler2 = mock.Mock()
        bus = messagebus.MessageBus(
            uow=FakeUnitOfWork(),
            event_handlers={events.OutOfStock: [handler1, handler2]},
            command_handlers={},
        )
        bus.handle(events.OutOfStock(sku="SKU"))
        handler2.assert_called_once()

    def test_event_handler_exception_is_logged_not_raised(self) -> None:
        """Testa que exceção em handler de evento é logada e não propagada."""

        def failing_handler(event: events.OutOfStock) -> None:
            raise RuntimeError("should not propagate")

        bus = messagebus.MessageBus(
            uow=FakeUnitOfWork(),
            event_handlers={events.OutOfStock: [failing_handler]},
            command_handlers={},
        )
        bus.handle(events.OutOfStock(sku="SKU"))


class TestMessageBusInvalidMessage:
    """Testes de mensagens inválidas no MessageBus."""

    def test_raises_for_unknown_message_type(self) -> None:
        """Testa que mensagem que não é Command nem Event lança exceção."""
        bus = messagebus.MessageBus(
            uow=FakeUnitOfWork(),
            event_handlers={},
            command_handlers={},
        )
        with pytest.raises(Exception, match="was not an Event or Command"):
            bus.handle("not a message")  # type: ignore[arg-type]


class TestMessageBusEventCascade:
    """Testes de cascateamento de eventos no MessageBus."""

    def test_command_generates_events_that_are_processed(self) -> None:
        """Testa que eventos gerados por comandos são processados em sequência."""
        event_log: list[str] = []

        def create_batch_handler(cmd: commands.CreateBatch) -> None:
            event_log.append(f"cmd:{cmd.ref}")

        def allocated_handler(event: events.Allocated) -> None:
            event_log.append(f"evt:{event.batchref}")

        uow = FakeUnitOfWork()

        bus = messagebus.MessageBus(
            uow=uow,
            event_handlers={events.Allocated: [allocated_handler]},
            command_handlers={commands.CreateBatch: create_batch_handler},
        )
        bus.handle(commands.CreateBatch("b1", "SKU", 100, None))
        assert "cmd:b1" in event_log
