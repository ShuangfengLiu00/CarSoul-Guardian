"""TASK007-V2 Digital Twin API tests.

Tests the Vehicle Digital Life Engine endpoints:
  - Create digital life
  - Soul profile
  - Soul score (VSS)
  - Life state
  - Life events
  - Memories
  - Health metrics
  - Predictions
  - Driver profile
  - Agent interface
  - 365-day lifecycle generator
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path so `import app...` works from tests/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force a dev SQLite DB so tests never touch a real database.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_carsoul_v2.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import create_access_token  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.connection import engine  # noqa: E402
from app.main import app  # noqa: E402

# Guardian enforces global Bearer auth (app.core.auth.AuthMiddleware);
# tests must present a valid token. Auth is wired in TASK009.
client = TestClient(app, headers={"Authorization": f"Bearer {create_access_token('test-user')}"})

# Ensure tables exist before tests run.
Base.metadata.create_all(bind=engine)


def _ensure_vehicle() -> int:
    """Ensure at least one vehicle exists and return its ID."""
    resp = client.get("/api/vehicle")
    if resp.status_code == 200:
        data = resp.json()
        items = data.get("items", [])
        if items:
            return items[0]["id"]
    # Create a vehicle if none exist
    resp = client.post("/api/vehicle", json={
        "brand": "Tesla",
        "model": "Model Y",
        "year": 2024,
        "vin": "TESTV2VIN00001",
        "fuel_type": "electric",
        "mileage": 0,
        "status": "active",
    })
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


# ===========================================================================
# 1. Create Digital Life
# ===========================================================================

class TestCreateDigitalLife:
    def test_create_digital_life(self):
        vehicle_id = _ensure_vehicle()
        resp = client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        assert resp.status_code == 201
        data = resp.json()
        assert data["vehicle_id"] == vehicle_id
        assert data["soul_id"].startswith("CSG-")
        assert "identity" in data
        assert data["identity"]["vehicle_uuid"].startswith("CSG-")

    def test_create_digital_life_idempotent(self):
        """Creating digital life twice should not error."""
        vehicle_id = _ensure_vehicle()
        # First creation
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        # Second creation (should return same soul_id or update)
        resp = client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        assert resp.status_code == 201

    def test_create_digital_life_nonexistent_vehicle(self):
        resp = client.post("/api/digital-twin/create?vehicle_id=99999")
        assert resp.status_code == 404


# ===========================================================================
# 2. Soul Profile
# ===========================================================================

class TestSoulProfile:
    def test_get_soul_profile(self):
        vehicle_id = _ensure_vehicle()
        # Ensure digital life exists
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.get(f"/api/digital-twin/{vehicle_id}/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vehicle_id"] == vehicle_id
        assert data["soul_id"].startswith("CSG-")
        assert "soul_score" in data
        assert "soul_grade" in data
        assert "soul_breakdown" in data
        assert "life_stage" in data
        assert "life_events" in data
        assert "memories" in data
        assert "health_metrics" in data
        assert "predictions" in data
        assert "ai_insights" in data
        assert "agent_hooks" in data

    def test_get_soul_profile_not_found(self):
        resp = client.get("/api/digital-twin/99999/profile")
        assert resp.status_code == 404


# ===========================================================================
# 3. Soul Score (VSS)
# ===========================================================================

class TestSoulScore:
    def test_get_soul_score(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.get(f"/api/digital-twin/{vehicle_id}/soul-score")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vehicle_id"] == vehicle_id
        assert "score" in data
        assert 0 <= data["score"] <= 100
        assert data["grade"] in ("legendary", "excellent", "normal", "risk")
        assert "breakdown" in data
        b = data["breakdown"]
        assert "health" in b
        assert "memory" in b
        assert "maintenance" in b
        assert "driving" in b
        assert "prediction" in b


# ===========================================================================
# 4. Soul Score History
# ===========================================================================

class TestSoulHistory:
    def test_get_soul_history(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.get(f"/api/digital-twin/{vehicle_id}/soul-history?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == len(data["items"])


# ===========================================================================
# 5. Life State
# ===========================================================================

class TestLifeState:
    def test_get_life_state(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.get(f"/api/digital-twin/{vehicle_id}/life-state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vehicle_id"] == vehicle_id
        assert data["life_stage"] in ("NEW", "GROWTH", "MATURE", "AGING", "RETIRE")
        assert "mileage" in data
        assert "vehicle_age_days" in data

    def test_refresh_life_state(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.post(f"/api/digital-twin/{vehicle_id}/life-state/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vehicle_id"] == vehicle_id


# ===========================================================================
# 6. Life Events
# ===========================================================================

class TestLifeEvents:
    def test_list_life_events(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.get(f"/api/digital-twin/{vehicle_id}/life-events")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_create_life_event(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.post(f"/api/digital-twin/{vehicle_id}/life-events", json={
            "event_type": "TRAVEL",
            "title": "周末郊游",
            "description": "前往莫干山度周末",
            "importance": 7,
            "mileage": 180,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["event_type"] == "TRAVEL"
        assert data["title"] == "周末郊游"

    def test_list_life_events_with_filter(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        client.post(f"/api/digital-twin/{vehicle_id}/life-events", json={
            "event_type": "MAINTENANCE",
            "title": "常规保养",
        })
        resp = client.get(f"/api/digital-twin/{vehicle_id}/life-events?event_type=MAINTENANCE")
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["event_type"] == "MAINTENANCE" for item in data["items"])


# ===========================================================================
# 7. Memories
# ===========================================================================

class TestMemories:
    def test_list_memories(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.get(f"/api/digital-twin/{vehicle_id}/memories")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_create_memory(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.post(f"/api/digital-twin/{vehicle_id}/memories", json={
            "memory_type": "habit",
            "content": "主人习惯晚上10点后驾驶",
            "emotion_score": 0.2,
            "importance": 6,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["memory_type"] == "habit"
        assert data["content"] == "主人习惯晚上10点后驾驶"

    def test_search_memories(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        client.post(f"/api/digital-twin/{vehicle_id}/memories", json={
            "memory_type": "preference",
            "content": "主人喜欢开启座椅加热",
        })
        resp = client.get(f"/api/digital-twin/{vehicle_id}/memories/search?q=座椅加热")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1


# ===========================================================================
# 8. Health Metrics
# ===========================================================================

class TestHealthMetrics:
    def test_list_health_metrics(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.get(f"/api/digital-twin/{vehicle_id}/health-metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_create_health_metric(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.post(f"/api/digital-twin/{vehicle_id}/health-metrics", json={
            "component": "brake",
            "health_score": 75.0,
            "temperature": 45.0,
            "wear_level": 65.0,
            "risk_level": "medium",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["component"] == "brake"
        assert data["risk_level"] == "medium"


# ===========================================================================
# 9. Predictions
# ===========================================================================

class TestPredictions:
    def test_list_predictions(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.get(f"/api/digital-twin/{vehicle_id}/predictions")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_create_prediction(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.post(f"/api/digital-twin/{vehicle_id}/predictions", json={
            "target_component": "tire",
            "prediction": "前轮胎纹深度将在5000公里后低于安全阈值",
            "risk_level": "high",
            "confidence": 0.82,
            "predicted_value": 5000,
            "predicted_unit": "km",
            "suggestion": "建议更换前轮轮胎",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["target_component"] == "tire"
        assert data["risk_level"] == "high"


# ===========================================================================
# 10. Driver Profile
# ===========================================================================

class TestDriverProfile:
    def test_get_driver_profile(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.get(f"/api/digital-twin/{vehicle_id}/driver-profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vehicle_id"] == vehicle_id
        assert "driver_style" in data

    def test_refresh_driver_profile(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.post(f"/api/digital-twin/{vehicle_id}/driver-profile/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vehicle_id"] == vehicle_id


# ===========================================================================
# 11. Agent Interface
# ===========================================================================

class TestAgentInterface:
    def test_doctor_agent(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.post(f"/api/digital-twin/{vehicle_id}/agent/doctor", json={
            "query": "请给出当前车辆的全面分析报告。",
            "agent_type": "doctor",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_type"] == "doctor"
        assert data["answer"]
        assert "confidence" in data
        assert "suggestions" in data

    def test_maintenance_agent(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.post(f"/api/digital-twin/{vehicle_id}/agent/maintenance", json={
            "query": "维护建议",
            "agent_type": "maintenance",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_type"] == "maintenance"
        assert data["answer"]

    def test_insurance_agent(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.post(f"/api/digital-twin/{vehicle_id}/agent/insurance", json={
            "query": "风险评估",
            "agent_type": "insurance",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_type"] == "insurance"
        assert data["answer"]

    def test_invalid_agent_type(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.post(f"/api/digital-twin/{vehicle_id}/agent/invalid", json={
            "query": "test",
            "agent_type": "invalid",
        })
        assert resp.status_code == 400


# ===========================================================================
# 12. 365-day Lifecycle Generator
# ===========================================================================

class TestLifecycleGenerator:
    def test_generate_lifecycle(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        resp = client.post(f"/api/digital-twin/{vehicle_id}/generate-lifecycle?force=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vehicle_id"] == vehicle_id
        assert data.get("skipped") is False or data.get("skipped") is None
        assert "health_metrics" in data
        assert "life_events" in data
        assert "memories" in data
        assert "predictions" in data

    def test_generate_lifecycle_skip_existing(self):
        vehicle_id = _ensure_vehicle()
        client.post(f"/api/digital-twin/create?vehicle_id={vehicle_id}")
        # Generate first
        client.post(f"/api/digital-twin/{vehicle_id}/generate-lifecycle?force=true")
        # Try again without force
        resp = client.post(f"/api/digital-twin/{vehicle_id}/generate-lifecycle")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("skipped") is True
