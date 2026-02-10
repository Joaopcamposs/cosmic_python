"""Cliente HTTP para testes e2e da API de alocação."""

import requests

from allocation import config


def post_to_add_batch(ref: str, sku: str, qty: int, eta: str | None) -> None:
    """Envia requisição para criar um lote."""
    url = config.get_api_url()
    r = requests.post(
        f"{url}/add_batch", json={"ref": ref, "sku": sku, "qty": qty, "eta": eta}
    )
    assert r.status_code == 201


def post_to_allocate(
    orderid: str, sku: str, qty: int, expect_success: bool = True
) -> requests.Response:
    """Envia requisição para alocar um pedido."""
    url = config.get_api_url()
    r = requests.post(
        f"{url}/allocate",
        json={
            "orderid": orderid,
            "sku": sku,
            "qty": qty,
        },
    )
    if expect_success:
        assert r.status_code == 202
    return r


def get_allocation(orderid: str) -> requests.Response:
    """Consulta as alocações de um pedido."""
    url = config.get_api_url()
    return requests.get(f"{url}/allocations/{orderid}")
