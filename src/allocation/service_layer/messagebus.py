"""Barramento de mensagens para processamento de comandos e eventos."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from allocation.domain import commands, events

if TYPE_CHECKING:
    from . import unit_of_work

logger = logging.getLogger(__name__)

Message = commands.Command | events.Event


class MessageBus:
    """Barramento de mensagens que roteia comandos e eventos para seus handlers."""

    def __init__(
        self,
        uow: unit_of_work.AbstractUnitOfWork,
        event_handlers: dict[type[events.Event], list[Callable[..., None]]],
        command_handlers: dict[type[commands.Command], Callable[..., None]],
    ) -> None:
        self.uow = uow
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers

    def handle(self, message: Message) -> None:
        """Processa uma mensagem (comando ou evento) e seus efeitos colaterais.

        Args:
            message: Comando ou evento a ser processado.

        Raises:
            Exception: Se a mensagem não for um Command nem um Event.
        """
        self.queue: list[Message] = [message]
        while self.queue:
            message = self.queue.pop(0)
            if isinstance(message, events.Event):
                self.handle_event(message)
            elif isinstance(message, commands.Command):
                self.handle_command(message)
            else:
                raise Exception(f"{message} was not an Event or Command")

    def handle_event(self, event: events.Event) -> None:
        """Processa um evento executando todos os handlers registrados."""
        for handler in self.event_handlers[type(event)]:
            try:
                logger.debug("handling event %s with handler %s", event, handler)
                handler(event)
                self.queue.extend(self.uow.collect_new_events())
            except Exception:
                logger.exception("Exception handling event %s", event)
                continue

    def handle_command(self, command: commands.Command) -> None:
        """Processa um comando executando o handler registrado.

        Raises:
            Exception: Re-lança qualquer exceção do handler do comando.
        """
        logger.debug("handling command %s", command)
        try:
            handler = self.command_handlers[type(command)]
            handler(command)
            self.queue.extend(self.uow.collect_new_events())
        except Exception:
            logger.exception("Exception handling command %s", command)
            raise
