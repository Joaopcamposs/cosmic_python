"""Comandos do domínio para o contexto de alocação."""

from dataclasses import dataclass
from datetime import date


class Command:
    """Classe base para todos os comandos de domínio."""


@dataclass
class Allocate(Command):
    """Comando para alocar uma linha de pedido a um lote disponível."""

    orderid: str
    sku: str
    qty: int


@dataclass
class CreateBatch(Command):
    """Comando para criar um novo lote de produtos."""

    ref: str
    sku: str
    qty: int
    eta: date | None = None


@dataclass
class ChangeBatchQuantity(Command):
    """Comando para alterar a quantidade de um lote existente."""

    ref: str
    qty: int
