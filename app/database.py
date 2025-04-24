from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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