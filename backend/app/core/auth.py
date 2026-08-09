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
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/user/login",
        "/api/user/register",
    }
)

# Prefixes for resources that are never authenticated (served by nginx in prod).
PUBLIC_PREFIXES: tuple[str, ...] = ("/static", "/assets")

_AUTH_SCHEME = "bearer"


def _is_public(path: str) -> bool:
    """Whether a request path bypasses the auth middleware."""
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


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
