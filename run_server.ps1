# Скрипт для запуска TradeHub
# Запускаем сервер напрямую через uvicorn

# Создание необходимых директорий
if (-not (Test-Path "./static")) { New-Item -Path "./static" -ItemType Directory | Out-Null }
if (-not (Test-Path "./media")) { New-Item -Path "./media" -ItemType Directory | Out-Null }
if (-not (Test-Path "./logs")) { New-Item -Path "./logs" -ItemType Directory | Out-Null }

# Открытие портов
netsh advfirewall firewall add rule name="TradeHub API" dir=in action=allow protocol=TCP localport=8000

# Получение IP-адреса
$ipAddress = (Get-NetIPAddress | Where-Object { $_.AddressFamily -eq "IPv4" -and $_.InterfaceAlias -match "Ethernet" }).IPAddress
Write-Host "Ваш IP-адрес: $ipAddress" -ForegroundColor Green
Write-Host "Сайт будет доступен по адресу: http://$ipAddress:8000" -ForegroundColor Green

# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 