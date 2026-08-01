
# Отключение предупреждений от Pydantic об версии Python
import warnings

# Задаем жесткое "глушение" для всего
warnings.filterwarnings("ignore")
# "Ломаем" функции, которыми langchain пытается сбросить или изменить фильтры
warnings.resetwarnings = lambda: None
warnings.filterwarnings = lambda *args, **kwargs: None


import asyncio

from coord_agent.agent import Coord_Agent
from coord_agent.config import CODE_AGENT_ID, DB_AGENT_ID
from code_agent.agent import Code_Agent
from db_agent.agent import DB_Agent


_AGENTS = None


def get_agents():
    """Поднимает координатора и исполнителей один раз (ленивый синглтон) -
    используется и CLI-циклом ниже, и agent_repeater_server (через
    handle_chat_request), чтобы не плодить отдельные наборы агентов."""
    global _AGENTS
    if _AGENTS is None:
        coord = Coord_Agent()
        executors = {
            CODE_AGENT_ID: (Code_Agent(), run_code_agent),
            DB_AGENT_ID: (DB_Agent(), run_db_agent),
        }
        _AGENTS = (coord, executors)
    return _AGENTS


async def run_coord_agent(agent: Coord_Agent, prompt: str, thread_id: str = None) -> dict:
    """Прогоняет реплику пользователя через координатора."""
    kwargs = {"thread_id": thread_id} if thread_id else {}
    return await agent.handle_message(prompt, **kwargs)


async def run_code_agent(agent: Code_Agent, task_spec: str, thread_id: str = None) -> str:
    """Отдаёт готовое ТЗ Агенту-Кодеру и возвращает его финальный ответ."""
    kwargs = {"thread_id": thread_id} if thread_id else {}
    response = await agent.send_message(task_spec, **kwargs)
    return response["messages"][-1].content


async def run_db_agent(agent: DB_Agent, task_spec: str, thread_id: str = None) -> str:
    """Отдаёт готовое ТЗ БД-Агенту и возвращает его финальный ответ."""
    kwargs = {"thread_id": thread_id} if thread_id else {}
    response = await agent.send_message(task_spec, **kwargs)
    return response["messages"][-1].content


async def handle_chat_request(session_id: str, message: str) -> dict:
    """Один шаг диалога для agent_repeater_server: координатор -> (если
    готово) исполнитель. session_id пробрасывается как thread_id, чтобы
    разные HTTP-сессии не путали друг другу память разговора."""
    coord, executors = get_agents()

    decision = await run_coord_agent(coord, message, thread_id=session_id)

    if decision["status"] in ("clarify", "error"):
        return decision

    target_agent = decision["target_agent"]
    task_spec = decision["task_spec"]

    executor, runner = executors.get(target_agent, (None, None))
    if executor is None:
        return {"status": "error", "raw": f"Неизвестный подрядчик '{target_agent}'"}

    reply = await runner(executor, task_spec, thread_id=session_id)
    return {"status": "ready", "target_agent": target_agent, "reply": reply}


async def run_agents():
    coord, executors = get_agents()

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
    asyncio.run(run_agents())


if __name__ == "__main__":
    main()