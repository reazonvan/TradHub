# PowerShell скрипт для запуска Docker с логированием
# Автор: Разработчик TradeHub
# Дата: 2023-11-20

Write-Host "Запуск TradeHub в режиме разработки с полным логированием" -ForegroundColor Green
Write-Host "------------------------------------------------------------" -ForegroundColor Green

# Очистка старых логов
if (Test-Path -Path "./logs/tradehub.log") {
    Write-Host "Очистка старых логов..." -ForegroundColor Yellow
    Clear-Content "./logs/tradehub.log"
}

# Запуск Docker Compose в фоновом режиме
Write-Host "Запуск Docker контейнеров..." -ForegroundColor Yellow
docker-compose up -d

# Небольшая пауза для запуска контейнеров
Start-Sleep -Seconds 5

# Вывод логов в реальном времени
Write-Host "`nЛоги приложения (Ctrl+C для остановки):" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------" -ForegroundColor Cyan

try {
    # Отслеживание логов всех сервисов
    docker-compose logs --follow --tail=50
}
finally {
    # При завершении скрипта (например, через Ctrl+C) спрашиваем про остановку контейнеров
    $confirmation = Read-Host "`nОстановить все контейнеры? (y/n)"
    if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
        Write-Host "Останавливаем контейнеры..." -ForegroundColor Yellow
        docker-compose down
        Write-Host "Контейнеры остановлены." -ForegroundColor Green
    }
    else {
        Write-Host "Контейнеры продолжают работать в фоновом режиме." -ForegroundColor Yellow
        Write-Host "Для остановки используйте команду: docker-compose down" -ForegroundColor Yellow
    }
} 