"""Cliente Redis para testes e2e de eventos."""

import json

import redis

from allocation import config

r: redis.Redis = redis.Redis(**config.get_redis_host_and_port())  # type: ignore[arg-type]


def subscribe_to(channel: str) -> redis.client.PubSub:
    """Inscreve-se em um canal Redis e aguarda confirmação."""
    pubsub = r.pubsub()
    pubsub.subscribe(channel)
    confirmation = pubsub.get_message(timeout=3)
    assert confirmation["type"] == "subscribe"
    return pubsub


def publish_message(channel: str, message: dict[str, object]) -> None:
    """Publica uma mensagem em um canal Redis."""
    r.publish(channel, json.dumps(message))
