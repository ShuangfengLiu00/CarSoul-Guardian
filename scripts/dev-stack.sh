#!/usr/bin/env bash
# dev-stack.sh — 受监管的全栈开发启动器（根治"孤儿进程 / 僵尸端口"类问题）
#
# 对应 C 阶段收口两项：
#   1. vite 启动前 kill-port：启动前先清掉 5173/8002/8000 上的残留监听（best-effort，失败忽略）
#      —— 杜绝"改了配置但旧 vite / 旧后端仍在跑"的影子进程。
#   2. :8001 僵尸根因预防：每个服务以 background 拉起，PID 写入 .devstack.pids；
#      前台 wait + trap(EXIT/INT/TERM) 在退出 / Ctrl+C 时按 PID 干净回收。
#      本会话内 spawned 的子进程一定能被回收，不会再遗留跨会话孤儿。
#
# 用法：
#   bash scripts/dev-stack.sh        # 启动并前台驻留，Ctrl+C 停止（按 PID 清理）
#   bash scripts/stop-dev.sh         # 单独停止（读 .devstack.pids）
#
# 注意：早期遗留的 :8001 僵尸（PID 15740）由 WorkBuddy 沙箱早期独立会话拉起，
# 当前交互会话枚举不到、taskkill 报 "not found"，无法从此处杀掉；它已不影响运行
# （vite 代理指向 :8002），只能随沙箱 / 宿主机重启清除。
# 本脚本保证【以后】不再产生此类孤儿。

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND="$ROOT/frontend"
CAR_MODEL_DIR="${CAR_MODEL_DIR:-$ROOT/../carModel}"
CARSOUL_PY="${CARSOUL_PY:-$HOME/.workbuddy/binaries/python/envs/default/Scripts/python.exe}"
PIDFILE="$ROOT/.devstack.pids"

echo "[dev-stack] clearing stale ports 5173 / 8002 / 8000 ..."
node "$FRONTEND/scripts/kill-port.mjs" 5173 || true
node "$FRONTEND/scripts/kill-port.mjs" 8002 || true
node "$FRONTEND/scripts/kill-port.mjs" 8000 || true

: > "$PIDFILE"

echo "[dev-stack] starting carModel :8000 ..."
( cd "$CAR_MODEL_DIR" && CARSOUL_PY="$CARSOUL_PY" bash start.sh ) &
echo $! >> "$PIDFILE"

echo "[dev-stack] starting Guardian backend :8002 ..."
( cd "$ROOT/backend" && ../envs/guardian/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002 ) &
echo $! >> "$PIDFILE"

echo "[dev-stack] starting vite :5173 ..."
( cd "$FRONTEND" && node node_modules/vite/bin/vite.js --host --port 5173 ) &
echo $! >> "$PIDFILE"

echo "[dev-stack] stack up. PIDs: $(tr '\n' ' ' < "$PIDFILE")"
echo "[dev-stack] Ctrl+C to stop (clean teardown by PID)."

cleanup() {
  echo
  echo "[dev-stack] tearing down ..."
  while IFS= read -r pid; do
    [ -z "$pid" ] && continue
    taskkill /PID "$pid" /F /T >/dev/null 2>&1 || kill -9 "$pid" >/dev/null 2>&1 || true
  done < "$PIDFILE"
  rm -f "$PIDFILE"
  echo "[dev-stack] stopped."
}
trap cleanup EXIT INT TERM
wait
