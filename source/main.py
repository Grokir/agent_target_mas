
# Отключение предупреждений от Pydantic об версии Python
import warnings

# Задаем жесткое "глушение" для всего
warnings.filterwarnings("ignore")
# "Ломаем" функции, которыми langchain пытается сбросить или изменить фильтры
warnings.resetwarnings = lambda: None
warnings.filterwarnings = lambda *args, **kwargs: None


import asyncio

import agent_repeater_server

from coord_agent.draft_coord import DraftCoordAgent
from coord_agent.config import CODE_AGENT_ID, DB_AGENT_ID
from code_agent.agent import Code_Agent
from db_agent.agent import DB_Agent


LHOST = "localhost"
LPORT = 5000


async def run_coord_agent(agent: DraftCoordAgent, prompt: str) -> dict:
    """Прогоняет реплику пользователя через координатора."""
    return await agent.handle_message(prompt)


async def run_code_agent(agent: Code_Agent, task_spec: str) -> str:
    """Отдаёт готовое ТЗ Агенту-Кодеру и возвращает его финальный ответ."""
    response = await agent.send_message(task_spec)
    return response["messages"][-1].content


async def run_db_agent(agent: DB_Agent, task_spec: str) -> str:
    """Отдаёт готовое ТЗ БД-Агенту и возвращает его финальный ответ."""
    response = await agent.send_message(task_spec)
    return response["messages"][-1].content


async def run_agents():
    coord = DraftCoordAgent()
    executors = {
        CODE_AGENT_ID: (Code_Agent(), run_code_agent),
        DB_AGENT_ID: (DB_Agent(), run_db_agent),
    }

    print("MAS запущена. 'exit' для выхода.\n")
    while True:
        user_input = input("Пользователь: ").strip()
        if user_input.lower() in ("exit", "quit", "выход"):
            break
        if not user_input:
            continue

        decision = await run_coord_agent(coord, user_input)

        if decision["status"] == "clarify":
            print(f"[Координатор]: {decision['question']}\n")
            continue

        if decision["status"] == "error":
            print(f"[Координатор вернул текст без JSON]: {decision['raw']}\n")
            continue

        target_agent = decision["target_agent"]
        task_spec = decision["task_spec"]
        print(f"[Координатор -> {target_agent}]: {task_spec}\n")

        executor, runner = executors.get(target_agent, (None, None))
        if executor is None:
            print(f"[Ошибка]: неизвестный подрядчик '{target_agent}'\n")
            continue

        result = await runner(executor, task_spec)
        print(f"[{target_agent}]: {result}\n")


def main():
    # запускаем репитер
    # agent_repeater_server.run(LHOST, LPORT)
    asyncio.run(run_agents())


if __name__ == "__main__":
    main()