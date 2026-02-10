"""Geradores de referências aleatórias para testes."""

import uuid


def random_suffix() -> str:
    """Gera um sufixo aleatório de 6 caracteres."""
    return uuid.uuid4().hex[:6]


def random_sku(name: str = "") -> str:
    """Gera um SKU aleatório."""
    return f"sku-{name}-{random_suffix()}"


def random_batchref(name: str | int = "") -> str:
    """Gera uma referência de lote aleatória."""
    return f"batch-{name}-{random_suffix()}"


def random_orderid(name: str | int = "") -> str:
    """Gera um ID de pedido aleatório."""
    return f"order-{name}-{random_suffix()}"
