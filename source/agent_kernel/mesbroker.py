"""
Брокер сообщений между агентами MAS.

Задаёт единый протокол обмена (ACLMessage) и абстрактный интерфейс
MessageBroker, за которым может стоять любой транспорт - от очередей в
одном процессе (InProcessBroker) до внешней шины (Redis/RabbitMQ и т.п.),
если агентов понадобится развести по разным процессам или машинам.
Агенты и main.py работают только с интерфейсом MessageBroker и не знают,
какой транспорт стоит за ним.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any


class Performative(str, Enum):
    """Тип ACL-сообщения (подмножество FIPA ACL, достаточное для MAS)."""
    REQUEST = "request"    # постановка задачи исполнителю
    INFORM = "inform"      # успешный результат
    FAILURE = "failure"    # исполнитель не смог обработать запрос


@dataclass
class ACLMessage:
    sender: str
    receiver: str
    performative: Performative
    content: Any
    conversation_id: str
    reply_to: str = ""
    timestamp: float = field(default_factory=time)

    def __post_init__(self):
        # По умолчанию отвечать нужно отправителю - reply_to переопределяют
        # явно только для одноразовых адресов ответа (см. main._ask).
        if not self.reply_to:
            self.reply_to = self.sender


class UnknownRecipientError(KeyError):
    """Получатель или временный адрес не зарегистрирован в брокере."""


class MessageBroker(ABC):
    """Абстрактный интерфейс шины сообщений."""

    @abstractmethod
    def register(self, agent_id: str) -> None:
        """Заводит адрес получателя (агента или временного reply_to)."""

    @abstractmethod
    def unregister(self, agent_id: str) -> None:
        """Убирает адрес, когда он больше не нужен."""

    @abstractmethod
    async def publish(self, message: ACLMessage) -> None:
        """Кладёт сообщение в очередь получателя (message.receiver)."""

    @abstractmethod
    async def receive(self, agent_id: str) -> ACLMessage:
        """Забирает следующее сообщение, адресованное agent_id (блокирующе)."""


class InProcessBroker(MessageBroker):
    """Транспорт по умолчанию: одна asyncio.Queue на адрес в пределах
    одного процесса/event loop."""

    def __init__(self):
        self._queues: dict[str, "asyncio.Queue[ACLMessage]"] = {}

    def register(self, agent_id: str) -> None:
        self._queues.setdefault(agent_id, asyncio.Queue())

    def unregister(self, agent_id: str) -> None:
        self._queues.pop(agent_id, None)

    async def publish(self, message: ACLMessage) -> None:
        queue = self._queues.get(message.receiver)
        if queue is None:
            raise UnknownRecipientError(message.receiver)
        await queue.put(message)

    async def receive(self, agent_id: str) -> ACLMessage:
        queue = self._queues.get(agent_id)
        if queue is None:
            raise UnknownRecipientError(agent_id)
        return await queue.get()
