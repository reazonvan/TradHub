# PowerShell скрипт для отображения только ошибок в логах
# Автор: Разработчик TradeHub
# Дата: 2023-11-20

Write-Host "Отображение только ошибок TradeHub" -ForegroundColor Red
Write-Host "Для остановки нажмите Ctrl+C" -ForegroundColor Yellow
Write-Host "------------------------------------------------------------" -ForegroundColor Red

try {
    # Фильтруем только ошибки из логов
    docker-compose logs --follow | Where-Object { $_ -match "ERROR|CRITICAL|FATAL|Exception|Error:" } | ForEach-Object {
        Write-Host $_ -ForegroundColor Red
    }
}
catch {
    Write-Host "Мониторинг остановлен" -ForegroundColor Yellow
}
finally {
    Write-Host "Мониторинг ошибок завершен" -ForegroundColor Yellow
} 