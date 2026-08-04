"""Vehicle service orders — after-sales closed-loop state machine (§3A.1).

Each order tracks the full lifecycle from Agent diagnosis → service order
creation → progress advancement → completion → user feedback. The state
machine is::

    created → booked → in_service → done → closed

Feedback (confirmed / false_alarm / no_event / partial) is collected when
the order reaches ``done`` or ``closed``, packaging the risk-feedback
concept as an "after-sales feedback" entry point.

All orders are persisted to the main database (not the in-memory
ActionStore audit ledger), so the full chain is queryable and traceable
from the UI.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database.base import Base

JSONType = SQLiteJSON().with_variant(JSON(), "postgresql")

# Valid status transitions (forward-only state machine).
STATUS_FLOW = ("created", "booked", "in_service", "done", "closed")

# Valid feedback types.
FEEDBACK_TYPES = ("confirmed", "false_alarm", "no_event", "partial")


class VehicleServiceOrder(Base):
    """A service order tracking the after-sales closed loop."""

    __tablename__ = "vehicle_service_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    # ---- Service details ----
    # roadside_assist | manufacturer_service | insurance_service | maintenance | diagnostic
    service_type: Mapped[str] = mapped_column(String(32))
    service_name: Mapped[str] = mapped_column(String(128))
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    reason: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---- Status machine: created → booked → in_service → done → closed ----
    status: Mapped[str] = mapped_column(String(16), default="created", index=True)

    # ---- Service provider / scheduling ----
    service_provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    estimated_response: Mapped[str | None] = mapped_column(String(64), nullable=True)
    booked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    in_service_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ---- Status history (JSON array of {status, timestamp, note}) ----
    status_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType, default=list
    )

    # ---- Cost ----
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ---- Feedback (售后反馈整理) ----
    # confirmed | false_alarm | no_event | partial
    feedback_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    feedback_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ---- Diagnosis reference (link to the Agent diagnosis that triggered this order) ----
    diagnosis_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
