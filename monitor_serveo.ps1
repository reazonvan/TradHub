# Скрипт для мониторинга туннеля Serveo
# Показывает информацию о подключениях и текущий URL

# Проверка существования директории для логов
if (-not (Test-Path "./logs/serveo")) {
    Write-Host "Директория для логов Serveo не найдена. Создаю..." -ForegroundColor Yellow
    New-Item -Path "./logs/serveo" -ItemType Directory | Out-Null
}

# Функция для получения текущего URL Serveo
function Get-ServeoUrl {
    $urlFile = "./logs/serveo/current_url.txt"
    if (Test-Path $urlFile) {
        $url = Get-Content $urlFile
        return $url
    }
    else {
        return "URL Serveo неизвестен. Запустите сервер с помощью start_with_serveo.ps1"
    }
}

# Функция для анализа логов Serveo
function Get-ServeoStat {
    $logDir = "./logs/serveo"
    $logFiles = Get-ChildItem -Path $logDir -Filter "serveo_*.log" | Sort-Object LastWriteTime -Descending
    
    if ($logFiles.Count -eq 0) {
        Write-Host "Логи Serveo не найдены. Запустите сервер с помощью start_with_serveo.ps1" -ForegroundColor Yellow
        return
    }
    
    $latestLog = $logFiles[0]
    $logContent = Get-Content $latestLog.FullName
    
    # Анализ логов
    $connections = $logContent | Where-Object { $_ -match "Forwarding HTTP traffic" }
    $errors = $logContent | Where-Object { $_ -match "error|failed|refused" }
    
    # Вывод статистики
    Write-Host "`nСтатистика туннеля Serveo" -ForegroundColor Cyan
    Write-Host "------------------------" -ForegroundColor Cyan
    Write-Host "Файл логов: $($latestLog.Name)" -ForegroundColor DarkGray
    Write-Host "Текущий URL: $(Get-ServeoUrl)" -ForegroundColor Green
    
    if ($connections.Count -gt 0) {
        Write-Host "`nПодключения:" -ForegroundColor Cyan
        $connections | ForEach-Object {
            Write-Host " - $_" -ForegroundColor White
        }
    }
    
    if ($errors.Count -gt 0) {
        Write-Host "`nОшибки:" -ForegroundColor Red
        $errors | ForEach-Object {
            Write-Host " - $_" -ForegroundColor Yellow
        }
    }
}

# Функция для отображения инструкций
function Show-Instructions {
    Write-Host @"
    
Мониторинг туннеля Serveo для TradeHub
======================================

Команды:
  1. Показать текущий URL туннеля
  2. Показать статистику подключений
  3. Мониторить логи туннеля в реальном времени
  4. Проверить статус сервисов
  5. Запустить туннель (если не запущен)
  Q. Выход

"@ -ForegroundColor Cyan
}

# Основной цикл скрипта
function Start-ServeoMonitor {
    Clear-Host
    Show-Instructions
    
    while ($true) {
        $choice = Read-Host "Выберите действие (1-5, Q для выхода)"
        
        switch ($choice) {
            "1" {
                Write-Host "`nТекущий URL Serveo: $(Get-ServeoUrl)" -ForegroundColor Green
            }
            "2" {
                Get-ServeoStat
            }
            "3" {
                $logFiles = Get-ChildItem -Path "./logs/serveo" -Filter "serveo_*.log" | Sort-Object LastWriteTime -Descending
                if ($logFiles.Count -eq 0) {
                    Write-Host "Логи Serveo не найдены." -ForegroundColor Yellow
                    continue
                }
                
                $latestLog = $logFiles[0]
                Write-Host "Мониторинг лога $($latestLog.Name) в реальном времени. Нажмите Ctrl+C для остановки." -ForegroundColor Yellow
                Get-Content $latestLog.FullName -Wait
            }
            "4" {
                Write-Host "`nСтатус сервисов:" -ForegroundColor Cyan
                docker-compose ps
            }
            "5" {
                $processes = Get-Process | Where-Object { $_.CommandLine -match "ssh -R.*serveo\.net" }
                if ($processes.Count -gt 0) {
                    Write-Host "Туннель Serveo уже запущен (PID: $($processes[0].Id))" -ForegroundColor Green
                }
                else {
                    Write-Host "Запуск туннеля Serveo..." -ForegroundColor Cyan
                    Start-Process powershell -ArgumentList "-File .\start_with_serveo.ps1" -NoNewWindow
                    Write-Host "Туннель запущен в отдельном окне." -ForegroundColor Green
                }
            }
            "Q" {
                Write-Host "Выход из монитора Serveo." -ForegroundColor Yellow
                return
            }
            default {
                Write-Host "Неизвестная команда. Пожалуйста, выберите действие из списка." -ForegroundColor Red
            }
        }
        
        Write-Host "`nНажмите любую клавишу для продолжения..." -ForegroundColor DarkGray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        Clear-Host
        Show-Instructions
    }
}

# Запуск монитора
Start-ServeoMonitor 