# Скрипт для запуска TradeHub на Windows
# Автор: Claude 3.7 Sonnet

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Для запуска сервера требуются права администратора. Пожалуйста, запустите скрипт от имени администратора." -ForegroundColor Red
    exit
}

# Проверка наличия Docker
$dockerInstalled = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerInstalled) {
    Write-Host "Docker не установлен. Пожалуйста, установите Docker Desktop для Windows." -ForegroundColor Red
    exit
}

# Проверка статуса Docker
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker не запущен. Пожалуйста, запустите Docker Desktop." -ForegroundColor Red
    exit
}

# Открытие портов в брандмауэре Windows
Write-Host "Открытие портов 80 и 8000 в брандмауэре Windows..." -ForegroundColor Cyan
netsh advfirewall firewall add rule name="TradeHub HTTP" dir=in action=allow protocol=TCP localport=80 | Out-Null
netsh advfirewall firewall add rule name="TradeHub API" dir=in action=allow protocol=TCP localport=8000 | Out-Null

# Создание необходимых директорий, если они не существуют
Write-Host "Проверка и создание необходимых директорий..." -ForegroundColor Cyan
if (-not (Test-Path "./static")) { New-Item -Path "./static" -ItemType Directory | Out-Null }
if (-not (Test-Path "./media")) { New-Item -Path "./media" -ItemType Directory | Out-Null }
if (-not (Test-Path "./logs")) { New-Item -Path "./logs" -ItemType Directory | Out-Null }
if (-not (Test-Path "./logs/nginx")) { New-Item -Path "./logs/nginx" -ItemType Directory | Out-Null }

# Получение IP-адреса
$ipAddress = (Get-NetIPAddress | Where-Object { $_.AddressFamily -eq "IPv4" -and $_.InterfaceAlias -match "Ethernet" -and $_.PrefixOrigin -ne "WellKnown" }).IPAddress
Write-Host "Ваш IP-адрес: $ipAddress" -ForegroundColor Green
Write-Host "Сайт будет доступен по адресу: http://$ipAddress" -ForegroundColor Green

# Старт контейнеров
Write-Host "Запуск сервисов TradeHub..." -ForegroundColor Cyan
docker-compose up -d

Write-Host @"

TradeHub успешно запущен!
---------------------------
Для доступа к сайту с других устройств используйте адрес:
http://$ipAddress

Для мониторинга логов используйте команду:
docker-compose logs -f

Для остановки сервера используйте:
docker-compose down

"@ -ForegroundColor Green

# Проверка статуса контейнеров
docker-compose ps 