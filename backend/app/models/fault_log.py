"""Vehicle fault log — the vehicle's "disease history".

Each row is a detected fault (OBD DTC code, severity, description, repair
status, occurrence time). Together with maintenance records this forms the
complete medical record of the vehicle's digital life.

Distinct from `VehicleAlert` (which is a user-facing notification) and
`RiskPrediction` (which is forward-looking): the fault log is the historical,
authoritative record of faults that actually occurred.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class VehicleFaultLog(Base):
    """A single fault occurrence on a vehicle."""

    __tablename__ = "vehicle_fault_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    # OBD-II DTC code, e.g. P0420, P0301, B1001, U0100
    fault_code: Mapped[str] = mapped_column(String(50), index=True)
    # low | medium | high | critical
    fault_level: Mapped[str] = mapped_column(String(20), default="medium", index=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # engine | transmission | brake | battery | tire | electronics | body | other
    system: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # active | diagnosing | repairing | resolved | ignored
    repair_status: Mapped[str] = mapped_column(
        String(30), default="active", index=True
    )

    # ---- Mileage at occurrence ----
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)

    occur_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
    resolved_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ---- Linked entities ----
    maintenance_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicle_maintenance_records.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
