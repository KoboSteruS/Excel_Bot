import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode
import aiofiles

from config import TELEGRAM_BOT_TOKEN, DB_JSON_PATH, UPLOADS_DIR, EXPORTS_DIR
from excel_handler import ExcelHandler
from json_db import JsonDB
from mistral_ai import MistralAIHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация компонентов
excel_handler = ExcelHandler()
db = JsonDB(DB_JSON_PATH)
mistral_handler = None

# Создание директорий
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = """
🤖 Добро пожаловать в бот для работы с Excel и Mistral AI!

Доступные команды:
/start - Показать это сообщение
/help - Показать справку
/status - Показать статус БД

Возможности:
📁 Отправьте Excel файл (.xlsx, .xls) - он будет прочитан и сохранен в БД
💬 Отправьте текстовое сообщение - Mistral AI ответит на основе данных в БД
📊 Бот может редактировать данные по вашему запросу и экспортировать их в Excel
"""
    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📖 Справка по использованию бота:

1. 📤 ЗАГРУЗКА EXCEL ФАЙЛА:
   Просто отправьте файл .xlsx или .xls боту
   Файл будет прочитан и все данные сохранены в БД (JSON)

2. 💬 ВОПРОСЫ К ДАННЫМ:
   Напишите любой вопрос о данных в БД
   Mistral AI проанализирует данные и ответит

3. ✏️ РЕДАКТИРОВАНИЕ ДАННЫХ:
   Попросите Mistral изменить данные
   Например: "Измени значение в строке 5, колонке 'Имя' на 'Иван'"
   Бот автоматически обновит БД

4. 📊 ЭКСПОРТ ДАННЫХ:
   Попросите экспортировать данные в Excel
   Например: "Экспортируй лист 'Лист1' в Excel"
   Бот создаст и отправит Excel файл

Примеры запросов:
- "Сколько строк в базе данных?"
- "Покажи все уникальные значения в колонке 'Город'"
- "Измени статус в строке 3 на 'Завершено'"
- "Экспортируй все данные листа 'Отчет' в Excel"
"""
    await update.message.reply_text(help_text)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status - показывает статус БД"""
    try:
        db_data = await db.get_all_data()
        sheets = db_data.get("sheets", {})
        metadata = db_data.get("metadata", {})
        
        status_text = "📊 Статус базы данных:\n\n"
        status_text += f"📁 Количество листов: {len(sheets)}\n\n"
        
        for sheet_name, rows in sheets.items():
            status_text += f"📋 {sheet_name}: {len(rows)} строк\n"
        
        if metadata.get("last_updated"):
            status_text += f"\n🕐 Последнее обновление: {metadata.get('last_updated')}"
        
        if not sheets:
            status_text += "\n\n⚠️ База данных пуста. Загрузите Excel файл."
        
        await update.message.reply_text(status_text)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при получении статуса: {str(e)}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки документов (Excel файлов)"""
    document = update.message.document
    
    if document is None:
        await update.message.reply_text("❌ Файл не найден.")
        return
    
    file_name = document.file_name.lower()
    
    # Проверяем, что это Excel файл
    if not (file_name.endswith('.xlsx') or file_name.endswith('.xls')):
        await update.message.reply_text("❌ Пожалуйста, отправьте Excel файл (.xlsx или .xls)")
        return
    
    try:
        # Отправляем сообщение о начале обработки
        status_msg = await update.message.reply_text("⏳ Обработка Excel файла...")
        
        # Скачиваем файл
        file = await context.bot.get_file(document.file_id)
        file_path = os.path.join(UPLOADS_DIR, document.file_name)
        await file.download_to_drive(file_path)
        
        # Читаем Excel
        excel_data = await excel_handler.read_excel(file_path)
        
        # Сохраняем в БД
        await db.save_excel_data(excel_data, source_file=document.file_name)
        
        # Формируем ответ
        result_text = f"✅ Файл успешно обработан!\n\n"
        result_text += f"📁 Файл: {document.file_name}\n"
        result_text += f"📊 Листов обработано: {len(excel_data)}\n\n"
        
        for sheet_name, rows in excel_data.items():
            result_text += f"📋 {sheet_name}: {len(rows)} строк\n"
        
        await status_msg.edit_text(result_text)
        
        # Удаляем временный файл
        try:
            os.remove(file_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка при обработке файла: {str(e)}")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений - взаимодействие с Mistral AI"""
    query = update.message.text
    
    if not query or query.strip() == "":
        return
    
    try:
        # Инициализируем Mistral handler, если еще не инициализирован
        global mistral_handler
        if mistral_handler is None:
            try:
                mistral_handler = MistralAIHandler()
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Ошибка инициализации Mistral AI: {str(e)}\n"
                    "Убедитесь, что MISTRAL_API_KEY установлен в .env файле"
                )
                return
        
        # Отправляем сообщение о начале обработки
        status_msg = await update.message.reply_text("🤔 Обрабатываю запрос через Mistral AI...")
        
        # Получаем данные из БД
        db_data = await db.get_all_data()
        
        # Обрабатываем запрос через Mistral
        result = await mistral_handler.process_query(query, db_data)
        
        response_text = result.get("response", "Не удалось получить ответ")
        needs_update = result.get("needs_update", False)
        update_actions = result.get("update_actions", [])
        
        # Обновляем БД, если нужно
        if needs_update and update_actions:
            try:
                await apply_updates(update_actions)
                response_text += "\n\n✅ База данных обновлена!"
            except Exception as e:
                response_text += f"\n\n⚠️ Ошибка при обновлении БД: {str(e)}"
        
        # Проверяем, запрошен ли экспорт в Excel
        export_keywords = ['экспорт', 'экспортировать', 'скачать', 'выгрузить', 'excel', 'export', 'отправь файл', 'дай файл']
        export_requested = any(keyword in query.lower() for keyword in export_keywords)
        
        # Если запрошен экспорт или были изменения, создаем и отправляем файл
        should_export = export_requested or (needs_update and update_actions)
        
        if should_export:
            # Определяем, какой лист экспортировать
            sheet_name = None
            for action in update_actions:
                if "sheet_name" in action:
                    sheet_name = action["sheet_name"]
                    break
            
            # Если sheet_name не найден в действиях, пытаемся найти в запросе
            if not sheet_name:
                db_data_updated = await db.get_all_data()
                sheets = db_data_updated.get("sheets", {}).keys()
                # Берем первый лист или ищем упоминание в запросе
                for sheet in sheets:
                    if sheet.lower() in query.lower():
                        sheet_name = sheet
                        break
                if not sheet_name and sheets:
                    sheet_name = list(sheets)[0]
            
            if sheet_name:
                try:
                    db_data_updated = await db.get_all_data()
                    export_data = await mistral_handler.format_db_for_export(
                        db_data_updated, sheet_name
                    )
                    export_file = os.path.join(EXPORTS_DIR, f"export_{sheet_name}.xlsx")
                    await excel_handler.create_excel_from_json(export_data, export_file, sheet_name)
                    
                    # Отправляем файл
                    with open(export_file, 'rb') as f:
                        await update.message.reply_document(
                            document=f,
                            filename=f"{sheet_name}_export.xlsx",
                            caption=f"📊 Экспортированные данные из листа '{sheet_name}'"
                        )
                except Exception as e:
                    logger.error(f"Ошибка при экспорте: {e}", exc_info=True)
                    response_text += f"\n\n⚠️ Ошибка при экспорте Excel: {str(e)}"
        
        # Отправляем ответ
        await status_msg.edit_text(response_text)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def apply_updates(update_actions: list):
    """Применяет обновления к БД на основе действий от Mistral"""
    for action in update_actions:
        action_type = action.get("action")
        sheet_name = action.get("sheet_name")
        
        if not sheet_name:
            continue
        
        try:
            if action_type == "update_field":
                row_index = action.get("row_index")
                field_name = action.get("field_name")
                new_value = action.get("new_value")
                if row_index is not None and field_name and new_value is not None:
                    await db.update_field(sheet_name, row_index, field_name, new_value)
            
            elif action_type == "add_row":
                row_data = action.get("row_data")
                if row_data:
                    await db.add_row(sheet_name, row_data)
            
            elif action_type == "delete_row":
                row_index = action.get("row_index")
                if row_index is not None:
                    await db.delete_row(sheet_name, row_index)
            
            elif action_type == "update_sheet":
                sheet_data = action.get("sheet_data")
                if sheet_data:
                    await db.update_sheet_data(sheet_name, sheet_data)
        
        except Exception as e:
            logger.error(f"Ошибка при применении действия {action_type}: {e}")
            raise


def main():
    """Главная функция для запуска бота"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен! Создайте .env файл с токеном.")
        return
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

