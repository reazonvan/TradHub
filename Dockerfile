FROM python:3.11-slim

WORKDIR /app

# Копирование зависимостей и установка
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходников приложения
COPY . .

RUN mkdir -p static media

# Порт для FastAPI
EXPOSE 8000

# Запуск приложения через uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 