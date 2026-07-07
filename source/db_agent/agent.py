from langchain_core.tools import tool, StructuredTool

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

def parse_tool_calls_from_content(content: str) -> list:
    """Извлекает tool calls из content модели"""
    try:
        # Ищем JSON в content
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if 'tool' in data and 'arguments' in data:
                return [{
                    'name': data['tool'],
                    'args': data['arguments'],
                    'id': f"call_{data['tool']}"
                }]
    except (json.JSONDecodeError, KeyError):
        pass
    return []

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
    # @staticmethod
    def __init__(self):
        self.__tools = [
            self._select_from_employees,
            self._insert_into_employees,
            self._update_employees,
            self._delete_from_employees,

            # Методы для работы с БД клиентов
            self._select_from_clients,
            self._insert_into_clients,
            self._update_clients,
            self._delete_from_clients,
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
        
        # return response.content if hasattr(response, 'content') else str(response)
        return response
        
    #================================


    @staticmethod
    @tool
    def _select_from_employees(filter_by: Optional[str], limit:Optional[int]=-1) -> str:
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
    def _insert_into_employees(
        login:str,
        password:str,
        name:str,
        surname:str,
        birthday_date:str,
        department:str,
        position:str,
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
            position: должность,
            wage: размер заработной платы (в рублях).
        """
        try:
            # data = CSVManager.read_csv(EMPLOYEES_TB)
            # print(f"\t{data}\n")
            new_row = {
                "Login": sanitize_csv_field(str(login)),
                "Password": sanitize_csv_field(str(password)),
                "Name": sanitize_csv_field(str(name)),
                "Surname": sanitize_csv_field(str(surname)),
                "Birthday_date": sanitize_csv_field(str(birthday_date)),
                "Department": sanitize_csv_field(str(department)),
                "Position": sanitize_csv_field(str(position)),
                "Wage": sanitize_csv_field(str(wage))
            }
            # data.append(new_row)
            # print(f"\t{data}\n")

            # CSVManager.write_csv(EMPLOYEES_TB, data)
            CSVManager.write_csv(EMPLOYEES_TB, [new_row])
            
            return json_dumps({"status": "success", "message": f"Сотрудник добавлен", "Login": sanitize_csv_field(login)}, ensure_ascii=False)
        except Exception as e:
            return f"Ошибка добавления сотрудника: {str(e)}"
        
    @staticmethod
    @tool
    def _update_employees(employee_login: str, new_data_json: str) -> str:
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
    def _delete_from_employees(employee_login: str) -> str:
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
    def _select_from_clients(filter_by: Optional[str] = None, limit:Optional[int]=-1) -> str:
        """
        Читает данные о клиентах из CSV базы.
        
        Args:
            filter_by: Необязательный фильтр 'ключ=значение' (например, 'email=test@mail.com').
            limit:      Необязательное ограчение длины полученных из БД данных.
            При limit < 0 выводится вся таблица.
        """
        try:
            data = CSVManager.read_csv(CLIENTS_TB)
            filtered_data = CSVManager.parse_filter(filter_by, data)

            if limit < 0:
                return json_dumps(filtered_data, ensure_ascii=False)

            tmp_res = []
            for row in filtered_data:
                tmp_res.append(row)
                if len(tmp_res) == limit:
                    return json_dumps(tmp_res, ensure_ascii=False)

        except Exception as e:
            return f"Ошибка чтения БД клиентов: {str(e)}"

    @staticmethod
    @tool
    def _insert_into_clients(
        id:int,
        company_name:str,
        contact_person:str,
        email:str,
        phone:str,
        industry:str,
        contract_start:str,
        status:str,
        account_manager:str) -> str:
        """
        Добавляет нового клиента в CSV базу.
        
        Args:
            id: ID клиента,
            company_name: Название организации (клиента),
            contact_person: Лицо, представляющее клиента,
            email: Email контактного лица,
            phone: Телефон контактного лица,
            industry: Направление деятельности клиента,
            contract_start: Дата заключения контракта,
            status: Статус контракта,
            account_manager: С каким менеджером работает клиент.
        """
        try:
            data = CSVManager.read_csv(CLIENTS_TB)
            new_id = CSVManager.get_next_id(data)
            
            new_row = {
                "ID": str(new_id),
                "Сompany_name": sanitize_csv_field(company_name),
                "Contact_person": sanitize_csv_field(contact_person),
                "Email": sanitize_csv_field(email),
                "Phone": sanitize_csv_field(phone),
                "Industry": sanitize_csv_field(industry),
                "Contract_start": sanitize_csv_field(contract_start),
                "Status": sanitize_csv_field(status),
                "Account_manager": sanitize_csv_field(account_manager)
            }
            data.append(new_row)
            CSVManager.write_csv(CLIENTS_TB, data)
            
            return json_dumps({"status": "success", "message": "Клиент добавлен", "ID": new_id}, ensure_ascii=False)
        except Exception as e:
            return f"Ошибка добавления клиента: {str(e)}"

    @staticmethod
    @tool
    def _update_clients(client_id: int, new_data_json: str) -> str:
        """
        Обновляет данные клиента.
        
        Args:
            client_id: ID клиента.
            new_data_json: JSON строка с новыми данными (например, '{"phone": "+79999999999"}').
        """
        try:
            updates = json_loads(new_data_json)
            data = CSVManager.read_csv(CLIENTS_TB)
            
            found = False
            for row in data:
                if int(row.get('ID', 0)) == client_id:
                    for key, value in updates.items():
                        if key in get_csv_fields(CLIENTS_TB) and key != 'ID':
                            row[key] = sanitize_csv_field(str(value))
                    found = True
                    break
                    
            if not found:
                return json_dumps({"status": "error", "message": f"Клиент {client_id} не найден"}, ensure_ascii=False)
                
            CSVManager.write_csv(CLIENTS_TB, data)
            return json_dumps({"status": "success", "message": f"Клиент {client_id} обновлен"}, ensure_ascii=False)
        except JSONDecodeError:
            return "Ошибка: new_data_json не является валидным JSON."
        except Exception as e:
            return f"Ошибка обновления: {str(e)}"

    @staticmethod
    @tool
    def _delete_from_clients(client_id: int) -> str:
        """
        Удаляет клиента из CSV базы по ID.
        
        Args:
            client_id: ID клиента.
        """
        try:
            data = CSVManager.read_csv(CLIENTS_TB)
            initial_count = len(data)
            data = [row for row in data if int(row.get('ID', 0)) != client_id]
            
            if len(data) == initial_count:
                return json_dumps({"status": "error", "message": f"Клиент {client_id} не найден"}, ensure_ascii=False)
                
            CSVManager.write_csv(CLIENTS_TB, data)
            return json_dumps({"status": "success", "message": f"Клиент {client_id} удален"}, ensure_ascii=False)
        except Exception as e:
            return f"Ошибка удаления: {str(e)}"
    