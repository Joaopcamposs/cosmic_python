"""Eventos de domínio para o contexto de alocação."""

from dataclasses import dataclass


class Event:
    """Classe base para todos os eventos de domínio."""


@dataclass
class Allocated(Event):
    """Evento emitido quando uma linha de pedido é alocada a um lote."""

    orderid: str
    sku: str
    qty: int
    batchref: str


@dataclass
class Deallocated(Event):
    """Evento emitido quando uma linha de pedido é desalocada de um lote."""

    orderid: str
    sku: str
    qty: int


@dataclass
class OutOfStock(Event):
    """Evento emitido quando não há estoque suficiente para alocar."""

    sku: str
