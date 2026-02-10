"""Bootstrap da aplicação: monta o barramento de mensagens com injeção de dependências."""

import inspect
from collections.abc import Callable

from allocation.adapters import orm, redis_eventpublisher
from allocation.adapters.notifications import (
    AbstractNotifications,
    EmailNotifications,
)
from allocation.service_layer import handlers, messagebus, unit_of_work


def bootstrap(
    start_orm: bool = True,
    uow: unit_of_work.AbstractUnitOfWork = unit_of_work.SqlAlchemyUnitOfWork(),
    notifications: AbstractNotifications | None = None,
    publish: Callable[..., None] = redis_eventpublisher.publish,
) -> messagebus.MessageBus:
    """Configura e retorna o barramento de mensagens com todas as dependências injetadas.

    Args:
        start_orm: Se True, inicializa os mappers do ORM.
        uow: Unit of Work a ser utilizado.
        notifications: Adaptador de notificações.
        publish: Função de publicação de eventos.

    Returns:
        Instância configurada do MessageBus.
    """
    if notifications is None:
        notifications = EmailNotifications()

    if start_orm:
        orm.start_mappers()

    dependencies: dict[str, object] = {
        "uow": uow,
        "notifications": notifications,
        "publish": publish,
    }
    injected_event_handlers = {
        event_type: [
            inject_dependencies(handler, dependencies) for handler in event_handlers
        ]
        for event_type, event_handlers in handlers.EVENT_HANDLERS.items()
    }
    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies)
        for command_type, handler in handlers.COMMAND_HANDLERS.items()
    }

    return messagebus.MessageBus(
        uow=uow,
        event_handlers=injected_event_handlers,
        command_handlers=injected_command_handlers,
    )


def inject_dependencies(
    handler: Callable[..., None], dependencies: dict[str, object]
) -> Callable[..., None]:
    """Injeta dependências em um handler baseado na assinatura da função.

    Args:
        handler: Função handler de comando ou evento.
        dependencies: Dicionário de dependências disponíveis.

    Returns:
        Função wrapper com dependências injetadas.
    """
    params = inspect.signature(handler).parameters
    deps = {
        name: dependency for name, dependency in dependencies.items() if name in params
    }
    return lambda message: handler(message, **deps)
