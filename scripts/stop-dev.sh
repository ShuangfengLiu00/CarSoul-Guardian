#!/usr/bin/env bash
# stop-dev.sh — 按 .devstack.pids 干净停止 dev-stack 拉起的服务
# 用法：bash scripts/stop-dev.sh
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDFILE="$ROOT/.devstack.pids"

if [ ! -f "$PIDFILE" ]; then
  echo "[stop-dev] no $PIDFILE (nothing running?)"
  exit 0
fi

echo "[stop-dev] stopping PIDs: $(tr '\n' ' ' < "$PIDFILE")"
while IFS= read -r pid; do
  [ -z "$pid" ] && continue
  taskkill /PID "$pid" /F /T >/dev/null 2>&1 || kill -9 "$pid" >/dev/null 2>&1 || true
done < "$PIDFILE"
rm -f "$PIDFILE"
echo "[stop-dev] done."
