"""
Драфт Агента-Координатора.

ТЗ:
  1) Получает промпт от пользователя, при необходимости уточняет детали.
  2) На основе задачи выбирает подрядчика: Агент-Кодер или БД-Агент.
  3) Приводит задачу к конструктивному ТЗ для передачи более простой
     (менее сообразительной) модели-исполнителю.

Код и структура (kernel_init/send_prompt, приватные __core, async send_message)
взяты из source/coord_agent/agent.py.
"""

import asyncio
import re
from json import loads as json_loads, JSONDecodeError
from typing import Optional

from agent_kernel.base_agent import kernel_init, send_prompt, memory_clear, DEFAULT_THREAD_ID
from coord_agent.config import MODEL_NAME, SYSPROMPT, CODE_AGENT_ID, DB_AGENT_ID


def _extract_json(content: str) -> Optional[dict]:
    """Достаёт JSON-объект из ответа модели (сперва пробуем чистый ответ, затем ищем объект внутри текста)."""
    content = content.strip()
    try:
        return json_loads(content)
    except JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    try:
        return json_loads(match.group())
    except JSONDecodeError:
        return None


class Coord_Agent:
    def __init__(self):
        self.__core = kernel_init(
            model_name=MODEL_NAME,
            tools=[],
            sysprompt=SYSPROMPT,
            temp=0.0,
        )

    async def handle_message(self, message: str, thread_id: str = DEFAULT_THREAD_ID) -> dict:
        """
        Возвращает один из вариантов:
          {"status": "clarify", "question": str}
          {"status": "ready", "target_agent": str, "task_spec": str}
          {"status": "error", "raw": str}  -- модель не вернула валидный JSON
        """
        response = await send_prompt(self.__core, message, thread_id=thread_id)
        content = response["messages"][-1].content

        decision = _extract_json(content)
        if decision is None or "status" not in decision:
            return {"status": "error", "raw": content}
        return decision

    def clear_memory(self):
        memory_clear(self.__core)


async def _demo():
    agent = Coord_Agent()
    print("Драфт координатора. 'exit' для выхода.\n")

    while True:
        user_input = input("Пользователь: ").strip()
        if user_input.lower() in ("exit", "quit", "выход"):
            break
        if not user_input:
            continue

        result = await agent.handle_message(user_input)

        if result["status"] == "clarify":
            print(f"[Координатор уточняет]: {result['question']}\n")
        elif result["status"] == "ready":
            print(f"[Координатор -> {result['target_agent']}]:")
            print(result["task_spec"], "\n")
        else:
            print(f"[Координатор вернул не-JSON ответ]: {result['raw']}\n")



