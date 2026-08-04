"""Seed data — populates a realistic vehicle digital-life archive on first run.

Called from `init_db()` in development so the Dashboard and archive pages
have meaningful data without manual entry.  In production, seeding is
skipped (controlled by `ENVIRONMENT`).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import VehicleAlert
from app.models.digital_twin import VehicleDigitalTwin
from app.models.driving_behavior import VehicleDrivingBehavior
from app.models.health_snapshot import VehicleHealthItem, VehicleHealthSnapshot
from app.models.lifecycle_event import VehicleLifecycleEvent
from app.models.maintenance import (
    VehicleMaintenanceRecord,
    VehicleMaintenanceSchedule,
)
from app.models.ownership_record import VehicleOwnershipRecord
from app.models.user import User
from app.models.vehicle import Vehicle

_TODAY = date.today()


def seed_database(db: Session) -> None:
    """Insert seed data if the vehicles table is empty."""
    existing = db.scalar(select(Vehicle).limit(1))
    if existing is not None:
        return

    # ---- Demo user ----
    user = db.scalar(select(User).where(User.username == "demo"))
    if user is None:
        user = User(
            username="demo",
            email="demo@carsoul.ai",
            hashed_password="$2b$12$placeholder",
            display_name="演示用户",
            role="owner",
            preferences={"theme": "dark", "language": "zh-CN"},
            agent_settings={"proactive": True, "language": "zh-CN"},
        )
        db.add(user)
        db.flush()

    # ---- Vehicle 1: Tesla Model Y ----
    v1 = Vehicle(
        owner_id=user.id,
        brand="Tesla",
        model="Model Y",
        year=2024,
        vin="LSJW32E78PD000017",
        plate_number="沪A·D2024",
        color="珍珠白",
        nickname="小白",
        engine_type="双电机四驱",
        fuel_type="electric",
        battery_capacity=60.0,
        mileage=12800,
        status="active",
        purchase_date=date(2024, 3, 15),
        purchase_price=263900.0,
        dealer="特斯拉上海体验中心",
        insurance_company="平安产险",
        insurance_policy_no="PA2024SH000123",
        insurance_expiry=date(2026, 3, 14),
        registration_date=date(2024, 3, 20),
        inspection_expiry=date(2028, 3, 20),
        twin_model_id="twin-tesla-model-y-001",
        notes="日常通勤 + 周末郊游",
    )
    db.add(v1)
    db.flush()

    # ---- Vehicle 2: BYD 汉 EV ----
    v2 = Vehicle(
        owner_id=user.id,
        brand="BYD",
        model="汉 EV",
        year=2023,
        vin="LGXC76A45P8000123",
        plate_number="粤B·E8888",
        color="极光蓝",
        nickname="蓝鲸",
        engine_type="单电机前驱",
        fuel_type="electric",
        battery_capacity=85.4,
        mileage=23450,
        status="active",
        purchase_date=date(2023, 6, 1),
        purchase_price=219800.0,
        dealer="比亚迪深圳旗舰店",
        insurance_company="人保财险",
        insurance_policy_no="PICC2023SZ000456",
        insurance_expiry=date(2026, 5, 31),
        registration_date=date(2023, 6, 5),
        inspection_expiry=date(2027, 6, 5),
        twin_model_id="twin-byd-han-ev-002",
        notes="家庭用车",
    )
    db.add(v2)
    db.flush()

    # ===================================================================
    # Vehicle 1 — Tesla Model Y full archive
    # ===================================================================

    # ---- Ownership ----
    db.add(VehicleOwnershipRecord(
        vehicle_id=v1.id, owner_id=user.id, owner_name="演示用户",
        start_date=date(2024, 3, 15), transfer_type="purchase",
        purchase_price=263900.0, mileage_at_transfer=0,
    ))

    # ---- Lifecycle events ----
    _seed_lifecycle(db, v1.id, [
        ("purchase", "车辆购入", "在特斯拉上海体验中心提车，珍珠白 Model Y 长续航版。",
         date(2024, 3, 15), 0, 263900.0, "特斯拉上海体验中心", None),
        ("registration", "完成上牌", "沪A·D2024 牌照注册完成。",
         date(2024, 3, 20), 50, 500.0, "上海车管所", None),
        ("insurance", "购买车险", "平安产险全险（交强+商业），保期一年。",
         date(2024, 3, 14), 0, 8500.0, "平安产险", None),
        ("maintenance", "首保", "5,000km 首次保养：空调滤芯检查 + 系统升级。",
         date(2024, 6, 10), 5200, 0.0, "特斯拉服务中心", None),
        ("maintenance", "二保", "10,000km 常规保养：轮胎换位 + 制动系统检查。",
         date(2024, 12, 5), 10500, 680.0, "特斯拉服务中心", None),
        ("custom", "OTA 升级", "软件版本更新至 2024.44，新增 Autopilot 改进。",
         date(2024, 11, 20), 9800, 0.0, None, "info"),
        ("accident", "轻微剐蹭", "停车场低速剐蹭，左前保险杠补漆。",
         date(2025, 1, 15), 11200, 1200.0, "特斯拉钣喷中心", "minor"),
    ])

    # ---- Health snapshots ----
    _seed_health(db, v1.id, [
        (92, 5200, date(2024, 6, 10), 95, 93, 90, 88, 97, 95,
         "车辆整体状况优秀，电池健康度良好。", [
             ("engine", "电机系统", "ok", 95, "双电机运转正常", None),
             ("brake", "制动系统", "ok", 93, "刹车片厚度充足", None),
             ("tire", "轮胎", "info", 90, "胎纹深度正常，建议6,000km后换位", "下次保养时换位"),
             ("battery", "动力电池", "ok", 88, "电池健康度 98.5%", None),
             ("body", "车身", "ok", 97, "漆面完好", None),
             ("electronics", "电子系统", "ok", 95, "所有传感器正常", None),
         ]),
        (88, 10500, date(2024, 12, 5), 90, 85, 82, 85, 93, 90,
         "整体良好，轮胎磨损需关注。", [
             ("engine", "电机系统", "ok", 90, "运转正常，无异响", None),
             ("brake", "制动系统", "info", 85, "刹车片磨损约40%", "2万km时检查更换"),
             ("tire", "轮胎", "warning", 82, "胎纹偏浅，建议关注", "1.5万km时考虑更换"),
             ("battery", "动力电池", "ok", 85, "电池健康度 97.2%", None),
             ("body", "车身", "info", 93, "左前保险杠有补漆痕迹", None),
             ("electronics", "电子系统", "ok", 90, "系统正常", None),
         ]),
        (85, 12800, date(2025, 7, 1), 88, 82, 78, 84, 90, 88,
         "刹车片和轮胎需重点关注，建议安排保养。", [
             ("engine", "电机系统", "ok", 88, "运转正常", None),
             ("brake", "制动系统", "warning", 82, "刹车片剩余约5,000km", "尽快更换刹车片"),
             ("tire", "轮胎", "warning", 78, "胎纹接近磨损极限", "建议更换轮胎"),
             ("battery", "动力电池", "ok", 84, "电池健康度 96.8%", None),
             ("body", "车身", "info", 90, "补漆区域正常", None),
             ("electronics", "电子系统", "ok", 88, "系统正常", None),
         ]),
    ])

    # ---- Maintenance records ----
    _seed_maintenance_records(db, v1.id, [
        ("routine", "机油+机滤", "首保 - 空调滤芯检查", date(2024, 6, 10), 5200, 0.0,
         "特斯拉服务中心", "王技师", None, date(2024, 12, 10), 10200),
        ("routine", "轮胎", "二保 - 轮胎换位 + 制动检查", date(2024, 12, 5), 10500, 680.0,
         "特斯拉服务中心", "李技师", None, date(2025, 6, 5), 15500),
        ("repair", "车身", "左前保险杠补漆", date(2025, 1, 15), 11200, 1200.0,
         "特斯拉钣喷中心", "张师傅", None, None, None),
    ])

    # ---- Maintenance schedules ----
    _seed_schedules(db, v1.id, [
        ("轮胎换位", "轮胎", 10000, 180, 10500, date(2024, 12, 5), "medium"),
        ("空调滤芯", "滤芯", None, 365, None, None, "low"),
        ("刹车片检查", "刹车", 20000, 365, None, None, "high"),
        ("电池健康检测", "电池", None, 180, None, None, "medium"),
        ("轮胎更换", "轮胎", 40000, None, None, None, "high"),
    ])

    # ---- Driving behaviour (last 7 days) ----
    _seed_driving(db, v1.id, [
        (_TODAY - timedelta(days=6), 3, 45.2, 68, 39.9, 89.0, 88, 92, 1, 2, 0, 0, 8, 6.8, 6.6),
        (_TODAY - timedelta(days=5), 2, 28.5, 42, 40.7, 78.0, 92, 90, 0, 1, 0, 0, 3, 4.2, 6.8),
        (_TODAY - timedelta(days=4), 4, 62.3, 95, 39.4, 95.0, 85, 86, 2, 3, 1, 1, 12, 9.5, 6.6),
        (_TODAY - timedelta(days=3), 1, 15.8, 25, 37.9, 65.0, 95, 94, 0, 0, 0, 0, 2, 2.3, 6.9),
        (_TODAY - timedelta(days=2), 3, 38.6, 55, 42.1, 82.0, 90, 89, 1, 1, 0, 0, 5, 5.8, 6.7),
        (_TODAY - timedelta(days=1), 2, 22.4, 35, 38.3, 72.0, 93, 91, 0, 0, 0, 0, 3, 3.4, 6.6),
        (_TODAY, 1, 12.1, 20, 36.3, 58.0, 96, 95, 0, 0, 0, 0, 1, 1.8, 6.7),
    ])

    # ---- Alerts ----
    _seed_alerts(db, v1.id, [
        ("maintenance", "warning", "刹车片", "刹车片即将到达更换周期",
         "当前刹车片剩余寿命约5,000km，建议尽快安排更换。", "预约特斯拉服务中心更换刹车片"),
        ("maintenance", "warning", "轮胎", "轮胎磨损接近极限",
         "前轮胎纹深度接近磨损标记，建议更换。", "更换四条轮胎或前后对调"),
        ("insurance", "info", "保险", "车险将在8个月后到期",
         "平安产险保单将于2026年3月14日到期。", "提前1个月续保"),
    ])

    # ---- Digital twin ----
    db.add(VehicleDigitalTwin(
        vehicle_id=v1.id,
        model_version="2.1",
        model_url="twin://tesla/model-y/001",
        telemetry={
            "speed": 0,
            "battery_level": 78,
            "odometer": 12800,
            "tire_pressure": [2.5, 2.5, 2.4, 2.4],
            "ambient_temp": 26.5,
            "cabin_temp": 23.0,
            "location": {"lat": 31.2304, "lng": 121.4737},
            "charging_state": "disconnected",
        },
        config={
            "update_interval_s": 10,
            "telemetry_fields": ["speed", "battery_level", "tire_pressure"],
            "alert_thresholds": {"battery_low": 20, "tire_pressure_low": 2.0},
        },
        sync_status="synced",
        last_sync_at=datetime.utcnow(),
        sync_frequency="realtime",
    ))

    # ===================================================================
    # Vehicle 2 — BYD 汉 EV (lighter archive)
    # ===================================================================

    db.add(VehicleOwnershipRecord(
        vehicle_id=v2.id, owner_id=user.id, owner_name="演示用户",
        start_date=date(2023, 6, 1), transfer_type="purchase",
        purchase_price=219800.0, mileage_at_transfer=0,
    ))

    _seed_lifecycle(db, v2.id, [
        ("purchase", "车辆购入", "比亚迪汉 EV 旗舰型，极光蓝。",
         date(2023, 6, 1), 0, 219800.0, "比亚迪深圳旗舰店", None),
        ("registration", "完成上牌", "粤B·E8888 牌照注册。",
         date(2023, 6, 5), 30, 500.0, "深圳车管所", None),
        ("maintenance", "首保", "5,000km 首保，全面检查。",
         date(2023, 9, 10), 5200, 0.0, "比亚迪4S店", None),
        ("maintenance", "二保", "15,000km 保养，更换空调滤芯 + 刹油。",
         date(2024, 3, 15), 15200, 860.0, "比亚迪4S店", None),
        ("custom", "电池检测", "4S店年度电池健康检测，结果良好。",
         date(2024, 6, 1), 18000, 0.0, "比亚迪4S店", "info"),
    ])

    _seed_health(db, v2.id, [
        (90, 15200, date(2024, 3, 15), 92, 88, 85, 91, 94, 90,
         "整体状况良好。", [
             ("engine", "电机系统", "ok", 92, "运转正常", None),
             ("brake", "制动系统", "ok", 88, "刹车片正常", None),
             ("tire", "轮胎", "info", 85, "胎纹正常，建议定期换位", None),
             ("battery", "动力电池", "ok", 91, "电池健康度 98.0%", None),
             ("body", "车身", "ok", 94, "漆面完好", None),
             ("electronics", "电子系统", "ok", 90, "正常", None),
         ]),
        (87, 23450, date(2025, 7, 1), 89, 84, 80, 88, 92, 87,
         "整体良好，轮胎和制动需关注。", [
             ("engine", "电机系统", "ok", 89, "运转正常", None),
             ("brake", "制动系统", "info", 84, "刹车片磨损约50%", "3万km时更换"),
             ("tire", "轮胎", "warning", 80, "后轮胎纹偏浅", "考虑更换后轮轮胎"),
             ("battery", "动力电池", "ok", 88, "电池健康度 97.0%", None),
             ("body", "车身", "ok", 92, "正常", None),
             ("electronics", "电子系统", "ok", 87, "正常", None),
         ]),
    ])

    _seed_maintenance_records(db, v2.id, [
        ("routine", "常规保养", "首保 - 5,000km全面检查", date(2023, 9, 10), 5200, 0.0,
         "比亚迪4S店", "陈技师", None, date(2024, 3, 10), 10200),
        ("routine", "滤芯", "二保 - 空调滤芯+刹油更换", date(2024, 3, 15), 15200, 860.0,
         "比亚迪4S店", "陈技师", None, date(2024, 9, 15), 25200),
    ])

    _seed_schedules(db, v2.id, [
        ("常规保养", "常规", 10000, 180, 15200, date(2024, 3, 15), "medium"),
        ("空调滤芯", "滤芯", None, 365, None, None, "low"),
        ("刹车油更换", "刹车", 40000, 730, None, None, "medium"),
        ("轮胎更换", "轮胎", 60000, None, None, None, "high"),
    ])

    _seed_alerts(db, v2.id, [
        ("maintenance", "info", "轮胎", "后轮轮胎磨损提醒",
         "后轮胎纹偏浅，建议关注。", "下次保养时检查后轮轮胎"),
        ("inspection", "info", "年检", "年检将在2年后到期",
         "年检有效期至2027年6月5日。", "提前安排年检"),
    ])

    db.add(VehicleDigitalTwin(
        vehicle_id=v2.id,
        model_version="1.5",
        model_url="twin://byd/han-ev/002",
        telemetry={
            "speed": 0,
            "battery_level": 65,
            "odometer": 23450,
            "tire_pressure": [2.4, 2.4, 2.3, 2.3],
            "ambient_temp": 28.0,
            "location": {"lat": 22.5431, "lng": 114.0579},
            "charging_state": "charging",
        },
        config={
            "update_interval_s": 15,
            "telemetry_fields": ["speed", "battery_level", "tire_pressure"],
        },
        sync_status="synced",
        last_sync_at=datetime.utcnow(),
        sync_frequency="hourly",
    ))

    db.commit()

    # ===================================================================
    # TASK007: seed sensor data, trips, faults, digital state
    # ===================================================================
    _seed_digital_life(db, v1)
    _seed_digital_life(db, v2)


def _seed_digital_life(db: Session, vehicle: Vehicle) -> None:
    """Populate sensor / trip / fault / digital-state data for a vehicle.

    Only runs if the vehicle has no sensor data yet (idempotent).
    """
    from sqlalchemy import select as _select
    from app.models.sensor_data import VehicleSensorData
    existing = db.scalar(
        _select(VehicleSensorData).where(VehicleSensorData.vehicle_id == vehicle.id).limit(1)
    )
    if existing is not None:
        return

    from app.services import data_generator
    data_generator.generate_sensor_data(db, vehicle, points=48, days=14)
    data_generator.generate_trips(db, vehicle, count=12, days=30)
    data_generator.generate_faults(db, vehicle, count=3)
    data_generator.refresh_digital_state(db, vehicle)

    # Initialize digital life (TASK007-V2)
    try:
        from app.services import soul_engine_service
        soul_engine_service.create_digital_life(db, vehicle.id)

        # Create a few starter memories
        from app.schemas.digital_life import VehicleMemoryCreate
        starter_memories = [
            ("habit", f"主人习惯在{vehicle.fuel_type == 'electric' and '通勤' or '日常'}时使用这辆车。", 0.3, 6),
            ("context", f"车辆品牌: {vehicle.brand}，型号: {vehicle.model}。", 0.0, 5),
            ("event", "数字生命诞生，开始记录每一次出行。", 0.5, 8),
        ]
        for mtype, content, emotion, importance in starter_memories:
            soul_engine_service.create_memory(db, vehicle.id, VehicleMemoryCreate(
                memory_type=mtype,
                content=content,
                emotion_score=emotion,
                importance=importance,
                source="system",
            ))

        # Compute initial soul score
        soul_engine_service.compute_soul_score(db, vehicle.id)
    except Exception:
        pass  # Non-critical; digital life can be initialized later


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_lifecycle(
    db: Session,
    vehicle_id: int,
    rows: list[tuple],
) -> None:
    for r in rows:
        (
            ev_type, title, desc, ev_date, mileage, cost, location, severity
        ) = r
        db.add(VehicleLifecycleEvent(
            vehicle_id=vehicle_id,
            event_type=ev_type,
            title=title,
            description=desc,
            event_date=ev_date,
            mileage=mileage,
            cost=cost,
            location=location,
            severity=severity,
        ))


def _seed_health(
    db: Session,
    vehicle_id: int,
    rows: list[tuple],
) -> None:
    for r in rows:
        (
            score, mileage, snap_date,
            eng, brk, tir, bat, bod, ele,
            summary, items,
        ) = r
        snap = VehicleHealthSnapshot(
            vehicle_id=vehicle_id,
            health_score=score,
            mileage=mileage,
            engine_score=eng,
            brake_score=brk,
            tire_score=tir,
            battery_score=bat,
            body_score=bod,
            electronics_score=ele,
            summary=summary,
            source="scheduled",
            snapshot_time=datetime.combine(snap_date, datetime.min.time()),
        )
        db.add(snap)
        db.flush()
        for cat, name, level, sc, detail, rec in items:
            db.add(VehicleHealthItem(
                snapshot_id=snap.id,
                vehicle_id=vehicle_id,
                category=cat,
                item_name=name,
                level=level,
                score=sc,
                detail=detail,
                recommendation=rec,
            ))


def _seed_maintenance_records(
    db: Session,
    vehicle_id: int,
    rows: list[tuple],
) -> None:
    for r in rows:
        (
            m_type, cat, title, m_date, mileage, cost,
            provider, tech, parts, next_date, next_km,
        ) = r
        db.add(VehicleMaintenanceRecord(
            vehicle_id=vehicle_id,
            maintenance_type=m_type,
            category=cat,
            title=title,
            maintenance_date=m_date,
            mileage=mileage,
            cost=cost,
            service_provider=provider,
            technician=tech,
            parts=parts,
            next_maintenance_date=next_date,
            next_maintenance_mileage=next_km,
        ))


def _seed_schedules(
    db: Session,
    vehicle_id: int,
    rows: list[tuple],
) -> None:
    for r in rows:
        name, cat, int_km, int_days, last_km, last_dt, prio = r
        db.add(VehicleMaintenanceSchedule(
            vehicle_id=vehicle_id,
            item_name=name,
            category=cat,
            interval_km=int_km,
            interval_days=int_days,
            last_mileage=last_km,
            last_date=last_dt,
            priority=prio,
        ))


def _seed_driving(
    db: Session,
    vehicle_id: int,
    rows: list[tuple],
) -> None:
    for r in rows:
        (
            r_date, trips, dist, dur, avg_s, max_s,
            safety, eco, ha, hb, st, os, idle, fuel, eff,
        ) = r
        db.add(VehicleDrivingBehavior(
            vehicle_id=vehicle_id,
            record_date=r_date,
            trip_count=trips,
            total_distance=dist,
            total_duration=dur,
            avg_speed=avg_s,
            max_speed=max_s,
            safety_score=safety,
            eco_score=eco,
            harsh_acceleration_count=ha,
            harsh_braking_count=hb,
            sharp_turn_count=st,
            overspeed_count=os,
            idle_duration=idle,
            fuel_consumption=fuel,
            energy_efficiency=eff,
        ))


def _seed_alerts(
    db: Session,
    vehicle_id: int,
    rows: list[tuple],
) -> None:
    for r in rows:
        a_type, level, cat, title, detail, rec = r
        db.add(VehicleAlert(
            vehicle_id=vehicle_id,
            alert_type=a_type,
            level=level,
            category=cat,
            title=title,
            detail=detail,
            recommendation=rec,
        ))
