import db_agent
from db_agent.agent import DB_Agent
from langchain_core.tools import tool


async def test_base_work() -> tuple[str, bool, str]:
    test_name = "Тест базовых функций БД агента"
    test_res_flag = True
    test_res_comment = ""

    queue_prompts_employee = [
        "выведи 5 записей из таблицы employee"
    ]
    queue_prompts_clients = [
        "выведи 5 записей из таблицы clients"
    ]

    agent = DB_Agent()
    try:
        print("\t\t[employee]")
        for p in queue_prompts_employee:
            print((await agent.send_message(p))["messages"][-1])
    except Exception as e:
        test_res_flag = False
        test_res_comment += ' ' + str(e)

    
    try:
        print("\t\t[clients]")
        for p in queue_prompts_clients:
            print((await agent.send_message(p))["messages"][-1])
    except Exception as e:
        test_res_flag = False
        test_res_comment += ' ' + str(e)
    
    return (test_name, test_res_flag, test_res_comment)