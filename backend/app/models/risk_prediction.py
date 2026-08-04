"""Risk prediction records — the persistent backbone of the closed loop.

Every run of the five-sub-agent workflow produces one ``RiskPrediction``.
The record captures *what was predicted* (level / probability / ETA /
root cause / explanation / full trace) and, later, *what actually
happened* (``actual_outcome`` + ``accuracy``). Connecting the two is what
turns the forward pipeline into a true 风险预测闭环 (risk-prediction
closed loop): predict → alert → act → feedback → calibrate.

Lifecycle::

    open ──acknowledge──▶ acknowledged ──resolve──▶ resolved
      │                                                    ▲
      └────────────── feedback (outcome) ─────────────────┘
    expired  (ETA passed with no feedback)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database.base import Base

# Dialect-agnostic JSON so it works on both SQLite (dev) and PostgreSQL.
JSONType = SQLiteJSON().with_variant(JSON(), "postgresql")


class RiskPrediction(Base):
    """A single risk-prediction run and its eventual outcome."""

    __tablename__ = "risk_predictions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    # ---- trigger ----
    # patrol | user | alert | scheduled
    triggered_by: Mapped[str] = mapped_column(String(16), default="user", index=True)

    # ---- what the workflow predicted ----
    is_normal: Mapped[bool] = mapped_column(default=False)
    predicted_level: Mapped[str] = mapped_column(String(16), default="info", index=True)
    # info | warning | urgent
    predicted_probability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    predicted_eta_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    primary_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(String(256), nullable=True)
    trend: Mapped[str | None] = mapped_column(String(32), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    actions_hint: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    anomalies_count: Mapped[int] = mapped_column(Integer, default=0)

    # ---- full reasoning chain (replayable / auditable) ----
    trace_log: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONType, nullable=True
    )

    # ---- linked alert (generated when level >= warning) ----
    alert_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicle_alerts.id", ondelete="SET NULL"), nullable=True
    )

    # ---- prediction lifecycle ----
    # open | acknowledged | resolved | expired
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ---- the loop closure: actual outcome + accuracy ----
    # confirmed | false_alarm | no_event | partial | None (not yet fed back)
    actual_outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    outcome_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 0.0 – 1.0; computed when feedback is submitted
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
