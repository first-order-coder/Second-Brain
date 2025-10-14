Param()

Write-Host "== Backend analysis ==" -ForegroundColor Cyan
Set-Location "$PSScriptRoot/..\backend"

# Create venv if missing
if (-not (Test-Path "venv/Scripts/python.exe")) {
  Write-Host "Creating virtualenv..." -ForegroundColor Yellow
  python -m venv venv
}

$python = "venv/\Scripts/\python.exe"
$pip = "venv/\Scripts/\pip.exe"

Write-Host "Installing analysis deps..." -ForegroundColor Yellow
& $pip install -q ruff mypy vulture

Write-Host "Ruff..." -ForegroundColor Yellow
& $python -m ruff check . | Out-String | Tee-Object -FilePath "..\docs\ruff_backend.txt"

Write-Host "Mypy..." -ForegroundColor Yellow
& $python -m mypy . | Out-String | Tee-Object -FilePath "..\docs\mypy_backend.txt"

Write-Host "Vulture..." -ForegroundColor Yellow
& $python -m vulture . --min-confidence 80 | Out-String | Tee-Object -FilePath "..\docs\vulture_backend.txt"

Write-Host "Done." -ForegroundColor Green
