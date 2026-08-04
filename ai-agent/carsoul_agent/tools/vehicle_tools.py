"""Vehicle-related tools — DB-backed with Mock fallback.

Each tool first tries to query the backend database via the service
layer.  If the DB is unavailable (agent running standalone, import
failure, query error), the tool transparently falls back to
illustrative Mock data that mirrors the seed dataset.

Tools:
  1. get_vehicle_info       — vehicle profile (brand, model, VIN, …)
  2. get_health_score       — latest health snapshot + sub-scores + risks
  3. get_maintenance_plan   — due / upcoming maintenance schedules
  4. get_driving_behavior   — recent driving behaviour summary
  5. get_lifecycle_timeline — life events (purchase, maintenance, …)
  6. get_alerts             — active alerts with recommendations
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from carsoul_agent.tools.base import BaseTool, ToolResult, default_registry
from carsoul_agent.tools.db_helper import db_query


# ---------------------------------------------------------------------------
# 1. Vehicle info
# ---------------------------------------------------------------------------

class GetVehicleInfoTool(BaseTool):
    name = "get_vehicle_info"
    description = (
        "根据 VIN 或车辆 ID 获取车辆完整档案信息"
        "（品牌、型号、年份、里程、车牌、燃料类型、保险、年检等）。"
    )
    parameters = {"vin": "string", "vehicle_id": "integer"}

    def run(self, vin: str | None = None, vehicle_id: int | None = None, **_: Any) -> ToolResult:
        # Try DB first
        data = db_query(lambda db: self._fetch(db, vin, vehicle_id))
        if data is not None:
            return ToolResult(ok=True, data=data)
        # Mock fallback
        return self._mock(vin, vehicle_id)

    # -- DB --

    @staticmethod
    def _fetch(db: Any, vin: str | None, vehicle_id: int | None) -> dict | None:
        from sqlalchemy import select
        from app.models.vehicle import Vehicle

        v: Vehicle | None = None
        if vehicle_id:
            v = db.get(Vehicle, vehicle_id)
        elif vin:
            v = db.scalar(select(Vehicle).where(Vehicle.vin == vin))
        if v is None:
            # Fall back to first vehicle in DB
            v = db.scalar(select(Vehicle).order_by(Vehicle.id.asc()).limit(1))
        if v is None:
            return None

        return {
            "vehicle_id": v.id,
            "vin": v.vin,
            "brand": v.brand,
            "model": v.model,
            "year": v.year,
            "mileage": v.mileage,
            "plate_number": v.plate_number,
            "color": v.color,
            "nickname": v.nickname,
            "fuel_type": v.fuel_type,
            "engine_type": v.engine_type,
            "battery_capacity": v.battery_capacity,
            "status": v.status,
            "purchase_date": v.purchase_date.isoformat() if v.purchase_date else None,
            "purchase_price": v.purchase_price,
            "insurance_company": v.insurance_company,
            "insurance_expiry": v.insurance_expiry.isoformat() if v.insurance_expiry else None,
            "inspection_expiry": v.inspection_expiry.isoformat() if v.inspection_expiry else None,
        }

    # -- Mock --

    @staticmethod
    def _mock(vin: str | None, vehicle_id: int | None) -> ToolResult:
        return ToolResult(
            ok=True,
            data={
                "vehicle_id": vehicle_id or 1,
                "vin": vin or "LSJW32E78PD000017",
                "brand": "Tesla",
                "model": "Model Y",
                "year": 2024,
                "mileage": 12800,
                "plate_number": "沪A·D2024",
                "color": "珍珠白",
                "nickname": "小白",
                "fuel_type": "electric",
                "battery_capacity": 60.0,
                "status": "active",
                "purchase_date": "2024-03-15",
                "insurance_expiry": "2026-03-14",
                "inspection_expiry": "2028-03-20",
            },
        )


# ---------------------------------------------------------------------------
# 2. Health score
# ---------------------------------------------------------------------------

class GetHealthScoreTool(BaseTool):
    name = "get_health_score"
    description = (
        "获取车辆最新健康指数（0-100）及各子系统分数和风险项明细。"
    )
    parameters = {"vehicle_id": "integer"}

    def run(self, vehicle_id: int = 1, **_: Any) -> ToolResult:
        data = db_query(lambda db: self._fetch(db, vehicle_id))
        if data is not None:
            return ToolResult(ok=True, data=data)
        return self._mock(vehicle_id)

    # -- DB --

    @staticmethod
    def _fetch(db: Any, vehicle_id: int) -> dict | None:
        from sqlalchemy import select
        from app.models.health_snapshot import VehicleHealthItem, VehicleHealthSnapshot

        snap = db.scalar(
            select(VehicleHealthSnapshot)
            .where(VehicleHealthSnapshot.vehicle_id == vehicle_id)
            .order_by(VehicleHealthSnapshot.snapshot_time.desc())
            .limit(1)
        )
        if snap is None:
            return None

        items = list(db.scalars(
            select(VehicleHealthItem).where(
                VehicleHealthItem.snapshot_id == snap.id
            )
        ).all())

        risks = []
        for item in items:
            if item.level in ("warning", "critical"):
                risks.append({
                    "category": item.category,
                    "item": item.item_name,
                    "level": item.level,
                    "detail": item.detail,
                    "recommendation": item.recommendation,
                })

        return {
            "vehicle_id": vehicle_id,
            "health_score": snap.health_score,
            "mileage": snap.mileage,
            "sub_scores": {
                "engine": snap.engine_score,
                "brake": snap.brake_score,
                "tire": snap.tire_score,
                "battery": snap.battery_score,
                "body": snap.body_score,
                "electronics": snap.electronics_score,
            },
            "risks": risks,
            "summary": snap.summary or "车辆健康状态良好。",
        }

    # -- Mock --

    @staticmethod
    def _mock(vehicle_id: int) -> ToolResult:
        return ToolResult(
            ok=True,
            data={
                "vehicle_id": vehicle_id,
                "health_score": 85,
                "mileage": 12800,
                "sub_scores": {
                    "engine": 88,
                    "brake": 82,
                    "tire": 78,
                    "battery": 84,
                    "body": 90,
                    "electronics": 88,
                },
                "risks": [
                    {"category": "brake", "item": "刹车片", "level": "warning",
                     "detail": "剩余约 5,000 km", "recommendation": "尽快更换刹车片"},
                    {"category": "tire", "item": "轮胎", "level": "warning",
                     "detail": "胎纹接近磨损极限", "recommendation": "建议更换轮胎"},
                    {"category": "body", "item": "车身", "level": "info",
                     "detail": "补漆区域正常", "recommendation": None},
                ],
                "summary": "刹车片和轮胎需重点关注，建议安排保养。",
            },
        )


# ---------------------------------------------------------------------------
# 3. Maintenance plan
# ---------------------------------------------------------------------------

class GetMaintenancePlanTool(BaseTool):
    name = "get_maintenance_plan"
    description = (
        "根据里程与时间生成本车保养计划建议，包括到期项和未来计划。"
    )
    parameters = {"vehicle_id": "integer"}

    def run(self, vehicle_id: int = 1, **_: Any) -> ToolResult:
        data = db_query(lambda db: self._fetch(db, vehicle_id))
        if data is not None:
            return ToolResult(ok=True, data=data)
        return self._mock(vehicle_id)

    # -- DB --

    @staticmethod
    def _fetch(db: Any, vehicle_id: int) -> dict | None:
        from sqlalchemy import select
        from app.models.maintenance import VehicleMaintenanceSchedule
        from app.models.vehicle import Vehicle
        from app.services.maintenance_service import _recompute_schedule

        vehicle = db.get(Vehicle, vehicle_id)
        if vehicle is None:
            return None

        schedules = list(db.scalars(
            select(VehicleMaintenanceSchedule)
            .where(VehicleMaintenanceSchedule.vehicle_id == vehicle_id)
            .order_by(VehicleMaintenanceSchedule.priority.desc())
        ).all())

        due_items: list[dict] = []
        upcoming_items: list[dict] = []
        for sched in schedules:
            _recompute_schedule(sched, vehicle)
            entry = {
                "item_name": sched.item_name,
                "category": sched.category,
                "priority": sched.priority,
                "status": sched.status,
                "next_due_km": sched.next_due_km,
                "next_due_date": sched.next_due_date.isoformat() if sched.next_due_date else None,
                "detail": sched.notes,
            }
            if sched.status in ("due", "overdue"):
                due_items.append(entry)
            elif sched.status == "pending":
                upcoming_items.append(entry)
        db.commit()

        return {
            "vehicle_id": vehicle_id,
            "current_mileage": vehicle.mileage,
            "due_items": due_items,
            "upcoming_items": upcoming_items,
        }

    # -- Mock --

    @staticmethod
    def _mock(vehicle_id: int) -> ToolResult:
        return ToolResult(
            ok=True,
            data={
                "vehicle_id": vehicle_id,
                "current_mileage": 12800,
                "due_items": [
                    {"item_name": "刹车片检查", "category": "刹车", "priority": "high",
                     "status": "overdue", "next_due_km": 10500, "detail": "已超过建议保养里程"},
                    {"item_name": "轮胎更换", "category": "轮胎", "priority": "high",
                     "status": "overdue", "detail": "胎纹接近极限"},
                ],
                "upcoming_items": [
                    {"item_name": "轮胎换位", "category": "轮胎", "priority": "medium",
                     "next_due_km": 20500, "next_due_date": str(date.today() + timedelta(days=120))},
                    {"item_name": "空调滤芯", "category": "滤芯", "priority": "low",
                     "next_due_date": str(date.today() + timedelta(days=180))},
                    {"item_name": "电池健康检测", "category": "电池", "priority": "medium",
                     "next_due_date": str(date.today() + timedelta(days=90))},
                ],
            },
        )


# ---------------------------------------------------------------------------
# 4. Driving behavior
# ---------------------------------------------------------------------------

class GetDrivingBehaviorTool(BaseTool):
    name = "get_driving_behavior"
    description = (
        "获取近期驾驶行为分析（安全评分、能耗评分、急加速/急刹车次数等）。"
    )
    parameters = {"vehicle_id": "integer", "days": "integer"}

    def run(self, vehicle_id: int = 1, days: int = 7, **_: Any) -> ToolResult:
        data = db_query(lambda db: self._fetch(db, vehicle_id, days))
        if data is not None:
            return ToolResult(ok=True, data=data)
        return self._mock(vehicle_id, days)

    # -- DB --

    @staticmethod
    def _fetch(db: Any, vehicle_id: int, days: int) -> dict | None:
        from app.services.driving_behavior_service import get_behavior_summary, list_behaviors

        summary = get_behavior_summary(db, vehicle_id, days)
        records = list_behaviors(db, vehicle_id, days)

        daily = [
            {
                "date": str(r.record_date),
                "safety_score": r.safety_score,
                "eco_score": r.eco_score,
                "harsh_events": (
                    r.harsh_acceleration_count
                    + r.harsh_braking_count
                    + r.sharp_turn_count
                    + r.overspeed_count
                ),
            }
            for r in records
        ]

        # Generate advice
        avg_safety = summary.get("avg_safety_score")
        harsh = summary.get("total_harsh_events", 0)
        if avg_safety is not None and avg_safety >= 90 and harsh <= 5:
            advice = "近期驾驶平稳，安全评分优秀，请继续保持。"
        elif harsh > 10:
            advice = "近期急加速/急刹车较多，建议保持匀速驾驶以提升安全与能耗评分。"
        else:
            advice = "驾驶行为整体正常，注意减少急刹车以进一步提升评分。"

        return {
            "vehicle_id": vehicle_id,
            "period_days": days,
            "summary": summary,
            "daily_records": daily,
            "advice": advice,
        }

    # -- Mock --

    @staticmethod
    def _mock(vehicle_id: int, days: int) -> ToolResult:
        return ToolResult(
            ok=True,
            data={
                "vehicle_id": vehicle_id,
                "period_days": days,
                "summary": {
                    "total_distance": 224.9,
                    "total_duration": 340,
                    "avg_safety_score": 91,
                    "avg_eco_score": 90,
                    "total_harsh_events": 7,
                    "total_fuel": 33.8,
                    "trip_count": 16,
                },
                "daily_records": [
                    {
                        "date": str(date.today() - timedelta(days=i)),
                        "safety_score": 85 + (i % 3) * 4,
                        "eco_score": 86 + (i % 3) * 3,
                        "harsh_events": (i % 3),
                    }
                    for i in range(min(days, 7))
                ],
                "advice": (
                    "近7天驾驶整体平稳，安全评分91分。"
                    "有少量急加速和急刹车事件，建议保持匀速驾驶以提升能耗评分。"
                ),
            },
        )


# ---------------------------------------------------------------------------
# 5. Lifecycle timeline
# ---------------------------------------------------------------------------

class GetLifecycleTimelineTool(BaseTool):
    name = "get_lifecycle_timeline"
    description = (
        "获取车辆生命周期事件时间线（购车、保养、维修、事故、保险等）。"
    )
    parameters = {"vehicle_id": "integer"}

    def run(self, vehicle_id: int = 1, **_: Any) -> ToolResult:
        data = db_query(lambda db: self._fetch(db, vehicle_id))
        if data is not None:
            return ToolResult(ok=True, data=data)
        return self._mock(vehicle_id)

    # -- DB --

    @staticmethod
    def _fetch(db: Any, vehicle_id: int) -> dict | None:
        from sqlalchemy import select
        from app.models.lifecycle_event import VehicleLifecycleEvent

        events_orm = list(db.scalars(
            select(VehicleLifecycleEvent)
            .where(VehicleLifecycleEvent.vehicle_id == vehicle_id)
            .order_by(VehicleLifecycleEvent.event_date.desc())
        ).all())

        if not events_orm:
            return None

        events = [
            {
                "date": e.event_date.isoformat() if e.event_date else None,
                "type": e.event_type,
                "title": e.title,
                "description": e.description,
                "mileage": e.mileage,
                "cost": e.cost,
                "location": e.location,
                "severity": e.severity,
            }
            for e in events_orm
        ]

        total_cost = sum(e["cost"] or 0 for e in events)

        return {
            "vehicle_id": vehicle_id,
            "events": events,
            "total_events": len(events),
            "total_cost": total_cost,
        }

    # -- Mock --

    @staticmethod
    def _mock(vehicle_id: int) -> ToolResult:
        return ToolResult(
            ok=True,
            data={
                "vehicle_id": vehicle_id,
                "events": [
                    {"date": "2024-03-15", "type": "purchase", "title": "车辆购入",
                     "mileage": 0, "cost": 263900},
                    {"date": "2024-03-20", "type": "registration", "title": "完成上牌",
                     "mileage": 50, "cost": 500},
                    {"date": "2024-06-10", "type": "maintenance", "title": "首保",
                     "mileage": 5200, "cost": 0},
                    {"date": "2024-11-20", "type": "custom", "title": "OTA 升级",
                     "mileage": 9800, "cost": 0},
                    {"date": "2024-12-05", "type": "maintenance", "title": "二保",
                     "mileage": 10500, "cost": 680},
                    {"date": "2025-01-15", "type": "accident", "title": "轻微剐蹭",
                     "mileage": 11200, "cost": 1200, "severity": "minor"},
                ],
                "total_events": 6,
                "total_cost": 266280,
            },
        )


# ---------------------------------------------------------------------------
# 6. Alerts
# ---------------------------------------------------------------------------

class GetAlertsTool(BaseTool):
    name = "get_alerts"
    description = "获取车辆当前活跃告警列表及处理建议。"
    parameters = {"vehicle_id": "integer"}

    def run(self, vehicle_id: int = 1, **_: Any) -> ToolResult:
        data = db_query(lambda db: self._fetch(db, vehicle_id))
        if data is not None:
            return ToolResult(ok=True, data=data)
        return self._mock(vehicle_id)

    # -- DB --

    @staticmethod
    def _fetch(db: Any, vehicle_id: int) -> dict | None:
        from sqlalchemy import select
        from app.models.alert import VehicleAlert

        alerts_orm = list(db.scalars(
            select(VehicleAlert)
            .where(VehicleAlert.vehicle_id == vehicle_id)
            .order_by(
                VehicleAlert.status.asc(),
                VehicleAlert.triggered_at.desc(),
            )
        ).all())

        if not alerts_orm:
            return None

        active = [a for a in alerts_orm if a.status == "active"]
        alerts = [
            {
                "id": a.id,
                "level": a.level,
                "type": a.alert_type,
                "category": a.category,
                "title": a.title,
                "detail": a.detail,
                "recommendation": a.recommendation,
                "status": a.status,
                "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            }
            for a in alerts_orm
        ]

        return {
            "vehicle_id": vehicle_id,
            "active_count": len(active),
            "alerts": alerts,
        }

    # -- Mock --

    @staticmethod
    def _mock(vehicle_id: int) -> ToolResult:
        return ToolResult(
            ok=True,
            data={
                "vehicle_id": vehicle_id,
                "active_count": 3,
                "alerts": [
                    {"level": "warning", "type": "maintenance", "category": "刹车片",
                     "title": "刹车片即将到达更换周期",
                     "recommendation": "预约特斯拉服务中心更换刹车片"},
                    {"level": "warning", "type": "maintenance", "category": "轮胎",
                     "title": "轮胎磨损接近极限",
                     "recommendation": "更换四条轮胎或前后对调"},
                    {"level": "info", "type": "insurance", "category": "保险",
                     "title": "车险将在8个月后到期",
                     "recommendation": "提前1个月续保"},
                ],
            },
        )


# ---------------------------------------------------------------------------
# 7. Calibration context (自纠错校准上下文)
# ---------------------------------------------------------------------------

class GetCalibrationContextTool(BaseTool):
    """读取历史风险预测反馈，构建自纠错校准上下文。

    这是 Agent「从反馈中学习」的数据入口：从后端 RiskPrediction 表
    读取已闭环（resolved + actual_outcome）的预测记录，统计误报率、
    确认率、近期反馈明细，供诊断/风险 Agent 在本次评估时校准置信度。
    """

    name = "get_calibration_context"
    description = (
        "获取本车历史风险预测的反馈校准上下文（误报率、确认率、"
        "近期反馈明细），用于 Agent 自纠错——根据过往预测准确度"
        "调整本次评估的置信度与风险等级。"
    )
    parameters = {"vehicle_id": "integer", "limit": "integer"}

    def run(self, vehicle_id: int = 1, limit: int = 10, **_: Any) -> ToolResult:
        data = db_query(lambda db: self._fetch(db, vehicle_id, limit))
        if data is not None:
            return ToolResult(ok=True, data=data)
        # Mock fallback：无后端时返回空校准（不影响首次诊断）
        return ToolResult(ok=True, data=self._empty(vehicle_id))

    @staticmethod
    def _empty(vehicle_id: int) -> dict:
        return {
            "vehicle_id": vehicle_id,
            "has_history": False,
            "total_feedback": 0,
            "false_alarm_rate": None,
            "confirmed_rate": None,
            "accuracy_rate": None,
            "recent_feedbacks": [],
            "calibration_note": "暂无历史反馈，本次评估使用默认置信度。",
        }

    @staticmethod
    def _fetch(db: Any, vehicle_id: int, limit: int) -> dict | None:
        from sqlalchemy import select, desc
        from app.models.risk_prediction import RiskPrediction  # type: ignore

        # 只取已闭环（有 actual_outcome）的预测
        stmt = (
            select(RiskPrediction)
            .where(
                RiskPrediction.vehicle_id == vehicle_id,
                RiskPrediction.actual_outcome.is_not(None),
            )
            .order_by(desc(RiskPrediction.created_at))
            .limit(limit)
        )
        rows = list(db.scalars(stmt).all())

        if not rows:
            return GetCalibrationContextTool._empty(vehicle_id)

        total = len(rows)
        false_alarms = sum(1 for r in rows if r.actual_outcome == "false_alarm")
        confirmed = sum(1 for r in rows if r.actual_outcome == "confirmed")
        accurate = sum(1 for r in rows if (r.accuracy or 0) >= 1.0)

        false_alarm_rate = round(false_alarms / total, 3) if total else None
        confirmed_rate = round(confirmed / total, 3) if total else None
        accuracy_rate = round(accurate / total, 3) if total else None

        recent_feedbacks = [
            {
                "prediction_id": r.id,
                "predicted_level": r.predicted_level,
                "root_cause": r.root_cause,
                "primary_type": r.primary_type,
                "actual_outcome": r.actual_outcome,
                "accuracy": r.accuracy,
                "outcome_notes": r.outcome_notes,
            }
            for r in rows
        ]

        # 构建校准提示——Agent 据此调整本次评估
        if false_alarm_rate is not None and false_alarm_rate >= 0.4:
            calibration_note = (
                f"历史误报率 {false_alarm_rate*100:.0f}% 偏高，"
                f"本次评估已下调置信度、放宽ETA窗口，避免过度预警。"
            )
        elif accuracy_rate is not None and accuracy_rate >= 0.8:
            calibration_note = (
                f"历史预测准确率 {accuracy_rate*100:.0f}% 良好，"
                f"本次评估维持标准置信度。"
            )
        else:
            calibration_note = "历史反馈数据有限，本次评估使用标准置信度。"

        return {
            "vehicle_id": vehicle_id,
            "has_history": True,
            "total_feedback": total,
            "false_alarm_rate": false_alarm_rate,
            "confirmed_rate": confirmed_rate,
            "accuracy_rate": accuracy_rate,
            "recent_feedbacks": recent_feedbacks,
            "calibration_note": calibration_note,
        }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_default_tools() -> None:
    for tool_cls in (
        GetVehicleInfoTool,
        GetHealthScoreTool,
        GetMaintenancePlanTool,
        GetDrivingBehaviorTool,
        GetLifecycleTimelineTool,
        GetAlertsTool,
        GetCalibrationContextTool,
    ):
        default_registry.register(tool_cls())


# Register on import so agents can discover them out of the box.
register_default_tools()
