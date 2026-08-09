#!/usr/bin/env node
// kill-port.mjs — best-effort 杀掉占用某 TCP 端口的监听进程。
//
// 用途：作为 `npm run dev` 的前置，保证每次起 vite 前先清掉占用 5173 的
//       残留 vite，杜绝"改了 vite.config 但旧 dev server 仍在跑、读的是旧配置"的影子进程。
//
// 设计原则（关键的"绝不阻断启动"）：
//   - 始终以 exit 0 结束（best-effort）。找不到端口、杀不掉、命令不可用 → 只告警，不报错。
//   - 支持 --dry-run：只打印"会杀哪个 PID"，不动手（用于验证）。
//   - 跨平台：Windows 用 netstat + taskkill；*nix 用 lsof + kill。

import { execSync } from 'node:child_process';

const args = process.argv.slice(2);
const dryRun = args.includes('--dry-run');
const port = args.find((a) => /^\d+$/.test(a));

if (!port) {
  console.error('[kill-port] usage: node kill-port.mjs <port> [--dry-run]');
  process.exit(0); // 不是致命错误，predev 不应因此中断
}

function findPidOnPort(port) {
  try {
    if (process.platform === 'win32') {
      const out = execSync('netstat -ano', { encoding: 'utf8' });
      for (const line of out.split('\n')) {
        if (!line.includes('LISTENING')) continue;
        const cols = line.trim().split(/\s+/);
        const addr = cols[1] || '';
        if (addr.endsWith(`:${port}`)) {
          const pid = cols[cols.length - 1];
          if (/^\d+$/.test(pid)) return pid;
        }
      }
    } else {
      const out = execSync(`lsof -ti tcp:${port} -sTCP:LISTEN`, { encoding: 'utf8' });
      const pid = out.trim().split('\n')[0];
      if (/^\d+$/.test(pid)) return pid;
    }
  } catch {
    // netstat / lsof 不可用，或无匹配
  }
  return null;
}

const pid = findPidOnPort(port);
if (!pid) {
  console.log(`[kill-port] port ${port} is free, nothing to kill`);
  process.exit(0);
}

if (dryRun) {
  console.log(`[kill-port] (dry-run) would kill PID ${pid} holding port ${port}`);
  process.exit(0);
}

try {
  if (process.platform === 'win32') {
    execSync(`taskkill /PID ${pid} /F /T`, { stdio: 'ignore' });
  } else {
    execSync(`kill -9 ${pid}`, { stdio: 'ignore' });
  }
  console.log(`[kill-port] killed PID ${pid} on port ${port}`);
} catch {
  // 跨会话/权限不足时杀不掉（例如 WorkBuddy 沙箱早期独立会话拉起的孤儿进程），
  // 当前令牌枚举不到它，这里优雅忽略，绝不中断后续启动。
  console.warn(`[kill-port] could not kill PID ${pid} (likely owned by another session); ignoring`);
}
process.exit(0);
