# Запуск контейнеров Docker
Write-Host "Запуск TradeHub через Docker Compose..." -ForegroundColor Green
docker-compose up -d

Write-Host "Сайт запущен и доступен по адресам:" -ForegroundColor Cyan
Write-Host "- Локально: http://localhost или http://127.0.0.1" -ForegroundColor Yellow
$ipAddress = (Get-NetIPAddress | Where-Object { $_.AddressFamily -eq "IPv4" -and $_.InterfaceAlias -match "Ethernet" }).IPAddress
Write-Host "- Из сети: http://$ipAddress" -ForegroundColor Yellow

Write-Host "Для просмотра логов используйте: docker-compose logs -f" -ForegroundColor Cyan
Write-Host "Для остановки: docker-compose down" -ForegroundColor Cyan 