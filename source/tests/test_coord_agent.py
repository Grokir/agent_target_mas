import pytest

from source.coord_agent.agent import Coord_Agent
from coord_agent.config import CODE_AGENT_ID, DB_AGENT_ID

pytestmark = pytest.mark.llm


@pytest.fixture
def agent():
    return Coord_Agent()


@pytest.mark.parametrize("prompt", [
    "Привет!",
    "Напиши скрипт на python, который выводит 'Hello, world!'",
], ids=["greeting", "code_task"])
async def test_base_work(agent, prompt):
    result = await agent.handle_message(prompt)
    print(result)

    assert result["status"] in ("clarify", "ready")

    if result["status"] == "ready":
        assert result["target_agent"] in (CODE_AGENT_ID, DB_AGENT_ID)
