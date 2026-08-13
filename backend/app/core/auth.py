"""Global authentication middleware for the Guardian backend.

Design notes
------------
- Coverage is **global**: every route is protected unless its path is in the
  explicit, narrow ``PUBLIC_PATHS`` allow-list (or matches a public prefix).
  We deliberately do NOT use per-route ``Depends`` — experience on this project
  shows opt-in wiring always leaves gaps ("覆盖不全" 我们已经栽过太多次).
- The JWT is verified with the already-existing ``decode_access_token``
  (``app.core.security``). That function is the single source of truth for both
  issuance and verification, so we reuse it rather than write a second path.
- The ``Authorization`` scheme comparison uses ``hmac.compare_digest`` to avoid
  a timing side-channel on the scheme token.
- 401 responses never echo the presented token or the expected format.
- Production readiness: the app already refuses to boot without a valid
  ``JWT_SECRET`` (see ``app.core.config._enforce_config_policy``), so this
  middleware can safely assume ``settings.JWT_SECRET`` is present.
"""

from __future__ import annotations

import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_access_token

# Narrow, explicit public surface. Everything else is blocked.
# Login (and registration, needed to obtain a token in the first place) are the
# only business endpoints allowed through without a token.
PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/health",
        "/api/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/user/login",
        "/api/user/register",
    }
)

# Prefixes for resources that are never authenticated (served by nginx in prod).
# `/api/carsoul` 与 `/api/health` 是只读车况展示接口（Guardian 转发 carModel
# 世界模型），作为公开产品主页的展示数据源对外暴露，不要求先登录。
# `/api/agent` 是产品主页的 AI 对话入口，转发到 carModel /agent/chat，由引擎侧
# 的 5 类合规闸门 + 身份先于地理纪律兜底，故作为公开交互端点暴露（与
# `/api/carsoul`、`/api/health` 的公开化口径一致）。
PUBLIC_PREFIXES: tuple[str, ...] = (
    "/static",
    "/assets",
    "/api/carsoul",
    "/api/health",
    "/api/agent",
    # T-BOX 遥测为车况中心只读展示数据源（与 /api/carsoul 同口径），仿真数据
    # 经 data_source/confidence/quality_flags 透传标记，SPEC §12.2 冒烟测试免鉴权。
    "/api/v1/tbox",
)

_AUTH_SCHEME = "bearer"


def _is_public(path: str) -> bool:
    """Whether a request path bypasses the auth middleware."""
    if path in PUBLIC_PATHS:
        return True
    # 边界感知的前缀匹配：仅当 path 恰好等于前缀，或以 `前缀/` 开头时才豁免。
    # 不能用裸 startswith —— 否则 `/staticX`、`/assetsfoo` 乃至未来的
    # `/staticdata/export` 端点会被错误地当成静态资源而静默绕过鉴权。
    return any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in PUBLIC_PREFIXES
    )


def _unauthorized() -> JSONResponse:
    # Intentionally minimal: do NOT echo the token or the expected format.
    return JSONResponse(status_code=401, content={"detail": "Unauthorized"})


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if _is_public(request.url.path):
            return await call_next(request)

        authorization = request.headers.get("authorization")
        if not authorization:
            return _unauthorized()

        scheme, _, token = authorization.partition(" ")
        # Constant-time scheme comparison to avoid a timing side-channel.
        if not hmac.compare_digest(scheme.strip().lower(), _AUTH_SCHEME) or not token:
            return _unauthorized()

        payload = decode_access_token(token.strip())
        if payload is None:
            return _unauthorized()

        # Make the identity available to routes that opt in.
        request.state.user = payload
        return await call_next(request)
