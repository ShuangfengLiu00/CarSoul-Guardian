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


async def _request(method: str, path: str, *, json=None, params=None, timeout: float = 30.0):
    # 服务间鉴权（P0 鉴权断链修复）：注入 Guardian 持有的 carModel 服务令牌。
    # 令牌由 carModel 用 CARSOUL_API_JWT_SECRET 签发，经 CARSOUL_WORLD_API_TOKEN
    # 环境变量注入；为空时调用必 401（fail-closed，不是 bug）。
    # 两侧 JWT 实现不同（Guardian=python-jose / carModel=stdlib），故不走共享密钥。
    headers = {}
    svc_token = settings.CARSOUL_WORLD_API_TOKEN
    if svc_token:
        headers["Authorization"] = f"Bearer {svc_token}"
    try:
        async with httpx.AsyncClient(
            base_url=settings.CARSOUL_WORLD_API_URL, timeout=timeout
        ) as client:
            resp = await client.request(
                method, path, json=json, params=params,
                headers=headers or None,
            )
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


async def compliance_gate_stats():
    """Fetch real compliance-gate interception counts from carModel.

    合规闸门跑在 **carModel 进程内**（agent/agent.py::_compliance_hit），
    Guardian 与它是两个独立进程，靠 HTTP 通信。因此计数只能记在 carModel 侧，
    Guardian 只做转发 —— 在 Guardian 里另起一个计数器只会数到"Guardian 自己
    看到的那部分"，与真实拦截总量对不上，属于另一种失真。

    carModel 读不到真值时返回 503，这里会原样变成 ``{"error": ...}``，
    由上层显示"暂无数据"而**不是** 0。
    """
    return await _request("GET", "/agent/compliance/gate-stats", timeout=10.0)


async def agent_chat(
    query: str,
    *,
    role: str = "owner",
    vehicle_id: str | None = None,
    session_id: str | None = None,
    mode: str = "compose",
):
    """Forward a natural-language question to carModel ``POST /agent/chat``.

    This is the ONLY LLM-backed conversational entrypoint in the whole system:
    it is the single path that carries RAG retrieval, forced citations, the
    compliance gate and honest-degradation discipline. Guardian must never
    answer a user question from local rules while pretending it came from here.

    Signature mirrors carModel's ``AgentChatReq``. Timeout is 60s (not the
    default 30s) because RAG + LLM composition is materially slower than the
    numeric prediction endpoints.

    Returns carModel's 20-field response dict, or ``{"error": ...}`` on failure.
    """
    return await _request(
        "POST",
        "/agent/chat",
        json={
            "query": query,
            "role": role,
            "vehicle_id": vehicle_id,
            "session_id": session_id,
            "mode": mode,
        },
        timeout=60.0,
    )
