# Скрипт для управления туннелем Serveo и связанными настройками
# Обеспечивает централизованное управление всеми компонентами туннеля

param (
    [switch]$start,
    [switch]$stop,
    [switch]$monitor,
    [switch]$backup,
    [switch]$security,
    [switch]$help
)

# Получение статуса Serveo
function Get-ServeoStatus {
    $processes = Get-Process | Where-Object { $_.CommandLine -match "ssh -R.*serveo\.net" }
    if ($processes.Count -gt 0) {
        return @{
            Running = $true
            PID = $processes[0].Id
            StartTime = $processes[0].StartTime
            Runtime = (Get-Date) - $processes[0].StartTime
        }
    }
    else {
        return @{
            Running = $false
        }
    }
}

# Получение текущего URL Serveo
function Get-ServeoUrl {
    $urlFile = "./logs/serveo/current_url.txt"
    if (Test-Path $urlFile) {
        $url = Get-Content $urlFile
        return $url
    }
    else {
        return "URL Serveo неизвестен"
    }
}

# Функция для отображения статуса всех сервисов
function Show-Status {
    Write-Host @"
    
TradeHub с туннелем Serveo - Статус
======================================
"@ -ForegroundColor Cyan
    
    # Проверка Docker
    Write-Host "`nПроверка Docker:" -ForegroundColor Cyan
    $dockerRunning = $false
    try {
        $dockerStatus = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host " - Docker запущен" -ForegroundColor Green
            $dockerRunning = $true
        }
        else {
            Write-Host " - Docker не запущен" -ForegroundColor Red
        }
    }
    catch {
        Write-Host " - Docker не установлен" -ForegroundColor Red
    }
    
    # Проверка сервисов Docker
    if ($dockerRunning) {
        Write-Host "`nСтатус контейнеров:" -ForegroundColor Cyan
        docker-compose ps --format "table {{.Name}}\t{{.Status}}"
    }
    
    # Проверка туннеля Serveo
    Write-Host "`nСтатус туннеля Serveo:" -ForegroundColor Cyan
    $serveoStatus = Get-ServeoStatus
    if ($serveoStatus.Running) {
        Write-Host " - Туннель запущен (PID: $($serveoStatus.PID))" -ForegroundColor Green
        Write-Host " - Запущен: $($serveoStatus.StartTime)" -ForegroundColor Green
        Write-Host " - Время работы: $($serveoStatus.Runtime.ToString('hh\:mm\:ss'))" -ForegroundColor Green
        Write-Host " - URL: $(Get-ServeoUrl)" -ForegroundColor Green
    }
    else {
        Write-Host " - Туннель не запущен" -ForegroundColor Yellow
    }
    
    # Проверка резервных копий
    Write-Host "`nСтатус резервных копий:" -ForegroundColor Cyan
    if (Test-Path "./backups") {
        $backups = Get-ChildItem -Path "./backups" -Filter "*.zip" | Sort-Object LastWriteTime -Descending
        if ($backups.Count -gt 0) {
            $latestBackup = $backups[0]
            Write-Host " - Последняя резервная копия: $($latestBackup.Name) ($(Get-Date $latestBackup.LastWriteTime -Format 'yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Green
            Write-Host " - Всего резервных копий: $($backups.Count)" -ForegroundColor Green
        }
        else {
            Write-Host " - Резервные копии не найдены" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host " - Директория для резервных копий не создана" -ForegroundColor Yellow
    }
    
    # Проверка файла белого списка IP
    Write-Host "`nСтатус безопасности:" -ForegroundColor Cyan
    if (Test-Path "./admin_ip_whitelist.txt") {
        $whitelistContent = Get-Content "./admin_ip_whitelist.txt" | Where-Object { $_ -match "^\d+\.\d+\.\d+\.\d+$" }
        Write-Host " - Белый список IP: настроен ($($whitelistContent.Count) адресов)" -ForegroundColor Green
    }
    else {
        Write-Host " - Белый список IP: не настроен" -ForegroundColor Yellow
    }
}

# Функция для отображения справки
function Show-Help {
    Write-Host @"
    
TradeHub с туннелем Serveo - Помощь
======================================

Использование: .\manage_serveo.ps1 [параметры]

Параметры:
  -start      Запустить все службы и туннель Serveo
  -stop       Остановить туннель Serveo
  -monitor    Мониторинг туннеля в реальном времени
  -backup     Создать резервную копию базы данных
  -security   Настроить параметры безопасности
  -help       Показать эту справку

Примеры:
  .\manage_serveo.ps1                    # Показать статус
  .\manage_serveo.ps1 -start             # Запустить все службы и туннель
  .\manage_serveo.ps1 -monitor           # Мониторинг туннеля в реальном времени
  .\manage_serveo.ps1 -backup            # Резервное копирование базы данных
  .\manage_serveo.ps1 -security          # Настройка безопасности
  
"@ -ForegroundColor Cyan
}

# Функция для настройки безопасности
function Configure-Security {
    Write-Host "`nНастройка безопасности для Serveo" -ForegroundColor Cyan
    Write-Host "----------------------------------" -ForegroundColor Cyan
    
    # Настройка файла белого списка IP
    Write-Host "`n1. Настройка белого списка IP для доступа к админке" -ForegroundColor Green
    
    if (-not (Test-Path "./admin_ip_whitelist.txt")) {
        Write-Host " - Файл белого списка IP не найден. Создание..." -ForegroundColor Yellow
        @"
# Белый список IP-адресов для доступа к административным функциям через Serveo
# Добавьте IP-адреса, с которых разрешен доступ, по одному на строку
# Это повышает безопасность при публичном доступе через туннель

# Локальные IP-адреса
127.0.0.1
192.168.0.1
192.168.1.1

# Добавьте свои публичные IP-адреса ниже
# xx.xx.xx.xx

# Примечание: Пустые строки и строки с комментариями (начинающиеся с #) игнорируются
"@ | Set-Content "./admin_ip_whitelist.txt"
    }
    
    $addIp = Read-Host "Добавить текущий публичный IP-адрес в белый список? (y/n)"
    if ($addIp -eq "y" -or $addIp -eq "Y") {
        try {
            Write-Host " - Получение вашего публичного IP-адреса..." -ForegroundColor Cyan
            $publicIp = (Invoke-WebRequest -Uri "https://api.ipify.org").Content
            
            if ($publicIp -match "^\d+\.\d+\.\d+\.\d+$") {
                $whitelist = Get-Content "./admin_ip_whitelist.txt"
                if (-not ($whitelist -contains $publicIp)) {
                    Add-Content -Path "./admin_ip_whitelist.txt" -Value $publicIp
                    Write-Host " - IP-адрес $publicIp успешно добавлен в белый список" -ForegroundColor Green
                }
                else {
                    Write-Host " - IP-адрес $publicIp уже есть в белом списке" -ForegroundColor Yellow
                }
            }
            else {
                Write-Host " - Не удалось получить корректный IP-адрес" -ForegroundColor Red
            }
        }
        catch {
            Write-Host " - Ошибка при получении публичного IP-адреса: $_" -ForegroundColor Red
        }
    }
    
    # Дополнительные настройки безопасности
    Write-Host "`n2. Дополнительные настройки безопасности" -ForegroundColor Green
    
    $enableSecurity = Read-Host "Включить дополнительные меры безопасности для Serveo? (y/n)"
    if ($enableSecurity -eq "y" -or $enableSecurity -eq "Y") {
        # Проверка наличия переменных окружения
        if (Test-Path "./.env") {
            $envContent = Get-Content "./.env"
            
            # Установка безопасных cookie
            if (-not ($envContent -match "COOKIE_SECURE=True")) {
                $envContent = $envContent -replace "COOKIE_SECURE=False", "COOKIE_SECURE=True"
                $envContent | Set-Content "./.env"
                Write-Host " - Безопасные cookie включены" -ForegroundColor Green
            }
            
            # Уменьшение времени жизни токена для сессий через Serveo
            if (-not ($envContent -match "ACCESS_TOKEN_EXPIRE_MINUTES=30")) {
                $envContent = $envContent -replace "ACCESS_TOKEN_EXPIRE_MINUTES=\d+", "ACCESS_TOKEN_EXPIRE_MINUTES=30"
                $envContent | Set-Content "./.env"
                Write-Host " - Время жизни токена уменьшено для повышения безопасности" -ForegroundColor Green
            }
        }
    }
    
    Write-Host "`nНастройка безопасности завершена." -ForegroundColor Green
}

# Основная логика скрипта
if ($help -or ($args.Count -eq 0 -and -not $start -and -not $stop -and -not $monitor -and -not $backup -and -not $security)) {
    if ($help) {
        Show-Help
    } else {
        Show-Status
    }
} else {
    # Обработка параметров
    if ($start) {
        # Запуск всех служб и туннеля
        Write-Host "Запуск всех служб и туннеля Serveo..." -ForegroundColor Cyan
        # Используем скрипт start_with_serveo.ps1
        & .\start_with_serveo.ps1
    }
    
    if ($stop) {
        # Остановка туннеля
        Write-Host "Остановка туннеля Serveo..." -ForegroundColor Cyan
        $serveoStatus = Get-ServeoStatus
        if ($serveoStatus.Running) {
            Stop-Process -Id $serveoStatus.PID -Force
            Write-Host "Туннель Serveo остановлен (PID: $($serveoStatus.PID))" -ForegroundColor Green
        } else {
            Write-Host "Туннель Serveo не запущен" -ForegroundColor Yellow
        }
    }
    
    if ($monitor) {
        # Мониторинг туннеля
        Write-Host "Запуск мониторинга туннеля Serveo..." -ForegroundColor Cyan
        & .\monitor_serveo.ps1
    }
    
    if ($backup) {
        # Создание резервной копии
        Write-Host "Создание резервной копии базы данных..." -ForegroundColor Cyan
        & .\backup_database.ps1
    }
    
    if ($security) {
        # Настройка безопасности
        Configure-Security
    }
} 