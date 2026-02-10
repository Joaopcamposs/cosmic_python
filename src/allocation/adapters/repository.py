"""Repositórios para persistência de agregados de domínio."""

import abc

from sqlalchemy import select
from sqlalchemy.orm import Session

from allocation.adapters import orm
from allocation.domain import model


class AbstractRepository(abc.ABC):
    """Classe base abstrata para repositórios de Product."""

    def __init__(self) -> None:
        self.seen: set[model.Product] = set()

    def add(self, product: model.Product) -> None:
        """Adiciona um produto ao repositório e rastreia como visto."""
        self._add(product)
        self.seen.add(product)

    def get(self, sku: str) -> model.Product | None:
        """Obtém um produto pelo SKU."""
        product = self._get(sku)
        if product:
            self.seen.add(product)
        return product

    def get_by_batchref(self, batchref: str) -> model.Product | None:
        """Obtém um produto pela referência do lote."""
        product = self._get_by_batchref(batchref)
        if product:
            self.seen.add(product)
        return product

    @abc.abstractmethod
    def _add(self, product: model.Product) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, sku: str) -> model.Product | None:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_by_batchref(self, batchref: str) -> model.Product | None:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    """Repositório concreto usando SQLAlchemy 2.0."""

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session

    def _add(self, product: model.Product) -> None:
        self.session.add(product)

    def _get(self, sku: str) -> model.Product | None:
        return self.session.scalars(select(model.Product).filter_by(sku=sku)).first()

    def _get_by_batchref(self, batchref: str) -> model.Product | None:
        return self.session.scalars(
            select(model.Product)
            .join(model.Batch)
            .where(orm.batches.c.reference == batchref)
        ).first()
