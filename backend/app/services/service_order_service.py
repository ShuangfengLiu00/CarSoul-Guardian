"""Service order service — after-sales closed-loop state machine (§3A.1).

Implements the full lifecycle:
  Agent 诊断 → 创建工单 → 进度推进 → 完成 → 用户反馈

The state machine is forward-only: ``created → booked → in_service →
done → closed``. Each transition appends to ``status_history`` so the
UI can render a progress timeline. Feedback is accepted when the order
reaches ``done`` or ``closed``.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.service_order import (
    FEEDBACK_TYPES,
    STATUS_FLOW,
    VehicleServiceOrder,
)
from app.schemas.service_order import (
    ServiceOrderCreate,
    ServiceOrderFeedback,
    ServiceOrderUpdate,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _next_status(current: str) -> str | None:
    """Return the next status in the forward-only flow, or None if at end."""
    idx = STATUS_FLOW.index(current)
    if idx < len(STATUS_FLOW) - 1:
        return STATUS_FLOW[idx + 1]
    return None


def _append_history(
    order: VehicleServiceOrder, status: str, note: str | None = None
) -> None:
    """Append a status-transition entry to the history JSON array."""
    entry: dict = {"status": status, "timestamp": _now().isoformat()}
    if note:
        entry["note"] = note
    history = list(order.status_history or [])
    history.append(entry)
    order.status_history = history


def list_orders(
    db: Session, vehicle_id: int, status: str | None = None
) -> list[VehicleServiceOrder]:
    """List service orders for a vehicle, optionally filtered by status."""
    stmt = (
        select(VehicleServiceOrder)
        .where(VehicleServiceOrder.vehicle_id == vehicle_id)
        .order_by(VehicleServiceOrder.created_at.desc())
    )
    if status:
        stmt = stmt.where(VehicleServiceOrder.status == status)
    return list(db.scalars(stmt).all())


def get_order(db: Session, order_id: int) -> VehicleServiceOrder | None:
    return db.get(VehicleServiceOrder, order_id)


def create_order(
    db: Session, vehicle_id: int, payload: ServiceOrderCreate
) -> VehicleServiceOrder:
    """Create a new service order (initial status = 'created')."""
    order = VehicleServiceOrder(
        **payload.model_dump(),
        vehicle_id=vehicle_id,
        status="created",
    )
    _append_history(order, "created", "工单由 Agent 诊断触发创建")
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def advance_order(
    db: Session, order_id: int, payload: ServiceOrderUpdate
) -> VehicleServiceOrder | None:
    """Advance the order to the next status (or a specific target status).

    Forward-only: the target status must be later in STATUS_FLOW than the
    current status. Setting optional fields (service_provider, cost, etc.)
    updates them in place.
    """
    order = db.get(VehicleServiceOrder, order_id)
    if order is None:
        return None

    current = order.status
    target = payload.status or _next_status(current)

    if target is None:
        # Already at 'closed' — nothing to advance.
        return order

    if target not in STATUS_FLOW:
        raise ValueError(f"Invalid status: {target}")

    if STATUS_FLOW.index(target) <= STATUS_FLOW.index(current):
        raise ValueError(
            f"Cannot move backwards or stay: {current} → {target}"
        )

    # Apply optional field updates.
    if payload.service_provider is not None:
        order.service_provider = payload.service_provider
    if payload.estimated_response is not None:
        order.estimated_response = payload.estimated_response
    if payload.cost is not None:
        order.cost = payload.cost

    # Set timestamp for the new status.
    now = _now()
    if target == "booked":
        order.booked_at = now
    elif target == "in_service":
        order.in_service_at = now
    elif target == "done":
        order.done_at = now
    elif target == "closed":
        order.closed_at = now

    order.status = target
    _append_history(order, target, payload.note)

    db.commit()
    db.refresh(order)
    return order


def submit_feedback(
    db: Session, order_id: int, payload: ServiceOrderFeedback
) -> VehicleServiceOrder | None:
    """Submit after-sales feedback for a completed (or closed) order.

    Feedback is only accepted when the order is in 'done' or 'closed'
    status — earlier stages are rejected.
    """
    order = db.get(VehicleServiceOrder, order_id)
    if order is None:
        return None

    if order.status not in ("done", "closed"):
        raise ValueError(
            f"Feedback only accepted for 'done' or 'closed' orders, "
            f"current status: {order.status}"
        )

    if payload.feedback_type not in FEEDBACK_TYPES:
        raise ValueError(f"Invalid feedback_type: {payload.feedback_type}")

    order.feedback_type = payload.feedback_type
    order.feedback_note = payload.feedback_note
    order.feedback_at = _now()

    _append_history(
        order,
        "feedback",
        f"售后反馈: {payload.feedback_type}"
        + (f" — {payload.feedback_note}" if payload.feedback_note else ""),
    )

    db.commit()
    db.refresh(order)
    return order


def delete_order(db: Session, order_id: int) -> bool:
    order = db.get(VehicleServiceOrder, order_id)
    if order is None:
        return False
    db.delete(order)
    db.commit()
    return True
