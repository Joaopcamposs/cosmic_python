"""Testes e2e para a API de alocação."""

import pytest

from . import api_client
from ..random_refs import random_batchref, random_orderid, random_sku


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_202_and_batch_is_allocated() -> None:
    """Testa o fluxo feliz: alocação retorna 202 e batch correto."""
    orderid = random_orderid()
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref(1)
    laterbatch = random_batchref(2)
    otherbatch = random_batchref(3)
    api_client.post_to_add_batch(laterbatch, sku, 100, "2011-01-02")
    api_client.post_to_add_batch(earlybatch, sku, 100, "2011-01-01")
    api_client.post_to_add_batch(otherbatch, othersku, 100, None)

    r = api_client.post_to_allocate(orderid, sku, qty=3)
    assert r.status_code == 202

    r = api_client.get_allocation(orderid)
    assert r.ok
    assert r.json() == [
        {"sku": sku, "batchref": earlybatch},
    ]


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message() -> None:
    """Testa que SKU inválido retorna 400 com mensagem de erro."""
    unknown_sku, orderid = random_sku(), random_orderid()
    r = api_client.post_to_allocate(orderid, unknown_sku, qty=20, expect_success=False)
    assert r.status_code == 400
    assert r.json()["detail"] == f"Invalid sku {unknown_sku}"

    r = api_client.get_allocation(orderid)
    assert r.status_code == 404


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_add_batch_returns_201() -> None:
    """Testa que adicionar um lote retorna 201."""
    sku = random_sku()
    ref = random_batchref()
    api_client.post_to_add_batch(ref, sku, 100, None)


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_add_batch_with_eta() -> None:
    """Testa que adicionar um lote com ETA funciona."""
    sku = random_sku()
    ref = random_batchref()
    api_client.post_to_add_batch(ref, sku, 100, "2025-06-15")


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_allocations_returns_404_for_unknown_order() -> None:
    """Testa que consultar alocações de pedido inexistente retorna 404."""
    r = api_client.get_allocation(random_orderid())
    assert r.status_code == 404
    assert r.json()["detail"] == "not found"


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_allocate_multiple_lines_to_same_order() -> None:
    """Testa alocação de múltiplos SKUs ao mesmo pedido."""
    orderid = random_orderid()
    sku1, sku2 = random_sku("a"), random_sku("b")
    batch1, batch2 = random_batchref(1), random_batchref(2)
    api_client.post_to_add_batch(batch1, sku1, 50, None)
    api_client.post_to_add_batch(batch2, sku2, 50, None)

    api_client.post_to_allocate(orderid, sku1, 10)
    api_client.post_to_allocate(orderid, sku2, 20)

    r = api_client.get_allocation(orderid)
    assert r.ok
    data = r.json()
    assert len(data) == 2
    skus = {item["sku"] for item in data}
    assert sku1 in skus
    assert sku2 in skus


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_allocate_prefers_warehouse_over_shipment() -> None:
    """Testa que a API aloca preferencialmente em lotes de estoque."""
    orderid = random_orderid()
    sku = random_sku()
    warehouse_batch = random_batchref("wh")
    shipment_batch = random_batchref("ship")
    api_client.post_to_add_batch(shipment_batch, sku, 100, "2030-01-01")
    api_client.post_to_add_batch(warehouse_batch, sku, 100, None)

    api_client.post_to_allocate(orderid, sku, 10)

    r = api_client.get_allocation(orderid)
    assert r.ok
    assert r.json()[0]["batchref"] == warehouse_batch
