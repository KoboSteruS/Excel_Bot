import json
import os
from typing import Dict, List, Any, Optional
import aiofiles


class JsonDB:
    """Класс для работы с JSON базой данных"""
    
    def __init__(self, db_path: str = "database.json"):
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Создает файл БД, если он не существует"""
        if not os.path.exists(self.db_path):
            self._write_sync({"sheets": {}, "metadata": {"created_at": None, "last_updated": None}})
    
    def _write_sync(self, data: Dict[str, Any]):
        """Синхронная запись в файл (для инициализации)"""
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def read(self) -> Dict[str, Any]:
        """Читает всю БД"""
        try:
            async with aiofiles.open(self.db_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            raise Exception(f"Ошибка при чтении БД: {str(e)}")
    
    async def write(self, data: Dict[str, Any]):
        """Записывает данные в БД"""
        try:
            async with aiofiles.open(self.db_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            raise Exception(f"Ошибка при записи в БД: {str(e)}")
    
    async def save_excel_data(self, excel_data: Dict[str, List[Dict[str, Any]]], source_file: Optional[str] = None):
        """
        Сохраняет данные из Excel в БД
        
        Args:
            excel_data: Словарь с данными из Excel (лист -> список строк)
            source_file: Название исходного файла
        """
        db = await self.read()
        
        if "sheets" not in db:
            db["sheets"] = {}
        
        # Сохраняем данные каждого листа
        for sheet_name, rows in excel_data.items():
            db["sheets"][sheet_name] = rows
        
        # Обновляем метаданные
        import datetime
        db["metadata"] = {
            "last_updated": datetime.datetime.now().isoformat(),
            "source_file": source_file
        }
        
        await self.write(db)
    
    async def get_all_data(self) -> Dict[str, Any]:
        """Возвращает все данные из БД"""
        return await self.read()
    
    async def get_sheet_data(self, sheet_name: str) -> Optional[List[Dict[str, Any]]]:
        """Возвращает данные конкретного листа"""
        db = await self.read()
        return db.get("sheets", {}).get(sheet_name)
    
    async def update_sheet_data(self, sheet_name: str, data: List[Dict[str, Any]]):
        """Обновляет данные листа"""
        db = await self.read()
        if "sheets" not in db:
            db["sheets"] = {}
        db["sheets"][sheet_name] = data
        await self.write(db)
    
    async def update_field(self, sheet_name: str, row_index: int, field_name: str, new_value: Any):
        """Обновляет конкретное поле в конкретной строке"""
        db = await self.read()
        if "sheets" not in db:
            db["sheets"] = {}
        if sheet_name not in db["sheets"]:
            db["sheets"][sheet_name] = []
        
        sheet_data = db["sheets"][sheet_name]
        if 0 <= row_index < len(sheet_data):
            sheet_data[row_index][field_name] = new_value
            await self.write(db)
        else:
            raise IndexError(f"Индекс строки {row_index} вне диапазона")
    
    async def add_row(self, sheet_name: str, row_data: Dict[str, Any]):
        """Добавляет новую строку в лист"""
        db = await self.read()
        if "sheets" not in db:
            db["sheets"] = {}
        if sheet_name not in db["sheets"]:
            db["sheets"][sheet_name] = []
        
        db["sheets"][sheet_name].append(row_data)
        await self.write(db)
    
    async def delete_row(self, sheet_name: str, row_index: int):
        """Удаляет строку из листа"""
        db = await self.read()
        if "sheets" not in db:
            db["sheets"] = {}
        if sheet_name not in db["sheets"]:
            raise ValueError(f"Лист {sheet_name} не существует")
        
        sheet_data = db["sheets"][sheet_name]
        if 0 <= row_index < len(sheet_data):
            del sheet_data[row_index]
            await self.write(db)
        else:
            raise IndexError(f"Индекс строки {row_index} вне диапазона")

