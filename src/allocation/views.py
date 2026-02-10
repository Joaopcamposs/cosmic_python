"""Views de leitura para consultas de alocação."""

from sqlalchemy import text

from allocation.service_layer import unit_of_work


def allocations(
    orderid: str, uow: unit_of_work.SqlAlchemyUnitOfWork
) -> list[dict[str, str]]:
    """Retorna as alocações de um pedido a partir da view de leitura.

    Args:
        orderid: Identificador do pedido.
        uow: Unit of Work para acesso ao banco.

    Returns:
        Lista de dicionários com sku e batchref.
    """
    with uow:
        results = uow.session.execute(
            text("SELECT sku, batchref FROM allocations_view WHERE orderid = :orderid"),
            dict(orderid=orderid),
        )
    return [dict(r._mapping) for r in results]
