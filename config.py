import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    DATABASE_URL = os.getenv('DATABASE_URL')
    MODEL_NAME = os.getenv('MODEL_NAME', 'qwen/qwen3-14b:free')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
    DB_NAME = os.getenv('DB_NAME', 'writing_db')
    DB_HOST = os.getenv('DB_HOST', 'db')  # 'db' - имя сервиса в docker-composedd