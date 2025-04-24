# Скрипт для запуска TradeHub на Windows без Docker
# Автор: Claude 3.7 Sonnet

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Для запуска сервера требуются права администратора. Пожалуйста, запустите скрипт от имени администратора." -ForegroundColor Red
    exit
}

# Проверка наличия Python
$pythonInstalled = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonInstalled) {
    Write-Host "Python не установлен. Пожалуйста, установите Python 3.11 или выше." -ForegroundColor Red
    exit
}

# Проверка версии Python
$pythonVersion = python -c "import sys; print(sys.version_info.major, sys.version_info.minor)" | Out-String
$pythonVersion = $pythonVersion.Trim()
$major, $minor = $pythonVersion.Split(" ")
if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 11)) {
    Write-Host "Требуется Python 3.11 или выше. У вас установлен Python $major.$minor" -ForegroundColor Red
    exit
}

# Проверка наличия PostgreSQL
$pgInstalled = Get-Command psql -ErrorAction SilentlyContinue
if (-not $pgInstalled) {
    Write-Host "PostgreSQL не установлен. Пожалуйста, установите PostgreSQL 14 или выше." -ForegroundColor Yellow
    $installPg = Read-Host "Хотите продолжить без PostgreSQL? (y/n)"
    if ($installPg -ne "y") {
        exit
    }
}

# Проверка наличия Redis
$redisInstalled = Get-Command redis-server -ErrorAction SilentlyContinue
if (-not $redisInstalled) {
    Write-Host "Redis не установлен. Пожалуйста, установите Redis." -ForegroundColor Yellow
    $installRedis = Read-Host "Хотите продолжить без Redis? (y/n)"
    if ($installRedis -ne "y") {
        exit
    }
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

# Получение IP-адреса
$ipAddress = (Get-NetIPAddress | Where-Object { $_.AddressFamily -eq "IPv4" -and $_.InterfaceAlias -match "Ethernet" -and $_.PrefixOrigin -ne "WellKnown" }).IPAddress
Write-Host "Ваш IP-адрес: $ipAddress" -ForegroundColor Green
Write-Host "Сайт будет доступен по адресу: http://$ipAddress:8000" -ForegroundColor Green

# Установка зависимостей
Write-Host "Установка зависимостей Python..." -ForegroundColor Cyan
pip install -r requirements.txt

# Запуск сервера
Write-Host "Запуск сервера TradeHub..." -ForegroundColor Cyan
Start-Process python -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" -NoNewWindow

Write-Host @"

TradeHub успешно запущен!
---------------------------
Для доступа к сайту с других устройств используйте адрес:
http://$ipAddress:8000

Для остановки сервера нажмите Ctrl+C в окне консоли.

"@ -ForegroundColor Green 