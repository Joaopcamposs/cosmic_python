"""Testes de integração para o repositório SQLAlchemy."""

import pytest
from sqlalchemy.orm import Session, sessionmaker

from allocation.adapters import repository
from allocation.domain import model

pytestmark = pytest.mark.usefixtures("mappers")


class TestSqlAlchemyRepositoryAdd:
    """Testes de adição de produtos ao repositório."""

    def test_add_and_get_product(
        self, sqlite_session_factory: sessionmaker[Session]
    ) -> None:
        """Testa que um produto adicionado pode ser recuperado pelo SKU."""
        session = sqlite_session_factory()
        repo = repository.SqlAlchemyRepository(session)
        batch = model.Batch(ref="b1", sku="CHAIR", qty=100, eta=None)
        product = model.Product(sku="CHAIR", batches=[batch])

        repo.add(product)
        session.commit()

        retrieved = repo.get("CHAIR")
        assert retrieved is not None
        assert retrieved.sku == "CHAIR"
        assert len(retrieved.batches) == 1
        assert retrieved.batches[0].reference == "b1"

    def test_add_tracks_product_in_seen(
        self, sqlite_session_factory: sessionmaker[Session]
    ) -> None:
        """Testa que add() registra o produto no conjunto seen."""
        session = sqlite_session_factory()
        repo = repository.SqlAlchemyRepository(session)
        product = model.Product(sku="WIDGET", batches=[])

        repo.add(product)

        assert product in repo.seen


class TestSqlAlchemyRepositoryGet:
    """Testes de busca de produtos no repositório."""

    def test_get_returns_none_for_nonexistent_sku(
        self, sqlite_session_factory: sessionmaker[Session]
    ) -> None:
        """Testa que get() retorna None para SKU inexistente."""
        session = sqlite_session_factory()
        repo = repository.SqlAlchemyRepository(session)
        assert repo.get("NONEXISTENT") is None

    def test_get_tracks_product_in_seen(
        self, sqlite_session_factory: sessionmaker[Session]
    ) -> None:
        """Testa que get() registra o produto no conjunto seen."""
        session = sqlite_session_factory()
        repo = repository.SqlAlchemyRepository(session)
        product = model.Product(sku="TABLE", batches=[])
        repo.add(product)
        session.commit()
        repo.seen.clear()

        repo.get("TABLE")

        assert len(repo.seen) == 1

    def test_get_does_not_add_none_to_seen(
        self, sqlite_session_factory: sessionmaker[Session]
    ) -> None:
        """Testa que get() NÃO adiciona None ao seen quando produto não existe."""
        session = sqlite_session_factory()
        repo = repository.SqlAlchemyRepository(session)
        repo.get("NOPE")
        assert len(repo.seen) == 0


class TestSqlAlchemyRepositoryGetByBatchref:
    """Testes de busca por referência de lote."""

    def test_get_by_batchref(
        self, sqlite_session_factory: sessionmaker[Session]
    ) -> None:
        """Testa busca de produto por referência de lote."""
        session = sqlite_session_factory()
        repo = repository.SqlAlchemyRepository(session)
        b1 = model.Batch(ref="b1", sku="sku1", qty=100, eta=None)
        b2 = model.Batch(ref="b2", sku="sku1", qty=100, eta=None)
        b3 = model.Batch(ref="b3", sku="sku2", qty=100, eta=None)
        p1 = model.Product(sku="sku1", batches=[b1, b2])
        p2 = model.Product(sku="sku2", batches=[b3])
        repo.add(p1)
        repo.add(p2)
        assert repo.get_by_batchref("b2") == p1
        assert repo.get_by_batchref("b3") == p2

    def test_get_by_batchref_returns_none_for_nonexistent(
        self, sqlite_session_factory: sessionmaker[Session]
    ) -> None:
        """Testa que get_by_batchref() retorna None para referência inexistente."""
        session = sqlite_session_factory()
        repo = repository.SqlAlchemyRepository(session)
        assert repo.get_by_batchref("NONEXISTENT") is None

    def test_get_by_batchref_tracks_product_in_seen(
        self, sqlite_session_factory: sessionmaker[Session]
    ) -> None:
        """Testa que get_by_batchref() registra o produto no seen."""
        session = sqlite_session_factory()
        repo = repository.SqlAlchemyRepository(session)
        batch = model.Batch(ref="b1", sku="SKU", qty=50, eta=None)
        product = model.Product(sku="SKU", batches=[batch])
        repo.add(product)
        session.commit()
        repo.seen.clear()

        repo.get_by_batchref("b1")

        assert len(repo.seen) == 1
