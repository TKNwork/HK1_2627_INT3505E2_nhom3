# Script chay toan bo he thong SmartSchedule bang 1 lenh duy nhat

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

# 1. Kiem tra docker compose va khoi dong Database
Write-Host ">>> Kiem tra va khoi dong Database..." -ForegroundColor Cyan
docker compose up -d --wait

# 2. Chay script quan ly toan bo 4 services
Write-Host ">>> Khoi chay 4 Microservices..." -ForegroundColor Green
if (Test-Path ".\.venv\Scripts\python.exe") {
    .\.venv\Scripts\python.exe scripts/run_all.py
} else {
    python scripts/run_all.py
}

