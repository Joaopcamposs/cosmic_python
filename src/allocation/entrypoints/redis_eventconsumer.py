"""Consumidor de eventos Redis para o serviço de alocação."""

import json
import logging

import redis

from allocation import bootstrap, config
from allocation.domain import commands
from allocation.service_layer.messagebus import MessageBus

logger = logging.getLogger(__name__)

r: redis.Redis = redis.Redis(**config.get_redis_host_and_port())  # type: ignore[arg-type]


def main() -> None:
    """Inicia o consumidor Redis Pub/Sub e escuta por mensagens."""
    logger.info("Redis pubsub starting")
    bus = bootstrap.bootstrap()
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("change_batch_quantity")

    for m in pubsub.listen():
        handle_change_batch_quantity(m, bus)


def handle_change_batch_quantity(m: dict[str, object], bus: MessageBus) -> None:
    """Processa uma mensagem de alteração de quantidade de lote.

    Args:
        m: Mensagem recebida do Redis.
        bus: Barramento de mensagens para processar o comando.
    """
    logger.info("handling %s", m)
    data = json.loads(m["data"])  # type: ignore[arg-type]
    cmd = commands.ChangeBatchQuantity(ref=data["batchref"], qty=data["qty"])
    bus.handle(cmd)


if __name__ == "__main__":
    main()
