"""
Миграция для создания таблицы верификации телефонов и добавления поля phone_verified в таблицу users
"""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.database import engine

# SQL-скрипты для выполнения миграции
CREATE_PHONE_VERIFICATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS phone_verifications (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) NOT NULL,
    code VARCHAR(6) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    attempts INTEGER DEFAULT 0
);
"""

CREATE_PHONE_INDEX = """
CREATE INDEX IF NOT EXISTS phone_verifications_phone_idx ON phone_verifications (phone);
"""

ADD_PHONE_VERIFIED_COLUMN = """
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE;
"""

def run_migration():
    """
    Запускает миграцию для создания таблицы верификации телефонов
    """
    try:
        # Создаем соединение с базой данных
        conn = engine.connect()
        
        # Создаем таблицу верификации телефонов
        conn.execute(text(CREATE_PHONE_VERIFICATIONS_TABLE))
        
        # Создаем индекс по полю phone
        conn.execute(text(CREATE_PHONE_INDEX))
        
        # Добавляем колонку phone_verified в таблицу users
        conn.execute(text(ADD_PHONE_VERIFIED_COLUMN))
        
        # Фиксируем изменения
        conn.commit()
        
        print("Миграция успешно выполнена.")
        return True
    except SQLAlchemyError as e:
        print(f"Ошибка при выполнении миграции: {str(e)}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration() 