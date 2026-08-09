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

# 默认只起 postgres + redis + backend(:8001) + frontend(nginx :8080)。
# carModel 世界模型引擎在独立仓库，需先自行 build 镜像 carsoul/world-model，
# 再用 -WithCarModel 启用，否则 /docs、/openapi.json、/cockpit/ 会返回 502
# （nginx 用延迟 DNS 解析，carModel 缺席不影响主站启动）。
if ($args -contains "-WithCarModel") {
    Write-Host "启用 carModel 世界模型引擎 (:8000)..." -ForegroundColor Yellow
    docker compose --profile with-carmodel up --build
} else {
    docker compose up --build
}

Pop-Location

Write-Host "`n前端门户: http://localhost:8080   Guardian API: http://localhost:8001" -ForegroundColor Green
Write-Host "如需 carModel 的 /docs 与 /cockpit/，请用: .\deploy\docker-up.ps1 -WithCarModel" -ForegroundColor Green
