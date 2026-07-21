import asyncio

class MessageBroker:
    """Имитация шины сообщений (Message Bus) для обмена ACL-сообщениями."""
    def __init__(self):
        self.queues: dict[str, asyncio.Queue] = {}

    def register_agent(self, agent_id: str):
        self.queues[agent_id] = asyncio.Queue()

    async def send_message(self, receiver_id: str, message: dict[str, any]):
        if receiver_id not in self.queues:
            raise ValueError(f"Агент '{receiver_id}' не найден в сети")
        await self.queues[receiver_id].put(message)

    async def receive_message(self, agent_id: str) -> dict[str, any]:
        return await self.queues[agent_id].get()