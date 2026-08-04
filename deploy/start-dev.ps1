# CarSoul Guardian - 本地开发一键启动 (PowerShell)
# 用法: .\deploy\start-dev.ps1
# 需要: Python 3.11+, Node 20+

$ErrorActionPreference = "Stop"
$ROOT = Resolve-Path "$PSScriptRoot\.."

Write-Host "==== CarSoul Guardian Dev Starter ====" -ForegroundColor Cyan

# --- Backend ---
Write-Host "`n[1/4] 准备后端虚拟环境..." -ForegroundColor Yellow
$venv = Join-Path $ROOT "backend\.venv"
if (-not (Test-Path $venv)) {
    python -m venv $venv
}
$py = Join-Path $venv "Scripts\python.exe"
& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install -r (Join-Path $ROOT "backend\requirements.txt") | Out-Null

Write-Host "[2/4] 启动后端 FastAPI (http://localhost:8000)..." -ForegroundColor Yellow
Start-Process -FilePath $py -ArgumentList "-m","uvicorn","app.main:app","--reload","--port","8000" -WorkingDirectory (Join-Path $ROOT "backend")

# --- Frontend ---
Write-Host "`n[3/4] 安装前端依赖..." -ForegroundColor Yellow
Push-Location (Join-Path $ROOT "frontend")
if (-not (Test-Path "node_modules")) { npm install }
Write-Host "[4/4] 启动前端 Vite (http://localhost:5173)..." -ForegroundColor Yellow
Start-Process -FilePath "npm" -ArgumentList "run","dev"
Pop-Location

Write-Host "`n✔ 启动指令已发出。后端 http://localhost:8000  前端 http://localhost:5173" -ForegroundColor Green
Write-Host "API 文档: http://localhost:8000/docs" -ForegroundColor Green
