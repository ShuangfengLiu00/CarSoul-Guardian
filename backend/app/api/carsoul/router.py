"""CarSoul World Model bridge API — Guardian -> carModel.

Exposes carModel's real SOH / failure / residual / counterfactual predictions
to the Guardian frontend through Guardian's own auth + CORS boundary. All
calls delegate to ``app.services.carsoul_world`` and degrade gracefully: if the
world-model engine is offline or returns an error envelope, we translate it
into a proper HTTP status instead of leaking a 500.

This keeps the "守护非控制" boundary: Guardian never computes vehicle physics
itself — it only forwards to the specialised engine and surfaces the result.
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel

from app.services import carsoul_world


router = APIRouter()


# --------------------------------------------------------------------------- #
# Request bodies
# --------------------------------------------------------------------------- #
class PredictRequest(BaseModel):
    vehicle_id: str
    horizon_days: int = 90


class ExplainRequest(BaseModel):
    vehicle_id: str
    concern: str = "general"


class ResidualRequest(BaseModel):
    vehicle_id: str
    horizon_months: int = 12


class FailureRequest(BaseModel):
    vehicle_id: str
    horizon_days: int = 90


class SimulateRequest(BaseModel):
    count: int = 10
    seed: int = 42


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _unwrap(payload: dict[str, Any]) -> dict[str, Any]:
    """Translate the bridge client's error envelope into an HTTPException."""
    if isinstance(payload, dict) and "error" in payload:
        err = payload["error"]
        if err.startswith("world_model_"):
            code = err[len("world_model_"):]
            try:
                status = int(code)
            except ValueError:
                status = 502
        else:
            status = 502
        raise HTTPException(status_code=status, detail=payload.get("detail", err))
    return payload


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@router.get("/health")
async def health() -> dict[str, Any]:
    """World-model engine liveness (carModel /health)."""
    return _unwrap(await carsoul_world.world_health())


@router.get("/state/{vehicle_id}")
async def state(vehicle_id: str) -> dict[str, Any]:
    """Latest world state for a vehicle (carModel /world/state/{id})."""
    return _unwrap(await carsoul_world.vehicle_state(vehicle_id))


@router.get("/history/{vehicle_id}")
async def history(
    vehicle_id: str,
    step: int = Query(30, ge=1, le=365),
) -> dict[str, Any]:
    """SOH / state history (carModel /world/history/{id})."""
    return _unwrap(await carsoul_world.soh_history(vehicle_id, step=step))


@router.post("/predict")
async def predict(body: PredictRequest) -> dict[str, Any]:
    """Forward SOH prediction (carModel /world/predict)."""
    return _unwrap(await carsoul_world.predict_soh(body.vehicle_id, body.horizon_days))


@router.post("/explain")
async def explain(body: ExplainRequest) -> dict[str, Any]:
    """Degradation explanation (carModel /world/explain)."""
    return _unwrap(await carsoul_world.explain_degradation(body.vehicle_id, body.concern))


@router.post("/residual")
async def residual(body: ResidualRequest) -> dict[str, Any]:
    """Residual-value prediction (carModel /world/residual)."""
    return _unwrap(await carsoul_world.predict_residual(body.vehicle_id, body.horizon_months))


@router.post("/failure")
async def failure(body: FailureRequest) -> dict[str, Any]:
    """Failure-risk prediction (carModel /world/failure)."""
    return _unwrap(await carsoul_world.predict_failure(body.vehicle_id, body.horizon_days))


@router.post("/simulate")
async def simulate(body: SimulateRequest) -> dict[str, Any]:
    """Trigger a carModel simulation batch (carModel /vehicle/simulate)."""
    return _unwrap(await carsoul_world.simulate_vehicles(body.count, body.seed))


# --------------------------------------------------------------------------- #
# Cockpit iframe pass-through (white-listed)
# --------------------------------------------------------------------------- #
# The embedded cockpit HTML calls carModel's **native** paths (/world/state/{id},
# /world/history/{id}, /world/residual, /agent/chat, ...) with no auth header
# (browser-embedded UI, same rationale as carModel's own /cockpit exemption).
# This endpoint forwards those paths to :8000 with Guardian's service token.
# It sits under /api/carsoul, which is already in Guardian's PUBLIC_PREFIXES
# (public product-page data source), so the iframe needs no login.
#
# Security: strict white-list only — no arbitrary path forwarding. Vehicle IDs
# are validated to avoid path injection into the upstream URL.
_VEHICLE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_GET_UPSTREAM_ALLOWED = frozenset({"world/state", "world/history"})
_POST_UPSTREAM_ALLOWED = frozenset(
    {
        "world/residual",
        "world/predict",
        "world/explain",
        "world/failure",
        "agent/chat",
    }
)


def _validate_proxy_path(method: str, path: str) -> str | None:
    """Return the upstream path if allowed, else None."""
    parts = path.split("/")
    if method == "GET":
        if len(parts) == 3 and parts[0] == "world" and "/".join(parts[:2]) in _GET_UPSTREAM_ALLOWED:
            vid = parts[2]
            return path if _VEHICLE_ID_RE.match(vid) else None
        return None
    if method == "POST":
        return path if path in _POST_UPSTREAM_ALLOWED else None
    return None


@router.api_route("/proxy/{path:path}", methods=["GET", "POST"])
async def proxy(path: str, request: Request) -> Response:
    """Forward a white-listed carModel endpoint for the embedded cockpit iframe."""
    upstream = _validate_proxy_path(request.method, path)
    if upstream is None:
        raise HTTPException(status_code=400, detail=f"path not allowed: {request.method} {path}")

    json_body = None
    if request.method == "POST":
        try:
            json_body = await request.json()
        except Exception:  # noqa: BLE001 — empty/invalid body → forward without body
            json_body = None

    status, body, _headers = await carsoul_world.proxy_pass(
        request.method,
        "/" + upstream,
        json_body=json_body,
        params=dict(request.query_params),
    )
    return Response(content=body, status_code=status, media_type="application/json")
