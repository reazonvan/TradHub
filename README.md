# 🌐 TradeHub - Современный маркетплейс цифровых товаров

![Версия](https://img.shields.io/badge/версия-1.0.0-blue)
![Лицензия](https://img.shields.io/badge/лицензия-MIT-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)
![Docker](https://img.shields.io/badge/Docker-готово-blue.svg)

<p align="center">
  <img src="https://via.placeholder.com/800x400?text=TradeHub" width="600" alt="TradeHub логотип"/>
</p>

TradeHub — это современный маркетплейс цифровых товаров и услуг, созданный с использованием передовых веб-технологий. Платформа обеспечивает удобный интерфейс как для покупателей, так и для продавцов цифровых продуктов.

## ✨ Особенности

- 🔐 **Безопасная аутентификация**: JWT-токены и надежное хранение паролей
- 💬 **Онлайн-чат**: Мгновенная связь между продавцами и покупателями через WebSocket
- 🎨 **Современный UI**: Адаптивный дизайн с использованием Tailwind CSS и Alpine.js
- 🚀 **Высокая производительность**: Асинхронная обработка запросов на FastAPI
- 📊 **Аналитика**: Отслеживание ключевых метрик через MCP (Model-Control-Presenter)
- 🔄 **Интерактивность**: Динамические элементы и обновления страниц с HTMX
- 📱 **Адаптивность**: Корректное отображение на всех устройствах

## 🛠️ Стек технологий

### Backend
- **FastAPI** - высокопроизводительный фреймворк для API
- **SQLAlchemy + PostgreSQL** - ORM и надежная СУБД
- **Redis + Celery** - асинхронные задачи и кеширование
- **JWT** - безопасная аутентификация и авторизация
- **WebSocket** - для реализации онлайн-чата

### Frontend
- **Jinja2** - мощный шаблонизатор
- **HTMX** - современный подход к созданию динамических интерфейсов
- **Tailwind CSS** - утилитарный CSS-фреймворк
- **Alpine.js** - легковесный JavaScript-фреймворк

### Инфраструктура
- **Docker + Docker Compose** - контейнеризация и оркестрация
- **Nginx** - веб-сервер и обратный прокси
- **MCP** - инструменты отладки и мониторинга

## 📋 Требования

- Docker и Docker Compose (рекомендуется)
- Python 3.11+ (для запуска без Docker)
- PostgreSQL 14+ (для запуска без Docker)
- Redis (для запуска без Docker)
- Node.js (для MCP и инструментов разработки)

## 🚀 Быстрый старт

### С использованием Docker (рекомендуется)

```bash
# Клонирование репозитория
git clone https://github.com/username/tradehub.git
cd tradehub

# Копирование и настройка переменных окружения
cp .env.example .env
# Отредактируйте .env файл под свои нужды

# Запуск всех сервисов
docker-compose up -d
```

### Без Docker

```bash
# Клонирование репозитория
git clone https://github.com/username/tradehub.git
cd tradehub

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка базы данных
python create_db.py

# Запуск
uvicorn app.main:app --reload
```

## 🔧 Запуск в качестве сервера

### Windows PowerShell

```powershell
# С Docker (рекомендуется)
Start-Process powershell -Verb RunAs -ArgumentList "-File start_tradehub.ps1"

# Без Docker
Start-Process powershell -Verb RunAs -ArgumentList "-File start_tradehub_no_docker.ps1"
```

После запуска сайт будет доступен по адресу:
- С Docker: `http://ваш_ip`
- Без Docker: `http://ваш_ip:8000`

## 🖥️ Панель управления MCP

TradeHub включает в себя MCP (Model-Control-Presenter) для отладки и аналитики:

```bash
# Запуск MCP сервера
npm run start-mcp
```

Доступ к панели MCP: `http://localhost:3025`

## 👥 Роли пользователей

- **Гость**: просмотр товаров, поиск, регистрация
- **Покупатель**: все возможности гостя + покупка товаров, чат с продавцом, отзывы
- **Продавец**: размещение товаров, управление заказами, общение с покупателями
- **Администратор**: полный доступ к модерации, управление пользователями, аналитика

## 📁 Структура проекта

```
tradehub/
├── app/                 # Основной код приложения
│   ├── models/          # SQLAlchemy модели
│   ├── routers/         # FastAPI эндпоинты
│   ├── schemas/         # Pydantic модели
│   ├── services/        # Бизнес-логика
│   ├── main.py          # Точка входа FastAPI
│   └── ...
├── nginx/               # Конфигурация Nginx
├── static/              # Статические файлы (CSS, JS)
├── templates/           # Jinja2 шаблоны
├── tests/               # Тесты
├── docker-compose.yml   # Конфигурация Docker
├── Dockerfile           # Сборка контейнера
└── ...
```

## 📚 Документация

- **API**: доступна по адресу `/docs` или `/redoc` после запуска
- **MCP**: подробная документация в [MCP_README.md](./MCP_README.md)
- **Настройка сервера**: инструкции в [SERVER_SETUP.md](./SERVER_SETUP.md)

## 🤝 Вклад в проект

Мы приветствуем ваш вклад в развитие TradeHub! Следуйте этим шагам:

1. Форкните репозиторий
2. Создайте ветку для вашей функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Добавлена удивительная функция'`)
4. Отправьте ветку в ваш форк (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📜 Лицензия

Распространяется под лицензией MIT. См. файл `LICENSE` для получения дополнительной информации.

## 📞 Контакты

- **Разработчик**: [Имя Разработчика](mailto:developer@example.com)
- **Сайт проекта**: [tradehub.example.com](https://tradehub.example.com)
- **GitHub**: [github.com/username/tradehub](https://github.com/username/tradehub) 