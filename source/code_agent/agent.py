from langchain_core.tools import tool, StructuredTool

from agent_kernel.base_agent import kernel_init, send_prompt, memory_clear
from db_agent.config import MODEL_NAME, SYSPROMPT

from typing import Optional
from json import dumps as json_dumps, loads as json_loads, JSONDecodeError

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

