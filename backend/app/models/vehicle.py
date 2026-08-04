"""Vehicle model — full digital-life archive (TASK007).

Extends the TASK006 placeholder with comprehensive vehicle profile fields:
powertrain, purchase/insurance/registration info, digital-twin linkage,
and ownership-friendly metadata.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Vehicle(Base):
    """A single vehicle — the root entity of the digital-life archive."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    # ---- Basic identity ----
    brand: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(64))
    year: Mapped[int] = mapped_column(Integer)
    vin: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    plate_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ---- Powertrain ----
    engine_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fuel_type: Mapped[str] = mapped_column(String(32), default="gasoline")
    # gasoline | diesel | hybrid | electric | plug_in_hybrid
    displacement: Mapped[float | None] = mapped_column(Float, nullable=True)  # L
    battery_capacity: Mapped[float | None] = mapped_column(Float, nullable=True)  # kWh

    # ---- Live status ----
    mileage: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="active")
    # active | inactive | sold | scrapped

    # ---- Purchase / dealer ----
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    dealer: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # ---- Insurance ----
    insurance_company: Mapped[str | None] = mapped_column(String(128), nullable=True)
    insurance_policy_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    insurance_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ---- Registration / inspection ----
    registration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    inspection_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ---- Digital twin ----
    twin_model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    twin_last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ---- Misc ----
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
