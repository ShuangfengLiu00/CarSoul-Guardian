#!/usr/bin/env bash
# CarSoul Guardian - 本地开发一键启动 (Linux/macOS)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "==== CarSoul Guardian Dev Starter ===="

# --- Backend ---
echo -e "\n[1/4] 准备后端虚拟环境..."
VENV="$ROOT/backend/.venv"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV/bin/python" -m pip install -r "$ROOT/backend/requirements.txt" >/dev/null

# 端口必须是 8001：frontend/vite.config.ts 的 dev proxy 把 /api 与 /health 转到
# :8001（:8000 已被 carModel 世界模型引擎占用）。写 8000 会导致前端起得来但所有
# 接口打不通。与 deploy/start-dev.ps1、Dockerfile.backend、deploy/nginx.conf
# 的 $guardian_upstream 保持一致。
echo "[2/4] 启动后端 FastAPI (http://localhost:8001)..."
(cd "$ROOT/backend" && "$VENV/bin/python" -m uvicorn app.main:app --reload --port 8001) &

# --- Frontend ---
echo -e "\n[3/4] 安装前端依赖..."
cd "$ROOT/frontend"
[ -d node_modules ] || npm install
echo "[4/4] 启动前端 Vite (http://localhost:5173)..."
npm run dev &
wait
