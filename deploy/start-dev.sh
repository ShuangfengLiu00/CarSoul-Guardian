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

echo "[2/4] 启动后端 FastAPI (http://localhost:8000)..."
(cd "$ROOT/backend" && "$VENV/bin/python" -m uvicorn app.main:app --reload --port 8000) &

# --- Frontend ---
echo -e "\n[3/4] 安装前端依赖..."
cd "$ROOT/frontend"
[ -d node_modules ] || npm install
echo "[4/4] 启动前端 Vite (http://localhost:5173)..."
npm run dev &
wait
