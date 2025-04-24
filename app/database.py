from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis
from app.config import settings

# Создание движка SQLAlchemy для соединения с базой данных
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Логирование SQL-запросов при DEBUG=True
    pool_pre_ping=True,   # Проверка соединения перед использованием
)

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание базового класса для моделей
Base = declarative_base()

# Создание подключения к Redis
try:
    redis_client = redis.from_url(settings.REDIS_URL)
    # Проверка подключения к Redis
    redis_client.ping()
except Exception as e:
    import logging
    logging.error(f"Ошибка подключения к Redis: {str(e)}")
    # Создаем заглушку для Redis, чтобы не падало приложение при недоступности Redis
    class RedisMock:
        def get(self, key):
            return None
        
        def set(self, key, value, ex=None, keepttl=False):
            pass
        
        def ping(self):
            return False
            
    redis_client = RedisMock()

# Функция-зависимость для получения сессии БД
def get_db():
    """
    Функция-генератор для получения сессии базы данных.
    Используется как зависимость в FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 