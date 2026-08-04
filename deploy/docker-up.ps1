# CarSoul Guardian - Docker 全栈一键启动 (PowerShell)
# 用法: .\deploy\docker-up.ps1
$ErrorActionPreference = "Stop"
$ROOT = Resolve-Path "$PSScriptRoot\.."
Write-Host "==== CarSoul Guardian Docker Compose ====" -ForegroundColor Cyan
# 复制 .env.example -> .env (若不存在)
$envFile = Join-Path $ROOT ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $ROOT ".env.example") $envFile
    Write-Host "已从 .env.example 创建 .env，请按需修改后重新执行。" -ForegroundColor Yellow
}
Push-Location $ROOT
docker compose up --build
Pop-Location
