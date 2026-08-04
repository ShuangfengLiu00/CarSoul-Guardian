"""Vehicle ownership records — transfer history.

Tracks who owned the vehicle and when, including purchase/sale prices and
mileage at transfer.  The current owner is the record with `end_date IS NULL`.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class VehicleOwnershipRecord(Base):
    """An ownership period for a vehicle."""

    __tablename__ = "vehicle_ownership_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    owner_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # purchase | sale | gift | inheritance
    transfer_type: Mapped[str] = mapped_column(String(32), default="purchase")

    purchase_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    sale_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    mileage_at_transfer: Mapped[int | None] = mapped_column(Integer, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
