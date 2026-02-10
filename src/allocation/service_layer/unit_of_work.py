"""Unit of Work para gerenciamento de transações."""

from __future__ import annotations

import abc
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from allocation import config
from allocation.adapters import repository
from allocation.domain import events


class AbstractUnitOfWork(abc.ABC):
    """Interface abstrata do Unit of Work."""

    products: repository.AbstractRepository

    def __enter__(self) -> AbstractUnitOfWork:
        return self

    def __exit__(self, *args: object) -> None:
        self.rollback()

    def commit(self) -> None:
        """Persiste as alterações na transação atual."""
        self._commit()

    def collect_new_events(self) -> Generator[events.Event, None, None]:
        """Coleta eventos pendentes de todos os agregados rastreados."""
        for product in self.products.seen:
            while product.events:
                yield product.events.pop(0)

    @abc.abstractmethod
    def _commit(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self) -> None:
        """Desfaz as alterações da transação atual."""
        raise NotImplementedError


DEFAULT_SESSION_FACTORY: sessionmaker[Session] = sessionmaker(
    bind=create_engine(
        config.get_postgres_uri(),
        isolation_level="REPEATABLE READ",
    )
)


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """Implementação concreta do Unit of Work com SQLAlchemy."""

    def __init__(
        self, session_factory: sessionmaker[Session] = DEFAULT_SESSION_FACTORY
    ) -> None:
        self.session_factory = session_factory

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self.session: Session = self.session_factory()
        self.products = repository.SqlAlchemyRepository(self.session)
        return self

    def __exit__(self, *args: object) -> None:
        super().__exit__(*args)
        self.session.close()

    def _commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        """Desfaz as alterações da sessão atual."""
        self.session.rollback()
