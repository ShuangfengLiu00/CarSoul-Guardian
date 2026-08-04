"""365-day lifecycle data generator — TASK007-V2.

Generates a complete 365-day digital life story for a new energy vehicle:

  - Daily health metrics (battery, motor, brake, tire, body, electronics)
  - Sensor stream readings (battery temp, motor speed, brake pressure, etc.)
  - Life events (first drive, travel, maintenance, accident, warning, recovery)
  - Vehicle memories (driving habits, preferences, events, emotions)
  - Driver profile evolution
  - AI predictions
  - VSS soul score history

The generator tells a coherent narrative: a new EV is purchased, goes
through a honeymoon period, develops wear patterns, experiences a
maintenance event, a minor warning, and eventually stabilizes — all
reflected in the VSS soul score trajectory.
"""
from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.digital_life import (
    DriverProfile,
    VehicleHealthMetrics,
    VehicleLifeEvent,
    VehicleMemory,
    VehiclePrediction,
    VehicleSensorStream,
    VehicleSoulScoreHistory,
)
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.digital_life import (
    VehicleHealthMetricsCreate,
    VehicleLifeEventCreate,
    VehicleMemoryCreate,
    VehiclePredictionCreate,
)
from app.services import soul_engine_service


# ===========================================================================
# Component health blueprints for an EV
# ===========================================================================

_COMPONENTS = [
    # (component, initial_health, daily_decay, temp_base, temp_jitter, wear_rate)
    ("battery", 98.0, 0.015, 28.0, 4.0, 0.02),
    ("motor", 97.0, 0.008, 45.0, 8.0, 0.015),
    ("brake", 96.0, 0.012, 35.0, 10.0, 0.025),
    ("tire", 95.0, 0.020, 30.0, 6.0, 0.035),
    ("body", 99.0, 0.003, 25.0, 3.0, 0.005),
    ("electronics", 98.0, 0.005, 30.0, 5.0, 0.008),
    ("cooling", 97.0, 0.010, 32.0, 7.0, 0.018),
]

# Sensor blueprints
_SENSORS = [
    ("battery_temperature", "℃", 28.0, 5.0),
    ("battery_level", "%", 72.0, 15.0),
    ("motor_speed", "rpm", 1200.0, 800.0),
    ("motor_temperature", "℃", 45.0, 12.0),
    ("brake_pressure", "%", 70.0, 20.0),
    ("tire_pressure_fl", "bar", 2.5, 0.15),
    ("tire_pressure_fr", "bar", 2.5, 0.15),
    ("tire_pressure_rl", "bar", 2.4, 0.15),
    ("tire_pressure_rr", "bar", 2.4, 0.15),
    ("cabin_temperature", "℃", 23.0, 4.0),
    ("speed", "km/h", 45.0, 30.0),
    ("power_draw", "kW", 12.0, 18.0),
]


# ===========================================================================
# Main entry point
# ===========================================================================

def generate_365_day_lifecycle(
    db: Session, vehicle_id: int, force: bool = False
) -> dict[str, Any]:
    """Generate a complete 365-day digital lifecycle for a vehicle.

    Returns a summary dict with counts of generated records.
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise ValueError(f"Vehicle {vehicle_id} not found")

    # Check if already has lifecycle data
    existing = db.scalar(
        select(VehicleLifeEvent)
        .where(VehicleLifeEvent.vehicle_id == vehicle_id)
        .limit(1)
    )
    if existing is not None and not force:
        return {
            "vehicle_id": vehicle_id,
            "message": "车辆已有生命周期数据，跳过生成。使用 force=true 可重新生成。",
            "skipped": True,
        }

    rng = random.Random(hash((vehicle_id, "lifecycle")) % 2**31)
    now = datetime.utcnow()
    birth = vehicle.purchase_date or (now - timedelta(days=365)).date()

    # Initialize digital life
    soul_engine_service.create_digital_life(db, vehicle_id)

    # Track cumulative state
    mileage = 0
    total_trips = 0
    total_distance = 0.0
    total_duration = 0
    total_harsh = 0
    harsh_events_list = []

    # Health tracking
    component_health = {c[0]: c[1] for c in _COMPONENTS}
    component_wear = {c[0]: 0.0 for c in _COMPONENTS}

    # Memory accumulation
    memories_created = 0
    events_created = 0
    predictions_created = 0
    sensors_created = 0
    metrics_created = 0

    # Generate day by day
    for day_offset in range(365):
        current_date = birth + timedelta(days=day_offset)
        current_dt = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=rng.uniform(6, 22))

        # Daily mileage (avg 35km/day, weekends more)
        is_weekend = current_date.weekday() >= 5
        daily_distance = rng.uniform(15, 50) * (1.3 if is_weekend else 1.0)
        if day_offset < 3:  # First few days: less driving
            daily_distance *= 0.5
        mileage += int(daily_distance)
        daily_trips = rng.choices([1, 2, 3, 4], [0.4, 0.35, 0.2, 0.05])[0]
        total_trips += daily_trips
        total_distance += daily_distance
        daily_duration = int(daily_distance / rng.uniform(25, 50) * 60)
        total_duration += daily_duration

        # Harsh events (occasional)
        harsh_today = rng.choices([0, 1, 2, 3], [0.7, 0.2, 0.08, 0.02])[0]
        total_harsh += harsh_today
        if harsh_today > 0:
            harsh_events_list.append((current_date, harsh_today))

        # ---- Generate health metrics (weekly) ----
        if day_offset % 7 == 0 or day_offset == 0:
            for comp, init_health, decay, temp_base, temp_jitter, wear_rate in _COMPONENTS:
                # Health degrades over time, with occasional recovery after maintenance
                days_elapsed = day_offset
                health = component_health[comp]

                # Apply natural decay
                health -= decay * 7  # weekly decay
                health = max(40.0, health)

                # Wear accumulates
                component_wear[comp] += wear_rate * 7 * (1 + harsh_today * 0.1)
                wear = min(100.0, component_wear[comp])

                # Temperature
                temp = rng.gauss(temp_base, temp_jitter)
                temp = max(10.0, min(80.0, temp))

                # Risk level
                if health < 60 or wear > 70:
                    risk = "high"
                elif health < 75 or wear > 50:
                    risk = "medium"
                else:
                    risk = "low"

                soul_engine_service.create_health_metric(db, vehicle_id, VehicleHealthMetricsCreate(
                    component=comp,
                    health_score=round(health, 1),
                    temperature=round(temp, 1),
                    wear_level=round(wear, 1),
                    risk_level=risk,
                ))
                # Use a timestamp in the past
                db.flush()
                # Update the record_time
                metric = db.scalar(
                    select(VehicleHealthMetrics)
                    .where(VehicleHealthMetrics.vehicle_id == vehicle_id)
                    .order_by(VehicleHealthMetrics.id.desc())
                    .limit(1)
                )
                if metric:
                    metric.record_time = current_dt

                component_health[comp] = health

                metrics_created += 1

        # ---- Generate sensor stream (daily, 2-4 readings) ----
        sensor_count = rng.randint(2, 4)
        for _ in range(sensor_count):
            for sensor_name, unit, baseline, jitter in _SENSORS:
                value = rng.gauss(baseline, jitter)
                # Clamp to reasonable ranges
                if "temperature" in sensor_name:
                    value = max(5.0, min(80.0, value))
                elif "level" in sensor_name or "pressure" in sensor_name:
                    value = max(0.0, min(100.0 if "%" in unit else 3.5, value))
                elif "speed" in sensor_name:
                    value = max(0.0, min(180.0, value))
                elif "power" in sensor_name:
                    value = max(0.0, min(150.0, value))

                reading = soul_engine_service.create_sensor_reading(
                    db, vehicle_id, sensor_name, round(value, 2), unit
                )
                reading.timestamp = current_dt + timedelta(
                    minutes=rng.randint(0, 1440)
                )
                sensors_created += 1

        # ---- Key life events ----
        _maybe_create_life_event(
            db, vehicle_id, day_offset, current_dt, mileage, rng
        )

    # ---- Create key memories ----
    memories_created += _create_lifecycle_memories(
        db, vehicle_id, birth, rng, total_trips, total_distance, total_harsh
    )

    # ---- Create predictions ----
    predictions_created += _create_predictions(
        db, vehicle_id, component_health, component_wear, mileage
    )

    # ---- Update driver profile ----
    profile = soul_engine_service.get_or_create_driver_profile(db, vehicle_id)
    avg_harsh_per_100km = (total_harsh / max(1, total_distance)) * 100
    profile.driver_style = "eco" if avg_harsh_per_100km < 3 else "balanced"
    profile.aggressive_score = round(min(100.0, 20.0 + avg_harsh_per_100km * 8), 1)
    profile.comfort_score = round(max(40.0, min(100.0, 100.0 - avg_harsh_per_100km * 5)), 1)
    profile.eco_score = round(85.0 - avg_harsh_per_100km * 2, 1)
    profile.total_trips = total_trips
    profile.total_distance = round(total_distance, 1)
    profile.total_duration = total_duration
    profile.total_harsh_events = total_harsh
    profile.preferred_speed_range = "30-60"
    profile.preferred_driving_time = "mixed"
    profile.preferred_road_type = "mixed"

    # ---- Update vehicle mileage ----
    vehicle.mileage = mileage
    db.flush()

    # ---- Compute and record VSS at several points ----
    # Record VSS snapshots at day 1, 30, 90, 180, 365
    for checkpoint_day in [1, 30, 90, 180, 365]:
        checkpoint_date = birth + timedelta(days=checkpoint_day)
        soul = soul_engine_service.compute_soul_score(db, vehicle_id)
        # Update the last soul score history record's timestamp
        last_history = db.scalar(
            select(VehicleSoulScoreHistory)
            .where(VehicleSoulScoreHistory.vehicle_id == vehicle_id)
            .order_by(VehicleSoulScoreHistory.id.desc())
            .limit(1)
        )
        if last_history:
            last_history.recorded_at = datetime.combine(checkpoint_date, datetime.min.time())

    # Final soul score computation
    soul_engine_service.update_life_state(db, vehicle_id)

    db.flush()

    return {
        "vehicle_id": vehicle_id,
        "message": f"已生成365天数字生命周期数据",
        "days": 365,
        "health_metrics": metrics_created,
        "sensor_readings": sensors_created,
        "life_events": events_created,
        "memories": memories_created,
        "predictions": predictions_created,
        "total_mileage": mileage,
        "total_trips": total_trips,
        "total_distance": round(total_distance, 1),
        "total_harsh_events": total_harsh,
        "skipped": False,
    }


# ===========================================================================
# Life event generator
# ===========================================================================

def _maybe_create_life_event(
    db: Session, vehicle_id: int, day: int, dt: datetime,
    mileage: int, rng: random.Random,
) -> int:
    """Create key life events at specific milestones."""
    events = [
        (0, "PURCHASE", "数字生命诞生", "车辆数字生命正式激活，开始记录每一次呼吸与心跳。", 10, "特斯拉上海体验中心", 0),
        (1, "FIRST_DRIVE", "首次驾驶", "第一次启动，电机轻声响应，一切就绪。", 9, "上海", 5),
        (7, "TRAVEL", "第一次通勤周", "完成了第一个完整通勤周，车辆开始学习主人的驾驶节奏。", 7, None, 180),
        (30, "MAINTENANCE", "首保", "一个月首保：系统全面检查，空调滤芯更换，软件版本更新。", 8, "特斯拉服务中心", 1200),
        (45, "TRAVEL", "周末郊游", "陪伴主人完成第一次长途出行，往返杭州西湖。", 7, "杭州", 320),
        (90, "WARNING", "胎压偏低提醒", "检测到右后轮胎压偏低，已提醒主人检查。", 6, None, 2800),
        (92, "RECOVERY", "胎压恢复", "主人为四个轮胎充气至标准值，胎压恢复正常。", 5, None, 2820),
        (120, "MAINTENANCE", "常规保养", "三个月常规保养：轮胎换位 + 制动系统检查 + 电池健康检测。", 7, "特斯拉服务中心", 4200),
        (150, "UPGRADE", "OTA升级", "软件版本更新至 v2025.12，新增能量回收增强和导航改进。", 6, None, 5300),
        (180, "TRAVEL", "国庆长途", "陪伴主人完成上海到北京的长途旅行，往返1200公里。", 9, "北京", 6800),
        (200, "ACCIDENT", "停车场剐蹭", "低速停车场剐蹭，左前保险杠轻微划痕，已补漆修复。", 7, "上海", 7200),
        (202, "RECOVERY", "补漆修复", "在特斯拉钣喷中心完成补漆，外观恢复如新。", 6, "特斯拉钣喷中心", 7220),
        (240, "WARNING", "刹车片磨损提醒", "检测到刹车片磨损达到60%，建议5000公里内更换。", 7, None, 8500),
        (245, "MAINTENANCE", "刹车片更换", "在服务中心更换前刹车片，制动性能恢复。", 8, "特斯拉服务中心", 8700),
        (270, "TRAVEL", "冬季出行", "陪伴主人完成冬季出行，车辆在低温环境下表现稳定。", 6, "南京", 9200),
        (300, "MAINTENANCE", "半年保养", "全面保养：轮胎检查 + 电池健康度检测 + 冷却液更换。", 8, "特斯拉服务中心", 10500),
        (330, "UPGRADE", "年度OTA", "年度大版本更新 v2026.1，新增FSD改进和能效优化。", 7, None, 11500),
        (360, "TRAVEL", "一周年纪念", "陪伴主人整整一年，行驶突破12000公里，数字生命持续成长。", 10, None, 12000),
    ]

    for event_day, etype, title, desc, importance, location, event_mileage in events:
        if day == event_day:
            soul_engine_service.create_life_event(db, vehicle_id, VehicleLifeEventCreate(
                event_type=etype,
                title=title,
                description=desc,
                importance=importance,
                mileage=event_mileage,
                location=location,
                event_time=dt,
            ))
            return 1

    # Random minor events
    if rng.random() < 0.02:  # 2% chance per day
        minor_events = [
            ("TRAVEL", "日常通勤", "完成日常通勤，路况良好。", 3),
            ("TRAVEL", "短途出行", "前往超市购物，短途行驶。", 2),
            ("WARNING", "能耗偏高", "检测到本次出行能耗略高于平均值。", 4),
            ("UPGRADE", "地图更新", "导航地图数据已更新。", 2),
        ]
        etype, title, desc, imp = rng.choice(minor_events)
        soul_engine_service.create_life_event(db, vehicle_id, VehicleLifeEventCreate(
            event_type=etype,
            title=title,
            description=desc,
            importance=imp,
            mileage=mileage,
            event_time=dt,
        ))
        return 1

    return 0


# ===========================================================================
# Memory generator
# ===========================================================================

def _create_lifecycle_memories(
    db: Session, vehicle_id: int, birth: date, rng: random.Random,
    total_trips: int, total_distance: float, total_harsh: int,
) -> int:
    """Create a rich set of vehicle memories."""
    memories = [
        # Habits
        ("habit", "主人习惯早上8点左右出门通勤，路线相对固定。", 0.3, 7, "sensor"),
        ("habit", "主人习惯晚上10点后减少驾驶，周末出行频率更高。", 0.2, 6, "sensor"),
        ("habit", "主人偏好使用能量回收模式，刹车使用频率较低。", 0.4, 6, "sensor"),
        ("habit", "主人习惯将空调设置在23℃，自动模式。", 0.1, 5, "sensor"),
        ("habit", "主人常去地点：公司、超市、父母家、健身房。", 0.3, 7, "sensor"),

        # Preferences
        ("preference", "主人喜欢听流行音乐，音量通常设置在30%。", 0.5, 5, "sensor"),
        ("preference", "主人偏好经济驾驶模式，偶尔切换运动模式。", 0.3, 6, "sensor"),
        ("preference", "主人习惯使用导航规划路线，避免拥堵路段。", 0.2, 5, "sensor"),

        # Events
        ("event", "第一次长途旅行去了杭州，全程高速续航表现优秀。", 0.6, 8, "system"),
        ("event", "国庆长途行驶1200公里，电池在快充站表现稳定。", 0.5, 8, "system"),
        ("event", "停车场剐蹭后，主人第一时间联系了服务中心。", -0.3, 7, "system"),
        ("event", "一周年纪念，陪伴主人行驶超过12000公里。", 0.7, 9, "system"),

        # Warnings
        ("warning", "右后轮胎压曾偏低至2.0bar，主人及时充气。", -0.2, 6, "sensor"),
        ("warning", "刹车片磨损到60%时系统提前预警，主人及时更换。", -0.1, 7, "sensor"),
        ("warning", "冬季低温环境下电池续航下降约15%，属正常范围。", -0.1, 5, "sensor"),

        # Recovery
        ("recovery", "胎压充气后恢复正常，系统确认无异常。", 0.3, 5, "system"),
        ("recovery", "刹车片更换后制动性能恢复至98%。", 0.4, 6, "system"),
        ("recovery", "补漆后外观恢复如新，主人很满意。", 0.5, 5, "system"),

        # Emotions
        ("emotion", "主人对车辆的智能化体验感到满意，经常向朋友推荐。", 0.7, 7, "agent"),
        ("emotion", "长途旅行后主人对续航表现感到放心。", 0.6, 6, "agent"),
        ("emotion", "剐蹭事件后主人有些心疼，但修复后恢复信心。", 0.1, 5, "agent"),

        # Context
        ("context", "车辆主要在上海地区使用，城市道路为主，偶尔高速。", 0.0, 6, "system"),
        ("context", "主人驾驶风格温和，急加速急刹车频率低于平均水平。", 0.3, 7, "sensor"),
        ("context", f"一年来累计行驶 {total_distance:.0f} 公里，完成 {total_trips} 次行程。", 0.4, 8, "system"),
        ("context", f"全年共记录 {total_harsh} 次激烈驾驶事件，驾驶安全度较高。", 0.3, 6, "system"),
    ]

    count = 0
    base_time = datetime.combine(birth, datetime.min.time())
    for i, (mtype, content, emotion, importance, source) in enumerate(memories):
        # Spread memories across the year
        mem_time = base_time + timedelta(days=i * 15 + rng.randint(0, 10))
        mem = soul_engine_service.create_memory(db, vehicle_id, VehicleMemoryCreate(
            memory_type=mtype,
            content=content,
            emotion_score=emotion,
            importance=importance,
            source=source,
        ))
        mem.created_time = mem_time
        count += 1

    return count


# ===========================================================================
# Prediction generator
# ===========================================================================

def _create_predictions(
    db: Session, vehicle_id: int,
    component_health: dict[str, float],
    component_wear: dict[str, float],
    mileage: int,
) -> int:
    """Create AI predictions based on current component health."""
    predictions = []

    # Battery prediction
    bat_health = component_health.get("battery", 90)
    bat_wear = component_wear.get("battery", 10)
    if bat_wear > 5:
        remaining_km = int((100 - bat_wear) * 200)
        predictions.append(VehiclePredictionCreate(
            target_component="battery",
            prediction=f"未来 {remaining_km} 公里内电池健康度将下降至 {bat_health - 5:.0f}，建议定期检测。",
            risk_level="low" if bat_wear < 20 else "medium",
            confidence=0.92,
            predicted_value=remaining_km,
            predicted_unit="km",
            root_cause=f"电池累计循环损耗 {bat_wear:.1f}%",
            suggestion="保持20%-80%充电区间可延长电池寿命。",
        ))

    # Brake prediction
    brk_health = component_health.get("brake", 85)
    brk_wear = component_wear.get("brake", 15)
    if brk_wear > 10:
        remaining_km = int((100 - brk_wear) * 150)
        predictions.append(VehiclePredictionCreate(
            target_component="brake",
            prediction=f"刹车片磨损已达 {brk_wear:.0f}%，预计剩余 {remaining_km} 公里。",
            risk_level="medium" if brk_wear > 40 else "low",
            confidence=0.88,
            predicted_value=remaining_km,
            predicted_unit="km",
            root_cause=f"刹车片磨损 {brk_wear:.1f}%",
            suggestion="下次保养时检查刹车片厚度，必要时更换。",
        ))

    # Tire prediction
    tire_health = component_health.get("tire", 80)
    tire_wear = component_wear.get("tire", 20)
    if tire_wear > 15:
        remaining_km = int((100 - tire_wear) * 100)
        predictions.append(VehiclePredictionCreate(
            target_component="tire",
            prediction=f"轮胎磨损 {tire_wear:.0f}%，预计 {remaining_km} 公里后达到更换标准。",
            risk_level="medium" if tire_wear > 50 else "low",
            confidence=0.85,
            predicted_value=remaining_km,
            predicted_unit="km",
            root_cause=f"轮胎磨损 {tire_wear:.1f}%",
            suggestion="定期进行轮胎换位可延长使用寿命。",
        ))

    # Motor prediction (always low risk for EV)
    predictions.append(VehiclePredictionCreate(
        target_component="motor",
        prediction="电机系统运行稳定，预计未来3000公里无异常风险。",
        risk_level="low",
        confidence=0.95,
        predicted_value=3000,
        predicted_unit="km",
        root_cause="电机温度和振动数据正常",
        suggestion="保持定期保养即可。",
    ))

    # Cooling prediction
    cool_health = component_health.get("cooling", 90)
    if cool_health < 85:
        predictions.append(VehiclePredictionCreate(
            target_component="cooling",
            prediction="冷却系统效率略有下降，建议下次保养时检查冷却液。",
            risk_level="low",
            confidence=0.80,
            predicted_value=90,
            predicted_unit="days",
            root_cause="冷却液使用时间较长",
            suggestion="更换冷却液可恢复系统效率。",
        ))

    count = 0
    for pred in predictions:
        soul_engine_service.create_prediction(db, vehicle_id, pred)
        count += 1

    return count
