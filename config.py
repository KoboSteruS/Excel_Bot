import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Mistral AI API Key
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")

# Пути к файлам
DB_JSON_PATH = "database.json"
UPLOADS_DIR = "uploads"
EXPORTS_DIR = "exports"

# Модель Mistral
MISTRAL_MODEL = "mistral-large-latest"

