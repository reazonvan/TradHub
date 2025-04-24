import os
from pydantic import BaseSettings
from typing import List
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройки для SMS API
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "sms_ru")  # По умолчанию используем SMS.ru
SMS_API_KEY = os.getenv("SMS_API_KEY", "")  # API ключ от SMS.ru
SMS_FROM = os.getenv("SMS_FROM", "")  # Имя отправителя (не всегда требуется)
SMS_TEST_MODE = os.getenv("SMS_TEST_MODE", "1") == "1"  # Тестовый режим по умолчанию включен

# Настройки для Twilio (альтернативный провайдер)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения
    """
    # Настройки приложения
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"
    # Получаем ALLOWED_HOSTS как строку
    _ALLOWED_HOSTS: str = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
    
    # URL сайта для формирования ссылок
    SITE_URL: str = os.getenv("SITE_URL", "http://localhost:8000")
    
    # Настройки безопасности cookie
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "False") == "True"
    
    # Настройки базы данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tradehub.db")
    
    # Настройки Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Настройки JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret_key_for_development_only")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 часа
    
    # Настройки файлов
    UPLOAD_DIR: str = "media/uploads"
    MAX_UPLOAD_SIZE: int = 5_242_880  # 5MB
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        """Преобразуем строку с запятыми в список строк"""
        return self._ALLOWED_HOSTS.split(",")

# Создание экземпляра настроек
settings = Settings() 