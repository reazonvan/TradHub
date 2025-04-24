import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем путь к корневой директории проекта
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Импортируем необходимые модули
from app.database import Base, engine

def run_migration():
    """
    Выполняет миграцию для добавления новых полей в таблицу users
    """
    # Подключаемся к базе данных
    conn = engine.connect()
    
    # Проверяем существование колонки phone
    result = conn.execute(text("PRAGMA table_info(users)"))
    columns = {row[1] for row in result.fetchall()}
    
    # Список изменений, которые нужно выполнить
    migrations = []
    
    # Проверяем и добавляем колонки, если их нет
    if 'phone' not in columns:
        migrations.append("ALTER TABLE users ADD COLUMN phone VARCHAR(20) UNIQUE")
    
    if 'two_factor_enabled' not in columns:
        migrations.append("ALTER TABLE users ADD COLUMN two_factor_enabled BOOLEAN DEFAULT 0")
    
    if 'two_factor_secret' not in columns:
        migrations.append("ALTER TABLE users ADD COLUMN two_factor_secret VARCHAR(255)")
    
    if 'created_at' not in columns:
        migrations.append("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    
    if 'updated_at' not in columns:
        migrations.append("ALTER TABLE users ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    
    if 'last_login' not in columns:
        migrations.append("ALTER TABLE users ADD COLUMN last_login DATETIME")
    
    # Выполняем миграции
    try:
        for migration in migrations:
            conn.execute(text(migration))
        
        # Необходимо выполнить коммит для сохранения изменений
        conn.commit()
        
        if migrations:
            print(f"Миграция успешно выполнена: добавлено {len(migrations)} колонок")
            for m in migrations:
                print(f" - {m}")
        else:
            print("Миграция не требуется: все колонки уже существуют")
            
    except Exception as e:
        print(f"Ошибка при выполнении миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration() 