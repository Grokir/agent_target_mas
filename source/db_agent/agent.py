from langchain_core.tools import tool

from agent_kernel.base_agent import kernel_init, send_prompt, memory_clear
from db_agent.config import MODEL_NAME, SYSPROMPT
from db_agent.config import PATH_DB_DIR, EMPLOYEES_TB, CLIENTS_TB

from csv import DictReader, DictWriter
from os.path import abspath
from typing import Optional
from json import dumps as json_dumps, loads as json_loads, JSONDecodeError

# Внутренний класс для работы с CSV, чтобы не дублировать код в инструментах
def get_abs_path(table_name:str) -> str:
    """Возвращает полный путь до файла"""
    return f"{abspath(PATH_DB_DIR)}/{table_name}"

def get_csv_fields(table_name: str) -> list[str]:
    """Получает заголовок файла-таблицы БД"""
    with open(get_abs_path(table_name), mode="r", encoding="utf-8") as file:
        reader = DictReader(file)
        return reader.fieldnames

def sanitize_csv_field(value: str) -> str:
    """Защита от CSV-инъекций (Excel injection)."""
    if value and value[0] in ('=', '+', '-', '@'):
        return "'" + value
    return str(value)

#============================================

class CSVManager:
    @staticmethod
    def read_csv(table_name: str) -> list[dict]:
        with open(get_abs_path(table_name), mode="r", encoding="utf-8") as file:
            reader = DictReader(file)
            res_list = []
            for row in reader:
                res_list.append(row)
            return res_list
        
    @staticmethod
    def write_csv(table_name: str, new_data: list[dict]):
        with open(get_abs_path(table_name), mode="a", encoding="utf-8", newline="") as file:
            writer = DictWriter(file, fieldnames=get_csv_fields(table_name))
            writer.writerows(new_data)

    @staticmethod
    def get_next_id(data: list[dict]) -> int:
        if not data:
            return 1
        max_id = max(int(row.get('id', 0)) for row in data if row.get('id', '0').isdigit())
        return max_id + 1
    
    @staticmethod
    def parse_filter(filter_by: Optional[str], data: list[dict]) -> list[dict]:
        """Простой парсер фильтров вида 'key=value'."""
        if not filter_by or '=' not in filter_by:
            return data
        
        key, value = filter_by.split('=', 1)
        key = key.strip().lower()
        value = value.strip().lower()
        
        return [row for row in data if row.get(key, '').lower() == value]


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
    def __select_from_employees(filter_by: Optional[str], limit:Optional[int]=-1) -> str:
        """
        Читает данные о сотрудниках из CSV базы.
        Используйте для поиска сотрудников.
        
        Args:
            filter_by:  Необязательный фильтр в формате 'ключ=значение'. 
                        Например: 'department=IT' или 'name=Иван'. 
                        Если не указано, вернет всех сотрудников.
            limit:      Необязательное ограчение длины полученных из БД данных.
                        При limit < 0 выводится вся таблица.
        """
        try:
            data = CSVManager.read_csv(EMPLOYEES_TB)
            filtered_data = CSVManager.parse_filter(filter_by, data)
            
            if limit < 0:
                return json_dumps(filtered_data, ensure_ascii=False)

            tmp_res = []
            for row in filtered_data:
                tmp_res.append(row)
                if len(tmp_res) == limit:
                    return json_dumps(tmp_res, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка чтения БД сотрудников: {str(e)}"

    @staticmethod
    @tool
    def __insert_into_employees(
        login:str,
        password:str,
        name:str,
        surname:str,
        birthday_date:str,
        department:str,
        posistion:str,
        wage:int) -> str:
        """
        Добавляет нового сотрудника в CSV базу. Автоматически генерирует ID.
        
        Args:
            login: логин сотрудника,
            password: пароль сотрудника,
            name: имя сотрудника,
            surname: фамилия сотрудника,
            birthday_date: дата рождения сотрудника в формате YYYY-MM-DD,
            department: отдел,
            posistion: должность,
            wage: размер заработной платы (в рублях).
        """
        try:
            data = CSVManager.read_csv(EMPLOYEES_TB)
            
            new_row = {
                "Login": str(login),
                "Password": sanitize_csv_field(password),
                "Name": sanitize_csv_field(name),
                "Surname": sanitize_csv_field(surname),
                "Birthday_date": sanitize_csv_field(birthday_date),
                "Department": sanitize_csv_field(department),
                "Posistion": sanitize_csv_field(posistion),
                "Wage": sanitize_csv_field(wage)
            }
            data.append(new_row)
            CSVManager.write_csv(EMPLOYEES_TB, data)
            
            return json_dumps({"status": "success", "message": f"Сотрудник добавлен", "ID": new_id}, ensure_ascii=False)
        except Exception as e:
            return f"Ошибка добавления сотрудника: {str(e)}"
        
    @staticmethod
    @tool
    def __update_employees(employee_login: str, new_data_json: str) -> str:
        """
        Обновляет данные существующего сотрудника.
        
        Args:
            employee_login: логин сотрудника для обновления.
            new_data_json: Новые данные в формате JSON строки. 
                           Пример: '{"position": "Senior Developer", "department": "AI"}'
        """
        try:
            updates = json_loads(new_data_json)
            data = CSVManager.read_csv(EMPLOYEES_TB)
            
            found = False
            for row in data:
                if int(row.get('Login', 0)) == employee_login:
                    for key, value in updates.items():
                        if key in get_csv_fields(EMPLOYEES_TB) and key != 'Login':
                            row[key] = sanitize_csv_field(str(value))
                    found = True
                    break
                    
            if not found:
                return json_dumps({"status": "error", "message": f"Сотрудник с Login '{employee_login}' не найден"}, ensure_ascii=False)
                
            CSVManager.write_csv(EMPLOYEES_TB, data)
            return json_dumps({"status": "success", "message": f"Данные сотрудника '{employee_login}' обновлены"}, ensure_ascii=False)
        except JSONDecodeError:
            return "Ошибка: new_data_json не является валидным JSON."
        except Exception as e:
            return f"Ошибка обновления: {str(e)}"

    @staticmethod
    @tool
    def __delete_from_employees(employee_login: str) -> str:
        """
        Удаляет сотрудника из CSV базы по ID.
        
        Args:
            employee_id: ID сотрудника для удаления.
        """
        try:
            data = CSVManager.read_csv(EMPLOYEES_TB)
            initial_count = len(data)
            
            data = [row for row in data if int(row.get('Login', 0)) != employee_login]
            
            if len(data) == initial_count:
                return json_dumps({"status": "error", "message": f"Сотрудник с Login '{employee_login}' не найден"}, ensure_ascii=False)
                
            CSVManager.write_csv(EMPLOYEES_TB, data)
            return json_dumps({"status": "success", "message": f"Сотрудник '{employee_login}' удален"}, ensure_ascii=False)
        except Exception as e:
            return f"Ошибка удаления: {str(e)}"

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
    