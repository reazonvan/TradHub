# PowerShell скрипт для мониторинга ошибок в логах
# Автор: Разработчик TradeHub
# Дата: 2023-11-20

# Функция для выделения цветом ошибок и предупреждений
function Format-LogLine {
    param (
        [string]$line
    )
    
    if ($line -match "ERROR|CRITICAL|FATAL|Exception|Error:") {
        Write-Host $line -ForegroundColor Red
    }
    elseif ($line -match "WARNING|WARN|Warning:") {
        Write-Host $line -ForegroundColor Yellow
    }
    elseif ($line -match "INFO|Information:") {
        Write-Host $line -ForegroundColor Green
    }
    elseif ($line -match "DEBUG|Trace:") {
        Write-Host $line -ForegroundColor Cyan
    }
    else {
        Write-Host $line
    }
}

Write-Host "Мониторинг ошибок TradeHub" -ForegroundColor Green
Write-Host "Для остановки нажмите Ctrl+C" -ForegroundColor Yellow
Write-Host "------------------------------------------------------------" -ForegroundColor Green

try {
    # Запускаем мониторинг логов с фильтрацией по ERROR, WARNING, Exception
    docker-compose logs --follow | ForEach-Object {
        $line = $_
        Format-LogLine $line
    }
}
catch {
    Write-Host "Мониторинг остановлен" -ForegroundColor Yellow
}
finally {
    Write-Host "Мониторинг завершен" -ForegroundColor Yellow
} 