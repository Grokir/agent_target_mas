from langchain_core.tools import tool, StructuredTool

from agent_kernel.base_agent import kernel_init, send_prompt, memory_clear
from coord_agent.config import MODEL_NAME, SYSPROMPT
from coord_agent.config import CODE_AGENT_ID, DB_AGENT_ID

from csv import DictReader, DictWriter
from os.path import abspath
from typing import Optional
from json import dumps as json_dumps, loads as json_loads, JSONDecodeError
import re

def _parse_tool_calls_from_content(content: str) -> list:
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

class Coord_Agent:
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
            tool_calls = _parse_tool_calls_from_content(response.content)
            
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
    def some_tool(): pass
