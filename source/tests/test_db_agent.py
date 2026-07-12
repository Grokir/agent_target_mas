import db_agent
from db_agent.agent import DB_Agent
from langchain_core.tools import tool


async def test_base_work() -> tuple[str, bool, str]:
    test_name = "Тест базовых функций БД агента"
    test_res_flag = True
    test_res_comment = ""

    queue_prompts_employee = [
        "Выведи первые 4 записи сотрудников",
        """Нужно добавить нового сотрудника:
        Login: roma_228,
        Пароль: 822_omar,
        Имя: Роман,
        Фамилия: Толстой,
        Дата рождения: 200505-05,
        Должность: Project Manager,
        Отдел: IT-dep,
        Заработная плата: 30_000""",
        "Удали сотрудника с логином roma_228",
        "У сотрудника с логином natalia_s нужно изменить фамилию на Проскурина, оставив все остальны поля без изменения."

    ]
    queue_prompts_clients = [
        "Выведи первые 4 записи клиентов",
        """Нужно добавить нового клиента:
        company_name: Рога&Копыта,
        contact_person: Сахатый Л.О.,
        email: sahatyi@example.mail,
        phone: +5(555)777-888-999,
        industry: Consulting,
        contract_start: 2030-03-30,
        status: Planning,
        account_manager: Волков А.А.""",
        "Удали клиента с ID 13.",
        "Нужно обновить данные для клиента с ID 12: изменить менеджера (Account_manager) на Евгению Фокину."
    ]
    try:
        agent = DB_Agent()
    except Exception as e:
        test_res_flag = False
        test_res_comment += ' ' + str(e)

    try:
        # print("\t\t[employee]")
        for p in queue_prompts_employee:
            await agent.send_message(p)
            # print((await agent.send_message(p))["messages"][-1].content)
            # print((await agent.send_message(p)))
            # print()

    except Exception as e:
        test_res_flag = False
        test_res_comment += ' ' + str(e)

    
    try:
        # print("\t\t[clients]")
        for p in queue_prompts_clients:
            await agent.send_message(p)
            # print((await agent.send_message(p))["messages"][-1].content)
            # print((await agent.send_message(p)))
            # print()
    except Exception as e:
        test_res_flag = False
        test_res_comment += ' ' + str(e)
    
    return (test_name, test_res_flag, test_res_comment)