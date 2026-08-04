"""Service order tests — after-sales closed-loop (§3A.1).

Tests the full chain: Agent 诊断 → 创建工单 → 进度推进 → 完成 → 用户反馈.
Covers: state machine transitions, status history, feedback validation,
persistence, and 404/error handling.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path so `import app...` works from tests/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force a dev SQLite DB so tests never touch a real database.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_service_order.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.database.base import Base  # noqa: E402
from app.database.connection import engine  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

# Ensure tables exist before tests run.
Base.metadata.create_all(bind=engine)


def _ensure_vehicle() -> int:
    """Get the first vehicle ID (seed data should exist in dev/test)."""
    resp = client.get("/api/vehicle")
    assert resp.status_code == 200
    items = resp.json().get("items", [])
    if items:
        return items[0]["id"]
    # Create a minimal vehicle if none exist.
    resp = client.post("/api/vehicle", json={
        "brand": "TestBrand",
        "model": "TestModel",
        "year": 2024,
        "fuel_type": "electric",
        "vin": "TEST-VIN-0001",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_order(vehicle_id: int) -> dict:
    """Create a service order and return the response body."""
    resp = client.post(f"/api/vehicle/{vehicle_id}/service-orders", json={
        "service_type": "manufacturer_service",
        "service_name": "电池冷却系统检查",
        "priority": "high",
        "reason": "Agent 诊断发现电池温度异常波动，建议进行冷却系统检查",
        "description": "充电时电池温度波动超过正常范围",
        "diagnosis_summary": "电池温度传感器读数异常，冷却效率可能下降",
    })
    assert resp.status_code == 201
    return resp.json()


class TestServiceOrderCreation:
    """Test order creation and listing."""

    def test_create_service_order(self):
        vid = _ensure_vehicle()
        order = _create_order(vid)
        assert order["status"] == "created"
        assert order["service_type"] == "manufacturer_service"
        assert order["priority"] == "high"
        assert order["vehicle_id"] == vid
        assert len(order["status_history"]) == 1
        assert order["status_history"][0]["status"] == "created"
        assert order["feedback_type"] is None

    def test_list_service_orders(self):
        vid = _ensure_vehicle()
        _create_order(vid)
        resp = client.get(f"/api/vehicle/{vid}/service-orders")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert all(o["vehicle_id"] == vid for o in body["items"])

    def test_list_filter_by_status(self):
        vid = _ensure_vehicle()
        _create_order(vid)
        resp = client.get(f"/api/vehicle/{vid}/service-orders?status=created")
        assert resp.status_code == 200
        assert all(o["status"] == "created" for o in resp.json()["items"])

        resp = client.get(f"/api/vehicle/{vid}/service-orders?status=closed")
        assert resp.status_code == 200
        # Newly created orders are not closed.
        assert all(o["status"] == "closed" for o in resp.json()["items"])

    def test_get_single_order(self):
        vid = _ensure_vehicle()
        order = _create_order(vid)
        resp = client.get(f"/api/vehicle/{vid}/service-orders/{order['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == order["id"]

    def test_get_order_wrong_vehicle_404(self):
        vid = _ensure_vehicle()
        order = _create_order(vid)
        resp = client.get(f"/api/vehicle/{vid + 99999}/service-orders/{order['id']}")
        assert resp.status_code == 404


class TestServiceOrderStateMachine:
    """Test the forward-only state machine: created → booked → in_service → done → closed."""

    def test_full_lifecycle_auto_advance(self):
        """Advance through all states automatically (no explicit target)."""
        vid = _ensure_vehicle()
        order = _create_order(vid)
        oid = order["id"]

        # created → booked
        resp = client.patch(f"/api/vehicle/{vid}/service-orders/{oid}", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "booked"
        assert resp.json()["booked_at"] is not None

        # booked → in_service
        resp = client.patch(f"/api/vehicle/{vid}/service-orders/{oid}", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_service"
        assert resp.json()["in_service_at"] is not None

        # in_service → done
        resp = client.patch(
            f"/api/vehicle/{vid}/service-orders/{oid}",
            json={"cost": 850.0, "note": "更换冷却液，检查散热器"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"
        assert resp.json()["done_at"] is not None
        assert resp.json()["cost"] == 850.0

        # done → closed
        resp = client.patch(f"/api/vehicle/{vid}/service-orders/{oid}", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"
        assert resp.json()["closed_at"] is not None

    def test_status_history_grows(self):
        """Each transition appends to status_history."""
        vid = _ensure_vehicle()
        order = _create_order(vid)
        oid = order["id"]

        # Advance to booked
        resp = client.patch(
            f"/api/vehicle/{vid}/service-orders/{oid}",
            json={"note": "已预约4S店"},
        )
        history = resp.json()["status_history"]
        assert len(history) == 2
        assert history[1]["status"] == "booked"
        assert history[1]["note"] == "已预约4S店"

    def test_explicit_target_status(self):
        """Advance directly to a specific status (skipping intermediates)."""
        vid = _ensure_vehicle()
        order = _create_order(vid)
        oid = order["id"]

        # created → in_service (skip booked)
        resp = client.patch(
            f"/api/vehicle/{vid}/service-orders/{oid}",
            json={"status": "in_service"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_service"

    def test_cannot_move_backwards(self):
        """Backward transitions are rejected."""
        vid = _ensure_vehicle()
        order = _create_order(vid)
        oid = order["id"]

        # Advance to booked first
        client.patch(f"/api/vehicle/{vid}/service-orders/{oid}", json={})

        # Try to go back to created
        resp = client.patch(
            f"/api/vehicle/{vid}/service-orders/{oid}",
            json={"status": "created"},
        )
        assert resp.status_code == 409

    def test_invalid_status_rejected(self):
        vid = _ensure_vehicle()
        order = _create_order(vid)
        oid = order["id"]

        resp = client.patch(
            f"/api/vehicle/{vid}/service-orders/{oid}",
            json={"status": "invalid_status"},
        )
        assert resp.status_code == 409


class TestServiceOrderFeedback:
    """Test after-sales feedback submission."""

    def test_feedback_after_done(self):
        """Feedback can be submitted when status is 'done'."""
        vid = _ensure_vehicle()
        order = _create_order(vid)
        oid = order["id"]

        # Advance to done
        for target in ("booked", "in_service", "done"):
            resp = client.patch(
                f"/api/vehicle/{vid}/service-orders/{oid}",
                json={"status": target} if target != "booked" else {},
            )
            assert resp.status_code == 200

        # Submit feedback
        resp = client.post(
            f"/api/vehicle/{vid}/service-orders/{oid}/feedback",
            json={
                "feedback_type": "confirmed",
                "feedback_note": "确实发现冷却系统问题，已修复",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["feedback_type"] == "confirmed"
        assert body["feedback_note"] == "确实发现冷却系统问题，已修复"
        assert body["feedback_at"] is not None

    def test_feedback_rejected_before_done(self):
        """Feedback is rejected when order is still in progress."""
        vid = _ensure_vehicle()
        order = _create_order(vid)
        oid = order["id"]

        resp = client.post(
            f"/api/vehicle/{vid}/service-orders/{oid}/feedback",
            json={"feedback_type": "confirmed"},
        )
        assert resp.status_code == 409

    def test_all_feedback_types(self):
        """All four feedback types are accepted."""
        vid = _ensure_vehicle()
        for ftype in ("confirmed", "false_alarm", "no_event", "partial"):
            order = _create_order(vid)
            oid = order["id"]
            # Advance to done
            for target in ("booked", "in_service", "done"):
                r = client.patch(
                    f"/api/vehicle/{vid}/service-orders/{oid}",
                    json={"status": target} if target != "booked" else {},
                )
                assert r.status_code == 200
            resp = client.post(
                f"/api/vehicle/{vid}/service-orders/{oid}/feedback",
                json={"feedback_type": ftype},
            )
            assert resp.status_code == 200
            assert resp.json()["feedback_type"] == ftype

    def test_invalid_feedback_type_rejected(self):
        vid = _ensure_vehicle()
        order = _create_order(vid)
        oid = order["id"]
        # Advance to done
        for target in ("booked", "in_service", "done"):
            client.patch(
                f"/api/vehicle/{vid}/service-orders/{oid}",
                json={"status": target} if target != "booked" else {},
            )
        resp = client.post(
            f"/api/vehicle/{vid}/service-orders/{oid}/feedback",
            json={"feedback_type": "invalid_type"},
        )
        assert resp.status_code == 409


class TestServiceOrderDelete:
    """Test order deletion."""

    def test_delete_order(self):
        vid = _ensure_vehicle()
        order = _create_order(vid)
        oid = order["id"]

        resp = client.delete(f"/api/vehicle/{vid}/service-orders/{oid}")
        assert resp.status_code == 204

        # Verify gone
        resp = client.get(f"/api/vehicle/{vid}/service-orders/{oid}")
        assert resp.status_code == 404

    def test_delete_nonexistent_404(self):
        vid = _ensure_vehicle()
        resp = client.delete(f"/api/vehicle/{vid}/service-orders/999999")
        assert resp.status_code == 404


class TestServiceOrderFullChain:
    """End-to-end: 诊断 → 创建工单 → 进度推进 → 完成 → 用户反馈."""

    def test_complete_after_sales_loop(self):
        vid = _ensure_vehicle()

        # Step 1: Agent diagnosis triggers order creation
        order = _create_order(vid)
        oid = order["id"]
        assert order["status"] == "created"
        assert order["diagnosis_summary"] is not None

        # Step 2: Book service appointment
        resp = client.patch(
            f"/api/vehicle/{vid}/service-orders/{oid}",
            json={"service_provider": "特斯拉服务中心", "note": "预约下周三"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "booked"
        assert resp.json()["service_provider"] == "特斯拉服务中心"

        # Step 3: Vehicle in service
        resp = client.patch(f"/api/vehicle/{vid}/service-orders/{oid}", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_service"

        # Step 4: Service completed
        resp = client.patch(
            f"/api/vehicle/{vid}/service-orders/{oid}",
            json={"cost": 1200.0, "note": "更换冷却泵，系统恢复正常"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"

        # Step 5: User feedback
        resp = client.post(
            f"/api/vehicle/{vid}/service-orders/{oid}/feedback",
            json={
                "feedback_type": "confirmed",
                "feedback_note": "充电温度恢复正常，感谢 CarSoul 守护",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["feedback_type"] == "confirmed"
        assert body["feedback_at"] is not None

        # Step 6: Close the order
        resp = client.patch(f"/api/vehicle/{vid}/service-orders/{oid}", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"
        assert resp.json()["closed_at"] is not None

        # Verify full status history
        resp = client.get(f"/api/vehicle/{vid}/service-orders/{oid}")
        assert resp.status_code == 200
        history = resp.json()["status_history"]
        statuses = [h["status"] for h in history]
        assert statuses == ["created", "booked", "in_service", "done", "feedback", "closed"]
