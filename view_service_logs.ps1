# PowerShell скрипт для просмотра логов конкретного сервиса
# Автор: Разработчик TradeHub
# Дата: 2023-11-20

param (
    [Parameter(Mandatory=$false)]
    [string]$Service = ""
)

$services = @("web", "postgres", "redis", "celery", "nginx")

# Функция для выбора сервиса интерактивно
function Select-Service {
    Write-Host "Доступные сервисы:" -ForegroundColor Yellow
    for ($i = 0; $i -lt $services.Length; $i++) {
        Write-Host "$($i+1). $($services[$i])" -ForegroundColor Cyan
    }
    Write-Host "A. Все сервисы" -ForegroundColor Cyan
    
    $selection = Read-Host "Выберите номер сервиса или 'A' для всех"
    
    if ($selection -eq "A" -or $selection -eq "a") {
        return ""
    }
    
    if ([int]::TryParse($selection, [ref]$null)) {
        $index = [int]$selection - 1
        if ($index -ge 0 -and $index -lt $services.Length) {
            return $services[$index]
        }
    }
    
    Write-Host "Неверный выбор. Показываю логи всех сервисов." -ForegroundColor Red
    return ""
}

# Если сервис не указан, предложить выбор
if (-not $Service) {
    $Service = Select-Service
}

Write-Host "------------------------------------------------------------" -ForegroundColor Green
if ($Service) {
    Write-Host "Просмотр логов сервиса: $Service" -ForegroundColor Green
    Write-Host "Для остановки нажмите Ctrl+C" -ForegroundColor Yellow
    docker-compose logs --follow --tail=100 $Service
}
else {
    Write-Host "Просмотр логов всех сервисов" -ForegroundColor Green
    Write-Host "Для остановки нажмите Ctrl+C" -ForegroundColor Yellow
    docker-compose logs --follow --tail=50
} 