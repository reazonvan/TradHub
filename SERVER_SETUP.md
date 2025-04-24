# Руководство по настройке сервера TradeHub на Windows

В этом руководстве описано, как превратить ваш ноутбук или компьютер с Windows в полноценный сервер для проекта TradeHub, чтобы другие пользователи могли получить к нему доступ из сети.

## Предварительные требования

### Вариант 1: Запуск через Docker (рекомендуется)
- Windows 10/11
- Права администратора
- [Docker Desktop для Windows](https://www.docker.com/products/docker-desktop)
- Стабильное подключение к Интернету
- Минимум 8 ГБ ОЗУ
- 20 ГБ свободного места на диске

### Вариант 2: Запуск без Docker
- Windows 10/11
- Права администратора
- [Python 3.11](https://www.python.org/downloads/) или выше
- [PostgreSQL 14](https://www.postgresql.org/download/windows/) или выше
- [Redis для Windows](https://github.com/tporadowski/redis/releases)
- Стабильное подключение к Интернету
- Минимум 4 ГБ ОЗУ

## Шаг 1: Настройка сетевого доступа

### Настройка роутера для доступа из интернета

Если вы хотите, чтобы сайт был доступен из интернета (не только в локальной сети):

1. Зайдите в настройки вашего роутера (обычно http://192.168.0.1 или http://192.168.1.1)
2. Найдите раздел "Перенаправление портов" (Port Forwarding)
3. Добавьте перенаправление для порта 80 (HTTP) на локальный IP вашего компьютера
4. По желанию можно также настроить динамический DNS (DDNS), чтобы получить постоянное доменное имя

### Настройка брандмауэра Windows

В скриптах запуска эти команды уже включены, но при необходимости можно выполнить вручную:

```powershell
# Открытие порта 80 для HTTP
netsh advfirewall firewall add rule name="TradeHub HTTP" dir=in action=allow protocol=TCP localport=80

# Открытие порта 8000 для API (при запуске без Docker)
netsh advfirewall firewall add rule name="TradeHub API" dir=in action=allow protocol=TCP localport=8000
```

## Шаг 2: Установка необходимого ПО

### Для запуска с Docker
1. Установите [Docker Desktop для Windows](https://www.docker.com/products/docker-desktop)
2. Запустите Docker Desktop и дождитесь его полной загрузки
3. Убедитесь, что Docker работает, выполнив в PowerShell:
   ```powershell
   docker --version
   ```

### Для запуска без Docker
1. Установите [Python 3.11](https://www.python.org/downloads/) или выше
2. Установите [PostgreSQL 14](https://www.postgresql.org/download/windows/) или выше
   - Запомните пароль пользователя postgres
   - Создайте базу данных tradehub
3. Установите [Redis для Windows](https://github.com/tporadowski/redis/releases)

## Шаг 3: Подготовка проекта

1. Клонируйте репозиторий или распакуйте архив с проектом
2. Создайте файл `.env` на основе `.env.example` и настройте переменные среды
   - Измените `DATABASE_URL`, `REDIS_URL` и `SITE_URL` на правильные значения
   - Добавьте ваш IP-адрес в `ALLOWED_HOSTS`

## Шаг 4: Запуск сервера

### С использованием Docker
```powershell
# Запустите от имени администратора
Start-Process powershell -Verb RunAs -ArgumentList "-File start_tradehub.ps1"
```

### Без Docker
```powershell
# Запустите от имени администратора
Start-Process powershell -Verb RunAs -ArgumentList "-File start_tradehub_no_docker.ps1"
```

## Шаг 5: Проверка работоспособности

1. Откройте браузер на вашем компьютере и перейдите по адресу:
   - С Docker: http://localhost или http://127.0.0.1
   - Без Docker: http://localhost:8000 или http://127.0.0.1:8000

2. Проверьте, что сайт открывается и работает корректно

3. Проверьте доступ с другого устройства в локальной сети:
   - Откройте браузер на другом устройстве (телефон, планшет, компьютер)
   - Введите IP-адрес вашего сервера:
     - С Docker: http://ваш_ip
     - Без Docker: http://ваш_ip:8000

## Шаг 6: Обеспечение отказоустойчивости

Для обеспечения постоянной работы сервера:

1. Отключите спящий режим и гибернацию:
   ```powershell
   powercfg /change standby-timeout-ac 0
   powercfg /change hibernate-timeout-ac 0
   ```

2. Настройте автозапуск Docker при старте Windows (если используете Docker)

3. Создайте задачу в планировщике задач Windows для автоматического запуска скрипта после перезагрузки

## Проблемы и их решения

### Порт 80 уже занят
Это может произойти, если у вас уже запущен веб-сервер (IIS, Apache, Nginx).
```powershell
# Проверьте, какой процесс занимает порт 80
netstat -ano | findstr :80
# Затем остановите этот процесс или измените порт в docker-compose.yml
```

### Docker не запускается
Убедитесь, что служба Docker запущена и Hyper-V включен (для Windows Pro/Enterprise).

### Проблемы с базой данных (без Docker)
Проверьте, что сервис PostgreSQL запущен и пароль в `.env` файле совпадает с паролем, указанным при установке. 