# TradeHub

TradeHub — маркетплейс цифровых товаров и услуг с современным дизайном и расширенными возможностями.

## Стек технологий

### Backend
- FastAPI - основной фреймворк для API
- SQLAlchemy + PostgreSQL - хранение данных
- Redis + Celery - асинхронные задачи
- JWT-аутентификация - безопасный вход
- WebSocket - онлайн-чат между пользователями

### Frontend
- Jinja2 - шаблонизация страниц
- HTMX - динамические элементы
- Tailwind CSS - адаптивный дизайн
- Alpine.js - интерактивность

### Инфраструктура
- Docker Compose - для развертывания всех сервисов

## Установка и запуск

```bash
# Клонирование репозитория
git clone https://github.com/username/tradehub.git
cd tradehub

# Запуск через Docker Compose
docker-compose up -d
```

## Запуск в качестве сервера для внешнего доступа

### Вариант 1: Запуск с использованием Docker (рекомендуется)

1. Установите Docker Desktop для Windows
2. Запустите скрипт `start_tradehub.ps1` от имени администратора:
   ```powershell
   Start-Process powershell -Verb RunAs -ArgumentList "-File start_tradehub.ps1"
   ```

### Вариант 2: Запуск без Docker

1. Установите необходимые компоненты:
   - Python 3.11 или выше
   - PostgreSQL 14 или выше
   - Redis для Windows

2. Запустите скрипт `start_tradehub_no_docker.ps1` от имени администратора:
   ```powershell
   Start-Process powershell -Verb RunAs -ArgumentList "-File start_tradehub_no_docker.ps1"
   ```

### Доступ к сайту

После запуска любым способом сайт будет доступен по IP-адресу вашего компьютера:
- С Docker: `http://ваш_ip`
- Без Docker: `http://ваш_ip:8000`

## Роли пользователей
- Гость: просмотр товаров, поиск, регистрация
- Покупатель: покупка товаров, чат с продавцом, отзывы
- Продавец: размещение товаров, управление заказами, общение
- Администратор: модерация, управление пользователями, аналитика 