import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random

# Загружаем переменные окружения
load_dotenv()

# Получаем путь к корневой директории проекта
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Импортируем необходимые модули
from app.database import Base
from app.models.user import User, UserRole
from app.models.product import Product, Category, ProductStatus
from app.models.order import Order, OrderStatus
from app.security import get_password_hash

# Создаем соединение с базой данных
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Создаем все таблицы
Base.metadata.create_all(bind=engine)

# Создаем сессию
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Проверяем, есть ли уже админ в базе данных
admin = db.query(User).filter(User.username == "admin").first()
if not admin:
    # Создаем администратора
    admin_password = get_password_hash("Admin123!")
    admin = User(
        username="admin",
        email="admin@tradehub.com",
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
    print("Администратор создан")
else:
    print("Администратор уже существует")

# Проверяем, есть ли продавцы в базе данных
sellers = db.query(User).filter(User.role == UserRole.SELLER.value).all()
if not sellers:
    # Создаем 5 продавцов
    for i in range(5):
        seller_password = get_password_hash(f"Seller{i+1}!")
        seller = User(
            username=f"seller{i+1}",
            email=f"seller{i+1}@tradehub.com",
            full_name=f"Продавец {i+1}",
            phone=f"+7999999{i+1:04d}",
            hashed_password=seller_password,
            role=UserRole.SELLER.value,
            seller_description=f"Описание продавца {i+1}. Предлагаю качественные услуги и товары в области программирования и дизайна.",
            seller_rating=random.uniform(3.5, 5.0),
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 100)),
            updated_at=datetime.utcnow()
        )
        db.add(seller)
    db.commit()
    print("Продавцы созданы")
else:
    print("Продавцы уже существуют")

# Закрываем сессию
db.close()

print("База данных успешно инициализирована") 