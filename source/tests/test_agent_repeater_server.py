import pytest
from fastapi.testclient import TestClient

from agent_repeater_server import app
from coord_agent.config import CODE_AGENT_ID, DB_AGENT_ID

pytestmark = pytest.mark.llm


@pytest.fixture
def client():
    # Агенты поднимаются лениво внутри main.get_agents() при первом /chat -
    # общий синглтон с CLI-циклом из main.py, отдельного lifespan тут нет.
    with TestClient(app) as c:
        yield c


def test_chat_greeting_returns_well_formed_response(client):
    response = client.post("/chat", json={
        "session_id": "test-greeting",
        "message": "Привет!",
    })
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ("clarify", "ready", "error")
    assert data["reply"]


def test_chat_code_task_routes_to_code_agent(client):
    response = client.post("/chat", json={
        "session_id": "test-code-task",
        "message": "Напиши и запусти локально код, который выводит 'Hello, world!'",
    })
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ready"
    assert data["target_agent"] == CODE_AGENT_ID
    assert data["reply"]


def test_chat_db_task_routes_to_db_agent(client):
    response = client.post("/chat", json={
        "session_id": "test-db-task",
        "message": "Выведи первые 3 записи из таблицы сотрудников",
    })
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ready"
    assert data["target_agent"] == DB_AGENT_ID
    assert data["reply"]


def test_chat_missing_fields_returns_422(client):
    response = client.post("/chat", json={"message": "нет session_id"})
    assert response.status_code == 422
