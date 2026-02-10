"""Testes unitários para o modelo Product."""

import pytest
from datetime import date, timedelta

from allocation.domain import events
from allocation.domain.model import Batch, OrderLine, Product

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


class TestProductAllocate:
    """Testes de alocação no Product."""

    def test_prefers_warehouse_batches_to_shipments(self) -> None:
        """Testa que lotes em estoque têm prioridade sobre embarques."""
        in_stock_batch = Batch("in-stock-batch", "RETRO-CLOCK", 100, eta=None)
        shipment_batch = Batch("shipment-batch", "RETRO-CLOCK", 100, eta=tomorrow)
        product = Product(sku="RETRO-CLOCK", batches=[in_stock_batch, shipment_batch])
        line = OrderLine("oref", "RETRO-CLOCK", 10)

        product.allocate(line)

        assert in_stock_batch.available_quantity == 90
        assert shipment_batch.available_quantity == 100

    def test_prefers_earlier_batches(self) -> None:
        """Testa que lotes com ETA mais próximo são preferidos."""
        earliest = Batch("speedy-batch", "MINIMALIST-SPOON", 100, eta=today)
        medium = Batch("normal-batch", "MINIMALIST-SPOON", 100, eta=tomorrow)
        latest = Batch("slow-batch", "MINIMALIST-SPOON", 100, eta=later)
        product = Product(sku="MINIMALIST-SPOON", batches=[medium, earliest, latest])
        line = OrderLine("order1", "MINIMALIST-SPOON", 10)

        product.allocate(line)

        assert earliest.available_quantity == 90
        assert medium.available_quantity == 100
        assert latest.available_quantity == 100

    def test_returns_allocated_batch_ref(self) -> None:
        """Testa que a alocação retorna a referência do lote."""
        in_stock_batch = Batch("in-stock-batch-ref", "HIGHBROW-POSTER", 100, eta=None)
        shipment_batch = Batch(
            "shipment-batch-ref", "HIGHBROW-POSTER", 100, eta=tomorrow
        )
        line = OrderLine("oref", "HIGHBROW-POSTER", 10)
        product = Product(
            sku="HIGHBROW-POSTER", batches=[in_stock_batch, shipment_batch]
        )
        allocation = product.allocate(line)
        assert allocation == in_stock_batch.reference

    def test_returns_none_when_out_of_stock(self) -> None:
        """Testa que retorna None quando não há estoque."""
        batch = Batch("batch1", "SMALL-FORK", 10, eta=today)
        product = Product(sku="SMALL-FORK", batches=[batch])
        product.allocate(OrderLine("order1", "SMALL-FORK", 10))
        allocation = product.allocate(OrderLine("order2", "SMALL-FORK", 1))
        assert allocation is None

    def test_allocate_with_empty_batches(self) -> None:
        """Testa alocação em produto sem lotes retorna None e emite OutOfStock."""
        product = Product(sku="EMPTY-SKU", batches=[])
        result = product.allocate(OrderLine("o1", "EMPTY-SKU", 1))
        assert result is None
        assert product.events[-1] == events.OutOfStock(sku="EMPTY-SKU")

    def test_multiple_allocations_to_same_product(self) -> None:
        """Testa múltiplas alocações ao mesmo produto usam lotes diferentes se necessário."""
        batch = Batch("b1", "DESK", 20, eta=None)
        product = Product(sku="DESK", batches=[batch])
        product.allocate(OrderLine("o1", "DESK", 10))
        product.allocate(OrderLine("o2", "DESK", 5))
        assert batch.available_quantity == 5
        assert product.version_number == 2


class TestProductEvents:
    """Testes de emissão de eventos do Product."""

    def test_outputs_allocated_event(self) -> None:
        """Testa que a alocação emite o evento Allocated."""
        batch = Batch("batchref", "RETRO-LAMPSHADE", 100, eta=None)
        line = OrderLine("oref", "RETRO-LAMPSHADE", 10)
        product = Product(sku="RETRO-LAMPSHADE", batches=[batch])
        product.allocate(line)
        expected = events.Allocated(
            orderid="oref", sku="RETRO-LAMPSHADE", qty=10, batchref=batch.reference
        )
        assert product.events[-1] == expected

    def test_records_out_of_stock_event_if_cannot_allocate(self) -> None:
        """Testa que evento OutOfStock é registrado quando não há estoque."""
        batch = Batch("batch1", "SMALL-FORK", 10, eta=today)
        product = Product(sku="SMALL-FORK", batches=[batch])
        product.allocate(OrderLine("order1", "SMALL-FORK", 10))
        product.allocate(OrderLine("order2", "SMALL-FORK", 1))
        assert product.events[-1] == events.OutOfStock(sku="SMALL-FORK")

    def test_events_list_starts_empty(self) -> None:
        """Testa que a lista de eventos começa vazia."""
        product = Product(sku="SKU", batches=[])
        assert product.events == []

    def test_multiple_allocations_produce_multiple_events(self) -> None:
        """Testa que múltiplas alocações geram múltiplos eventos Allocated."""
        batch = Batch("b1", "MULTI-SKU", 100, eta=None)
        product = Product(sku="MULTI-SKU", batches=[batch])
        product.allocate(OrderLine("o1", "MULTI-SKU", 10))
        product.allocate(OrderLine("o2", "MULTI-SKU", 20))
        assert len(product.events) == 2
        assert all(isinstance(e, events.Allocated) for e in product.events)


class TestProductVersioning:
    """Testes de versionamento do Product."""

    def test_increments_version_number(self) -> None:
        """Testa que a versão é incrementada a cada alocação."""
        line = OrderLine("oref", "SCANDI-PEN", 10)
        product = Product(
            sku="SCANDI-PEN", batches=[Batch("b1", "SCANDI-PEN", 100, eta=None)]
        )
        product.version_number = 7
        product.allocate(line)
        assert product.version_number == 8

    def test_version_starts_at_zero(self) -> None:
        """Testa que a versão começa em zero."""
        product = Product(sku="SKU", batches=[])
        assert product.version_number == 0

    def test_version_not_incremented_on_out_of_stock(self) -> None:
        """Testa que a versão NÃO incrementa quando há falta de estoque."""
        product = Product(sku="SKU", batches=[])
        product.version_number = 5
        product.allocate(OrderLine("o1", "SKU", 1))
        assert product.version_number == 5


class TestProductChangeBatchQuantity:
    """Testes de alteração de quantidade de lote no Product."""

    def test_change_batch_quantity_reduces_available(self) -> None:
        """Testa que alterar quantidade reduz o disponível."""
        batch = Batch("b1", "SKU", 50, eta=None)
        product = Product(sku="SKU", batches=[batch])
        product.change_batch_quantity("b1", 30)
        assert batch.available_quantity == 30

    def test_change_batch_quantity_emits_deallocated_events(self) -> None:
        """Testa que reduzir abaixo do alocado emite eventos Deallocated."""
        batch = Batch("b1", "SKU", 50, eta=None)
        product = Product(sku="SKU", batches=[batch])
        product.allocate(OrderLine("o1", "SKU", 20))
        product.events.clear()

        product.change_batch_quantity("b1", 10)

        deallocated_events = [
            e for e in product.events if isinstance(e, events.Deallocated)
        ]
        assert len(deallocated_events) == 1
        assert deallocated_events[0].orderid == "o1"
        assert deallocated_events[0].sku == "SKU"
        assert deallocated_events[0].qty == 20

    def test_change_batch_quantity_no_deallocation_needed(self) -> None:
        """Testa que reduzir sem ultrapassar alocação não emite Deallocated."""
        batch = Batch("b1", "SKU", 50, eta=None)
        product = Product(sku="SKU", batches=[batch])
        product.allocate(OrderLine("o1", "SKU", 10))
        product.events.clear()

        product.change_batch_quantity("b1", 30)

        assert len(product.events) == 0
        assert batch.available_quantity == 20

    def test_change_batch_quantity_raises_for_unknown_ref(self) -> None:
        """Testa que alterar lote inexistente lança StopIteration."""
        product = Product(sku="SKU", batches=[Batch("b1", "SKU", 50, eta=None)])
        with pytest.raises(StopIteration):
            product.change_batch_quantity("UNKNOWN", 10)
