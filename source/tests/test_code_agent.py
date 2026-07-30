import os
import pytest

from code_agent.agent import Code_Agent

pytestmark = pytest.mark.llm

TEST_FILE = "test.txt"


@pytest.fixture
def agent():
    yield Code_Agent()
    # Один из промптов ниже пишет test.txt в текущую директорию — убираем
    # за собой, иначе файл остаётся в репозитории после каждого прогона.
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)


@pytest.mark.parametrize("prompt", [
    """Запусти локально код:
            with open('test.txt', 'w') as f:
                f.write('Grokir was here! >:D')
        """,
    """Запусти изолированно код: print('Grokir was here! >:D')""",
    """Напиши web сервер на python, который бы позволял загружать на него файлы для локального хранения.""",
], ids=["run_local", "run_docker", "generate_web_server"])
async def test_base_work(agent, prompt):
    response = await agent.send_message(prompt)
    content = response["messages"][-1].content

    assert content
