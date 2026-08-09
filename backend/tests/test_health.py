"""Backend smoke tests (TASK006)."""
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app

# Guardian enforces global Bearer auth (app.core.auth.AuthMiddleware);
# tests must present a valid token. Auth is wired in TASK009.
client = TestClient(app, headers={"Authorization": f"Bearer {create_access_token('test-user')}"})


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["name"] == "CarSoul Guardian"


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_agent_chat_fallback():
    resp = client.post(
        "/api/agent/chat",
        json={"user": "tester", "message": "我的车需要保养吗"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_status"] in {"active", "degraded"}
    assert body["answer"]
