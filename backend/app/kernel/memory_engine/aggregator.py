"""时间窗口聚合器 — 将离散因果事件聚合为时间窗口内的累计影响。

窗口：daily(24h) / weekly(7d) / monthly(30d) / lifetime(全生命周期)

聚合输出按 impact_target 分组，统计累计影响量、事件总数与因果事件数，
供五因子归因引擎（T7）与车况中心消费。causal_count 从每条记忆的
payload["causality_grade"] 读取（由 MemoryEngine.remember 写入）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # 仅用于类型标注，运行时避免循环导入
    from kernel.memory_engine.engine import MemoryEngine
    from kernel.memory_engine.models import VehicleMemory


class CausalAggregator:
    """时间窗口因果事件聚合器。

    Parameters
    ----------
    engine : MemoryEngine
        用于 recall 的记忆引擎实例。
    """

    WINDOWS: dict[str, int | None] = {
        "daily": 86_400,
        "weekly": 604_800,
        "monthly": 2_592_000,
        "lifetime": None,
    }

    def __init__(self, engine: "MemoryEngine") -> None:
        self._engine = engine

    def aggregate(self, vehicle_id: str, window: str = "monthly") -> dict[str, Any]:
        """聚合指定时间窗口内的因果影响。

        Returns
        -------
        dict
            {"window": str,
             "impacts": {target: {total_delta, event_count, causal_count}},
             "summary": str}
        """
        since = self._window_start(window)
        events: list["VehicleMemory"] = self._engine.recall(
            vehicle_id, since=since, limit=500
        )

        impacts: dict[str, dict[str, Any]] = {}
        for event in events:
            target = event.impact_target
            if not target:
                continue
            bucket = impacts.setdefault(
                target,
                {"total_delta": 0.0, "event_count": 0, "causal_count": 0},
            )
            bucket["total_delta"] += event.impact_delta
            bucket["event_count"] += 1
            payload = event.payload or {}
            if payload.get("causality_grade") == "causal":
                bucket["causal_count"] += 1

        return {
            "window": window,
            "impacts": impacts,
            "summary": self._build_summary(impacts),
        }

    def _window_start(self, window: str) -> datetime | None:
        """计算窗口起始时间，lifetime 返回 None（不设下界）。"""
        seconds = self.WINDOWS.get(window)
        if seconds is None:
            return None
        return datetime.now(timezone.utc) - timedelta(seconds=seconds)

    def _build_summary(self, impacts: dict[str, dict[str, Any]]) -> str:
        """构建聚合摘要文本。"""
        if not impacts:
            return "近窗内无因果事件记录。"
        parts: list[str] = []
        for target, data in impacts.items():
            delta = data["total_delta"]
            if delta > 0:
                direction = "退化"
            elif delta < 0:
                direction = "改善"
            else:
                direction = "无变化"
            parts.append(
                f"{target}: {direction} {abs(delta):.3f}"
                f" ({data['event_count']} 事件，{data['causal_count']} 因果)"
            )
        return "；".join(parts)
