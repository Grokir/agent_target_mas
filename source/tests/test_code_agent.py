from code_agent.agent import Code_Agent
from langchain_core.tools import tool


async def test_base_work() -> tuple[str, bool, str]:
    test_name = "Тест базовых функций БД агента"
    test_res_flag = True
    test_res_comment = ""

    queue_prompts = [
        """Запусти локально код:
            with open('test.txt', 'w') as f:
                f.write('Grokir was here! >:D')
        """,
        """Запусти изолированно код: print('Grokir was here! >:D')""",
        """Напиши web сервер на python, который бы позволял загружать на него файлы для локального хранения.""",
    ]
    try:
        agent = Code_Agent()
    except Exception as e:
        test_res_flag = False
        test_res_comment += ' ' + str(e)

    try:
        for p in queue_prompts:
            # await agent.send_message(p)
            print((await agent.send_message(p))["messages"][-1].content)
            # print((await agent.send_message(p)))
            # print()

    except Exception as e:
        test_res_flag = False
        test_res_comment += ' ' + str(e)

    return (test_name, test_res_flag, test_res_comment)