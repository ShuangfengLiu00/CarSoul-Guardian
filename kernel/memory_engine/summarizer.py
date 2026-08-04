"""Memory summariser — produces agent-ready natural-language summaries.

This is the *interpretation* layer that turns raw memory records into
the kind of natural-language context an agent can cite in a consultation:

    "您 2026 年 8 月快充频次上升 40%，与当前电池温升相关"

The summariser works in three stages:

  1. **Aggregate** — group memories by impact_target and event_type,
     compute monthly counts and cumulative impact deltas.
  2. **Detect** — for each event type, compare the recent 30-day window
     against the previous 30-day window to find trends (↑/↓ X%).
  3. **Correlate** — when two topics co-occur in the same time window
     (e.g. ``battery_stress`` + ``temperature_anomaly``), surface the
     correlation as a causal hint.

The output is Chinese text, truncated to a token budget
(~2 Chinese chars per token).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from kernel.memory_engine.models import MemorySummary, VehicleMemory


# ------------------------------------------------------------------ #
#  Topic display names (Chinese)
# ------------------------------------------------------------------ #
_TOPIC_LABELS: dict[str, str] = {
    "battery_stress": "电池应力",
    "battery_health": "电池健康",
    "motor_wear": "电机磨损",
    "brake_safety": "制动安全",
    "tire_safety": "轮胎安全",
    "suspension_comfort": "悬挂舒适度",
    "temperature_anomaly": "温度异常",
    "cooling_system": "冷却系统",
    "charging_behavior": "充电行为",
    "driving_style": "驾驶风格",
}

# Correlations: if both topics appear in the same month, hint a causal link.
# (topic_a, topic_b) → hint text
_CORRELATIONS: dict[tuple[str, str], str] = {
    ("charging_behavior", "battery_stress"): "快充频次变化与电池应力相关",
    ("battery_stress", "temperature_anomaly"): "电池应力与温度异常相关",
    ("cooling_system", "temperature_anomaly"): "冷却系统问题导致温度异常",
    ("driving_style", "motor_wear"): "驾驶风格影响电机磨损",
    ("driving_style", "brake_safety"): "驾驶风格影响制动安全",
    ("charging_behavior", "battery_health"): "充电行为影响电池健康",
}


class Summarizer:
    """Produces token-budgeted natural-language summaries from memories."""

    def summarize(
        self,
        vehicle_id: str,
        memories: list[VehicleMemory],
        topics: list[str],
        token_budget: int = 500,
    ) -> MemorySummary:
        """Build a :class:`MemorySummary` from raw memory records.

        Parameters
        ----------
        vehicle_id : str
            The vehicle being summarised.
        memories : list[VehicleMemory]
            Raw memory records (already filtered to the relevant time
            window and vehicle).
        topics : list[str]
            Distinct impact_target values for the vehicle.
        token_budget : int
            Approximate max tokens (~2 Chinese chars per token).
        """
        if not memories:
            return MemorySummary(
                vehicle_id=vehicle_id,
                text="暂无车辆历史记忆。",
                memory_count=0,
                topics=[],
                token_estimate=5,
                truncated=False,
            )

        # ---- 1. Aggregate by topic + month ----
        topic_stats = self._aggregate_by_topic(memories)
        monthly_stats = self._aggregate_by_month(memories)
        trends = self._detect_trends(memories)
        correlations = self._detect_correlations(monthly_stats)

        # ---- 2. Build natural-language sections ----
        sections: list[str] = []
        sections.append(self._format_overview(memories, topics))
        sections.append(self._format_topic_summary(topic_stats))
        if trends:
            sections.append(self._format_trends(trends))
        if correlations:
            sections.append(self._format_correlations(correlations))
        sections.append(self._format_recent_events(memories))

        full_text = "\n".join(sections)

        # ---- 3. Truncate to token budget ----
        char_budget = token_budget * 2  # ~2 Chinese chars per token
        truncated = False
        if len(full_text) > char_budget:
            full_text = full_text[:char_budget - 3] + "…"
            truncated = True

        token_estimate = len(full_text) // 2

        return MemorySummary(
            vehicle_id=vehicle_id,
            text=full_text,
            memory_count=len(memories),
            topics=topics,
            token_estimate=token_estimate,
            truncated=truncated,
        )

    # ------------------------------------------------------------------ #
    #  Aggregation
    # ------------------------------------------------------------------ #
    def _aggregate_by_topic(
        self, memories: list[VehicleMemory]
    ) -> dict[str, dict[str, Any]]:
        """Group memories by impact_target, compute stats per topic."""
        groups: dict[str, list[VehicleMemory]] = defaultdict(list)
        for m in memories:
            if m.impact_target:
                groups[m.impact_target].append(m)

        stats: dict[str, dict[str, Any]] = {}
        for topic, group in groups.items():
            total_delta = sum(m.impact_delta for m in group)
            avg_confidence = sum(m.confidence for m in group) / len(group)
            event_types = sorted({m.event_type for m in group})
            stats[topic] = {
                "count": len(group),
                "total_delta": round(total_delta, 3),
                "avg_confidence": round(avg_confidence, 2),
                "event_types": event_types,
                "label": _TOPIC_LABELS.get(topic, topic),
                "first_at": min(m.occurred_at for m in group),
                "last_at": max(m.occurred_at for m in group),
            }
        return stats

    def _aggregate_by_month(
        self, memories: list[VehicleMemory]
    ) -> dict[str, dict[str, list[VehicleMemory]]]:
        """Group memories by {year-month: {topic: [memories]}}."""
        monthly: dict[str, dict[str, list[VehicleMemory]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for m in memories:
            if m.impact_target:
                key = m.occurred_at.strftime("%Y-%m")
                monthly[key][m.impact_target].append(m)
        return monthly

    # ------------------------------------------------------------------ #
    #  Trend detection
    # ------------------------------------------------------------------ #
    def _detect_trends(
        self, memories: list[VehicleMemory]
    ) -> list[dict[str, Any]]:
        """Detect trends by comparing recent 30 days vs previous 30 days.

        Returns a list of trend dicts:
            {event_type, recent_count, previous_count, change_pct, direction}
        """
        now = datetime.now(timezone.utc)
        recent_start = now - timedelta(days=30)
        previous_start = now - timedelta(days=60)

        recent: dict[str, int] = defaultdict(int)
        previous: dict[str, int] = defaultdict(int)

        for m in memories:
            if m.occurred_at >= recent_start:
                recent[m.event_type] += 1
            elif m.occurred_at >= previous_start:
                previous[m.event_type] += 1

        trends: list[dict[str, Any]] = []
        all_types = set(recent.keys()) | set(previous.keys())
        for et in sorted(all_types):
            r = recent.get(et, 0)
            p = previous.get(et, 0)
            if p == 0:
                if r > 0:
                    trends.append({
                        "event_type": et, "recent": r, "previous": p,
                        "change_pct": None, "direction": "new",
                    })
                continue
            change = (r - p) / p
            if abs(change) < 0.1:  # less than 10% change is not a trend
                continue
            trends.append({
                "event_type": et, "recent": r, "previous": p,
                "change_pct": round(change, 2),
                "direction": "up" if change > 0 else "down",
            })
        return trends

    # ------------------------------------------------------------------ #
    #  Correlation detection
    # ------------------------------------------------------------------ #
    def _detect_correlations(
        self, monthly_stats: dict[str, dict[str, list[VehicleMemory]]]
    ) -> list[str]:
        """Find co-occurring topics in the same month."""
        hints: list[str] = []
        seen: set[tuple[str, str]] = set()

        for month, topic_groups in monthly_stats.items():
            active_topics = set(topic_groups.keys())
            for t1 in active_topics:
                for t2 in active_topics:
                    if t1 >= t2:
                        continue
                    key = (t1, t2) if t1 < t2 else (t2, t1)
                    if key in seen:
                        continue
                    hint = _CORRELATIONS.get(key) or _CORRELATIONS.get(
                        (key[1], key[0])
                    )
                    if hint:
                        hints.append(f"[{month}] {hint}")
                        seen.add(key)
        return hints

    # ------------------------------------------------------------------ #
    #  Formatting
    # ------------------------------------------------------------------ #
    def _format_overview(
        self, memories: list[VehicleMemory], topics: list[str]
    ) -> str:
        """Format the overview line."""
        time_span = (
            max(m.occurred_at for m in memories).strftime("%Y-%m")
            if memories
            else "N/A"
        )
        topic_labels = [
            _TOPIC_LABELS.get(t, t) for t in topics
        ] if topics else ["无"]
        return (
            f"【车辆记忆概览】共 {len(memories)} 条记忆，"
            f"覆盖 {len(topics)} 个影响维度"
            f"（{'、'.join(topic_labels)}），"
            f"最近活动：{time_span}。"
        )

    def _format_topic_summary(
        self, topic_stats: dict[str, dict[str, Any]]
    ) -> str:
        """Format per-topic statistics."""
        if not topic_stats:
            return ""
        lines = ["【影响维度明细】"]
        for topic, stats in sorted(
            topic_stats.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            delta_str = (
                f"累计影响 {'+' if stats['total_delta'] >= 0 else ''}"
                f"{stats['total_delta']}"
            )
            lines.append(
                f"  · {stats['label']}（{topic}）："
                f"{stats['count']} 次事件，{delta_str}，"
                f"置信度 {stats['avg_confidence']}，"
                f"事件类型：{', '.join(stats['event_types'][:3])}"
            )
        return "\n".join(lines)

    def _format_trends(self, trends: list[dict[str, Any]]) -> str:
        """Format detected trends."""
        lines = ["【近期趋势】"]
        for t in trends:
            et = t["event_type"]
            if t["direction"] == "new":
                lines.append(f"  · {et}：近 30 天新增 {t['recent']} 次（此前无记录）")
            elif t["direction"] == "up":
                pct = int(t["change_pct"] * 100)
                lines.append(
                    f"  · {et}：近 30 天 {t['recent']} 次，"
                    f"较上期上升 {pct}%"
                )
            else:
                pct = int(abs(t["change_pct"]) * 100)
                lines.append(
                    f"  · {et}：近 30 天 {t['recent']} 次，"
                    f"较上期下降 {pct}%"
                )
        return "\n".join(lines)

    def _format_correlations(self, correlations: list[str]) -> str:
        """Format detected correlations."""
        if not correlations:
            return ""
        lines = ["【关联分析】"]
        for c in correlations[:5]:  # cap at 5 to save space
            lines.append(f"  · {c}")
        return "\n".join(lines)

    def _format_recent_events(self, memories: list[VehicleMemory]) -> str:
        """Format the 3 most recent events."""
        recent = sorted(memories, key=lambda m: m.occurred_at, reverse=True)[:3]
        if not recent:
            return ""
        lines = ["【最近事件】"]
        for m in recent:
            date_str = m.occurred_at.strftime("%Y-%m-%d")
            impact_str = ""
            if m.impact_target:
                label = _TOPIC_LABELS.get(m.impact_target, m.impact_target)
                impact_str = f"，影响：{label}({'+' if m.impact_delta >= 0 else ''}{m.impact_delta})"
            lines.append(f"  · [{date_str}] {m.event_type}{impact_str}")
        return "\n".join(lines)
