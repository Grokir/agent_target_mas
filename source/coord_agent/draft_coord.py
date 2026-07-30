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

from agent_kernel.base_agent import kernel_init, send_prompt, memory_clear
from coord_agent.config import MODEL_NAME, CODE_AGENT_ID, DB_AGENT_ID


DRAFT_SYSPROMPT = f"""Ты — Технический Координатор в мультиагентной системе разработки.
Ты ведёшь диалог с пользователем и должен передать итоговую задачу ровно ОДНОМУ подрядчику:
- "{CODE_AGENT_ID}" — пишет и исполняет python-код
- "{DB_AGENT_ID}" — работает с базой данных (сотрудники, клиенты)

ПРАВИЛА РАБОТЫ:
1. Если запрос пользователя недостаточно ясен для выбора подрядчика или постановки задачи —
   задай 1-3 уточняющих вопроса. Не додумывай детали сам.
2. Если информации достаточно — выбери подрядчика и составь для него конструктивное
   техническое задание. Учитывай, что исполнитель — модель попроще: ТЗ должно быть
   коротким, конкретным, без двусмысленностей, по шагам.
3. Никогда не пиши код и не выполняй операции с БД сам — только маршрутизация и постановка задачи.
4. Всегда учитывай контекст предыдущих сообщений диалога.

ФОРМАТ ОТВЕТА — строго один JSON-объект, без текста вне него. Даже на приветствие,
благодарность или любую реплику без явной задачи — отвечай JSON со status "clarify",
а не обычным текстом:
- Если нужны уточнения:
  {{"status": "clarify", "question": "<твои уточняющие вопросы одной строкой>"}}
- Если задача готова к передаче:
  {{"status": "ready", "target_agent": "{CODE_AGENT_ID}" | "{DB_AGENT_ID}", "task_spec": "<готовое ТЗ>"}}

ПРИМЕРЫ:
- Пользователь: "Привет!"
  Ответ: {{"status": "clarify", "question": "Здравствуйте! Какую задачу нужно решить: что-то на Python или работа с базой данных?"}}
- Пользователь: "Спасибо, все понятно"
  Ответ: {{"status": "clarify", "question": "Рад помочь! Если появится новая задача — опишите её."}}
- Пользователь: "Напиши скрипт, который выводит Hello world"
  Ответ: {{"status": "ready", "target_agent": "{CODE_AGENT_ID}", "task_spec": "Написать и выполнить python-скрипт, который печатает строку 'Hello, world!'."}}
"""


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


class DraftCoordAgent:
    def __init__(self):
        self.__core = kernel_init(
            model_name=MODEL_NAME,
            tools=[],
            sysprompt=DRAFT_SYSPROMPT,
            temp=0.0,
        )

    async def handle_message(self, message: str) -> dict:
        """
        Возвращает один из вариантов:
          {"status": "clarify", "question": str}
          {"status": "ready", "target_agent": str, "task_spec": str}
          {"status": "error", "raw": str}  -- модель не вернула валидный JSON
        """
        response = await send_prompt(self.__core, message)
        content = response["messages"][-1].content

        decision = _extract_json(content)
        if decision is None or "status" not in decision:
            return {"status": "error", "raw": content}
        return decision

    def clear_memory(self):
        memory_clear(self.__core)


async def _demo():
    agent = DraftCoordAgent()
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



