import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

# Получаем путь к корневой директории проекта
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Импортируем необходимые модули
from app.database import Base
from app.models.user import User, UserRole
from app.security import get_password_hash

# Создаем соединение с базой данных
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Создаем сессию
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Создаем нового администратора
admin_password = get_password_hash("5906639Pe")
admin = User(
    username="reazonvan",
    email="ivanpetrov20066.ip@gmail.com",
    full_name="Администратор",
    phone="+79991234567",
    hashed_password=admin_password,
    role=UserRole.ADMIN.value,
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow()
)
db.add(admin)
db.commit()
db.refresh(admin)
print("Администратор успешно создан")

# Закрываем сессию
db.close() 