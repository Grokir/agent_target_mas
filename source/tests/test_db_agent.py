import db_agent
from db_agent.agent import DB_Agent
from langchain_core.tools import tool


async def test_base_work() -> tuple[str, bool, str]:
    test_name = "Тест базовых функций БД агента"
    test_res_flag = True
    test_res_comment = ""

    queue_prompts_employee = [
        # "Выведи 5 записей из файла employees.csv используя инструмент _select_from_employees"
        # "Выведи 5 записей из файла employees.csv"
        # "Выведи первые 3 записи"
        # "Выведи первые 4 записи сотрудников",
        # "Сначала ОБЯЗАТЕЛЬНО выведи данные, которые ты будешь вставлять в таблицу. Добавь нового сотрудника Романа Толстого, который родился 2005-05-05. Его должность: Проектный менеджер в отделе IT. А заработная плата равна 30_000. Логином будет: roma_228, а паролем: 822_omar."
        # """Для нового сотрудника Романа Толстого, который родился 2005-05-05. Его должность: Проектный менеджер в отделе IT. А заработная плата равна 30_000. Логином будет: roma_228, а паролем: 822_omar. Составь данные для вставки, НО НЕ ВСТАВЛЯЙ ИХ, А ВЫВЕДИ НА ЭКРАН."""
        """Нужно добавить нового сотрудника:
        Login: roma_228,
        Пароль: 822_omar,
        Имя: Роман,
        Фамилия: Толстой,
        Дата рождения: 200505-05,
        Должность: Project Manager,
        Отдел: IT-dep,
        Заработная плата: 30_000"""
    ]
    queue_prompts_clients = [
        # "Выведи 5 записей из файла clients.csv используя инструмент _select_from_clients"
        # "Выведи 5 записей из файла clients.csv"
        # "Выведи первые 4 записи клиентов"
    ]
    try:
        agent = DB_Agent()
    except Exception as e:
        test_res_flag = False
        test_res_comment += ' ' + str(e)

    try:
        print("\t\t[employee]")
        for p in queue_prompts_employee:
            # await agent.send_message(p)
            # print((await agent.send_message(p))["messages"][-1].content)
            print((await agent.send_message(p)))
    except Exception as e:
        test_res_flag = False
        test_res_comment += ' ' + str(e)

    
    try:
        print("\t\t[clients]")
        for p in queue_prompts_clients:
            # await agent.send_message(p)
            print((await agent.send_message(p))["messages"][-1].content)
    except Exception as e:
        test_res_flag = False
        test_res_comment += ' ' + str(e)
    
    return (test_name, test_res_flag, test_res_comment)