# Скрипт для настройки автоматического запуска TradeHub при загрузке Windows
# Автор: Claude 3.7 Sonnet

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Для настройки автозапуска требуются права администратора. Пожалуйста, запустите скрипт от имени администратора." -ForegroundColor Red
    exit
}

# Получение текущего пути
$currentPath = Get-Location
$scriptPath = "$currentPath\start_tradehub.ps1"
$noDockScriptPath = "$currentPath\start_tradehub_no_docker.ps1"

# Проверка наличия скриптов запуска
if (-not (Test-Path $scriptPath)) {
    Write-Host "Скрипт start_tradehub.ps1 не найден в текущей директории." -ForegroundColor Red
    exit
}

# Проверка наличия Docker
$dockerInstalled = Get-Command docker -ErrorAction SilentlyContinue

# Выбор скрипта для автозапуска
$scriptToRun = ""
if ($dockerInstalled) {
    Write-Host "Docker обнаружен. Рекомендуется использовать вариант с Docker." -ForegroundColor Cyan
    $useDocker = Read-Host "Использовать Docker для автозапуска? (y/n, по умолчанию: y)"
    if ($useDocker -ne "n") {
        $scriptToRun = $scriptPath
        Write-Host "Выбран вариант с Docker." -ForegroundColor Green
    } else {
        $scriptToRun = $noDockScriptPath
        Write-Host "Выбран вариант без Docker." -ForegroundColor Yellow
    }
} else {
    Write-Host "Docker не обнаружен. Будет использован вариант без Docker." -ForegroundColor Yellow
    $scriptToRun = $noDockScriptPath
}

# Отключение спящего режима и гибернации для сервера
Write-Host "Отключение спящего режима и гибернации..." -ForegroundColor Cyan
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0

# Создание действия для планировщика задач
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptToRun`""

# Создание триггера для запуска при загрузке
$trigger = New-ScheduledTaskTrigger -AtStartup

# Настройка параметров запуска от имени администратора
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Создание задачи в планировщике
$taskName = "TradeHub_Autostart"
$description = "Автоматический запуск сервера TradeHub при загрузке компьютера"

# Удалить задачу, если она уже существует
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Создание новой задачи
$task = Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Description $description

Write-Host @"

Автозапуск для TradeHub успешно настроен!
-----------------------------------------
Задача "$taskName" будет запускаться автоматически при загрузке Windows.

Дополнительные настройки:
1. Спящий режим и гибернация отключены
2. Сервер будет запускаться с правами системы

Для проверки можно перезагрузить компьютер или запустить задачу вручную через планировщик задач Windows.

"@ -ForegroundColor Green 