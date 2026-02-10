"""Handlers de comandos e eventos do barramento de mensagens."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import TYPE_CHECKING

from sqlalchemy import text

from allocation.domain import commands, events, model
from allocation.domain.model import OrderLine

if TYPE_CHECKING:
    from allocation.adapters import notifications
    from . import unit_of_work


class InvalidSku(Exception):
    """Exceção lançada quando um SKU inválido é solicitado para alocação."""


def add_batch(
    cmd: commands.CreateBatch,
    uow: unit_of_work.AbstractUnitOfWork,
) -> None:
    """Adiciona um novo lote a um produto existente ou cria o produto.

    Args:
        cmd: Comando com os dados do lote.
        uow: Unit of Work para gerenciar a transação.
    """
    with uow:
        product = uow.products.get(sku=cmd.sku)
        if product is None:
            product = model.Product(cmd.sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(cmd.ref, cmd.sku, cmd.qty, cmd.eta))
        uow.commit()


def allocate(
    cmd: commands.Allocate,
    uow: unit_of_work.AbstractUnitOfWork,
) -> None:
    """Aloca uma linha de pedido ao lote mais adequado.

    Args:
        cmd: Comando com os dados da alocação.
        uow: Unit of Work para gerenciar a transação.

    Raises:
        InvalidSku: Se o SKU não existir no sistema.
    """
    line = OrderLine(cmd.orderid, cmd.sku, cmd.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        product.allocate(line)
        uow.commit()


def reallocate(
    event: events.Deallocated,
    uow: unit_of_work.AbstractUnitOfWork,
) -> None:
    """Realoca uma linha de pedido desalocada."""
    allocate(commands.Allocate(**asdict(event)), uow=uow)


def change_batch_quantity(
    cmd: commands.ChangeBatchQuantity,
    uow: unit_of_work.AbstractUnitOfWork,
) -> None:
    """Altera a quantidade de um lote, podendo causar desalocações."""
    with uow:
        product = uow.products.get_by_batchref(batchref=cmd.ref)
        product.change_batch_quantity(ref=cmd.ref, qty=cmd.qty)
        uow.commit()


def send_out_of_stock_notification(
    event: events.OutOfStock,
    notifications: notifications.AbstractNotifications,
) -> None:
    """Envia notificação de falta de estoque por e-mail."""
    notifications.send(
        "stock@made.com",
        f"Out of stock for {event.sku}",
    )


def publish_allocated_event(
    event: events.Allocated,
    publish: Callable[[str, events.Event], None],
) -> None:
    """Publica evento de alocação no Redis."""
    publish("line_allocated", event)


def add_allocation_to_read_model(
    event: events.Allocated,
    uow: unit_of_work.SqlAlchemyUnitOfWork,
) -> None:
    """Adiciona alocação à view de leitura."""
    with uow:
        uow.session.execute(
            text(
                "INSERT INTO allocations_view (orderid, sku, batchref)"
                " VALUES (:orderid, :sku, :batchref)"
            ),
            dict(orderid=event.orderid, sku=event.sku, batchref=event.batchref),
        )
        uow.commit()


def remove_allocation_from_read_model(
    event: events.Deallocated,
    uow: unit_of_work.SqlAlchemyUnitOfWork,
) -> None:
    """Remove alocação da view de leitura."""
    with uow:
        uow.session.execute(
            text(
                "DELETE FROM allocations_view WHERE orderid = :orderid AND sku = :sku"
            ),
            dict(orderid=event.orderid, sku=event.sku),
        )
        uow.commit()


EVENT_HANDLERS: dict[type[events.Event], list[Callable[..., None]]] = {
    events.Allocated: [publish_allocated_event, add_allocation_to_read_model],
    events.Deallocated: [remove_allocation_from_read_model, reallocate],
    events.OutOfStock: [send_out_of_stock_notification],
}

COMMAND_HANDLERS: dict[type[commands.Command], Callable[..., None]] = {
    commands.Allocate: allocate,
    commands.CreateBatch: add_batch,
    commands.ChangeBatchQuantity: change_batch_quantity,
}
