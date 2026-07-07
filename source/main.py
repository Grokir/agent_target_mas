
# Отключение предупреждений от Pydantic об версии Python
import warnings

# Задаем жесткое "глушение" для всего
warnings.filterwarnings("ignore")
# "Ломаем" функции, которыми langchain пытается сбросить или изменить фильтры
warnings.resetwarnings = lambda: None
warnings.filterwarnings = lambda *args, **kwargs: None


import agent_repeater_server
from tests.runner import run_tests


LHOST = "localhost"
LPORT = 5000


def main():
    # запускаем репитер
    # agent_repeater_server.run(LHOST, LPORT)
    run_tests()


if __name__ == "__main__":
    main()