"""Bridge client: Guardian -> CarSoul World Model (carModel) engine.

Forwards calls to the vehicle world model HTTP API (default
``http://localhost:8000``) so Guardian features can consume real SOH /
failure / residual / counterfactual predictions instead of mock data.

Every call degrades gracefully: network / HTTP errors return a structured
``{"error": ...}`` envelope instead of raising, so the UI can show
"world model unavailable" without a 500.
"""
from __future__ import annotations

import httpx

from app.core.config import settings


async def _request(method: str, path: str, *, json=None, params=None):
    try:
        async with httpx.AsyncClient(
            base_url=settings.CARSOUL_WORLD_API_URL, timeout=30.0
        ) as client:
            resp = await client.request(method, path, json=json, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:  # carModel 4xx/5xx (含 404 无此车辆 / 503 模型未就绪)
        detail = exc.response.text[:300] if exc.response else ""
        return {"error": f"world_model_{exc.response.status_code}", "detail": detail}
    except httpx.HTTPError as exc:  # 连不上 / 超时
        return {"error": "world_model_unavailable", "detail": str(exc)}


async def world_health():
    return await _request("GET", "/health")


async def vehicle_state(vehicle_id: str):
    return await _request("GET", f"/world/state/{vehicle_id}")


async def soh_history(vehicle_id: str, step: int = 30):
    return await _request("GET", f"/world/history/{vehicle_id}", params={"step": step})


async def predict_soh(vehicle_id: str, horizon_days: int = 90):
    return await _request(
        "POST", "/world/predict",
        json={"vehicle_id": vehicle_id, "horizon_days": horizon_days},
    )


async def explain_degradation(vehicle_id: str, concern: str = "general"):
    return await _request(
        "POST", "/world/explain",
        json={"vehicle_id": vehicle_id, "concern": concern},
    )


async def predict_residual(vehicle_id: str, horizon_months: int = 12):
    return await _request(
        "POST", "/world/residual",
        json={"vehicle_id": vehicle_id, "horizon_months": horizon_months},
    )


async def predict_failure(vehicle_id: str, horizon_days: int = 90):
    return await _request(
        "POST", "/world/failure",
        json={"vehicle_id": vehicle_id, "horizon_days": horizon_days},
    )


async def simulate_vehicles(count: int = 10, seed: int = 42):
    return await _request(
        "POST", "/vehicle/simulate", json={"count": count, "seed": seed}
    )
