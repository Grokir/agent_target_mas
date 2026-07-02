from langchain_core.tools import tool

from agent_kernel.base_agent import kernel_init, send_prompt, memory_clear
from db_agent.config import MODEL_NAME, SYSPROMPT, PATH_DB_DIR
from csv import DictReader, DictWriter
from os.path import abspath

# Внутренний класс для работы с CSV, чтобы не дублировать код в инструментах
def get_abs_path(table_name:str) -> str:
    return f"{abspath(PATH_DB_DIR)}/{table_name}"

def get_csv_fields(table_name: str) -> list[str]:
    with open(get_abs_path(table_name), mode="r", encoding="utf-8") as file:
        reader = DictReader(file)
        return reader.fieldnames

def read_csv(table_name: str) -> list[dict]:
    with open(get_abs_path(table_name), mode="r", encoding="utf-8") as file:
        reader = DictReader(file)
        res_list = []
        for row in reader:
            res_list.append(row)
        return res_list

def write_csv(table_name: str, new_data: list[dict]):
    with open(get_abs_path(table_name), mode="a", encoding="utf-8", newline="") as file:
        writer = DictWriter(file, fieldnames=get_csv_fields(table_name))
        writer.writerows(new_data)


class DB_Agent:
    def __init__(self):
        self.__tools = [
            # Методы для работы с БД сотрудников
            self.__select_from_employees,
            self.__insert_into_employees,
            self.__update_employees,
            self.__delete_from_employees,

            # Методы для работы с БД клиентов
            self.__select_from_clients,
            self.__insert_into_clients,
            self.__update_clients,
            self.__delete_from_clients,
        ]
        self.__core = kernel_init(
            model_name=MODEL_NAME, 
            tools=self.__tools, 
            sysprompt=SYSPROMPT
        )
    
    #================================
    
    @staticmethod
    @tool
    def __select_from_employees():    pass
    @staticmethod
    @tool
    def __insert_into_employees():    pass
    @staticmethod
    @tool
    def __update_employees():         pass
    @staticmethod
    @tool
    def __delete_from_employees():    pass

    #================================
    
    @staticmethod
    @tool
    def __select_from_clients():      pass
    @staticmethod
    @tool
    def __insert_into_clients():      pass
    @staticmethod
    @tool
    def __update_clients():           pass
    @staticmethod
    @tool
    def __delete_from_clients():      pass
    