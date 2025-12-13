import json
import asyncio
from typing import Dict, Any, Optional
from mistralai import Mistral
from config import MISTRAL_API_KEY, MISTRAL_MODEL


class MistralAIHandler:
    """Класс для работы с Mistral AI"""
    
    def __init__(self):
        if not MISTRAL_API_KEY:
            raise ValueError("MISTRAL_API_KEY не установлен в переменных окружения")
        self.client = Mistral(api_key=MISTRAL_API_KEY)
        self.model = MISTRAL_MODEL
    
    async def get_context_from_db(self, db_data: Dict[str, Any]) -> str:
        """
        Преобразует данные БД в текстовый контекст для Mistral
        
        Args:
            db_data: Данные из JSON БД
            
        Returns:
            Текстовое представление данных
        """
        context = "=== БАЗА ДАННЫХ (JSON) ===\n\n"
        context += json.dumps(db_data, ensure_ascii=False, indent=2)
        context += "\n\n=== КОНЕЦ БАЗЫ ДАННЫХ ===\n\n"
        return context
    
    async def process_query(self, query: str, db_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает запрос пользователя через Mistral AI с контекстом БД
        
        Args:
            query: Запрос пользователя
            db_data: Данные из JSON БД
            
        Returns:
            Словарь с ответом и флагом, нужно ли редактировать БД
        """
        context = await self.get_context_from_db(db_data)
        
        system_prompt = """Ты помощник, который работает с базой данных в формате JSON.
База данных содержит данные из Excel файлов, организованные по листам (sheets).

Твоя задача:
1. Анализировать данные из JSON и отвечать на вопросы пользователя
2. Если пользователь просит изменить данные, определить, какие именно изменения нужны
3. Возвращать ответ в формате JSON с полями:
   - "response": текстовый ответ пользователю
   - "needs_update": true/false - нужно ли обновить БД
   - "update_actions": массив действий для обновления (если needs_update = true)
   
Формат действий для обновления:
{
  "action": "update_field" | "add_row" | "delete_row" | "update_sheet",
  "sheet_name": "название листа",
  "row_index": номер строки (для update_field, delete_row),
  "field_name": "название поля" (для update_field),
  "new_value": новое значение (для update_field),
  "row_data": данные строки (для add_row),
  "sheet_data": все данные листа (для update_sheet)
}

Будь точным и внимательным при работе с данными."""
        
        user_message = f"{context}\n\nВопрос пользователя: {query}\n\nОтветь в формате JSON."
        
        try:
            # Выполняем синхронный вызов в executor, чтобы не блокировать event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.complete(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.3
                )
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Пытаемся извлечь JSON из ответа
            try:
                # Ищем JSON в ответе
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    # Если JSON не найден, возвращаем текстовый ответ
                    result = {
                        "response": response_text,
                        "needs_update": False,
                        "update_actions": []
                    }
            except json.JSONDecodeError:
                # Если не удалось распарсить JSON, возвращаем текстовый ответ
                result = {
                    "response": response_text,
                    "needs_update": False,
                    "update_actions": []
                }
            
            return result
        except Exception as e:
            return {
                "response": f"Ошибка при обработке запроса: {str(e)}",
                "needs_update": False,
                "update_actions": []
            }
    
    async def format_db_for_export(self, db_data: Dict[str, Any], sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Форматирует данные БД для экспорта в Excel
        
        Args:
            db_data: Данные из JSON БД
            sheet_name: Название листа для экспорта (если None, возвращаются все)
            
        Returns:
            Словарь с данными для экспорта
        """
        sheets = db_data.get("sheets", {})
        
        if sheet_name:
            return {sheet_name: sheets.get(sheet_name, [])}
        else:
            return sheets

