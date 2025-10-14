Param()

Write-Host "== Frontend analysis ==" -ForegroundColor Cyan
Set-Location "$PSScriptRoot/..\frontend"

# Install local deps if needed
if (-not (Test-Path "node_modules")) {
  Write-Host "Installing npm deps..." -ForegroundColor Yellow
  npm ci --no-audit --no-fund
}

Write-Host "Typecheck..." -ForegroundColor Yellow
npm run -s tsc -- --noEmit

Write-Host "ESLint..." -ForegroundColor Yellow
npm run -s lint

Write-Host "depcheck..." -ForegroundColor Yellow
npx -y depcheck --json | Out-File -Encoding utf8 "..\docs\depcheck_frontend.json"

Write-Host "ts-prune..." -ForegroundColor Yellow
npx -y ts-prune --ignore "*/__tests__/*,*/stories/*" | Out-File -Encoding utf8 "..\docs\ts_prune_frontend.txt"

Write-Host "Done." -ForegroundColor Green
