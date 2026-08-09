"""Timeline Demo API tests (Step 8 — 'A Car's Life')."""
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app

# Guardian enforces global Bearer auth (app.core.auth.AuthMiddleware);
# tests must present a valid token. Auth is wired in TASK009.
client = TestClient(app, headers={"Authorization": f"Bearer {create_access_token('test-user')}"})


def test_life_story_endpoint():
    """GET /api/timeline/life-story returns a complete 3-year narrative."""
    resp = client.get("/api/timeline/life-story")
    assert resp.status_code == 200
    body = resp.json()

    # --- vehicle info ---
    v = body["vehicle"]
    assert v["vin"] == "VFSIM-2025-00042"
    assert v["name"] == "星辰号"
    assert v["profile"] == "family_ev"

    # --- 3 phases: 2025, 2026, 2027 ---
    phases = body["phases"]
    assert len(phases) == 3
    assert [p["year"] for p in phases] == [2025, 2026, 2027]
    assert [p["label"] for p in phases] == ["诞生", "用车", "异常"]

    # --- Phase 1: birth — SOH 100, mileage 0 ---
    p1 = phases[0]
    assert p1["telemetry"]["soh"] == 100.0
    assert p1["telemetry"]["mileage"] == 0.0
    assert len(p1["events"]) >= 2
    assert len(p1["memories"]) >= 2
    assert p1.get("agent_collaboration") is None or \
           p1["agent_collaboration"]["triggered"] is False

    # --- Phase 2: usage — SOH degraded, mileage increased ---
    p2 = phases[1]
    assert p2["telemetry"]["soh"] < 100.0
    assert p2["telemetry"]["mileage"] > 0
    assert p2["telemetry"]["fast_charge_ratio"] > 0

    # --- Phase 3: anomaly — agent collaboration triggered ---
    p3 = phases[2]
    assert p3["telemetry"]["charging_speed_ratio"] < 0.95
    collab = p3["agent_collaboration"]
    assert collab is not None
    assert collab["triggered"] is True
    assert collab["trigger_reason"]
    assert len(collab["findings"]) >= 3
    for f in collab["findings"]:
        assert f["agent_name"]
        assert f["finding"]
        assert 0.0 <= f["confidence"] <= 1.0


def test_life_story_demo_mode_flag():
    """demo_mode must always be True (red-line 2: simulated data only)."""
    resp = client.get("/api/timeline/life-story")
    assert resp.status_code == 200
    assert resp.json()["demo_mode"] is True


def test_life_story_health_report_traceability():
    """Every report metric must have a traceable source."""
    resp = client.get("/api/timeline/life-story")
    body = resp.json()
    report = body["report"]

    assert report["health_score"] > 0
    assert report["health_grade"]
    assert report["charging_strategy"]
    assert len(report["traceable_items"]) >= 4

    valid_sources = {"memory", "telemetry", "agent"}
    for item in report["traceable_items"]:
        assert item["source_type"] in valid_sources
        assert item["source_id"]
        assert item["source_description"]
        assert item["value"]


def test_life_story_deterministic():
    """Two calls return identical data (deterministic generator)."""
    r1 = client.get("/api/timeline/life-story").json()
    r2 = client.get("/api/timeline/life-story").json()
    assert r1 == r2


def test_life_story_valuation():
    """Used car valuation: projected > current, delta > 0."""
    resp = client.get("/api/timeline/life-story")
    val = resp.json()["report"]["used_car_valuation"]
    assert val["current"] > 0
    assert val["projected"] > val["current"]
    assert val["delta"] > 0
