"""Guardian Kernel 层 — 审计账本与运行时基础设施。

分层依赖（C-08）：kernel 是最底层，被 agents / orchestrator 依赖，不反向。

模块：
  actionstore_guardian.py — Agent 审计事件落账（哈希链防篡改）
"""
