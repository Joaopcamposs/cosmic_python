"""Modelos de domínio para o contexto de alocação de estoque."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from . import events


class Product:
    """Agregado raiz que gerencia lotes e alocações de um SKU."""

    def __init__(self, sku: str, batches: list[Batch], version_number: int = 0) -> None:
        self.sku = sku
        self.batches = batches
        self.version_number = version_number
        self.events: list[events.Event] = []

    def allocate(self, line: OrderLine) -> str | None:
        """Aloca uma linha de pedido ao lote mais adequado disponível.

        Args:
            line: Linha de pedido a ser alocada.

        Returns:
            Referência do lote alocado ou None se sem estoque.
        """
        try:
            batch = next(b for b in sorted(self.batches) if b.can_allocate(line))
            batch.allocate(line)
            self.version_number += 1
            self.events.append(
                events.Allocated(
                    orderid=line.orderid,
                    sku=line.sku,
                    qty=line.qty,
                    batchref=batch.reference,
                )
            )
            return batch.reference
        except StopIteration:
            self.events.append(events.OutOfStock(line.sku))
            return None

    def change_batch_quantity(self, ref: str, qty: int) -> None:
        """Altera a quantidade de um lote e desaloca pedidos se necessário.

        Args:
            ref: Referência do lote.
            qty: Nova quantidade do lote.
        """
        batch = next(b for b in self.batches if b.reference == ref)
        batch._purchased_quantity = qty
        while batch.available_quantity < 0:
            line = batch.deallocate_one()
            self.events.append(events.Deallocated(line.orderid, line.sku, line.qty))


@dataclass(unsafe_hash=True)
class OrderLine:
    """Linha de pedido representando um item solicitado por um cliente."""

    orderid: str
    sku: str
    qty: int


class Batch:
    """Lote de produtos disponível para alocação."""

    def __init__(self, ref: str, sku: str, qty: int, eta: date | None) -> None:
        self.reference = ref
        self.sku = sku
        self.eta = eta
        self._purchased_quantity = qty
        self._allocations: set[OrderLine] = set()

    def __repr__(self) -> str:
        return f"<Batch {self.reference}>"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Batch):
            return False
        return other.reference == self.reference

    def __hash__(self) -> int:
        return hash(self.reference)

    def __gt__(self, other: Batch) -> bool:
        if self.eta is None:
            return False
        if other.eta is None:
            return True
        return self.eta > other.eta

    def allocate(self, line: OrderLine) -> None:
        """Aloca uma linha de pedido a este lote."""
        if self.can_allocate(line):
            self._allocations.add(line)

    def deallocate_one(self) -> OrderLine:
        """Remove e retorna uma alocação arbitrária deste lote."""
        return self._allocations.pop()

    @property
    def allocated_quantity(self) -> int:
        """Quantidade total alocada neste lote."""
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        """Quantidade disponível para alocação neste lote."""
        return self._purchased_quantity - self.allocated_quantity

    def can_allocate(self, line: OrderLine) -> bool:
        """Verifica se este lote pode alocar a linha de pedido."""
        return self.sku == line.sku and self.available_quantity >= line.qty
