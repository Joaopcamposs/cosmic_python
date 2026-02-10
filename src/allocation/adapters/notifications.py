"""Adaptadores de notificação (e-mail) para o serviço de alocação."""

import abc
import smtplib

from allocation import config


class AbstractNotifications(abc.ABC):
    """Interface abstrata para envio de notificações."""

    @abc.abstractmethod
    def send(self, destination: str, message: str) -> None:
        """Envia uma notificação ao destinatário."""
        raise NotImplementedError


DEFAULT_HOST: str = config.get_email_host_and_port()["host"]
DEFAULT_PORT: int = config.get_email_host_and_port()["port"]


class EmailNotifications(AbstractNotifications):
    """Implementação de notificações via SMTP."""

    def __init__(self, smtp_host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.server = smtplib.SMTP(smtp_host, port=port)
        self.server.noop()

    def send(self, destination: str, message: str) -> None:
        """Envia um e-mail de notificação."""
        msg = f"Subject: allocation service notification\n{message}"
        self.server.sendmail(
            from_addr="allocations@example.com",
            to_addrs=[destination],
            msg=msg,
        )
