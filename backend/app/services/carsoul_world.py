"""Bridge client: Guardian -> CarSoul World Model (carModel) engine.

Forwards calls to the vehicle world model HTTP API (default
``http://localhost:8000``) so Guardian features can consume real SOH /
failure / residual / counterfactual predictions instead of mock data.

Every call degrades gracefully: network / HTTP errors return a structured
``{"error": ...}`` envelope instead of raising, so the UI can show
"world model unavailable" without a 500.
"""
from __future__ import annotations

import json

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


async def proxy_pass(
    method: str,
    path: str,
    *,
    json_body=None,
    params=None,
    timeout: float = 60.0,
) -> tuple[int, str, dict]:
    """Raw pass-through for the embedded cockpit iframe (white-listed upstream paths).

    Unlike ``_request`` (which collapses upstream errors into a 200 envelope),
    this preserves the upstream **status code and raw body** so the cockpit's
    ``api()`` helper can correctly distinguish success from 4xx/5xx (its
    ``if (!r.ok) throw`` contract drives the "engine offline" indicator).

    Returns ``(status_code, body_text, headers)``. Network-level failures map
    to 502 so the cockpit shows a degraded state instead of a parse error.
    """
    headers = {}
    svc_token = settings.CARSOUL_WORLD_API_TOKEN
    if svc_token:
        headers["Authorization"] = f"Bearer {svc_token}"
    try:
        async with httpx.AsyncClient(
            base_url=settings.CARSOUL_WORLD_API_URL, timeout=timeout
        ) as client:
            resp = await client.request(
                method, path, json=json_body, params=params, headers=headers or None
            )
            return resp.status_code, resp.text, dict(resp.headers)
    except httpx.HTTPError as exc:
        return 502, json.dumps({"error": "world_model_unavailable", "detail": str(exc)}), {}


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


async def compliance_samples(category: str | None = None, limit: int = 20):
    """Fetch real **PII-masked** compliance-gate samples from carModel.

    gate-stats 只回答"拦了多少次"，本端点回答"拦下的到底是什么样的提问"——
    二者共用诚实数据纪律：carModel 读不到真值时返回 503，这里原样变成
    ``{"error": ...}``，由上层显示"暂无数据"而**不是**空列表冒充"没有拦截过"。

    样本是脱敏后的占位符串（``[ID]`` / ``[PHONE]`` / …），原始问句不落盘、
    不进日志、不可反推；这是 PIPL 范围内唯一合法的明细留存形式。
    """
    params = {"limit": limit}
    if category:
        params["category"] = category
    return await _request(
        "GET", "/agent/compliance/samples", params=params, timeout=10.0
    )


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
