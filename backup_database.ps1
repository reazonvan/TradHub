# Скрипт для резервного копирования базы данных PostgreSQL в TradeHub
# Выполняет ежедневное резервное копирование и хранит архивы по дням недели

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Для создания резервных копий требуются права администратора. Пожалуйста, запустите скрипт от имени администратора." -ForegroundColor Red
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

# Загрузка переменных окружения из .env
function Get-EnvVar {
    param (
        [string]$name,
        [string]$default
    )
    
    if (Test-Path .env) {
        $envContent = Get-Content .env
        foreach ($line in $envContent) {
            if ($line -match "^$name=(.*)$") {
                return $matches[1]
            }
        }
    }
    
    return $default
}

# Получение данных для подключения к базе данных
$POSTGRES_USER = Get-EnvVar "POSTGRES_USER" "tradehub_user"
$POSTGRES_PASSWORD = Get-EnvVar "POSTGRES_PASSWORD" "strong_password"
$POSTGRES_DB = Get-EnvVar "POSTGRES_DB" "tradehub_db"

# Создание директории для бэкапов
$backupDir = "./backups"
if (-not (Test-Path $backupDir)) {
    New-Item -Path $backupDir -ItemType Directory | Out-Null
    Write-Host "Создана директория для резервных копий: $backupDir" -ForegroundColor Green
}

# Получение дня недели
$dayOfWeek = (Get-Date).DayOfWeek
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "$backupDir/tradehub_$dayOfWeek.sql"
$archiveFile = "$backupDir/tradehub_$timestamp.zip"

# Выполнение pg_dump в контейнере
Write-Host "Создание резервной копии базы данных $POSTGRES_DB..." -ForegroundColor Cyan
try {
    docker exec postgres pg_dump -U $POSTGRES_USER -d $POSTGRES_DB > $backupFile
    
    if (Test-Path $backupFile) {
        $backupSize = (Get-Item $backupFile).Length / 1MB
        Write-Host "Резервная копия успешно создана: $backupFile (размер: $([math]::Round($backupSize, 2)) МБ)" -ForegroundColor Green
        
        # Архивация копии
        Compress-Archive -Path $backupFile -DestinationPath $archiveFile -Force
        Write-Host "Архив резервной копии создан: $archiveFile" -ForegroundColor Green
        
        # Очистка старых архивов (оставляем последние 7)
        $oldBackups = Get-ChildItem -Path $backupDir -Filter "tradehub_*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 7
        foreach ($oldBackup in $oldBackups) {
            Remove-Item $oldBackup.FullName -Force
            Write-Host "Удален устаревший архив: $($oldBackup.Name)" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "Ошибка при создании резервной копии: файл не найден" -ForegroundColor Red
    }
}
catch {
    Write-Host "Ошибка при выполнении резервного копирования: $_" -ForegroundColor Red
}

# Функция для настройки автоматического выполнения задачи
function Set-BackupTask {
    param (
        [string]$taskName = "TradeHubBackup",
        [string]$interval = "Daily"
    )
    
    $scriptPath = Join-Path (Get-Location) "backup_database.ps1"
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$scriptPath`""
    
    # Настройка времени выполнения
    $trigger = $null
    switch ($interval) {
        "Daily" {
            $trigger = New-ScheduledTaskTrigger -Daily -At "03:00"
        }
        "Weekly" {
            $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "03:00"
        }
        "Hourly" {
            $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 9999)
        }
    }
    
    # Запуск с правами администратора
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    
    # Создание и регистрация задачи
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    
    # Проверяем существование задачи
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    
    if ($existingTask) {
        # Обновление существующей задачи
        Set-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings
        Write-Host "Задача резервного копирования '$taskName' успешно обновлена." -ForegroundColor Green
    }
    else {
        # Создание новой задачи
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Ежедневное резервное копирование базы данных TradeHub"
        Write-Host "Задача резервного копирования '$taskName' успешно создана." -ForegroundColor Green
    }
}

# Спрашиваем пользователя о создании расписания
$createSchedule = Read-Host "Добавить задачу для ежедневного резервного копирования? (y/n)"
if ($createSchedule -eq "y" -or $createSchedule -eq "Y") {
    $interval = Read-Host "Выберите интервал (Daily - ежедневно, Weekly - еженедельно, Hourly - ежечасно) [Daily]"
    if ([string]::IsNullOrEmpty($interval)) {
        $interval = "Daily"
    }
    
    # Установка задачи
    Set-BackupTask -interval $interval
} 