from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from datetime import datetime, timedelta
import logging
import sys
import json
from pathlib import Path

from app.routers import auth, users, products, orders, admin, chat
from app.database import engine, Base
from app.config import settings
from app.security import get_cookie_user

# Настройка логирования
# Создаем директорию для логов, если её нет
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Настройка общего логгера
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        # Логи в файл
        logging.FileHandler(logs_dir / "tradehub.log"),
        # Логи в консоль
        logging.StreamHandler(sys.stdout)
    ]
)

# Получаем корневой логгер и устанавливаем уровень логов
logger = logging.getLogger("tradehub")
logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

# Логгер для запросов и ответов
api_logger = logging.getLogger("api")
api_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

# Логгер для ошибок и исключений
error_logger = logging.getLogger("errors")
error_logger.setLevel(logging.ERROR)

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# Запуск миграций
try:
    from app.migrations.create_phone_verifications import run_migration
    migration_result = run_migration()
    if migration_result:
        logger.info("Миграция для верификации телефонов успешно выполнена")
    else:
        logger.error("Ошибка при выполнении миграции для верификации телефонов")
except Exception as e:
    logger.error(f"Ошибка при запуске миграции: {str(e)}")

# Инициализация приложения FastAPI
app = FastAPI(
    title="TradeHub API",
    description="API для маркетплейса цифровых товаров и услуг",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "Content-Disposition"],
    max_age=3600,
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

# Инициализация шаблонов Jinja2
templates = Jinja2Templates(directory="templates")

# Определение глобальных переменных для шаблонов Jinja2
# В FastAPI нет context_processor, добавляем переменные в каждый шаблон
def get_global_template_vars():
    """
    Получение глобальных переменных для шаблонов
    """
    return {
        "site_name": "TradeHub",
        "current_year": datetime.now().year,
    }

# Определение кастомных фильтров для Jinja2
def format_price(value):
    """Форматирует число в денежный формат с пробелами"""
    return f"₽ {'{:,.0f}'.format(value).replace(',', ' ')}"

def time_ago(value):
    """Возвращает относительное время (например, "5 минут назад")"""
    now = datetime.utcnow()
    diff = now - value
    
    if diff < timedelta(minutes=1):
        return "только что"
    elif diff < timedelta(hours=1):
        minutes = diff.seconds // 60
        return f"{minutes} {'минуту' if minutes == 1 else 'минуты' if 2 <= minutes <= 4 else 'минут'} назад"
    elif diff < timedelta(days=1):
        hours = diff.seconds // 3600
        return f"{hours} {'час' if hours == 1 else 'часа' if 2 <= hours <= 4 else 'часов'} назад"
    elif diff < timedelta(days=30):
        days = diff.days
        return f"{days} {'день' if days == 1 else 'дня' if 2 <= days <= 4 else 'дней'} назад"
    else:
        return value.strftime("%d.%m.%Y")

def date_format(value):
    """Форматирует дату в локализованный формат"""
    return value.strftime("%d.%m.%Y %H:%M")

# Создаем функцию url_for для использования в шаблонах, которая генерирует URL-адреса для эндпоинтов
def url_for(name, **params):
    """
    Функция для генерации URL-адреса по имени эндпоинта
    """
    # Словарь с соответствием имен эндпоинтов и URL-адресов
    endpoint_map = {
        # URL-адреса для профиля пользователя
        "user_profile": "/users/profile",
        "update_user_profile": "/users/profile/edit",
        "update_user_profile_page": "/users/profile/edit",
        "upload_avatar": "/users/profile/avatar",
        "user_security": "/users/profile/security",
        "change_password": "/users/profile/security/change-password",
        "enable_2fa": "/users/profile/security/2fa/enable",
        "disable_2fa": "/users/profile/security/2fa/disable",
        "terminate_session": "/users/profile/security/sessions/{session_id}/terminate",
        "terminate_all_sessions": "/users/profile/security/sessions/terminate-all",
        "become_seller": "/users/profile/become-seller",
        "become_seller_page": "/users/profile/become-seller",
        "become_seller_submit": "/users/profile/become-seller",
        
        # Другие маршруты магазина
        "user_orders": "/orders/my",
        "seller_products": "/products/my",
        "seller_orders": "/orders/seller",
        "user_wishlist": "/wishlist",
        
        # Маршруты аутентификации
        "login": "/auth/login",
        "register": "/auth/register",
        "logout": "/auth/logout",
        
        # Другие маршруты
        "home": "/",
        "product_list": "/products",
        "product_detail": "/products/{product_id}",
        "shopping_cart": "/cart",
    }
    
    # Получаем URL-адрес из словаря
    url = endpoint_map.get(name)
    if not url:
        logger.warning(f"URL для эндпоинта {name} не найден")
        return "#"  # Возвращаем заглушку, если URL не найден
    
    # Заменяем параметры в URL
    for key, value in params.items():
        url = url.replace(f"{{{key}}}", str(value))
    
    return url

# Регистрация кастомных фильтров и глобальных функций
templates.env.filters["format_price"] = format_price
templates.env.filters["time_ago"] = time_ago
templates.env.filters["date_format"] = date_format
templates.env.globals["url_for"] = url_for

# Подключение роутеров
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Начало запроса - логируем информацию
    request_id = f"{datetime.now().timestamp()}-{id(request)}"
    client_host = request.client.host if request.client else "unknown"
    
    request_info = {
        "request_id": request_id,
        "client_ip": client_host,
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "headers": dict(request.headers),
        "timestamp": datetime.now().isoformat()
    }
    
    # Логируем информацию о запросе
    api_logger.info(f"Запрос {request_id}: {request.method} {request.url.path} от {client_host}")
    
    # Детальное логирование для POST запросов
    if request.method == "POST":
        try:
            if request.headers.get("content-type", "").startswith("application/json"):
                body = await request.json()
                # Скрываем пароли и другие чувствительные данные
                if "password" in body:
                    body["password"] = "[СКРЫТО]"
                request_info["body"] = body
                api_logger.debug(f"Тело запроса: {json.dumps(body, ensure_ascii=False)}")
            elif request.headers.get("content-type", "").startswith("multipart/form-data"):
                form = await request.form()
                form_dict = {k: "[FILE]" if hasattr(v, "filename") else v for k, v in form.items()}
                # Скрываем пароли
                if "password" in form_dict:
                    form_dict["password"] = "[СКРЫТО]"
                request_info["form"] = form_dict
                api_logger.debug(f"Форма запроса: {json.dumps(form_dict, ensure_ascii=False)}")
        except Exception as e:
            api_logger.error(f"Ошибка при логировании тела запроса: {str(e)}")
    
    # Засекаем время
    start_time = datetime.now()
    
    try:
        # Выполняем запрос
        response = await call_next(request)
        
        # Подсчитываем время выполнения
        process_time = (datetime.now() - start_time).total_seconds()
        
        # Логируем информацию о времени выполнения и статусе ответа
        api_logger.info(
            f"Ответ {request_id}: {response.status_code} для {request.method} {request.url.path} "
            f"(выполнено за {process_time:.4f} сек)"
        )
        
        # Добавляем заголовок с временем обработки
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    except Exception as exc:
        # Логируем ошибки
        process_time = (datetime.now() - start_time).total_seconds()
        error_logger.exception(
            f"Ошибка {request_id}: Исключение при обработке {request.method} {request.url.path}: "
            f"{str(exc)} (через {process_time:.4f} сек)"
        )
        raise

@app.middleware("http")
async def add_current_user_to_request(request: Request, call_next):
    """
    Добавляет текущего пользователя в request для передачи в шаблоны
    """
    # Получаем пользователя из cookie
    current_user = get_cookie_user(request)
    
    # Добавляем пользователя в request.state
    request.state.user = current_user
    
    # Вызываем следующий обработчик
    response = await call_next(request)
    
    return response

# Функция для объединения контекста шаблона
def get_template_context(request: Request, context: dict = None) -> dict:
    """
    Объединяет контекст шаблона с глобальными переменными
    """
    # Базовый контекст
    result = {
        "request": request,
        "user": getattr(request.state, "user", None),
    }
    
    # Добавляем глобальные переменные
    result.update(get_global_template_vars())
    
    # Добавляем переданный контекст, если он есть
    if context:
        result.update(context)
    
    return result

# Основные маршруты сайта
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Главная страница сайта
    """
    context = get_template_context(request)
    return templates.TemplateResponse("index.html", context)

@app.get("/health")
async def health_check():
    """
    Проверка состояния API
    """
    return {"status": "ok", "time": datetime.now().isoformat()}

# Добавляем middleware для X-Serveo-URL
@app.middleware("http")
async def check_serveo_url(request: Request, call_next):
    """
    Middleware для определения URL Serveo и установки правильных заголовков
    """
    # Извлекаем имя хоста из запроса
    host = request.headers.get("host", "")
    
    # Проверяем, является ли запрос от Serveo
    if "serveo.net" in host:
        logger.info(f"Запрос через Serveo: {host}")
        
        # Запоминаем URL Serveo в логах
        with open("logs/serveo/current_url.txt", "w") as f:
            f.write(f"http://{host}")
    
    # Продолжаем обработку запроса
    response = await call_next(request)
    
    # Добавляем заголовок безопасности для всех ответов
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    
    return response 