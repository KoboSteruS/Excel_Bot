import pandas as pd
import os
from typing import Dict, List, Any


class ExcelHandler:
    """Класс для работы с Excel файлами"""
    
    @staticmethod
    async def read_excel(file_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Читает Excel файл и возвращает словарь, где ключ - название листа,
        значение - список словарей с данными
        
        Args:
            file_path: Путь к Excel файлу
            
        Returns:
            Словарь с данными из всех листов
        """
        try:
            excel_file = pd.ExcelFile(file_path)
            result = {}
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                # Преобразуем DataFrame в список словарей
                # Заменяем NaN на None для JSON совместимости
                result[sheet_name] = df.where(pd.notna(df), None).to_dict('records')
            
            return result
        except Exception as e:
            raise Exception(f"Ошибка при чтении Excel файла: {str(e)}")
    
    @staticmethod
    async def create_excel_from_json(data: Dict[str, List[Dict[str, Any]]], output_path: str, sheet_name: str = None) -> str:
        """
        Создает Excel файл из данных JSON
        
        Args:
            data: Словарь, где ключ - название листа, значение - список словарей
            output_path: Путь для сохранения Excel файла
            sheet_name: Название листа для экспорта (если None, используется первый лист)
            
        Returns:
            Путь к созданному файлу
        """
        try:
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                if sheet_name and sheet_name in data:
                    # Экспортируем конкретный лист
                    df = pd.DataFrame(data[sheet_name])
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                elif data:
                    # Экспортируем все листы
                    for sheet, rows in data.items():
                        df = pd.DataFrame(rows)
                        df.to_excel(writer, sheet_name=sheet, index=False)
                else:
                    raise ValueError("Нет данных для экспорта")
            
            return output_path
        except Exception as e:
            raise Exception(f"Ошибка при создании Excel файла: {str(e)}")


