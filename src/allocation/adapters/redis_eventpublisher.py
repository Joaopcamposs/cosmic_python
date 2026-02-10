"""Publicador de eventos via Redis Pub/Sub."""

import json
import logging
from dataclasses import asdict

import redis

from allocation import config
from allocation.domain import events

logger = logging.getLogger(__name__)

r: redis.Redis = redis.Redis(**config.get_redis_host_and_port())  # type: ignore[arg-type]


def publish(channel: str, event: events.Event) -> None:
    """Publica um evento no canal Redis especificado.

    Args:
        channel: Nome do canal Redis.
        event: Evento de domínio a ser publicado.
    """
    logging.info("publishing: channel=%s, event=%s", channel, event)
    r.publish(channel, json.dumps(asdict(event)))
