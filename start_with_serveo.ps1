# Скрипт для запуска TradeHub с туннелем Serveo
# Обеспечивает безопасный публичный доступ к приложению

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

# Создание необходимых директорий
Write-Host "Проверка и создание необходимых директорий..." -ForegroundColor Cyan
if (-not (Test-Path "./static")) { New-Item -Path "./static" -ItemType Directory | Out-Null }
if (-not (Test-Path "./media")) { New-Item -Path "./media" -ItemType Directory | Out-Null }
if (-not (Test-Path "./logs")) { New-Item -Path "./logs" -ItemType Directory | Out-Null }
if (-not (Test-Path "./logs/nginx")) { New-Item -Path "./logs/nginx" -ItemType Directory | Out-Null }
if (-not (Test-Path "./logs/serveo")) { New-Item -Path "./logs/serveo" -ItemType Directory | Out-Null }

# Создание файла .env, если он не существует
if (-not (Test-Path "./.env")) {
    Write-Host "Файл .env не найден. Создаю копию из .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    
    # Генерируем случайный ключ для API
    $randomKey = -join ((65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    (Get-Content .env) -replace "your-super-secret-key-change-this", $randomKey | Set-Content .env
    
    Write-Host "Файл .env создан. Пожалуйста, проверьте настройки в файле." -ForegroundColor Green
}

# Обновление CORS настроек для работы через Serveo
Write-Host "Настройка CORS для работы через Serveo..." -ForegroundColor Cyan
$envContent = Get-Content .env
if (-not ($envContent -match "ALLOWED_HOSTS=.*serveo\.net")) {
    $envContent = $envContent -replace "ALLOWED_HOSTS=(.*)", "ALLOWED_HOSTS=`$1,serveo.net,*.serveo.net"
    $envContent | Set-Content .env
    Write-Host "CORS настройки обновлены для работы с Serveo." -ForegroundColor Green
}

# Старт контейнеров
Write-Host "Запуск сервисов TradeHub..." -ForegroundColor Cyan
docker-compose up -d

# Ожидание запуска сервисов
Write-Host "Ожидание запуска сервисов..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host @"

TradeHub запущен локально!
---------------------------
Теперь создаем защищенный туннель Serveo...

"@ -ForegroundColor Green

# Функция для логирования соединений Serveo
function Start-ServeoTunnel {
    $logFile = "./logs/serveo/serveo_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    
    # Запуск SSH туннеля с логированием
    Write-Host "Создание туннеля Serveo. Лог записывается в $logFile" -ForegroundColor Cyan
    Write-Host "Нажмите Ctrl+C для остановки туннеля" -ForegroundColor Yellow
    
    # Запуск туннеля с перенаправлением с 80 (nginx) порта
    ssh -R 80:localhost:80 serveo.net 2>&1 | Tee-Object -FilePath $logFile
}

# Запуск туннеля с обработкой ошибок
try {
    Start-ServeoTunnel
}
catch {
    Write-Host "Ошибка при создании туннеля: $_" -ForegroundColor Red
}
finally {
    Write-Host "Туннель Serveo остановлен." -ForegroundColor Yellow
    Write-Host "Сервисы TradeHub продолжают работать локально." -ForegroundColor Cyan
    Write-Host "Для остановки сервисов используйте: docker-compose down" -ForegroundColor Cyan
} 