"""Testes unitários para o modelo Batch."""

from datetime import date, timedelta

from allocation.domain.model import Batch, OrderLine

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def make_batch_and_line(
    sku: str, batch_qty: int, line_qty: int
) -> tuple[Batch, OrderLine]:
    """Cria um par lote/linha de pedido para testes."""
    return (
        Batch("batch-001", sku, batch_qty, eta=today),
        OrderLine("order-123", sku, line_qty),
    )


class TestBatchAllocate:
    """Testes de alocação no Batch."""

    def test_allocating_reduces_available_quantity(self) -> None:
        """Testa que alocar reduz a quantidade disponível."""
        batch = Batch("batch-001", "SMALL-TABLE", qty=20, eta=today)
        line = OrderLine("order-ref", "SMALL-TABLE", 2)
        batch.allocate(line)
        assert batch.available_quantity == 18

    def test_can_allocate_if_available_greater_than_required(self) -> None:
        """Testa que pode alocar quando há quantidade suficiente."""
        large_batch, small_line = make_batch_and_line("ELEGANT-LAMP", 20, 2)
        assert large_batch.can_allocate(small_line)

    def test_cannot_allocate_if_available_smaller_than_required(self) -> None:
        """Testa que não pode alocar quando a quantidade é insuficiente."""
        small_batch, large_line = make_batch_and_line("ELEGANT-LAMP", 2, 20)
        assert small_batch.can_allocate(large_line) is False

    def test_can_allocate_if_available_equal_to_required(self) -> None:
        """Testa que pode alocar quando a quantidade é exata."""
        batch, line = make_batch_and_line("ELEGANT-LAMP", 2, 2)
        assert batch.can_allocate(line)

    def test_cannot_allocate_if_skus_do_not_match(self) -> None:
        """Testa que não pode alocar com SKUs diferentes."""
        batch = Batch("batch-001", "UNCOMFORTABLE-CHAIR", 100, eta=None)
        different_sku_line = OrderLine("order-123", "EXPENSIVE-TOASTER", 10)
        assert batch.can_allocate(different_sku_line) is False

    def test_allocation_is_idempotent(self) -> None:
        """Testa que alocar a mesma linha duas vezes não duplica."""
        batch, line = make_batch_and_line("ANGULAR-DESK", 20, 2)
        batch.allocate(line)
        batch.allocate(line)
        assert batch.available_quantity == 18

    def test_allocate_does_nothing_if_cannot_allocate(self) -> None:
        """Testa que alocar com estoque insuficiente não altera o lote."""
        batch = Batch("batch-001", "SMALL-TABLE", qty=5, eta=today)
        line = OrderLine("order-ref", "SMALL-TABLE", 10)
        batch.allocate(line)
        assert batch.available_quantity == 5
        assert batch.allocated_quantity == 0


class TestBatchDeallocate:
    """Testes de desalocação no Batch."""

    def test_deallocate_one_returns_an_order_line(self) -> None:
        """Testa que deallocate_one remove e retorna uma linha alocada."""
        batch = Batch("batch-001", "FANCY-LAMP", qty=20, eta=today)
        line = OrderLine("order-1", "FANCY-LAMP", 5)
        batch.allocate(line)
        assert batch.available_quantity == 15
        deallocated = batch.deallocate_one()
        assert deallocated == line
        assert batch.available_quantity == 20

    def test_deallocate_one_from_multiple_allocations(self) -> None:
        """Testa deallocate_one quando há múltiplas alocações."""
        batch = Batch("batch-001", "FANCY-LAMP", qty=20, eta=today)
        line1 = OrderLine("order-1", "FANCY-LAMP", 5)
        line2 = OrderLine("order-2", "FANCY-LAMP", 3)
        batch.allocate(line1)
        batch.allocate(line2)
        assert batch.available_quantity == 12
        batch.deallocate_one()
        assert batch.available_quantity in (15, 17)


class TestBatchProperties:
    """Testes das propriedades calculadas do Batch."""

    def test_allocated_quantity_with_no_allocations(self) -> None:
        """Testa que allocated_quantity é zero sem alocações."""
        batch = Batch("batch-001", "WIDGET", qty=50, eta=today)
        assert batch.allocated_quantity == 0

    def test_allocated_quantity_with_multiple_allocations(self) -> None:
        """Testa que allocated_quantity soma todas as alocações."""
        batch = Batch("batch-001", "WIDGET", qty=50, eta=today)
        batch.allocate(OrderLine("o1", "WIDGET", 10))
        batch.allocate(OrderLine("o2", "WIDGET", 5))
        assert batch.allocated_quantity == 15

    def test_available_quantity_is_purchased_minus_allocated(self) -> None:
        """Testa que available_quantity = purchased - allocated."""
        batch = Batch("batch-001", "WIDGET", qty=50, eta=today)
        batch.allocate(OrderLine("o1", "WIDGET", 10))
        assert batch.available_quantity == 40


class TestBatchEquality:
    """Testes de igualdade, hash e repr do Batch."""

    def test_batches_with_same_reference_are_equal(self) -> None:
        """Testa que dois lotes com mesma referência são iguais."""
        batch1 = Batch("batch-001", "SKU-A", 100, eta=today)
        batch2 = Batch("batch-001", "SKU-B", 50, eta=tomorrow)
        assert batch1 == batch2

    def test_batches_with_different_reference_are_not_equal(self) -> None:
        """Testa que dois lotes com referências diferentes não são iguais."""
        batch1 = Batch("batch-001", "SKU-A", 100, eta=today)
        batch2 = Batch("batch-002", "SKU-A", 100, eta=today)
        assert batch1 != batch2

    def test_batch_is_not_equal_to_non_batch(self) -> None:
        """Testa que Batch não é igual a outro tipo."""
        batch = Batch("batch-001", "SKU-A", 100, eta=today)
        assert batch != "batch-001"
        assert batch != 42

    def test_batches_with_same_reference_have_same_hash(self) -> None:
        """Testa que lotes com mesma referência têm o mesmo hash."""
        batch1 = Batch("batch-001", "SKU-A", 100, eta=today)
        batch2 = Batch("batch-001", "SKU-B", 50, eta=tomorrow)
        assert hash(batch1) == hash(batch2)
        assert len({batch1, batch2}) == 1

    def test_repr(self) -> None:
        """Testa a representação textual do Batch."""
        batch = Batch("batch-42", "FANCY-LAMP", 100, eta=today)
        assert repr(batch) == "<Batch batch-42>"


class TestBatchSorting:
    """Testes de ordenação de Batch por ETA."""

    def test_warehouse_batch_comes_before_shipment(self) -> None:
        """Testa que lote em estoque (eta=None) vem antes de embarque."""
        warehouse = Batch("wh-batch", "SKU", 100, eta=None)
        shipment = Batch("ship-batch", "SKU", 100, eta=today)
        assert sorted([shipment, warehouse]) == [warehouse, shipment]

    def test_earlier_eta_comes_first(self) -> None:
        """Testa que lote com ETA mais cedo vem primeiro."""
        early = Batch("early", "SKU", 100, eta=today)
        late = Batch("late", "SKU", 100, eta=later)
        assert sorted([late, early]) == [early, late]

    def test_two_warehouse_batches_are_not_ordered(self) -> None:
        """Testa que dois lotes em estoque não têm ordenação relativa via gt."""
        b1 = Batch("b1", "SKU", 100, eta=None)
        b2 = Batch("b2", "SKU", 100, eta=None)
        assert not (b1 > b2)
        assert not (b2 > b1)

    def test_sorting_multiple_batches(self) -> None:
        """Testa ordenação com mistura de estoque e embarques."""
        warehouse = Batch("wh", "SKU", 100, eta=None)
        early = Batch("early", "SKU", 100, eta=today)
        mid = Batch("mid", "SKU", 100, eta=tomorrow)
        late = Batch("late", "SKU", 100, eta=later)
        result = sorted([late, warehouse, mid, early])
        assert result == [warehouse, early, mid, late]
