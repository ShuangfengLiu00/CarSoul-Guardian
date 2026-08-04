"""Mock data generator / digital-twin simulator (TASK007).

Generates realistic sensor readings, trips, and fault logs for a vehicle,
and refreshes the real-time digital state. Powers the
``POST /api/vehicle/{id}/simulate`` endpoint and the seed-data population.

The generator is energy-type aware (fuel vs electric produce different
sensor families) and uses bounded random walks so the data looks natural.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models.fault_log import VehicleFaultLog
from app.models.sensor_data import VehicleSensorData
from app.models.trip import VehicleTrip
from app.models.vehicle import Vehicle
from app.schemas.vehicle_life import SimulationRequest, SimulationResult
from app.services import digital_state_service

# ---- Sensor blueprints by energy type ----
# Each entry: (sensor_type, unit, baseline, jitter, low_alert, high_alert)
_FUEL_SENSORS = [
    ("engine_temp", "℃", 92, 6, 70, 115),
    ("coolant_temp", "℃", 88, 5, 70, 110),
    ("oil_pressure", "kPa", 320, 40, 80, 500),
    ("rpm", "rpm", 800, 400, 0, 6500),
    ("fuel_level", "%", 60, 5, 0, 100),
    ("battery_voltage", "V", 14.2, 0.4, 11.5, 15.0),
    ("tire_pressure_fl", "bar", 2.4, 0.1, 1.8, 3.0),
    ("tire_pressure_fr", "bar", 2.4, 0.1, 1.8, 3.0),
    ("tire_pressure_rl", "bar", 2.3, 0.1, 1.8, 3.0),
    ("tire_pressure_rr", "bar", 2.3, 0.1, 1.8, 3.0),
    ("intake_air_temp", "℃", 30, 5, 0, 80),
    ("speed", "km/h", 0, 60, 0, 200),
]

_ELECTRIC_SENSORS = [
    ("battery_voltage", "V", 398, 8, 320, 420),
    ("battery_temp", "℃", 28, 5, 0, 50),
    ("battery_level", "%", 70, 6, 0, 100),
    ("motor_temp", "℃", 45, 10, 0, 120),
    ("tire_pressure_fl", "bar", 2.5, 0.1, 1.8, 3.0),
    ("tire_pressure_fr", "bar", 2.5, 0.1, 1.8, 3.0),
    ("tire_pressure_rl", "bar", 2.4, 0.1, 1.8, 3.0),
    ("tire_pressure_rr", "bar", 2.4, 0.1, 1.8, 3.0),
    ("cabin_temp", "℃", 23, 3, 0, 40),
    ("speed", "km/h", 0, 60, 0, 200),
    ("power_draw", "kW", 12, 18, 0, 150),
    ("regen_brake", "kW", 0, 20, 0, 50),
]

# ---- Fault templates ----
_FAULT_TEMPLATES = [
    ("P0420", "high", "三元催化效率低于阈值", "engine"),
    ("P0301", "high", "1缸偶发失火", "engine"),
    ("P0171", "medium", "燃油系统过稀", "engine"),
    ("P0442", "low", "EVAP系统小泄漏", "engine"),
    ("P0500", "high", "车速传感器信号异常", "electronics"),
    ("P0128", "medium", "节温器达到工作温度过慢", "engine"),
    ("C1201", "high", "ABS系统通信故障", "brake"),
    ("B1001", "medium", "安全气囊模块故障", "electronics"),
    ("U0100", "critical", "ECU通信丢失", "electronics"),
    ("P0AA6", "critical", "高压绝缘电阻过低", "battery"),
]

_ROAD_CONDITIONS = ["urban", "highway", "suburban", "mountain", "rural"]
_WEATHER = ["sunny", "cloudy", "rainy", "snowy", "foggy"]


def _sensor_blueprint(vehicle: Vehicle) -> list[tuple]:
    if vehicle.fuel_type in ("electric",):
        return _ELECTRIC_SENSORS
    if vehicle.fuel_type in ("hybrid", "plug_in_hybrid"):
        # Hybrid: merge unique sensor types from both sets.
        seen = set()
        merged = []
        for s in _ELECTRIC_SENSORS + _FUEL_SENSORS:
            if s[0] not in seen:
                merged.append(s)
                seen.add(s[0])
        return merged
    return _FUEL_SENSORS


def generate_sensor_data(
    db: Session,
    vehicle: Vehicle,
    points: int,
    days: int,
) -> int:
    """Generate `points` sensor readings spread over `days`."""
    blueprint = _sensor_blueprint(vehicle)
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    created = 0
    rng = random.Random(hash((vehicle.id, now.isoformat())) % 2**31)

    for i in range(points):
        # Spread timestamps across the window.
        ts = start + timedelta(
            seconds=rng.uniform(0, (now - start).total_seconds())
        )
        for sensor_type, unit, baseline, jitter, lo, hi in blueprint:
            value = round(rng.gauss(baseline, jitter), 2)
            value = max(lo, min(hi, value))
            meta = None
            if sensor_type.startswith("tire_pressure"):
                pos = sensor_type[-2:].upper()
                meta = {"position": pos}
            db.add(VehicleSensorData(
                vehicle_id=vehicle.id,
                sensor_type=sensor_type,
                sensor_value=value,
                unit=unit,
                meta=meta,
                created_at=ts,
            ))
            created += 1
    db.commit()
    return created


def generate_trips(
    db: Session,
    vehicle: Vehicle,
    count: int,
    days: int,
) -> int:
    """Generate `count` realistic trips over the last `days`."""
    now = datetime.utcnow()
    rng = random.Random(hash((vehicle.id, "trip")) % 2**31)
    is_ev = vehicle.fuel_type == "electric"
    created = 0

    for _ in range(count):
        days_ago = rng.uniform(0, days)
        start_time = now - timedelta(days=days_ago, hours=rng.uniform(0, 12))
        distance = round(rng.uniform(3, 80), 1)
        duration_min = max(5, int(distance / rng.uniform(25, 60) * 60))
        end_time = start_time + timedelta(minutes=duration_min)
        avg_speed = round(distance / (duration_min / 60), 1)
        max_speed = round(min(avg_speed * rng.uniform(1.2, 1.8), 180), 1)

        if is_ev:
            energy = round(distance * rng.uniform(0.13, 0.20), 2)  # kWh
        else:
            energy = round(distance * rng.uniform(0.06, 0.10), 2)  # L

        db.add(VehicleTrip(
            vehicle_id=vehicle.id,
            start_time=start_time,
            end_time=end_time,
            distance=distance,
            average_speed=avg_speed,
            max_speed=max_speed,
            energy_consumption=energy,
            road_condition=rng.choice(_ROAD_CONDITIONS),
            weather=rng.choice(_WEATHER),
            harsh_acceleration_count=rng.choices([0, 1, 2, 3], [0.6, 0.2, 0.1, 0.1])[0],
            harsh_braking_count=rng.choices([0, 1, 2], [0.7, 0.2, 0.1])[0],
            overspeed_count=rng.choices([0, 1], [0.85, 0.15])[0],
            start_location={"lat": 31.23 + rng.uniform(-0.1, 0.1),
                            "lng": 121.47 + rng.uniform(-0.1, 0.1)},
            end_location={"lat": 31.23 + rng.uniform(-0.1, 0.1),
                          "lng": 121.47 + rng.uniform(-0.1, 0.1)},
        ))
        created += 1
    db.commit()
    return created


def generate_faults(
    db: Session,
    vehicle: Vehicle,
    count: int,
) -> int:
    """Generate `count` fault log entries (mix of resolved and active)."""
    rng = random.Random(hash((vehicle.id, "fault")) % 2**31)
    now = datetime.utcnow()
    created = 0

    for _ in range(count):
        code, level, desc, system = rng.choice(_FAULT_TEMPLATES)
        days_ago = rng.uniform(1, 120)
        occur = now - timedelta(days=days_ago)
        # 70% resolved, 30% active
        if rng.random() < 0.7:
            status = "resolved"
            resolved = occur + timedelta(days=rng.uniform(1, 14))
        else:
            status = "active"
            resolved = None
        db.add(VehicleFaultLog(
            vehicle_id=vehicle.id,
            fault_code=code,
            fault_level=level,
            description=desc,
            system=system,
            repair_status=status,
            mileage=vehicle.mileage - rng.randint(0, max(1, vehicle.mileage)),
            occur_time=occur,
            resolved_time=resolved,
        ))
        created += 1
    db.commit()
    return created


def refresh_digital_state(db: Session, vehicle: Vehicle) -> bool:
    """Recompute the real-time digital state from latest sensor data."""
    blueprint = _sensor_blueprint(vehicle)
    rng = random.Random()
    now = datetime.utcnow()

    # Pull the most recent reading per sensor type.
    latest: dict[str, tuple[float, str]] = {}
    for sensor_type, unit, *_ in blueprint:
        row = select_sensor_latest(db, vehicle.id, sensor_type)
        if row:
            latest[sensor_type] = (row.sensor_value, row.unit)

    # Derive sub-system health (0-100) from sensor proximity to ideal.
    def _health_from(sensor_type: str, ideal: float, danger_delta: float) -> float:
        if sensor_type not in latest:
            return 85.0
        val = latest[sensor_type][0]
        deviation = abs(val - ideal) / danger_delta
        return max(40.0, min(100.0, 100.0 - deviation * 50))

    is_ev = vehicle.fuel_type == "electric"
    if is_ev:
        engine_health = _health_from("motor_temp", 45, 60)
        battery_health = _health_from("battery_temp", 28, 20)
        fuel_key = "battery_level"
    else:
        engine_health = _health_from("engine_temp", 92, 20)
        battery_health = _health_from("battery_voltage", 14.2, 2.5)
        fuel_key = "fuel_level"

    brake_health = _health_from("tire_pressure_fl", 2.4, 0.6)
    tire_health = (_health_from("tire_pressure_fl", 2.4, 0.6)
                   + _health_from("tire_pressure_fr", 2.4, 0.6)
                   + _health_from("tire_pressure_rl", 2.3, 0.6)
                   + _health_from("tire_pressure_rr", 2.3, 0.6)) / 4

    temp = latest.get("engine_temp" if not is_ev else "motor_temp", (None, ""))[0]
    fuel_level = latest.get(fuel_key, (None, ""))[0]

    digital_state_service.update_from_components(
        db,
        vehicle.id,
        engine=round(engine_health, 1),
        battery=round(battery_health, 1),
        brake=round(brake_health, 1),
        tire=round(tire_health, 1),
        body=92.0,
        electronics=90.0,
        temperature=temp,
        mileage=vehicle.mileage,
        fuel_level=fuel_level,
        location={"lat": 31.2304, "lng": 121.4737, "name": "上海"},
    )
    return True


def select_sensor_latest(db: Session, vehicle_id: int, sensor_type: str):
    """Return the latest sensor reading row for a type (lazy import to avoid cycle)."""
    from sqlalchemy import select as _select
    from app.models.sensor_data import VehicleSensorData as _VSD
    return db.scalar(
        _select(_VSD)
        .where(
            _VSD.vehicle_id == vehicle_id,
            _VSD.sensor_type == sensor_type,
        )
        .order_by(_VSD.created_at.desc())
        .limit(1)
    )


def run_simulation(
    db: Session, payload: SimulationRequest
) -> SimulationResult:
    """Run a full mock-data generation pass for a vehicle."""
    from sqlalchemy import select as _select
    vehicle = db.scalar(_select(Vehicle).where(Vehicle.id == payload.vehicle_id))
    if vehicle is None:
        return SimulationResult(
            vehicle_id=payload.vehicle_id,
            message="Vehicle not found",
        )

    sensor_n = generate_sensor_data(db, vehicle, payload.sensor_points, payload.days)
    trip_n = generate_trips(db, vehicle, payload.trip_count, payload.days)
    fault_n = generate_faults(db, vehicle, payload.fault_count)
    state_updated = False
    if payload.update_digital_state:
        state_updated = refresh_digital_state(db, vehicle)

    return SimulationResult(
        vehicle_id=vehicle.id,
        sensor_data_created=sensor_n,
        trips_created=trip_n,
        faults_created=fault_n,
        digital_state_updated=state_updated,
        message=(
            f"已生成 {sensor_n} 条传感器数据、{trip_n} 条行程、"
            f"{fault_n} 条故障记录"
            + ("，并刷新实时数字状态。" if state_updated else "。")
        ),
    )
