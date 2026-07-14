from langchain_core.tools       import tool, StructuredTool
from langchain_openai           import ChatOpenAI

from agent_kernel.base_agent    import kernel_init, send_prompt, memory_clear
from db_agent.config            import MODEL_NAME, SYSPROMPT

from typing                     import Optional
from json                       import dumps as json_dumps, loads as json_loads, JSONDecodeError

from docker.errors              import ContainerError, ImageNotFound
import docker
import re
import sys
import subprocess


def parse_tool_calls_from_content(content: str) -> list:
    """Извлекает tool calls из content модели"""
    try:
        # Ищем JSON в content
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json_loads(json_match.group())
            if 'tool' in data and 'arguments' in data:
                return [{
                    'name': data['tool'],
                    'args': data['arguments'],
                    'id': f"call_{data['tool']}"
                }]
    except (JSONDecodeError, KeyError):
        pass
    return []


def init_generation_llm(model_name:str):
    """Инициализация LLM для генерации новых атак (можно переиспользовать ту же модель)."""
    global LLM_FOR_GENERATION
    if LLM_FOR_GENERATION is None:
        LLM_FOR_GENERATION = ChatOpenAI(
            # model="mistral-nemo-instruct-2407",  # или ваша модель
            # base_url="http://localhost:1234/v1",

            model=model_name,  # или ваша модель
            base_url=base_url,
            api_key="not-needed",
            temperature=0.9
        )
    return LLM_FOR_GENERATION


class Code_Agent:
    # @staticmethod
    def __init__(self):
        self.__tools = [

        ]

        self.__core = kernel_init(
            model_name=MODEL_NAME, 
            tools=self.__tools, 
            sysprompt=SYSPROMPT,
            temp=0.0
        )

    # async def send_message(self, message:str):
    #     """Возвращает текстовый ответ от ядра"""
    #     return await send_prompt(self.__core, message)
        
    async def send_message(self, message: str):
        response = await send_prompt(self.__core, message)
        
        # Проверяем, есть ли tool calls в content
        if hasattr(response, 'content') and response.content:
            tool_calls = parse_tool_calls_from_content(response.content)
            
            if tool_calls:
                # Обрабатываем tool calls вручную
                for tool_call in tool_calls:
                    # Находим нужный инструмент
                    tool = next((t for t in self.__tools if t.name == tool_call['name']), None)
                    if tool:
                        # Выполняем инструмент
                        result = await tool.ainvoke(tool_call['args'])
                        # Возвращаем результат
                        return result
        return response
        
    #================================


    @staticmethod
    @tool
    def run_python_code(code_string: str, timeout: int = 5) -> dict:
        """
        Локальнаый запуск python кода
            # Пример использования:
            code = \"""
            def greet(name):
                print(f"Hello, {name}!")

            greet("World")
            \"""
            print(run_python_code(code))
        """
        try:
            # Запуск кода через подпроцесс safe-mode
            result = subprocess.run(
                [sys.executable, "-c", code_string],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Error: Code execution timed out.",
                "exit_code": -1
            }
        
    
    @staticmethod
    @tool
    def run_code_in_docker(code_string: str, timeout_sec: int = 5, mem_limit: str = "128m") -> dict:
        """Изолированный запуск python кода
            code_string - код на языке Python, который будет запускаться в изолированной среде
            timeout_sec - время ожидания выполнения кода
            mem_limit   - ограничение на использование оперативной памяти
        """
        client = docker.from_env()
        
        # Оборачиваем код, чтобы передать его через аргумент командной строки
        # (Альтернатива: монтировать временный файл, но так быстрее)
        cmd = f"python -c {repr(code_string)}"
        
        try:
            # Запуск легковесного контейнера Alpine Python
            container = client.containers.run(
                image="python:3.11-alpine",
                command=["python", "-c", code_string],
                detach=True,
                mem_limit=mem_limit,       # Ограничение памяти
                nano_cpus=1000000000,      # Ограничение CPU (1 ядро)
                network_mode="none"        # Полное отключение интернета для безопасности
            )
            
            # Ждем завершения с таймаутом
            result = container.wait(timeout=timeout_sec)
            logs = container.logs(stdout=True, stderr=True).decode("utf-8")
            container.remove()             # Удаляем контейнер после работы
            
            return {
                "success": result["StatusCode"] == 0,
                "stdout": logs if result["StatusCode"] == 0 else "",
                "stderr": logs if result["StatusCode"] != 0 else "",
                "exit_code": result["StatusCode"]
            }
            
        except ContainerError as e:
            # Если контейнер завершился с ошибкой (не 0)
            return {
                "success": False,
                "stdout": e.stdout.decode("utf-8"),
                "stderr": e.stderr.decode("utf-8"),
                "exit_code": e.exit_status
            }
        except Exception as e:
            # Сюда попадет и таймаут, и системные ошибки
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "exit_code": -1
            }

    @staticmethod
    @tool
    def generate_python_code(tech_task:str) -> str:
        """
        Генерирует python код на основе технического задания.
        """

        llm = kernel_init(
            model_name=MODEL_NAME, 
            tools=[], 
            sysprompt=SYSPROMPT,
            temp=0.9
        )
        system = "Ты — инструмент для генерации python кода на основе полученного технического задания."
        user = f"Техническое задание: {tech_task}."
        response = llm.invoke([("system", system), ("human", user)])
        return response.content

