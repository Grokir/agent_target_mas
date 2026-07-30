import pytest

from db_agent.agent import DB_Agent, CSVManager
from db_agent.config import EMPLOYEES_TB, CLIENTS_TB

pytestmark = pytest.mark.llm

EMPLOYEE_PROMPTS = [
    "Выведи первые 4 строки из таблицы сотрудников",
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


def _client_prompts(client_id: int) -> list[str]:
    """Промпты для теста клиентов. update/delete нацелены на ID, который
    вставит сам тест, а не на захардкоженные номера чужих записей."""
    return [
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
        f"Нужно обновить данные для клиента с ID {client_id}: изменить менеджера (Account_manager) на Евгению Фокину.",
        f"Удали клиента с ID {client_id}.",
    ]


@pytest.fixture
def agent():
    return DB_Agent()


async def test_employees_base_work(agent):
    # Промпты выполняются последовательно одним агентом: сотрудник добавляется
    # и удаляется в рамках этого же теста (self-contained round trip).
    for prompt in EMPLOYEE_PROMPTS:
        response = await agent.send_message(prompt)
        content = response["messages"][-1].content
        print(content)

        assert content

    # Проверяем реальное состояние файла, а не пересказ модели: удаление
    # могло "текстово" отрапортовать успех, ничего не удалив на самом деле.
    remaining = CSVManager.read_csv(EMPLOYEES_TB)
    assert not any(row["Login"] == "roma_228" for row in remaining)


async def test_clients_base_work(agent):
    # ID нового клиента назначается автоинкрементом внутри insert_into_clients,
    # поэтому вычисляем его так же (get_next_id) и используем этот же ID для
    # update/delete — тест создаёт и убирает за собой только свои данные,
    # не трогая и не завися от существующих записей в clients.csv.
    new_client_id = CSVManager.get_next_id(CSVManager.read_csv(CLIENTS_TB))

    for prompt in _client_prompts(new_client_id):
        response = await agent.send_message(prompt)
        content = response["messages"][-1].content
        print(content)

        assert content

    remaining = CSVManager.read_csv(CLIENTS_TB)
    assert not any(int(row["ID"]) == new_client_id for row in remaining)
