"""Session management + FastAPI dependency.

Exposes `SessionLocal` (factory) and `get_db()` (dependency injection).
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.database.connection import engine
from app.utils.logger import logger

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables and seed demo data (TASK007).

    Called once at startup. Creates the full vehicle digital-life archive
    schema, then populates a realistic demo dataset in development.
    """
    # Import here to avoid circular imports at module load.
    from app.database.base import Base  # noqa: WPS433
    from app.core.config import settings  # noqa: WPS433
    # Import all models so they register on Base.metadata.
    from app.models import (  # noqa: F401, WPS433
        User,
        Vehicle,
        VehicleAlert,
        VehicleDigitalState,
        VehicleDigitalTwin,
        VehicleDrivingBehavior,
        VehicleFaultLog,
        VehicleHealthItem,
        VehicleHealthSnapshot,
        VehicleLifecycleEvent,
        VehicleMaintenanceRecord,
        VehicleMaintenanceSchedule,
        VehicleOwnershipRecord,
        VehicleSensorData,
        VehicleTrip,
        RiskPrediction,
        VehicleServiceOrder,
        # TASK007-V2 digital life engine
        VehicleIdentity,
        VehicleLifeState,
        VehicleHealthMetrics,
        VehicleSensorStream,
        VehicleLifeEvent,
        VehicleMemory,
        DriverProfile,
        VehiclePrediction,
        VehicleSoulScoreHistory,
    )

    Base.metadata.create_all(bind=engine)

    # Seed demo data in development
    if settings.is_dev:
        try:
            from app.services.seed_data import seed_database  # noqa: WPS433
            db = SessionLocal()
            try:
                seed_database(db)
                logger.info("Seed data applied (development mode).")
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Seed data skipped: {}", exc)
