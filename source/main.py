
# Отключение предупреждений от Pydantic об версии Python
import warnings

# Задаем жесткое "глушение" для всего
warnings.filterwarnings("ignore")
# "Ломаем" функции, которыми langchain пытается сбросить или изменить фильтры
warnings.resetwarnings = lambda: None
warnings.filterwarnings = lambda *args, **kwargs: None


import asyncio
from uuid import uuid4

from agent_kernel.base_agent import DEFAULT_THREAD_ID
from agent_kernel.mesbroker import ACLMessage, MessageBroker, InProcessBroker, Performative
from coord_agent.agent import Coord_Agent
from coord_agent.config import CODE_AGENT_ID, DB_AGENT_ID, COORD_AGENT_ID
from code_agent.agent import Code_Agent
from db_agent.agent import DB_Agent


_AGENTS = None
_CONSUMER_TASKS: list[asyncio.Task] = []


def get_agents():
    """Поднимает координатора, исполнителей и брокер сообщений между ними
    один раз (ленивый синглтон) - используется и CLI-циклом ниже, и
    agent_repeater_server (через handle_chat_request), чтобы не плодить
    отдельные наборы агентов."""
    global _AGENTS
    if _AGENTS is None:
        broker = InProcessBroker()
        coord = Coord_Agent()
        executors = {
            CODE_AGENT_ID: (Code_Agent(), run_code_agent),
            DB_AGENT_ID: (DB_Agent(), run_db_agent),
        }

        broker.register(COORD_AGENT_ID)
        for agent_id, (executor, runner) in executors.items():
            broker.register(agent_id)
            _CONSUMER_TASKS.append(
                asyncio.create_task(_run_executor_loop(broker, agent_id, executor, runner))
            )

        _AGENTS = (coord, executors, broker)
    return _AGENTS


async def _run_executor_loop(broker: MessageBroker, agent_id: str, executor, runner) -> None:
    """Фоновый цикл агента-исполнителя: слушает свой адрес в брокере,
    прогоняет задачу через ядро и публикует ответ по reply_to заказчика.
    Ошибку исполнения заворачиваем в FAILURE, а не даём таске упасть -
    иначе агент молча перестанет отвечать на все следующие запросы."""
    while True:
        request = await broker.receive(agent_id)
        try:
            content = await runner(executor, request.content, thread_id=request.conversation_id)
            performative = Performative.INFORM
        except Exception as exc:
            content = str(exc)
            performative = Performative.FAILURE

        await broker.publish(ACLMessage(
            sender=agent_id,
            receiver=request.reply_to,
            performative=performative,
            content=content,
            conversation_id=request.conversation_id,
        ))


async def _ask(broker: MessageBroker, sender: str, target_agent: str, content: str, conversation_id: str) -> ACLMessage:
    """Публикует запрос конкретному агенту и дожидается его ответа. Для
    каждого запроса заводится одноразовый адрес reply_to, чтобы ответы
    параллельных диалогов не путались друг с другом в общей шине."""
    reply_to = f"{sender}:{uuid4().hex}"
    broker.register(reply_to)
    try:
        await broker.publish(ACLMessage(
            sender=sender,
            receiver=target_agent,
            performative=Performative.REQUEST,
            content=content,
            conversation_id=conversation_id,
            reply_to=reply_to,
        ))
        return await broker.receive(reply_to)
    finally:
        broker.unregister(reply_to)


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
    готово) исполнитель через брокер сообщений. session_id пробрасывается
    как conversation_id/thread_id, чтобы разные HTTP-сессии не путали друг
    другу ни память разговора, ни ответы в общей шине."""
    coord, executors, broker = get_agents()

    decision = await run_coord_agent(coord, message, thread_id=session_id)

    if decision["status"] in ("clarify", "error"):
        return decision

    target_agent = decision["target_agent"]
    task_spec = decision["task_spec"]

    if target_agent not in executors:
        return {"status": "error", "raw": f"Неизвестный подрядчик '{target_agent}'"}

    reply = await _ask(broker, COORD_AGENT_ID, target_agent, task_spec, session_id)
    if reply.performative == Performative.FAILURE:
        return {"status": "error", "raw": reply.content}
    return {"status": "ready", "target_agent": target_agent, "reply": reply.content}


async def run_agents():
    coord, executors, broker = get_agents()

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

        if target_agent not in executors:
            print(f"[Ошибка]: неизвестный подрядчик '{target_agent}'\n")
            continue

        reply = await _ask(broker, COORD_AGENT_ID, target_agent, task_spec, DEFAULT_THREAD_ID)
        if reply.performative == Performative.FAILURE:
            print(f"[Ошибка от {target_agent}]: {reply.content}\n")
            continue
        print(f"[{target_agent}]: {reply.content}\n")


def main():
    asyncio.run(run_agents())


if __name__ == "__main__":
    main()
